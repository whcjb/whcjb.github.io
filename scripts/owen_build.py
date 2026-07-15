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

def para_to_md(k, t):
    if k == 'VER':
        return f'### {t}'
    if k in ('H2', 'PART') and re.match(r'CHAPTER\s+\d+\s*$', t):
        return None            # 章标记不入正文(front matter 已有章号)
    if k in ('H2', 'PART'):
        return f'## {t}'
    return t

def emit_chapters():
    # 收集全部 13 章 segments(每章取其所属卷)
    chapters = {}
    for vol in [3,4,5,6,7]:
        for ch, ps in chapter_segments(vol).items():
            if ch not in chapters:      # 首次出现为准(避免跨卷重复)
                chapters[ch] = ps
    os.makedirs(OUT, exist_ok=True)
    present = sorted(chapters)
    from subprocess import check_output
    date = check_output(['date','+%Y-%m-%d %H:%M']).decode().strip()
    for ch in present:
        ps = chapters[ch]
        lines = []
        for k, t in ps:
            md = para_to_md(k, t)
            if md is None:
                continue
            lines.append(md)
        body = '\n\n'.join(lines)
        fm = ['---', 'layout: owen-chapter', 'book_id: hebrews',
              'book_name: "希伯来书·约翰欧文注释"', f'chapter: {ch}',
              f'title: "第{CN[ch]}章"', f'date: {date}']
        idx = present.index(ch)
        if idx > 0:
            pc = present[idx-1]; fm += [f'prev_section: {pc}', f'prev_label: "第{CN[pc]}章"']
        if idx < len(present)-1:
            nc = present[idx+1]; fm += [f'next_section: {nc}', f'next_label: "第{CN[nc]}章"']
        fm += ['---', '']
        open(f'{OUT}/{ch}.md','w',encoding='utf-8').write('\n'.join(fm) + f'# 希伯来书 第{CN[ch]}章\n\n' + body + '\n')
        print(f'  写入 {OUT}/{ch}.md ({len(ps)} 段)')
    return present

if __name__ == '__main__':
    if '--emit' in sys.argv:
        chs = emit_chapters()
        print(f'共 {len(chs)} 章: {chs}')
    else:
        do_map()
