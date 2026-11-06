import sys,os,glob,re,json,pickle
sys.path.insert(0,os.path.dirname(__file__))
import pdffn
PDFDIR='/Users/yanpeifa/Documents/论文/matthew_henry/'
# book_name -> dir
names={}
for f in glob.glob('mhenry/*/1.md'):
    s=open(f,encoding='utf-8').read()
    m=re.search(r'^book_name:\s*(.+)$',s,re.M)
    if m and not f.split('/')[1].endswith('-en'): names[m.group(1).strip()]=f.split('/')[1]
res={}
for p in sorted(glob.glob(PDFDIR+'*.pdf')):
    b=os.path.basename(p)
    hit=[(n,d) for n,d in names.items() if n in b.replace('列王纪','列王记')]
    hit.sort(key=lambda x:-len(x[0]))
    if not hit: print('nomap',b); continue
    bs,st,out=pdffn.extract(p)
    res.setdefault(hit[0][1],[]).extend([dict(o,pdf=b) for o in out])
pickle.dump(res,open(os.path.join(os.path.dirname(__file__),'witness.pkl'),'wb'))
print({k:len(v) for k,v in res.items()})
