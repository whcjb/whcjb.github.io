#!/usr/bin/env python3
"""马太亨利中文版：经文框内容体检（只读，零模型额度）。

每个 mh-verse 框按框头在中文 PDF 里定位，取 PDF 从框头起的连续经文段（经文字体，
遇 ≥4 字的注释字体即止），与框内文字逐字比对（difflib），报框里缺掉的连续片段。

已知病因：早期转换把以「「」开头的经文节整节丢掉（结12:2、结13:2、结13:17 …）。

用法：
  python3 scripts/audit_mhenry_verse_boxes.py [book...]          # 列出缺节
  python3 scripts/audit_mhenry_verse_boxes.py --tsv out.tsv      # 同时写明细
"""
import difflib, os, re, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import ROOT, ANCHOR, UNIT_RE, han, chapter_files, pdf_files, _head
from fix_mhenry_unit_seams import pdf_stream_raw, clean

MIN_MISS = 6        # 框里缺 ≥ 6 个连续汉字才报


def scripture_span(P, F, vs, limit):
    vfont = max(set(F[vs:vs + ANCHOR]), key=F[vs:vs + ANCHOR].count)
    run = 0
    for i in range(vs, min(limit, len(P))):
        if F[i] != vfont:
            run += 1
            if run >= 4:
                return i - run + 1
        else:
            run = 0
    return min(limit, len(P))


VAR = str.maketrans('著麼么甚祢牠', '着吗吗什你它')


_NORM = {}


def best_head(P, v, cur, window=120000):
    """框头锚点在 [cur, cur+window) 的所有出现里，挑「框文前 200 字有多少能逐字对上」最高的。
    框里缺节时框比 PDF 短，用 ratio 会偏低，所以按框文命中比例打分；先做和合本用字归一。"""
    if _NORM.get('id') != id(P):
        _NORM['id'], _NORM['P'] = id(P), P.translate(VAR)   # 一对一替换，下标不变
    P = _NORM['P']
    key = v[:8].translate(VAR)        # 8 字：第 2 节缺失时 12 字锚点会横跨缺口
    a = v[:200].translate(VAR)
    best, score = -1, 0.0
    j = P.find(key, cur, cur + window)
    while j >= 0:
        def hit(x, y):
            sm = difflib.SequenceMatcher(None, x, y, autojunk=False)
            return sum(k.size for k in sm.get_matching_blocks()) / max(1, len(x))
        # 开头 60 字逐字吻合（防止锚到综述里的引文）+ 整框吻合（窗口 1.5 倍容纳框里缺节）
        r = 0.5 * hit(a[:60], P[j:j + 90]) + \
            0.5 * hit(a, P[j:j + int(len(a) * 1.5) + 20])
        if r > score:
            best, score = j, r
        j = P.find(key, j + 1, cur + window)
    return (best, True) if score >= 0.7 else (-1, False)


def audit(book, zh):
    files = pdf_files(book, zh)
    if not files:
        return None
    P, F, R, idx = pdf_stream_raw(files)
    out = []
    cur = 0
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
            se = scripture_span(P, F, vs, vs + len(v) * 3 + 500)
            cur = vs + 1
            pv = P[vs:se]
            sm = difflib.SequenceMatcher(None, v, pv, autojunk=False)
            miss = []
            for op, i1, i2, j1, j2 in sm.get_opcodes():
                if op in ('insert', 'replace') and (j2 - j1) - (i2 - i1) >= MIN_MISS:
                    miss.append((j1, j2))
            # 只算框「中间」缺的：落在框最后一段匹配之前（框尾缺另由接缝体检管）
            blocks = [b for b in sm.get_matching_blocks() if b.size >= 4]
            if not blocks:
                continue
            last_j = blocks[-1].b + blocks[-1].size
            miss = [(a, b) for a, b in miss if b <= last_j]
            if miss:
                footmark = bool(re.search(r'<sup|\[\^', m.group(1)))
                out.append(dict(ch=ch, unit=ui, md=md, vs=vs, se=se, miss=miss,
                                pv_raw=clean(R[idx[vs]:idx[se - 1] + 1]),
                                foot=footmark, span=(m.start(1), m.end(1)),
                                miss_txt=[pv[a:b] for a, b in miss]))
    return out


def main():
    args = sys.argv[1:]
    tsv = None
    if '--tsv' in args:
        k = args.index('--tsv'); tsv = args[k + 1]; del args[k:k + 2]
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {bk['id']: bk['name'] for grp in books.values() for bk in grp}
    rows, total = [], 0
    for book in args or list(names):
        if book.endswith('-en') or book not in names:
            continue
        zh = names[book]
        if not pdf_files(book, zh):
            zh = zh.replace('纪', '记') if '纪' in zh else zh.replace('记', '纪')
        res = audit(book, zh)
        if res is None:
            continue
        print(f'== {book}: {len(res)} 框缺节')
        for r in res:
            print(f"   {r['ch']} u{r['unit']} 缺{sum(b - a for a, b in r['miss'])}字 "
                  f"{'[有脚注标记]' if r['foot'] else ''} {' / '.join(t[:20] for t in r['miss_txt'])}")
            rows.append((book, r['ch'], r['unit'], ' / '.join(r['miss_txt'])))
        total += len(res)
    print('TOTAL', total)
    if tsv:
        with open(tsv, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write('\t'.join(map(str, r)) + '\n')


if __name__ == '__main__':
    main()
