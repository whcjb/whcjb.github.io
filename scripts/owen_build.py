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

def ver_range(t):
    """VER 文本 -> (lo, hi) 节号范围; 无则 None"""
    m = re.match(r'Vers?e?s?\.?\s*([\d,\s–\-]+)', t)
    if not m:
        return None
    ds = [int(x) for x in re.findall(r'\d+', m.group(1))]
    return (ds[0], ds[-1]) if ds else None

def split_chapter(ps):
    """-> (intro_paras, [(label, slug, [paras])])
    切页边界: 只在节号「单调前进」(lo 超过本章已见最大节)时才开新页;
    Owen 释义里回引的低节号(如讲完 Ver.9 又回引 Ver.5)并入当前块, 不另起页。
    块内段落一律照 PDF 原顺序原样(忠实)。"""
    i = 0; intro = []
    # intro = 开头英文散文(章总论); 遇希腊/希伯来原文(经文/考据起点)或首个 VER 即止
    while i < len(ps):
        k, t = ps[i]
        if k == 'VER' or is_greek(t):
            break
        if not (k in ('H2','PART') and re.match(r'CHAPTER\s+\d+\s*$', t)):
            intro.append((k, t))
        i += 1
    blocks = []          # [{'num','slug','paras'}]
    cur = None; cur_maxhi = 0; pending = []   # 首个 VER 前的经文/考据 → 并入第一个经节块
    while i < len(ps):
        k, t = ps[i]
        if k == 'VER':
            rng = ver_range(t)
            if rng and (cur is None or rng[0] > cur_maxhi):   # 单调前进 = 新节块
                num, _ = ver_label(t)
                cur = {'num': num, 'slug': slug_of(num or '0'), 'paras': pending}
                pending = []; blocks.append(cur); cur_maxhi = rng[1]
            elif rng:                                          # 回引 = 并入当前块
                cur_maxhi = max(cur_maxhi, rng[1])
        if cur is None:                                        # 尚无块 → 暂存, 待首个 VER 领走
            pending.append((k, t)); i += 1; continue
        cur['paras'].append((k, t)); i += 1
    if cur is None:                                            # 全章无 VER(纯散文) → pending 落回 intro
        intro += pending
    out = [(f"Ver. {b['num']}" if b['num'] else 'Ver.', b['slug'], b['paras']) for b in blocks]
    return intro, out

def block_body_faithful(grp):
    """经节块忠实渲染: VER→owen-ver, H2/PART→h2, 其余→p; 照 PDF 原顺序, 不折叠/不缩进/不切分。"""
    e = _html.escape
    lines = []
    for k, t in grp:
        if k in ('H2','PART') and re.match(r'CHAPTER\s+\d+\s*$', t):
            continue
        if k == 'VER':
            lines.append(f'<p class="owen-ver">{e(t)}</p>')
        elif k in ('H2','PART'):
            lines.append(f'<h2>{e(t)}</h2>')
        else:
            lines.append(f'<p>{e(t)}</p>')
    return '\n\n'.join(lines)

import html as _html
PHIL_WITNESS = re.compile(r'^(V\.\s*L\.|Syr\.|Vulg\.|Beza|Eras\.|Arab\.|A\.\s*Montan|LXX|Sept\.|Chald\.| Æthiop)')
def is_philology(p):
    """Owen 逐词原文考据段: 以希腊/希伯来文起, 或以「词, "译解"」+多语版本标记起"""
    s = p.strip()
    if re.match(r'^[Ͱ-Ͽἀ-῿֐-׿]', s):   # 希腊/希伯来文开头
        return True
    if PHIL_WITNESS.match(s):
        return True
    # 短词 + 逗号 + 引号译解, 且含多语版本/拉丁标记
    if re.match(r'^[A-Za-z][\w\-]{0,14},\s*["“]', s) and \
       re.search(r'(Syr\.|Vulg\.|Beza|Eras\.|Chald\.|Lat\.|Montan)', s):
        return True
    return False

# 层级 rank(实证得出, 越小越高): I. > First > 1. > (1.) > [1.]
RANK = {'ROMAN': 0, 'FIRST': 1, 'NUM': 2, 'PAREN': 3, 'BRACK': 4}
_FIRST = {'First':1,'Second':2,'Third':3,'Fourth':4,'Fifth':5,'Sixth':6,
          'Seventh':7,'Eighth':8,'Ninth':9,'Tenth':10,'Lastly':99}
