#!/usr/bin/env python3
"""James Foote《路加福音讲义》(Lectures on the Gospel according to Luke) ABBYY → 讲次 markdown

底本与分工见 foote_raw/luke/PROVENANCE.md。主底本＝第 2 版三卷（Google 扫描、牛津藏本）：
    vol 1  lecturesongospe03footgoog   Lect. I–XL
    vol 2  lecturesongospe02footgoog   Lect. XLI–XC
    vol 3  lecturesongospe00footgoog   Lect. XCI–CXXXVII
第 3 版卷一（lecturesongospe01footgoog，Lect. I–LXVI）只当第二证人，不在这里抽。

版面信号（ABBYY 实测，第 1 卷）：
    正文        fs 9，段首 startIndent ≈ 78
    经文段      fs 8，悬挂缩进（startIndent < 0），紧跟在讲题 / 经文出处之后
    讲题        单行 `LECTURE n.`，居中
    经文出处    单行 `LUKE i. 1-4.`，紧跟讲题
    页眉        单行，页首：`8 LECTURE I.` / `LUKE I. 1-4. 9`
跨页续段：页内第一个正文段**没有 startIndent** → 接上一页最后一段（skill §3.1）。

用法：python3 scripts/extract_foote.py [--vol 1|2|3]
产物：foote_raw/luke/work/lectures.json + foote_raw/luke/work/md/NNN.md（检查用）
"""
import argparse
import gzip
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_abbyy import NS, IT_ON, IT_OFF, HYPH, BREAK, _line_text, _join_lines  # noqa: E402
from alexander_common import bare, collect_compounds, cleanup  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'foote_raw' / 'luke'
SRC = RAW / 'src'
WORK = RAW / 'work'
VOLS = {1: 'lecturesongospe03footgoog', 2: 'lecturesongospe02footgoog', 3: 'lecturesongospe00footgoog'}
FIRST_LECT = {1: 1, 2: 41, 3: 91}
LAST_LECT = {1: 40, 2: 90, 3: 137}

ROMAN_CH = '[IVXLCDMl1J]'
# 不开 re.I：脚注出处 `‡ Luke ii. 40, 52.` 与 recto 页眉同形，页眉的 LUKE 是全大写。
# lecture 有一处小写页眉（vol3 leaf 262 `2j8 lecture CIX.`），单独放宽
RUNHEAD = re.compile(r'^\W{0,3}(?:[\dIlSJjOo]{1,4}\s*)?\W{0,2}(?:[Ll][Ee][Cc][Tt][Uu]\w{1,3}|LECTUKE|LUKE|LUEE|LDKE)\b.{0,25}$')
PAGENUM = re.compile(r'^\W{0,2}\d{1,3}\W{0,2}$')
# OCR 变体实测：LECTUEE / LECTUSE / LECTXJEE；罗马数字尾 I 常读成 L（XIIL / XVUL）
# vol3 另有：C 读成 O（`LECTURE OXIII.`）、小写（`LECTURE cm.`）、讲题与序号粘连（`LECTUHEXCIL`）
LECT_HEAD = re.compile(r'^\W{0,2}(?:[Il]\s+)?L[A-Za-z]{2,3}T[A-Z]{2,4}\s*([IVXLCDMl1JUOonmcivx][IVXLCDMl1JUOonmcivxrY\s]*)[.,;:\-]?\W{0,2}$')
END_PUNCT = re.compile(r'[.!?:;"”’\'*)\]—]\W{0,2}$')
# 续段可能先有几个噪点（`\*, and his meat…`、`"jy^ *saw two…`）再接小写
LOWER_START = re.compile(r'^\W{0,10}[a-z]')
# 书帖签名 `VOL. II. K`（装订用，不是正文）
SIGNATURE = re.compile(r'^\W{0,2}VOL[.,]?\s*[IVXl1]+[.,]?\s*\S{0,3}\s*\S{0,3}$')
# 书帖签名的读花形态（`roL. n. D`、`VOL. H. *2* R`、`2 A`、`2g`、`c`）；注脚行末尾粘着的签名另剥（SIG_TAIL）
SIGNATURE2 = re.compile(r'^\W{0,2}(?:[VvYr][Oo0][Ll][.,]?\s*\S{1,4}[.,]?(?:\s+\S{1,3}){0,2}|\d?\s?[A-Za-z]{1,2})\W{0,2}$')
SIG_TAIL = re.compile(r'\s+VOL[.,]?\s*[IVXLl1]{1,4}[.,]?\s*\d?\s?[A-Z]{1,2}\.?\s*$')
END_VOL = re.compile(r'^\W{0,2}END\s+O[FP]\s+VOL', re.I)
# 经文出处本身也读花（`LUKK V. 27-32.` / `LtTKE Til. 18-23.`）：L 起头、短、带数字
REF_HEAD = re.compile(r'^\W{0,2}L\S{2,4}\s+[IVXLlTin1]{1,5}[.,]?\s*\S*\d.{0,12}$')


