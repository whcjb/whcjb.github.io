#!/usr/bin/env python3
"""卡里尔缺部 OCR 第 ③ 层：短词上下文纠错（真词误读）。

    /usr/bin/python3 scripts/caryl_ocr_ctx.py 9            # 试跑：改动计数与样例
    /usr/bin/python3 scripts/caryl_ocr_ctx.py 9 --apply    # fixed/ 就地改，改动记 ctx.tsv

抽读第 9 部印本第 569 页（2026-11-24）：一页 16 处错里约 10 处是斜体虚词读成了**别的真词**——If→Is（三次）、
or→er、of→ef、the→ibe/toe、saw→sam、was→mas。第 ①② 层只查非词，碰不到它们。
语料自证：TCP 卡里尔 8 部 250 万词（同一作者、同一批印工）统计二元搭配。只动 ≤ 4 字母的词：
候选 = 第 ① 层混淆对改一处（caryl_ocr_fix.step）得到的、本书出现 ≥ 100 次的词；
守卫：候选与前词、与后词两组搭配在语料里**都出现过**，且「前词·候选」「候选·后词」两项概率之积 ≥ 原词的 50 倍；
原词本身是本书常见词（≥ 200 次）的一概不碰（nor→not、may→way、fell→fall 在 2000 倍门槛下仍会改错）；
单字母不碰；前后词须是本书 ≥ 20 次的完整词（ly、hill 这类残片做邻词时统计不可靠）。
专名、旁注、标签、经文框出处行不碰（同 caryl_ocr_fix.RE_PROTECT）。
"""
import argparse
import collections
import glob
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_fix as fx  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
RE_W = re.compile(r"[A-Za-z]+")


def corpus():
    uni, bi = collections.Counter(), collections.Counter()
    for f in glob.glob(str(fx.TCP_MD / '*.md')):
        t = re.sub(r'<span class="cy-margin"[^>]*>.*?</span>|<[^>]+>|\{:[^}]*\}', ' ', Path(f).read_text(encoding='utf-8'))
        t = t.replace('*', '')
        for sent in re.split(r'[.;:?!()\[\]]', t):
            ws = [w.lower() for w in RE_W.findall(sent)]
            uni.update(ws)
            bi.update(zip(ws, ws[1:]))
    return uni, bi


UNI, BI = corpus()
N = sum(UNI.values())


def p_bi(a, b):
    return (BI.get((a, b), 0) + 0.01) / (UNI.get(a, 0) + 1)


def cands(t):
    out = set()
    for v in fx.step({t}) | fx.step({t.lower()}):
        lv = v.lower()
        if lv != t.lower() and UNI.get(lv, 0) >= 100:
            out.add(lv)
    return out


RE_FIRST = re.compile(r'(</div>\s*\n\n(?:<div class="commentary-anchor"[^>]*></div>\s*\n\n)*(?:<span class="cy-pb"[^>]*></span>)*)'
                      r'([^A-Za-z\n<]{0,3})([A-Za-z]{1,8})(\s+)([A-Za-z]+)')
JOBISH = re.compile(r'^(?:[A-Za-z]{0,2}[O0][BR8]|DB|10[B28]|1?0[23])$')