def _roman(s):
    R={'I':1,'V':5,'X':10,'L':50,'C':100}; tot=0; prev=0
    for c in reversed(s.upper()):
        v=R.get(c,0); tot += -v if v<prev else v; prev=max(prev,v)
    return tot

def parse_marker(t):
    """-> (type, value, marker_str, rest) 或 None"""
    m = re.match(r'^\[(\d{1,3})\.?\]\s*(.+)', t, re.S)
    if m: return ('BRACK', int(m.group(1)), f'[{m.group(1)}.]', m.group(2))
    m = re.match(r'^\((\d{1,3})\.?\)\s*(.+)', t, re.S)
    if m: return ('PAREN', int(m.group(1)), f'({m.group(1)}.)', m.group(2))
    m = re.match(r'^([IVX]{1,5})\.\s+(.+)', t, re.S)
    if m: return ('ROMAN', _roman(m.group(1)), f'{m.group(1)}.', m.group(2))
    m = re.match(r'^(\d{1,3})\.\s+(.+)', t, re.S)
    if m: return ('NUM', int(m.group(1)), f'{m.group(1)}.', m.group(2))
    m = re.match(r'^(First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Lastly)(ly)?([,.]\s+.+)', t, re.S)
    if m: return ('FIRST', _FIRST[m.group(1)], m.group(1)+(m.group(2) or ''), m.group(3).lstrip('., '))
    return None

# 内嵌分点切分: 句末标点后紧跟 N./(N.)/[N.] + 空格 + 大写(拉丁/希腊)= 下一个分点
_INLINE = re.compile(r'(?<=[.;:!?"”’])\s+(?=(?:\d{1,3}\.|\(\d{1,3}\.?\)|\[\d{1,3}\.?\])\s+[A-Z"“Ͱ-Ͽἀ-῿])')
def pre_split(t):
    return [s.strip() for s in _INLINE.split(t) if s.strip()]

def render_expo(paras):
    """栈式解析真实嵌套深度: 值≥2 回到同类型开层并关子层; 值=1 按 rank 弹栈后压栈。
    深度 = 当前开着的祖先层数。返回 [(depth, marker_str_or_None, text)]"""
    stack = []   # [{'type','val'}]
    out = []
    for t in paras:
        pm = parse_marker(t)
        if not pm:
            out.append((len(stack)-1 if stack else 0, None, t)); continue
        typ, val, mstr, rest = pm
        if val >= 2:
            idx = next((i for i in range(len(stack)-1, -1, -1) if stack[i]['type']==typ), None)
            if idx is not None:
                del stack[idx+1:]; stack[idx]['val']=val; depth=idx
            else:
                while stack and RANK[stack[-1]['type']] >= RANK[typ]: stack.pop()
                stack.append({'type':typ,'val':val}); depth=len(stack)-1
        else:  # val == 1 新列表
            while stack and RANK[stack[-1]['type']] >= RANK[typ]: stack.pop()
            stack.append({'type':typ,'val':1}); depth=len(stack)-1
        out.append((depth, mstr, rest))
    return out

def expo_html(paras):
    e = _html.escape
    html_lines = []
    for depth, mstr, text in render_expo(paras):
        d = min(depth, 4)   # 视觉缩进封顶 4 级
        if mstr:
            html_lines.append(f'<p class="owen-d{d} owen-mk"><b class="owen-num">{e(mstr)}</b> {e(text)}</p>')
        else:
            html_lines.append(f'<p class="owen-d{d}">{e(text)}</p>')
    return html_lines

def block_body(grp):
    """经节组: 经文框(希/英) + 折叠的原文字词考据 + 释义正文(嵌套分点缩进)"""
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
    # 分离开头的字词考据区 → 折叠; 容忍考据间的短插句, 遇首段实质释义(长英文)即止
    j = 0; started = False
    while j < len(body):
        if is_philology(body[j]):
            started = True; j += 1
        elif started and len(body[j]) < 140:   # 考据中夹的短句
            j += 1
        else:
            break
    phil, expo = body[:j], body[j:]
    if not expo:            # 兜底: 若全被判为考据, 不折叠, 全显示
        phil, expo = [], body
    if phil:
        det = '<details class="owen-philology" markdown="0"><summary>原文字词考据（希腊 / 希伯来 / 叙利亚 / 拉丁文逐词对照）</summary>'
        for p in phil:
            det += f'<p>{_html.escape(p)}</p>'
        det += '</details>'
        out.append(det)
    expo = [frag for p in expo for frag in pre_split(p)]   # 先切开内嵌分点
    out.extend(expo_html(expo))
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

