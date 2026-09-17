#!/usr/bin/env python3
"""整页比对：把**页面影像**和我们这一页的正文一起送去，只问「哪里对不上」。

为什么要这一层：前面所有的闸都是「检测器」——它们只找自己认得的类型。
诗篇这条线上，所有检测器报全绿之后，实读三页又捞出四类全新的
（节号被读错、呼格 O 读成数字 0、引号多一个少一个、连字断在第一个字母）。
**新类型只能靠眼睛**，而 480 页靠人眼读不完。

所以换个问法：不让模型重抄整页（输出翻倍，还会引入新的生成式错误），
而是把我们的正文交给它，只让它**报差异**。核对比转写容易得多，也好验。

两遍独立跑，**只取两遍都报的**；再由人逐条核（多数能靠 1850 三卷本或裁图定案）。
模型报的东西一律当线索，不当结论——这一层出的是**待查清单**，不直接落盘。

刻意让它忽略的（我们成规矩的排印取舍，不是错）：
  · 斜体标记 `*…*`、`<!-- … -->` 注释
  · 19 世纪法式间距（`word ;` → `word;`）、弯引号 → 直引号
  · 行末连字（我们接成一个词）、页眉与页码（我们不收进正文）

用法：
    python3 scripts/psalms_page_proofread.py --round 1 --from 14 --to 30
    python3 scripts/psalms_page_proofread.py --round 2 --from 14 --to 30
    python3 scripts/psalms_page_proofread.py --report
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
OFFSET = 3                      # pdf_index = 书页页码 + OFFSET
PAGE_RE = re.compile(r'<!-- PAGE (\d+) -->')
TAG = re.compile(r'<[^<>]+>')


def log_path(rnd):
    return ROOT / f'logs/alexander_psalms_page_round{rnd}.tsv'


SYSTEM = (
    'You are proof-reading a 19th-century printed book against a transcription '
    '(Alexander, "The Psalms Translated and Explained", 1864).\n'
    'You get ONE page image and the transcription of that page. Report ONLY the '
    'places where the transcription does not match what is printed.\n'
    'Rules:\n'
    '1. One finding per line, exactly:  MISMATCH: <transcription> ||| <image>\n'
    '   Quote just enough words to locate it (3-8 words), not whole sentences.\n'
    '2. If the page matches, output exactly:  NONE\n'
    '3. IGNORE these — they are deliberate conventions of the transcription, '
    'not errors:\n'
    '   - italic markers *like this* and <!-- comments -->\n'
    '   - the running head and the page number (not transcribed at all)\n'
    '   - 19th-century spacing before punctuation ("word ; " -> "word;")\n'
    '   - curly quotes rendered as straight quotes\n'
    '   - a word hyphenated across a line break, rejoined into one word\n'
    '   - Hebrew and Greek words (a separate pass handles those)\n'
    '   - page boundaries: the transcription may start a paragraph early or run '
    'a paragraph past the end of this page. Ignore any text at the very start or '
    'the very end that simply belongs to the neighbouring page — report only '
    'mismatches inside the part that IS on this page.\n'
    '   - editorial matter added by the modern reprint (a "NOTE TO THE READER", '
    'roman-numeral conversion tables): not part of the work, never transcribed.\n'
    '4. DO report: wrong or missing or extra words; wrong verse numbers; wrong '
    'chapter/verse references (roman numerals and digits); punctuation that '
    'changes the sense; text that belongs to a different place.\n'
    '5. Never guess. If you cannot read the printed form, do not report it.\n'
    '6. Keep the original 19th-century spelling (shews, connexion) — those are '
    'correct, not errors.'
)


def page_text(pg, index):
    """这一页的正文（可能跨篇），去掉标记。"""
    out = []
    for sec, a, b in index.get(pg, []):
        t = (SRC / f'{sec}.md').read_text(encoding='utf-8')
        body = t.split('---', 2)[2] if t.startswith('---') else t
        out.append(TAG.sub('', body[a:b]))
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(out)).strip()


def build_index():
    index = defaultdict(list)
    for f in sorted(SRC.glob('*.md')):
        sec = f.stem
        t = f.read_text(encoding='utf-8')
        body = t.split('---', 2)[2] if t.startswith('---') else t
        marks = [(m.start(), int(m.group(1)), m.end()) for m in PAGE_RE.finditer(body)]
        for i, (s, pg, e) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
            index[pg].append((sec, e, end))
    return index


def render(doc, pg, dpi=300):
    import fitz                                    # noqa: F401
    idx = pg + OFFSET
    if not (0 <= idx < doc.page_count):
        return None
    return doc[idx].get_pixmap(dpi=dpi).tobytes('png')


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


def run(rnd, lo, hi, only_hits=False):
    import fitz
    index = build_index()
    keep = None
    if only_hits:
        keep = set()
        p1 = log_path(1)
        if p1.exists():
            for line in p1.open(encoding='utf-8'):
                f = line.rstrip('\n').split('\t')
                if len(f) >= 2 and f[1].isdigit() and int(f[1]) > 0:
                    keep.add(int(f[0]))
        print(f'第一遍报过差异的页：{len(keep)}')
    doc = fitz.open(PDF)
    out = log_path(rnd)
    done = set()
    if out.exists():
        done = {l.split('\t')[0] for l in out.open(encoding='utf-8')}
    total, fails, n = 0.0, 0, 0
    with out.open('a', encoding='utf-8') as fh:
        for pg in sorted(p for p in index if lo <= p <= hi):
            if str(pg) in done or (keep is not None and pg not in keep):
                continue
            text = page_text(pg, index)
            if not text.strip():
                continue
            png = render(doc, pg)
            if png is None:
                continue
            try:
                res, cost = ask(png, text)
                fails = 0
            except Exception as e:                        # noqa: BLE001
                print(f'  p{pg} 失败 {e}', flush=True)
                fails += 1
                if fails >= 5:
                    sys.exit('✗ 连续 5 次失败，中止（已判的已落盘，重跑续上）')
                time.sleep(4)
                continue
            total += cost
            n += 1
            hits = parse(res)
            fh.write(f'{pg}\t{len(hits)}\t' +
                     '\t'.join(f'{a} ||| {b}' for a, b in hits) + '\n')
            fh.flush()
            if n % 10 == 0:
                print(f'[{pg}] 已判 {n} 页，${total:.2f}', flush=True)
    print(f'完成 {n} 页 ${total:.2f} → {out}')


def norm(s):
    return re.sub(r'[^0-9a-zA-Z֐-׿]', '', s).lower()


def report():
    rounds = {}
    for rnd in (1, 2):
        d = defaultdict(list)
        p = log_path(rnd)
        if not p.exists():
            continue
        for line in p.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            pg = f[0]
            for item in f[2:]:
                if ' ||| ' in item:
                    a, b = item.split(' ||| ', 1)
                    d[pg].append((a, b))
        rounds[rnd] = d
    if len(rounds) < 2:
        print('两遍还没都跑完'); return
    both, only = [], 0
    for pg, items in rounds[1].items():
        other = rounds[2].get(pg, [])
        for a, b in items:
            m = [x for x in other if norm(x[0]) == norm(a) or norm(x[1]) == norm(b)]
            if m:
                both.append((pg, a, b, m[0][1]))
            else:
                only += 1
    out = ROOT / 'logs/alexander_psalms_page_candidates.tsv'
    with out.open('w', encoding='utf-8') as fh:
        fh.write('书页\t我们\t一遍读数\t二遍读数\n')
        for pg, a, b, b2 in both:
            fh.write(f'{pg}\t{a}\t{b}\t{b2}\n')
    print(f'两遍都报的 {len(both)} 处（只有一遍报的 {only} 处已丢弃）→ {out}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round', type=int, choices=(1, 2))
    ap.add_argument('--from', dest='lo', type=int, default=0)
    ap.add_argument('--to', dest='hi', type=int, default=9999)
    ap.add_argument('--report', action='store_true')
    ap.add_argument('--only-hits', action='store_true',
                    help='只跑第一遍报过差异的页——第二遍的活儿是筛掉假阳性，'
                         '第一遍一句话没说的页没什么可筛的')
    a = ap.parse_args()
    if a.report:
        report()
    elif a.round:
        run(a.round, a.lo, a.hi, a.only_hits)
    else:
        ap.error('要 --round N 或 --report')


if __name__ == '__main__':
    main()
