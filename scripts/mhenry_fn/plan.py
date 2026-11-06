import sys,os,re,pickle,json
from collections import Counter,defaultdict
from difflib import SequenceMatcher
sys.path.insert(0,os.path.dirname(__file__))
import fnscan,align
W=align.W
CJK=lambda s:''.join(c for c in s if '一'<=c<='鿿')
def sim(a,b):
    a,b=CJK(a),CJK(b)
    if not a or not b: return 0
    return SequenceMatcher(None,a,b,autojunk=False).ratio()
def site_defs(s):
    fn=s.partition('<aside class="mhenry-footnotes">')[2]
    return [m.group(1).strip() for m in re.finditer(r'<p><sup>\d+</sup>(.*?)</p>',fn,re.S)]
SUPRE=re.compile(r'<sup>(\d+)</sup>')
def marker_pos(body,p,ctx):
    # tail of pdf ctx after its last CJK char
    t=ctx.replace('⁂','')
    i=len(t)
    while i>0 and not ('\u4e00'<=t[i-1]<='\u9fff'): i-=1
    tail=''.join(ch for ch in t[i:] if not ch.isspace())
    j=p+1
    for ch in tail:
        while j<len(body) and body[j] in ' \t': j+=1
        if j<len(body) and body[j]==ch: j+=1
        else: return None
    m=SUPRE.match(body,j)
    if m: return j,m.end()
    k=j
    while k<len(body) and body[k].isdigit(): k+=1
    return j,k
plans={}; report=defaultdict(list)
for b in sorted(W):
    w=[o for o in W[b] if o['ctx'] is not None and o['def']]
    if not w: continue
    chs=align.load_book(b)
    per=defaultdict(list); prev=None
    for o in w:
        r,why=align.locate(chs,o['ctx'],after=prev)
        if r: prev=r
        if why=='ok-verse': report['inverse'].append((chs[r[0]][0],o['ctx'][-12:]))
        if not r: report['unlocated'].append((b,o['page'],why,o['ctx'][-15:],o['def'][:30])); continue
        ci,p=r; body=chs[ci][2]
        r2=marker_pos(body,p,o['ctx'])
        if r2 is None: report['tailmismatch'].append((chs[ci][0],o['page'],o['ctx'][-15:],body[p-8:p+12],o['def'][:30])); continue
        j,k=r2
        d=body[j:k]
        if d and not d.startswith('<sup'):
            ns=str(o['n'])
            if body[k:k+1] in '：:' and body[k+1:k+2].isdigit():
                if d==ns: pass
                elif d.startswith(ns): k=j+len(ns)
                else: report['digitmismatch'].append((chs[ci][0],o['page'],o['n'],body[j-10:k+4])); continue
            elif len(d)<=2: pass
            else: report['digitmismatch'].append((chs[ci][0],o['page'],o['n'],body[j-10:k+4])); continue
        per[ci].append(dict(j=j,k=k,digits=body[j:k],pdfdef=o['def'],page=o['page']))
    for ci,(f,s,body,n,idx,nv,idxv) in enumerate(chs):
        sd=site_defs(s)
        ms=sorted(per.get(ci,[]),key=lambda x:x['j'])
        if not ms and not sd: continue
        used=set()
        for m in ms:
            best=max(((sim(d,m['pdfdef']),i) for i,d in enumerate(sd) if i not in used),default=(0,None))
            if best[0]>=0.6: m['def']=sd[best[1]]; used.add(best[1]); m['src']='site'
            else: m['def']=m['pdfdef']; m['src']='pdf'
        unused=[sd[i] for i in range(len(sd)) if i not in used]
        plans[f]=dict(markers=ms,unused=unused,nsite=len(sd))
pickle.dump((plans,report),open(os.path.join(os.path.dirname(__file__),'plan.pkl'),'wb'))
st=Counter()
for f,p in plans.items():
    for m in p['markers']: st['m_'+('hasdigit' if m['digits'] else 'nodigit')]+=1; st['def_'+m['src']]+=1
    st['unused_defs']+=len(p['unused'])
print(dict(st)); print('in-verse',report['inverse']); print('unlocated',len(report['unlocated']),'tailmismatch',len(report['tailmismatch']),'digitmismatch',len(report['digitmismatch']))
