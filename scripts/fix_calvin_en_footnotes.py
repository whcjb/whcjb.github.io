#!/usr/bin/env python3
"""从 Ages PDF 脚注附录回填 calvin/<book>-en 缺失的 [^fN] def。
用法: fix_calvin_en_footnotes.py <book-en-dir> <pdf> [--apply]"""
import sys, re, glob, os
import fitz

def parse_appendix(pdf):
    d=fitz.open(pdf)
    # 找附录起点：出现 "FOOTNOTES" 且其后有 ft/FT 编号的页
    start=None
    for i in range(d.page_count):
        t=d[i].get_text()
        if re.search(r'\bFOOTNOTES\b', t, re.I) and re.search(r'\b[Ff][Tt]\d+\b', t):
            start=i; break
    if start is None:
        # 退而求其次：第一页含 ft 编号密集的
        for i in range(d.page_count):
            if len(re.findall(r'\b[Ff][Tt]\d+\b', d[i].get_text()))>=3: start=i; break
    if start is None: return {},None
    full='\n'.join(d[i].get_text() for i in range(start,d.page_count))
    # 去页码行、CHAPTER 分组行、FOOTNOTES 标题行
    lines=[l for l in full.split('\n')
           if not re.match(r'^\s*\d{1,4}\s*$',l)
           and not re.match(r'^\s*CHAPTER\s+\d+\s*$',l,re.I)
           and not re.match(r'^\s*FOOTNOTES\s*$',l,re.I)]
    full='\n'.join(lines)
    m={}
    for n,txt in re.findall(r'\b[Ff][Tt](\d+)[.\s]\s*(.*?)(?=\b[Ff][Tt]\d+[.\s]|\Z)', full, re.S):
        txt=re.sub(r'\s+',' ',txt).strip()
        if txt and (int(n) not in m or len(txt)>len(m[int(n)])): m[int(n)]=txt
    return m, start

def main():
    d_en=sys.argv[1].rstrip('/'); pdf=sys.argv[2]; apply='--apply' in sys.argv
    m,start=parse_appendix(pdf)
    print(f"[{os.path.basename(d_en)}] PDF附录起 idx={start} 解析 ft 条数={len(m)} 范围={min(m) if m else '-'}~{max(m) if m else '-'}")
    # 对齐校验：找一个已有 def 对照
    files=sorted(glob.glob(f'{d_en}/*.md'))
    checked=False
    miss_total=0; uncov=[]
    for f in files:
        t=open(f,encoding='utf-8').read()
        refs=set(int(x) for x in re.findall(r'\[\^f(\d+)\]',t))
        defs={int(x[1]):x[0] for x in [(mo.group(0),mo.group(1)) for mo in re.finditer(r'^\[\^f(\d+)\]: ',t,re.M)]}
        # 对齐校验一次
        if not checked:
            for n in sorted(set(int(x) for x in re.findall(r'^\[\^f(\d+)\]: ',t,re.M))):
                if n in m:
                    cur=re.search(rf'^\[\^f{n}\]: (.*)$',t,re.M).group(1)[:50]
                    print(f"  对齐校验 f{n}: PDF={m[n][:50]!r}\n              MD ={cur!r}")
                    checked=True; break
        miss=sorted(refs-set(int(x) for x in re.findall(r'^\[\^f(\d+)\]: ',t,re.M)))
        if not miss: continue
        cov=[n for n in miss if n in m]; unc=[n for n in miss if n not in m]
        miss_total+=len(miss); uncov+=[(os.path.basename(f),n) for n in unc]
        if apply and cov:
            add='\n\n'+'\n\n'.join(f'[^f{n}]: {m[n]}' for n in cov)+'\n'
            open(f,'w',encoding='utf-8').write(t.rstrip('\n')+add)
        print(f"  {os.path.basename(f)}: 缺{len(miss)} 可补{len(cov)} 无源{len(unc)}"+(f" {unc}" if unc else ""))
    print(f"合计缺 {miss_total}，无源 {len(uncov)}"+(" APPLIED" if apply else " (dry-run)"))

main()
