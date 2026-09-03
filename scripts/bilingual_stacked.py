#!/usr/bin/env python3
"""纵向叠放双语经文 → scripture-box 双语表（markdown 级，供中文版 publish 用）。

英文侧已在 structured_to_md._pair_stacked_bilingual 里从 [TAG] 级配对好；
中文侧的输入是**已翻译的 markdown**（zh_chapters），两边文字都在，只是渲染成

    <h2 class="scripture-anchor" id="obadiah-2-4" data-ref="OBADIAH 2-4" …></h2>
    <p style="margin-left:2em;">2 我使你以东在列国中为最小的…</p>
    <p style="text-align:right;">2 Ecce parvum posui te…（看哪…）</p>
    …

交替散段。skill 02a §11.0 明写这是被反复打回过的反例。本模块把它们配成

    <div class="scripture-box scripture-box--bilingual" markdown="1">
    <p class="scripture-ref">…</p>
    <table class="scripture-bilingual"><tbody>
    <tr><td class="scripture-en">…</td><td class="scripture-la">…</td></tr>
    </tbody></table>
    </div>

`ages-code` 与 `book-name` **从对应英文页同 id 的 box 里取**，不自己拼——
中文页的 anchor 里没有 AGES 六位码，凭书名猜等于编造。取不到就不带 code。

幂等：已经是 box 的段落不动（正则只匹配散段形态）。
"""
import re

# ⚠️ id 不一定在 <h2> 上：中文版 publish 的 relocate_anchors_in_body
# 会把 id 从 <h2 class="scripture-anchor"> 挪到紧随的
# <div class="commentary-anchor" id="…">（07-verse-index §1 的硬要求）。
# 所以 h2 只取 data-ref，id 另从同块里的 commentary-anchor 找。
ANCHOR_RE = re.compile(
    r'<h2 class="scripture-anchor"[^>]*\bdata-ref="([^"]*)"[^>]*>(.*?)</h2>')
CMT_ANCHOR_RE = re.compile(r'<div class="commentary-anchor" id="([^"]+)"></div>')
LEFT_P_RE = re.compile(
    r'^<p style="margin-left:2em;"[^>]*>\s*(\d{1,3})\.?\s+(.*?)</p>\s*$', re.S)
RIGHT_P_RE = re.compile(
    r'^<p style="text-align:\s*right;?"[^>]*>\s*(\d{1,3})\.?\s+(.*?)</p>\s*$', re.S)


def en_box_meta(en_text):
    """→ {anchor_id: (ages_code_html, book_name)}，从英文页的 box 里取。"""
    meta = {}
    for m in re.finditer(
            r'<h2 class="scripture-anchor"[^>]*\bid="([^"]+)"[^>]*>.*?</h2>\s*'
            r'<div class="scripture-box[^"]*"[^>]*>\s*'
            r'<p class="scripture-ref">(.*?)</p>', en_text, re.S):
        aid, ref = m.group(1), m.group(2)
        code = re.search(r'<span class="ages-code">(.*?)</span>', ref)
        book = re.search(r'<span class="book-name">(.*?)</span>', ref)
        meta[aid] = (code.group(1) if code else None,
                     book.group(1) if book else None)
    return meta


def pair_markdown(text, en_text=None, book_cn=None):
    """把散段形态的双语经文配成 box。→ (新文本, 改写的块数)"""
    meta = en_box_meta(en_text) if en_text else {}
    blocks = text.split('\n\n')
    out, i, fixed = [], 0, 0
    while i < len(blocks):
        b = blocks[i]
        am = ANCHOR_RE.search(b)
        if not am:
            out.append(b); i += 1; continue
        out.append(b)
        # 往后收连续的「左段 / 右段」散段
        left, right, order, j = {}, {}, [], i + 1
        while j < len(blocks):
            seg = blocks[j].strip()
            if not seg:
                j += 1; continue
            lm, rm = LEFT_P_RE.match(seg), RIGHT_P_RE.match(seg)
            if lm:
                if lm.group(1) in left:
                    break
                left[lm.group(1)] = lm.group(2).strip(); order.append(lm.group(1))
            elif rm:
                if rm.group(1) in right:
                    break
                right[rm.group(1)] = rm.group(2).strip()
            else:
                break
            j += 1
        if not (left and right and (set(left) & set(right))):
            i += 1; continue
        # 组装 box
        cm = CMT_ANCHOR_RE.search(b)
        aid = cm.group(1) if cm else ''
        code, book = meta.get(aid, (None, None))
        rng = am.group(1)
        rng = re.sub(r'^[A-Za-z0-9\s]*?(?=\d)', '', rng).strip() or rng
        # 书名优先取 h2 自己的文字（中文页写的就是「俄巴底亚书 2-4」），
        # 英文页那份只作兜底——从英文页取会在中文页上印出 "Obadiah"。
        h2_name = re.sub(r'[\d\s:：\-–,，]+$', '', am.group(2)).strip()
        name = h2_name or book_cn or book or ''
        ref_parts = []
        if code:
            ref_parts.append(f'<span class="ages-code">{code}</span>')
        if name:
            ref_parts.append(f'<span class="book-name">{name}</span> ')
        ref_parts.append(f'<span class="verse-range">{rng}</span>')
        rows = []
        for n in sorted(set(left) | set(right), key=int):
            en = f'<strong>{n}.</strong> ' + left.get(n, '') if left.get(n) else ''
            la = f'<strong>{n}.</strong> ' + right.get(n, '') if right.get(n) else ''
            rows.append(f'<tr><td class="scripture-en">{en}</td>'
                        f'<td class="scripture-la">{la}</td></tr>')
        out.append('<div class="scripture-box scripture-box--bilingual" markdown="1">\n'
                   f'<p class="scripture-ref">{"".join(ref_parts)}</p>\n\n'
                   '<table class="scripture-bilingual">\n<tbody>\n'
                   + '\n'.join(rows)
                   + '\n</tbody>\n</table>\n\n</div>')
        fixed += 1
        i = j
    return '\n\n'.join(out), fixed


