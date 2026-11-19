#!/usr/bin/env python3
"""史密斯《大卫的有福之人》1616 年版（EEBO-TCP B00721）缺页 → 用 1868 年 Nichol 重印本补文。

    python3 scripts/smith_psalm1_fill.py        # 写 smith_raw/psalm1/fills.json，并打印每处接缝供核对

TCP 录入所据那一册缺 6 处共 34 页（archive.org 上 1616 年那一册在祷文处缺得一样）。用户 2026-11-19 定：
用后来版次的扫描本 OCR 补全。Nichol 本（Edinburgh 1868，IA davidsblessedman00smit）据后来的增订本重排、拼法现代化；
补进去的文字在页面上用框标出来源。

定位：取缺口前、后各 12 个词（拼法归一：v→u、j→i、y→i、双字母合一、去词尾 e），在 Nichol 正文词流里找最相似的窗口，
前锚取窗口末、后锚取窗口首，中间就是补文。前五处字数与所缺页数吻合（每页 160–175 词）。
第 6 处（书末家庭祷文中间 2 页）Nichol 本的祷文已经改写（提到国王王后、查理王子），对不上，不补，页面注明。

清理：第 ② 层 tesseract 对证 + 第 ① 层字形规则（nichol1868_ocr.py），编者脚注（6 号字）不收。
"""
import difflib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nichol1868_ocr as n   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'smith_raw' / 'psalm1'
TEI = '{http://www.tei-c.org/ns/1.0}'
PAGES = (47, 118)          # Nichol 合订本里史密斯部分（ABBYY 页序）
# 第 1 处（卷首 6 页，献辞「…bring forth fruit in due season in this」之后、目录之前）：Nichol 本的献辞是 1635 年版的，
# 结尾能对上；缺页里此外还有什么（或有致读者）无从确认，所以只补到献辞署名为止，不带「Prittlewell, 1635」日期行。
FILL_END = {1: r'SAMUEL SMITH\.?$'}
NOTE = {1: 'Only the end of the Epistle Dedicatory can be supplied: the 1868 reprint follows the dedication of a later '
           'edition (dated 1635), and what else stood on these six pages cannot be identified. '
           '这里只能补出献辞的结尾：1868 年重印本用的是后来版次（1635 年）的献辞，缺的六页里此外还有什么无从确认。'}
SKIP_GAPS = {6: 'The two pages wanting here fall in the middle of the morning prayer; the prayer in the later edition '
                'reprinted in 1868 has been rewritten, so they cannot be supplied from it. '
                '原书此处缺两页，在晨祷中间；1868 年重印本所据的后来版次祷文已改写，无从补入。'}


def sk(w):
    w = n.norm(w).replace('v', 'u').replace('j', 'i').replace('y', 'i')
    w = re.sub(r'(.)\1', r'\1', w)
    return w[:-1] if w.endswith('e') and len(w) > 3 else w


def nichol_stream():
    """Nichol 正文 → 段落列表 [{'text', 'page', 'new'}] 与词流 [(段号, match)]。"""
    pages = n.load()
    pars, stream = [], []
    for i in range(PAGES[0], PAGES[1] + 1):
        for bi, b in enumerate(pages[i]):
            if n.kind(b) != 'text':
                continue
            wit = n.tess(i, bi, b)
            for p in b['pars']:
                if p['fs'] and p['fs'] < 6.5:          # 编者脚注
                    continue
                led = []
                t, _ = n.repair(p['text'], wit, led)
                t = n.glyph_repair(t, led)
                pars.append(dict(text=t, page=i, new='startIndent' in p['attrs'], dis=n.disagree(t, wit)))
                plain = t.replace(n.IT_ON, ' ').replace(n.IT_OFF, ' ')
                for m in n.WORD.finditer(plain):
                    stream.append((len(pars) - 1, m))
    return pars, stream


def tcp_tokens(xmlf):
    r = ET.parse(xmlf).getroot()
    toks = []

    def walk(e):
        if e.tag == TEI + 'gap' and e.get('reason') == 'missing':
            toks.append(('GAP', e.get('extent')))
        elif e.tag != TEI + 'note':
            if e.text:
                toks.extend(('W', sk(x)) for x in n.WORD.findall(e.text.replace('ſ', 's')))
            for c in e:
                walk(c)
        if e.tail:
            toks.extend(('W', sk(x)) for x in n.WORD.findall(e.tail.replace('ſ', 's')))
    walk(r.find('.//' + TEI + 'text'))
    return toks


def best(seq, words):
    L, top = len(seq), (0, None)
    for i in range(len(words) - L):
        s = difflib.SequenceMatcher(None, seq, words[i:i + L], autojunk=False).ratio()
        if s > top[0]:
            top = (s, i)
    return top


