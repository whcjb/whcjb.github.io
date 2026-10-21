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
import collections
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


def _ctxw(text):
    return [re.sub(r'[^\w•]', '', w).lower() for w in plain(text).split()]


def align(order=None):
    """→ {(slug, 组序): (gid, 片段)}，与未对上的清单。

    同串候选在 ±400 窗口里按上下文（前后各三词）打分挑，不再取最近的——单个 〈◊〉 这种
    处处都有的串，取最近会抢走后面的位子、一路错下去（3-1 曾错位四组）。
    片段：整处为 None；一处缺字被经文分节或旁注从中切开（2:8 节首 `the•,` 在上一节、
    3:1 `••wes. 〈◊〉` 中间夹旁注）时，md 里只是 site 的一截：('w', i, j, n) 按词取第 i..j 词
    （共 n 词），('c', 前缀) 按字取后缀。"""
    sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    order = order or json.loads((RAW / 'order.json').read_text())
    streams = {'main': [s for s in sites if s['stream'] == 'main'],
               'note': [s for s in sites if s['stream'] == 'note']}
    ptr = {'main': 0, 'note': 0}
    used = collections.Counter()
    pend = {'main': None, 'note': None}
    pend_tw = None
    amap, miss = {}, []
    for slug in order:
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        flat = re.sub(r'<[^>]+>', lambda x: ' ' * len(x.group(0)), md)     # 等长抹标签，位置与 gap_groups 一致
        for n, (a, b, s, isnote) in enumerate(gap_groups(md)):
            key = 'note' if isnote else 'main'
            seq = streams[key]
            want = plain(s)
            ww = want.split()
            L = _ctxw(flat[max(0, a - 300):a])[-3:]
            R = _ctxw(flat[b:b + 300])[:3]
            def ctx(site):
                sl = _ctxw(' '.join(site['left'][-3:]))
                sr = _ctxw(' '.join(site['right'][:3]))
                return sum(x == y for x, y in zip(L[::-1], sl[::-1])), sum(x == y for x, y in zip(R, sr))
            best = None
            # ① 同串：原规则（先前后最近）；只有不含字母的串（〈◊〉、•• 之类处处都有）才按上下文挑
            exact = []
            for w in range(0, 400):
                for i in ((ptr[key] + w,) if w == 0 else (ptr[key] + w, ptr[key] - w)):
                    if 0 <= i < len(seq) and not used[seq[i]['gid']] and plain(seq[i]['tcp']) == want:
                        exact.append(i)
            if exact:
                best = (None, exact[0], None)
                if not re.search(r'[A-Za-z]', want) and sum(ctx(seq[exact[0]])) == 0:
                    best = None         # 〈◊〉 之类、最近那处上下文全不合：先看是不是近旁某处被切开的一截
            if best is None and pend.get(key):
                # 上一组是某处的前一截：这一组若正好是剩下那截，直接接上
                pg, pj, ptw = pend[key]
                if ptw[pj:pj + len(ww)] == ww:
                    best = (None, None, ('w', pj, pj + len(ww), len(ptw)), pg)
            pend[key] = None
            if best is None and (re.search(r'[A-Za-z]', want) or not exact):
                # ② 被分节/旁注切开的一截：外侧上下文要对上
                for i in range(max(0, ptr[key] - 400), min(len(seq), ptr[key] + 400)):
                    site = seq[i]
                    tw = plain(site['tcp']).split()
                    part = None
                    for k in range(len(tw) - len(ww) + 1):
                        if tw[k:k + len(ww)] == ww and len(tw) > len(ww):
                            part = ('w', k, k + len(ww), len(tw))
                            break
                    t = plain(site['tcp'])
                    if part is None and len(ww) == 1 and ' ' not in t and t.endswith(want) and t != want:
                        part = ('c', t[:-len(want)])
                    if part is None:
                        continue
                    cl, cr = ctx(site)
                    left_ok = part[0] == 'w' and part[1] == 0 and cl >= 3
                    right_ok = (part[0] == 'c' or part[2] == part[3]) and cr >= 3
                    if left_ok or right_ok:
                        best = (None, i, part)
                        break
            if best is None and exact:
                best = (None, exact[0], None)
            if best is None:
                miss.append((slug, n, s))
                continue
            _, hit, part = best[:3]
            g = best[3] if len(best) > 3 else seq[hit]['gid']
            if part and part[0] == 'w' and part[2] < part[3]:
                pend[key] = (g, part[2], plain(seq[hit]['tcp']).split() if hit is not None else pend_tw)
            used[g] += 1
            amap[(slug, n)] = (g, part)
            if part is None:
                ptr[key] = hit + 1
    return amap, miss


