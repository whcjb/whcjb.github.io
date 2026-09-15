#!/usr/bin/env python3
"""对残留待复核项，用**紧贴该行的裁图**再判读——整页图定位太难，前两遍大量回 `?`。

裁图由 crop_meta.json 给出（锚点在 PDF 文本层里唯一命中才裁，见生成脚本）。
每次只送一张小图 + 一处 OCR 残串，模型只回答「影像上这一处印的是什么」。
跑两遍（--round 1 / 2），与整页第一遍的读数三者一致才算过闸。

用法：
    python3 scripts/adjudicate_alexander_crop.py --round 1
    python3 scripts/adjudicate_alexander_crop.py --round 2
"""
import argparse, base64, json, re, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = Path('/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/'
         'b389719a-2ff7-46f0-8f1a-c7a2ed5b858d/scratchpad')

SYSTEM = (
    'You are a careful palaeographer proof-reading a 19th-century printed book '
    '(Alexander, "The Psalms Translated and Explained", 1864).\n'
    'You get a tight crop of a few printed lines, and ONE spot where the OCR is '
    'suspected wrong. Report what the IMAGE actually shows at that spot.\n'
    'Rules:\n'
    '1. Output exactly one line:  reading=<what is printed>\n'
    '2. Give the original script. Hebrew/Greek type → Hebrew/Greek characters.\n'
    '3. If the OCR string is in fact correct as printed, output  reading=OK\n'
    '4. If you cannot make it out or cannot find the spot, output  reading=?\n'
    '   Never guess, never infer from context.\n'
    '5. Report only the word/phrase at that spot, nothing else.\n'
    '6. Keep 19th-century spelling (shews, connexion) — do NOT modernise.'
)


def ask(png, it):
    text = (f'The OCR text reads «{it["tok"]}» here:\n…{it["ctx"]}…\n\n'
            f'What does the image actually show in place of «{it["tok"]}»?')
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': text}]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config',
           '--disallowedTools', '*', '--input-format', 'stream-json',
           '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True,
                       text=True, timeout=600)
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
            res = str(o.get('result') or '')
            m = re.search(r'reading\s*=\s*(.+)', res)
            return (m.group(1).strip().strip('«»「」"') if m else '?'), \
                   float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--round', type=int, required=True, choices=(1, 2))
    a = ap.parse_args()
    meta = json.load(open(S / 'crop_meta.json'))
    out = ROOT / f'logs/alexander_crop_round{a.round}.tsv'
    done = set()
    if out.exists():
        done = {l.split('\t')[0] for l in out.open(encoding='utf-8')}
    total = 0.0
    fails = 0
    with out.open('a', encoding='utf-8') as fh:
        for k, it in enumerate(meta, 1):
            if str(it['n']) in done:
                continue
            png = (S / 'crop' / it['file']).read_bytes()
            try:
                res, cost = ask(png, it)
                fails = 0
            except Exception as e:                       # noqa: BLE001
                print(f'  #{it["n"]} 失败 {e}', flush=True)
                fails += 1
                if fails >= 5:
                    sys.exit('✗ 连续 5 次失败，中止（已判读的已落盘，重跑续上）')
                time.sleep(4)
                continue
            total += cost
            fh.write(f'{it["n"]}\t{it["sec"]}\t{it["tok"]}\t{res}\n')
            fh.flush()
            if k % 20 == 0:
                print(f'[{k}/{len(meta)}] ${total:.2f}', flush=True)
    print(f'完成 ${total:.2f} → {out}')


if __name__ == '__main__':
    main()
