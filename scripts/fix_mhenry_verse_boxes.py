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
from audit_mhenry_unit_seams import ROOT, ANCHOR, UNIT_RE, han, chapter_files, pdf_files, _head
from fix_mhenry_unit_seams import pdf_stream_raw, clean
from audit_mhenry_verse_boxes import scripture_span, MIN_MISS, best_head

VAR = str.maketrans('著麼么甚祢牠', '着吗吗什你它')


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
                    s = s[:a] + '\n' + it['new'] + '\n' + s[b:]
                open(md, 'w', encoding='utf-8').write(s)
    print(f'OK {ok}  SKIP {bad}')


if __name__ == '__main__':
    main()