def fix_dropcap(md, log, slug):
    """段首花体大写字母常读丢或读成杂字（第 4 部 109 段里约 30 段）：OB/DB/GOB/§OB/102 → JOB；N the → IN the；
    E need → WE need；T the → AT the；He three → THe three；His latter → THis latter；OPHAR → ZOPHAR。
    只动每段经文框之后的第一个词，只用明确的几条（JOB 残形；N/I/Y the → IN；E have → WE；T the → AT；He/His/Hese 补 T，
    须搭配强 20 倍）。通用的「前补一个字母」试过：But、Hear、How 这类本来正常的段首词被改成 Cut、Year、Rom，弃用。"""
    m = RE_FIRST.search(md)
    if not m:
        return md
    junk, w, sp, nx = m.group(2), m.group(3), m.group(4), m.group(5)
    digits = re.sub(r'\D', '', junk)
    n = nx.lower()
    core = w[1:] if len(w) > 2 and w[0] == 'M' and w[1] == 'H' else w     # 「MHis」「MHe」：花体 T 读成 M
    if re.fullmatch(r'[A-Z]{1,2}He', w):
        core = 'He'                                                       # 「QPHe friends」
    if w in ('OPHAR', 'LIPHAZ', 'ILDAD', 'LIHU'):                         # 花体首字母丢失的人名
        new0 = {'OPHAR': 'ZOPHAR', 'LIPHAZ': 'ELIPHAZ', 'ILDAD': 'BILDAD', 'LIHU': 'ELIHU'}[w]
        log.append((slug, f'{junk}{w} {nx}', f'{new0} {nx}', 'dropcap'))
        return md[:m.start(2)] + new0 + md[m.end(3):]
    new = None
    if JOBISH.match(w) or (digits and JOBISH.match(digits + w)):
        new = 'JOB'
    elif w in ('N', 'I', 'Y') and n in ('the', 'this', 'these', 'that', 'those'):
        new = 'IN'
    elif w == 'E' and n in ('have', 'need', 'are', 'may', 'see', 'must', 'shall', 'will', 'find', 'read', 'come', 'now'):
        new = 'WE'
    elif w == 'T' and n == 'the':
        new = 'AT'
    elif core.lower() in ('he', 'his', 'hese', 'hat') and (core != w or junk.strip() or core.isupper() or
                                                         p_bi('t' + core.lower(), n) >= 20 * p_bi(core.lower(), n)):
        t = 't' + core.lower()
        if UNI.get(t, 0) >= 50:
            new = t.upper() if core.isupper() else t.capitalize()
    if not new:
        return md
    log.append((slug, f'{junk}{w} {nx}', f'{new} {nx}', 'dropcap'))
    return md[:m.start(2)] + new + md[m.end(3):]


RE_FLAG = re.compile(r'<span class="cy-ocr"[^>]*>([^<]+)</span>')


def ctx_words(md, s, e):
    """标记前后各一个词（跳过标签）。"""
    left = re.findall(r"[A-Za-z]+", re.sub(r'<[^>]+>', ' ', md[max(0, s - 200):s]))
    right = re.findall(r"[A-Za-z]+", re.sub(r'<[^>]+>', ' ', md[e:e + 200]))
    return (left[-1].lower() if left else ''), (right[0].lower() if right else '')


def fix_flagged(md, log, slug):
    """两层都判不了、标了存疑的非词（cy-ocr）：候选（字形混淆改一两处、或拆成两个词）按「本书词频 × 前后搭配」打分，
    最佳 ≥ 次佳 30 倍、且与前词或后词的搭配在语料里出现过，才改；改了仍保留存疑虚线（抽查约一成改错）。
    抽读第 4 部印本 p.377：一页 13 处错里 7 处是这类（ascept、tureatneth、Iike、coantrey、sothe…）。"""
    def rep(m):
        t = m.group(1)
        if not re.fullmatch(r"[A-Za-z']+", t) or UNI.get(t.lower(), 0) >= 5 or ' ' in t:
            return m.group(0)               # 已是词表里的词（上一轮改过的、或本就是真词）：不再动，保幂等
        a, b = ctx_words(md, m.start(), m.end())
        if UNI.get(a, 0) < 20 or UNI.get(b, 0) < 20:
            return m.group(0)               # 邻词是断词残片（elo quence、tran slation）时搭配统计失灵
        cands = set()
        fr = {t}
        for depth in range(2):
            fr = fx.step(fr)
            cands |= {v.lower() for v in fr}
            if depth == 0 and any(UNI.get(c, 0) >= 5 and (BI.get((a, c), 0) or BI.get((c, b), 0)) for c in cands):
                break                       # 只改一处就有像样的候选，不再看改两处的
        lt = t.lower().replace("'", '')
        for k in range(2, len(lt) - 1):
            if UNI.get(lt[:k], 0) >= 200 and UNI.get(lt[k:], 0) >= 200:
                cands.add(lt[:k] + ' ' + lt[k:])
        sc = {}
        for c in cands:
            ws = c.split()
            if not all(UNI.get(w, 0) >= 5 for w in ws):
                continue
            first, last = ws[0], ws[-1]
            if not (BI.get((a, first), 0) or BI.get((last, b), 0)):
                continue
            sc[c] = math.log(UNI[first] + 1) * 0 + math.log(p_bi(a, first) * p_bi(last, b) * (UNI.get(first, 0) + 1))
        if not sc:
            return m.group(0)
        ranked = sorted(sc.items(), key=lambda kv: -kv[1])
        if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < math.log(30):
            return m.group(0)
        new = ranked[0][0]
        new = new[0].upper() + new[1:] if t[0].isupper() else new
        log.append((slug, f'{a} [{t}] {b}', new, 'flag'))
        # 改了也保留存疑虚线：抽查这类改动约一成改错（rho→the 应 who、moct→meet 应 mock），
        # 去掉标记会把看得见的错变成看不见的错（old-book-ocr §0）
        return f'<span class="cy-ocr" title="OCR 存疑：据上下文推定，原读 {t}">{new}</span>'
    return RE_FLAG.sub(rep, md)


