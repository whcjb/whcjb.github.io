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
        # ── 序言与导言（yaoyi1.pdf 实际页码） ──
        # 格式：(章ID, 起始页, 结束页, 章标题) 或 (章ID, 起始页, 结束页, 章标题, 栏目标题)
        # 章ID 为字符串时输出为序言章节（无"第X章"前缀）
        ("abbrev",   13,  16, "缩写与符号",                  "缩写与符号"),
        ("zh-intro", 17,  42, "中译本导言",                  "中译本导言"),
        ("intro",    43,  88, "导言",                        "导言"),
        ("preface",  89,  91, "约翰·加尔文致读者书（1559年版）", "致读者书"),
        ("argument", 92,  93, "1560年法文版主旨",             "1560年法文版主旨"),
        ("letter",   94, 116, "致法王法兰西斯一世书",          "致法王书"),
        # ── yaoyi1.pdf 第一卷正文（实际页码经章节标题核实） ──
        (1,  119, 122, "认识神与认识自己是密切相关的，而两者是如何相互关联的"),
        (2,  123, 126, "何谓认识神，以及认识神的意义何在"),
        (3,  127, 130, "人生来就有对神的认识"),
        (4,  131, 135, "这种知识因无知和恶毒被压抑或败坏了"),
        (5,  136, 154, "有关神的知识也彰显在宇宙的创造和护理之中"),
        (6,  155, 159, "任何要到神——造物者面前的人都必须经由圣经的引领和教导"),
        (7,  160, 167, "圣经必须受圣灵的印证，如此圣经的权威才得以确定；若说圣经的可靠性依赖教会的判断，这是邪恶的谎言"),
        (8,  168, 179, "就人的理性而言，有充足的证据证明圣经的可靠性"),
        (9,  180, 183, "那些离弃圣经只依靠异象的狂热分子，抛弃了一切敬虔的原则"),
        (10, 184, 187, "圣经为了避免一切的迷信，教导独一的真神在一切外邦人虚假的神之上"),
        (11, 188, 206, "圣经不许人勾画有形体的神，并且拜偶像就是背叛真神"),
        (12, 207, 211, "为了将一切的尊荣都归给神，我们应当清楚地区分神与偶像"),
        (13, 212, 252, "圣经从创世记开始就教导我们，神只有一个本质却有三个位格"),
        (14, 253, 275, "圣经在创造宇宙和万物的启示中，已清楚区分真神与众假神"),
        (15, 276, 289, "受造时的人性、神赐人的才能、神的形像、自由意志，及人堕落前的尊严"),
        (16, 290, 303, "神以祂的大能滋养和管理祂所创造的宇宙，并以自己的护理统治全宇宙"),
        (17, 304, 321, "我们如何从这教义中获得最大的益处"),
        (18, 322, 333, "神虽然利用罪人的恶行并扭转他们的心，使他们成就祂的旨意，但神自己却仍纯洁"),
    ],
    2: [
        # ── yaoyi1.pdf 第二卷正文（实际页码，部分待 OCR 完成后核实）──
        # ch1 和 ch2 已通过章节标题核实；ch3+ 待 OCR 完成后更新
        (1,  335, 348, "因亚当的堕落和背叛，全人类落在神的咒诅之下，从起初受造的光景中堕落了；原罪的教义"),
        (2,  349, 999, "人已完全丧失自由选择而悲惨地作罪的奴仆"),  # end page TBD
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
        (20, 518, 555, "政府"),
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
    节标题行（数字+点开头）视为完整，返回 '。' 阻止跨页拼接。
    真正的脚注行（圆圈开头且非长中文正文）跳过，继续向上查找。"""
    for line in reversed(text.split('\n')):
        s = line.strip()
        if not s:
            continue
        if re.match(r'^\d+[.．]\s*\S', s):   # 节标题行，视为完整
            return '。'
        # 真正的脚注行跳过（找上方的正文行）
        if s[0] in CIRCLED_SET and is_footnote_para(s):
            continue
        # 去掉行末带圈标号后取末字
        core = s.rstrip()
        while core and core[-1] in CIRCLED_SET:
            core = core[:-1].rstrip()
        return core[-1] if core else s[-1]
    return ''

def _append_to_last_body(text: str, addition: str) -> str:
    """将 addition 拼接到 text 最后一行正文行的末尾。
    跳过真正的脚注行（圆圈开头但内容短/非中文），保留正文版本标记行。"""
    lines = text.split('\n')
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if not s:
            continue
        # 跳过真正的脚注行（圆圈开头且不是长中文正文）
        if s[0] in CIRCLED_SET and is_footnote_para(s):
            continue
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
        first_nl = page_text.find('\n')
        first_line = page_text[:first_nl] if first_nl != -1 else page_text
        rest       = page_text[first_nl:] if first_nl != -1 else ''
        # 若下一页首行是节标题（数字+点），不拼接，直接换行
        next_is_heading = bool(re.match(r'^\d+[.．]\s+\S', first_line.strip()))
        if last_char and last_char not in SENTENCE_END and not next_is_heading:
            result = _append_to_last_body(result, first_line.lstrip()) + rest
        else:
            result = result + '\n' + page_text
    return result, all_footnotes

def is_footnote_para(line: str) -> bool:
    """判断是否为脚注行（圆圈数字开头后紧跟空格）。
    脚注格式：'⑤ 加尔文在此...'（圆圈后有空格）
    正文版本标记：'⑦我们所要谈...'（圆圈后直接跟文字，无空格）"""
    s = line.strip()
    if not s or s[0] not in CIRCLED_SET:
        return False
    # 圆圈后直接接非空格字符 → 正文版本标记，非脚注
    if len(s) > 1 and s[1] != ' ':
        return False
    return True

def is_group_label(line: str) -> bool:
    s = line.strip()
    return len(s) < 100 and bool(re.search(r'[（(]\d+[—\-–]\d+[）)]', s))

def clean_line(line: str) -> str:
    """去掉校勘标注 (a)(b)(b/a) 以及行首多余引号"""
    line = re.sub(r'\([a-z]+(?:/[a-z]+)*\)', '', line)
    line = re.sub(r'^[""]+', '', line.strip())
    return line.strip()

def process_chapter(ocr_dir: Path, ch_num, start_page: int,
                    end_page: int, ch_title: str, volume: int,
                    section_title_override: str = '') -> str:
    """ch_num 可为整数（正文章节）或字符串（序言/导言等）。"""
    is_preface = isinstance(ch_num, str)
    raw, all_footnotes = load_pages(ocr_dir, start_page, end_page)
    lines = raw.split('\n')

    main_lines: list[str] = []

    # 跳过开头的章标题（OCR 中可能跨多行）；序言不跳过
    skip_header = not is_preface
    skipped     = 0

    for raw_line in lines:
        line    = raw_line.rstrip()
        stripped = line.strip()

        # 跳过章标题区域：只跳过章标题行本身及其直接相连的续行
        # 遇到空行即停止，防止误吞紧接章标题的分组标签
        if skip_header and skipped < 10:
            if re.match(r'^[a-e°\s]*第[一二三四五六七八九十]+章', stripped):
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
            # 检查前一非空行是否是本标签的前半截（不以句末标点结尾，且自身不是标签/节标题）
            prev_idx = len(out) - 1
            while prev_idx >= 0 and not out[prev_idx].strip():
                prev_idx -= 1
            if prev_idx >= 0:
                prev_line = out[prev_idx].strip()
                # 去掉行末带圈标号后取末字
                prev_core = prev_line
                while prev_core and prev_core[-1] in CIRCLED_SET:
                    prev_core = prev_core[:-1].rstrip()
                prev_last = prev_core[-1] if prev_core else ''
                if (prev_last and prev_last not in SENTENCE_END
                        and not is_group_label(prev_line)
                        and not re.match(r'^###', prev_line)):
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

    now    = datetime.now().strftime('%Y-%m-%d %H:%M')

    if is_preface:
        sec_id    = f"{volume}-{ch_num}"
        sec_title = section_title_override or ch_title
        front_matter = f"""\
---
layout: reading-chapter
author_id: calvin
author_name: 约翰·加尔文
book_id: institutes
book_title: 基督教要义
section: "{sec_id}"
section_title: "{sec_title}"
chapter_title: "{ch_title}"
volume: {volume}
chapter: "{ch_num}"
date: {now}
---

"""
    else:
        ch_zh  = NUMS_ZH[ch_num - 1]
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
    # 可选第三个参数：指定单独处理某一章（整数章号或字符串 ID，如 "intro"）
    only_ch_arg = sys.argv[3] if len(sys.argv) >= 4 else None
    only_ch = None
    if only_ch_arg is not None:
        try:
            only_ch = int(only_ch_arg)
        except ValueError:
            only_ch = only_ch_arg  # 字符串 ID（如 "intro", "letter"）

    if not ocr_dir.is_dir():
        sys.exit(f"OCR 目录不存在：{ocr_dir}")

    chapters = CHAPTERS.get(volume, [])
    if not chapters:
        sys.exit(f"第 {volume} 卷暂无章节配置，请在脚本 CHAPTERS 中填写。")

    done = 0
    for entry in chapters:
        ch_num, start_p, end_p, title = entry[0], entry[1], entry[2], entry[3]
        sec_title_override = entry[4] if len(entry) >= 5 else ''
        if only_ch is not None and ch_num != only_ch:
            continue
        label = f"序言({ch_num})" if isinstance(ch_num, str) else f"第{ch_num}章"
        print(f"处理第{volume}卷{label}（页{start_p}–{end_p}）…", end=' ', flush=True)
        content = process_chapter(ocr_dir, ch_num, start_p, end_p, title, volume, sec_title_override)
        out_dir = OUT_DIR / f"{volume}-{ch_num}"
        out_dir.mkdir(exist_ok=True)
        (out_dir / "index.md").write_text(content, encoding="utf-8")
        print(f"{len(content)} 字节")
        done += 1

    print(f"\n✓ 第{volume}卷共 {done} 章写入完毕")


if __name__ == "__main__":
    main()