def emit_verse_collapsed():
    """按章一页; 页内每个经节组包成默认折叠的 <details>(summary=Ver.N+经文预览),
    点开看该节注释。组内正文照 PDF 原顺序原样(忠实), 只加折叠外壳。"""
    chapters = {}
    for vol in [3,4,5,6,7]:
        for ch, ps in chapter_segments(vol).items():
            chapters.setdefault(ch, ps)
    present = sorted(chapters)
    from subprocess import check_output
    date = check_output(['date','+%Y-%m-%d %H:%M']).decode().strip()
    e = _html.escape
    # 清旧: N/index.md 覆盖即可; 顺带删可能残留的 slug 子文件
    for f in glob.glob(f'{OUT}/*/*.md'):
        if not f.endswith('/index.md'):
            os.remove(f)
    for f in glob.glob(f'{OUT}/*.md'):
        os.remove(f)
    for ch in present:
        intro, blocks = split_chapter(chapters[ch])
        parts = []
        # 章首导言(忠实, 不折叠)
        for k, t in intro:
            parts.append(f'<h2>{e(t)}</h2>' if k in ('H2','PART') else f'<p>{e(t)}</p>')
        # 各经节组折叠块
        for label, slug, grp in blocks:
            prev = ''
            for k, t in grp:
                if k == 'VER':
                    _, vt = ver_label(t)
                    if vt and re.search(r'[A-Za-z]', vt):
                        prev = vt; break
            preview = (prev[:70] + '…') if len(prev) > 70 else prev
            det = f'<details class="owen-vg"><summary><span class="owen-vg-ref">{e(label)}</span>'
            if preview:
                det += f'<span class="owen-vg-prev">{e(preview)}</span>'
            det += '</summary>\n<div class="owen-vg-body">\n'
            det += block_body_faithful(grp)
            det += '\n</div>\n</details>'
            parts.append(det)
        idx = present.index(ch)
        fm = ['---','layout: owen-chapter','book_id: hebrews',
              'book_name: "希伯来书·约翰欧文注释"',f'chapter: {ch}',
              f'title: "第{CN[ch]}章"',f'date: {date}']
        if idx > 0:
            fm += [f'prev_url: "/owen/hebrews/{present[idx-1]}/"', f'prev_label: "第{CN[present[idx-1]]}章"']
        if idx < len(present)-1:
            fm += [f'next_url: "/owen/hebrews/{present[idx+1]}/"', f'next_label: "第{CN[present[idx+1]]}章"']
        fm += ['---','']
        os.makedirs(f'{OUT}/{ch}', exist_ok=True)
        open(f'{OUT}/{ch}/index.md','w',encoding='utf-8').write(
            '\n'.join(fm) + f'# 希伯来书 第{CN[ch]}章\n\n' + '\n\n'.join(parts) + '\n')
        print(f'  {OUT}/{ch}/ ({len(blocks)} 经节组)')
    print(f'共 {len(present)} 章(折叠经节组版)')

