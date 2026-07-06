#!/usr/bin/env python3
"""
publish_titus_zh.py — 将 titus 已翻译的中文章节发布到 calvin/titus/

输入：calvin_raw/titus/zh_chapters/<N>.md  (preface, 1..5)
输出：calvin/titus/<N>.md         (覆盖旧版 CCEL 译本)
      calvin/titus/index.html     (calvin-book-modern, chapters=已译数)

样式对齐 acts-filibi 中文发布流程：
- layout: calvin-en
- book_id: titus
- book_name: 提多书·加尔文注释
- 内联 relocate_anchors_in_body + add_verse_anchors_in_body
  让 verse-index 胶囊跳到注释段开头（不是经文块）

用法（项目根目录）：
    python3 scripts/publish_titus_zh.py
"""
import json
import re
import subprocess
from pathlib import Path

SRC_DIR = Path('calvin_raw/titus/zh_chapters')
OUT_DIR = Path('calvin/titus')

BOOK_ID   = 'titus'
BOOK_NAME = '提多书·加尔文注释'

# ── 和合本经文查找（左列英文换中文，右列保留拉丁文）──
_BIBLE_PATH = Path(__file__).parent / 'zh_cuv.json'
_bible = json.load(open(_BIBLE_PATH, encoding='utf-8-sig'))
_titus_chapters = next(b for b in _bible if b['abbrev'] == 'tt')['chapters']

# zh_cuv.json 是繁体 + 字符间空格，转简体 + 去空格
import opencc as _opencc
_t2s = _opencc.OpenCC('t2s')


def lookup_cuv(ch: int, v: int):
    if ch - 1 >= len(_titus_chapters):
        return None
    chapter = _titus_chapters[ch - 1]
    if v - 1 >= len(chapter) or v < 1:
        return None
    return _t2s.convert(chapter[v - 1].replace(' ', ''))


# match 整个 scripture-box bilingual 块
_BOX_RE = re.compile(
    r'(<div class="scripture-box scripture-box--bilingual"[^>]*>\s*'
    r'<p class="scripture-ref">.*?<span class="verse-range">(\d+):\d+(?:-\d+)?</span></p>\s*'
    r'(?:<h2 class="scripture-anchor"[^>]*>[^<]+</h2>\s*)?'  # 可选 scripture-anchor h2
    r'<table class="scripture-bilingual">.*?</table>)',
    re.DOTALL,
)

_TR_RE = re.compile(
    r'<tr><td class="scripture-en">.*?<strong>(\d+)\.</strong>.*?</td>'
    r'(<td class="scripture-la">.*?</td>)</tr>',
    re.DOTALL,
)


def _fnref_to_sup(text: str) -> str:
    """[^fN] / [^N] → <sup id="fnref:fN"><a href="#fn:fN" class="footnote">fN</a></sup>
    (per skill 02a §11.2 — <td> 内 kramdown 不处理 markdown, 必须手工转)"""
    return re.sub(
        r'\[\^([Ff]?\d+[A-Za-z]?)\]',
        r'<sup id="fnref:\1"><a href="#fn:\1" class="footnote">\1</a></sup>',
        text,
    )


