#!/usr/bin/env python3
"""
从 calvin_acts1.pdf 提取英文文字，通过 claude CLI 翻译成中文，
保存到 calvin_raw/acts/page_NNNN.txt，然后按章汇总写入 calvin/acts/N.md

章节页码（PDF 1-indexed）：
  第1章:  22-44    第8章:  186-210
  第2章:  45-79    第9章:  211-232
  第3章:  80-96    第10章: 233-260
  第4章:  97-113   第11章: 261-272
  第5章: 114-133   第12章: 273-283
  第6章: 134-144   第13章: 284-313
  第7章: 145-185

用法：
    python3 scripts/translate_acts.py              # 翻译全部 pp.22-313
    python3 scripts/translate_acts.py 22 44        # 只翻译第1章
    python3 scripts/translate_acts.py --assemble   # 只做汇总（跳过翻译）
"""
import sys, time, subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_usage import call_cli   # noqa: E402
import fitz

PDF    = Path('/Users/yanpeifa/Documents/论文/calvin_acts1.pdf')
OUT    = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/acts')
CALVIN = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin/acts')

CHAPTERS = [
    (1,  22,  44),
    (2,  45,  79),
    (3,  80,  96),
    (4,  97, 113),
    (5, 114, 133),
    (6, 134, 144),
    (7, 145, 185),
    (8, 186, 210),
    (9, 211, 232),
    (10, 233, 260),
    (11, 261, 272),
    (12, 273, 283),
    (13, 284, 313),
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
total_chapters: 13
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
        start = int(sys.argv[1]) if len(sys.argv) > 1 else 22
        end   = int(sys.argv[2]) if len(sys.argv) > 2 else 313
        translate(start, end)
        print('\n--- 开始汇总章节文件 ---')
        assemble()
