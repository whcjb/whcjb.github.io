import fitz,re,glob,os,sys,pickle
from collections import Counter
sys.path.insert(0,os.path.dirname(__file__))
from textcmp import chapkey,ISC,PD
K=10
def pdf_raw(paths):
    raw=[];cj=[];pages=[]   # raw text, cjk->raw offset, cjk->page
    for path in paths:
        d=fitz.open(path); c=Counter()
        for pg in list(d)[:40]:
            for b in pg.get_text('dict')['blocks']:
                for l in b.get('lines',[]):
                    for s in l['spans']: c[round(s['size'],1)]+=len(s['text'])
        bs=c.most_common(1)[0][0]
        for pno,pg in enumerate(d):
            sp=[(s['size'],s['origin'][1],s['text']) for b in pg.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['origin'][1]>=45]
            by=[y for sz,y,t in sp if sz>=bs-0.5 and len(re.findall(r'[一-鿿]',t))>=2]
            maxy=max(by) if by else 0
            for sz,y,t in sp:
                if y>maxy+3: continue
                if sz<bs-1.5 and t.strip().isdigit(): continue
                for ch in t:
                    if ISC(ch): cj.append(len(raw)); pages.append((os.path.basename(path)[:12],pno+1))
                    raw.append(ch)
    return ''.join(raw),cj,pages
MASK=re.compile(r'\A---\n.*?\n---\n|<style.*?</style>|<script.*?</script>|<[^>]+>',re.S)
def md_index(book):
    files={};cj=[]
    for f in sorted(glob.glob(f'mhenry/{book}/*.md'),key=chapkey):
        s=open(f,encoding='utf-8').read(); files[f]=s
        end=s.find('<aside class="mhenry-footnotes">'); end=len(s) if end<0 else end
        m=bytearray(len(s))
        for x in MASK.finditer(s): m[x.start():x.end()]=b'\x01'*(x.end()-x.start())
        for i in range(end):
            if not m[i] and ISC(s[i]): cj.append((f,i))
    return files,cj


LABEL=re.compile(r'\s+(?:[IVX]+\.|\d+\.|\[\d+\.\]|（\d+）)')
def despace(t):
    t=re.sub(r'(?<=\d) +(?=[一-鿿）：，。；])','',t)
    t=re.sub(r'(?<=[一-鿿（：；，]) +(?=\d)','',t)
    return t
def common(a,b):
    n=0
    while n<len(a) and n<len(b) and a[n]==b[n]: n+=1
    return n
def make_insert(raw,pcj,i,j,files,f,off,off2):
    s=files[f]
    prefix=raw[pcj[i-1]+1:pcj[i]]
    body=raw[pcj[i]:pcj[j-1]+1]
    tail=raw[pcj[j-1]+1:(pcj[j] if j<len(pcj) else len(raw))]
    m=LABEL.search(tail)
    if m: tail=tail[:m.start()]
    tail=tail.rstrip()
    body2=re.sub(r'\s*第[一二三四五六七八九十百零]+[章篇]\s*$','',body)
    if body2!=body: tail=''; body=body2
    gap=s[off:off2] if off2>off else s[off:off+200]
    pre=prefix.strip()
    lead=len(gap)-len(gap.lstrip())
    n=common(pre,gap[lead:])
    if n: pos=off+lead+n; pre=pre[n:]
    else: pos=off
    pre=LABEL.sub(lambda m:m.group(0),pre)
    ins=despace((pre+body) if pre else body)
    # tail: drop what's already there
    rest=s[pos:pos+len(tail)+5]
    if rest.startswith(tail): tail=''
    else:
        k=common(despace(tail),rest)
        tail=despace(tail)[k:] if k==len(despace(tail)) else despace(tail)
    return pos,(ins+tail)
