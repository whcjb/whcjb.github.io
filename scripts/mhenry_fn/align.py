import sys,os,glob,re,pickle
from collections import Counter,defaultdict
sys.path.insert(0,os.path.dirname(__file__))
import fnscan
W=pickle.load(open(os.path.join(os.path.dirname(__file__),'witness.pkl'),'rb'))
ISC=lambda ch:'一'<=ch<='鿿'
def chapkey(f):
    b=os.path.basename(f)[:-3]
    return (0,int(b)) if b.isdigit() else (-1,0)
def norm(body):
    sp=fnscan.protected_spans(body)
    prot=bytearray(len(body))
    for a,b in sp:
        # keep mh-verse text? no: markers never inside verse boxes
        for k in range(a,b): prot[k]=1
    s=[];idx=[]
    for i,ch in enumerate(body):
        if not prot[i] and ISC(ch): s.append(ch); idx.append(i)
    return ''.join(s),idx
def load_book(b):
    ch=[]
    for f in sorted(glob.glob(f'mhenry/{b}/*.md'),key=chapkey):
        s=open(f,encoding='utf-8').read()
        body=s.partition('<aside class="mhenry-footnotes">')[0]
        n,idx=norm(body); ch.append((f,s,body,n,idx))
    return ch
def locate(chs,ctx,K=12,after=None):
    c=''.join(ch for ch in ctx if ISC(ch))
    last='none'
    for k in (K,16,20,24,9,7):
        key=c[-k:]
        if len(key)<k and k>len(c): 
            if len(c)<6: return None,'short'
            key=c
        hits=[(ci,m.end()) for ci,x in enumerate(chs) for m in re.finditer(re.escape(key),x[3])]
        if after is not None and len(hits)>1:
            h2=[h for h in hits if (h[0],chs[h[0]][4][h[1]-1])>after and h[0]<=after[0]+1]
            if len(h2)==1: hits=h2
        if len(hits)==1:
            ci,e=hits[0]; return (ci,chs[ci][4][e-1]),'ok'
        last='multi' if hits else 'none'
    return None,last
if __name__=='__main__':
    tot=Counter()
    for b in sorted(W):
        w=[o for o in W[b] if o['ctx'] is not None and o['def']]
        if not w: continue
        chs=load_book(b); st=Counter()
        for o in w:
            r,why=locate(chs,o['ctx']); st[why]+=1
        tot+=st; print(b,dict(st))
    print(dict(tot))
