#!/usr/bin/env python3
"""restructure_thess_en.py — 把 calvin/{1,2}thessalonians-en/*.md 从
旧 Ages 格式（或半改的 .calvin-parallel 中间态）重构为 1cor/2cor 那种
scripture-box 双语 table 结构。

支持多种输入形态：
  A. 纯裸格式:
       **N.** English
       <p style="text-align:right;">N. Latin</p>
  B. 半改中间态:
       <table class="scripture-table calvin-parallel">
       <tr><td><p><strong>N.</strong> English</p></td><td><p>N. Latin</p></td></tr>
       ...
       </table>
  C. Smushed 段落 (Latin_N + English_N+1):
       <p style="margin-left:2em;" markdown="1">**N.** Latin_N. M. English_M</p>

输出 (对齐 1cor gold):
       <div class="scripture-box scripture-box--bilingual" markdown="1">
       <p class="scripture-ref"><span class="ages-code">&lt;NNCCVV&gt;</span>
         <span class="book-name">TITLE</span> <span class="verse-range">C:V-V</span></p>
       <h2 class="scripture-anchor" id="book-c-v-v" data-ref="TITLE C:V-V"
         style="display:none">TITLE C:V-V</h2>
       <table class="scripture-bilingual">
       <tbody>
       <tr><td class="scripture-en">...</td><td class="scripture-la">...</td></tr>
       ...

用法：
    python3 scripts/restructure_thess_en.py 1thess           # 1 Thess 全 5 章
    python3 scripts/restructure_thess_en.py 2thess           # 2 Thess 全 3 章
    python3 scripts/restructure_thess_en.py 1thess 3         # 单章
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BOOKS = {
    '1thess': {
        'src_dir': ROOT / 'calvin/1thessalonians-en',
        'book_num': 52,
        'title': '1 Thessalonians',
        'upper': '1 THESSALONIANS',
        'anchor_prefix': '1-thessalonians',
    },
    '2thess': {
        'src_dir': ROOT / 'calvin/2thessalonians-en',
        'book_num': 53,
        'title': '2 Thessalonians',
        'upper': '2 THESSALONIANS',
        'anchor_prefix': '2-thessalonians',
    },
    '1timothy': {
        'src_dir': ROOT / 'calvin/1timothy-en',
        'book_num': 54,
        'title': '1 Timothy',
        'upper': '1 TIMOTHY',
        'anchor_prefix': '1-timothy',
    },
}


# Smushed <p margin-left> containing Latin_N + English_N+1
# 1timothy 常见 English 起首形态是无点数字 `2 Unto Timothy`（bare），所以
# 第二个数字后的 `\.` 需要可选
SMUSHED_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">'
    r'(?:\*\*(\d+)\.\*\*|(\d+)\.\s*[—–-]?)\s*'
    r'([^<]+?)\s+(\d+)\.?\s+'
    r'([A-Z(“"\'][^<]+?)</p>',
)


def split_smushed(m: re.Match) -> str:
    n = int(m.group(1) or m.group(2))
    latin_body = m.group(3).strip()
    m2 = int(m.group(4))
    english_body = m.group(5).strip()
    if m2 != n + 1:
        return m.group(0)
    return (
        f'<p style="text-align:right;" markdown="1">{n}. {latin_body}</p>\n\n'
        f'<p style="margin-left:2em;" markdown="1">**{m2}.** {english_body}</p>'
    )


_MEGA_P_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">(.+?)</p>', re.S
)
_MEGA_MARKER_RE = re.compile(
    r'(\*\*(\d+)\.\*\*|(?<=\s)(\d+)\.(?=\s))'
)


def split_mega_smushed(text: str) -> str:
    """把 <p margin-left>**N.** Latin M. Eng M. Lat M+1. Eng...</p> 拆多段"""

    def repl(m: re.Match) -> str:
        content = m.group(1)
        markers = []
        for mm in _MEGA_MARKER_RE.finditer(content):
            markers.append({
                'start': mm.start(),
                'end': mm.end(),
                'n': int(mm.group(2) or mm.group(3)),
                'bold': bool(mm.group(2)),
            })
        if len(markers) < 2:
            return m.group(0)
        segments = []
        for i, mkr in enumerate(markers):
            body_end = markers[i + 1]['start'] if i + 1 < len(markers) else len(content)
            segments.append({
                'n': mkr['n'],
                'bold': mkr['bold'],
                'body': content[mkr['end']:body_end].strip(),
            })
        # 首段 bold=Latin. 后续 bare 段: 同 N 第一次=EN, 第二次=LA.
        # 特例: 首段是 bare (无 bold), 按 EN 处理.
        out = []
        seen: dict[int, int] = {}
        for seg in segments:
            n = seg['n']
            if seg['bold']:
                kind = 'la'
            else:
                seen[n] = seen.get(n, 0) + 1
                kind = 'en' if seen[n] == 1 else 'la'
            body = seg['body'].rstrip('.,;: ') + ('.' if seg['body'].endswith('.') else '')
            body = seg['body']
            if kind == 'la':
                out.append(
                    f'<p style="text-align:right;" markdown="1">{n}. {body}</p>'
                )
            else:
                out.append(
                    f'<p style="margin-left:2em;" markdown="1">**{n}.** {body}</p>'
                )
        return '\n\n'.join(out)

    return _MEGA_P_RE.sub(repl, text)


def md_to_html(s: str) -> str:
    s = re.sub(r'^\*\*(\d+)\.\*\*', r'<strong>\1.</strong>', s)
    s = re.sub(r'\*\*([^*]+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    return s


# Verse extraction patterns
ENG_STANDALONE_RE = re.compile(r'^\*\*(\d+)\.\*\*\s+(.+?)$', re.M)
# 1timothy 首节 English 通常裸: `1 Paul, an apostle...`（无粗体，无点）
# 用 `[A-Z(“"']` 起首 + 该行不是 CHAPTER 头且不含 h2 tag，保守匹配
ENG_BARE_RE = re.compile(r'^(\d+)\s+([A-Z(“"\'][^\n<]{20,}?)$', re.M)
# 1timothy section 开头常带 partial scripture-box, 首节 English 用 HTML `<strong>N.</strong>`
# 停在下一 `<strong>` 或 `<`(标签) 或行尾, 以支持 4:11-12 那种单行多节混排
HTML_STRONG_RE = re.compile(
    r'<strong>(\d+)\.</strong>\s+([^<]+?)(?=\s*<strong>|\s*<|\n|$)'
)
ENG_INDENT_RE = re.compile(
    r'<p style="margin-left:2em;" markdown="1">\*\*(\d+)\.\*\*\s+([^<]+?)</p>',
)
LATIN_RE = re.compile(
    r'<p style="text-align:right;" markdown="1">(\d+)\.\s+([^<]+?)</p>',
)
# 半改 .calvin-parallel 表格里的双列 pair
PARALLEL_ROW_RE = re.compile(
    r'<tr><td><p><strong>(\d+)\.</strong>\s*([^<]+?)</p></td>'
    r'<td><p>(\d+)\.\s+([^<]+?)</p></td></tr>',
)
# 2thess ch1 (v.7-10 段) 里 calvin-parallel row 出现 smushed:
# `<tr><td><p><strong>N.</strong> Latin_N N+1 English_N+1</p></td><td><p>N+1. Latin_N+1</p></td></tr>`
# 左列: Latin_N + English_N+1 (无点, 首字母大写), 右列: Latin_N+1
PARALLEL_ROW_SMUSHED_RE = re.compile(
    r'<tr><td><p><strong>(\d+)\.</strong>\s*([^<]+?)\s+(\d+)\.?\s+([A-Z(“"\'][^<]+?)</p></td>'
    r'<td><p>(\d+)\.\s+([^<]+?)</p></td></tr>',
)


def extract_verses(section_body: str) -> dict[int, dict]:
    verses: dict[int, dict] = {}

    def add(n, kind, text):
        verses.setdefault(n, {}).setdefault(kind, text.strip())

    # Sources A + C fragments
    for m in ENG_STANDALONE_RE.finditer(section_body):
        body = m.group(2).strip()
        if '<span style="color:#800000">' in body:
            continue  # skip commentary
        add(int(m.group(1)), 'en', body)
    for m in ENG_INDENT_RE.finditer(section_body):
        n = int(m.group(1))
        body = m.group(2)
        # 若同 verse 的 English 已经存在 (来自 SMUSHED_RE 拆分), 且此处又见 `<p margin-left>**N.**`
        # 则该 <p> 是 Latin_N (Ages 尾节 colophon 模式, 如 1thess 5:28 / 2thess 3:18)
        if verses.get(n, {}).get('en'):
            if 'la' not in verses.get(n, {}):
                add(n, 'la', body)
        else:
            add(n, 'en', body)
    for m in LATIN_RE.finditer(section_body):
        add(int(m.group(1)), 'la', m.group(2))
    # 1timothy 首节 English 常为裸格式 `1 Paul, an apostle...`
    for m in ENG_BARE_RE.finditer(section_body):
        n = int(m.group(1))
        # 保守: 只填未出现的节, 避免覆盖 std/indent 已抓的
        if 'en' not in verses.get(n, {}):
            add(n, 'en', m.group(2))
    # 1timothy partial scripture-box 里 `<strong>N.</strong> ...` 序列
    # 单行内同 N 出现两次 = 第一 EN 第二 LA (Ages OLD partial-box 内联 EN|LA 惯例)
    seen_html_strong: set[int] = set()
    for m in HTML_STRONG_RE.finditer(section_body):
        n = int(m.group(1))
        body = m.group(2).strip()
        if not body:
            continue
        if n not in seen_html_strong:
            if 'en' not in verses.get(n, {}):
                add(n, 'en', body)
            seen_html_strong.add(n)
        else:
            if 'la' not in verses.get(n, {}):
                add(n, 'la', body)

    # Source B (smushed): calvin-parallel row 左列 Latin_N + Eng_N+1 混排
    # 必须先 smushed 再普通 (smushed 是普通的超集), 用 group N 匹配的段跳过
    smushed_pos: list[tuple[int, int]] = []
    for m in PARALLEL_ROW_SMUSHED_RE.finditer(section_body):
        n_lat = int(m.group(1))
        latin_body = m.group(2).strip()
        n_eng_next = int(m.group(3))
        eng_body_next = m.group(4).strip()
        n_lat_next = int(m.group(5))
        latin_body_next = m.group(6).strip()
        if n_eng_next == n_lat + 1 and n_lat_next == n_lat + 1:
            add(n_lat, 'la', latin_body)
            add(n_eng_next, 'en', eng_body_next)
            add(n_lat_next, 'la', latin_body_next)
            smushed_pos.append((m.start(), m.end()))

    # Source B: existing .calvin-parallel table rows
    for m in PARALLEL_ROW_RE.finditer(section_body):
        # 跳过已被 smushed 处理的 row (避免误抓 Latin 当 English)
        if any(s <= m.start() < e for s, e in smushed_pos):
            continue
        n_en = int(m.group(1))
        n_la = int(m.group(3))
        if n_en == n_la:
            add(n_en, 'en', m.group(2))
            add(n_en, 'la', m.group(4))

    return verses


def build_scripture_box(cfg, ch: int, v_from: int, v_to: int,
                          verses: dict[int, dict]) -> str:
    ages_code = f'{cfg["book_num"]}{ch:02d}{v_from:02d}'
    verse_range = f'{v_from}' if v_from == v_to else f'{v_from}-{v_to}'
    anchor_id = (f'{cfg["anchor_prefix"]}-{ch}-{v_from}'
                  if v_from == v_to
                  else f'{cfg["anchor_prefix"]}-{ch}-{v_from}-{v_to}')
    data_ref = f'{cfg["upper"]} {ch}:{verse_range}'

    lines = [
        '<div class="scripture-box scripture-box--bilingual" markdown="1">',
        (f'<p class="scripture-ref"><span class="ages-code">&lt;{ages_code}&gt;</span>'
         f'<span class="book-name">{cfg["title"]}</span> '
         f'<span class="verse-range">{ch}:{verse_range}</span></p>'),
        (f'<h2 class="scripture-anchor" id="{anchor_id}" '
         f'data-ref="{data_ref}" style="display:none">{data_ref}</h2>'),
        '',
        '<table class="scripture-bilingual">',
        '<tbody>',
    ]
    for v in range(v_from, v_to + 1):
        d = verses.get(v, {})
        en = md_to_html(d.get('en', f'[MISSING v{v} English]'))
        la = md_to_html(d.get('la', f'[MISSING v{v} Latin]'))
        lines.append(
            f'<tr><td class="scripture-en"><strong>{v}.</strong> {en}</td>'
            f'<td class="scripture-la"><strong>{v}.</strong> {la}</td></tr>'
        )
    lines += ['</tbody>', '</table>', '', '</div>']
    return '\n'.join(lines)


def restructure_file(cfg, path: Path) -> tuple[int, int]:
    text = path.read_text(encoding='utf-8')
    # 匹配三种形态:
    #   (A) 裸标题 (line-anchored): `1 THESSALONIANS 1:1-2` (旧 1thess/2thess raw)
    #   (B) h2 包裹 (line-anchored): `<h2 class="scripture-anchor" ... data-ref="1 TIMOTHY 1:1-4" ...>...</h2>`
    #   (C) 内联 (2thess ch1 有 `[^f6] 2 THESSALONIANS 1:7-10` 尾巴挂在长注释段末尾)
    upper_esc = re.escape(cfg["upper"])
    section_head_re = re.compile(
        rf'(?:^{upper_esc} (\d+):(\d+)(?:-(\d+))?$'
        rf'|^<h2 class="scripture-anchor" id="[^"]+" '
        rf'data-ref="{upper_esc} (\d+):(\d+)(?:-(\d+))?" '
        rf'style="display:none">{upper_esc} \d+:\d+(?:-\d+)?</h2>$'
        rf'|\s{upper_esc} (\d+):(\d+)(?:-(\d+))?\s*$)',
        re.M,
    )

    # Split smushed (source C)
    text, _ = SMUSHED_RE.subn(split_smushed, text)
    # 裸段 bare mega-smushed 预处理: `^N Latin_N. M. English_M ...` (无 <p> 包裹, 无 bold)
    # 1thess 2:13 line 100 case. 包成 <p margin-left>**N.**...</p> 让下游 split 处理.
    text = re.sub(
        r'^(\d+)\s+([A-Z][^<\n]{40,}?)\s+(\d+\.\s+[A-Z][^<\n]+)$',
        lambda m: f'<p style="margin-left:2em;" markdown="1">**{m.group(1)}.** {m.group(2)} {m.group(3)}</p>',
        text, flags=re.M,
    )
    # 再跑一次 SMUSHED_RE 把新包的 bare 也拆
    text, _ = SMUSHED_RE.subn(split_smushed, text)
    # Split mega-smushed (Ages OLD 多节挤同一 <p>):
    # `**N.** Latin_N M. Eng_M M. Lat_M M+1. Eng_M+1 M+1. Lat_M+1 M+2. Eng_M+2 ...`
    text = split_mega_smushed(text)

    raw_heads = list(section_head_re.finditer(text))
    if not raw_heads:
        return 0, 0

    # 解析每 head 为 (head_start, head_end, ch, v_from, v_to)
    parsed = []
    for m in raw_heads:
        if m.group(1):
            ch = int(m.group(1)); v_from = int(m.group(2))
            v_to = int(m.group(3)) if m.group(3) else v_from
        elif m.group(4):
            ch = int(m.group(4)); v_from = int(m.group(5))
            v_to = int(m.group(6)) if m.group(6) else v_from
        else:
            ch = int(m.group(7)); v_from = int(m.group(8))
            v_to = int(m.group(9)) if m.group(9) else v_from
        parsed.append({
            'start': m.start(), 'end': m.end(),
            'ch': ch, 'v_from': v_from, 'v_to': v_to,
        })

    # 不合并 sections — 保留各自 body, 让 v.7 归到出现处对应的 section
    # (1:1-7 + 1:7-10 场景下, v.7 EN/LA 出现在内联 marker 之后, 归 1:7-10;
    #  section 1 会 shrink 到实际含 verse 的最大 v_to 即 1:1-6)
    replacements = []
    n_verses_total = 0

    for i, p in enumerate(parsed):
        head_start = p['start']; head_end = p['end']
        ch = p['ch']; v_from = p['v_from']; v_to = p['v_to']
        next_start = parsed[i + 1]['start'] if i + 1 < len(parsed) else len(text)
        body = text[head_end:next_start]

        # verse_end: 仅取本 section 声明的 [v_from, v_to] 内 verse marker 的最远 end 位置
        verse_end = None
        # LATIN_RE
        for lm in LATIN_RE.finditer(body):
            if v_from <= int(lm.group(1)) <= v_to:
                verse_end = max(verse_end or 0, lm.end())
        # ENG_STANDALONE_RE — 跳过注释段 (`**N.** <span style="color:#800000">*...*`)
        # 否则会把 `**1.** *Pray for us*` 之类的注释头当经文, verse_end 溢到注释区
        for lm in ENG_STANDALONE_RE.finditer(body):
            if v_from <= int(lm.group(1)) <= v_to:
                if '<span style="color:#800000">' in lm.group(2):
                    continue
                verse_end = max(verse_end or 0, lm.end())
        # ENG_INDENT_RE
        for lm in ENG_INDENT_RE.finditer(body):
            if v_from <= int(lm.group(1)) <= v_to:
                verse_end = max(verse_end or 0, lm.end())
        # PARALLEL_ROW_RE / SMUSHED (整表 </tbody></table> 位置, 若表内含 v_from..v_to 的行)
        m_table = re.search(r'<table class="scripture-table calvin-parallel">.*?</tbody>\s*</table>', body, re.S)
        if m_table:
            inside = m_table.group(0)
            has_target = any(
                v_from <= int(mm.group(1)) <= v_to
                for mm in re.finditer(r'<tr><td><p><strong>(\d+)\.', inside)
            ) or any(
                v_from <= int(mm.group(3)) <= v_to
                for mm in re.finditer(
                    r'<tr><td><p><strong>(\d+)\.</strong>\s*[^<]+?\s+(\d+)\.?\s+',
                    inside,
                )
            ) or any(
                v_from <= int(mm.group(1)) <= v_to
                for mm in re.finditer(r'<td><p>(\d+)\.\s', inside)
            )
            if has_target:
                verse_end = max(verse_end or 0, m_table.end())
        if verse_end is None:
            continue

        verse_block = body[:verse_end]
        verses = extract_verses(verse_block)
        if not verses:
            continue

        # shrink v_to 到实际含 en 或 la 的最大节号 (处理 2thess 1:1-7 尾节缺失)
        vs_present = [v for v in range(v_from, v_to + 1) if verses.get(v)]
        if vs_present:
            actual_v_to = max(vs_present)
            if actual_v_to < v_to:
                v_to = actual_v_to

        n_paired = sum(1 for v in range(v_from, v_to + 1)
                        if verses.get(v, {}).get('en') and verses.get(v, {}).get('la'))
        n_verses_total += n_paired

        new_block = build_scripture_box(cfg, ch, v_from, v_to, verses)
        section_start = head_start
        section_end = head_end + verse_end
        # 内联 marker (行中间): 前面段落文本紧挨 marker, 必须补 `\n\n` 避免 div 粘住
        if section_start > 0 and text[section_start - 1] != '\n':
            new_block = '\n\n' + new_block
        replacements.append((section_start, section_end, new_block))

    new_text = text
    for start, end, repl in reversed(replacements):
        new_text = new_text[:start] + repl + new_text[end:]

    path.write_text(new_text, encoding='utf-8')
    return len(replacements), n_verses_total


def main():
    args = sys.argv[1:]
    if not args or args[0] not in BOOKS:
        print(__doc__)
        sys.exit(1)
    book_key = args[0]
    cfg = BOOKS[book_key]
    chapter_args = args[1:]

    if chapter_args:
        files = [cfg['src_dir'] / f'{c}.md' for c in chapter_args]
    else:
        files = sorted(cfg['src_dir'].glob('[0-9]*.md'))

    total_sec = total_v = 0
    for f in files:
        if not f.exists():
            print(f'  {f}: 不存在, 跳过')
            continue
        n_sec, n_v = restructure_file(cfg, f)
        print(f'  {f.name}: {n_sec} sections converted, {n_v} verses paired')
        total_sec += n_sec
        total_v += n_v
    print(f'\nTOTAL: {total_sec} sections, {total_v} verses paired')


if __name__ == '__main__':
    main()
