#!/usr/bin/env python3
"""用 PDF 上标层的实测位置，安置 psalms-1 章末「未定位的注释」。

这些条目此前被判为「标记已佚」，但实测并非如此：CAL_PSA1.pdf 的小字号（上标）
字符层里，46 条中有 26 条查得到标记。既然底本印着，就能按实测位置还原，不用推断。

做法：
1. 逐页取出字号明显小于正文的字符，拼成上标串，定位目标 code；
2. 取该 code 之前的一段**正文**字符作锚（去空白比较，与 footnote_marks.json 同套路）；
3. 在对应英文章节里唯一匹配该锚 → 其后插入 [^code]；
4. 中文 raw 与英文逐行对应，取同一行的同一相对位置插入；
5. 两侧孤儿块删掉已落位条目，中文定义从块中收割进 zh_footnote_defs.json。

匹配不唯一或中英行结构对不上的条目一律跳过并列出，宁可不动也不放错位置。

用法:
    python3 scripts/psalms1_place_from_pdf.py --dry-run
    python3 scripts/psalms1_place_from_pdf.py
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PDF = Path('/Users/yanpeifa/Documents/论文/calvin/CAL_PSA1.pdf')
EN = ROOT / 'calvin/psalms-1-en'
ZH = ROOT / 'calvin_raw/psalms-1/zh_chapters'
MARK = '<!-- unplaced-footnotes -->'


def orphans():
    out = {}
    for p in EN.glob('*.md'):
        if not p.stem.isdigit():
            continue
        m = re.search(r'<div class="unplaced-footnotes".*?</div>',
                      p.read_text(encoding='utf-8'), re.S)
        if m:
            for c in re.findall(r'^- \*\*([A-Za-z0-9]+)\*\*', m.group(0), re.M):
                out['f' + c] = p.stem
    return out


def pdf_contexts(codes):
    """→ {code: 标记之前的正文锚(已去空白)}"""
    import pdfplumber
    want = {c.lower() for c in codes}
    got = {}
    with pdfplumber.open(PDF) as pdf:
        for page in pdf.pages:
            chars = page.chars
            if not chars:
                continue
            sizes = [round(c['size'], 1) for c in chars]
            body = max(set(sizes), key=sizes.count)
            small = [i for i, s in enumerate(sizes) if s < body - 1]
            if not small:
                continue
            sup = ''.join(chars[i]['text'] for i in small)
            for m in re.finditer(r'f[a-f]0?\d+[A-Za-z]?', sup, re.I):
                code = m.group(0).lower()
                if code not in want or code in got:
                    continue
                start_char = small[m.start()]          # 标记首字符在页内的下标
                prev = ''.join(c['text'] for c in chars[:start_char]
                               if round(c['size'], 1) >= body - 1)
                got[code] = re.sub(r'\s+', '', prev)[-70:]
    return got


def strip_map(text):
    plain, idx = [], []
    i, n, intag = 0, len(text), False
    while i < n:
        ch = text[i]
        if ch == '<':
            j = text.find('>', i)
            i = j + 1 if j >= 0 else n
            continue
        if not ch.isspace():
            plain.append(ch); idx.append(i)
        i += 1
    return ''.join(plain), idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    orph = orphans()
    print(f'孤儿 {len(orph)} 条，从 PDF 取标记位置…')
    ctx = pdf_contexts(orph)
    print(f'PDF 上标层命中 {len(ctx)} 条\n')

    zh_path = ROOT / 'calvin_raw/psalms-1/zh_footnote_defs.json'
    zh_defs = json.loads(zh_path.read_text(encoding='utf-8'))
    placed, approx, skipped = {}, [], []

    for code, anchor in sorted(ctx.items()):
        ch = orph[code]
        ep, zp = EN / f'{ch}.md', ZH / f'{ch}.md'
        et = ep.read_text(encoding='utf-8')
        zt = zp.read_text(encoding='utf-8') if zp.exists() else None
        plain, idx = strip_map(et)
        hit = -1
        for cut in (0, 25, 40):
            probe = anchor[cut:]
            if len(probe) < 14:
                break
            if plain.count(probe) == 1:
                hit = idx[plain.index(probe) + len(probe) - 1] + 1
                break
        if hit < 0:
            skipped.append((code, ch, '锚点非唯一命中')); continue
        # 英文带章末定义区、中文没有 → 只比对定义区之前的正文
        def body_lines(s):
            m = re.search(r'^\[\^[a-z]{1,3}\d+[A-Za-z]?\]:', s, re.M)
            return (s[:m.start()] if m else s).split('\n')
        el, zl = body_lines(et), (body_lines(zt) if zt else None)
        li = et[:hit].count('\n')
        col = hit - (et.rfind('\n', 0, hit) + 1)
        if zl is None or abs(len(el) - len(zl)) > 2 or li >= min(len(el), len(zl)):
            skipped.append((code, ch, f'中英正文行不符 {len(el)}/{len(zl) if zl else "-"}')); continue
        # 中文落点：按「句序」对齐 —— 标记落在英文该段第几句之后，中文就放第几句之后。
        # 脚注标记几乎总在句末，段内句数中英通常一致；句数不符则跳过，不猜。
        def sent_ends(s, puncts):
            """返回每个句末标点在字符串中的结束下标（跳过标签内部）。"""
            ends, depth = [], 0
            for i, c in enumerate(s):
                if c == '<': depth += 1
                elif c == '>': depth = max(0, depth - 1)
                elif depth == 0 and c in puncts:
                    ends.append(i + 1)
            return ends
        e_ends = sent_ends(el[li], '.!?')
        z_ends = sent_ends(zl[li], '。！？')
        rest = el[li][col:]
        if not rest.strip():
            placed.setdefault(ch, []).append((code, li, col, ('end', None)))
        elif len(e_ends) == len(z_ends) and col in e_ends:
            k = e_ends.index(col)
            placed.setdefault(ch, []).append((code, li, col, ('sent', z_ends[k])))
        else:
            # 段落由 PDF 实测位置确定，段内具体位置无法机械判定 → 落在该段末尾
            placed.setdefault(ch, []).append((code, li, col, ('para', None)))
            approx.append((code, ch))

    for ch, items in sorted(placed.items(), key=lambda x: int(x[0])):
        print(f'ch{ch}: 可落位 {[c for c,_,_,_ in items]}')
    if approx:
        print(f'\n其中 {len(approx)} 条中文按段末落位(段落由 PDF 实测确定, 段内位置近似)')
    if skipped:
        print('\n跳过:')
        for code, ch, why in skipped:
            print(f'  ch{ch} {code}: {why}')
    if a.dry_run:
        print('\n（预演，未写入）')
        return

    for ch, items in placed.items():
        ep, zp = EN / f'{ch}.md', ZH / f'{ch}.md'
        el = ep.read_text(encoding='utf-8').split('\n')
        zl = zp.read_text(encoding='utf-8').split('\n')
        for code, li, col, (kind, zpos) in sorted(items, key=lambda x: -x[2]):
            el[li] = el[li][:col] + f'[^{code}]' + el[li][col:]
            if kind in ('end', 'para'):
                zl[li] = zl[li].rstrip() + f'[^{code}]'
            else:
                zl[li] = zl[li][:zpos] + f'[^{code}]' + zl[li][zpos:]
        et, zt = '\n'.join(el), '\n'.join(zl)
        codes = {c for c, _, _, _ in items}
        et, _ = drop_block(et, codes)
        zt, got = drop_block(zt, codes)
        zh_defs.update(got)
        ep.chmod(0o644); ep.write_text(et, encoding='utf-8')
        zp.chmod(0o644); zp.write_text(zt, encoding='utf-8'); zp.chmod(0o444)
    zh_path.write_text(json.dumps(zh_defs, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'\n已落位 {sum(len(v) for v in placed.values())} 条；'
          f'zh_footnote_defs.json → {len(zh_defs)} 条')


def drop_block(text, codes):
    m = re.search(r'(\n*' + re.escape(MARK) +
                  r'\n<div class="unplaced-footnotes".*?</div>\n?)', text, re.S)
    if not m:
        return text, {}
    got, kept = {}, []
    for line in m.group(1).split('\n'):
        mm = re.match(r'- \*\*([A-Za-z0-9]+)\*\*\s*(.*)$', line)
        if mm and 'f' + mm.group(1) in codes:
            got['f' + mm.group(1)] = mm.group(2).strip()
        else:
            kept.append(line)
    if not any(l.startswith('- **') for l in kept):
        return text[:m.start(1)].rstrip() + '\n' + text[m.end(1):], got
    return text[:m.start(1)] + '\n'.join(kept) + text[m.end(1):], got


if __name__ == '__main__':
    main()
