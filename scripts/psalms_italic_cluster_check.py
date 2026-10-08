#!/usr/bin/env python3
"""**成簇**虚词斜体的影像复核——`psalms_italic_stray.py` 只判孤立的那一批。

`psalms_italic_stray` 的判据是「前后 60 字符内没有别的 `<em>`」：他的译词引用
总是成簇出现，孤零零一个虚词斜体才可疑。孤立的 13 处已逐处核完（真误判 4）。
**成簇的 183 处一直没核**——它们落在三种正当语境里（节号之后的整节译文、
`literally *to or for* it` 这类并列译法、`The *and* at the commencement` 这类
元语言），可「正当语境」是读出来的印象，读不出「这个词印面其实是正体」。

所以照样翻影像：按书页分组，把该页上要问的短语一次性列给模型，
只问**每个短语印面是斜体还是正体**，不让它重抄整页。
与我们不一致的，再自己裁图定案——模型顺着我们说「ITALIC」的那一侧不可信
（见 memory `feedback_model_none_unreliable`）。

用法：
    python3 scripts/psalms_italic_cluster_check.py --list        # 只列清单
    python3 scripts/psalms_italic_cluster_check.py --run         # 判读（约 $8）
    python3 scripts/psalms_italic_cluster_check.py --report      # 看分歧
"""
import argparse
import base64
import html
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import psalms_italic_stray as S

ROOT = Path(__file__).resolve().parent.parent
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
OFFSET = 3
OUT = ROOT / 'logs/alexander_psalms_italic_cluster.tsv'
PAGE = re.compile(r'<!-- PAGE (\d+) -->')
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")

SYSTEM = (
    'You are reading a page of a 19th-century printed book '
    '(Alexander, "The Psalms Translated and Explained", 1864) from its image.\n'
    'You are given the page image and a numbered list of short phrases. In each '
    'phrase one word is marked with ⟦ ⟧. For that marked word only, say whether '
    'it is printed in ITALIC type or in ROMAN (upright) type on this page.\n'
    'Rules:\n'
    '1. One line per item, exactly:  <n>: ITALIC   or   <n>: ROMAN   or   <n>: NOTFOUND\n'
    '2. Judge by the letterforms on the page, not by what you would expect. '
    'Italic in this book is a sloping face with a distinctly different "a", "e" and "y".\n'
    '3. The surrounding words of the phrase are given only to help you find the '
    'place. Judge ONLY the word between ⟦ ⟧.\n'
    '4. If you cannot find the phrase on this page, answer NOTFOUND. Never guess.\n'
    '5. Output nothing but those lines.'
)


def collect():
    items = []
    for p in sorted(S.SRC.glob('*.md'), key=lambda x: (x.stem != 'preface', x.stem)):
        raw = p.read_text(encoding='utf-8')
        md = raw.split('---', 2)[2] if raw.startswith('---') else raw
        out = subprocess.run(['kramdown', '--input', 'GFM'], input=md,
                             capture_output=True, text=True).stdout
        ems = [(m.start(), m.end(), html.unescape(S.TAG.sub('', m.group(1))).strip())
               for m in re.finditer(r'<em>(.*?)</em>', out, re.S)]
        marks = [(m.start(), int(m.group(1))) for m in PAGE.finditer(md)]
        mdw = [(m.start(), m.group(0)) for m in WORD.finditer(md)]
        seq = [w.lower() for _, w in mdw]
        for a, b, w in ems:
            if w.lower() not in S.FUNC:
                continue
            if not [s for s in ems if s[0] != a and s[0] < b + S.NEAR and s[1] > a - S.NEAR]:
                continue
            left = html.unescape(S.TAG.sub('', out[max(0, a - 160):a]))
            right = html.unescape(S.TAG.sub('', out[b:b + 70]))
            if S.META.search(left) or S.META_R.search(right):
                continue
            # 定位书页：左侧词序列在 md 里对齐；对不上就退一步用右侧
            pg = None
            for need in ([x.lower() for x in WORD.findall(left)[-5:]] + [w.lower()],
                         [w.lower()] + [x.lower() for x in WORD.findall(right)[:5]]):
                if len(need) < 3:
                    continue
                for i in range(len(seq) - len(need) + 1):
                    if seq[i:i + len(need)] == need:
                        pgs = [n for s, n in marks if s < mdw[i][0]]
                        pg = pgs[-1] if pgs else None
                        break
                if pg:
                    break
            items.append(dict(sec=p.stem, word=w, page=pg,
                              ctx=re.sub(r'\s+', ' ',
                                         left[-70:] + ' ⟦' + w + '⟧ ' + right[:45]).strip()))
    return items


def ask(png, lines):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Phrases on this page:\n\n' + '\n'.join(lines)}]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json',
           '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True,
                       text=True, timeout=900)
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:160])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError(f'no result rc={r.returncode} {r.stderr[:160]}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    items = collect()
    byp = defaultdict(list)
    for i, it in enumerate(items):
        if it['page']:
            byp[it['page']].append((i, it))
    print(f'成簇虚词斜体 {len(items)} 处；定位到书页 '
          f'{sum(len(v) for v in byp.values())} 处，占 {len(byp)} 个书页')
    if a.list:
        for pg in sorted(byp):
            for i, it in byp[pg]:
                print(f'  p{pg:>3} [{it["sec"]:>4}] *{it["word"]}*  …{it["ctx"]}…')
        return 0
    if a.report:
        if not OUT.exists():
            print('还没判读')
            return 0
        bad = [l for l in OUT.read_text(encoding='utf-8').splitlines()[1:]
               if l.split('\t')[3] != 'ITALIC']
        print(f'与我们不一致 / 找不到：{len(bad)} 处')
        for l in bad:
            print('  ' + l[:170])
        return 0
    if not a.run:
        print('要 --list / --run / --report')
        return 0
    import fitz
    doc = fitz.open(PDF)
    done = set()
    if OUT.exists():
        done = {l.split('\t')[0] for l in OUT.read_text(encoding='utf-8').splitlines()[1:]}
    newfile = not OUT.exists()
    total, n = 0.0, 0
    with OUT.open('a', encoding='utf-8') as fh:
        if newfile:
            fh.write('序号\t篇\t书页\t判读\t词\t上下文\n')
        for pg in sorted(byp):
            group = [(i, it) for i, it in byp[pg] if str(i) not in done]
            if not group:
                continue
            idx = pg + OFFSET
            if not (0 <= idx < doc.page_count):
                continue
            png = doc[idx].get_pixmap(dpi=300).tobytes('png')
            lines = [f'{k + 1}. {it["ctx"]}' for k, (_, it) in enumerate(group)]
            try:
                res, cost = ask(png, lines)
            except Exception as e:                           # noqa: BLE001
                print(f'  p{pg} 失败 {e}', flush=True)
                time.sleep(4)
                continue
            total += cost
            n += 1
            verdict = {}
            for line in res.splitlines():
                m = re.match(r'\s*(\d+)\s*[:.]\s*(ITALIC|ROMAN|NOTFOUND)', line, re.I)
                if m:
                    verdict[int(m.group(1))] = m.group(2).upper()
            for k, (i, it) in enumerate(group):
                v = verdict.get(k + 1, 'NOANSWER')
                fh.write(f'{i}\t{it["sec"]}\t{pg}\t{v}\t{it["word"]}\t{it["ctx"]}\n')
            fh.flush()
            if n % 10 == 0:
                print(f'[p{pg}] 已判 {n} 页，${total:.2f}', flush=True)
    print(f'完成 {n} 页 ${total:.2f} → {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
