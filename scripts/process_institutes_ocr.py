#!/usr/bin/env python3
"""
将 OCR 文本整理为基督教要义 Jekyll markdown 章节文件。

用法：
    python3 scripts/process_institutes_ocr.py <卷号> <OCR目录>

示例：
    python3 scripts/process_institutes_ocr.py 4 ~/Documents/论文/ocr_output/yaoyi3
    python3 scripts/process_institutes_ocr.py 2 ~/Documents/论文/ocr_output/yaoyi2

脚本读取 OCR 目录中的 page_NNNN.txt，按下方 CHAPTERS 配置拼合成章节，
生成 reading/calvin/institutes/<卷>-<章>/index.md。

每次新增 OCR 章节，只需在对应卷的 CHAPTERS 列表中追加条目，重新运行即可。
"""
import re, sys, subprocess
from pathlib import Path
from datetime import datetime

# ── 路径配置 ─────────────────────────────────────────────────────────────────
SITE_DIR = Path(__file__).parent.parent
OUT_DIR  = SITE_DIR / "reading/calvin/institutes"

CIRCLED     = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚"
CIRCLED_SET = set(CIRCLED)
NUMS_ZH     = ["一","二","三","四","五","六","七","八","九","十",
               "十一","十二","十三","十四","十五","十六","十七","十八","十九","二十"]

# ── 各卷章节配置 ─────────────────────────────────────────────────────────────
# 格式：(章号, OCR起始页1-based, OCR结束页1-based, 章标题)
# 起止页根据实际 OCR 文件确定，可用目录页反查。

CHAPTERS = {
    1: [
        # 第一卷已整理，如需重新生成可在此补充
        # (1, 页码, 页码, "章标题"),
    ],
    2: [
        # 第二卷已整理，如需重新生成可在此补充
    ],
    3: [
        # 第三卷已整理，如需重新生成可在此补充
    ],
    4: [
        # ── yaoyi3.pdf（下册）──
        # 已整理：
        (1,  8,  38, "我们必须保守与神的真教会合而为一的心，因为她是一切敬虔之人的母亲"),
        (2, 39,  51, "比较真假教会"),
        (3, 52,  66, "教会教师和牧师的资格及其职分"),
        (4, 67,  82, "古时教会的光景以及在未有天主教前的行政"),
        # 待补充（OCR 完成后填入页码）：
        # (5, 83, ???, "天主教的专制，完全推翻了古时教会的行政"),
        # (6, ???, ???, "罗马教区的首要性"),
        # ... 以此类推至第 20 章
    ],
}

VOLUME_TITLES = {
    1: "认识创造天地万物的神",
    2: "在救赎主基督里认识神",
    3: "我们领受基督之恩的方式",
    4: "神采用外在方式吸引我们与基督交通，并保守我们在这交通里",
}

# ── 工具函数 ──────────────────────────────────────────────────────────────────

def load_pages(ocr_dir: Path, start: int, end: int) -> str:
    texts = []
    for p in range(start, end + 1):
        f = ocr_dir / f"page_{p:04d}.txt"
        if f.exists():
            texts.append(f.read_text(encoding="utf-8").strip())
    return "\n".join(texts)

def is_footnote_para(line: str) -> bool:
    s = line.strip()
    return bool(s) and s[0] in CIRCLED_SET

def is_group_label(line: str) -> bool:
    s = line.strip()
    return len(s) < 100 and bool(re.search(r'[（(]\d+[—\-–]\d+[）)]', s))

def clean_line(line: str) -> str:
    """去掉校勘标注 (a)(b)(b/a) 以及行首多余引号"""
    line = re.sub(r'\([a-z]+(?:/[a-z]+)*\)', '', line)
    line = re.sub(r'^[""]+', '', line.strip())
    return line.strip()

