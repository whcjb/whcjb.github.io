#!/usr/bin/env python3
# 用法：/usr/bin/python3 scripts/isaiah_gap_dropped.py v2 [页...] | python3 scripts/isaiah_gap_filter.py
#      （系统 python 才装了 fitz；SAVE=1 时把候选行图存到 $SCRATCHPAD/j/）
# 行首/行内/行尾异常空白且影像有墨 → 疑似整词漏读
# 分行：按 x 从左到右逐词接续，竖向与该行末词重叠 ≥50% 即同行（抗页面弯曲）
import sys,fitz,statistics,os
from pathlib import Path
OUT=os.environ.get('SCRATCHPAD','/tmp')
os.makedirs(OUT+'/j',exist_ok=True)
vol=sys.argv[1]
pdf={'v1':'propheciesisaiah01alexuoft.pdf','v2':'propheciesisaiah02alexuoft.pdf'}[vol]
off={'v1':78,'v2':46}[vol]; rng={'v1':(1,652),'v2':(1,501)}[vol]
doc=fitz.open(str(Path.home()/'Documents/论文/alexander'/pdf))
pages=[int(x) for x in sys.argv[2:]] or range(rng[0],rng[1]+1)
SAVE=os.environ.get('SAVE')
def ink(pg,r):
    if r.width<4 or r.height<3: return 0
    sp=pg.get_pixmap(dpi=100,clip=r,colorspace=fitz.csGRAY)
    s=sp.samples; return sum(1 for c in s if c<110)/max(1,len(s))
def ov(a,b):
    h=min(a[3],b[3])-max(a[1],b[1]); return h/min(a[3]-a[1],b[3]-b[1])
for p in pages:
    pg=doc[p+off-1]
    ws=sorted([w for w in pg.get_text('words') if w[1]>40 and w[3]-w[1]<20],key=lambda w:w[0])
    lines=[]
    for w in ws:
        best=None;bo=0.5
        for L in lines:
            last=L[-1]
            if last[2]<=w[0]+1:
                o=ov(last,w)
                if o>bo: best,bo=L,o
        if best: best.append(w)
        else: lines.append([w])
    rows=sorted([L for L in lines if len(L)>=3],key=lambda L:L[0][1])
    if len(rows)<5: continue
    left=sorted(r[0][0] for r in rows)[len(rows)//5]
    right=sorted(r[-1][2] for r in rows)[len(rows)*4//5]
    for li,L in enumerate(rows):
        cand=[]
        def box(x0,x1,a,b):
            return fitz.Rect(x0,min(a[1],b[1]),x1,max(a[3],b[3]))
        if L[0][0]-left>14: cand.append(('start',box(left,L[0][0]-1.5,L[0],L[0]),-1,0))
        nxt=rows[li+1] if li+1<len(rows) else None
        if right-L[-1][2]>14 and nxt and nxt[0][0]-left<8: cand.append(('end',box(L[-1][2]+1.5,right,L[-1],L[-1]),len(L)-1,len(L)))
        gaps=[b[0]-a[2] for a,b in zip(L,L[1:])]
        med=statistics.median(gaps)
        for i,g in enumerate(gaps):
            if g>max(9,3*med): cand.append(('mid',box(L[i][2]+1.5,L[i+1][0]-1.5,L[i],L[i+1]),i,i+1))
        for kind,r,a,b in cand:
            d=ink(pg,r)
            if d>float(os.environ.get("INK","0.015")):
                y0=int(min(w[1] for w in L))
                if SAVE: pg.get_pixmap(dpi=250,clip=fitz.Rect(pg.rect.x0,y0-14,pg.rect.x1,max(w[3] for w in L)+3)).save('%s/j/G_%s_%d_%d.png'%(OUT,vol,p,y0))
                prv=rows[li-1] if li>0 else []
                pre=' '.join(w[4] for w in L[max(0,a-3):a+1]) if a>=0 else ' '.join(w[4] for w in prv[-3:])
                post=' '.join(w[4] for w in L[b:b+3]) if b<len(L) else (' '.join(w[4] for w in nxt[:3]) if nxt else '')
                print(vol,p,'y=%d'%y0,kind,round(r.width,1),round(d,3),'|',pre,'[ ]',post,flush=True)
