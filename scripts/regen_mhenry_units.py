#!/usr/bin/env python3
"""按中文 PDF 重新生成马太亨利某章若干个连续单元（小标题 + 经文框 + 注释体）。

给接缝/经文框脚本修不动的重度损坏用：md 把 PDF 的几个单元并成一个、注释段大块错位、
缺小标题等。只认 PDF：
  - 段落 = PDF 行末带空格处分段
  - 小标题 = 不以句末标点结尾的短段，且下一段是经文 → <div class="mh-date-heading">
  - 经文 = 经文字体为主、以节号开头的段 → <div class="mh-verse">
  - 注释段以罗马号开头 → <div class="mh-l1"><span class="mh-label">I.</span>
  - 正文中的小号脚注引号数字照 md 习惯保留为普通数字
验收：原区段注释体文字（8 字串，和合本用字归一）≥98% 出现在新区段，否则不落盘。

用法：
  python3 scripts/regen_mhenry_units.py <book> <ch> <u_from> <u_to> [--apply]
  u_to 可写 end 表示到本章最后一个单元
"""
import os, re, sys, difflib
import fitz, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import pdf_profile, ROOT, PDF_DIR, TOP_MARGIN, RUNHEAD, HAN, UNIT_RE, han, pdf_files
from audit_mhenry_verse_boxes import best_head
from fix_mhenry_unit_seams import pdf_stream_raw, clean
from fix_mhenry_verse_boxes import fmt_verse

VAR = str.maketrans('著麼么甚祢牠', '着吗吗什你它')
ROMAN = re.compile(r'^(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)\.\s*')
END_PUNCT = '。！？：；，、'          # 小标题常以「（主前593 年）」收尾，「）」不算句末


def pdf_lines(files):
    """逐行记录：文字、是否段末、每个汉字的字体首字母、该行汉字在全书汉字流里的起止。
    过滤规则与 pdf_stream_raw 逐 span 一致（<11 号丢、y<40 丢、页眉丢），保证下标对齐。"""
    lines, hcount = [], 0
    min_size, conv = pdf_profile(files)
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        for page in doc:
            for blk in page.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    txt, fonts, h0, big, any_body = '', '', hcount, False, False
                    for sp in ln['spans']:
                        t = conv(sp['text']) if conv else sp['text']
                        if sp['bbox'][1] < TOP_MARGIN:
                            continue
                        if sp['size'] < min_size:
                            if any_body and re.fullmatch(r'\s*\d+\s*', t) and sp['size'] < 9:
                                txt += t.strip()      # 正文里的脚注引号
                            continue
                        if RUNHEAD.match(t.strip()):
                            continue
                        any_body = True
                        if sp['size'] >= 13:
                            big = True
                        txt += t
                        for c in t:
                            if HAN.match(c):
                                fonts += sp['font'][:1]; hcount += 1
                    if not any_body:
                        continue
                    big = big and re.fullmatch(r'\s*第[零一二三四五六七八九十百]+[章篇]\s*', txt) is not None
                    lines.append(dict(text=txt, end=txt.endswith(' '), fonts=fonts,
                                      h0=h0, h1=hcount, big=big))
    return lines


def paragraphs(lines):
    paras, cur = [], []
    for l in lines:
        if l['big']:
            if cur:
                paras.append(cur); cur = []
            continue
        cur.append(l)
        if l['end']:
            paras.append(cur); cur = []
    if cur:
        paras.append(cur)
    return paras