def emit_faithful():
    """严格照 PDF: 按章一页, 段落原顺序原样输出。不折叠/不重排/不分级/不切分。"""
    chapters = {}
    for vol in [3,4,5,6,7]:
        for ch, ps in chapter_segments(vol).items():
            if ch not in chapters:
                chapters[ch] = ps
    present = sorted(chapters)
    from subprocess import check_output
    date = check_output(['date','+%Y-%m-%d %H:%M']).decode().strip()
    e = _html.escape
    # 清旧结构(经节组子目录 + 旧 md)
    for d in glob.glob(f'{OUT}/*/'):
        for f in glob.glob(d+'*'): os.remove(f)
        os.rmdir(d)
    for f in glob.glob(f'{OUT}/*.md'): os.remove(f)
    for ch in present:
        lines = []
        for k, t in chapters[ch]:
            if k in ('H2','PART') and re.match(r'CHAPTER\s+\d+\s*$', t):
                continue                       # 章号已在页标题
            if k == 'VER':
                lines.append(f'<p class="owen-ver">{e(t)}</p>')
            elif k in ('H2','PART'):
                lines.append(f'<h2>{e(t)}</h2>')
            else:
                lines.append(f'<p>{e(t)}</p>')
        idx = present.index(ch)
        fm = ['---','layout: owen-chapter','book_id: hebrews',
              'book_name: "希伯来书·约翰欧文注释"',f'chapter: {ch}',
              f'title: "第{CN[ch]}章"',f'date: {date}']
        if idx > 0:
            fm += [f'prev_url: "/owen/hebrews/{present[idx-1]}/"', f'prev_label: "第{CN[present[idx-1]]}章"']
        if idx < len(present)-1:
            fm += [f'next_url: "/owen/hebrews/{present[idx+1]}/"', f'next_label: "第{CN[present[idx+1]]}章"']
        fm += ['---','']
        os.makedirs(f'{OUT}/{ch}', exist_ok=True)
        open(f'{OUT}/{ch}/index.md','w',encoding='utf-8').write(
            '\n'.join(fm) + f'# 希伯来书 第{CN[ch]}章\n\n' + '\n\n'.join(lines) + '\n')
        print(f'  {OUT}/{ch}/ ({len(chapters[ch])} 段)')
    print(f'共 {len(present)} 章(忠实版)')

EXER_OUT = 'owen/hebrews/exercitations'
SERIES = ['约翰欧文导论（Exercitations）', '安息日与主日专论（Day of Sacred Rest）']

def _roman_num(s):
    R={'I':1,'V':5,'X':10,'L':50,'C':100}; tot=0; prev=0
    for c in reversed(s.upper()):
        v=R.get(c,0); tot += -v if v<prev else v; prev=max(prev,v)
    return tot

def nicecase(s):
    """全大写标题 → 词首大写(不越过撇号, 避免 Daniel'S)"""
    s = s.lower()
    return re.sub(r"(?<![A-Za-z'])[a-z]", lambda m: m.group().upper(), s)

def exercitations():
    """-> [{seq, vol, roman, series, title, body:[(k,t)]}] 共 40 篇。
    标题 = EXER 后连续全大写行(含长标题); series 在 roman 重置到 I 时切换。"""
    items = []
    for vol in [1, 2]:
        paras = load(vol)
        idxs = [i for i,(k,t) in enumerate(paras) if k == 'EXER']
        for a, i in enumerate(idxs):
            end = idxs[a+1] if a+1 < len(idxs) else len(paras)
            roman = paras[i][1].replace('EXERCITATION', '').strip().rstrip('.')
            j = i + 1; tparts = []
            while j < end:
                k, t = paras[j]; s = t.strip()
                if re.match(r'^\d+[.,]', s):          # 到内容提要 "1. ..." 停
                    break
                if re.sub(r'[^A-Za-z]', '', s) and s == s.upper():
                    tparts.append(s); j += 1
                else:
                    break
            title = ' '.join(tparts)
            body = paras[j:end]
            items.append({'vol': vol, 'roman': roman, 'title': title, 'body': body})
    # 分系列 + 全局序号
    seq = 0; series = 0; prev_n = 0
    for it in items:
        n = _roman_num(it['roman'])
        if seq > 0 and n == 1 and prev_n >= 1:        # roman 重置到 I = 新系列
            series += 1
        prev_n = n; seq += 1
        it['seq'] = seq; it['series'] = series
    return items

