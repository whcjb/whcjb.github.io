#!/usr/bin/env python3
# 读 gaps3 输出，只留正文里 pre/post 英文词直接相连（中间无外文）的候选
import sys,re,glob
norm=lambda s:re.sub(r'[^a-z]','',s.lower())
md=''
for f in sorted(glob.glob('alexander/isaiah/*.md')):
    t=re.sub(r'<[^>]+>','',open(f).read()).replace('*',''); md+=' '+t
tok=[]
for x in re.findall(r'\S+',md):
    # 外文与英文粘连（如 writers.—נפש）拆开
    for part in re.findall(r'[A-Za-zÀ-ÿ\'\-]+|[^\sA-Za-zÀ-ÿ\'\-\d.,;:!?()\[\]—"]+',x):
        n=norm(part); tok.append(n if n else 'X')
s=' '+' '.join(tok)+' '
for line in sys.stdin:
    if '|' not in line: continue
    head,ctx=line.rstrip('\n').split('|',1)
    pre,post=ctx.split('[ ]')
    pr=[norm(w) for w in pre.split() if norm(w)][-2:]; po=[norm(w) for w in post.split() if norm(w)][:2]
    if len(pr)<2 or len(po)<1: continue
    adj=' '+' '.join(pr+po)+' '
    if adj in s: print(line.rstrip())
