"""琼斯《约翰二书、三书简释》共用：读抽取产物、列缺字组、落判读。

骨架照搬 attersoll_common.py，只是一部底本出两卷书（2john / 3john），路径按卷取：
    jones_raw/src/A04619.xml          底本（两卷共用）
    jones_raw/<book>/en_chapters/     抽取产物
    jones_raw/<book>/gap_review.tsv   判读表（格式同阿特索尔，见 attersoll_common.py 文首）

缺字组编号 gid = 本卷抽取产物（order.json 的篇序）里第几个缺字词组，相邻的缺字词并成一组，
页边旁注与正文分开并组。gap_sites.json 记下每组的原串与上下文，落盘时逐组核对原串，对不上就不落。
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'jones_raw'
SRC_XML = BASE / 'src' / 'A04619.xml'
BOOKS = ('2john', '3john')

TOK = re.compile(r'•+|〈◊〉|〈…〉|〈Greek〉|▪')
RE_WORD = re.compile(r'[^\s<>]+')
CONJ_L, CONJ_R = '⟦', '⟧'


def raw(book):
    return BASE / book


def order(book):
    return json.loads((raw(book) / 'order.json').read_text())


def read_src(book, slug):
    return (raw(book) / 'en_chapters' / f'{slug}.md').read_text(encoding='utf-8')


def gap_groups(md):
    """md 里的缺字词组：[(起, 止, 原串, 是否旁注)]。"""
    margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="jw-margin[^"]*"[^>]*>.*?</span>', md, re.S)]

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


def tsv(book, name):
    f = raw(book) / name
    if not f.exists():
        return []
    return [ln.rstrip('\n').split('\t') for ln in f.read_text(encoding='utf-8').splitlines()
            if ln and ln[0].isdigit()]


def decisions(book):
    """gid → (读法, 类别)。类别：w=看图读出 c=推补（用户同意）。? 与未判的不落。"""
    d = {}
    for f in tsv(book, 'gap_review.tsv'):
        g, v = int(f[0]), f[1]
        if v in ('?', '') or v.startswith('P:'):
            continue
        d[g] = ('' if v == '∅' else v, 'w')
    for f in tsv(book, 'gap_approved.tsv'):
        d[int(f[0])] = (f[1], 'c')
    return d


def apply(md, groups_gid, dec, sites):
    """把判读落进一篇。groups_gid：本篇各组的 gid。原串与 gap_sites 不合的组不落。"""
    edits = []
    for (a, b, s, _), g in zip(gap_groups(md), groups_gid):
        if g not in dec or sites[g]['tcp'] != s:
            continue
        v, kind = dec[g]
        if '*' in v:                     # 读法自带斜体标记：整组照写
            edits.append((a, b, f'{CONJ_L}{v}{CONJ_R}' if kind == 'c' else v))
            continue
        lead = re.match(r'^\**', s).group(0)
        trail = re.search(r'\**$', s).group(0)
        inner = v
        if kind == 'c' and inner:
            m = re.match(r'^(.*?)([.,;:!?)]*)$', inner)
            inner = f'{CONJ_L}{m.group(1)}{CONJ_R}{m.group(2)}'
        edits.append((a, b, f'{lead}{inner}{trail}' if inner else ''))
    for a, b, t in sorted(edits, reverse=True):
        if t and re.match(r' [.,;:?!)]', md[b:b + 2]):
            b += 1
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
    return md, len(edits)


_CACHE = {}


def _index(book):
    if book not in _CACHE:
        f = raw(book) / 'gap_sites.json'
        sites = json.loads(f.read_text(encoding='utf-8')) if f.exists() else []
        by = {}
        for s in sites:
            by.setdefault(s['slug'], []).append(s['gid'])
        _CACHE[book] = dict(gid=by, sites={s['gid']: s for s in sites}, dec=decisions(book))
    return _CACHE[book]


def load(book, slug):
    c = _index(book)
    md = read_src(book, slug)
    return apply(md, c['gid'].get(slug, []), c['dec'], c['sites'])[0]