# ── 形态二：单列 box + box 外的拉丁散段 ────────────────────────────
# 以赛亚书两卷（958 处，占中文侧散段的 82%）与摩西五经合参都是这个形状：
#     <div class="scripture-box" markdown="1">
#     <p class="scripture-ref">…</p>
#     <strong>1.</strong> 当乌西雅…作犹大王的时候…      ← 只有中文
#     </div>
#     <p style="text-align:right;">1. Visio Isaiae filii Amoz…（…）</p>  ← 拉丁在框外
# 把框外的拉丁按节号并进框内，并把单列 box 升级成双语表。
BOX_RE = re.compile(
    r'<div class="scripture-box"(?![^>]*bilingual)[^>]*>(.*?)</div>', re.S)
INNER_VERSE_RE = re.compile(
    r'<strong>\s*(\d{1,3})\s*\.?\s*</strong>\s*(.*?)(?=(?:<strong>\s*\d{1,3})|\Z)', re.S)


def pair_box_with_stray_latin(text):
    """→ (新文本, 改写的 box 数)

    ⚠️ 不能按 `split('\\n\\n')` 的块来找 box：box 内部本来就有空行
    （ref 段与经文段之间），一切就把 `<div>`、经文、`</div>` 切到三个块里，
    正则匹配不到（第一版踩过，0 命中）。所以在全文上 finditer 定位 box 区间，
    再看紧随其后的右对齐散段。
    """
    out, pos, fixed = [], 0, 0
    for bm in BOX_RE.finditer(text):
        if 'scripture-bilingual' in bm.group(0):
            continue
        inner = bm.group(1)
        verses = [(n, t.strip()) for n, t in INNER_VERSE_RE.findall(inner)]
        if not verses:
            continue
        # 框后连续的右对齐拉丁散段（允许空行相隔）
        tail = text[bm.end():]
        la, consumed = {}, 0
        for pm in re.finditer(r'\A\s*<p style="text-align:\s*right;?"[^>]*>'
                              r'\s*(\d{1,3})\.?\s+(.*?)</p>', tail, re.S):
            pass
        while True:
            pm = re.match(r'\s*<p style="text-align:\s*right;?"[^>]*>'
                          r'\s*(\d{1,3})\.?\s+(.*?)</p>', tail[consumed:], re.S)
            if not pm or pm.group(1) in la:
                break
            la[pm.group(1)] = pm.group(2).strip()
            consumed += pm.end()
        if not la or not (set(n for n, _ in verses) & set(la)):
            continue
        ref = re.search(r'<p class="scripture-ref">.*?</p>', inner, re.S)
        vmap = dict(verses)
        rows = []
        for n in sorted(set(vmap) | set(la), key=int):
            en = f'<strong>{n}.</strong> ' + vmap[n] if vmap.get(n) else ''
            lat = f'<strong>{n}.</strong> ' + la[n] if la.get(n) else ''
            rows.append(f'<tr><td class="scripture-en">{en}</td>'
                        f'<td class="scripture-la">{lat}</td></tr>')
        out.append(text[pos:bm.start()])
        out.append('<div class="scripture-box scripture-box--bilingual" markdown="1">\n'
                   + (ref.group(0) + '\n\n' if ref else '')
                   + '<table class="scripture-bilingual">\n<tbody>\n'
                   + '\n'.join(rows)
                   + '\n</tbody>\n</table>\n\n</div>')
        pos = bm.end() + consumed
        fixed += 1
    out.append(text[pos:])
    return ''.join(out), fixed
