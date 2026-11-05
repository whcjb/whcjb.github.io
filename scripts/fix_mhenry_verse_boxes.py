#!/usr/bin/env python3
"""按 PDF 补回经文框中间缺掉的整节（audit_mhenry_verse_boxes.py 报出的）。

新框 = PDF 从框头到「原框尾在 PDF 里对应的位置」之间的原文——中间缺节补齐，
起止不变（框尾缺经文、经文漏进注释体归接缝脚本管）。
验收：原框文字（和合本用字归一后）≥90% 出现在新框里，否则跳过。

用法：
  python3 scripts/fix_mhenry_verse_boxes.py [book...]          # dry-run
  python3 scripts/fix_mhenry_verse_boxes.py --apply [book...]
"""
import difflib, os, re, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import HAN, ROOT, ANCHOR, UNIT_RE, han, chapter_files, pdf_files, _head
from fix_mhenry_unit_seams import pdf_stream_raw, clean
from audit_mhenry_verse_boxes import scripture_span, MIN_MISS, best_head

VAR = str.maketrans('著麼么甚祢牠她', '着吗吗什你它他')


def fmt_verse(t):
    """md 经文框习惯：节号前空一格。"""
    t = re.sub(r'(?<=[^\d\s-])(\d{1,3}(?:-\d{1,3})?)(?=\s*[“‘「（一-鿿])', r' \1', t)
    t = re.sub(r'(\d)\s+(?=[“‘（一-鿿])', r'\1 ', t)
    return re.sub(r' {2,}', ' ', t).strip()


def plan(book, zh):
    files = pdf_files(book, zh)
    if not files:
        return []
    P, F, R, idx = pdf_stream_raw(files)
    out, cur = [], 0
    for md in chapter_files(book):
        ch = os.path.basename(md)[:-3]
        s = open(md, encoding='utf-8').read()
        for ui, m in enumerate(UNIT_RE.finditer(s), 1):
            v = han(m.group(1))
            if len(v) < ANCHOR:
                continue
            vs, exact = best_head(P, v, cur)
            if vs < 0 or not exact:
                continue
            cur = vs + 1
            # 框头前补：框头前紧挨着的经文字体段，且本章 md 里找不到 → 丢掉的第一节
            vfont = max(set(F[vs:vs + 12]), key=F[vs:vs + 12].count)
            k0 = vs
            while k0 > max(0, vs - 600):
                if F[k0 - 1] == vfont:
                    k0 -= 1
                    continue
                j = k0 - 1; n = 0                 # 允许夹 1-3 个异体字体的字
                while j >= 0 and F[j] != vfont and n < 4:
                    j -= 1; n += 1
                if n >= 4 or j < 0:
                    break
                k0 = j + 1
            pre = P[k0:vs]
            md_h = han(s).translate(VAR)
            boxes_h = ''.join(han(x) for x in re.findall(r'<div class="mh-verse">(.*?)</div>', s, re.S)).translate(VAR)
            pn = pre.translate(VAR)
            # 注释里常引经文，所以只看：本章各经文框里都没有，且整段在全文里没有原样出现
            if len(pre) >= 6 and pn[:12] not in boxes_h and pn[-12:] not in boxes_h:
                j0 = idx[k0]
                mnum = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', R[max(0, j0 - 10):j0])
                if mnum:
                    j0 -= len(mnum.group(0))
                j1 = idx[vs]
                mh = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', R[max(0, j1 - 10):j1])
                if mh:
                    j1 -= len(mh.group(0))
                while j0 > 0 and R[j0 - 1] in '（(「“‘『':
                    j0 -= 1                      # 带上紧挨着的开括号/开引号
                if not mnum:
                    # 诗篇第 1 节以诗题「1（……）」开头，诗题字体不同，回溯在诗题处停了：把诗题连节号带上
                    msup = re.search(r'(?<![\d.．])\d{1,3}\s*（[^（）\n]{1,80}）\s*$', R[max(0, j0 - 120):j0])
                    if msup:
                        j0 -= len(msup.group(0))
                raw_seg = R[j0:j1]
                mv = re.search(r'(?<![\d.．])\d{1,3}(?:-\d{1,3})?(?!\d|\s*年)\s*[「“‘『（]?\s*(?=[\u4e00-\u9fff])', raw_seg)
                if mv:
                    raw_seg = raw_seg[mv.start():]        # 去掉同字体的小标题（太5「登山宝训」）
                prepend = fmt_verse(clean(raw_seg))
                n0 = re.match(r'\s*(\d{1,3})', re.sub(r'<[^>]+>', '', m.group(1)))
                if not re.match(r'\d', prepend) and n0 and int(n0.group(1)) > 1:
                    # PDF 本身漏印节号（诗66「（一篇诗歌，交与伶长。）全地都当向神欢呼！2 ……」）
                    # 小标题与经文同字体时会一起回溯进来：去掉框前那段最后一个句末标点之前的部分
                    cut = max(prepend.rfind(' '), -1)
                    head_txt = prepend
                    mt = re.search(r'[（(]', head_txt)
                    if mt:
                        head_txt = head_txt[mt.start():]
                    prepend = f'{int(n0.group(1)) - 1} ' + head_txt.strip()
                commentary_like = re.search(r'^\d+章|第\s*\d+(?:-\d+)?\s*节|这里|注意|请看|(?<![A-Za-z])I\.|（\d+）', prepend)
                same_font_book = book in ('john', 'romans')    # 这两卷 PDF 经文与注释同字体，字体判据失效
                if re.match(r'\d', prepend) and len(han(prepend)) >= 6 and not commentary_like and not same_font_book:
                    vh = han(prepend).translate(VAR)
                    if vh in md_h:
                        # 已在 md 里：只接受「挂在上一块某行末尾」的情形（太5:13 在上一单元注释末、诗3:1 在综述末）
                        ustart = s.rfind('<div class="mh-unit">', 0, m.start(1))
                        lo = s.rfind('<div class="mh-unit-body">', 0, ustart)
                        if lo < 0:
                            lo = s.find('<div class="mh-overview">')
                        rem = None
                        for lm in re.finditer(r'[^\n]+', s[lo:ustart] if lo >= 0 else ''):
                            L = lm.group(0)
                            # 行末那截的汉字正好是这节经文
                            k = len(L)
                            cnt = 0
                            while k > 0 and cnt < len(vh):
                                k -= 1
                                if HAN.match(L[k]):
                                    cnt += 1
                            mm = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', L[:k])
                            k2 = mm.start() if mm else k
                            while k2 > 0 and L[k2 - 1] in '（(「“‘『':
                                k2 -= 1
                            if han(L[k2:]).translate(VAR) == vh and '<' not in L[k2:]:
                                rem = (lo + lm.start() + k2, lo + lm.end())
                        if not rem:
                            continue
                        out.append(dict(book=book, ch=ch, unit=ui, md=md, span=(m.start(1), m.end(1)),
                                        prepend=prepend, remove=rem, new=None, cover=1.0, added=1,
                                        miss=['挪回框头:' + prepend[:16]]))
                        continue
                    out.append(dict(book=book, ch=ch, unit=ui, md=md, span=(m.start(1), m.end(1)),
                                    prepend=prepend, new=None, cover=1.0, added=len(han(prepend)),
                                    miss=['框头前缺:' + prepend[:16]]))
                    continue
            se = scripture_span(P, F, vs, vs + len(v) * 3 + 500)
            pv = P[vs:se]
            sm = difflib.SequenceMatcher(None, v, pv, autojunk=False)
            blocks = [b for b in sm.get_matching_blocks() if b.size >= 4]
            if not blocks:
                continue
            last_j = blocks[-1].b + blocks[-1].size
            gaps = [(j1, j2) for op, i1, i2, j1, j2 in sm.get_opcodes()
                    if op in ('insert', 'replace') and (j2 - j1) - (i2 - i1) >= MIN_MISS and j2 <= last_j]
            if not gaps:
                continue
            end = vs + last_j
            j_end = idx[end - 1] + 1
            mp = re.match(r'[。，；：！？”’」』）)〉]*', R[j_end:j_end + 4])
            j_end += mp.end()
            j0 = idx[vs]
            mh = re.search(r'\d{1,3}(?:-\d{1,3})?\s*[「“‘『（]?\s*$', R[max(0, j0 - 10):j0])
            if mh:
                j0 -= len(mh.group(0))      # 带上框头的节号和开引号
            new = fmt_verse(clean(R[j0:j_end]))
            # 验收
            nv = han(new).translate(VAR)
            ov = v.translate(VAR)
            sm2 = difflib.SequenceMatcher(None, ov, nv, autojunk=False)
            cover = sum(b.size for b in sm2.get_matching_blocks()) / max(1, len(ov))
            out.append(dict(book=book, ch=ch, unit=ui, md=md, span=(m.start(1), m.end(1)),
                            new=new, cover=cover, added=len(han(new)) - len(v),
                            miss=[pv[a:b][:16] for a, b in gaps]))
    return out