def render(paras, vfont):
    out, in_unit, in_l1 = [], False, False

    def close_l1():
        nonlocal in_l1
        if in_l1:
            out.append('</div>\n\n'); in_l1 = False

    def close_unit():
        nonlocal in_unit
        close_l1()
        if in_unit:
            out.append('</div>\n</div>\n\n'); in_unit = False

    kinds = []
    for p in paras:
        t = clean(''.join(l['text'] for l in p))
        f = ''.join(l['fonts'] for l in p)
        vr = f.count(vfont) / len(f) if f else 0
        starts_num = bool(re.match(r'\d{1,3}(?:-\d{1,3})?\s*(?![.．\d])', t))
        is_label = bool(ROMAN.match(t) or re.match(r'\d+[.．]|[（(]\d+[）)]|\[\d+\.\]', t))
        # 节号是小号上标的 PDF（林前等）经文段开头没有数字：经文字体 ≥90% 也算
        is_v = (starts_num and vr > 0.8) or (not is_label and vr >= 0.9 and len(t) >= 10)
        if t.strip():
            kinds.append(('V' if is_v else 'C', t))
    for i, (k, t) in enumerate(kinds):
        nxt = kinds[i + 1][0] if i + 1 < len(kinds) else None
        if k == 'C' and len(t) <= 40 and t[-1:] not in END_PUNCT and nxt == 'V':
            close_unit()
            t = re.sub(r'(\d)(年）)', r'\1 \2', t)     # md 现有写法「主前593 年」
            out.append(f'<div class="mh-date-heading">{t}</div>\n\n')
            continue
        if k == 'V':
            prev = kinds[i - 1][0] if i else None
            if prev == 'V' and in_unit and out and out[-1].endswith('VERSE_OPEN'):
                out[-1] = out[-1][:-len('VERSE_OPEN')] + ' ' + fmt_verse(t) + 'VERSE_OPEN'
                continue
            close_unit()
            out.append('<div class="mh-unit">\n<div class="mh-verse">\n' + fmt_verse(t) + 'VERSE_OPEN')
            in_unit = True
            continue
        # 注释段
        if out and out[-1].endswith('VERSE_OPEN'):
            out[-1] = out[-1][:-len('VERSE_OPEN')] + '\n</div>\n<div class="mh-unit-body">\n\n'
        m = ROMAN.match(t)
        if m:
            close_l1()
            out.append(f'<div class="mh-l1"><span class="mh-label">{m.group(1)}.</span>\n\n{t[m.end():]}\n\n')
            in_l1 = True
        else:
            out.append(t + '\n\n')
    if out and out[-1].endswith('VERSE_OPEN'):
        out[-1] = out[-1][:-len('VERSE_OPEN')] + '\n</div>\n<div class="mh-unit-body">\n\n'
    close_unit()
    return ''.join(out)


def region(s, units, u_from, u_to):
    """md 里第 u_from..u_to 单元（含紧挨着的前置小标题）的字符区间。"""
    def ustart(k):
        st = s.rfind('<div class="mh-unit">', 0, units[k - 1].start(1))
        hd = re.search(r'<div class="mh-date-heading">[^<]*</div>\s*$', s[:st])
        return hd.start() if hd else st
    a = ustart(u_from)
    if u_to < len(units):
        b = ustart(u_to + 1)
    else:
        aside = s.find('<aside', units[-1].start(2))
        b = aside if aside >= 0 else len(s.rstrip())
    return a, b


