#!/usr/bin/env python3
"""马太亨利中文版：按 PDF 把单元小标题放到它该在的位置（零模型额度）。

病症（全库）：
  - 小标题粘在章综述末尾（太3「……（第16-17节）。施洗约翰传道」）
  - 小标题粘在上一单元注释的段末（申24「……不能不得赏赐。公义与慷慨」）
  - 几个小标题堆在同一个单元前面、或放错单元（王上1、出20）
  - 新约多卷完全没有小标题 div

做法：
  1. 从 PDF 提小标题：不以句末标点结尾的短段（≤40 字），且下一段是经文段；
     记下紧随的经文在汉字流里的位置。
  2. md 每个单元框头在 PDF 定位（best_head），标题归给「框头 ≥ 标题后经文起点」的第一个单元。
  3. 对每个归属到单元的标题：
     - 删掉 md 里同名的标题 div（无论在哪）与粘在块末尾的同名纯文字
       （块末尾 = 后面紧跟换行或标签；不动句中提及）
     - 在单元 <div class="mh-unit"> 前插入 <div class="mh-date-heading">标题</div>
     与 PDF 标题对不上的现有标题 div 原样不动。
验收：除标题文字外，正文汉字逐字不变；div 平衡。

用法：
  python3 scripts/fix_mhenry_headings.py [book...]           # dry-run
  python3 scripts/fix_mhenry_headings.py --apply [book...]
"""
import os, re, sys
import yaml
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit_mhenry_unit_seams import ROOT, UNIT_RE, HAN, han, chapter_files, pdf_files
from audit_mhenry_verse_boxes import best_head, VAR
from fix_mhenry_unit_seams import pdf_stream_raw, clean
from regen_mhenry_units import pdf_lines, paragraphs, END_PUNCT

HEAD_DIV = re.compile(r'<div class="mh-date-heading">([^<]*)</div>\s*')


def norm(t):
    return han(t).translate(VAR)


def pdf_headings(files):
    lines = pdf_lines(files)
    paras = [p for p in paragraphs(lines) if clean(''.join(l['text'] for l in p)).strip()]
    # 经文字体：以节号开头的段落里最多的字体
    from collections import Counter
    c = Counter()
    for p in paras:
        t = clean(''.join(l['text'] for l in p))
        if re.match(r'\d{1,3}(?:-\d{1,3})?\s*(?![.．\d])', t):
            f = ''.join(l['fonts'] for l in p)
            if f:
                c[max(set(f), key=f.count)] += 1
    vfont = c.most_common(1)[0][0] if c else 'K'
    out = []
    for i, p in enumerate(paras[:-1]):
        t = clean(''.join(l['text'] for l in p))
        if not (2 <= len(t) <= 40) or t[-1:] in END_PUNCT:
            continue
        q = paras[i + 1]
        qt = clean(''.join(l['text'] for l in q))
        qf = ''.join(l['fonts'] for l in q)
        vr = qf.count(vfont) / len(qf) if qf else 0
        if not ((re.match(r'\d', qt) and vr > 0.7) or vr >= 0.9):
            continue
        t = re.sub(r'(\d)(年）)', r'\1 \2', t)
        out.append(dict(text=t, sp=q[0]['h0']))
    return out


def plan_chapter(s, P, heads, cur):
    units = list(UNIT_RE.finditer(s))
    pos = []
    for m in units:
        v = han(m.group(1))
        if len(v) < 8:
            pos.append(None); continue
        vs, ok = best_head(P, v, cur, 200000)
        pos.append(vs if ok else None)
        if ok:
            cur = vs
    # 标题归属：框头 ≥ sp-3 且距离 < 600 的第一个单元
    assign = {}
    for h in heads:
        best = None
        for ui, vs in enumerate(pos):
            if vs is None:
                continue
            if h['sp'] - 3 <= vs < h['sp'] + 600:
                best = ui
                break
        if best is not None and best not in assign:
            assign[best] = h
    return units, pos, assign, cur