def main():
    args = sys.argv[1:]
    do_apply = '--apply' in args
    args = [a for a in args if a != '--apply']
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {bk['id']: bk['name'] for grp in books.values() for bk in grp}
    ok = bad = 0
    for book in args or list(names):
        if book.endswith('-en') or book not in names:
            continue
        zh = names[book]
        if not pdf_files(book, zh):
            zh = zh.replace('纪', '记') if '纪' in zh else zh.replace('记', '纪')
        its = plan(book, zh)
        byfile = {}
        for it in its:
            good = it['cover'] >= 0.9 and it['added'] > 0
            tag = 'OK' if good else 'SKIP'
            print(f"{book} {it['ch']} u{it['unit']} +{it['added']}字 覆盖{it['cover']:.2f} {tag} | {' / '.join(it['miss'])}")
            if good:
                ok += 1
                byfile.setdefault(it['md'], []).append(it)
            else:
                bad += 1
        if do_apply:
            for md, lst in byfile.items():
                s = open(md, encoding='utf-8').read()
                for it in sorted(lst, key=lambda x: -x['span'][0]):
                    a, b = it['span']
                    if it.get('remove'):
                        r0, r1 = it['remove']
                        s = s[:a] + '\n' + it['prepend'] + ' ' + s[a:b].lstrip('\n') + s[b:]
                        s = s[:r0] + s[r1:]
                        continue
                    if it.get('prepend'):
                        body = s[a:b].lstrip('\n')
                        s = s[:a] + '\n' + it['prepend'] + ' ' + body + s[b:] if not body.endswith('\n') else s[:a] + '\n' + it['prepend'] + ' ' + body + s[b:]
                    else:
                        s = s[:a] + '\n' + it['new'] + '\n' + s[b:]
                open(md, 'w', encoding='utf-8').write(s)
    print(f'OK {ok}  SKIP {bad}')


if __name__ == '__main__':
    main()
