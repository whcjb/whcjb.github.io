#!/usr/bin/env python3
"""只问斜体：我们标的 `*…*` 与印面上真正排成斜体的，范围对不对。

全书印面比对那一遍的提示里**明说了忽略斜体标记差异**（不然每页都会被引号与
标记样式淹掉），所以斜体范围从来没验证过。这一支专问这一件事。

斜体在这本书里不是装饰：约翰斯通拿它区分「所引经文／他自己的修订译文」与
「讲解」，范围错一个词，读者就分不清哪句是经文。

    python3 scripts/johnstone_italic_proofread.py --sample 12
    python3 scripts/johnstone_italic_proofread.py --all
"""
import argparse
import base64
import io
import json
import os
import random
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import extract_johnstone as E
import johnstone_page_proofread as P

ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'images')
LOG = os.path.join(ROOT, 'logs', 'johnstone_italic.tsv')

SYSTEM = (
    'You are checking ITALICS only, on one page of a 19th-century printed book '
    '(Robert Johnstone on Philippians, Edinburgh 1875) against a transcription '
    'in which italics are marked with *asterisks*.\n'
    'Report ONLY places where the ITALIC EXTENT differs: a word printed in '
    'italic but not marked, a word marked but printed upright, or an italic run '
    'that starts/ends on the wrong word.\n'
    'Rules:\n'
    '1. One finding per line, exactly:  ITALIC: <our marking> ||| <what is printed>\n'
    '   Show the asterisks in both sides so the boundary is unambiguous.\n'
    '2. GREEK words are set in a sloped Greek type throughout — that is the '
    'typeface, NOT emphasis. Never report Greek as a missing italic.\n'
    '3. Ignore the running head, the page number, and spelling/word differences.\n'
    '4. Ignore italics inside the small-type footnotes at the foot of the page.\n'
    '5. If every italic run matches, answer exactly:  OK'
)


def ask(png, text):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Transcription of this page:\n\n' + text}]}}
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
    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    first, shapes = E.learn_heads(ocr)
    sec = E.assign_leaves(ocr)
    whole = P.published()
    w_words, w_pos = [], []
    for m in P.WORD.finditer(whole):
        w_words.append(m.group(0)); w_pos.append((m.start(), m.end()))

    body = [l for l in sorted(ocr)
            if sec.get(l) not in (None, 'front') and len(ocr[l]) > 20]
    done = set()
    if os.path.exists(LOG):
        done = {int(l.split('\t')[0]) for l in open(LOG, encoding='utf-8')
                if l.split('\t')[0].isdigit()}
    if a.leaves:
        leaves = [int(x) for x in a.leaves.split(',')]
    elif a.all:
        leaves = [l for l in body if l not in done]
    else:
        random.seed(a.seed)
        leaves = sorted(random.sample([l for l in body if l not in done],
                                      a.sample or 12))

    fh = open(LOG, 'a', encoding='utf-8')
    total = 0.0
    for n, leaf in enumerate(leaves, 1):
        raw = E.page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                          first.get(leaf, ''), shapes)
        # ⚠️ 这一支**不能剥星号**：要比的就是星号的位置
        text = P.slice_for(raw, whole, w_words, w_pos)
        if not text:
            fh.write(f'{leaf}\t0\tANCHOR-FAIL\t\n'); fh.flush(); continue
        im = Image.open(os.path.join(IMG, f'{leaf:04d}.jp2'))
        im = im.resize((P.WIDTH, int(im.height * P.WIDTH / im.width)))
        buf = io.BytesIO(); im.save(buf, 'PNG')
        try:
            res, cost = ask(buf.getvalue(), text)
        except Exception as e:
            print(f'{leaf:4d} 失败 {e}', file=sys.stderr); continue
        total += cost
        hits = [l.strip() for l in res.splitlines() if l.strip().startswith('ITALIC')]
        fh.write(f'{leaf}\t{cost:.4f}\t{"ITALIC" if hits else "OK"}\t'
                 + ' ⟂ '.join(hits) + '\n')
        fh.flush()
        print(f'{leaf:4d} {len(hits):2d} 处  ${cost:.4f}  累计 ${total:.2f}'
              f'  ({n}/{len(leaves)})', file=sys.stderr)
    fh.close()


if __name__ == '__main__':
    main()
