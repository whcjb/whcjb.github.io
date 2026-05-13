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

CIRCLED     = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟㊱㊲㊳㊴㊵㊶㊷㊸㊹㊺㊻㊼㊽㊾㊿"
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
        (1,   8,  38, "我们必须保守与神的真教会合而为一的心，因为她是一切敬虔之人的母亲"),
        (2,  39,  51, "比较真假教会"),
        (3,  52,  66, "教会教师和牧师的资格及其职分"),
        (4,  67,  82, "古时教会的光景以及在未有天主教前的行政"),
        (5,  83, 100, "天主教的专制，完全推翻了古时教会的行政"),
        (6, 101, 118, "罗马教区的首要性"),
        (7, 119, 153, "罗马教宗制度的来源，以及发展到整个教会的自由都被夺去了，并且教会毫无限制地受压制"),
        (8, 154, 172, "教会权威关于真道的信条，教会借着天主教放肆的行为，是如何败坏神的纯洁教义的"),
        (9, 173, 187, "会议以及会议的权威"),
        (10, 188, 221, "颁布法规的权威，就是教皇与他的支持者所用来对人极端野蛮的专政和残害"),
        (11, 222, 241, "教会司法权的范围以及天主教对此权柄的滥用"),
        (12, 242, 267, "教会的纪律；主要的用处在于斥责与革除教籍"),
        (13, 268, 292, "许愿，且轻率许愿的人叫自己悲惨地落在陷阱里"),
        (14, 293, 321, "圣礼"),
        (15, 322, 343, "洗礼"),
        (16, 344, 381, "婴儿洗礼最符合基督所设立的圣礼，以及这象征的性质"),
        (17, 382, 457, "基督的圣餐及其所带给我们的福分"),
        (18, 458, 479, "天主教亵渎神的弥撒，不但亵渎了主的圣餐，甚至也将之毁灭"),
        (19, 480, 519, "其他的五种仪式，错误地被称为圣礼，虽然到如今被视为圣礼，然而在此被证明是假的，且它们的真相被揭露出来"),
        (20, 520, 555, "政府"),
    ],
}

VOLUME_TITLES = {
    1: "认识创造天地万物的神",
    2: "在救赎主基督里认识神",
    3: "我们领受基督之恩的方式",
    4: "神采用外在方式吸引我们与基督交通，并保守我们在这交通里",
}

# ── 工具函数 ──────────────────────────────────────────────────────────────────

SENTENCE_END = set('。！？…""』）')

def _last_body_char(text: str) -> str:
    """返回文本中最后一行正文的末字（忽略行末带圈脚注标号）。
    节标题行（数字+点开头）视为完整，返回 '。' 阻止跨页拼接。"""
    for line in reversed(text.split('\n')):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+[.．]\s*\S', s):   # 节标题行，视为完整
            return '。'
        # 去掉行末带圈标号后取末字
        core = s.rstrip()
        while core and core[-1] in CIRCLED_SET:
            core = core[:-1].rstrip()
        return core[-1] if core else s[-1]
    return ''

def _append_to_last_body(text: str, addition: str) -> str:
    """将 addition 拼接到 text 最后一行正文行的末尾。"""
    lines = text.split('\n')
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if s and s[0] not in CIRCLED_SET:
            lines[i] = lines[i].rstrip() + addition
            return '\n'.join(lines)
    return text + addition

def _extract_page_parts(page_text: str) -> tuple[str, list[tuple[str, str]]]:
    """从单页 OCR 文本中分离正文与脚注。

    返回 (body_text, ordered_fns)：
    - body_text: 去掉脚注行的正文
    - ordered_fns: [(local_marker, text), ...] 按页面出现顺序
    """
    lines = page_text.split('\n')
    body_lines: list[str] = []
    page_fn_dict: dict[str, list[str]] = {}
    page_fn_order: list[str] = []
    current_fn: str | None = None

    for line in lines:
        stripped = line.strip()
        if is_footnote_para(stripped):
            current_fn = stripped[0]
            rest = re.sub(r'^\([a-z/]+\)\s*', '', stripped[1:].strip())
            if current_fn not in page_fn_dict:
                page_fn_dict[current_fn] = [rest]
                page_fn_order.append(current_fn)
            else:
                page_fn_dict[current_fn].append(rest)
        elif current_fn is not None and stripped:
            cn_ratio = sum(1 for c in stripped if '\u4e00' <= c <= '\u9fff') / max(len(stripped), 1)
            if cn_ratio > 0.65 and len(stripped) > 25 and not is_footnote_para(stripped):
                current_fn = None
                body_lines.append(line)
            else:
                page_fn_dict[current_fn].append(stripped)
        else:
            current_fn = None
            body_lines.append(line)

    ordered_fns = [(m, ' '.join(page_fn_dict[m]).strip()) for m in page_fn_order]
    return '\n'.join(body_lines), ordered_fns


