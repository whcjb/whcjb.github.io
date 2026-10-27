"""詹金《犹大书讲解》共用：读抽取产物并落缺字判读。

判读来源（gid = jenkyn_witness.py gap_sites.json 的编号），后者覆盖前者：
  1. witness_locs.json 的 auto（A/B 档：1865 同位读出、过真词闸与邻词闸、合残字）
  2. gap_review.tsv     逐条看图（读法；P:xx = 推断，待用户同意；? = 判不了；∅ = 原书此处无字）
  3. gap_approved.tsv   用户同意按推补发布的 P: 条目（gid 列表），正文写 ⟦…⟧
未同意的 P: 与 ? 留记号（页面标红）。

落点：抽取产物里每个缺字记号前嵌着编号 \\ue000N\\ue001（extract_jenkyn.load_roots 编的 gn）；
一处缺字词组记着它含哪些 gn，按 gn 找到 md 里那几个词，整词替换。不靠串比对，所以不会错位。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_jenkyn import ID_L, ID_R  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'jenkyn_raw' / 'jude'
SRC = RAW / 'en_chapters'

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
RE_ID = re.compile(f'{ID_L}(\\d+){ID_R}')
CONJ_L, CONJ_R = '⟦', '⟧'


def _tsv(name):
    f = RAW / name
    if not f.exists():
        return []
    return [ln.rstrip('\n').split('\t') for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and ln[0].isdigit()]


def sites():
    return json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))


def decisions():
    """gid → (读法, 类别)。类别：w=证人读出 c=推补（已获同意）。"""
    locs = {r['gid']: r for r in json.loads((RAW / 'witness_locs.json').read_text(encoding='utf-8'))}
    d = {}
    for g, r in locs.items():
        if r.get('tier') in ('A', 'B') and r.get('auto'):
            d[g] = r['auto']
    for f in _tsv('gap_review.tsv'):
        d[int(f[0])] = f[1]
    ok = {int(f[0]) for f in _tsv('gap_approved.tsv')}
    out = {}
    for g, v in d.items():
        if v in ('?', ''):
            continue
        if v == '∅':
            out[g] = ('', 'w')
        elif v.startswith('P:'):
            if g in ok:
                out[g] = (v[2:], 'c')
        else:
            out[g] = (v, 'w')
    return out


def word_span(md, gns):
    """gn 列表 → md 里覆盖这几个缺字的整词区间 (a, b)；中间夹标签（页码、旁注）的返回 None。"""
    pa = md.find(f'{ID_L}{gns[0]}{ID_R}')
    pb = md.find(f'{ID_L}{gns[-1]}{ID_R}')
    if pa < 0 or pb < 0:
        return None
    a = pa
    while a > 0 and not md[a - 1].isspace() and md[a - 1] != '>':
        a -= 1
    b = pb
    while b < len(md) and not md[b].isspace() and md[b] != '<':
        b += 1
    if '<' in md[a:b] or '>' in md[a:b]:
        return None
    return a, b


def replace_group(s, inner):
    """原串 s（含斜体星号）→ 读法 inner，星号尽量留在外侧（同 adams_common.apply）。"""
    lead = re.match(r'^\**', s).group(0)
    trail = re.search(r'\**$', s).group(0)
    mid = s[len(lead):len(s) - len(trail)] if trail else s[len(lead):]
    if '*' in mid:
        sw, vw = s.split(' '), inner.split(' ')
        if len(sw) == len(vw):
            return ' '.join(re.match(r'^\**', x).group(0) + y + re.search(r'\**$', x).group(0)
                            for x, y in zip(sw, vw))
        stars = mid.count('*')
        return f'{lead}{inner}{"*" * stars}{trail}' if inner else '*' * stars
    return f'{lead}{inner}{trail}' if inner else ''


def apply(md, dec, by_gn):
    """把判读落进一篇 → (md, 落下组数, 落不下的 gid)。"""
    edits, bad = [], []
    present = {int(x) for x in RE_ID.findall(md)}
    done = set()
    for gn in sorted(present):
        site = by_gn.get(gn)
        if site is None or site['gid'] in done:
            continue
        done.add(site['gid'])
        if site['gid'] not in dec:
            continue
        sp = word_span(md, site['gns'])
        if sp is None:
            bad.append(site['gid'])
            continue
        v, kind = dec[site['gid']]
        if kind == 'c' and v:
            m = re.match(r'^(.*?)([.,;:!?)]*)$', v)
            v = f'{CONJ_L}{m.group(1)}{CONJ_R}{m.group(2)}'
        a, b = sp
        edits.append((a, b, replace_group(RE_ID.sub('', md[a:b]), v)))
    for a, b, t in sorted(edits, reverse=True):
        if re.match(r'^\**⁀', t):           # ⁀ = 与左邻词连写
            t = t.replace('⁀', '', 1)
            while a > 0 and md[a - 1] == ' ':
                a -= 1
        if re.search(r'⁀\**$', t):          # 与右邻词连写
            t = t[::-1].replace('⁀', '', 1)[::-1]
            while b < len(md) and md[b] == ' ':
                b += 1
        md = md[:a] + t + md[b:]
        if not t:
            md = md[:a].rstrip(' ') + ' ' + md[a:].lstrip(' ')
    return md, len(edits), bad


def tcp_fixes():
    f = RAW / 'tcp_fixes.tsv'
    if not f.exists():
        return []
    return [tuple(ln.split('\t')[:2]) for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and not ln.startswith('#')]


_CACHE = {}


def load(slug):
    if 'dec' not in _CACHE:
        _CACHE['dec'] = decisions()
        _CACHE['by_gn'] = {gn: s for s in sites() for gn in s['gns']}
    md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    md = apply(md, _CACHE['dec'], _CACHE['by_gn'])[0]
    md = RE_ID.sub('', md)
    for a, b in tcp_fixes():
        md = md.replace(a, b)
    return md


if __name__ == '__main__':
    dec = decisions()
    by_gn = {gn: s for s in sites() for gn in s['gns']}
    order = json.loads((RAW / 'order.json').read_text())['order']
    tot, left, bads, texts = 0, 0, [], []
    for slug in order:
        md = (SRC / f'{slug}.md').read_text(encoding='utf-8')
        out, n, bad = apply(md, dec, by_gn)
        out = RE_ID.sub('', out)
        texts.append(out)
        tot += n
        bads += bad
        left += len(TOK.findall(out))
        if out.count('*') % 2 != RE_ID.sub('', md).count('*') % 2:
            print(f'⚠️ {slug}: 星号奇偶变了', file=sys.stderr)
    print(f'判读表 {len(dec)}（推补 {sum(1 for v in dec.values() if v[1] == "c")}）；落下 {tot} 组；'
          f'落不下 {len(bads)} {bads[:20]}；剩余记号 {left}', file=sys.stderr)
    for a, b in tcp_fixes():
        n = sum(t.count(a) for t in texts)
        if n != 1:
            print(f'⚠️ tcp_fix 原串出现 {n} 次（须为 1）：{a}', file=sys.stderr)
