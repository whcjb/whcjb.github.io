#!/usr/bin/env python3
"""
owen_build.py — 把 owen_raw/hebrews/vol{N}_structured.txt 重组成:
  · 希伯来书 1-13 章(Vol3-7 逐节注释)
  · 40 篇导论 Exercitation(Vol1-2)
章边界: 优先用「真」CHAPTER N 标记(独立 [H2] 且下一段是长 body); 缺失/混入时
用「经节号重置」兜底(Ver.N 从高跳回低 = 新章), 起始章号按卷基准。

先 --map 打印章映射核对; 再 --emit 生成 markdown 到 owen/hebrews/。
"""
import re, sys, os, glob

RAW = 'owen_raw/hebrews'
VOL_BASE_CH = {3: 1, 4: 3, 5: 5, 6: 8, 7: 11}   # 各卷起始 Heb 章(粗基准, 供 verse-reset)

def load(vol):
    txt = open(f'{RAW}/vol{vol}_structured.txt', encoding='utf-8').read()
    out = []
    for p in txt.split('\n\n'):
        p = p.strip()
        if not p:
            continue
        m = re.match(r'\[(\w+)\]\s*(.*)', p, re.S)
        if m:
            out.append((m.group(1), m.group(2).strip()))
        else:
            out.append(('BODY', p))
    return out

def ver_num(text):
    m = re.match(r'Vers?e?s?\.?\s+(\d+)', text)
    return int(m.group(1)) if m else None

def real_chapters(paras):
    """返回 [(chap_no, start_idx)]: TOC 区之后的独立 CHAPTER N 标记 = 真章首。
    TOC 区 = 第一段长散文(len>250)之前的部分。"""
    toc_end = 0
    for i, (k, t) in enumerate(paras):
        if len(t) > 250:
            toc_end = i; break
    res = {}
    for i, (k, t) in enumerate(paras):
        if i < toc_end - 3:               # TOC 区(章首标记就在首段长散文前, 留 3 段余量)
            continue
        m = re.match(r'CHAPTER\s+(\d+)\s*$', t)
        if m:
            res[int(m.group(1))] = i      # 同章号取正文出现(TOC 已排除)
    return sorted(res.items())

def split_by_verse_reset(paras, base_ch, start=0, end=None):
    """无干净章标记时: 按英文 Ver.N 号重置切章, 从 base_ch 起编号"""
    end = end if end is not None else len(paras)
    bounds = []          # (chap, start_idx)
    ch = base_ch; last_v = 0; started = False
    for i in range(start, end):
        k, t = paras[i]
        if k != 'VER' or not re.search(r'[A-Za-z]', t):   # 只看英文 Ver 行
            continue
        v = ver_num(t)
        if v is None:
            continue
        if not started:
            bounds.append((ch, i)); started = True; last_v = v; continue
        if v < last_v - 1:               # 号跳回 = 新章
            ch += 1; bounds.append((ch, i))
        last_v = v
    return bounds

import fitz
def toc_chapters(vol):
    """从 PDF 目录解析该卷含哪些 Heb 章(顺序)。"""
    d = fitz.open(os.path.expanduser(f'~/Documents/论文/owen/owen_hebrews_{vol}.pdf'))
    toc = ''.join(d[i].get_text() for i in range(2, 8))
    chs = []
    for ln in toc.split('\n'):
        m = re.match(r'^\s*CHAPTER\s+(\d+)\s*$', ln.strip())
        if m:
            c = int(m.group(1))
            if c not in chs:
                chs.append(c)
    return chs

