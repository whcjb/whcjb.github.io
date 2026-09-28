#!/usr/bin/env python3
"""以赛亚书：抽一张**印刷书页**，把页面影像和我们这一页的正文一起送去，只问「哪里对不上」。

和诗篇那支（`psalms_page_proofread.py`）同一个道理，但**不能照抄它按
`<!-- PAGE n -->` 切页的做法**：

  诗篇的段落短，几乎每一页都有新段落起头，标记落在页首误差一段之内；
  以赛亚的段落常常一段横跨两三页，而标记是发在「**起头**在这一页的第一段」
  之前的——于是
    · 整页都是上一段续行的书页，一个标记也没有（卷一缺 104 页、卷二缺 112 页，
      合计 1153 页里的 216 页。这是段落粒度的必然结果，不是标记丢了）；
    · 有标记的页，标记位置也可能落在页中（书页 480 的标记落在 `V. 7.` 上，
      而印面 480 是从上一页的续行开始的）。
  照标记切，送进去的「这一页」可能横跨三张印面，模型会报出一堆假差异。

所以这里改成**按印面文字锚定**：拿 PDF 自带文本层取这一页的头尾各若干词，
在我们的正文里定位，按定位切片。锚不上就直说锚不上，不硬切——
锚不上本身就是线索（多半是整段丢失或严重错位）。

用法：
    python3 scripts/isaiah_page_proofread.py --vol 2 --pages 470,480,490,500
    python3 scripts/isaiah_page_proofread.py --vol 2 --pages 490 --round 2
    python3 scripts/isaiah_page_proofread.py --report
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
PDF_DIR = Path.home() / 'Documents/论文/alexander'

# 书页 → fitz 页序号（0 基）。由各章头部注释「书页 a-b | vN 扫描页 c-d」核出。
VOL = {
    1: dict(pdf='propheciesisaiah01alexuoft.pdf', delta=77, chapters=range(1, 40),
            hi=652),
    2: dict(pdf='propheciesisaiah02alexuoft.pdf', delta=45, chapters=range(40, 67),
            hi=501),
}

TAG = re.compile(r'<[^<>]+>')
HEAD = re.compile(r'^\s*\d{0,4}\s*(CHAPTER\s*[LXVIC ]+\.?|[A-Z]{3,}[A-Z .]*)\s*\d{0,4}\s*')

SYSTEM = (
    'You are proof-reading a 19th-century printed book against a transcription '
    '(J. A. Alexander, "The Prophecies of Isaiah", 1846-47).\n'
    'You get ONE page image and the transcription of that page. Report ONLY the '
    'places where the transcription does not match what is printed.\n'
    'Rules:\n'
    '1. One finding per line, exactly:  MISMATCH: <transcription> ||| <image>\n'
    '   Quote just enough words to locate it (3-8 words), not whole sentences.\n'
    '2. If the page matches, output exactly:  NONE\n'
    '3. IGNORE these — they are deliberate conventions of the transcription, '
    'not errors:\n'
    '   - italic markers *like this* and <!-- comments -->\n'
    '   - verse numbers: the book prints "V. 7." but the transcription writes '
    'just "7." — never report the missing "V."\n'
    '   - the running head and the page number (not transcribed at all)\n'
    '   - 19th-century spacing before punctuation ("word ; " -> "word;")\n'
    '   - curly quotes rendered as straight quotes\n'
    '   - a word hyphenated across a line break, rejoined into one word\n'
    '   - Hebrew, Greek, Syriac and Arabic words (a separate pass handles those)\n'
    '   - page boundaries: the transcription is cut by matching words, so it may '
    'start or end a few words inside the neighbouring page. Ignore anything that '
    'simply belongs to the neighbouring page — report only mismatches inside the '
    'part that IS on this page.\n'
    '4. DO report: wrong or missing or extra words; wrong verse numbers; wrong '
    'chapter/verse references (roman numerals and digits); punctuation that '
    'changes the sense; text that belongs to a different place.\n'
    '5. Never guess. If you cannot read the printed form, do not report it.\n'
    '6. Keep the original 19th-century spelling (shews, connexion, sceptick) — '
    'those are correct, not errors.\n\n'
    'Work in TWO passes before you answer, and report the union of both:\n'
    '  Pass 1 — read the printed page line by line against the transcription, '
    'word by word.\n'
    '  Pass 2 — go back to the top and re-check ONLY the things that are easy to '
    'skim past: punctuation that changes the sense (? ! ; : , .), opening and '
    'closing quotation marks, Latin / German / French words and their endings, '
    'proper names, chapter-and-verse numbers, and single letters that could be a '
    'different letter (b/l, c/e, n/u, i/j, 1/l).\n'
    'Report every finding from either pass, once each. Do not mention the passes.'
)
# 为什么把「两遍」写进提示词，而不是真的跑两遍：
# 同一配置独立跑两遍实测，单遍召回约 86–91%，第二遍每页只多出 0.3 条左右——
# 确实该看第二遍。但**第二遍不该再发一次图**：图占输入的七成、占每页费用的八成，
# 而第二遍要的只是多想一会儿。三条路量过：
#   · 再发一次图（朴素两遍）      $0.090/页
#   · `--resume` 续会话问第二遍    $0.068/页（图变成读缓存 0.1×，而不是写缓存 2×）
#   · **提示词里要求分两段看**     $0.055/页 ← 采用
# 第三条在 6 页上捞到 21 条，≥ 朴素两遍的并集 20 条（还多捞到
# `scelus estjugulare`、`tum agite`、`nec conventum`），代价只是每页多几百
# output token。所以**不需要第二轮扫描**。


def log_path(rnd):
    return ROOT / f'logs/alexander_isaiah_page_round{rnd}.tsv'


def norm(s):
    """只留字母数字，同时留下到原串的下标映射。"""
    out, idx = [], []
    for i, ch in enumerate(s):
        if ch.isalnum():
            out.append(ch.lower())
            idx.append(i)
    return ''.join(out), idx


def chapter_of(vol, pg):
    """哪一章覆盖这个书页（可能两章，取起头更早的那个）。"""
    hits = []
    for ch in VOL[vol]['chapters']:
        f = SRC / f'{ch}.md'
        if not f.exists():
            continue
        t = f.read_text(encoding='utf-8')
        m = re.search(r'<!-- isaiah \S+ \| 书页 (\d+)-(\d+) \| v(\d)', t)
        if not m or int(m.group(3)) != vol:
            continue
        if int(m.group(1)) <= pg <= int(m.group(2)):
            hits.append((ch, t))
    return hits


def body(t):
    b = t.split('---', 2)[2] if t.startswith('---') else t
    return TAG.sub('', b)


def printed(doc, vol, pg):
    page = doc[pg + VOL[vol]['delta']]
    txt = page.get_text().replace('\n', ' ')
    txt = re.sub(r'\s+', ' ', txt).strip()
    return HEAD.sub('', txt, count=1)


def locate(hay_n, hay_i, needle, hay):
    """锚串定位，返回原串下标；找不到返回 None。"""
    n, _ = norm(needle)
    if not n:
        return None
    p = hay_n.find(n)
    if p < 0 or hay_n.find(n, p + 1) >= 0:      # 找不到，或不唯一
        return None
    return hay_i[p], hay_i[p + len(n) - 1] + 1


def slice_our(vol, pg, doc):
    """按印面头尾锚，从我们的正文里切出这一页。"""
    pr = printed(doc, vol, pg)
    words = pr.split()
    if len(words) < 40:
        return None, None, f'印面文本太短（{len(words)} 词），跳过'
    for ch, t in chapter_of(vol, pg):
        hay = body(t)
        hay_n, hay_i = norm(hay)
        a = b = None
        for k in range(0, 12):                  # 头锚：往后挪，躲开被切坏的首词
            a = locate(hay_n, hay_i, ' '.join(words[k:k + 9]), hay)
            if a:
                break
        for k in range(0, 12):                  # 尾锚：往前挪，躲开页末断词
            b = locate(hay_n, hay_i, ' '.join(words[-9 - k:len(words) - k]), hay)
            if b:
                break
        if a and b and b[1] > a[0]:
            return ch, hay[a[0]:b[1]], None
        if a or b:
            return ch, None, f'只锚上{"头" if a else "尾"}一端（ch{ch}）'
    return None, None, '两端都锚不上'


def ask(png, text):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Transcription of this page:\n\n' + text}]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config',
           '--disallowedTools', '*', '--input-format', 'stream-json',
           '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True,
                       text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f'rc={r.returncode} {r.stderr[:160]}')
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:160])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result')


def parse(res):
    out = []
    for line in res.splitlines():
        m = re.match(r'\s*MISMATCH:\s*(.+?)\s*\|\|\|\s*(.+?)\s*$', line)
        if m:
            out.append((m.group(1), m.group(2)))
    return out


def run(vol, pages, rnd, dpi=200):
    import fitz
    doc = fitz.open(PDF_DIR / VOL[vol]['pdf'])
    out = log_path(rnd)
    done = set()
    if out.exists():
        done = {l.split('\t')[0] + l.split('\t')[1] for l in out.open(encoding='utf-8')
                if len(l.split('\t')) > 1}
    total, fails, n = 0.0, 0, 0
    with out.open('a', encoding='utf-8') as fh:
        for pg in pages:
            if f'{vol}{pg}' in done:
                print(f'  v{vol} p{pg} 已判过，跳过')
                continue
            ch, text, why = slice_our(vol, pg, doc)
            if text is None:
                print(f'  v{vol} p{pg} 切不出：{why}')
                fh.write(f'{vol}\t{pg}\t-\tSLICE-FAIL: {why}\n')
                fh.flush()
                continue
            png = doc[pg + VOL[vol]['delta']].get_pixmap(dpi=dpi).tobytes('png')
            try:
                res, cost = ask(png, text)
                fails = 0
            except Exception as e:                       # noqa: BLE001
                # 跑几百页的批量必须扛得住偶发失败：单页失败不落盘、不记 done，
                # 下次重跑自然补上；连续 5 次多半是会话额度用尽，整批中止
                print(f'  v{vol} p{pg} 失败 {e}', flush=True)
                fails += 1
                if fails >= 5:
                    sys.exit('✗ 连续 5 次失败，中止（已判的已落盘，重跑续上）')
                time.sleep(4)
                continue
            total += cost
            hits = parse(res)
            fh.write(f'{vol}\t{pg}\t{ch}\t{len(hits)}\t' +
                     '\t'.join(f'{a} ||| {b}' for a, b in hits) + '\n')
            fh.flush()
            n += 1
            print(f'  [{n}] v{vol} p{pg} (ch{ch}) → {len(hits)} 处 ${cost:.3f} '
                  f'累计 ${total:.2f}', flush=True)
            for a, b in hits:
                print(f'      我们「{a}」 ||| 印面「{b}」')
    print(f'合计 ${total:.2f} → {out}')


def report():
    for rnd in (1, 2):
        p = log_path(rnd)
        if not p.exists():
            continue
        print(f'== round {rnd} ==')
        for line in p.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            print('  ', '\t'.join(f[:4])[:160])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2))
    ap.add_argument('--pages')
    ap.add_argument('--round', type=int, default=1, choices=(1, 2))
    # 200 而不是 300：整页影像占输入 token 的七成，而且每页的图都不一样、
    # 永远命中不了缓存，按「写缓存」计费（1 小时 TTL 是 2× 基础价），
    # 每页开销的八成以上就是这一张图。
    # 300→200 实测 token 少 22%，**召回没有变化**：拿 8 页已扫但未落盘的页
    # 两个分辨率各跑一遍，共有 18 条，只 300 有 3 条、只 200 有 2 条——
    # 差的那几条是同一页两次跑的随机波动（引的词长短不同），不是看不清。
    # 再低没试过；裁掉页边白边只省 3%（文字块本来就占 74%），不值得做。
    ap.add_argument('--dpi', type=int, default=200)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.report:
        return report()
    if not (a.vol and a.pages):
        ap.error('要 --vol N --pages a,b,c')
    pages = []
    for part in a.pages.split(','):
        if '-' in part:
            lo, hi = part.split('-')
            pages += list(range(int(lo), int(hi) + 1))
        else:
            pages.append(int(part))
    run(a.vol, pages, a.round, a.dpi)


if __name__ == '__main__':
    sys.exit(main())
