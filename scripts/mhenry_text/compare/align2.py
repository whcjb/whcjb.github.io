import sys,pickle,re,bisect
from collections import Counter
from difflib import SequenceMatcher
D='/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/cd7386b6-ad90-43f0-9d6c-3c3467ef6739/scratchpad/'
sys.path.insert(0,D)
VAR=str.maketrans({'她':'他','它':'他','牠':'他','祂':'他','著':'着','甚':'什','罢':'吧','於':'于','裡':'里','麽':'么','啣':'衔','餽':'馈','赒':'周','摺':'折','希':'稀','沈':'沉','作':'做','象':'像','份':'分','借':'藉'})
K=12
def lis_pairs(pairs):
    # pairs sorted by p; longest increasing subsequence on m
    tails=[];tidx=[];prev=[None]*len(pairs)
    for i,(p,m) in enumerate(pairs):
        k=bisect.bisect_left(tails,m)
        if k==len(tails): tails.append(m); tidx.append(i)
        else: tails[k]=m; tidx[k]=i
        prev[i]=tidx[k-1] if k>0 else None
    out=[];i=tidx[-1] if tidx else None
    while i is not None: out.append(pairs[i]); i=prev[i]
    return out[::-1]
def align(P,M):
    cp=Counter(P[i:i+K] for i in range(len(P)-K+1)); cm=Counter(M[i:i+K] for i in range(len(M)-K+1))
    pm={M[i:i+K]:i for i in range(len(M)-K+1) if cm[M[i:i+K]]==1}
    pairs=[(i,pm[P[i:i+K]]) for i in range(len(P)-K+1) if cp[P[i:i+K]]==1 and P[i:i+K] in pm]
    ch=lis_pairs(pairs)
    # blocks: maximal runs where p,m both advance by 1
    blocks=[]
    for p,m in ch:
        if blocks and p==blocks[-1][0]+blocks[-1][2]-K+1 and m==blocks[-1][1]+blocks[-1][2]-K+1:
            blocks[-1][2]+=1
        else: blocks.append([p,m,K])
    # gaps
    gaps=[];pe=0;me=0
    for p,m,n in blocks:
        if p>=pe and m>=me: gaps.append((pe,p,me,m)); pe=p+n; me=m+n
        else: pe=max(pe,p+n); me=max(me,m+n)
    gaps.append((pe,len(P),me,len(M)))
    return gaps
def events(P,M,gaps,minlen=6):
    ev=[]
    for pa,pb,ma,mb in gaps:
        if pb-pa<minlen and mb-ma<minlen: continue
        if pb-pa>4000 or mb-ma>4000: ev.append(('BIG',pa,pb,ma,mb)); continue
        sm=SequenceMatcher(None,P[pa:pb],M[ma:mb],autojunk=False)
        for op,i1,i2,j1,j2 in sm.get_opcodes():
            if op=='delete' and i2-i1>=minlen: ev.append(('LOSS',pa+i1,pa+i2,ma+j1,ma+j1))
            elif op=='insert' and j2-j1>=minlen: ev.append(('INS',pa+i1,pa+i1,ma+j1,ma+j2))
            elif op=='replace' and max(i2-i1,j2-j1)>=minlen:
                r=SequenceMatcher(None,P[pa+i1:pa+i2],M[ma+j1:ma+j2],autojunk=False).ratio()
                if r<0.5: ev.append(('REPL',pa+i1,pa+i2,ma+j1,ma+j2))
    return ev
if __name__=='__main__':
    import restore
    R=pickle.load(open(D+'textcmp.pkl','rb'))
    out={}
    for b,r in sorted(R.items()):
        P=r['P'].translate(VAR); M=r['M'].translate(VAR)
        g=align(P,M); ev=events(P,M,g)
        out[b]=ev
        c=Counter(e[0] for e in ev); print(b,dict(c))
    pickle.dump(out,open(D+'events.pkl','wb'))
