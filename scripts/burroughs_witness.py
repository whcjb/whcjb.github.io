#!/usr/bin/env python3
"""巴罗夫《何西阿书讲解》缺字判读：第二证人按位置判读（old-book-ocr 第 ② 层）+ 判读图（第 ③ 层）。

    python3 scripts/burroughs_witness.py build            # 各证人 djvu.xml → witness/<id>/words.json
    python3 scripts/burroughs_witness.py pages            # 录入本每页 → 证人叶号 witness/page_leaf.json
    python3 scripts/burroughs_witness.py match            # 各缺字组 → 证人读法 witness/cands.json（试跑，报统计）
    python3 scripts/burroughs_witness.py land [--apply]   # 过闸的读法写进 gap_review.tsv / gap_approved.tsv
    python3 scripts/burroughs_witness.py sheets --gids a-b --name x   # 判读图：各组所在处裁片拼成一张

证人（IA，都是原书实物扫描，不是缩微胶片；ABBYY 文本层带词坐标）：
| 卷 | TCP | 证人 | 说明 |
|---|---|---|---|
| 1 | A30572（1652 第二版） | expositionofprop01burr（杜克，1643 初版） | **他版**：1652 是「新校」再版，重排；只作旁证，读法落推补表、加方括号 |
| 2 | A77979（1650） | expositionofprop02burr（杜克） | 同版 |
| 3 | A30574（1650） | expositionofprop03burr（杜克）+ expositionwithpr00jere（西弗吉尼亚卫斯理学院，Asbury 旧藏） | 同版两份；两份都有读法时须一致 |
| 4 | A30575（1651） | expositionofprop04burr（杜克） | 同版 |

闸（宁可不判）：
1. 定位：缺字组左邻 3 词、右邻 3 词在证人同一叶（± 邻叶）里各自连续对上，且这样的位置唯一；中间夹的词数 = 缺字组词数。
2. 字形：证人读法与录入本残字逐字母相合（• 处任意一个字母；ſ/f、u/v、i/j 视作同形）。
3. 词形：补出的词须在本书录入本里另外出现过（≥2 次），或在判词典里——证人 ABBYY 把长 ſ 读成 f，
   f/s、u/v、i/j 两可时以录入本自证定，定不了的不落。
4. 希腊文、希伯来文（〈Greek〉）与整段缺（〈…〉）不走这里，只能看图。
"""
import argparse
import collections
import difflib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import burroughs_common as bc  # noqa: E402

RAW = bc.RAW
WIT = RAW / 'witness'
VOLW = {1: ['expositionofprop01burr'], 2: ['expositionofprop02burr'],
        3: ['expositionofprop03burr', 'expositionwithpr00jere'], 4: ['expositionofprop04burr']}
SAME_ED = {1: False, 2: True, 3: True, 4: True}


TOKRE = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')


def key(w):
    w = w.lower().replace('ſ', 's').replace('f', 's').replace('v', 'u').replace('j', 'i').replace('vv', 'uu')
    return re.sub(r'[^a-z0-9]', '', w)


# ── build ──
def build():
    for ids in VOLW.values():
        for wid in ids:
            src = WIT / wid / f'{wid}_djvu.xml'
            leaves = []
            for _, obj in ET.iterparse(src, events=('end',)):
                if obj.tag != 'OBJECT':
                    continue
                words = []
                for ln_i, line in enumerate(obj.iter('LINE')):
                    for w in line.iter('WORD'):
                        t = (w.text or '').strip()
                        if t:
                            c = [int(x) for x in w.get('coords').split(',')[:4]]
                            words.append([t, ln_i, c])
                leaves.append(dict(w=int(obj.get('width')), h=int(obj.get('height')), words=words))
                obj.clear()
            (WIT / wid / 'words.json').write_text(json.dumps(leaves, ensure_ascii=False), encoding='utf-8')
            print(f'{wid}: {len(leaves)} 叶，{sum(len(x["words"]) for x in leaves)} 词', file=sys.stderr)


def load_words(wid):
    return json.loads((WIT / wid / 'words.json').read_text(encoding='utf-8'))