def _replace_inline_markers(text: str, fn_map: dict[str, str]) -> str:
    """将正文中的带圈数字替换为全局顺序带圈数字。"""
    for old_marker, new_marker in fn_map.items():
        text = text.replace(old_marker, new_marker)
    return text


def load_pages(ocr_dir: Path, start: int, end: int
               ) -> tuple[str, list[tuple[int, str]]]:
    """拼合多页 OCR 文本，返回 (joined_body, all_footnotes)。

    - joined_body: 去掉脚注行、修复跨页断句的正文
    - all_footnotes: [(global_n, text), ...] 全局顺序脚注
    """
    all_footnotes: list[tuple[int, str]] = []
    body_pages: list[str] = []

    for p in range(start, end + 1):
        f = ocr_dir / f"page_{p:04d}.txt"
        if not f.exists():
            continue
        page_text = f.read_text(encoding="utf-8").strip()
        body_text, ordered_fns = _extract_page_parts(page_text)

        # 分配全局顺序带圈数字并替换正文内联标记
        local_to_global: dict[str, str] = {}
        for marker, fn_text in ordered_fns:
            n = len(all_footnotes)  # 0-based index into CIRCLED
            global_marker = CIRCLED[n] if n < len(CIRCLED) else f'({n+1})'
            all_footnotes.append((global_marker, fn_text))
            local_to_global[marker] = global_marker
        if local_to_global:
            body_text = _replace_inline_markers(body_text, local_to_global)
        body_pages.append(body_text)

    if not body_pages:
        return "", []

    # 跨页拼接（基于已去脚注的正文）
    result = body_pages[0]
    for page_text in body_pages[1:]:
        last_char = _last_body_char(result)
        if last_char and last_char not in SENTENCE_END:
            first_nl = page_text.find('\n')
            if first_nl == -1:
                first_line, rest = page_text, ''
            else:
                first_line, rest = page_text[:first_nl], page_text[first_nl:]
            result = _append_to_last_body(result, first_line.lstrip()) + rest
        else:
            result = result + '\n' + page_text
    return result, all_footnotes

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
    raw, all_footnotes = load_pages(ocr_dir, start_page, end_page)
    lines = raw.split('\n')

    main_lines: list[str] = []

    # 跳过开头的章标题（OCR 中可能跨多行）
    skip_header = True
    skipped     = 0

    for raw_line in lines:
        line    = raw_line.rstrip()
        stripped = line.strip()

        # 跳过章标题区域：只跳过章标题行本身及其直接相连的续行
        # 遇到空行即停止，防止误吞紧接章标题的分组标签
        if skip_header and skipped < 10:
            if re.match(r'^[°\s]*第[一二三四五六七八九十]+章', stripped):
                skipped += 1; continue
            if skipped > 0 and not stripped:
                skip_header = False
                continue
            if skipped > 0 and stripped and len(stripped) < 20 and not re.search(r'\d', stripped):
                skipped += 1; continue
            elif skipped > 0:
                skip_header = False

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
            # 检查前一非空行是否是本标签的第一行（以、或，结尾，且自身不含页码范围）
            prev_idx = len(out) - 1
            while prev_idx >= 0 and not out[prev_idx].strip():
                prev_idx -= 1
            if prev_idx >= 0 and out[prev_idx].strip().endswith(('、', '，', ',')):
                prev_line = out[prev_idx].strip()
                if not is_group_label(prev_line):
                    merged = prev_line + line
                    out = out[:prev_idx]
                    while out and not out[-1].strip():
                        out.pop()
                    out += ['', merged, '']
                    continue
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

    # 后处理：合并被空行误断的跨页句子
    # 若某行不以句末标点结尾，且紧跟空行+普通正文（非标题/分组标签），则去掉空行
    fixed: list[str] = []
    i = 0
    while i < len(out):
        line = out[i]
        if (line == '' and fixed and i + 1 < len(out)):
            prev = fixed[-1].strip()
            nxt  = out[i + 1].strip()
            # 判断前行末字（忽略行末带圈脚注标号）
            tmp = prev
            while tmp and tmp[-1] in CIRCLED_SET: tmp = tmp[:-1].rstrip()
            last = tmp[-1] if tmp else ''
            is_continuation = (
                last and last not in SENTENCE_END
                and not re.match(r'^[#<]|^---', nxt)
                and not is_group_label(nxt)
                and not re.match(r'^\d+[.．]\s', nxt)
                and nxt  # 下一行非空
            )
            if is_continuation:
                i += 1  # 跳过这个空行
                continue
        fixed.append(line)
        i += 1
    out = fixed

    # 脚注 HTML（全局顺序带圈数字）
    fn_html = []
    for marker, text in all_footnotes:
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
