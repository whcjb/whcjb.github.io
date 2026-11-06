import sys,glob,os,re,pickle
D='/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/cd7386b6-ad90-43f0-9d6c-3c3467ef6739/scratchpad/'
sys.path.insert(0,D)
import textcmp,align2
from collections import Counter
PD=textcmp.PD
old=pickle.load(open(D+'textcmp.pkl','rb'))
R={};EV={}
for b,r in sorted(old.items()):
    mc=textcmp.md_body(b); pc=[]
    for p in r['pdfs']: pc+=textcmp.pdf_body(p)
    P=''.join(c for c,_ in pc); M=''.join(c for c,_ in mc)
    R[b]=dict(pdfs=r['pdfs'],P=P,M=M,pc=pc,mc=mc,cl=[])
    Pv=P.translate(align2.VAR); Mv=M.translate(align2.VAR)
    EV[b]=align2.events(Pv,Mv,align2.align(Pv,Mv))
    c=Counter(e[0] for e in EV[b])
    if b not in('john','romans','philemon'): print(b,dict(c),end='; ')
pickle.dump(R,open(D+'textcmp.pkl','wb')); pickle.dump(EV,open(D+'events.pkl','wb'))