def roman_val(s):
    s = s.upper().replace('1', 'I').replace('J', 'I').replace('O', 'C').replace('Y', 'V').replace(' ', '')
    vals = dict(I=1, V=5, X=10, L=50, C=100, D=500, M=1000)
    tot = 0
    for i, ch in enumerate(s):
        v = vals.get(ch, 0)
        if i + 1 < len(s) and vals.get(s[i + 1], 0) > v:
            tot -= v
        else:
            tot += v
    return tot


def _mk(lines, par, fs, drop_line):
    text = _join_lines((_line_text(l) for l in lines), drop_line)
    if not bare(text).strip():
        return None
    si = par.get('startIndent')
    return {
        'text': text,
        'nlines': len(lines),
        'fs': fs,
        'si': int(si) if si not in (None, '') else None,
        't': int(lines[0].get('t') or 0),
        'b': int(lines[-1].get('b') or 0),
        'l': int(lines[0].get('l') or 0),
    }


def _par_fs(par):
    fs = Counter()
    for fm in par.iter(NS + 'formatting'):
        n = sum(len(c.text or '') for c in fm.iter(NS + 'charParams'))
        try:
            fs[round(float(fm.get('fs') or 0))] += n
        except ValueError:
            pass
    return fs.most_common(1)[0][0] if fs else 0