# ── 录入本按页切 ──
def tcp_pages():
    """vol → [(po, 页码, [词])]；po 与 gap_sites 的 po 同口径（本卷第几个带页码的页，新卷从书名页起重算）。"""
    od = json.loads((RAW / 'order.json').read_text(encoding='utf-8'))
    vol_of = {x['slug']: x['vol'] for k in ('sections', 'front', 'back') for x in od[k]}
    out = collections.defaultdict(list)
    cur_vol, po, label, buf = None, 0, None, []
    for slug in od['order']:
        v = vol_of[slug]
        if v != cur_vol:
            if buf and cur_vol:
                out[cur_vol].append((po, label, buf))
            cur_vol, po, label, buf = v, 0, None, []
        md = bc.read_src(slug)
        for part in re.split(r'(<span class="jb-pb"[^>]*></span>)', md):
            m = re.match(r'<span class="jb-pb"[^>]*data-p="([^"]+)"', part)
            if m:
                out[v].append((po, label, buf))
                po += 1
                label, buf = m.group(1), []
            elif not part.startswith('<span class="jb-pb"'):
                buf += bc.flat_words(part)
    out[cur_vol].append((po, label, buf))
    return out


def grams(keys, n=3):
    ks = [k for k in keys if len(k) >= 2]
    return {tuple(ks[i:i + n]) for i in range(len(ks) - n + 1)}


