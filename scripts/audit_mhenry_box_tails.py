#!/usr/bin/env python3
"""经文框尾挂着注释的体检（只读）：按和合本逐字比对找经文终点，终点后剩 ≥10 字且多半不在和合本里的列出。
用法：python3 scripts/audit_mhenry_box_tails.py [book...]"""
import re,sys,json,opencc,difflib,glob,os
sys.path.insert(0,'scripts')
from audit_mhenry_unit_seams import han, HAN
from audit_mhenry_verse_boxes import VAR
from audit_mhenry_verse_numbers import ORDER, verse_numbers
cc=opencc.OpenCC('t2s'); cuv=json.load(open('scripts/zh_cuv.json',encoding='utf-8-sig'))
V2=str.maketrans('阿於裡她祢','啊于里他你')
N=lambda t: han(cc.convert(t)).translate(VAR).translate(V2)
U=re.compile(r'<div class="mh-verse">\n?(.*?)\n?</div>\s*<div class="mh-unit-body">\n*',re.S)
def find_cut(t,exp):
    lh=N(t); sm=difflib.SequenceMatcher(None,lh,exp,autojunk=False)
    end=0; lastb=0
    for blk in sm.get_matching_blocks():
        if blk.size<3: continue
        if blk.a-end<=3 and blk.b>=lastb: end=blk.a+blk.size; lastb=blk.b+blk.size
        elif blk.a-end>3: break
    cnt=0; pos=len(t)
    for i,c in enumerate(t):
        if HAN.match(c):
            cnt+=1
            if cnt==end: pos=i+1; break
    best=None
    for i in range(max(0,pos-60),min(len(t),pos+60)):
        if t[i] in '。！？”’）':
            nxt=N(t[i+1:i+40])[:8]
            if len(nxt)>=6 and nxt not in exp:
                if best is None or abs(i-pos)<abs(best-pos): best=i
    if best is None: return None
    pos=best+1
    while pos<len(t) and t[pos] in '。！？”’）': pos+=1
    return pos
books=sys.argv[1:] or ORDER
for b in books:
    for f in sorted(glob.glob(f'mhenry/{b}/[0-9]*.md')):
        ch=int(re.search(r'(\d+)\.md',f).group(1)); chs=cuv[ORDER.index(b)]['chapters']
        if ch>len(chs): continue
        s=open(f).read()
        for ui,m in enumerate(U.finditer(s),1):
            t=m.group(1); vn=verse_numbers(re.sub(r'<[^>]+>','',t))
            if not vn: continue
            exp=''.join(N(x.replace(' ','')) for x in chs[ch-1][min(vn)-1:])
            pos=find_cut(t,exp)
            if pos is None: continue
            comm=t[pos:].strip()
            ch_=N(comm)
            if len(ch_)>=10:
                # 剩余部分在和合本里的占比
                sm=difflib.SequenceMatcher(None,ch_,exp,autojunk=False)
                cov=sum(x.size for x in sm.get_matching_blocks())/len(ch_)
                if cov<0.5:
                    print(f'{b} {ch} u{ui} 剩{len(ch_)}字 cov{cov:.2f} | …{t[max(0,pos-20):pos]} ‖ {comm[:40]}')