def process_chapter(ocr_dir: Path, ch_num: int, start_page: int,
                    end_page: int, ch_title: str, volume: int) -> str:
    raw   = load_pages(ocr_dir, start_page, end_page)
    lines = raw.split('\n')

    main_lines: list[str] = []
    fn_blocks: dict[str, list[str]] = {}
    current_fn: str | None = None

    # 跳过开头的章标题（OCR 中可能跨多行）
    skip_header = True
    skipped     = 0

    for raw_line in lines:
        line    = raw_line.rstrip()
        stripped = line.strip()

        # 跳过章标题区域（前 10 行内探测）
        if skip_header and skipped < 10:
            if re.match(r'^第[一二三四五六七八九十]+章', stripped):
                skipped += 1; continue
            if skipped > 0 and stripped and len(stripped) < 35 and not re.search(r'\d', stripped):
                skipped += 1; continue  # 标题换行续行（纯中文短行）
            elif skipped > 0 and not stripped:
                skipped += 1; continue
            elif skipped > 0:
                skip_header = False

        # 脚注段落
        if is_footnote_para(stripped):
            current_fn = stripped[0]
            rest = re.sub(r'^\([a-z/]+\)\s*', '', stripped[1:].strip())
            fn_blocks[current_fn] = [rest]
            continue

        # 脚注续行
        if current_fn is not None and stripped:
            cn_ratio = sum(1 for c in stripped if '\u4e00' <= c <= '\u9fff') / max(len(stripped), 1)
            if cn_ratio > 0.65 and len(stripped) > 25 and not is_footnote_para(stripped):
                current_fn = None
                main_lines.append(line)
            else:
                fn_blocks[current_fn].append(stripped)
            continue

        current_fn = None
        main_lines.append(line)

    # 格式化正文
    out: list[str] = []
    prev_blank = False
    for raw_line in main_lines:
        line = raw_line.strip()
        if not line:
            if not prev_blank:
                out.append('')
            prev_blank = True
            continue
        prev_blank = False

        if is_group_label(line):
            out += ['', line, '']
            continue

        m = re.match(r'^(\d+)[.．]\s+(.+)', line)
        if m:
            out += ['', f'### {m.group(1)}. {clean_line(m.group(2))}', '']
            continue

        out.append(clean_line(line))

    # 去掉首尾空行
    while out and not out[0].strip():  out.pop(0)
    while out and not out[-1].strip(): out.pop()

    # 脚注 HTML
    fn_html = []
    for marker in CIRCLED:
        if marker in fn_blocks:
            text = ' '.join(fn_blocks[marker]).strip()
            if text:
                fn_html.append(f'<div class="inst-fn">{marker} {text}</div>')

    ch_zh  = NUMS_ZH[ch_num - 1]
    now    = datetime.now().strftime('%Y-%m-%d %H:%M')

    front_matter = f"""\
---
layout: reading-chapter
author_id: calvin
author_name: 约翰·加尔文
book_id: institutes
book_title: 基督教要义
section: "{volume}-{ch_num}"
section_title: "第{NUMS_ZH[volume-1]}卷·第{ch_zh}章"
chapter_title: "{ch_title}"
volume: {volume}
chapter: {ch_num}
date: {now}
---

## 第{ch_zh}章 {ch_title}

"""
    body = '\n'.join(out)
    fns  = '\n'.join(fn_html)
    return front_matter + body + ('\n\n' + fns if fns else '') + '\n'


# ── 主入口 ────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    volume  = int(sys.argv[1])
    ocr_dir = Path(sys.argv[2]).expanduser()

    if not ocr_dir.is_dir():
        sys.exit(f"OCR 目录不存在：{ocr_dir}")

    chapters = CHAPTERS.get(volume, [])
    if not chapters:
        sys.exit(f"第 {volume} 卷暂无章节配置，请在脚本 CHAPTERS 中填写。")

    for ch_num, start_p, end_p, title in chapters:
        print(f"处理第{volume}卷第{ch_num}章（页{start_p}–{end_p}）…", end=' ', flush=True)
        content = process_chapter(ocr_dir, ch_num, start_p, end_p, title, volume)
        out_dir = OUT_DIR / f"{volume}-{ch_num}"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "index.md").write_text(content, encoding="utf-8")
        print(f"{len(content)} 字节")

    print(f"\n✓ 第{volume}卷共 {len(chapters)} 章写入完毕")


if __name__ == "__main__":
    main()