def inject_chinese_scripture(body: str) -> str:
    """把 bilingual scripture-box 左列的英文替换为和合本中文；
    Latin 列 [^fN] 转 HTML <sup>；box 末追加 scripture-fnref-stub 占位。"""
    def process_box(m_box):
        full = m_box.group(1)
        ch = int(m_box.group(2))
        # 收集本 box 内所有出现过的 fn 编号（保序去重）
        seen_refs = []
        for ref in re.findall(r'\[\^([Ff]?\d+[A-Za-z]?)\]', full):
            if ref not in seen_refs:
                seen_refs.append(ref)

        def replace_tr(tr_m):
            n_str = tr_m.group(1)
            la_td = tr_m.group(2)
            # Latin 列的 [^fN] 转 <sup>
            la_td = _fnref_to_sup(la_td)
            zh = lookup_cuv(ch, int(n_str))
            if not zh:
                # 无 CUV 匹配时至少也修 la_td 的 fn refs
                # 重构 tr, en 保留原 en 内容(先转 fn ref)
                en_body_m = re.search(r'<td class="scripture-en">(.*?)</td>', tr_m.group(0), re.S)
                en_body = _fnref_to_sup(en_body_m.group(1)) if en_body_m else ''
                return (f'<tr><td class="scripture-en">{en_body}</td>{la_td}</tr>')
            return (f'<tr><td class="scripture-en"><strong>{n_str}.</strong> {zh}</td>'
                    f'{la_td}</tr>')

        new_full = _TR_RE.sub(replace_tr, full)

        # 在 </div> 前 emit scripture-fnref-stub 让 kramdown 生成 <li id="fn:fN">
        if seen_refs:
            stub_refs = ' '.join(f'[^{r}]' for r in seen_refs)
            stub = (f'\n\n<p class="scripture-fnref-stub" style="display:none" '
                    f'markdown="1">{stub_refs}</p>')
            new_full = new_full.rstrip()
            if new_full.endswith('</div>'):
                new_full = new_full[:-len('</div>')].rstrip() + stub + '\n\n</div>'
            else:
                new_full = new_full + stub
        return new_full

    return _BOX_RE.sub(process_box, body)

CN_NUM = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
          '十一', '十二', '十三', '十四', '十五', '十六']


def cn_chapter(n) -> str:
    if n == 'preface':
        return '前言'
    return f'第{CN_NUM[n]}章'


def get_date() -> str:
    return subprocess.check_output(['date', '+%Y-%m-%d %H:%M']).decode().strip()


def strip_frontmatter(text: str) -> str:
    if not text.startswith('---'):
        return text
    m = re.match(r'^---\n.*?\n---\n', text, re.DOTALL)
    return text[m.end():] if m else text


def clean_body(body: str) -> str:
    """移除翻译残留的 <<<END>>>；剥 scripture-anchor 上 inline display:none。"""
    lines = body.split('\n')
    cleaned = [l for l in lines if l.strip() != '<<<END>>>']
    body = '\n'.join(cleaned)
    body = re.sub(
        r'(<h2 class="scripture-anchor"[^>]*?) style="display:none"(>)',
        r'\1\2',
        body,
    )
    return body


def build_frontmatter(n, total: int, date: str, has_preface: bool) -> str:
    fm  = '---\n'
    fm += 'layout: calvin-en\n'
    fm += f'book_id: {BOOK_ID}\n'
    fm += f'book_name: "{BOOK_NAME}"\n'
    fm += f'title: "{cn_chapter(n)}"\n'
    fm += f'date: {date}\n'
    if n == 'preface':
        fm += 'next_section: 1\n'
        fm += 'next_label: "第一章"\n'
    else:
        if n > 1:
            fm += f'prev_section: {n - 1}\n'
            fm += f'prev_label: "{cn_chapter(n - 1)}"\n'
        elif has_preface:
            fm += 'prev_section: preface\n'
            fm += 'prev_label: "前言"\n'
        if n < total:
            fm += f'next_section: {n + 1}\n'
            fm += f'next_label: "{cn_chapter(n + 1)}"\n'
    fm += '---\n\n'
    return fm


VERSE_MARK_RE = re.compile(r'^\*\*(\d{1,3})\.\*\*[\s<]')


def add_verse_anchors_in_body(body: str, ch) -> str:
    """每个 `**N.**` 注释段前插入 per-verse commentary-anchor。
    跳过 scripture-box（经文本身用 <strong>N.</strong> HTML，不会被 VERSE_MARK_RE 命中）。
    """
    if not isinstance(ch, int):
        return body  # preface 不加 per-verse anchor
    lines = body.split('\n')
    out = []
    in_box = False
    seen: dict[int, int] = {}
    for raw in lines:
        s = raw.strip()
        if s.startswith('<div class="scripture-box"'):
            in_box = True
            out.append(raw)
            continue
        if in_box:
            if s == '</div>':
                in_box = False
            out.append(raw)
            continue
        m = VERSE_MARK_RE.match(raw)
        if m:
            v = int(m.group(1))
            seen[v] = seen.get(v, 0) + 1
            suffix = '' if seen[v] == 1 else f'-{seen[v]}'
            out.append(f'<div class="commentary-anchor" id="{BOOK_ID}-{ch}-{v}{suffix}"></div>')
        out.append(raw)
    return '\n'.join(out)