def chapter_segments(vol):
    """TOC 驱动: body 按英文 Ver.(首节==1)重置切段, 按 TOC 章号顺序编号。
    返回 {chap_no: [paras...]}"""
    paras = load(vol)
    chs = toc_chapters(vol)
    if not chs:
        chs = [VOL_BASE_CH.get(vol, 1)]
    # 找 body 里每章起点: 英文 Ver 且首节号==1(章首); 跳过 TOC 区
    toc_end = next((i for i,(k,t) in enumerate(paras) if len(t) > 250), 0)
    starts = []
    prev_v = None
    for i in range(toc_end, len(paras)):
        k, t = paras[i]
        if k != 'VER' or not re.search(r'[A-Za-z]', t):
            continue
        v = ver_num(t)
        if v is None:
            continue
        # 章首 = 首节回到 1(且非紧接的重复 1)
        if v == 1 and (prev_v is None or prev_v > 2):
            starts.append(i)
        prev_v = v
    # 章号: 首段(章首之前的导言)归第一章; starts 依次对应 chs
    segs = {}
    if not starts:
        segs[chs[0]] = paras[toc_end:]
        return segs
    # chs 数应 == starts 数; 不等时按较小者对齐, 多出的并入末章
    n = min(len(chs), len(starts))
    # 第一章从 toc_end(含导言)开始
    bounds = [toc_end] + starts[1:n] if n > 1 else [toc_end]
    for j in range(n):
        ch = chs[j]
        s = bounds[j] if j < len(bounds) else starts[j]
        e = (bounds[j+1] if j+1 < len(bounds) else len(paras))
        segs[ch] = paras[s:e]
    return segs

def do_map():
    allmap = {}
    for vol in [3,4,5,6,7]:
        segs = chapter_segments(vol)
        for ch, ps in segs.items():
            vers = [t for k,t in ps if k=='VER' and re.search(r'[A-Za-z]',t)]
            allmap.setdefault(ch, []).append((vol, len(ps), len(vers)))
    for ch in sorted(allmap):
        print(f'Heb {ch:>2}: ', end='')
        for vol,np,nv in allmap[ch]:
            print(f'[Vol{vol} {np}段 {nv}节] ', end='')
        print()

CN = ['零','一','二','三','四','五','六','七','八','九','十','十一','十二','十三']
OUT = 'owen/hebrews'

def ver_label(t):
    """'Ver. 1, 2.—...' -> ('1, 2', '经文文本')"""
    m = re.match(r'(Vers?e?s?\.?\s*([\d,\s–\-]+))\.?\s*[—\-–]\s*(.*)', t, re.S)
    if not m:
        return (None, t)
    nums = re.sub(r'\s+', ' ', m.group(2)).strip().rstrip('.').strip()
    return (nums, m.group(3).strip())

def is_greek(s):
    return bool(re.search(r'[Ͱ-Ͽἀ-῿]', s))

def build_body(ps):
    """按节分块: 章首导言 → 每节[Ver.N 标题 + 经文框(希/英) + 考据/释义正文]"""
    out = []
    i = 0
    # 章首导言(第一个 VER 之前)
    while i < len(ps) and ps[i][0] != 'VER':
        k, t = ps[i]
        if not (k in ('H2','PART') and re.match(r'CHAPTER\s+\d+\s*$', t)):
            out.append(f'## {t}' if k in ('H2','PART') else t)
        i += 1
    # 逐节
    while i < len(ps):
        k, t = ps[i]
        if k != 'VER':
            out.append(t); i += 1; continue
        num, _ = ver_label(t)
        # 收集同节的连续 VER(希/英) + 之后的 body 直到下一个不同节号的 VER
        scr = []
        body = []
        while i < len(ps):
            k2, t2 = ps[i]
            if k2 == 'VER':
                n2, vt = ver_label(t2)
                if scr and n2 != num:      # 新节
                    break
                scr.append(vt); i += 1
            else:
                body.append(t2); i += 1
        # emit 节块
        vlabel = f'Ver. {num}' if num else 'Ver.'
        out.append(f'\n### {vlabel}')
        if scr:
            box = '<div class="owen-scr" markdown="0">'
            for s in scr:
                cls = 'owen-scr-grk' if is_greek(s) else 'owen-scr-en'
                box += f'<p class="{cls}">{s}</p>'
            box += '</div>'
            out.append(box)
        out.extend(body)
    return out

def slug_of(nums):
    """'1, 2' -> '1-2';  '3' -> '3';  '10–14' -> '10-14'"""
    ds = [int(x) for x in re.findall(r'\d+', nums)]
    if not ds: return '0'
    return str(ds[0]) if len(ds) == 1 else f'{ds[0]}-{ds[-1]}'