def _slice(v, part):
    if part is None:
        return v
    if part[0] == 'c':
        return v[len(part[1]):] if v.startswith(part[1]) else None
    _, i, j, n = part
    vw = v.split()
    if len(vw) == n:
        return ' '.join(vw[i:j])
    if i == 0:                  # 词数对不上：只认「前一截 / 后一截」两分
        return ' '.join(vw[:j]) if j < n else v
    if j == n:                  # 后一截：前面几词按一对一让掉
        return ' '.join(vw[i:]) if len(vw) > i else None
    return None


CONJ_L, CONJ_R = '⟦', '⟧'


def apply(slug, md, amap, dec):
    """把判读落进一篇。证人读出的直接替换；推补包 ⟦⟧。原串里的斜体星号尽量保留在外侧。"""
    edits = []
    for n, (a, b, s, _) in enumerate(gap_groups(md)):
        hit = amap.get((slug, n))
        if hit is None or hit[0] not in dec:
            continue
        v, kind = dec[hit[0]]
        v = _slice(v, hit[1])
        if v is None:
            continue
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
        # ⁀ = 与相邻词连写（缺口在词中间、TCP 却分成两词：`Scriptur 〈…〉`、`〈◊〉 ip• tentem`）
        if re.match(r'^\**⁀', t):
            t = t.replace('⁀', '', 1)
            while a > 0 and md[a - 1] == ' ':
                a -= 1
        if re.search(r'⁀\**$', t):
            t = t[::-1].replace('⁀', '', 1)[::-1]
            while b < len(md) and md[b] == ' ':
                b += 1
        md = md[:a] + t + md[b:]
        if not t:     # 删掉的记号：吃掉多出来的空格
            md = md[:a].rstrip(' ') + ' ' + md[a:].lstrip(' ') if a < len(md) else md
    return md, len(edits)


def tcp_fixes():
    """tcp_fixes.tsv：TCP 录入错误（非缺字），对照 1633 原图确认后的改正。原串须在落完缺字的全书里唯一。"""
    return [tuple(ln.split('\t')[:2]) for ln in (RAW / 'tcp_fixes.tsv').read_text(encoding='utf-8').splitlines()
            if ln and not ln.startswith('#')] if (RAW / 'tcp_fixes.tsv').exists() else []


_CACHE = {}


def load(slug):
    if 'amap' not in _CACHE:
        _CACHE['amap'], _CACHE['miss'] = align()
        _CACHE['dec'] = decisions()
    md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    md = apply(slug, md, _CACHE['amap'], _CACHE['dec'])[0]
    for a, b in tcp_fixes():
        md = md.replace(a, b)
    return md


def check_fixes(texts):
    """每条 tcp_fix 的原串在全书恰好出现一次，否则报出（出现 0 次＝没落上，>1＝会误改）。"""
    bad = []
    for a, b in tcp_fixes():
        n = sum(t.count(a) for t in texts)
        if n != 1:
            bad.append((a, n))
    return bad


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
    outs = [apply(sl, (SRC / f'{sl}.md').read_text(encoding='utf-8'), amap, dec)[0] for sl in order]
    for a, n in check_fixes(outs):
        print(f'⚠️ tcp_fix 原串出现 {n} 次（须为 1）：{a}', file=sys.stderr)
    print(f'tcp_fixes {len(tcp_fixes())} 条', file=sys.stderr)
