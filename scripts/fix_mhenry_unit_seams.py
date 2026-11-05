#!/usr/bin/env python3
"""按 PDF 修 audit_mhenry_unit_seams.py 报出的两类接缝错（零模型额度）。

  [A] 注释开头被吞 → 从 PDF 取回接缝处的原文，补在注释体开头
  [B] 注释漏进经文框 → 按 PDF 找经文真实结尾，把框尾那截挪到注释体开头

只自动处理「干净」的情形，其余列为 MANUAL 不动：
  - 缺口里夹着经文字体（可能整段经文+注释都丢了）
  - 缺口里有两个以上罗马大纲号
  - 缺口太长（> MAX_GAP 汉字）
  - 缺口文字其实在本章 md 别处（只是挪了位置，不是丢）

用法：
  python3 scripts/fix_mhenry_unit_seams.py [book...]           # dry-run，打印每处拟改
  python3 scripts/fix_mhenry_unit_seams.py --apply [book...]
"""
import os, re, sys
import fitz, yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import (pdf_profile, locate, RUNHEAD, ROOT, PDF_DIR, TOP_MARGIN, ANCHOR, GAP_MIN, HAN,
                                     UNIT_RE, pdf_files, han, chapter_files)

MAX_GAP = 400
ROMAN = re.compile(r'(?<![A-Za-z])((?:X{0,3})(?:IX|IV|V?I{0,3}))\.(?=\s*\S)')
ROMAN_STRICT = re.compile(r'(?<![A-Za-z.])(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII)\.')


def pdf_stream_raw(files):
    """汉字流 P、字体流 F、原文 R、P[i] 在 R 里的下标 idx。"""
    P, F, R, idx, codes = [], [], [], [], {}
    rlen = 0
    min_size, conv = pdf_profile(files)
    for fn in files:
        doc = fitz.open(PDF_DIR + fn)
        for page in doc:
            for blk in page.get_text('dict')['blocks']:
                for ln in blk.get('lines', []):
                    for sp in ln['spans']:
                        if sp['size'] < min_size or sp['bbox'][1] < TOP_MARGIN:
                            continue
                        if RUNHEAD.match(sp['text'].strip()):
                            continue
                        k = codes.setdefault(sp['font'], chr(65 + len(codes)))
                        t = conv(sp['text']) if conv else sp['text']
                        for j, c in enumerate(t):
                            if HAN.match(c):
                                P.append(c); F.append(k); idx.append(rlen + j)
                        R.append(t); rlen += len(t)
    return ''.join(P), ''.join(F), ''.join(R), idx


