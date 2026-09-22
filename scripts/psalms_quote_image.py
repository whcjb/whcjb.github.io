#!/usr/bin/env python3
"""段内引号配对不上的地方，回到 1864 影像上按**整段**判读。

为什么不能沿用「这一处印的是什么」那套：配对不上有两种成因，
  · 多出来一个引号（OCR 把脏点、逗号、字母读成了引号）→ 该删
  · 少了配对的那一半（OCR 把引号吞了）→ 该补
后者在「那一处」上根本问不出来——那一处本来就没有字。
所以改成问整段：**把印面上这一段里的引号逐个列出来**，再与我们的对齐。

也不能拿 1850 三卷本当证人：引号是**两版排印会不同**的东西，
诗 3「Absalom, his son」那次就是这么栽的——证人没有那个逗号，
1864 印面上有。引号这一类只认 1864 的影像。

两遍独立跑，取交集；出的是待判清单，逐条由人落。

用法：
    python3 scripts/psalms_quote_image.py --build
    python3 scripts/psalms_quote_image.py --round 1
    python3 scripts/psalms_quote_image.py --round 2
    python3 scripts/psalms_quote_image.py --report
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
OFFSET = 3
PAGE_RE = re.compile(r'<!-- PAGE (\d+) -->')
TAG = re.compile(r'<[^<>]+>')
META = ROOT / 'logs/alexander_psalms_quote_para.json'

SYSTEM = (
    'You are reading a page of a 19th-century printed book (Alexander, "The '
    'Psalms Translated and Explained", 1864).\n'
    'You get the page image and ONE paragraph as it was transcribed. Find that '
    'paragraph on the page and report EVERY quotation mark that is actually '
    'PRINTED in it.\n'
    'Rules:\n'
    '1. One line per printed quotation mark, exactly:\n'
    '     QUOTE: <3-5 words before> ^ <3-5 words after>\n'
    '   Use ^ to mark where the quotation mark stands. Copy the words as '
    'printed.\n'
    '2. If the paragraph contains no quotation mark at all, output exactly: NONE\n'
    '3. Count BOTH opening and closing marks, single and double alike. '
    'Report them in the order they appear.\n'
    '4. The transcription may differ from the print — that is the point. '
    'Report what the IMAGE shows, never what the transcription suggests.\n'
    '5. Apostrophes inside words (David\'s, can\'t) are NOT quotation marks; '
    'do not report them.\n'
    '6. If the paragraph runs onto the next page, report only the part that is '
    'on this page.\n'
    '7. If you cannot find the paragraph, output exactly: NOTFOUND'
)


def log_path(rnd):
    return ROOT / f'logs/alexander_psalms_quotepara_round{rnd}.tsv'


def build():
    """挑出段内引号配对不上的段落，连同它所在的书页。"""
    items = []
    for p in sorted(SRC.glob('*.md')):
        t = p.read_text(encoding='utf-8')
        body = t.split('---', 2)[2] if t.startswith('---') else t
        start = body.find('<!-- PAGE ')
        if start < 0:
            continue
        marks = [(m.start(), int(m.group(1))) for m in PAGE_RE.finditer(body)]
        pos = start
        for para in body[start:].split('\n\n'):
            plain = TAG.sub('', para)
            if plain.count('"') % 2:
                pg = next((n for off, n in reversed(marks) if off <= pos), None)
                if pg:
                    items.append(dict(sec=p.stem, page=pg,
                                      text=re.sub(r'\s+', ' ', plain).strip()))
            pos += len(para) + 2
    META.write_text(json.dumps(items, ensure_ascii=False, indent=1),
                    encoding='utf-8')
    print(f'配对不上的段落 {len(items)} 个 → {META}')


def ask(png, text):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'The paragraph, as transcribed:\n\n' + text}]}}
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


def run(rnd):
    import fitz
    items = json.loads(META.read_text(encoding='utf-8'))
    doc = fitz.open(PDF)
    out = log_path(rnd)
    done = {l.split('\t')[0] for l in out.open(encoding='utf-8')} if out.exists() else set()
    total, fails = 0.0, 0
    with out.open('a', encoding='utf-8') as fh:
        for i, it in enumerate(items):
            if str(i) in done:
                continue
            idx = it['page'] + OFFSET
            if not (0 <= idx < doc.page_count):
                continue
            # 原生 400 dpi，不上采样
            png = doc[idx].get_pixmap(dpi=400).tobytes('png')
            try:
                res, cost = ask(png, it['text'])
                fails = 0
            except Exception as e:                        # noqa: BLE001
                print(f'  #{i} 失败 {e}', flush=True)
                fails += 1
                if fails >= 5:
                    sys.exit('✗ 连续 5 次失败，中止')
                time.sleep(4)
                continue
            total += cost
            marks = [m.group(1).strip() for m in
                     re.finditer(r'QUOTE:\s*(.+)', res)]
            none = 'NONE' in res and not marks
            fh.write(f'{i}\t{it["sec"]}\t{it["page"]}\t'
                     f'{"NONE" if none else len(marks)}\t' + '\t'.join(marks) + '\n')
            fh.flush()
            if (i + 1) % 10 == 0:
                print(f'[{i+1}/{len(items)}] ${total:.2f}', flush=True)
    print(f'完成 ${total:.2f} → {out}')


def norm(s):
    return re.sub(r'[^a-z0-9^]', '', s.lower())


def report():
    items = json.loads(META.read_text(encoding='utf-8'))
    rounds = {}
    for rnd in (1, 2):
        d = {}
        p = log_path(rnd)
        if not p.exists():
            continue
        for line in p.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            d[int(f[0])] = (f[3], f[4:])
        rounds[rnd] = d
    if len(rounds) < 2:
        print('两遍还没都跑完')
        return
    out = ROOT / 'logs/alexander_psalms_quote_verdict.tsv'
    agree = differ = 0
    with out.open('w', encoding='utf-8') as fh:
        fh.write('序号\t篇\t书页\t我们几个\t影像几个\t两遍是否一致\t影像位置\t段落\n')
        for i, it in enumerate(items):
            a, b = rounds[1].get(i), rounds[2].get(i)
            if not a or not b:
                continue
            same = (a[0] == b[0] and
                    [norm(x) for x in a[1]] == [norm(x) for x in b[1]])
            agree += same
            differ += not same
            ours = it['text'].count('"')
            fh.write(f'{i}\t{it["sec"]}\t{it["page"]}\t{ours}\t{a[0]}\t'
                     f'{"一致" if same else "不一致"}\t{" ‖ ".join(a[1])}\t'
                     f'{it["text"][:90]}\n')
    print(f'两遍一致 {agree}，不一致 {differ} → {out}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--round', type=int, choices=(1, 2))
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.build:
        build()
    elif a.round:
        run(a.round)
    elif a.report:
        report()
    else:
        ap.error('要 --build / --round N / --report')


if __name__ == '__main__':
    main()
