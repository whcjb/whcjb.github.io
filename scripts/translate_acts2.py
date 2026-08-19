#!/usr/bin/env python3
"""
从 calvin_acts2.pdf 提取英文文字，通过 claude CLI 翻译成中文，
保存到 calvin_raw/acts2/page_NNNN.txt，然后按章汇总写入 calvin/acts/N.md

章节页码（PDF 1-indexed）：
  第14章:  8-24    第22章: 170-181
  第15章: 25-56    第23章: 182-196
  第16章: 57-78    第24章: 197-207
  第17章: 79-106   第25章: 208-215
  第18章: 107-121  第26章: 216-227
  第19章: 122-136  第27章: 228-237
  第20章: 137-155  第28章: 238-251
  第21章: 156-169

用法：
    python3 scripts/translate_acts2.py              # 翻译全部 pp.8-251
    python3 scripts/translate_acts2.py 8 24         # 只翻译第14章
    python3 scripts/translate_acts2.py --assemble   # 只做汇总（跳过翻译）
"""
import sys, time, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_usage import call_cli   # noqa: E402
import fitz

PDF    = Path('/Users/yanpeifa/Documents/论文/calvin_acts2.pdf')
OUT    = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts2')
CALVIN = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts')

CHAPTERS = [
    (14,   8,  24),
    (15,  25,  56),
    (16,  57,  78),
    (17,  79, 106),
    (18, 107, 121),
    (19, 122, 136),
    (20, 137, 155),
    (21, 156, 169),
    (22, 170, 181),
    (23, 182, 196),
    (24, 197, 207),
    (25, 208, 215),
    (26, 216, 227),
    (27, 228, 237),
    (28, 238, 251),
]

SYSTEM = (
    "你是一位精通加尔文神学的中文译者，专门翻译加尔文的圣经注释。"
    "请将英文原文翻译成流畅的中文，忠实原文，保持加尔文的神学深度和文体风格。"
    "要求：1.忠实原文，保持段落结构 "
    "2.经文节号保留，如'1. The former speech'→'1 前言确实……' "
    "3.拉丁文/希腊文保留原文并括号内附中文，如fides（信心） "
    "4.页码数字（单独一行）和CHAPTER X章节标题跳过不翻译 "
    "5.脚注编号保留 "
    "6.只输出译文，不加任何说明"
)

FRONT_MATTER = """\
---
layout: calvin-chapter
book_id: acts
book_name: 使徒行传
chapter: {chapter}
total_chapters: 28
header-img: psalm-bg-mountain.jpg
date: {date}
---

"""

def get_date():
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()

def translate_page(text: str) -> str:
    """调用 claude CLI 翻译一页文本"""
    prompt = f"请将以下加尔文《使徒行传注释》英文翻译成中文：\n\n{text}"
    # call_cli 带 CLI_TRIM_FLAGS（不发工具/MCP/CLAUDE.md/skills）并打印本次
    # token 用量；脚本结束时 claude_usage 会打印汇总。
    return call_cli(['--system-prompt', SYSTEM], prompt, timeout=300, label='页')

# ── 汇总 ────────────────────────────────────────────────────────────────
def assemble():
    CALVIN.mkdir(parents=True, exist_ok=True)
    now = get_date()
    for ch, start, end in CHAPTERS:
        parts = []
        for p in range(start, end + 1):
            f = OUT / f'page_{p:04d}.txt'
            if f.exists() and f.stat().st_size > 10:
                parts.append(f.read_text(encoding='utf-8').strip())
        if not parts:
            print(f'第{ch}章：无翻译文件，跳过')
            continue
        body = '\n\n'.join(parts)
        md = FRONT_MATTER.format(chapter=ch, date=now) + body + '\n'
        out_md = CALVIN / f'{ch}.md'
        out_md.write_text(md, encoding='utf-8')
        print(f'第{ch}章 → {out_md}  ({len(body)} 字)')
    print('汇总完成')

# ── 翻译 ────────────────────────────────────────────────────────────────
def translate(start_page, end_page):
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(str(PDF))

    print(f'翻译 PDF pp.{start_page}–{end_page}，共 {end_page - start_page + 1} 页')
    print(f'输出: {OUT}')

    ok = skip = err = 0
    t0 = time.time()

    for page_num in range(start_page, end_page + 1):
        out_file = OUT / f'page_{page_num:04d}.txt'
        if out_file.exists() and out_file.stat().st_size > 50:
            skip += 1
            continue

        idx = page_num - 1
        page_text = doc[idx].get_text().strip()
        if not page_text or len(page_text) < 20:
            out_file.write_text('', encoding='utf-8')
            skip += 1
            continue

        try:
            translated = translate_page(page_text)
            out_file.write_text(translated, encoding='utf-8')
            ok += 1
            elapsed = time.time() - t0
            avg = elapsed / ok
            eta = avg * (end_page - page_num)
            print(f'[p{page_num}] {len(translated)}字  avg={avg:.0f}s  ETA={eta/60:.0f}min', flush=True)
        except Exception as e:
            err += 1
            print(f'[p{page_num}] ERROR: {e}', flush=True)
            time.sleep(3)

    print(f'\n完成: {ok} 页翻译, {skip} 页跳过, {err} 页失败')
    print(f'总耗时: {(time.time()-t0)/60:.0f} 分钟')

# ── 入口 ────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if '--assemble' in sys.argv:
        assemble()
    else:
        start = int(sys.argv[1]) if len(sys.argv) > 1 else 8
        end   = int(sys.argv[2]) if len(sys.argv) > 2 else 251
        translate(start, end)
        print('\n--- 开始汇总章节文件 ---')
        assemble()
