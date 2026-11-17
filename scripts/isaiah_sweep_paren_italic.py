"""以赛亚书：括注里的异读斜体收尾跑到括号外（`(or *X) Y*` → `(or *X*) *Y*`）。2026-11-17 第 54 章实读后全书扫；
原书括号正体、括注异读斜体、括号后经文续斜体（第 54 章及第 1、10 章影像核过）。罕见前缀 29 处逐条看图，
唯 8:6「(because there is)」系星号错位、另行手改。可重跑（幂等）：python3 scripts/isaiah_sweep_paren_italic.py [--apply]"""
import re,glob,sys
PRE=r'(?:[^()*\n]|\*[^*()\n]*\*){0,40}?'
R=re.compile(r'\((' + PRE + r')\*([^*()\n]+)\)([^*()\n]*)\*')
def fix(m):
    pre,x,rest=m.groups()
    if pre.endswith('I ') or x.strip()!=x: return None
    lead=re.match(r'[,.;:!?\'’"]*',rest).group(0); body=rest[len(lead):]
    if body.strip():
        sp=re.match(r'\s*',body).group(0); b=body[len(sp):]
        if b!=b.rstrip(): return None
        return f'({pre}*{x}*){lead}{sp}*{b}*'
    return f'({pre}*{x}*){lead}{body}'
def run(t,log,p):
    while True:
        out=[];last=0;n=0
        for m in R.finditer(t):
            r=fix(m)
            if r is None: log.append(('SKIP',p,m.group(0))); continue
            out.append(t[last:m.start()]); out.append(r); last=m.end(); n+=1
            log.append(('FIX',p,m.group(0),r))
        out.append(t[last:]); t=''.join(out)
        if not n: return t
if __name__=='__main__':
    apply='--apply' in sys.argv; log=[]
    for p in sorted(glob.glob('alexander/isaiah/[0-9]*.md')):
        s=open(p).read(); fm,body=s.split('\n---\n',1)
        nb=run(body,log,p)
        if apply and nb!=body: open(p,'w').write(fm+'\n---\n'+nb)
    fx=[l for l in log if l[0]=='FIX']; sk=[l for l in log if l[0]=='SKIP']
    print('FIX',len(fx),'SKIP',len(set(sk)))
    for l in sorted(set(sk)): print('SKIP',l[1][-6:],l[2])
    import random; random.seed(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 1)
    for l in random.sample(fx,min(25,len(fx))): print(l[1][-6:],l[2],'\n      →',l[3])
    odd=[l for l in fx if not re.match(r'\((or |literally,? |i\. e\. )\*',l[2])]
    print('--- 非 or/literally/i.e. 前缀',len(odd))
    for l in odd: print(l[1][-6:],l[2],'\n      →',l[3])
