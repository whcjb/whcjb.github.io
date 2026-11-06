import sys,os,re,pickle,glob
from difflib import SequenceMatcher
sys.path.insert(0,os.path.dirname(__file__))
import fnscan
D=os.path.dirname(__file__)
plans,report=pickle.load(open(os.path.join(D,'plan.pkl'),'rb'))
WRITE='--write' in sys.argv
CJK=lambda s:''.join(c for c in s if '一'<=c<='鿿')
R=lambda a,b:SequenceMatcher(None,CJK(a),CJK(b),autojunk=False).ratio()
bk=lambda f:f.split('/')[1]
def clean_pdf(t):
    t=re.sub(r'(?<=\d)\s+(?=[一-鿿“「（])|(?<=[一-鿿”」）：])\s+(?=\d)','',t)
    return t.strip()
placed_by_book={}
for f,p in plans.items():
    placed_by_book.setdefault(bk(f),[]).extend(m['def'] if m['src']=='site' else m['pdfdef'] for m in p['markers'])
unl_books={}
for u in report['unlocated']: unl_books.setdefault(u[0],[]).append(u[4])
# pdf-sourced defs: prefer the site's wording if the same def sits in another chapter
site_all={}
for f,p in plans.items():
    for d in p['unused']: site_all.setdefault(bk(f),[]).append(d)
manual=[];changed=0;dropped=0
for f,p in sorted(plans.items()):
    s=open(f,encoding='utf-8').read()
    pre,sep,post=s.partition('<aside class="mhenry-footnotes">')
    body=pre
    # unused defs that are not duplicates of a placed def → manual
    keep=[d for d in p['unused'] if not any(R(d,x)>0.8 for x in placed_by_book[bk(f)])]
    if keep: manual.append((f,'unused-nondup',[k[:30] for k in keep])); continue
    ms=sorted(p['markers'],key=lambda m:m['j'])
    if any(ms[i]['j']<ms[i-1]['k'] for i in range(1,len(ms))): manual.append((f,'overlap',None)); continue
    out=[];last=0;defs=[]
    for n,m in enumerate(ms,1):
        out.append(body[last:m['j']]); out.append(f'<sup>{n}</sup>'); last=m['k']
        if m['src']=='site': d=m['def']
        else:
            alt=[x for x in site_all.get(bk(f),[]) if R(x,m['pdfdef'])>=0.6]
            d=alt[0] if alt else clean_pdf(m['pdfdef'])
        defs.append(d)
    out.append(body[last:])
    nb=''.join(out)
    # body must be identical except the markers
    strip=lambda x:re.sub(r'<sup>\d+</sup>','',x)
    a=strip(nb); b=strip(body)
    removed=[body[m['j']:m['k']] for m in ms]
    if a!=re.sub(r'<sup>\d+</sup>','',''.join(body[x:y] for x,y in zip([0]+[m['k'] for m in ms],[m['j'] for m in ms]+[len(body)]))):
        manual.append((f,'bodycheck',None)); continue
    # rebuild aside
    aside='\n'.join(f'<p><sup>{i}</sup> {d}</p>' for i,d in enumerate(defs,1))
    if sep:
        tail=post[post.index('</aside>'):]
        new=nb+sep+'\n'+aside+'\n'+tail
    else:
        blk='<aside class="mhenry-footnotes">\n'+aside+'\n</aside>\n'
        if '<div class="preface-closing">' in nb:
            i=nb.index('<div class="preface-closing">'); new=nb[:i]+blk+'\n'+nb[i:]
        else:
            new=nb.rstrip('\n')+'\n\n'+blk
        manual.append((f,'aside-created',len(defs)))
    dropped+=len(p['unused'])
    if new!=s:
        changed+=1
        if WRITE: open(f,'w',encoding='utf-8').write(new)
print('changed',changed,'dropped_dup_defs',dropped,'manual',len(manual))
for m in manual: print(m)