def note_lines(page_el):
    """页底注脚行（skill §2.6「版面层的硬信号」）：ABBYY 常把注脚那一行并进正文末段、或给它标成正文字号
    （第 45 讲全讲 9 条注脚都混进了正文句中）。字号靠不住，**行高**靠得住：注脚行高 47–61，正文行 78–90。
    只看正文字号的段（本来字号就小的段照旧整段归注区，不拆——多行注脚里带希腊字母的行偏高，拆了会把注脚劈开）：
    取这些段里最后一个正常行高的行之后、行高不到全页中位数 0.8 的行。"""
    pars = [par for blk in page_el.iter(NS + 'block') if blk.get('blockType') == 'Text'
            for par in blk.iter(NS + 'par')]
    pfs = Counter()
    for par in pars:
        pfs[_par_fs(par)] += len(list(par.iter(NS + 'line')))
    if not pfs:
        return set()
    body = pfs.most_common(1)[0][0]
    ls = [ln for par in pars if _par_fs(par) >= body for ln in par.iter(NS + 'line')]
    hs = sorted(int(ln.get('b') or 0) - int(ln.get('t') or 0) for ln in ls)
    if len(hs) < 8:
        return set()
    med = hs[len(hs) // 2]
    small = lambda ln: int(ln.get('b') or 0) - int(ln.get('t') or 0) < 0.8 * med
    last_normal = max((int(ln.get('t') or 0) for ln in ls if not small(ln)), default=0)
    cand = sorted((ln for ln in ls if small(ln) and int(ln.get('t') or 0) > last_normal),
                  key=lambda ln: int(ln.get('t') or 0))
    # 注脚不会以小写起头；打头的小写行是正文末行（页面歪斜时行高也会偏矮，132 讲 p.593）
    while cand and re.match(r'\s*[a-z]', _line_text(cand[0])):
        cand.pop(0)
    if not cand:
        return set()
    # 段末短行（讲末 `Amen.`、`for ever."`）行高也矮，但贴左边排；注脚居中或缩排、或以注号起头
    lefts = sorted(int(ln.get('l') or 0) for ln in ls if not small(ln))
    left = lefts[len(lefts) // 4] if lefts else 0
    first = cand[0]
    head = _line_text(first).lstrip()
    # 段首行缩进约 80，注脚居中（偏移 100 以上）；页底恰是新段首行时别当注脚
    if int(first.get('l') or 0) - left < 95 and not re.match(r'[*♦•†‡§|«»^]|[tfJ]\s+[A-Z1-9]', head):
        return set()
    return {id(ln) for ln in cand}


def par_info(par, drop_line, notes=frozenset()):
    """→ [par, ...]。讲题偶尔与经文出处被 ABBYY 归成同一段（vol2 leaf 245：
    `LECTURE LVII.` + `LUKE XI. 5-13.` 两行一段），这里按行拆开。
    页底注脚行（note_lines）从所在段里拆出来，单成一段、字号记 0（下游按「小字号段」归注区）。"""
    lines = list(par.iter(NS + 'line'))
    if not lines:
        return []
    nl = [l for l in lines if id(l) in notes]
    if nl and len(nl) < len(lines):
        # 段里混着注脚行：正文行照原段处理，注脚行合成一段（与整段都是注脚时的口径一致）
        body = [l for l in lines if id(l) not in notes]
        whole = par_info(par, drop_line)
        p = _mk(body, par, whole[0]['fs'] if whole else 0, drop_line)
        q = _mk(nl, {}, 0, drop_line)
        return [x for x in (p, q) if x]
    if nl:
        p = _mk(lines, par, 0, drop_line)      # 整段都是注脚（字号误读成正文的那类）
        return [p] if p else []
    fs = Counter()
    for fm in par.iter(NS + 'formatting'):
        n = sum(len(c.text or '') for c in fm.iter(NS + 'charParams'))
        try:
            fs[round(float(fm.get('fs') or 0))] += n
        except ValueError:
            pass
    fs = fs.most_common(1)[0][0] if fs else 0
    first = bare(_line_text(lines[0])).strip()
    if len(lines) > 1 and LECT_HEAD.match(first):
        out = [_mk([lines[0]], {}, fs + 2, None)]       # 讲题字号按大于正文计
        out += [_mk([l], {}, fs, None) for l in lines[1:2]]
        if len(lines) > 2:
            out.append(_mk(lines[2:], par, fs, drop_line))
        return [x for x in out if x]
    p = _mk(lines, par, fs, drop_line)
    return [p] if p else []


# 读花的页眉：`94 LECTUBB TIL` / `LUKB XI. fi^ift. 241` —— 一头是页码，另一头是 L 起头的短词
RUNHEAD_LOOSE = re.compile(r'^\W{0,3}\S{1,4}\s+\W{0,2}L(?![a-z]+\b)\S{2,7}\s+[IVXLCOTilnmUY1J\-]{1,7}\W{0,3}$'
                           r'|^\W{0,2}L(?![a-z]+\b)\S{2,5}\s+[IVXLTilnUY1J]{1,6}[.,]?\s*\S{1,9}\s+\S{1,4}\W{0,2}$')


# 页码前还夹着噪点 token（`J 14 LECTURE VIII.`、`1 ] 8 LECTURE XCIX.`、`t LUKE V. 12-15. 287`）
# L 打头的词不得是「L＋全小写」：脚注出处 `‡ Luke ii. 40, 52.` 与页眉同形，页眉的 LUKE/LECTURE 是大写
RUNHEAD_NOISY = re.compile(r'^(?:\S{1,2}\s+){1,2}(?:\S{1,4}\s+)?L(?![a-z]+\b)\S{2,6}\s+[IVXLCOTilnmUY1J\-]{1,7}[.,]?'
                           r'(?:\s*\S{1,9}\s+\S{1,4})?\W{0,3}$')


def drop_line(t):
    if len(t) > 40:
        return False
    if RUNHEAD_NOISY.match(t) and re.search(r'\d', t):
        return True
    return (bool(RUNHEAD.match(t)) and bool(re.search(r'\d', t))) or bool(RUNHEAD_LOOSE.match(t))


def load_pages(vol):
    pages = []
    with gzip.open(SRC / f'{VOLS[vol]}_abbyy.gz') as f:
        idx = 0
        for _, el in ET.iterparse(f):
            if el.tag != NS + 'page':
                continue
            pars = []
            notes = note_lines(el)
            for blk in el.iter(NS + 'block'):
                if blk.get('blockType') != 'Text':
                    continue
                for par in blk.iter(NS + 'par'):
                    pars += par_info(par, drop_line, notes)
            pars.sort(key=lambda p: p['t'])
            pages.append({'leaf': idx, 'pars': pars})
            idx += 1
            el.clear()
    return pages


def printed_numbers(vol):
    p = SRC / f'{VOLS[vol]}_page_numbers.json'
    if not p.exists():
        return {}
    d = json.load(open(p))
    return {x['leafNum']: x['pageNumber'] for x in d['pages'] if x.get('pageNumber')}


def strip_heads(pg):
    """剔页首 / 页尾的页眉与孤页码。页眉可能不在第一行（skill §3.2a），往后看三行。

    讲题后紧跟的经文出处 `LUKE III. 15-20.` 与 recto 页眉同形（都带数字），
    讲题之后的那一行一律不剔。
    """
    pars = pg['pars']
    keep = []
    for i, p in enumerate(pars):
        t = bare(p['text']).strip()
        edge = i < 3 or i >= len(pars) - 1
        after_head = keep and LECT_HEAD.match(bare(keep[-1]['text']).strip())
        if edge and not after_head and p['nlines'] == 1 \
                and (PAGENUM.match(t) or (drop_line(t) and not LECT_HEAD.match(t))):
            continue
        keep.append(p)
    return keep


def is_lecture_head(pars, i, body_fs):
    """讲题判定：单行 + 形状对 + 字号大于正文。

    讲题排 10–12 号（vol1 实测 37 处），页眉 8–9 号。页码掉到另一行的页眉会剩下
    一行孤立的 `LECTURE XIII.`（vol1 p.190），形状与讲题完全相同，只能靠字号分。
    讲题本身也会读花（`LEOTUEE XXXIII.` / `LECTXJEE XXXV.`），形状判据放宽，字号把关。
    """
    p = pars[i]
    if p['nlines'] != 1 or not LECT_HEAD.match(bare(p['text']).strip()):
        return False
    if p['fs'] > body_fs:
        return True
    # 后备：少数讲题排成正文字号（vol1 Lect. I、XXII）。看后文的结构——
    # 下一行是单行经文出处，再下一段是悬挂缩进的经文段。孤立页眉后面接的是正文。
    nxt = pars[i + 1:i + 3]
    return (len(nxt) == 2 and nxt[0]['nlines'] == 1 and REF_HEAD.match(bare(nxt[0]['text']).strip())
            and nxt[1]['si'] is not None and nxt[1]['si'] < 0)


def extract(vol):
    pages = load_pages(vol)
    pnum = printed_numbers(vol)
    compounds = collect_compounds([{'pars': pg['pars']} for pg in pages])
    lects = []
    cur = None
    mode = None            # 'ref' | 'passage' | 'body'
    expect = FIRST_LECT[vol]
    body_fs = Counter(p['fs'] for pg in pages for p in pg['pars'] for _ in range(p['nlines'])).most_common(1)[0][0]
    ended = False
    pending_prefix = ''
    for pg in pages:
        if ended:
            break
        page_no = pnum.get(pg['leaf'], '')
        first_body_on_page = True
        kept = strip_heads(pg)
        # 页脚脚注：本页最后一个正文字号段之后的小字段（脚注排到页底，skill §2.6）
        last_body = max((i for i, q in enumerate(kept) if q['fs'] >= body_fs and q['nlines'] > 1), default=-1)
        for i, p in enumerate(kept):
            t = bare(p['text']).strip()
            if END_VOL.match(t):
                ended = True
                break
            if is_lecture_head(kept, i, body_fs):
                n = roman_val(LECT_HEAD.match(t).group(1))
                if n != expect:
                    print(f'  ! vol{vol} leaf {pg["leaf"]}: 讲题读作 {t!r}={n}，按序应为 {expect}，取序号', file=sys.stderr)
                cur = {'n': expect, 'vol': vol, 'ref': '', 'passage': [], 'paras': [], 'notes': [],
                       'start_page': page_no}
                lects.append(cur)
                expect += 1
                mode = 'ref'
                continue
            if cur is None:
                continue            # 书前：扉页、序、目录；卷末书目广告（另行处理）
            # 讲题后紧跟的单行就是经文出处（本身也会读花：`LtTKE Til. 18-23.`）
            if mode == 'ref' and p['nlines'] == 1 and len(t) < 30:
                cur['ref'] = t
                mode = 'passage'
                continue
            small = p['fs'] < body_fs
            if mode in ('ref', 'passage') and small:
                cur['passage'].append(p['text'])
                mode = 'passage'
                continue
            if mode == 'body' and i > last_body >= 0 and p['fs'] < body_fs:
                if SIGNATURE.match(t) or SIGNATURE2.match(t):
                    continue
                cur['notes'].append({'text': SIG_TAIL.sub('', p['text']), 'page': page_no})
                continue
            # 没有字母的碎段（页顶一颗 `*`、一个引号）：不删（原书影像上确有墨点，留给后层取证），
            # 但也不让它单独占「本页第一段」——挂到下一段开头，续段判据照常看下一段
            if not re.search(r'[A-Za-z]', t):
                pending_prefix += p['text'] + ' '
                continue
            if pending_prefix:
                p = dict(p, text=pending_prefix + p['text'])
                pending_prefix = ''
            # 正文。续段两条判据（skill §3.1）：
            #   ① 页内第一段且无首行缩进（ABBYY 的版面信号）
            #   ② 上段末尾无句末标点 + 本段小写起头（两条同时成立；ABBYY 偶尔给续段也标了缩进）
            cont = bool(cur['paras']) and (
                (first_body_on_page and (p['si'] is None or p['si'] < 30))
                or (not END_PUNCT.search(bare(cur['paras'][-1]['text'])) and LOWER_START.match(bare(p['text']))))
            if not cont and cur['paras'] and LOWER_START.match(bare(p['text']).lstrip('*"\'^ ')) \
                    and not END_PUNCT.search(bare(cur['paras'][-1]['text'])):
                cont = True
            mode = 'body'
            if cont:
                cur['paras'][-1]['text'] += BREAK + p['text']
                cur['paras'][-1]['pages'].append(page_no)
            else:
                cur['paras'].append({'text': p['text'], 'pages': [page_no], 'fs': p['fs']})
            first_body_on_page = False
    if expect - 1 != LAST_LECT[vol]:
        print(f'  ! vol{vol}: 讲数 {expect - FIRST_LECT[vol]}，应到 {LAST_LECT[vol]}', file=sys.stderr)
    for L in lects:
        L['passage'] = cleanup(BREAK.join(L['passage']), compounds)
        for q in L['paras'] + L['notes']:
            q['text'] = cleanup(q['text'], compounds)
    return lects


def to_md(L):
    out = [f"## LECTURE {L['n']}", '', f"**{L['ref']}**", '', '> ' + L['passage'], '']
    for q in L['paras']:
        out.append(f"<!-- PAGE {q['pages'][0]} -->")
        out.append(q['text'])
        out.append('')
    if L.get('notes'):
        out += ['---', '']
        for q in L['notes']:
            out += [f"<!-- NOTE p.{q['page']} --> " + q['text'], '']
    return '\n'.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', type=int, choices=(1, 2, 3))
    a = ap.parse_args()
    vols = [a.vol] if a.vol else [1, 2, 3]
    WORK.mkdir(parents=True, exist_ok=True)
    (WORK / 'md').mkdir(exist_ok=True)
    jp = WORK / 'lectures.json'
    allL = json.load(open(jp)) if jp.exists() else {}
    for v in vols:
        Ls = extract(v)
        for L in Ls:
            allL[str(L['n'])] = L
            (WORK / 'md' / f"{L['n']:03d}.md").write_text(to_md(L))
        print(f'vol{v}: {len(Ls)} 讲')
    json.dump(allL, open(jp, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
