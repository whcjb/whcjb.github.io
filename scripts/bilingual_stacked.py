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
# 节号形态在同一本书里都能变出好几种，正则必须一次收全：
#   `2 我使你…`        裸数字 + 空格
#   `**20.** 在迦南人…`  粗体节号（中文侧常见）
#   `19..Et possidebunt` 两个点、且点后**没有空格**（俄巴底亚 v.19，
#                        原先要求 `\s+` 于是整组漏掉，用户第二次指出）
_VNUM = r'(?:\*\*)?\s*(\d{1,3})\s*\.*\s*(?:\*\*)?\s*'
LEFT_P_RE = re.compile(
    r'^<p style="margin-left:2em;"[^>]*>\s*' + _VNUM + r'(.*?)</p>\s*$', re.S)
RIGHT_P_RE = re.compile(
    r'^<p style="text-align:\s*right;?"[^>]*>\s*' + _VNUM + r'(.*?)</p>\s*$', re.S)
# box 与散段之间可能夹着 verse-anchor 的 div，收集时要跳过
SKIP_BETWEEN_RE = re.compile(r'^\s*<div class="commentary-anchor"[^>]*></div>\s*$')


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
# 也要匹配**已经是双语**的 box：修完前几节后，后面若还跟着散段
# （俄巴底亚 v.12-14：box 里只有 v12，v13/v14 还在框外），
# 得能往已有表里追加行。原先 `(?![^>]*bilingual)` 把它们排除了。
BOX_RE = re.compile(r'<div class="scripture-box[^"]*"[^>]*>(.*?)</div>', re.S)
# 节号在 box 内有两种写法：HTML `<strong>5.</strong>` 与 markdown `**5.**`。
# 原先只认前者，于是「中文 + 拉丁都用 `**5.**`」的单列 box 整块被丢掉
# （俄巴底亚 box#2，325 字符，靠字符多重集校验抓到）。
INNER_VERSE_RE = re.compile(
    r'(?:<strong>|\*\*)\s*(\d{1,3})\s*\.?\s*(?:</strong>|\*\*)\s*'
    r'(.*?)(?=(?:<strong>|\*\*)\s*\d{1,3}\s*\.?\s*(?:</strong>|\*\*)|\Z)', re.S)


def pair_box_with_stray_latin(text):
    """→ (新文本, 改写的 box 数)

    ⚠️ 不能按 `split('\\n\\n')` 的块来找 box：box 内部本来就有空行
    （ref 段与经文段之间），一切就把 `<div>`、经文、`</div>` 切到三个块里，
    正则匹配不到（第一版踩过，0 命中）。所以在全文上 finditer 定位 box 区间，
    再看紧随其后的右对齐散段。
    """
    out, pos, fixed = [], 0, 0
    for bm in BOX_RE.finditer(text):
        inner = bm.group(1)
        # 已双语：从现有 <tr> 里读回各节，后面收到的散段追加进去
        existing = {}
        for tr in re.findall(r'<tr>(.*?)</tr>', inner, re.S):
            cs = {k: v for k, v in re.findall(
                r'<td class="scripture-(en|la)">(.*?)</td>', tr, re.S)}
            num = None
            for side in ('en', 'la'):
                m2 = re.search(r'<strong>\s*(\d{1,3})\s*\.?\s*</strong>', cs.get(side, ''))
                if m2:
                    num = m2.group(1); break
            if num:
                strip_n = lambda x: re.sub(
                    r'^\s*<strong>\s*\d{1,3}\s*\.?\s*</strong>\s*', '', x).strip()
                existing[num] = (strip_n(cs.get('en', '')), strip_n(cs.get('la', '')))
        verses = [(n, t.strip()) for n, t in INNER_VERSE_RE.findall(inner)
                  if '<td' not in t]
        if existing:
            verses = [(n, v[0]) for n, v in existing.items()]
        if not verses:
            continue
        # 框后连续的右对齐拉丁散段（允许空行相隔）
        tail = text[bm.end():]
        la, extra_en, consumed = {}, {}, 0
        while True:
            rest = tail[consumed:]
            # 跳过空行与夹在中间的 verse-anchor div
            sk = re.match(r'\s*<div class="commentary-anchor"[^>]*></div>', rest)
            if sk:
                consumed += sk.end(); continue
            pm = re.match(r'\s*<p style="text-align:\s*right;?"[^>]*>\s*'
                          + _VNUM + r'(.*?)</p>', rest, re.S)
            if pm and pm.group(1) not in la:
                la[pm.group(1)] = pm.group(2).strip()
                consumed += pm.end(); continue
            # 框外还可能有该节的**中文/英文**段（俄巴底亚 v.20 就在框外）
            lm = re.match(r'\s*<p style="margin-left:2em;"[^>]*>\s*'
                          + _VNUM + r'(.*?)</p>', rest, re.S)
            if lm:
                num, body = lm.group(1), lm.group(2).strip()
                # 段内可能还接着**下一节**的正文（俄巴底亚 v.10-11：一段里
                # 混着 v10 拉丁 +（括注中译）+ v11 中文）。在下一个节号处切开。
                nxt = re.search(r'(?:(?<=\s)|(?<=）)|(?<=\)))(\d{1,3})\.\s*(?=\S)', body)
                trail_num, trail = (nxt.group(1), body[nxt.end():].strip()) if nxt else (None, '')
                if nxt:
                    body = body[:nxt.start()].strip()
                if num in dict(verses):
                    # box 里已有该节的**正文**，那这一段就是该节的**拉丁**
                    if num not in la:
                        la[num] = body
                elif num not in extra_en:
                    extra_en[num] = body
                if trail_num and trail_num not in extra_en and trail_num not in dict(verses):
                    extra_en[trail_num] = trail
                consumed += lm.end(); continue
            break
        if not la or not ((set(n for n, _ in verses) | set(extra_en)) & set(la)):
            continue
        ref = re.search(r'<p class="scripture-ref">.*?</p>', inner, re.S)
        vmap = dict(verses)
        vmap.update(extra_en)
        for n, (e, l) in existing.items():      # 已有表里的拉丁不能丢
            if l and n not in la:
                la[n] = l
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