def emit_exercitations():
    from subprocess import check_output
    date = check_output(['date','+%Y-%m-%d %H:%M']).decode().strip()
    e = _html.escape
    items = exercitations()
    # 清旧
    if os.path.isdir(EXER_OUT):
        for f in glob.glob(f'{EXER_OUT}/**/*', recursive=True):
            if os.path.isfile(f): os.remove(f)
    for f in glob.glob(f'{EXER_OUT}/*/'):
        try: os.rmdir(f)
        except OSError: pass
    for it in items:
        seq = it['seq']
        lines = []
        for k, t in it['body']:
            if k == 'EXER':
                continue
            if k in ('H2','PART'):
                lines.append(f'<h2>{e(t)}</h2>')
            elif k == 'VER':
                lines.append(f'<p class="owen-ver">{e(t)}</p>')
            else:
                lines.append(f'<p>{e(t)}</p>')
        htitle = nicecase(it['title']) if it['title'] else f"Exercitation {it['roman']}"
        fm = ['---','layout: owen-chapter','book_id: "hebrews/exercitations"',
              'book_name: "约翰欧文导论"',f'title: "导论 {seq} · {htitle[:50]}"',f'date: {date}']
        if seq > 1:
            p = items[seq-2]
            fm += [f'prev_url: "/owen/hebrews/exercitations/{seq-1}/"',
                   f'prev_label: "导论 {seq-1}"']
        if seq < len(items):
            fm += [f'next_url: "/owen/hebrews/exercitations/{seq+1}/"',
                   f'next_label: "导论 {seq+1}"']
        fm += ['---','']
        head = (f'<div class="owen-exer-eyebrow">{e(SERIES[it["series"]])} · Exercitation {e(it["roman"])}</div>\n\n'
                f'# {e(htitle)}\n\n')
        os.makedirs(f'{EXER_OUT}/{seq}', exist_ok=True)
        open(f'{EXER_OUT}/{seq}/index.md','w',encoding='utf-8').write(
            '\n'.join(fm) + head + '\n\n'.join(lines) + '\n')
    # 索引页
    cards = {}
    for it in items:
        htitle = nicecase(it['title']) if it['title'] else f"Exercitation {it['roman']}"
        cards.setdefault(it['series'], []).append(
            f'<li><a href="{{{{ site.baseurl }}}}/owen/hebrews/exercitations/{it["seq"]}/">'
            f'<span class="exn">{it["seq"]}</span>'
            f'<span class="ext"><b>Exercitation {e(it["roman"])}</b>{e(htitle)}</span></a></li>')
    secs = ''
    for s in sorted(cards):
        secs += f'<h2 class="exer-series">{e(SERIES[s])}</h2>\n<ol class="exer-list">\n' + '\n'.join(cards[s]) + '\n</ol>\n'
    idx = ['---','layout: default','title: 约翰欧文·希伯来书导论','---','']
    open(f'{EXER_OUT}/index.html','w',encoding='utf-8').write('\n'.join(idx) + EXER_INDEX_TMPL.replace('{{SECTIONS}}', secs))
    print(f'导论 {len(items)} 篇 → {EXER_OUT}/  (系列: ' + ', '.join(f'{SERIES[s]}={len([x for x in items if x["series"]==s])}' for s in sorted(cards)) + ')')

EXER_INDEX_TMPL = '''
<div class="container" style="padding-top:80px; max-width:820px;">
  <div style="text-align:center; margin-bottom:10px;">
    <div style="margin-bottom:14px; font-size:13px;"><a href="{{ site.baseurl }}/owen/hebrews/" style="color:#1f5a4b;">&larr; 希伯来书</a></div>
    <h1 style="font-family:Georgia,'Songti SC',serif; color:#1f4a3f; font-size:28px; letter-spacing:.03em;">导论 · Exercitations</h1>
    <div style="color:#1f5a4b; font-size:14px; letter-spacing:.10em; margin-top:6px;">约翰·欧文《希伯来书注释》Vol 1–2</div>
    <div style="color:#9a9a92; font-size:12px; margin-top:6px;">英文版（中文翻译进行中）</div>
  </div>
  {{SECTIONS}}
</div>
<style>
.exer-series{font-family:Georgia,'Songti SC',serif;color:#1f4a3f;font-size:18px;
  margin:34px 0 14px;padding-bottom:8px;border-bottom:1px solid #cfe0d6}
.exer-list{list-style:none;padding:0;margin:0;display:grid;gap:8px}
.exer-list a{display:flex;align-items:baseline;gap:12px;padding:11px 14px;border:1px solid #e2ebe5;
  border-radius:8px;background:#fbfaf6;text-decoration:none;color:#2a2a26;transition:all .15s}
.exer-list a:hover{background:#1f5a4b;border-color:#1f5a4b}
.exer-list a:hover .exn,.exer-list a:hover .ext,.exer-list a:hover b{color:#fff}
.exn{flex:0 0 auto;width:26px;text-align:right;font-family:Georgia,serif;color:#7aa896;font-size:14px}
.ext{font-size:14px;line-height:1.5;color:#3a3a34}
.ext b{display:block;color:#1f5a4b;font-size:12.5px;font-weight:bold;letter-spacing:.02em;margin-bottom:1px}
</style>
'''

if __name__ == '__main__':
    if '--exer' in sys.argv:
        emit_exercitations()
    elif '--emit' in sys.argv:
        emit_verse_collapsed()
    else:
        do_map()