def fix_md(md, log, slug):
    prot = [(m.start(), m.end()) for m in fx.RE_PROTECT.finditer(md)]
    toks, k = [], 0
    for m in RE_W.finditer(md):
        while k < len(prot) and prot[k][1] <= m.start():
            k += 1
        if k < len(prot) and prot[k][0] <= m.start() < prot[k][1]:
            continue
        toks.append(m)
    edits = {}
    for i in range(1, len(toks) - 1):
        m = toks[i]
        t = m.group(0)
        if len(t) > 4 or len(t) < 2:
            continue
        pv, nx = toks[i - 1], toks[i + 1]
        # 前后词须与本词在同一句（中间只隔空白、逗号）
        if re.search(r'[.;:?!()\[\]<>]', md[pv.end():m.start()]) or re.search(r'[.;:?!()\[\]<>]', md[m.end():nx.start()]):
            continue
        a, b, lt = pv.group(0).lower(), nx.group(0).lower(), t.lower()
        if UNI.get(a, 0) < 20 or UNI.get(b, 0) < 20 or len(a) < 2 or len(b) < 2:
            continue                        # 前后词是残片（ly、hill）时搭配统计不可靠
        base = p_bi(a, lt) * p_bi(lt, b)
        best, bs = None, base
        for c in cands(t):
            if BI.get((a, c), 0) == 0 or BI.get((c, b), 0) == 0:
                continue
            s = p_bi(a, c) * p_bi(c, b)
            if s > bs:
                best, bs = c, s
        if UNI.get(lt, 0) >= 200:
            continue                        # 常见真词（nor、may、fell、man…）一概不碰：2000 倍门槛也拦不住 nor→not、may→way
        thr = 50
        if best and bs >= thr * base:
            new = best.capitalize() if t[0].isupper() else best
            edits[(m.start(), m.end())] = new
            log.append((slug, f'{a} [{t}] {b}', new, f'{math.log10(bs / base):.1f}'))
    out, last = [], 0
    for (s, e), new in sorted(edits.items()):
        out.append(md[last:s])
        out.append(new)
        last = e
    out.append(md[last:])
    return ''.join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    d = BASE / f'p{a.part}' / 'fixed'
    log, outs = [], {}
    for f in sorted(d.glob('*.md')):
        outs[f] = fix_md(fix_flagged(fix_dropcap(f.read_text(encoding='utf-8'), log, f.stem), log, f.stem), log, f.stem)
    c = collections.Counter((re.search(r'\[(.*?)\]', x[1]).group(1).lower(), x[2].lower()) if x[3] not in ('dropcap',)
                            else (x[1].split()[0], x[2].split()[0]) for x in log)
    print(f'第 {a.part} 部：改 {len(log):,} 处', file=sys.stderr)
    print('  ' + '；'.join(f'{w}→{n} {k}' for (w, n), k in c.most_common(40)), file=sys.stderr)
    if a.apply:
        for f, md in outs.items():
            f.write_text(md, encoding='utf-8')
        (BASE / f'p{a.part}' / 'ctx.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')
    return log


if __name__ == '__main__':
    main()