# ── 形态无关的重建器（取代上面按形态枚举的两个函数）─────────────────
# 逐形态打补丁走不通：同一批书里已经数出 6 种形状（散段交替 / 单列box+框外拉丁 /
# 已双语box+框外余节 / 一段里混着甲节拉丁+乙节正文 / `19..Et` 双点无空格 /
# `## 哈该书 1:5、6` 裸标题+裸 `**N.**` 段），每修一种用户就发现下一种。
# 所以改成：**只认「经文段起点」+「带节号的块」，不认形状**。
#
#   起点 = scripture-box / scripture-anchor h2 / `## <书名> <ref>` 裸标题
#   之后贪婪收集所有含行首节号的块，直到遇到不含的
#   左右列判定按样式：margin-left / 裸段 = 正文列；text-align:right|center = 拉丁列
#   同一节若正文列已有值，再来的同号项归拉丁列（框里已有正文的情形）
#   块内若还接着下一节的节号，就地切开分流
SEC_START_RE = re.compile(
    r'(?:<div class="scripture-box[^"]*"[^>]*>)'
    r'|(?:<h2 class="scripture-anchor"[^>]*>)'
    r'|(?:^##\s+\S+\s+[\d:：]+.*$)', re.M)
ANY_VERSE_RE = re.compile(
    r'^(?:<p style="(?P<style>[^"]*)"[^>]*>)?\s*(?:\*\*)?\s*(?P<num>\d{1,3})'
    r'\s*\.*\s*(?:\*\*)?\s*(?P<body>.*?)(?:</p>)?\s*$', re.S)
NEXT_VERSE_RE = re.compile(r'(?:(?<=\s)|(?<=）)|(?<=\)))(\d{1,3})\.\s*(?=\S)')


