#!/usr/bin/env python3
"""manton_raw/james/*.md → manton/james/（英文版发布）

托马斯·曼顿《雅各书注释》。raw 由 scripts/extract_manton_james.py 从 CCEL
EPUB 提取，底本信息见该脚本 docstring。

产出
----
    manton/james/index.html          目录页（layout: manton-book）
    manton/james/dedicatory/index.md 献辞
    manton/james/advertisement/index.md 致读者
    manton/james/preface/index.md    全书序论
    manton/james/1..5/index.md       正文五章

经节锚点（step 07 verse-index 的输入）
------------------------------------
raw 里每个释经单元以 `<!--VERSE N-->` 打头（N 可以是 `2` / `2-4` / `3, 4`）。
发布时：

  1. 单元首段（`VER. N. *经文*`）渲染成 `<p class="manton-ver">`
  2. **紧接其后**插 per-verse 锚点 `<div class="commentary-anchor" id="james-CH-V">`

锚点落在经文之后、释经正文之前 —— step 07 §1 的硬要求：落在经文之前
用户点胶囊只看得到经文看不到注释，算没做对。范围单元（`2-4`）按
step 07 §4 展开成逐节锚点，每节一个胶囊，不留范围锚点。

用法
----
    python3 scripts/publish_manton_james.py
"""
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'manton_raw' / 'james'
OUT = ROOT / 'manton' / 'james'

BOOK_ID = 'james'
BOOK_NAME = 'Manton on the Epistle of James'
AUTHOR = 'Thomas Manton'

ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V'}

# (raw 名, 路径段, 页面标题, 导航 label)
FRONT = [
    ('dedicatory',    'dedicatory',    'The Epistle Dedicatory',        'Dedicatory'),
    ('advertisement', 'advertisement', 'An Advertisement to the Reader', 'Advertisement'),
    ('preface',       'preface',       'A Preface to the Whole Epistle', 'Preface'),
]
CHAPTERS = [1, 2, 3, 4, 5]

VERSE_MARK_RE = re.compile(r'^<!--VERSE\s+(.+?)-->$')