def apply_chapter(s, units, assign):
    # 先删：同名标题 div、块末尾粘着的同名文字
    names = {norm(h['text']): h for h in assign.values()}
    keyset = set(names)

    def drop_div(m):
        return '' if norm(m.group(1)) in keyset else m.group(0)
    s2 = HEAD_DIV.sub(drop_div, s)
    removed_glued = 0
    for k, h in sorted(names.items(), key=lambda kv: -len(kv[0])):   # 长的先删：「感恩」是「感恩；敬虔的决心」的前缀
        # 纯文字粘在块末尾：标题原文（数字与「年」之间空格可有可无）后紧跟换行或 <
        core = re.escape(re.sub(r'\s', '', h['text'])).replace(r'\ ', '')
        cs = re.sub(r'\s', '', h['text'])
        pat = r'\s*'.join(re.escape(c) for c in cs)     # 末字后不吞空白：保住原有换行
        rx = re.compile(r'(?<=[。！？”’」』）)\]一-鿿])' + pat + r'(?=\s*(?:\n|<))')
        s2, n = rx.subn('', s2)
        removed_glued += n
    # 再插：每个单元前插标题
    units2 = list(UNIT_RE.finditer(s2))
    for ui in sorted(assign, reverse=True):
        if ui >= len(units2):
            continue
        st = s2.rfind('<div class="mh-unit">', 0, units2[ui].start(1))
        s2 = s2[:st] + f'<div class="mh-date-heading">{assign[ui]["text"]}</div>\n\n' + s2[st:]
    return s2, removed_glued


def main():
    args = sys.argv[1:]
    do_apply = '--apply' in args
    args = [a for a in args if a != '--apply']
    books = yaml.safe_load(open(f'{ROOT}/_data/mhenry_books.yml', encoding='utf-8'))
    names = {bk['id']: bk['name'] for grp in books.values() for bk in grp}
    tot_ins = tot_glued = tot_files = 0
    for book in args or list(names):
        if book.endswith('-en') or book not in names:
            continue
        zh = names[book]
        files = pdf_files(book, zh) or pdf_files(book, zh.replace('纪', '记') if '纪' in zh else zh.replace('记', '纪'))
        if not files:
            continue
        P, F, R, idx = pdf_stream_raw(files)
        if len(P) < 1000:
            print(f'-- {book}: PDF 无文字层，跳过'); continue
        heads = pdf_headings(files)
        cur, n_ch = 0, 0
        for md in chapter_files(book):
            s = open(md, encoding='utf-8').read()
            units, pos, assign, cur = plan_chapter(s, P, heads, cur)
            if not assign:
                continue
            # 已经就位的不算改动
            todo = {}
            for ui, h in assign.items():
                st = s.rfind('<div class="mh-unit">', 0, units[ui].start(1))
                prev = s[:st]
                mh = re.search(r'<div class="mh-date-heading">([^<]*)</div>\s*$', prev)
                stacked = len(re.findall(r'<div class="mh-date-heading">', prev[-400:])) > 1 and mh
                if mh and norm(mh.group(1)) == norm(h['text']) and not stacked:
                    continue
                todo[ui] = h
            # 块末尾还挂着同名标题文字（诗3 综述末「苦难与信靠」），也要处理
            for h in assign.values():
                pat = r'\s*'.join(re.escape(c) for c in re.sub(r'\s', '', h['text']))
                if re.search(r'(?<=[。！？”’」』）)\]\u4e00-\u9fff])' + pat + r'(?=\s*(?:\n|<))', HEAD_DIV.sub('', s)):
                    todo.setdefault(-1, h)
            # 整章只要有一处要动，就按全部归属重排（保证同名 div 只留一个）
            if not todo:
                continue
            s2, glued = apply_chapter(s, units, assign)
            # 验收：去掉标题后正文汉字不变
            def body(t):
                t = HEAD_DIV.sub('', t)
                for h in sorted(assign.values(), key=lambda x: -len(x['text'])):
                    t = re.sub(''.join(re.escape(c) + r'\s*' for c in re.sub(r'\s', '', h['text'])), '', t)
                return norm(re.sub(r'<style.*?</style>', '', t, flags=re.S))
            ok = body(s) == body(s2) and (s2.count('<div') - s2.count('</div>')) == (s.count('<div') - s.count('</div>'))
            ch = os.path.basename(md)[:-3]
            print(f"{book} {ch}: 归位 {len(todo)} 个（共 {len(assign)}），删粘连 {glued} {'OK' if ok else 'FAIL'} | "
                  + ' / '.join(h['text'][:12] for h in todo.values()))
            if ok:
                tot_ins += len(todo); tot_glued += glued; tot_files += 1
                if do_apply:
                    open(md, 'w', encoding='utf-8').write(s2)
    print(f'TOTAL 文件 {tot_files} 归位 {tot_ins} 删粘连 {tot_glued}')


if __name__ == '__main__':
    main()