def clean(raw):
    s = raw.replace('\n', '')
    s = re.sub(r'(?<=[一-鿿\d（）：，。；、])\s+(?=[一-鿿\d（）：，。；、])', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace('「', '“').replace('」', '”').replace('『', '‘').replace('』', '’')
    return s


def join(a, b):
    """拼接 PDF 片段与原有正文：接缝处同一标点只留一个。"""
    if a and b and a[-1] in '，。；：、' and b.lstrip()[:1] == a[-1]:
        b = b.lstrip()[1:]
    return a + b


def first_text_pos(seg):
    """注释体里第一个正文字符的位置（跳过开头的空行/标签块）。"""
    m = re.match(r'\s*', seg)
    return m.end()


def plan(book, zh):
    files = pdf_files(book, zh)
    if not files:
        return []
    P, F, R, idx = pdf_stream_raw(files)
    plans = []
    cur = 0
    for md in chapter_files(book):
        ch = os.path.basename(md)[:-3]
        s = open(md, encoding='utf-8').read()
        md_han = han(s)
        for ui, m in enumerate(UNIT_RE.finditer(s), 1):
            v, b = han(m.group(1)), han(m.group(2))
            if len(v) < ANCHOR or len(b) < ANCHOR:
                continue
            loc = locate(P, v, b, cur)
            if loc is None:
                continue
            if len(loc) == 2:
                cur = loc[1]; continue
            vs, ve, bs, (ex_vh, ex_bh, ex_vt) = loc
            cur = bs
            vf = F[vs:vs + ANCHOR]
            vfont = max(set(vf), key=vf.count)

            if not ex_vt:
                # 框尾措辞与 PDF 不同、锚点模糊：吸附到最近的「经文字体→注释字体」切换点
                best = None
                for i in range(max(vs + 1, ve - 20), min(bs + 1, ve + 21)):
                    if F[i - 1] == vfont and all(c != vfont for c in F[i:i + 4]):
                        if best is None or abs(i - ve) < abs(best - ve):
                            best = i
                if best is not None:
                    ve, ex_vt = best, True
            exact = ex_bh and ex_vt          # 框头只用来定经文字体，模糊无妨
            # 经文真实结尾：从经文开头往后，第一段连续 ≥4 个非经文字体汉字之前
            true_end = ve
            run = 0
            for i in range(vs, ve):
                if F[i] != vfont:
                    run += 1
                    if run >= 4:
                        true_end = i - run + 1
                        break
                else:
                    run = 0
            leak_n = ve - true_end          # [B] 框尾混入的注释汉字数
            if leak_n > len(v) * 0.8:
                leak_n, true_end = 0, ve        # 定位失准，不按漏入处理
            gap_n = bs - ve                 # [A] 缺口汉字数
            if leak_n < 6 and gap_n < GAP_MIN:
                # [C] 注释体开头其实是经文（经文漏进注释体）：从 bs 起的经文字体连续段
                L, run = 0, 0
                for i in range(bs, min(len(F), bs + 3000)):
                    if F[i] != vfont:
                        run += 1
                        if run >= 4:
                            L = i - run + 1 - bs
                            break
                    else:
                        run = 0
                vt = re.sub(r'<[^>]+>', '', m.group(1)).rstrip()
                after = R[idx[bs + L - 1] + 1:idx[bs + L - 1] + 4] if L else ''
                seg_raw = R[idx[bs]:idx[bs + L - 1] + 1] if L else ''
                incomplete = not re.search(r'[。！？”’」』）)]$', vt)
                has_vnum = re.search(r'\d+\s*[“‘「『（]?[\u4e00-\u9fff]', seg_raw) is not None
                cites = re.match(r'\s*[（(]', after) is not None
                if L >= 8 and (incomplete or has_vnum) and not cites:
                    plans.append(dict(book=book, ch=ch, unit=ui, md=md, leak=0, gap=0, mode='pull',
                                      pull=L, pull_han=P[bs:bs + L], why=[], shape='C',
                                      raw=clean(R[idx[bs]:idx[bs + L - 1] + 1]),
                                      verse_span=(m.start(1), m.end(1)),
                                      body_span=(m.start(2), m.end(2))))
                continue

            item = dict(book=book, ch=ch, unit=ui, md=md, leak=leak_n, gap=gap_n,
                        verse_span=(m.start(1), m.end(1)), body_span=(m.start(2), m.end(2)))
            why = []
            if gap_n >= GAP_MIN:
                g = P[ve:bs]
                if sum(1 for c in F[ve:bs] if c == vfont) > max(4, gap_n * 0.3):
                    why.append('缺口夹经文字体')
                if gap_n > MAX_GAP:
                    why.append(f'缺口过长{gap_n}')
                mid = g[len(g) // 2 - 5:len(g) // 2 + 5]
                if mid in md_han:
                    why.append('缺口文字在md别处')
            # PDF 原文：从经文真实结尾（汉字 true_end-1 之后）到注释开头汉字 bs 之前
            r0 = idx[true_end - 1] + 1
            r1 = idx[bs]
            raw = R[r0:r1]
            txt = clean(raw)
            txt = re.sub(r'^[\s。，；：！？”’」』）)]+', '', txt)
            item['raw'] = txt
            item['leak_han'] = P[true_end:ve]
            romans = ROMAN_STRICT.findall(txt)
            if len(romans) > 1:
                why.append('缺口含多个罗马号')
            # 缺口字体结构：V=经文字体段 c=注释字体段（<4 字的碎段并入前段）
            segs = []
            for i in range(ve, bs):
                k = 'V' if F[i] == vfont else 'c'
                if segs and segs[-1][0] == k:
                    segs[-1][1] += 1
                else:
                    segs.append([k, 1])
            simp = []
            for k, n in segs:
                if simp and (n < 4 or simp[-1][0] == k):
                    simp[-1][1] += n
                else:
                    simp.append([k, n])
            item['shape'] = ''.join(k for k, _ in simp)
            item['segs'] = simp
            item['mode'] = 'body'
            starts_vnum = re.match(r'\d', txt) is not None
            if why == ['缺口夹经文字体'] and leak_n < 6:
                if item['shape'] == 'V':
                    item['mode'] = 'verse'   # 经文框缺末尾几节：按 PDF 补回框尾
                    why = []
                elif item['shape'].startswith('c'):
                    why = []                 # 注释开头丢失，里面的楷体只是引文
                elif item['shape'].startswith('Vc') and not starts_vnum:
                    why = []                 # 开头的楷体是注释起句引文
                elif item['shape'] == 'Vc':
                    # 框尾缺经文 + 注释开头丢失：在字体分界处切开
                    nV = simp[0][1]
                    cut = idx[ve + nV - 1] + 1
                    item['mode'] = 'split'
                    item['split_at'] = cut
                    why = []
            if item.get('mode') == 'split':
                item['raw_v'] = re.sub(r'^[\s。，；：！？”’」』）)]+', '', clean(R[r0:item['split_at']]))
                item['raw'] = clean(R[item['split_at']:r1])
                mp = re.match(r'^[。！？”’」』）)〉\s]+', item['raw'])   # 收尾标点归经文
                if mp:
                    item['raw_v'] += mp.group(0).strip()
                    item['raw'] = item['raw'][mp.end():]
            if not exact:
                why.append('锚点模糊')
            if why and ex_vh and ex_bh and gap_n < 3000 and '缺口过长' not in ','.join(why[:0]):
                # 整单元按 PDF 重建：经文框 = 框头起连续经文段；注释头补 PDF 经文后文字
                se, run = bs, 0
                for i in range(vs, bs):
                    if F[i] != vfont:
                        run += 1
                        if run >= 4:
                            se = i - run + 1
                            break
                    else:
                        run = 0
                if se > vs:
                    j1 = idx[se - 1] + 1
                    tail_p = re.match(r'[。，；：！？”’」』）)〉\s]*', R[j1:idx[se] if se < len(idx) else j1])
                    j1 += tail_p.end() if tail_p else 0
                    item['mode'] = 'rebuild'
                    j0 = idx[vs]
                    mh = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', R[max(0, j0 - 10):j0])
                    if mh:
                        j0 -= len(mh.group(0))      # 带上框头节号与开引号
                    from fix_mhenry_verse_boxes import fmt_verse
                    item['new_verse'] = fmt_verse(clean(R[j0:j1]))
                    item['new_verse_han'] = P[vs:se]
                    item['raw'] = clean(R[j1:idx[bs]]) if se < bs else ''
                    item['orig_why'] = why
                    why = []
            item['why'] = why
            plans.append(item)
    return plans


def rebuild_one(s, it):
    v0, v1 = it['verse_span']
    b0, b1 = it['body_span']
    verse, body = s[v0:v1], s[b0:b1]
    nvh = it['new_verse_han']
    # 注释体里与新经文框重复的整段经文：删段（段 = 空行分隔、不含标签）
    paras = re.split(r'(\n\s*\n)', body)
    kept = []
    for ptxt in paras:
        ph = han(ptxt)
        if '<' not in ptxt and len(ph) >= 8 and ph in nvh:
            continue
        kept.append(ptxt)
    body2 = ''.join(kept)
    # 段首挂着一截经文（段落其余是注释）：剥掉与新框重复的前缀
    p = first_text_pos(body2)
    k, n = p, 0
    while k < len(body2) and body2[k] != '<' and body2[k] != '\n':
        if HAN.match(body2[k]):
            if nvh.find(han(body2[p:k + 1])) < 0:
                break
            n += 1
        k += 1
    if n >= 8:
        # 回退到 k 之前最后一个汉字之后的标点
        body2 = body2[:p] + body2[k:].lstrip('。，；：！？”’」』）) ')
    nv = '\n' + it['new_verse'] + '\n'
    it2 = dict(it, mode='body', leak=0, verse_span=(v0, v0 + len(nv)), body_span=None)
    s2 = s[:v0] + nv + s[v1:b0] + body2 + s[b1:]
    nb0 = v0 + len(nv) + (b0 - v1)
    nb1 = nb0 + len(body2)
    if it['raw']:
        it2['body_span'] = (nb0, nb1)
        it2['gap'] = len(han(it['raw']))
        s2 = apply_one(s2, it2)
        if s2 is None:
            return None
    # 验收：原注释体一个 8 字串都不许丢；原经文框允许和合本用字差异，归一后 ≥80% 对得上
    VAR = str.maketrans('著麼么甚祢牠', '着吗吗什你它')
    new_h = han(s2).translate(VAR)
    def grams(t):
        t = han(t).translate(VAR)
        return [t[i:i + 8] for i in range(0, max(0, len(t) - 8), 4)]
    misses = [g for g in grams(body) if g not in new_h]
    vg = grams(verse)
    vmiss = [g for g in vg if g not in new_h]
    it['misses'] = misses + ['V:' + g for g in vmiss]
    if misses or (vg and len(vmiss) > 0.2 * len(vg)):
        print('  SKIP 重建后原文有缺', len(misses), len(vmiss), '/', len(vg), it['book'], it['ch'], it['unit'])
        return None
    return s2


def apply_one(s, it):
    """返回改后的 s（同一文件内按位置从后往前调用）。"""
    v0, v1 = it['verse_span']
    b0, b1 = it['body_span']
    body = s[b0:b1]
    verse = s[v0:v1]
    ins = it['raw']
    if it.get('mode') == 'rebuild':
        return rebuild_one(s, it)
    if it.get('mode') == 'pull':
        p = first_text_pos(body)
        n, k = it['pull'], p
        while n > 0 and k < len(body):
            if body[k] == '<':
                break                       # 注释体整段都是经文：挪到标签前为止
            if HAN.match(body[k]):
                n -= 1
            k += 1
        while k < len(body) and body[k] in '。，；：！？”’」』）) ':
            k += 1
        moved = body[p:k]
        if not moved.strip() or not it['pull_han'].startswith(han(moved)):
            print('  SKIP 漏入段与PDF不一致', it['book'], it['ch'], it['unit']); return None
        sep = ' ' if re.match(r'\d', moved) else ''
        verse = verse.rstrip() + sep + moved.strip() + '\n'
        rest = body[k:].lstrip()
        new_body = body[:p] + rest if rest.strip() else '\n'
        return s[:v0] + verse + s[v1:b0] + new_body + s[b1:]
    if it.get('mode') == 'split':
        sep = ' ' if re.match(r'\d', it['raw_v']) else ''
        verse = verse.rstrip() + sep + it['raw_v'] + '\n'
    if it.get('mode') == 'verse':
        sep = ' ' if re.match(r'\d', ins) else ''
        verse = verse.rstrip() + sep + ins + '\n'
        return s[:v0] + verse + s[v1:]
    # [B] 从经文框尾切掉漏入的那截：按汉字数从尾部回退
    if it['leak'] >= 6:
        n = it['leak']
        vh = han(verse)
        if not vh.endswith(it['leak_han']):
            # 注释前半截丢失、后半截漏进框尾：只切框尾与 PDF 吻合的后缀，补入时用 PDF 全文
            lh = it['leak_han']; n = 0
            while n < len(lh) and n < len(vh) and vh[-1 - n] == lh[-1 - n]:
                n += 1
            if n < 6:
                print('  SKIP 经文框尾与PDF不一致', it['book'], it['ch'], it['unit'])
                return None
            it = dict(it, leak_han=lh[-n:])
        k = len(verse)
        while n > 0 and k > 0:
            k -= 1
            if HAN.match(verse[k]):
                n -= 1
        # 回到该句起点前的标点（漏入段从 k 开始）
        cut = k
        if re.search(r'\d\s*[“‘「『（]?$', verse[max(0, cut - 4):cut]):
            print('  SKIP 漏入段前是节号（本身是经文）', it['book'], it['ch'], it['unit'])
            return None
        # 漏入段在经文框里的原文，必须与 PDF 汉字一致
        if han(verse[cut:]) != it['leak_han']:
            print('  SKIP 经文框尾与PDF不一致', it['book'], it['ch'], it['unit'])
            return None
        verse = verse[:cut].rstrip() + '\n'
    # 注释体开头
    p = first_text_pos(body)
    rest = body[p:]
    lead_label = re.match(r'<div class="mh-l1"><span class="mh-label">([IVX]+)\.</span>\s*', rest)
    if lead_label:
        # 注释体以大纲号开头：PDF 缺口末尾那个同号去掉，缺口作为引言段落放在前面
        ins2 = re.sub(r'\s*' + lead_label.group(1) + r'\.\s*$', '', ins)
        new_body = body[:p] + ins2 + '\n\n' + rest
    else:
        mr = ROMAN_STRICT.search(ins)
        if mr:
            pre, lab, post = ins[:mr.start()].rstrip(), mr.group(1), ins[mr.end():].lstrip()
            nxt = re.search(r'\n*<div class="mh-l1">', rest)
            if nxt:
                inner, after = rest[:nxt.start()].rstrip(), rest[nxt.start():].lstrip('\n')
            else:
                inner, after = rest.rstrip(), ''
            blk = (f'<div class="mh-l1"><span class="mh-label">{lab}.</span>\n\n'
                   f'{join(post, inner)}\n</div>\n\n')
            new_body = body[:p] + (pre + '\n\n' if pre else '') + blk + after
            if not after:
                new_body = new_body.rstrip() + '\n\n'
        else:
            sep = '\n\n' if it['leak'] >= 6 and it['gap'] < GAP_MIN else ''
            new_body = body[:p] + (ins + sep + rest if sep else join(ins, rest))
    return s[:v0] + verse + s[v1:b0] + new_body + s[b1:]


def main():
    args = sys.argv[1:]
    do_apply = '--apply' in args
    args = [a for a in args if a != '--apply']
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {bk['id']: bk['name'] for grp in books.values() for bk in grp}
    want = args or list(names)
    auto = manual = 0
    for book in want:
        if book.endswith('-en') or book not in names:
            continue
        zh = names[book]
        if not pdf_files(book, zh):
            zh = zh.replace('纪', '记') if '纪' in zh else zh.replace('记', '纪')
        plans = plan(book, zh)
        byfile = {}
        for it in plans:
            tag = 'MANUAL ' + ','.join(it['why']) if it['why'] else 'AUTO'
            print(f"{book} {it['ch']} u{it['unit']} leak={it['leak']} gap={it['gap']} shape={it['shape']} {tag}\n"
                  f"    + {it['raw'][:160]}")
            if it['why']:
                manual += 1
            else:
                auto += 1
                byfile.setdefault(it['md'], []).append(it)
        if do_apply:
            for md, its in byfile.items():
                s = open(md, encoding='utf-8').read()
                for it in sorted(its, key=lambda x: -x['verse_span'][0]):
                    r = apply_one(s, it)
                    if r is not None:
                        s = r
                open(md, 'w', encoding='utf-8').write(s)
    print(f'AUTO {auto}  MANUAL {manual}')


if __name__ == '__main__':
    main()
