"""泰勒《提多书注释》共用：读抽取产物、列缺字组、落判读。

缺字组编号 gid = 抽取产物（order.json 的篇序）里第几个缺字词组，相邻的缺字词并成一组，
页边旁注与正文分开并组。抽取不重排原书顺序，所以编号即文档顺序；gap_sites.json 记下每组的
原串与上下文，落盘时逐组核对原串，对不上就不落（抽取改动后编号漂移会被这道闸拦住）。

判读来源（后者覆盖前者）：
  gap_review.tsv   逐条看 1612 原版影像（bim）的判读：gid / 读法 / 依据 / 备注
                   读法：词（原书拼法）；∅ = 原书此处无字；? = 判不了；P:xx = 推断（待用户同意）
                   读法以 ⁀ 起头/收尾 = 与左/右邻词连写（缺字是标点或半个词）
                   读法里带 `*` 的整组照写（用于组内斜体边界与 TCP 原串不同），否则原串首尾的 `*` 保留在外侧
  gap_approved.tsv 用户同意的推断（gid / 读法），落成 ⟦…⟧ 推补
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'taylor_raw' / 'titus'
SRC = RAW / 'en_chapters'

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
RE_WORD = re.compile(r'[^\s<>]+')
CONJ_L, CONJ_R = '⟦', '⟧'


def order():
    return json.loads((RAW / 'order.json').read_text())


def read_src(slug):
    return (SRC / f'{slug}.md').read_text(encoding='utf-8')


def gap_groups(md):
    """md 里的缺字词组：[(起, 止, 原串, 是否旁注)]。"""
    margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="ty-margin"[^>]*>.*?</span>', md, re.S)]

    def in_margin(p):
        return any(a <= p < b for a, b in margins)
    flat = re.sub(r'<[^>]+>', lambda x: ' ' * len(x.group(0)), md)
    words = [(m.start(), m.end(), m.group(0)) for m in RE_WORD.finditer(flat)]
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
        groups.append((a, b, md[a:b], in_margin(a)))
        k = j + 1
    return groups


def flat_words(md):
    """去标签的词序列（上下文用）。"""
    return re.sub(r'<[^>]+>', ' ', md).replace('*', '').split()


def _tsv(name):
    f = RAW / name
    if not f.exists():
        return []
    return [ln.rstrip('\n').split('\t') for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and ln[0].isdigit()]


def decisions():
    """gid → (读法, 类别)。类别：w=看图读出 c=推补（用户同意）。? 与未判的不落。"""
    d = {}
    for f in _tsv('gap_review.tsv'):
        g, v = int(f[0]), f[1]
        if v in ('?', '') or v.startswith('P:'):
            continue
        d[g] = ('' if v == '∅' else v, 'w')
    for f in _tsv('gap_approved.tsv'):
        d[int(f[0])] = (f[1], 'c')
    return d


def apply(md, groups_gid, dec, sites):
    """把判读落进一篇。groups_gid：本篇各组的 gid。原串与 gap_sites 不合的组不落。"""
    edits = []
    for (a, b, s, _), g in zip(gap_groups(md), groups_gid):
        if g not in dec or sites[g]['tcp'] != s:
            continue
        v, kind = dec[g]
        if '*' in v:                     # 读法自带斜体标记（组内斜体边界与原串不同）：整组照写
            edits.append((a, b, f'{CONJ_L}{v}{CONJ_R}' if kind == 'c' else v))
            continue
        lead = re.match(r'^\**', s).group(0)
        trail = re.search(r'\**$', s).group(0)
        inner = v
        if kind == 'c' and inner:
            m = re.match(r'^(.*?)([.,;:!?)]*)$', inner)
            inner = f'{CONJ_L}{m.group(1)}{CONJ_R}{m.group(2)}'
        mid = s[len(lead):len(s) - len(trail)] if trail else s[len(lead):]
        if '*' in mid:
            sw, vw = s.split(' '), inner.split(' ')
            if len(sw) == len(vw):
                parts = []
                for x, y in zip(sw, vw):
                    xl = re.match(r'^\**', x).group(0)
                    xt = re.search(r'\**$', x).group(0)
                    parts.append(f'{xl}{y}{xt}')
                edits.append((a, b, ' '.join(parts)))
                continue
            edits.append((a, b, f'{lead}{inner}{"*" * mid.count("*")}{trail}' if inner else '*' * mid.count('*')))
            continue
        edits.append((a, b, f'{lead}{inner}{trail}' if inner else ''))
    for a, b, t in sorted(edits, reverse=True):
        # TCP 在缺字记号两侧留了空格：`labour 〈…〉 .` 落字后不留 `trauaile .`
        if t and re.match(r' [.,;:?!)]', md[b:b + 2]):
            b += 1
        if re.match(r'^\**⁀', t):           # ⁀ = 与左邻词连写（缺的是标点、词的前半截）
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
    return md, len(edits)


def tcp_fixes():
    """tcp_fixes.tsv：TCP 录入错误（非缺字），对照 1612 原图确认后的改正；原串须在全书唯一。"""
    f = RAW / 'tcp_fixes.tsv'
    return [tuple(ln.split('\t')[:2]) for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and not ln.startswith('#')] if f.exists() else []


_CACHE = {}


def _index():
    if 'gid' not in _CACHE:
        sites = json.loads((RAW / 'gap_sites.json').read_text(encoding='utf-8'))
        by = {}
        for s in sites:
            by.setdefault(s['slug'], []).append(s['gid'])
        _CACHE.update(gid=by, sites={s['gid']: s for s in sites}, dec=decisions())
    return _CACHE


def load(slug):
    c = _index()
    md = read_src(slug)
    md = apply(md, c['gid'].get(slug, []), c['dec'], c['sites'])[0]
    for a, b in tcp_fixes():
        md = md.replace(a, b)
    return md
