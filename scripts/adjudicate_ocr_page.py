#!/usr/bin/env python3
"""扫描页图像 ↔ OCR raw 文本 逐页判读（无文本层底本专用）。

适用：底本 PDF 没有可用文本层，无法做零成本的机械比对
（scripts/audit_ocr_vs_pdf.py 那条路）。罗马书、歌罗西书是扫描件；
约翰福音虽有文本层但其自身也是 OCR，两边都不可信，同样走这里。

做法：把扫描页渲染成图，连同该页的 OCR raw 文本一起交模型，
只让它报「文本与图不符之处」，不让它重抄整页——重抄的输出 token 是
判读的两倍，且会引入新的生成式错误。

⚠️ 与 raw 的页码是**严格一一对应**的：page_000N.md ↔ PDF 第 N 页
（0-based 索引 N-1）。歌罗西书实测 76↔76 对齐。别的书套用前必须先验。

CLI 调用裁掉全部工具/MCP/CLAUDE.md（--safe-mode / --strict-mcp-config /
--disallowedTools "*"）。图像走 --input-format stream-json 传 base64；
该模式强制要求 --output-format stream-json 且必须加 --verbose。

用法：
    python3 scripts/adjudicate_ocr_page.py --book colossians --pages 20-23
    python3 scripts/adjudicate_ocr_page.py --book colossians --all
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

BOOKS = {
    'colossians': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/加尔文歌罗西书注释19716kb.pdf',
        'raw': 'calvin_raw/colossians-scan/ocr',
    },
    'romans': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/罗马书注释-加尔文.pdf',
        'raw': 'calvin_raw/romans-scan/ocr',
    },
    'john': {
        'pdf': '/Users/yanpeifa/Documents/论文/calvin/加尔文--约翰福音注释.pdf',
        'raw': 'calvin_raw/john-scan/ocr',
    },
}

SYSTEM = (
    '你是中文古籍校对员。给你一页扫描影像和一份该页的 OCR 文本，'
    '你的唯一任务是找出**文本与影像不符之处**。\n'
    '规则：\n'
    '1. 只报不符之处，不要重抄整页，不要复述、不要评论、不要总结\n'
    '2. 每处一行，格式严格为： 影像=「X」 文本=「Y」 上下文=「…前后各约8字…」\n'
    '3. 只报**实质字词**差异（错字、漏字、多字、串行）。\n'
    '   下列一律不报：标点、繁简、异体字（着/著、里/裡）、空格、换行、\n'
    '   页眉页码、以及 OCR 文本里的 markdown 标记\n'
    '4. 影像模糊无法判读的地方，写 影像=「?」并照实说明，不要猜\n'
    '5. 若整页没有实质差异，只输出一行： 无差异'
)


def render(pdf_path, page_idx, dpi=150):
    import fitz
    d = fitz.open(pdf_path)
    pm = d[page_idx].get_pixmap(dpi=dpi)
    png = pm.tobytes('png')
    d.close()
    return png


def ask(png, text, label=''):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64',
                                     'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': '这一页的 OCR 文本如下，请找出与影像不符之处：\n\n' + text},
    ]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config',
           '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json',
           '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n',
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f'CLI rc={r.returncode} {r.stderr[:200]}')
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('未拿到 result 事件')


def clean_raw(p: Path) -> str:
    t = p.read_text(encoding='utf-8')
    t = re.sub(r'^#.*$', '', t, flags=re.M)      # 去 raw 里的 markdown 标题
    return t.strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True, choices=sorted(BOOKS))
    ap.add_argument('--pages', help='如 20-23 或 5')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--dpi', type=int, default=150)
    ap.add_argument('--out', default=None)
    a = ap.parse_args()

    cfg = BOOKS[a.book]
    raws = sorted((ROOT / cfg['raw']).glob('page_*.md'))
    if not raws:
        sys.exit(f'找不到 raw：{cfg["raw"]}')

    if a.all:
        nums = list(range(1, len(raws) + 1))
    elif a.pages:
        if '-' in a.pages:
            lo, hi = map(int, a.pages.split('-'))
            nums = list(range(lo, hi + 1))
        else:
            nums = [int(a.pages)]
    else:
        sys.exit('要 --pages 或 --all')

    out_path = Path(a.out or f'logs/adjudicate_{a.book}.md')
    out_path.parent.mkdir(parents=True, exist_ok=True)
    total = 0.0
    hits = 0
    with out_path.open('a', encoding='utf-8') as fh:
        for n in nums:
            raw = ROOT / cfg['raw'] / f'page_{n:04d}.md'
            if not raw.exists():
                continue
            text = clean_raw(raw)
            if len(re.findall(r'[一-鿿]', text)) < 30:
                continue                     # 近空页（扉页等）跳过，省钱
            try:
                png = render(cfg['pdf'], n - 1, a.dpi)
                res, cost = ask(png, text, label=f'p{n}')
            except Exception as e:            # noqa: BLE001
                print(f'  p{n} 失败：{e}', flush=True)
                continue
            total += cost
            flagged = '无差异' not in res[:12]
            hits += flagged
            mark = '⚠' if flagged else '·'
            print(f'{mark} p{n:>4}  ${cost:.4f}  累计 ${total:.2f}', flush=True)
            if flagged:
                fh.write(f'\n## page {n}\n\n{res.strip()}\n')
                fh.flush()
            time.sleep(0.4)
    print(f'\n完成：{len(nums)} 页，其中 {hits} 页有差异；合计 ${total:.2f}')
    print(f'明细 → {out_path}')


if __name__ == '__main__':
    main()
