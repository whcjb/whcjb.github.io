#!/usr/bin/env python3
"""福特《路加福音讲义》整页转录：第三个证人（ABBYY / tesseract / 视觉模型）。

照 johnstone_transcribe.py（skill old-book-ocr §2.6「一页影像只送一次」）：一页送一次图，连版式标记一起转录，
之后所有比对在本地做。⚠️ 转录**只当证人，不进产物**：三家同位一致才落，分歧处回影像（原生分辨率裁图）定夺。

只转「残字 ≥3 处」的页（838）＋希腊引文页（tess_grc 置信度 ≥60 的希腊词 ≥2 个，58 页）＝866 页，
页单由 --pages 文件给（JSON 列表 "卷:leaf"）。图取 PDF 内嵌原图，缩到 1300px 宽（比约翰斯通的 1100 宽，
为了看清希腊重音）。一路串行（额度与翻译共用，见 feedback_translate_single_lane）。

    python3 scripts/foote_transcribe.py --pages <json> --sample 5
    python3 scripts/foote_transcribe.py --pages <json> --all
产物：foote_raw/luke/vlm/v{卷}/{leaf:04d}.txt；花费记 logs/foote_transcribe.tsv
"""
import argparse
import base64
import io
import json
import random
import subprocess
import sys
from pathlib import Path

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
PDF = {1: 'vol1_ed2_lecturesongospe03footgoog.pdf', 2: 'vol2_ed2_lecturesongospe02footgoog.pdf',
       3: 'vol3_ed2_lecturesongospe00footgoog.pdf'}
OUT = ROOT / 'foote_raw' / 'luke' / 'vlm'
COST = ROOT / 'logs' / 'foote_transcribe.tsv'
WIDTH = 1300

SYSTEM = (
    'Transcribe this page of a 19th-century printed book (James Foote, "Lectures on the Gospel according to '
    'Luke", 2nd edition, Edinburgh 1840s) exactly as printed.\n'
    'Conventions — follow them strictly:\n'
    '1. Put the running head (page number with LECTURE n., or LUKE i. 1-4. with page number) on its own first '
    'line, prefixed  [HEAD] .\n'
    '2. Mark italics with *asterisks* around the italic run. Greek is set in its own typeface: that is not '
    'emphasis — never mark Greek as italic.\n'
    '3. Transcribe Greek and Hebrew letter by letter with every accent and breathing exactly as printed. '
    'If a letter or accent cannot be made out, write [?] in its place rather than guessing.\n'
    '4. Footnote reference marks in the text (* † ‡ § ‖ ¶): write them as  [FN:*] , [FN:†]  etc. at the exact '
    'point. The footnotes themselves go at the end, each on its own line beginning  [FN:*]  etc.\n'
    '5. Printer signature marks at the foot (VOL. II. K, a lone letter or 2A): write  [SIG:...] .\n'
    '6. Keep the original spelling, punctuation and capitalisation exactly, including long dashes, '
    'æ/œ ligatures, and small capitals written as ordinary capitals. Do not modernise or correct anything, '
    'even an evident misprint.\n'
    '7. Join words broken by a line-break hyphen into one word; keep hyphens that belong to the word.\n'
    '8. Blank line between paragraphs; keep verse quotations and lines of poetry on their own lines.\n'
    '9. If a word is genuinely illegible, write [?] — never supply a word from context.\n'
    'Output the transcription and nothing else.'
)


def page_png(vol, leaf):
    doc = fitz.open(ROOT / 'foote_raw' / 'luke' / 'pdf' / PDF[vol])
    imgs = doc[leaf].get_images(full=True)
    raw = doc.extract_image(imgs[0][0])['image']
    im = Image.open(io.BytesIO(raw)).convert('L')
    if im.width > WIDTH:
        im = im.resize((WIDTH, int(im.height * WIDTH / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, 'PNG')
    return buf.getvalue()


def ask(png):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Transcribe this page.'}]}}
    # 同 CLI_TRIM_FLAGS：不发工具定义 / MCP / CLAUDE.md / skills
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config', '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json',
           '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True, text=True, timeout=900)
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:200])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result: ' + r.stderr[-200:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True)
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--all', action='store_true')
    a = ap.parse_args()
    pages = [tuple(map(int, x.split(':'))) for x in json.load(open(a.pages))]
    todo = [(v, l) for v, l in pages if not (OUT / f'v{v}' / f'{l:04d}.txt').exists()]
    if not a.all:
        random.seed(20261109)
        todo = sorted(random.sample(todo, min(a.sample or 5, len(todo))))
    COST.parent.mkdir(exist_ok=True)
    total, fails = 0.0, 0
    with open(COST, 'a', encoding='utf-8') as fh:
        for n, (v, l) in enumerate(todo, 1):
            try:
                res, cost = ask(page_png(v, l))
            except Exception as e:                     # noqa: BLE001
                fails += 1
                print(f'v{v} {l:4d} 失败 {e}', file=sys.stderr, flush=True)
                if 'limit' in str(e).lower():
                    print('⛔ 额度用尽，中止', file=sys.stderr, flush=True)
                    sys.exit(42)
                if fails >= 5:
                    print('⛔ 连续失败过多，中止', file=sys.stderr, flush=True)
                    sys.exit(3)
                continue
            fails = 0
            total += cost
            (OUT / f'v{v}').mkdir(parents=True, exist_ok=True)
            (OUT / f'v{v}' / f'{l:04d}.txt').write_text(res, encoding='utf-8')
            fh.write(f'{v}\t{l}\t{cost:.4f}\t{len(res)}\n')
            fh.flush()
            print(f'v{v} {l:4d} {len(res):5d} 字  ${cost:.4f}  累计 ${total:.2f}  ({n}/{len(todo)})',
                  file=sys.stderr, flush=True)


if __name__ == '__main__':
    main()