def pages():
    tp = tcp_pages()
    res = {}
    for v, ids in VOLW.items():
        for wid in ids:
            leaves = load_words(wid)
            lg = [grams([key(w[0]) for w in lf['words']]) for lf in leaves]
            ptr, mp, miss = 0, {}, 0
            for po, label, words in tp[v]:
                g = grams([key(w) for w in words])
                if len(g) < 8:
                    continue
                best, bi = 0, None
                for i in range(ptr, min(len(leaves), ptr + 12)):
                    s = len(g & lg[i])
                    if s > best:
                        best, bi = s, i
                if bi is None or best < max(4, len(g) // 10):
                    # 近处没有（录入本跳过了目录等整叶）：往后全卷找，要求更强
                    for i in range(ptr, len(leaves)):
                        s = len(g & lg[i])
                        if s > best:
                            best, bi = s, i
                    if bi is None or best < max(8, len(g) // 5):
                        miss += 1
                        continue
                mp[po] = bi
                ptr = bi
            res[wid] = mp
            print(f'卷{v} {wid}: 录入本 {len(tp[v])} 页，对上 {len(mp)}，对不上 {miss}', file=sys.stderr)
    (WIT / 'page_leaf.json').write_text(json.dumps(res), encoding='utf-8')


# ── match ──
_LEX = None


def lexicon():
    global _LEX
    if _LEX is None:
        cnt = collections.Counter()
        for f in sorted((RAW / 'en_chapters').glob('*.md')):
            for w in re.findall(r"[A-Za-z]+", re.sub(r'<[^>]+>', ' ', f.read_text(encoding='utf-8'))):
                cnt[w.lower()] += 1
        dic = set()
        for p in ('/usr/share/dict/words', '/usr/share/dict/web2'):
            if Path(p).exists():
                dic |= {x.strip().lower() for x in open(p, encoding='utf-8', errors='ignore')}
        _LEX = (cnt, dic)
    return _LEX


def is_word(w):
    cnt, dic = lexicon()
    w = w.lower()
    return cnt[w] >= 2 or w in dic


def resolve(raw):
    """证人读出的词 → 原书拼法候选：ABBYY 的 f 可能是 ſ；u/v、i/j 两可。返回唯一可取的形式或 None。"""
    cnt, dic = lexicon()
    opts = {''}
    for ch in raw:
        lo = ch.lower()
        alts = {'f': 'fs', 's': 's', 'u': 'uv', 'v': 'vu', 'i': 'ij', 'j': 'ji'}.get(lo, lo)
        alts = [a.upper() if ch.isupper() else a for a in alts]
        opts = {o + a for o in opts for a in alts}
        if len(opts) > 64:
            return None
    good = [o for o in opts if cnt[o.lower()] >= 2]
    if len(good) == 1:
        return good[0]
    if len(good) > 1:
        top = sorted(good, key=lambda o: -cnt[o.lower()])
        return top[0] if cnt[top[0].lower()] >= 10 * cnt[top[1].lower()] else None
    return None                                   # 判词典不兜底：ABBYY 读错的字母会被冷僻真词接住（•in → jin）


def sim(a, b):
    if a == b:
        return True
    if len(a) <= 3 or len(b) <= 3:
        return False
    return difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def ckey(w):
    """上下文词的键：带缺字记号的当通配（None），无字母的（&、标点）丢掉（返回空串，调用方滤掉）。"""
    if TOKRE.search(w):
        return None
    return key(w)


def wsim(a, b):
    return a is None or sim(a, b)


def locate(L, R, K, nmid):
    """K（证人键序列）里：L 末 3 词连续相似、R 前 3 词连续相似，中间夹 nmid（±1）个词。返回 [(i, j)]。
    L、R 里的 None 是通配（上下文自己也缺字）；三个里至少两个是实词。"""
    L3 = [k for k in L if k != ''][-3:]
    R3 = [k for k in R if k != ''][:3]
    if len(L3) < 3 or len(R3) < 3 or sum(k is None for k in L3 + R3) > 2 \
            or sum(k is None for k in L3) > 1 or sum(k is None for k in R3) > 1:
        return []
    hits = []
    for i in range(len(K) - 2):
        if not all(wsim(L3[t], K[i + t]) for t in range(3)):
            continue
        a = i + 3
        for mid in (nmid, nmid - 1, nmid + 1):
            j = a + mid
            if mid < 0 or j + 3 > len(K):
                continue
            if all(wsim(R3[t], K[j + t]) for t in range(3)):
                hits.append((a, j))
                break
    return hits


def fill_word(tw, ww):
    """录入本残字 tw（含 •）+ 证人词 ww → 补全词，或 None。只认字母，标点照 tw。"""
    core = re.sub(r'^[^A-Za-z•]+|[^A-Za-z•]+$', '', tw.replace('*', ''))
    if not core or '•' not in core or re.search(r'[^A-Za-z•]', core):
        return None
    wl = re.sub(r'[^A-Za-z]', '', ww)
    if len(wl) != len(core):
        return None
    out = []
    for c, w in zip(core, wl):
        if c == '•':
            out.append(w)
        elif key(c) != key(w):
            return None
        else:
            out.append(c)
    raw = ''.join(out)
    res = resolve(raw)
    if res is None:
        return None
    # 录入本已有的字母照录入本，不让 resolve 改动
    res = ''.join(c if c != '•' else r for c, r in zip(core, res))
    up = [c for c in core if c.isalpha()]
    if len(up) > 1 and all(c.isupper() for c in up):
        res = res.upper()
    return tw.replace('*', '').replace(core, res, 1)


def anchor_chars(words, side, n=12):
    """上下文词 → 锚字符串（键形，不含空格）。遇到缺字词就截断（锚只取连续的实词）。"""
    seq = words if side == 'R' else list(reversed(words))
    out = ''
    for w in seq:
        if TOKRE.search(w):
            break
        k = key(w)
        out = (out + k) if side == 'R' else (k + out)
        if len(out) >= n:
            break
    return out[:n] if side == 'R' else out[-n:]


def near(a, b):
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def find_anchor(W, A, lo=0, hi=None):
    """W 里与 A 近似的位置（ratio ≥ .84），用 A 的首或尾 4 字精确命中做候选。返回 [(起, 止)]。"""
    hi = len(W) if hi is None else hi
    n = len(A)
    cands = set()
    for seed, off in ((A[:4], 0), (A[-4:], n - 4)):
        p = W.find(seed, lo)
        while 0 <= p < hi:
            for d in (-1, 0, 1):
                st = p - off + d
                if st >= lo and st + n <= len(W):
                    cands.add(st)
            p = W.find(seed, p + 1)
    hits = []
    for st in sorted(cands):
        best = max(((near(A, W[st:st + n + e]), e) for e in (-1, 0, 1)), default=(0, 0))
        if best[0] >= .84:
            hits.append((st, st + n + best[1], best[0]))
    # 相邻起点合并（同一处 ±1）
    out = []
    for h in hits:
        if out and h[0] - out[-1][0] <= 2:
            if h[2] > out[-1][2]:
                out[-1] = h
        else:
            out.append(h)
    return out


def match():
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    pl = json.loads((WIT / 'page_leaf.json').read_text())
    wcache = {}
    cands = {}
    stat = collections.Counter()
    for s in sites:
        t = s['tcp']
        if '〈Greek〉' in t or '〈…〉' in t or 'MISSING' in t or '▪' in t:
            stat['看图类'] += 1
            continue
        words_t = t.split()
        if len(words_t) != 1:
            stat['多词组（看图）'] += 1
            continue
        tw = words_t[0]
        La, Ra = anchor_chars(s['left'], 'L'), anchor_chars(s['right'], 'R')
        if len(La) < 8 or len(Ra) < 8:
            stat['锚太短'] += 1
            continue
        reads = []
        for wid in VOLW[s['vol']]:
            mp = pl[wid]
            leaf = mp.get(str(s['po']))
            if leaf is None:
                nb = [int(k) for k in mp if abs(int(k) - s['po']) <= 2]
                if not nb:
                    continue
                leaf = mp[str(min(nb, key=lambda k: abs(k - s['po'])))]
            if wid not in wcache:
                wcache[wid] = load_words(wid)
            lv = wcache[wid]
            W, raw, where = [], [], []
            for li in range(max(0, leaf - 1), min(len(lv), leaf + 2)):
                for wi, w in enumerate(lv[li]['words']):
                    for ch in w[0]:
                        k = key(ch)
                        if k:
                            W.append(k)
                            raw.append(ch)
                            where.append((li, wi))
            W = ''.join(W)
            lh = find_anchor(W, La)
            got = []
            for a0, a1, _ in lh:
                for b0, b1, _ in find_anchor(W, Ra, a1, a1 + 40):
                    got.append((a1, b0))
            got = list(dict.fromkeys(got))
            if len(got) != 1:
                stat['定位不唯一' if got else '定位不上'] += 1
                reads.append(None)
                continue
            a, b = got[0]
            reads.append((wid, ''.join(raw[a:b]), sorted(set(where[a:b]))))
        ok = [r for r in reads if r]
        if not ok:
            continue
        outs = []
        for wid, mid, locs in ok:
            if '〈◊〉' in tw:
                r = resolve(mid) if mid else None
                v = tw.replace('〈◊〉', r) if r and (len(r) >= 2 or r.lower() in ('a', 'i', 'o')) else None
            else:
                v = fill_word(tw, mid)
            outs.append((v, wid, locs))
        vals = {o[0] for o in outs}
        if None in vals:
            stat['字形不合'] += 1
            continue
        if len(vals) > 1:
            stat['两证人不一'] += 1
            continue
        kind = 'word' if '〈◊〉' in t else 'letter'
        cands[s['gid']] = dict(read=outs[0][0], wid=outs[0][1], locs=outs[0][2], kind=kind, vol=s['vol'], tcp=t,
                               n=len(outs))
        stat[f'读出·{kind}·卷{s["vol"]}'] += 1
    (WIT / 'cands.json').write_text(json.dumps(cands, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'缺字组 {len(sites)}：' + '，'.join(f'{k} {v}' for k, v in sorted(stat.items())), file=sys.stderr)


# ── land ──
# 抽样看图（2026-11-26）：同版 32 条中看得到的 26 条全对，初版 16 条中看得到的 15 条全对；2138 影像 then/them 两可，不落
HOLD = {2138}
NOTE_SAME = '同版实物扫描（{wid}）同处 OCR 读作「{read}」，与录入本残字逐字母相合；抽样看图核过'
NOTE_ED1 = '1643 初版（{wid}）同处读作「{read}」，与 1652 录入本残字逐字母相合'


def land(apply):
    cands = json.loads((WIT / 'cands.json').read_text(encoding='utf-8'))
    rv = {r[0]: r for r in bc._tsv('gap_review.tsv')}
    ap = {r[0]: r for r in bc._tsv('gap_approved.tsv')}
    add_rv, add_ap = [], []
    for g, c in sorted(cands.items(), key=lambda x: int(x[0])):
        if int(g) in HOLD or g in rv or g in ap:
            continue
        v = c['read'].replace('*', '')
        if SAME_ED[c['vol']]:
            add_rv.append(f'{g}\t{v}\t证人OCR\t' + NOTE_SAME.format(wid=c['wid'], read=v))
        else:
            add_ap.append(f'{g}\t{v}\t初版同处\t\t' + NOTE_ED1.format(wid=c['wid'], read=v))
    print(f'判读表 +{len(add_rv)}，推补表 +{len(add_ap)}', file=sys.stderr)
    if apply:
        for name, rows, head in (('gap_review.tsv', add_rv, '# gid\t读法\t依据\t备注'),
                                 ('gap_approved.tsv', add_ap, '# gid\t读法\t类别\t\t依据')):
            f = RAW / name
            old = f.read_text(encoding='utf-8').rstrip('\n').split('\n') if f.exists() else [head]
            f.write_text('\n'.join(old + rows) + '\n', encoding='utf-8')


# ── put：看图判读落表 ──
def put(path):
    """path 每行：gid<TAB>补字<TAB>备注。补字：• 依次填入的字母（多段用 | 分隔），或整词缺／〈Greek〉处的整词；
    ? = 影像也读不出（备注写 P:推断）。第 1 卷（他版影像）落推补表，其余落判读表（看图读出，不加括号）。"""
    sites = {str(x['gid']): x for x in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    rv = {r[0] for r in bc._tsv('gap_review.tsv')}
    ap = {r[0] for r in bc._tsv('gap_approved.tsv')}
    add_rv, add_ap, seen = [], [], []
    for ln in Path(path).read_text(encoding='utf-8').splitlines():
        if not ln.strip() or ln.startswith('#'):
            continue
        g, fill, *note = ln.split('\t')
        note = note[0] if note else ''
        s = sites[g]
        if g in rv or g in ap:
            print(f'⚠️ {g} 已有判读，跳过', file=sys.stderr)
            continue
        t = s['tcp'].replace('*', '')
        if fill == '-':                       # 裁片里看不到（落在裁片外）：记账，换裁法再看
            seen.append(f'{g}\t{note or "裁片外"}')
            continue
        if fill == '?':
            v = '?'
        else:
            parts = fill.split('|')
            toks = TOKRE.findall(t)
            if len(parts) != len(toks):
                raise ValueError(f'{g}: 原串 {t!r} 有 {len(toks)} 处缺，给了 {len(parts)} 段')
            it = iter(parts)
            v = TOKRE.sub(lambda m: next(it), t)
            v = re.sub(r'(?<=\S)⁀ (?=\S)|(?<=\S) ⁀(?=\S)', '', v)   # 段间连写号（e⁀|xt）当场并词，落字时只认首尾的 ⁀
            for tok, part in zip(toks, parts):
                if tok.startswith('•') and len(part) != len(tok) and not note.startswith('字数'):
                    raise ValueError(f'{g}: {tok} 缺 {len(tok)} 字，给了 {part!r}')
        where = f'{s.get("vol")}卷'
        if s['vol'] == 1 and v != '?':
            add_ap.append(f'{g}\t{v}\t初版影像\t\t1643 初版（expositionofprop01burr）同处影像读作「{v}」' + (f'；{note}' if note else ''))
        else:
            add_rv.append(f'{g}\t{v}\t看图\t{note}')
    if seen:
        f = RAW / 'witness_seen.tsv'
        old = f.read_text(encoding='utf-8') if f.exists() else '# gid\t看过但裁片里看不到（换裁法再看）\n'
        f.write_text(old + '\n'.join(seen) + '\n', encoding='utf-8')
    for name, rows in (('gap_review.tsv', add_rv), ('gap_approved.tsv', add_ap)):
        if rows:
            f = RAW / name
            f.write_text(f.read_text(encoding='utf-8').rstrip('\n') + '\n' + '\n'.join(rows) + '\n', encoding='utf-8')
    print(f'判读表 +{len(add_rv)}，推补表 +{len(add_ap)}', file=sys.stderr)


def todo(vol, n):
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    done = {int(r[0]) for r in bc._tsv('gap_review.tsv')} | {int(r[0]) for r in bc._tsv('gap_approved.tsv')}
    f = RAW / 'witness_seen.tsv'
    if f.exists():
        done |= {int(ln.split('\t')[0]) for ln in f.read_text(encoding='utf-8').splitlines() if ln[:1].isdigit()}
    wc, out = {}, []
    for s in sites:
        if s['vol'] != vol or s['gid'] in done:
            continue
        if locate_site(s, wc) is None:
            continue
        out.append(s['gid'])
        if len(out) >= n:
            break
    print(','.join(map(str, out)))


# ── 定位（判读图用）：两侧锚都在最好；只有一侧时取那一侧 ──
def locate_site(s, wcache):
    """→ (wid, leaf, bbox, how)；bbox = 原图像素 (x0, y0, x1, y1)，缺字大致所在的那一小段。"""
    pl = _pl()
    La, Ra = anchor_chars(s['left'], 'L'), anchor_chars(s['right'], 'R')
    for wid in VOLW[s['vol']]:
        mp = pl[wid]
        leaf = mp.get(str(s['po']))
        if leaf is None:
            nb = [int(k) for k in mp if abs(int(k) - s['po']) <= 2]
            if not nb:
                continue
            leaf = mp[str(min(nb, key=lambda k: abs(k - s['po'])))]
        if wid not in wcache:
            wcache[wid] = load_words(wid)
        lv = wcache[wid]
        W, where = [], []
        for li in range(max(0, leaf - 1), min(len(lv), leaf + 2)):
            for wi, w in enumerate(lv[li]['words']):
                for ch in w[0]:
                    if key(ch):
                        W.append(key(ch))
                        where.append((li, wi))
        W = ''.join(W)
        lh = find_anchor(W, La) if len(La) >= 8 else []
        rh = find_anchor(W, Ra) if len(Ra) >= 8 else []
        pair = [(a, b) for a in lh for b in rh if 0 <= b[0] - a[1] <= 40]
        if len(pair) == 1:
            (a0, a1, _), (b0, b1, _) = pair[0]
            pts, how = [where[a1 - 1], where[min(b0, len(where) - 1)]], '两侧'
        elif len(lh) == 1:
            pts, how = [where[lh[0][1] - 1]], '左锚'
        elif len(rh) == 1:
            pts, how = [where[rh[0][0]]], '右锚'
        else:
            est = estimate(s, lv, leaf)
            if est:
                return (wid,) + est
            continue
        li = pts[0][0]
        same = [p for p in pts if p[0] == li]
        bx = [lv[li]['words'][wi][2] for _, wi in same]          # coords: x0, y1(下), x1, y0(上)
        y0 = min(b[3] for b in bx)
        y1 = max(b[1] for b in bx)
        if how == '两侧' and len(same) == 2 and abs(bx[0][1] - bx[1][1]) < (y1 - y0):
            cx = (bx[0][2] + bx[1][0]) / 2                        # 左锚尾与右锚头之间
        elif how == '右锚':
            cx = bx[0][0] - 120
        else:
            cx = bx[0][2] + 120                                   # 左锚尾往右一点；跨行时缺字在下一行行首，裁高度已含
        return wid, li, (cx - 1, y0, cx + 1, y1), how
    return None


_TP = None


def estimate(s, lv, leaf):
    """估位：缺字在录入本本页的词序比例 → 证人本叶正文行的同一比例处。返回 (leaf, bbox, '估位')。"""
    global _TP
    if _TP is None:
        _TP = tcp_pages()
    page = next((w for po, lab, w in _TP[s['vol']] if po == s['po']), None)
    if not page or s.get('stream') == 'note':
        return None
    keys = [key(w) for w in page]
    L = [key(w) for w in s['left'][-3:]]
    idx = None
    for i in range(len(keys) - len(L) + 1):
        if keys[i:i + len(L)] == L:
            idx = i + len(L)
            break
    if idx is None:
        return None
    frac = idx / max(1, len(keys))
    words = lv[leaf]['words']
    lines = collections.OrderedDict()
    for t, ln, c in words:
        lines.setdefault(ln, []).append(c)
    rows = sorted(((sum(c[1] + c[3] for c in cs) / 2 / len(cs), cs) for cs in lines.values() if len(cs) >= 4),
                  key=lambda x: x[0])
    if len(rows) < 8:
        return None
    k = min(len(rows) - 1, int(frac * len(rows)))
    y = rows[k][0]
    xs = [c[0] for _, cs in rows for c in cs] + [c[2] for _, cs in rows for c in cs]
    x0, x1 = min(xs), max(xs)
    lh = sum(c[1] - c[3] for c in rows[k][1]) / len(rows[k][1])
    return leaf, ((x0 + x1) / 2 - 1, y - lh / 2, (x0 + x1) / 2 + 1, y + lh / 2), '估位'


_PL = None


def _pl():
    global _PL
    if _PL is None:
        _PL = json.loads((WIT / 'page_leaf.json').read_text())
    return _PL


def leaf_img(wid, leaf):
    import subprocess
    f = WIT / wid / 'img' / f'n{leaf}.jpg'
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        url = f'https://archive.org/download/{wid}/page/n{leaf}_w2000.jpg'
        subprocess.run(['curl', '-sL', '--max-time', '120', '-o', str(f), url], check=True)
    return f


def gidrange(spec):
    out = []
    for part in spec.split(','):
        if '-' in part:
            a, b = part.split('-')
            out += list(range(int(a), int(b) + 1))
        elif part:
            out.append(int(part))
    return out


def prefetch(gids):
    """一批判读图要用的叶并行下载（curl -P 8，前台）。"""
    import subprocess
    sites = {x['gid']: x for x in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    wcache, need = {}, set()
    for g in gids:
        loc = locate_site(sites[g], wcache)
        if loc:
            need.add((loc[0], loc[1]))
    todo = [(w, l) for w, l in sorted(need) if not (WIT / w / 'img' / f'n{l}.jpg').exists()]
    args = []
    for w, l in todo:
        (WIT / w / 'img').mkdir(parents=True, exist_ok=True)
        args += [f'https://archive.org/download/{w}/page/n{l}_w2000.jpg', str(WIT / w / 'img' / f'n{l}.jpg')]
    if args:
        subprocess.run(['xargs', '-n', '2', '-P', '8', 'sh', '-c', 'curl -sL --max-time 180 -o "$1" "$0"'],
                       input='\n'.join(args).encode(), check=False)
    print(f'需要 {len(need)} 叶，新下载 {len(todo)}', file=sys.stderr)


def sheets(gids, name, per=16):
    """判读图（第 ③ 层）。须用带 PIL 的解释器跑：/usr/bin/python3 scripts/burroughs_witness.py sheets …"""
    from PIL import Image, ImageDraw
    sites = {x['gid']: x for x in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    cands = json.loads((WIT / 'cands.json').read_text(encoding='utf-8'))
    out_dir = WIT / 'sheets'
    out_dir.mkdir(exist_ok=True)
    wcache, items, lost = {}, [], []
    for g in gids:
        s = sites[g]
        loc = locate_site(s, wcache)
        if not loc:
            lost.append(g)
            continue
        items.append((g, s, loc))
    CW, CH = 980, 200
    if items and all(x[2][3] == '估位' for x in items):        # 估位批：整行宽、九行高，不压扁
        CH = 470
    SRC_W = 1400                                                   # 原图上裁 1400 宽（约正文一行半）再缩到 980
    lines = []
    for k in range(0, len(items), per):
        chunk = items[k:k + per]
        cols = 2
        rows = (len(chunk) + 1) // 2
        sheet = Image.new('RGB', (CW * cols, (CH + 24) * rows), 'white')
        dr = ImageDraw.Draw(sheet)
        for n, (g, s, (wid, leaf, (x0, y0, x1, y1), how)) in enumerate(chunk):
            im = Image.open(leaf_img(wid, leaf))
            sc = im.size[0] / wcache[wid][leaf]['w']
            cx, cy = (x0 + x1) / 2 * sc, (y0 + y1) / 2 * sc
            lh = max(60, (y1 - y0) * sc)
            hw = SRC_W / 2
            box = (int(cx - hw), int(cy - lh * 1.9), int(cx + hw), int(cy + lh * 1.9))
            if how == '估位':                                       # 估位不准：整行宽、上下各四行半
                hw = min(im.size[0] / 2, 1000 * sc)
                box = (int(cx - hw), int(cy - lh * 4.5), int(cx + hw), int(cy + lh * 4.5))
            crop = im.crop(box).resize((CW, CH))
            c, r = n % cols, n // cols
            sheet.paste(crop, (c * CW, r * (CH + 24) + 24))
            ctx = ' '.join(s['left'][-3:]) + ' <' + s['tcp'] + '> ' + ' '.join(s['right'][:3])
            ctx = ctx.replace('•', '#').replace('〈◊〉', '[WORD]').replace('〈…〉', '[SPAN]').replace('〈Greek〉', '[GREEK]')
            ctx = ctx.encode('ascii', 'replace').decode()
            hint = cands.get(str(g), {}).get('read', '')
            lab = f'{g} {how[:1]}  {ctx}' + (f'   OCR: {hint}' if hint else '')
            lab = lab.encode('ascii', 'replace').decode()
            dr.rectangle((c * CW, r * (CH + 24), (c + 1) * CW - 1, r * (CH + 24) + 23), fill=(255, 240, 200))
            dr.text((c * CW + 6, r * (CH + 24) + 6), lab[:150], fill='black')
            lines.append(f'{g}\t{wid}\tn{leaf}\t{how}\t{s["tcp"]}\t{hint}')
        f = out_dir / f'{name}_{k // per:02d}.jpg'
        sheet.save(f, quality=82)
        print(f, file=sys.stderr)
    (out_dir / f'{name}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    if lost:
        print(f'定位不上 {len(lost)}：{lost[:30]}', file=sys.stderr)


# ── 旁注判读图：旁注不在正文流里，用它所对正文位置（mleft/mright）定位到行，裁该行上下两侧页边 ──
def note_loc(s, wcache):
    ps = dict(s, left=s.get('mleft') or [], right=s.get('mright') or [], stream='main')
    return locate_site(ps, wcache)


def mtodo(vol, n):
    """旁注里尚未判读、也没记过「裁片外」的组，按 (叶, 行位) 聚成格。"""
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    done = {int(r[0]) for r in bc._tsv('gap_review.tsv')} | {int(r[0]) for r in bc._tsv('gap_approved.tsv')}
    f = RAW / 'witness_seen.tsv'
    seen = {int(ln.split('\t')[0]) for ln in f.read_text(encoding='utf-8').splitlines() if ln[:1].isdigit()} if f.exists() else set()
    out = [s['gid'] for s in sites if s['vol'] == vol and s['stream'] == 'note' and s['gid'] not in done | seen]
    print(','.join(map(str, out[:n])))


def msheets(gids, name, per=10):
    """一格 = 同叶同处（行位差 < 6 行）的一组旁注缺字；格内是该行上下各 7 行的左右两条页边并排。"""
    from PIL import Image, ImageDraw
    sites = {x['gid']: x for x in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    wcache, cells, lost = {}, [], []
    for g in gids:
        loc = note_loc(sites[g], wcache)
        if not loc:
            lost.append(g)
            continue
        wid, leaf, (x0, y0, x1, y1), how = loc
        cy, lh = (y0 + y1) / 2, max(1, y1 - y0)
        for c in cells:
            if c['wid'] == wid and c['leaf'] == leaf and abs(c['cy'] - cy) < 6 * lh:
                c['g'].append(g)
                break
        else:
            cells.append(dict(wid=wid, leaf=leaf, cy=cy, lh=lh, how=how, g=[g]))
    out_dir = WIT / 'sheets'
    out_dir.mkdir(exist_ok=True)
    TW, TH = 980, 560
    lines = []
    for k in range(0, len(cells), per):
        chunk = cells[k:k + per]
        rows = (len(chunk) + 1) // 2
        sheet = Image.new('RGB', (TW * 2, (TH + 34) * rows), 'white')
        dr = ImageDraw.Draw(sheet)
        for n, c in enumerate(chunk):
            im = Image.open(leaf_img(c['wid'], c['leaf']))
            W, H = im.size
            sc = W / wcache[c['wid']][c['leaf']]['w']
            cy, lh = c['cy'] * sc, max(40, c['lh'] * sc)
            top, bot = int(cy - lh * 7), int(cy + lh * 7)
            mw = int(W * 0.30)
            left, right = im.crop((0, top, mw, bot)), im.crop((W - mw, top, W, bot))
            strip = Image.new('RGB', (mw * 2 + 8, bot - top), 'black')
            strip.paste(left, (0, 0)); strip.paste(right, (mw + 8, 0))
            strip = strip.resize((TW, TH))
            col, row = n % 2, n // 2
            sheet.paste(strip, (col * TW, row * (TH + 34) + 34))
            labs = []
            for g in c['g']:
                s = sites[g]
                t = (' '.join(s['left'][-2:]) + ' <' + s['tcp'] + '> ' + ' '.join(s['right'][:2]))
                t = t.replace('•', '#').replace('〈◊〉', '[W]').replace('〈…〉', '[SPAN]').replace('〈Greek〉', '[GK]')
                labs.append(f'{g}: ' + t.encode('ascii', 'replace').decode())
                lines.append(f'{g}\t{c["wid"]}\tn{c["leaf"]}\t{c["how"]}\t{s["tcp"]}\t')
            dr.rectangle((col * TW, row * (TH + 34), (col + 1) * TW - 1, row * (TH + 34) + 33), fill=(255, 240, 200))
            dr.text((col * TW + 4, row * (TH + 34) + 2), '  |  '.join(labs)[:170], fill='black')
            dr.text((col * TW + 4, row * (TH + 34) + 17), '  |  '.join(labs)[170:340], fill='black')
        f = out_dir / f'{name}_{k // per:02d}.jpg'
        sheet.save(f, quality=82)
        print(f, file=sys.stderr)
    (out_dir / f'{name}.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'{len(gids)} 组 → {len(cells)} 格；定位不上 {len(lost)}：{lost[:20]}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd')
    ap.add_argument('--gids', default='')
    ap.add_argument('--name', default='s')
    ap.add_argument('--per', type=int, default=16)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'todo':
        todo(int(a.name), a.per)
    elif a.cmd == 'put':
        put(a.gids)
    elif a.cmd == 'land':
        land(a.apply)
    elif a.cmd == 'mtodo':
        mtodo(int(a.name), a.per)
    elif a.cmd == 'msheets':
        g = gidrange(a.gids)
        sites = {x['gid']: x for x in json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
        wc = {}
        need = {(l[0], l[1]) for l in (note_loc(sites[x], wc) for x in g) if l}
        for w, l in sorted(need):
            leaf_img(w, l)
        msheets(g, a.name, a.per)
    elif a.cmd == 'sheets':
        prefetch(gidrange(a.gids))
        sheets(gidrange(a.gids), a.name, a.per)
    else:
        {'build': build, 'pages': pages, 'match': match}[a.cmd]()


if __name__ == '__main__':
    main()