def parse_verse_spec(spec):
    """`2` / `2-4` / `3, 4` / `15-16` → 逐节整数列表。

    step 07 §4：范围单元必须展开成逐节锚点，否则点第 4 节的胶囊会落到
    第 2 节。曼顿的单元跨度很小（最多 3 节），展开后每节都指向该单元
    开头 —— 那正是这几节释经真正开始的地方。
    """
    out = []
    for part in re.split(r'[,\s]+', spec.strip()):
        part = part.strip(' .')
        if not part:
            continue
        m = re.fullmatch(r'(\d+)[–-](\d+)', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            out.extend(range(a, b + 1))
        elif part.isdigit():
            out.append(int(part))
    # 去重保序
    seen, uniq = set(), []
    for v in out:
        if v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def split_footnotes(text):
    """正文与脚注定义区分离。raw 里用 `\\n---\\n` 分隔。"""
    m = re.search(r'\n---\n\n(\[\^f\d+\]: )', text)
    if not m:
        return text.rstrip(), ''
    return text[:m.start()].rstrip(), text[m.start():].lstrip('\n')


def transform_body(body, ch):
    """raw 正文 → 发布正文。插经节锚点、包装 VER 段。"""
    blocks = body.split('\n\n')
    out = []
    i = 0
    n_anchor = 0
    while i < len(blocks):
        b = blocks[i].strip()
        if not b:
            i += 1
            continue
        m = VERSE_MARK_RE.match(b)
        if m and i + 1 < len(blocks):
            spec = m.group(1)
            # `center` 标志：雅 1:1 题辞在原书是居中排的（extract 里说明），
            # 版式照原书走，不与其余节头强行统一（principles §0.0 反向约束）
            centered = 'center' in spec
            verses = parse_verse_spec(spec)
            head = blocks[i + 1].strip()
            # 单元首段就是「VER. N. *经文*」，渲染成经文头
            # markdown="1" 必须带：里面有 *斜体*，kramdown 不解析
            # 无属性 HTML 块内的 markdown（Gate 5b）
            cls = 'manton-ver manton-ver--center' if centered else 'manton-ver'
            out.append(f'<p class="{cls}" markdown="1">{head}</p>')
            # 锚点紧跟经文之后 = 释经正文起点（step 07 §1）
            for v in verses:
                out.append(f'<div class="commentary-anchor" id="{BOOK_ID}-{ch}-{v}"></div>')
                n_anchor += 1
            i += 2
            continue
        out.append(b)
        i += 1
    return '\n\n'.join(out), n_anchor


def front_matter(**kw):
    lines = ['---']
    for k, v in kw.items():
        if v is None:
            continue
        if isinstance(v, str) and (':' in v or v.startswith(' ')):
            lines.append(f'{k}: "{v}"')
        else:
            lines.append(f'{k}: {v}')
    lines.append('---')
    return '\n'.join(lines) + '\n'


def main():
    if not RAW.exists():
        sys.exit(f'找不到 raw：{RAW}，先跑 scripts/extract_manton_james.py')
    OUT.mkdir(parents=True, exist_ok=True)

    # CLAUDE.md：date 必须是真实当前时间，精确到分钟
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # 全书页面顺序，用来算 prev/next
    seq = [(seg, label) for _, seg, _, label in FRONT]
    seq += [(str(c), f'Chapter {ROMAN[c]}') for c in CHAPTERS]

    total_anchors = 0

    def nav(idx):
        prev = seq[idx - 1] if idx > 0 else None
        nxt = seq[idx + 1] if idx + 1 < len(seq) else None
        return prev, nxt

    # ── 前置三篇 ─────────────────────────────────────────────
    for pos, (raw_name, seg, title, label) in enumerate(FRONT):
        text = (RAW / f'{raw_name}.md').read_text(encoding='utf-8')
        body, fns = split_footnotes(text)
        body, _ = transform_body(body, 0)
        prev, nxt = nav(pos)
        fm = front_matter(
            layout='manton-chapter', book_id=BOOK_ID, book_name=BOOK_NAME,
            author=AUTHOR, section=seg, title=title, date=now,
            prev_url=f'/manton/james/{prev[0]}/' if prev else None,
            prev_label=prev[1] if prev else None,
            next_url=f'/manton/james/{nxt[0]}/' if nxt else None,
            next_label=nxt[1] if nxt else None,
        )
        d = OUT / seg
        d.mkdir(parents=True, exist_ok=True)
        content = fm + '\n' + f'# {title}\n\n' + body + ('\n\n' + fns if fns else '') + '\n'
        (d / 'index.md').write_text(content, encoding='utf-8')
        print(f'{seg:14s} {len(content):8,d} chars')

    # ── 正文五章 ─────────────────────────────────────────────
    for pos, ch in enumerate(CHAPTERS, start=len(FRONT)):
        text = (RAW / f'{ch}.md').read_text(encoding='utf-8')
        body, fns = split_footnotes(text)
        # raw 首部的 h1/h2（AN EXPOSITION WITH NOTES / CHAPTER I）由页面
        # 标题接管，去掉避免正文里出现重复大标题
        body = re.sub(r'^(#{1,4} .*\n\n)+', '', body)
        body, n_anchor = transform_body(body, ch)
        total_anchors += n_anchor
        prev, nxt = nav(pos)
        title = f'Chapter {ROMAN[ch]}'
        fm = front_matter(
            layout='manton-chapter', book_id=BOOK_ID, book_name=BOOK_NAME,
            author=AUTHOR, chapter=ch, title=title, date=now,
            prev_url=f'/manton/james/{prev[0]}/' if prev else None,
            prev_label=prev[1] if prev else None,
            next_url=f'/manton/james/{nxt[0]}/' if nxt else None,
            next_label=nxt[1] if nxt else None,
        )
        d = OUT / str(ch)
        d.mkdir(parents=True, exist_ok=True)
        content = (fm + '\n' + f'# The Epistle of James — {title}\n\n'
                   + body + ('\n\n' + fns if fns else '') + '\n')
        (d / 'index.md').write_text(content, encoding='utf-8')
        print(f'ch{ch:<12} {len(content):8,d} chars  anchors={n_anchor}')

    # ── 目录页 ───────────────────────────────────────────────
    (OUT / 'index.html').write_text(
        front_matter(
            layout='manton-book', book_id=BOOK_ID, book_name=BOOK_NAME,
            author=AUTHOR, title='Manton on James', chapters=len(CHAPTERS),
            has_preface='true', date=now,
        ), encoding='utf-8')

    print(f'\n共 {total_anchors} 个经节锚点 → {OUT}')


if __name__ == '__main__':
    main()