def md(t):
    t = re.sub(n.IT_ON + r'(\s*)', r'\1*', t)
    t = re.sub(r'(\s*)' + n.IT_OFF, r'*\1', t)
    t = re.sub(r'\*\s*\*', ' ', t)
    t = re.sub(r' ?\*1\*(?= [A-Z])', '?', t)      # 问号读成斜体 1（tesseract 三处都读作 ?，2026-11-19 核）
    t = re.sub(r'\s*■\s*', ' ', t)                 # 页面污点
    return t.strip()


def main():
    pars, stream = nichol_stream()
    words = [sk(m.group()) for _, m in stream]
    toks = tcp_tokens(RAW / 'src' / 'B00721.xml')
    fills, g = {}, 0
    for k, t in enumerate(toks):
        if t[0] != 'GAP':
            continue
        g += 1
        if g in SKIP_GAPS:
            fills[g] = dict(skip=SKIP_GAPS[g])
            continue
        before = [x[1] for x in toks[max(0, k - 14):k] if x[0] == 'W'][-12:]
        after = [x[1] for x in toks[k + 1:k + 20] if x[0] == 'W'][:12]
        sb, ib = best(before, words)
        a0 = ib + len(before)
        if g in FILL_END:                            # 后锚不可用：止于指定段落（含）
            pend = next(pi for pi in range(stream[a0][0], len(pars))
                        if re.search(FILL_END[g], pars[pi]['text'].replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()))
            a1 = max(j for j, (pi, _) in enumerate(stream) if pi == pend) + 1
            sa = 1.0
        else:
            sa, ia = best(after, words)
            a1 = ia                                  # 补文 = 词流 [a0, a1)
        assert sb >= 0.6 and sa >= 0.6 and a1 > a0, (g, sb, sa, a0, a1)
        p0, m0 = stream[a0]
        p1, m1 = stream[a1 - 1]
        chunks = []
        for pi in range(p0, p1 + 1):
            text = pars[pi]['text']
            s = m0.start() if pi == p0 else 0
            e = m1.end() if pi == p1 else len(text)
            piece = text[s:e]
            if pi == p1:                                 # 把紧跟末词的标点带上
                piece += re.match(r'[^\w\s]*', text[e:]).group()
            if chunks and not pars[pi]['new']:
                chunks[-1] += ' ' + piece
            else:
                chunks.append(piece)
        body = [md(c) for c in chunks if c.strip()]
        # 接缝去重：锚窗错位一个词时，补文首／末会重出 TCP 相邻的词（缺口 4 的 prosper）
        fw = n.WORD.findall(body[0])
        if fw and sk(fw[0]) == before[-1]:
            body[0] = body[0][body[0].find(fw[0]) + len(fw[0]):].lstrip(' ,')
        lw = n.WORD.findall(body[-1])
        if lw and g not in FILL_END and sk(lw[-1]) == after[0]:
            body[-1] = body[-1][:body[-1].rfind(lw[-1])].rstrip()
        dis = [(pars[pi]['page'],) + d for pi in range(p0, p1 + 1) for d in pars[pi]['dis']]
        pp = [n.printed_page(x) for x in sorted({pars[pi]['page'] for pi in range(p0, p1 + 1)})]
        fills[g] = dict(paras=body, note=NOTE.get(g, ''), disagree=dis, nichol_pp=pp, nichol_pages=sorted({pars[pi]['page'] for pi in range(p0, p1 + 1)}),
                        words=a1 - a0, score=[round(sb, 2), round(sa, 2)], extent=t[1])
        print(f'— 缺口 {g}（{t[1]}，{a1 - a0} 词，锚 {sb:.2f}/{sa:.2f}，Nichol 第 {fills[g]["nichol_pages"]} 页）')
        print('   TCP 前文：', ' '.join(before[-6:]))
        print('   补文起：  ', body[0][:90])
        print('   补文止：  ', body[-1][-90:])
        print('   TCP 后文：', ' '.join(after[:6]))
    # 第 ③ 层：看图判读表（fill_fixes.tsv，原串须在该处补文里恰好出现一次）
    fixes = [l.rstrip('\n').split('\t') for l in (RAW / 'fill_fixes.tsv').read_text(encoding='utf-8').splitlines()
             if l and not l.startswith('#')]
    for old, new in fixes:
        hits = [(g, i) for g, f in fills.items() for i, p in enumerate(f.get('paras', [])) if old in p]
        cnt = sum(fills[g]['paras'][i].count(old) for g, i in hits)
        if cnt != 1:
            print(f'⚠️ 判读表条目命中 {cnt} 次：{old!r}')
            continue
        g, i = hits[0]
        fills[g]['paras'][i] = fills[g]['paras'][i].replace(old, new)
    (RAW / 'fills.json').write_text(json.dumps(fills, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    left = sum(len(n.nonwords(p)[0]) for f in fills.values() for p in f.get('paras', []))
    tot = sum(n.nonwords(p)[1] for f in fills.values() for p in f.get('paras', []))
    print(f'补文共 {tot} 词，残余非词 {left}（{left / max(tot, 1):.2%}）')


if __name__ == '__main__':
    main()
