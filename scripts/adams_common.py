"""亚当斯《彼得后书注释》共用：读抽取产物并落缺字判读。

判读来源（gid = adams_witness.py gap_sites.json 的编号），后者覆盖前者：
  1. witness_locs.json 的 auto（A/B 档：1862 同位读出、合残字、本书语料词形；抽样 329 条看图核对）
  2. gap_review.tsv        逐条看图（读法；P:xx = 推断；? = 判不了）
  3. gap_recheck.tsv       推断条目对照 1633 原图宽裁复核（= 维持上次；∅ = 原图无缺词，删记号）
  4. gap_promote_r1862.tsv 推断条目里 1862 同位读出同一词的，按证人读数落（用户 2026-10-21 同意）
最后仍是 P: 的 → 编者推补，正文写 ⟦…⟧（用户 2026-10-21 同意先以推补发布）；? 与未定位的留记号。

落点：抽取产物里的缺字词按文档顺序与 gap_sites 对齐（同串比对，窗口内找；卷二开头的 conclusion
被挪到 2-10 篇，顺序与 TEI 不完全一致，所以不能严格按序号）。对不上的报出来，不落。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'adams_raw' / '2peter'
SRC = RAW / 'en_chapters'

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
RE_WORD = re.compile(r'[^\s<>]+')


def _tsv(name):
    f = RAW / name
    if not f.exists():
        return []
    return [ln.rstrip('\n').split('\t') for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and ln[0].isdigit()]


def decisions():
    """gid → (读法, 类别)。类别：w=证人读出 c=推补 None=不落。"""
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    d = {}
    for g, r in locs.items():
        if r.get('tier') in ('A', 'B') and r.get('auto'):
            d[g] = (r['auto'], 'w')
    for f in _tsv('gap_review.tsv'):
        g, v = int(f[0]), f[1]
        d[g] = (v, 'w')
    for f in _tsv('gap_recheck.tsv'):
        g, v = int(f[0]), f[1]
        if v == '=':
            continue
        d[g] = (v, 'w')
    for f in _tsv('gap_promote_r1862.tsv'):
        d[int(f[0])] = (f[1], 'w')
    out = {}
    for g, (v, _) in d.items():
        if v == '?' or v == '':
            continue
        if v == '∅':
            out[g] = ('', 'w')
        elif v.startswith('P:'):
            out[g] = (v[2:], 'c')
        else:
            out[g] = (v, 'w')
    return out


def plain(s):
    return s.replace('*', '')


def gap_groups(md):
    """md 里的缺字词组：[(起, 止, 原串, 是否旁注)]。相邻的缺字词并成一组（同 adams_witness.gaps）。"""
    margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="ad-margin"[^>]*>.*?</span>', md, re.S)]

    def in_margin(p):
        return any(a <= p < b for a, b in margins)
    words = []
    for m in RE_WORD.finditer(re.sub(r'<[^>]+>', lambda x: ' ' * len(x.group(0)), md)):
        words.append((m.start(), m.end(), m.group(0)))
    groups = []
    k = 0
    while k < len(words):
        if not TOK.search(words[k][2]):
            k += 1
            continue
        j = k
        while j + 1 < len(words) and TOK.search(words[j + 1][2]) \
                and in_margin(words[j + 1][0]) == in_margin(words[k][0]):
            j += 1
        a, b = words[k][0], words[j][1]
        groups.append((a, b, ' '.join(w[2] for w in words[k:j + 1]), in_margin(a)))
        k = j + 1
    return groups


def align(order=None):
    """→ {(slug, 组序): gid}，与未对上的清单。"""
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    order = order or json.loads((RAW / 'order.json').read_text())
    streams = {'main': [s for s in sites if s['stream'] == 'main'],
               'note': [s for s in sites if s['stream'] == 'note']}
    ptr = {'main': 0, 'note': 0}
    used = set()
    amap, miss = {}, []
    for slug in order:
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        for n, (a, b, s, isnote) in enumerate(gap_groups(md)):
            key = 'note' if isnote else 'main'
            seq = streams[key]
            want = plain(s)
            hit = None
            for w in range(0, 400):
                for i in (ptr[key] + w, ptr[key] - w):
                    if 0 <= i < len(seq) and seq[i]['gid'] not in used and plain(seq[i]['tcp']) == want:
                        hit = i
                        break
                if hit is not None:
                    break
            if hit is None:
                miss.append((slug, n, s))
                continue
            used.add(seq[hit]['gid'])
            amap[(slug, n)] = seq[hit]['gid']
            ptr[key] = hit + 1
    return amap, miss


CONJ_L, CONJ_R = '⟦', '⟧'


def apply(slug, md, amap, dec):
    """把判读落进一篇。证人读出的直接替换；推补包 ⟦⟧。原串里的斜体星号尽量保留在外侧。"""
    edits = []
    for n, (a, b, s, _) in enumerate(gap_groups(md)):
        g = amap.get((slug, n))
        if g is None or g not in dec:
            continue
        v, kind = dec[g]
        lead = re.match(r'^\**', s).group(0)
        trail = re.search(r'\**$', s).group(0)
        inner = v
        if kind == 'c' and inner:
            # 推补：标点留在括号外
            m = re.match(r'^(.*?)([.,;:!?)]*)$', inner)
            inner = f'{CONJ_L}{m.group(1)}{CONJ_R}{m.group(2)}'
        mid = s[len(lead):len(s) - len(trail)] if trail else s[len(lead):]
        if '*' in mid:
            # 组内有斜体边界（`Domin••,* •ill`）：词数相同就逐词替换、各词保留自己的星号；
            # 不同就把组内星号接在读法后面——宁可边界挪一个词，不让星号配对乱掉
            sw, vw = s.split(' '), inner.split(' ')
            if len(sw) == len(vw):
                parts = []
                for x, y in zip(sw, vw):
                    xl = re.match(r'^\**', x).group(0)
                    xt = re.search(r'\**$', x).group(0)
                    parts.append(f'{xl}{y}{xt}')
                edits.append((a, b, ' '.join(parts)))
                continue
            stars = mid.count('*')
            edits.append((a, b, f'{lead}{inner}{"*" * stars}{trail}' if inner else '*' * stars))
            continue
        edits.append((a, b, f'{lead}{inner}{trail}' if inner else ''))
    for a, b, t in sorted(edits, reverse=True):
        md = md[:a] + t + md[b:]
        if not t:     # 删掉的记号：吃掉多出来的空格
            md = md[:a].rstrip(' ') + ' ' + md[a:].lstrip(' ') if a < len(md) else md
    return md, len(edits)


_CACHE = {}


def load(slug):
    if 'amap' not in _CACHE:
        _CACHE['amap'], _CACHE['miss'] = align()
        _CACHE['dec'] = decisions()
    md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    return apply(slug, md, _CACHE['amap'], _CACHE['dec'])[0]


if __name__ == '__main__':
    amap, miss = align()
    dec = decisions()
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    print(f'缺字组 对上 {len(amap)} / 未对上 {len(miss)}；判读表 {len(dec)}（推补 {sum(1 for v in dec.values() if v[1]=="c")}）',
          file=sys.stderr)
    for m in miss[:15]:
        print('  未对上', m, file=sys.stderr)
    order = json.loads((RAW / 'order.json').read_text())
    left = 0
    tot = 0
    for slug in order:
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        out, n = apply(slug, md, amap, dec)
        tot += n
        left += len(TOK.findall(out))
        if out.replace('⟦', '').replace('⟧', '').count('*') % 2 != md.count('*') % 2:
            print(f'⚠️ {slug}: 星号奇偶变了', file=sys.stderr)
    print(f'落下 {tot} 组；剩余记号 {left}', file=sys.stderr)