def split_chapter(ps):
    """-> (intro_paras, [(label, slug, [paras])])"""
    i = 0; intro = []
    while i < len(ps) and ps[i][0] != 'VER':
        k, t = ps[i]
        if not (k in ('H2','PART') and re.match(r'CHAPTER\s+\d+\s*$', t)):
            intro.append((k, t))
        i += 1
    blocks = []
    while i < len(ps):
        k, t = ps[i]
        if k != 'VER':
            i += 1; continue
        num, _ = ver_label(t)
        grp = []
        while i < len(ps):
            k2, t2 = ps[i]
            if k2 == 'VER':
                n2, _ = ver_label(t2)
                if grp and n2 != num: break
            grp.append(ps[i]); i += 1
        blocks.append((f'Ver. {num}', slug_of(num or '0'), grp))
    return intro, blocks

def block_body(grp):
    """经节组内容: 经文框(希/英) + 考据/释义正文"""
    out = []; scr = []; body = []
    for k, t in grp:
        if k == 'VER':
            _, vt = ver_label(t); scr.append(vt)
        else:
            body.append(t)
    if scr:
        box = '<div class="owen-scr" markdown="0">'
        for s in scr:
            cls = 'owen-scr-grk' if is_greek(s) else 'owen-scr-en'
            box += f'<p class="{cls}">{s}</p>'
        box += '</div>'
        out.append(box)
    out.extend(body)
    return '\n\n'.join(out)

def emit_verse_pages():
    chapters = {}
    for vol in [3,4,5,6,7]:
        for ch, ps in chapter_segments(vol).items():
            if ch not in chapters:
                chapters[ch] = ps
    present = sorted(chapters)
    from subprocess import check_output
    date = check_output(['date','+%Y-%m-%d %H:%M']).decode().strip()
    # 先算全局经节组链(跨章 prev/next)
    all_pages = []   # (ch, label, slug)
    ch_blocks = {}
    for ch in present:
        intro, blocks = split_chapter(chapters[ch])
        ch_blocks[ch] = (intro, blocks)
        for label, slug, grp in blocks:
            all_pages.append((ch, label, slug))
    # 清旧的 N.md
    for f in glob.glob(f'{OUT}/*.md'):
        os.remove(f)
    npages = 0
    for ch in present:
        intro, blocks = ch_blocks[ch]
        os.makedirs(f'{OUT}/{ch}', exist_ok=True)
        # 章目录页
        introhtml = '\n\n'.join(f'## {t}' if k in ('H2','PART') else t for k,t in intro)
        links = '\n'.join(
            f'<li><a href="{{{{ site.baseurl }}}}/owen/hebrews/{ch}/{slug}/">{label}</a></li>'
            for label, slug, grp in blocks)
        ci = ['---','layout: owen-book','book_id: hebrews',
              'book_name: "希伯来书·约翰欧文注释"',f'chapter: {ch}',
              f'title: "第{CN[ch]}章"',f'date: {date}','---','',
              f'# 希伯来书 第{CN[ch]}章','']
        open(f'{OUT}/{ch}/index.md','w',encoding='utf-8').write(
            '\n'.join(ci) + introhtml + f'\n\n<ul class="owen-vg-list">\n{links}\n</ul>\n')
        # 各经节组页
        for label, slug, grp in blocks:
            gi = all_pages.index((ch, label, slug))
            fm = ['---','layout: owen-chapter','book_id: hebrews',
                  'book_name: "希伯来书·约翰欧文注释"',f'chapter: {ch}',
                  f'verse_group: "{slug}"',f'title: "希伯来书 {ch}:{slug}"',f'date: {date}']
            if gi > 0:
                pch,pl,psl = all_pages[gi-1]
                plabel = pl if pch==ch else f'希 {pch}:{psl}'
                fm += [f'prev_url: "/owen/hebrews/{pch}/{psl}/"', f'prev_label: "{plabel}"']
            if gi < len(all_pages)-1:
                nch,nl,nsl = all_pages[gi+1]
                nlabel = nl if nch==ch else f'希 {nch}:{nsl}'
                fm += [f'next_url: "/owen/hebrews/{nch}/{nsl}/"', f'next_label: "{nlabel}"']
            fm += ['---','']
            open(f'{OUT}/{ch}/{slug}.md','w',encoding='utf-8').write(
                '\n'.join(fm) + f'# 希伯来书 {ch}:{slug}\n\n<div class="owen-vg-sub">约翰·欧文注释 · {label}</div>\n\n' + block_body(grp) + '\n')
            npages += 1
    print(f'共 {len(present)} 章, {npages} 个经节组页面')
    return present

if __name__ == '__main__':
    if '--emit' in sys.argv:
        emit_verse_pages()
    else:
        do_map()