def relocate_anchors_in_body(body: str) -> str:
    """把 scripture-anchor h2 上的 id 挪到经文块后的 commentary-anchor div。
    旧 1timothy 用 id="1-corinthians-1-1-3" 风格（kebab）；保持。"""
    h2_re = re.compile(
        r'^(<h2 class="scripture-anchor")\s+id="([^"]+)"(.*?)>(.*)$'
    )
    lines = body.split('\n')
    out: list[str] = []
    i = 0
    while i < len(lines):
        m = h2_re.match(lines[i])
        if not m:
            out.append(lines[i])
            i += 1
            continue
        pre, aid, post_attrs, h2_tail = m.groups()
        new_h2 = f'{pre}{post_attrs}>{h2_tail}'
        anchor = f'<div class="commentary-anchor" id="{aid}"></div>'

        j = i + 1
        while j < len(lines) and lines[j].strip() == '':
            j += 1
        if j < len(lines) and lines[j].lstrip().startswith('<div class="scripture-box"'):
            k = j + 1
            depth = 1
            while k < len(lines) and depth > 0:
                depth += lines[k].count('<div') - lines[k].count('</div>')
                if depth == 0:
                    break
                k += 1
            if k >= len(lines):
                out.append(lines[i])
                i += 1
                continue
            out.append(new_h2)
            out.extend(lines[i + 1:k + 1])
            out.append(anchor)
            i = k + 1
        else:
            out.append(new_h2)
            out.append(anchor)
            i += 1
    return '\n'.join(out)


def main():
    chapters = sorted(int(p.stem) for p in SRC_DIR.glob('*.md') if p.stem.isdigit())
    has_preface = (SRC_DIR / 'preface.md').exists()
    if not chapters and not has_preface:
        print(f'错误：{SRC_DIR} 下没有可发布章节')
        return
    if chapters and chapters != list(range(1, len(chapters) + 1)):
        print(f'警告：章节非连续 {chapters}')

    total = max(chapters) if chapters else 0
    items = (['preface'] if has_preface else []) + chapters
    print(f'发现已译：preface={has_preface}, chapters={chapters} (共 {total} 章)', flush=True)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date = get_date()

    for n in items:
        src = SRC_DIR / f'{n}.md'
        raw = src.read_text(encoding='utf-8')
        body = strip_frontmatter(raw)
        body = clean_body(body)
        # Claude 有时把 <strong>N.</strong> 翻译回 markdown **N.** —
        # 在 inject_chinese_scripture 前修回 HTML, 否则 _TR_RE 抓不到
        body = re.sub(
            r'(<td class="scripture-en">)\s*\*\*(\d+)\.\*\*',
            r'\1<strong>\2.</strong>',
            body,
        )
        body = inject_chinese_scripture(body)
        body = relocate_anchors_in_body(body)
        if isinstance(n, int):
            body = add_verse_anchors_in_body(body, n)
        body_lines = body.lstrip('\n').split('\n')
        if body_lines and re.match(r'^#\s+(?:第.+?章|前言|Preface)\s*$', body_lines[0]):
            body_lines.pop(0)
            while body_lines and not body_lines[0].strip():
                body_lines.pop(0)
        body = '\n'.join(body_lines)

        fm = build_frontmatter(n, total, date, has_preface)
        content = fm + body.rstrip() + '\n'

        out = OUT_DIR / f'{n}.md'
        out.write_text(content, encoding='utf-8')
        print(f'  写入 {out}  ({out.stat().st_size:,} bytes)', flush=True)

    idx = OUT_DIR / 'index.html'
    idx_content = (
        '---\n'
        'layout: calvin-book-modern\n'
        f'book_id: {BOOK_ID}\n'
        'book_name: 提多书\n'
        f'chapters: {total}\n'
    )
    if has_preface:
        idx_content += 'has_preface: true\n'
    idx_content += '---\n'
    idx.write_text(idx_content, encoding='utf-8')
    print(f'  写入 {idx}', flush=True)

    print(f'\n✓ 发布完成 → {OUT_DIR}/ (chapters={total})')


if __name__ == '__main__':
    main()