def main():
    args = sys.argv[1:]
    do_apply = '--apply' in args
    args = [x for x in args if x != '--apply']
    book, ch, u_from, u_to = args[0], args[1], int(args[2]), args[3]
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {bk['id']: bk['name'] for grp in books.values() for bk in grp}
    zh = names[book]
    if not pdf_files(book, zh):
        zh = zh.replace('纪', '记') if '纪' in zh else zh.replace('记', '纪')
    files = pdf_files(book, zh)
    md = f'{ROOT}/mhenry/{book}/{ch}.md'
    s = open(md, encoding='utf-8').read()
    units = list(UNIT_RE.finditer(s))
    u_to = len(units) if u_to == 'end' else int(u_to)
    P, F, R, idx = pdf_stream_raw(files)
    # PDF 起点：u_from 框头；终点：u_to+1 框头（或下一章标题）
    # 起点从本章 md 全文在 PDF 中的大致位置之后找
    ch_head = han(s[s.find('<div class="mh-overview">'):])[:8]
    base = max(0, P.find(ch_head)) if ch_head else 0
    st = os.environ.get('REGEN_START')          # 手工指定 PDF 起点文字（框为空时用）
    if st:
        vs, ok = P.find(han(st), base), True
        assert vs >= 0, 'REGEN_START 找不到'
    else:
        vs, ok = best_head(P, han(units[u_from - 1].group(1)), base, 400000)
    if not ok and not st:
        vs, ok = best_head(P, han(units[u_from - 1].group(1)), 0, len(P))
    assert ok, 'u_from 框头定位失败'
    if u_to < len(units):
        ve, ok = best_head(P, han(units[u_to].group(1)), vs + 1, 60000)
        assert ok, 'u_to+1 框头定位失败'
    else:
        ve = None
    lines = pdf_lines(files)
    vfont_code = F[vs]
    # 把 F 的字体代码换回字体名首字母：pdf_lines 用的是字体名首字母
    font_name = None
    if not st:
        # 经文字体 = 框头那个字在 PDF 里的字体（框头本身就是经文）
        lv = next(l for l in lines if l['h1'] > vs)
        seg_f = lv['fonts'][vs - lv['h0']:vs - lv['h0'] + 8]
        font_name = max(set(seg_f), key=seg_f.count) if seg_f else None
    if font_name is None:
        for l in lines:
            if l['h1'] > vs and re.match(r'\s*\d{1,3}(?:-\d{1,3})?\s*(?![.．\d])', l['text']) and l['fonts']:
                font_name = max(set(l['fonts']), key=l['fonts'].count)
                break
    # 取行：从含 vs 的行起（并回退一段小标题），到含 ve 的行前（并去掉它的前置小标题）
    i0 = next(i for i, l in enumerate(lines) if l['h1'] > vs)
    if ve is not None:
        i1 = next(i for i, l in enumerate(lines) if l['h1'] > ve)
    else:
        nxt = f'{ROOT}/mhenry/{book}/{int(ch) + 1}.md'
        i1 = None
        if os.path.exists(nxt):
            t2 = open(nxt, encoding='utf-8').read()
            ov = han(t2[t2.find('<div class="mh-overview">'):])[:12]
            j = P.find(ov, vs) if ov else -1
            if j >= 0:
                i1 = next(i for i, l in enumerate(lines) if l['h1'] > j)
        if i1 is None:
            i1 = next((i for i in range(i0 + 1, len(lines)) if lines[i]['big']), len(lines))
    VARN = lambda t: han(t).translate(VAR)
    # 起点：框头所在段的段首。段首到框头之间若是 md 别处没有的经文（如框缺第 1 节），从段首起
    ps = i0
    while ps > 0 and not lines[ps - 1]['end'] and not lines[ps - 1]['big']:
        ps -= 1
    before = ''.join(l['text'] for l in lines[ps:i0]) + lines[i0]['text']
    k_in = vs - lines[i0]['h0']
    pre_h = P[lines[ps]['h0']:vs]
    prev_box = VARN(units[u_from - 2].group(1)) if u_from >= 2 else ''
    fonts_before = ''.join(l['fonts'] for l in lines[ps:i0 + 1])[:len(pre_h)]
    extend = (len(pre_h) >= 4 and pre_h.translate(VAR)[:8] not in prev_box
              and fonts_before and fonts_before.count(font_name) / len(fonts_before) > 0.8
              and re.match(r'\s*\d', lines[ps]['text']))
    if extend:
        i0, vs = ps, lines[ps]['h0']
        print(f'起点前移到段首，补回 md 缺的 {len(pre_h)} 字经文：{pre_h[:20]}')
    sel = [dict(l) for l in lines[i0:i1]]
    # 起点精确到框头那个字（连同前面的节号与开引号），不带进上一节的尾巴
    l0 = sel[0]
    k = vs - l0['h0']
    if k > 0:
        cnt, pos = 0, 0
        for pos, c in enumerate(l0['text']):
            if HAN.match(c):
                if cnt == k:
                    break
                cnt += 1
        mnum = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', l0['text'][:pos])
        if mnum:
            pos = mnum.start()
        l0['text'] = l0['text'][pos:]
        l0['fonts'] = l0['fonts'][k:]
        l0['h0'] = vs
    # 终点精确到下一单元框头那个字之前（不含它的节号），同一行里前面的经文要留下
    if ve is not None and i1 < len(lines) and ve > lines[i1]['h0']:
        lt = dict(lines[i1])
        k2 = ve - lt['h0']
        cnt, pos = 0, len(lt['text'])
        for j_, c in enumerate(lt['text']):
            if HAN.match(c):
                if cnt == k2:
                    pos = j_
                    break
                cnt += 1
        mnum = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', lt['text'][:pos])
        if mnum:
            pos = mnum.start()
        lt['text'] = lt['text'][:pos].rstrip() + ' '
        lt['fonts'] = lt['fonts'][:k2]
        lt['h1'] = ve
        lt['end'] = True
        if HAN.search(lt['text']):
            sel.append(lt)
    paras = paragraphs(sel)
    # 前置小标题：i0 之前紧挨着的一段短段
    pre = paragraphs(lines[max(0, i0 - 3):i0]) if lines[i0]['h0'] == vs else []
    pre = [p_ for p_ in pre if clean(''.join(l['text'] for l in p_)).strip()]
    if pre:
        t = clean(''.join(l['text'] for l in pre[-1]))
        if len(t) <= 40 and t[-1:] not in END_PUNCT:
            paras = [pre[-1]] + paras
    # 末尾的小标题：下一单元前面已有同名小标题才去掉，否则保留（放在下一单元前）
    nxt_head = ''
    if u_to < len(units):
        st_next = s.rfind('<div class="mh-unit">', 0, units[u_to].start(1))
        mh_ = re.search(r'<div class="mh-date-heading">([^<]*)</div>\s*$', s[:st_next])
        nxt_head = re.sub(r'[\s（）()0-9年主前后]', '', mh_.group(1)) if mh_ else ''
    paras = [p_ for p_ in paras if clean(''.join(l['text'] for l in p_)).strip()]
    if paras:
        t = clean(''.join(l['text'] for l in paras[-1]))
        if len(t) <= 40 and t[-1:] not in END_PUNCT:
            if nxt_head and re.sub(r'[\s（）()0-9年主前后]', '', t) == nxt_head:
                paras = paras[:-1]
            else:
                paras[-1] = [dict(paras[-1][0], text=t, end=True)]
                paras.append('HEADING_AT_END')
    heading_at_end = paras and paras[-1] == 'HEADING_AT_END'
    if heading_at_end:
        paras = paras[:-1]
    new = render(paras, font_name)
    if heading_at_end:
        tl = clean(''.join(l['text'] for l in paras[-1]))
        tl2 = re.sub(r'(\d)(年）)', r'\1 \2', tl)
        if not new.rstrip().endswith('</div>') or f'>{tl2}</div>' not in new[-200:]:
            j_ = new.rfind(tl + '\n\n')                 # render 当注释段输出的，删掉
            if j_ >= 0:
                new = new[:j_] + new[j_ + len(tl) + 2:]
            new = new.rstrip() + f'\n\n<div class="mh-date-heading">{tl2}</div>\n\n'
    a, b = region(s, units, u_from, u_to)
    s0, a0, b0 = s, a, b                       # 原文件与原区段（重复守卫用）
    # 末尾单元只有经文、没有注释：PDF 下一单元开头的几节——并到 md 下一单元框头
    carry = ''
    mlast = list(re.finditer(r'(<div class="mh-date-heading">[^<]*</div>\s*)?<div class="mh-unit">\n<div class="mh-verse">\n(.*?)\n</div>\n<div class="mh-unit-body">\n*(.*?)</div>\n</div>\n*', new, re.S))
    if mlast and u_to < len(units):
        ml = mlast[-1]
        if not re.sub(r'<[^>]+>|\s', '', ml.group(3)) and ml.end() >= len(new.rstrip()) - 5:
            carry = ml.group(2).strip()
            head_txt = ml.group(1) or ''
            new = new[:ml.start()] + head_txt
            print(f'末尾单元只有经文，并入下一单元框头：{carry[:30]}')
    if os.environ.get('REGEN_OVERVIEW', '1') == '1':
        # 综述：md 综述只是 PDF 综述的前半截时，按 PDF 补全
        mo = re.search(r'(<div class="mh-overview">\n)(.*?)(\n</div>)', s, re.S)
        if mo:
            oh_ = VARN(mo.group(2))
            j0 = P.find(han(mo.group(2))[:12])
            if j0 >= 0:
                k0 = next(i for i, l in enumerate(lines) if l['h1'] > j0)
                ov_paras = []
                for p_ in paragraphs(lines[k0:i0 + 200]):
                    tt = clean(''.join(l['text'] for l in p_))
                    if not tt.strip():
                        continue
                    ff = ''.join(l['fonts'] for l in p_)
                    is_v = re.match(r'\d{1,3}(?:-\d{1,3})?\s*(?![.．\d])', tt) and ff and ff.count(font_name) / len(ff) > 0.8
                    if is_v or (len(tt) <= 40 and tt[-1:] not in END_PUNCT):
                        break                       # 综述止于第一个小标题或经文段
                    ov_paras.append(p_)
                ov = ''.join(clean(''.join(l['text'] for l in p_)) for p_ in ov_paras)
                ov = ov[ov.find(mo.group(2).strip()[:6]):] if mo.group(2).strip()[:6] in ov else ov
                if VARN(ov).startswith(oh_[:-3]) and len(han(ov)) > len(oh_) + 5:
                    print(f'综述按 PDF 补全：{len(oh_)} → {len(han(ov))} 字')
                    s = s[:mo.start(2)] + ov + s[mo.end(2):]
                    units = list(UNIT_RE.finditer(s))
                    a, b = region(s, units, u_from, u_to)
    if carry:
        nb = s.find('<div class="mh-verse">\n', b)
        s = s[:nb + len('<div class="mh-verse">\n')] + carry + ' ' + s[nb + len('<div class="mh-verse">\n'):]
        units = list(UNIT_RE.finditer(s))
        a, b = region(s, units, u_from, u_to)
    old = s[a:b]
    # 验收
    def body_text(t):
        return ''.join(m.group(2) for m in UNIT_RE.finditer(t)) if UNIT_RE.search(t) else t
    oh = han(re.sub(r'<div class="mh-verse">.*?</div>', '', old, flags=re.S)).translate(VAR)
    nh = han(s[:a] + new + s[b:]).translate(VAR)      # 挪到相邻单元的也算在
    grams = [oh[i:i + 8] for i in range(0, max(1, len(oh) - 8), 4)]
    miss = [g for g in grams if g not in nh]
    cover = 1 - len(miss) / max(1, len(grams))
    print(f'old {len(han(old))} 字 → new {len(han(new))} 字；原注释 8 字串覆盖 {cover:.3f}，缺 {len(miss)}：{miss[:8]}')
    out = os.environ.get('REGEN_PREVIEW')
    if out:
        open(out, 'w', encoding='utf-8').write(new)
    else:
        print('---- NEW (head) ----'); print(new[:1500]); print('---- NEW (tail) ----'); print(new[-600:])
    if do_apply:
        ratio = (len(han(new)) + len(han(carry))) / max(1, len(han(old)))   # 并入下一单元的也算
        # 不得制造重复：新区段的 10 字串不能大量出现在本章区段以外
        outside = han(s0[:a0] + s0[b0:]).translate(VAR)
        nn = han(new).translate(VAR)
        g10 = [nn[i:i + 10] for i in range(0, max(1, len(nn) - 10), 10)]
        dup = sum(1 for g in g10 if g in outside) / max(1, len(g10))
        print(f'区段外重复 {dup:.3f}')
        if dup > 0.03 and len(nn) >= 30:
            print('会制造重复，不落盘'); sys.exit(1)
        if cover < float(os.environ.get("REGEN_MIN", "0.98")) or not 0.75 <= ratio <= float(os.environ.get("REGEN_RATIO_MAX", "1.35")):
            print('覆盖不足，不落盘'); sys.exit(1)
        open(md, 'w', encoding='utf-8').write(s[:a] + new + s[b:])
        print('written', md)


if __name__ == '__main__':
    main()
