#!/usr/bin/env python3
"""整页转录：一页影像只送一次，把版面信息一次性拿全，之后所有比对都在本地做。

**为什么不按问题分遍送图**（SKILL.md §2.6「一页影像只送一次」）：
送图是唯一的大头成本且按页重复付——1100px 宽的页图约 2700 个图 token，
单次 $0.05，问什么几乎不影响单价。按问题分遍 = 同一张图付三次钱。
约翰斯通这本第一遍（只问文字）花了 $24，第二遍（只问斜体）刚跑 30 页就
发现这个错。

转录出来的是**第三个证人**（ABBYY / tesseract / 视觉模型）。这本书全网只有
一份扫描件，前两家在斜体上会一起失手，第三方因此特别值钱。

⚠️ 转录**只当证人，不进产物**：用来定位分歧，分歧处回影像定夺。
生成式模型读不清时会补一个通顺的词，这条不因为「看着挺准」而松动。

    python3 scripts/johnstone_transcribe.py --sample 20
    python3 scripts/johnstone_transcribe.py --all
"""
import argparse
import base64
import io
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_johnstone as E

ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'images')
OUT = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'vlm')
COST = os.path.join(ROOT, 'logs', 'johnstone_transcribe.tsv')
WIDTH = 1100

SYSTEM = (
    'Transcribe this page of a 19th-century printed book (Robert Johnstone, '
    '"Lectures Exegetical and Practical on the Epistle of Paul to the '
    'Philippians", Edinburgh 1875) exactly as printed.\n'
    'Conventions — follow them strictly:\n'
    '1. Mark italics with *asterisks* around the italic run. GREEK is set in a '
    'sloped Greek type throughout: that is the typeface, not emphasis — never '
    'mark Greek as italic.\n'
    '2. Put the running head on its own first line, prefixed  [HEAD] .\n'
    '3. Put each marginal verse figure inline, at the exact point it stands, '
    'wrapped like  [M:12] .\n'
    '4. Footnote markers in the text: write them as  [FN:1] . The footnotes '
    'themselves go at the end, each on its own line prefixed  [FN:1] .\n'
    '5. Printer signature marks at the foot (a lone letter or 2A etc.): '
    'write  [SIG:2A] .\n'
    '6. Keep the original spelling, punctuation and capitalisation exactly, '
    'including long dashes, ligatures (æ), and small capitals written as '
    'ordinary capitals.\n'
    '7. Join words broken by a line-break hyphen into one word; keep hyphens '
    'that belong to the word.\n'
    '8. Blank line between paragraphs. Do not add any commentary.\n'
    'Output the transcription and nothing else.'
)


def ask(png):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Transcribe this page.'}]}}
    cmd = ['claude', '-p', '--safe-mode', '--mcp-config', '{"mcpServers":{}}',
           '--strict-mcp-config', '--disallowedTools', '*',
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
                raise RuntimeError(str(o.get('result'))[:200])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leaves', default='')
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--seed', type=int, default=20261009)
    a = ap.parse_args()

    from PIL import Image
    os.makedirs(OUT, exist_ok=True)
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    sec = E.assign_leaves(ocr)
    body = [l for l in sorted(ocr) if sec.get(l) is not None and len(ocr[l]) > 20]
    done = {int(f[:-4]) for f in os.listdir(OUT) if f.endswith('.txt')}

    if a.leaves:
        leaves = [int(x) for x in a.leaves.split(',')]
    elif a.all:
        leaves = [l for l in body if l not in done]
    else:
        random.seed(a.seed)
        leaves = sorted(random.sample([l for l in body if l not in done],
                                      a.sample or 20))

    fh = open(COST, 'a', encoding='utf-8')
    total = 0.0
    for n, leaf in enumerate(leaves, 1):
        im = Image.open(os.path.join(IMG, f'{leaf:04d}.jp2'))
        im = im.resize((WIDTH, int(im.height * WIDTH / im.width)))
        buf = io.BytesIO(); im.save(buf, 'PNG')
        try:
            res, cost = ask(buf.getvalue())
        except Exception as e:
            print(f'{leaf:4d} 失败 {e}', file=sys.stderr); continue
        total += cost
        with open(os.path.join(OUT, f'{leaf:04d}.txt'), 'w', encoding='utf-8') as f:
            f.write(res)
        fh.write(f'{leaf}\t{cost:.4f}\t{len(res)}\n'); fh.flush()
        print(f'{leaf:4d} {len(res):5d} 字  ${cost:.4f}  累计 ${total:.2f}'
              f'  ({n}/{len(leaves)})', file=sys.stderr)
    fh.close()


if __name__ == '__main__':
    main()