def _unbox(text):
    """把已有 box 拆回「ref + 逐节纯文本项」，让所有形态归一。

    先拆再重建，是为了不必枚举形状：box 内的节、框外的散段、已双语的表，
    拆完以后都是同一种「节号 + 文字」的项，收集器只认这个。
    """
    def rep(m):
        inner = m.group(1)
        ref = re.search(r'<p class="scripture-ref">.*?</p>', inner, re.S)
        items = []
        # 已双语：从 <tr> 拆
        trs = re.findall(r'<tr>(.*?)</tr>', inner, re.S)
        if trs:
            for tr in trs:
                cs = {k: v for k, v in re.findall(
                    r'<td class="scripture-(en|la)">(.*?)</td>', tr, re.S)}
                for side, style in (('en', 'margin-left:2em;'),
                                    ('la', 'text-align:right;')):
                    v = cs.get(side, '')
                    if not re.sub(r'<[^>]+>', '', v).strip():
                        continue
                    items.append(f'<p style="{style}" markdown="1">{v}</p>')
        else:
            seen = set()
            for n, t in INNER_VERSE_RE.findall(inner):
                t = t.strip()
                if not t:
                    continue
                # 同一节号第二次出现 = 拉丁（单列 box 里中文与拉丁都写 `**N.**`）
                style = 'text-align:right;' if n in seen else 'margin-left:2em;'
                seen.add(n)
                items.append(f'<p style="{style}" markdown="1">'
                             f'<strong>{n}.</strong> {t}</p>')
        # 保留 kramdown 脚注占位（02a §8）：它在 box 内但不是经文项，
        # 不显式保留就会被整块吞掉（zechariah/1.md 的 `[^f2][^f3]
        # {:.scripture-fnref-stub}`，33 字符，靠字符多重集抓到）。
        stub = re.search(r'(?:\[\^[^\]]+\]\s*)+\n?\{:\.scripture-fnref-stub\}', inner)
        tailparts = ([stub.group(0)] if stub else [])
        return ((ref.group(0) + '\n\n') if ref else '') + \
            '\n\n'.join(items + tailparts)

    return BOX_RE.sub(rep, text)


def rebuild_sections(text):
    """形态无关地重建双语 box。→ (新文本, 重建的段数)"""
    text = _unbox(text)
    blocks = text.split('\n\n')
    out, i, fixed = [], 0, 0
    while i < len(blocks):
        b = blocks[i]
        if not (SEC_START_RE.search(b) or '<p class="scripture-ref">' in b):
            out.append(b); i += 1; continue
        out.append(b)
        ref_slot = len(out) - 1          # 记住位置，**重建成功后**才摘 ref
        ref_html = None
        rm = re.search(r'<p class="scripture-ref">.*?</p>', b, re.S)
        if rm:
            ref_html = rm.group(0)      # 先只记下，不动 out[ref_slot]
        pri, lat, stubs, j = {}, {}, [], i + 1
        while j < len(blocks):
            seg = blocks[j].strip()
            if not seg:
                j += 1; continue
            if re.fullmatch(r'<div class="commentary-anchor"[^>]*></div>', seg):
                j += 1; continue
            rm2 = re.search(r'<p class="scripture-ref">.*?</p>', seg, re.S)
            if rm2 and not ref_html:
                ref_html = rm2.group(0); j += 1; continue
            if re.search(r'\{:\.scripture-fnref-stub\}', seg):
                stubs.append(seg); j += 1; continue
            m = ANY_VERSE_RE.match(seg)
            if not m or '<h2' in seg or seg.startswith('##'):
                break
            style = m.group('style') or ''
            num, body = m.group('num'), m.group('body').strip()
            nx = NEXT_VERSE_RE.search(body)
            trail = None
            if nx:
                trail = (nx.group(1), body[nx.end():].strip())
                body = body[:nx.start()].strip()
            is_la = ('right' in style) or ('center' in style)
            tgt = lat if (is_la or num in pri) else pri
            if num not in tgt:
                tgt[num] = body
            if trail and trail[0] not in pri:
                pri[trail[0]] = trail[1]
            j += 1
        if not (pri and lat):
            i += 1; continue
        # 到这里才确定要重建：把 ref 从原块里摘掉，挪进新 box
        if ref_html:
            out[ref_slot] = out[ref_slot].replace(ref_html, '').strip()
        rows = []
        for n in sorted(set(pri) | set(lat), key=int):
            e = f'<strong>{n}.</strong> ' + pri[n] if pri.get(n) else ''
            l = f'<strong>{n}.</strong> ' + lat[n] if lat.get(n) else ''
            rows.append(f'<tr><td class="scripture-en">{e}</td>'
                        f'<td class="scripture-la">{l}</td></tr>')
        out.append('<div class="scripture-box scripture-box--bilingual" markdown="1">\n'
                   + ((ref_html + '\n\n') if ref_html else '')
                   + '<table class="scripture-bilingual">\n<tbody>\n'
                   + '\n'.join(rows) + '\n</tbody>\n</table>\n\n</div>')
        out.extend(stubs)
        fixed += 1
        i = j
    return '\n\n'.join(out), fixed
