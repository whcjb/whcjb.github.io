import fitz,re,glob,os,sys,pickle
from collections import Counter,defaultdict
sys.path.insert(0,os.path.dirname(__file__))
PD='/Users/yanpeifa/Documents/论文/matthew_henry/'
ISC=lambda c:'一'<=c<='鿿'
K=10
def pdf_body(path):
    d=fitz.open(path); out=[]  # list of (char, page)
    from collections import Counter
    c=Counter()
    for pg in list(d)[:40]:
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']: c[round(s['size'],1)]+=len(s['text'])
    bs=c.most_common(1)[0][0]
    for pno,pg in enumerate(d):
        sp=[(s['size'],s['origin'][1],s['origin'][0],s['text']) for b in pg.get_text('dict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] if s['origin'][1]>=45]
        by=[y for sz,y,x,t in sp if sz>=bs-0.5 and len(re.findall(r'[一-鿿]',t))>=2]
        maxy=max(by) if by else 0
        for sz,y,x,t in sp:
            if y>maxy+3: continue
            if sz<bs-1.5 and t.strip().isdigit(): continue
            for ch in t:
                if ISC(ch): out.append((ch,pno+1))
    return out
def chapkey(f):
    b=os.path.basename(f)[:-3]
    return (0,int(b)) if b.isdigit() else (-1,0)
def md_body(book):
    out=[]
    for f in sorted(glob.glob(f'mhenry/{book}/*.md'),key=chapkey):
        s=open(f,encoding='utf-8').read()
        s=s.partition('<aside class="mhenry-footnotes">')[0]
        s=re.sub(r'\A---\n.*?\n---\n','',s,flags=re.S)
        s=re.sub(r'<style.*?</style>|<script.*?</script>|<[^>]+>','',s,flags=re.S)
        for i,ch in enumerate(s):
            if ISC(ch): out.append((ch,f))
    return out
def runs(seq,covered,minlen):
    res=[];i=0;n=len(seq)
    while i<n:
        if not covered[i]:
            j=i
            while j<n and not covered[j]: j+=1
            if j-i>=minlen: res.append((i,j))
            i=j
        else: i+=1
    return res
def compare(pdf_chars,md_chars,minlen=6):
    P=''.join(c for c,_ in pdf_chars); M=''.join(c for c,_ in md_chars)
    ms={M[i:i+K] for i in range(len(M)-K+1)}; ps={P[i:i+K] for i in range(len(P)-K+1)}
    cp=[False]*len(P)
    for i in range(len(P)-K+1):
        if P[i:i+K] in ms:
            for t in range(i,i+K): cp[t]=True
    cm=[False]*len(M)
    for i in range(len(M)-K+1):
        if M[i:i+K] in ps:
            for t in range(i,i+K): cm[t]=True
    # duplicates in md: 30-gram occurring twice
    cnt=Counter(M[i:i+30] for i in range(len(M)-29))
    dup=[i for i in range(len(M)-29) if cnt[M[i:i+30]]>1]
    return P,M,cp,cm,runs(P,cp,minlen),runs(M,cm,minlen),dup

def classify(P,M,lost,ins,F=8):
    """pure loss: flanks adjacent in M; pure insertion: flanks adjacent in P"""
    out=[]
    for i,j in lost:
        L=P[max(0,i-F):i]; R=P[j:j+F]
        k=M.find(L+R) if len(L)==F and len(R)==F else -1
        out.append(('LOSS' if k>=0 else 'SUBL',i,j,k+F if k>=0 else -1))
    for i,j in ins:
        L=M[max(0,i-F):i]; R=M[j:j+F]
        k=P.find(L+R) if len(L)==F and len(R)==F else -1
        out.append(('INS' if k>=0 else 'SUBI',i,j,k+F if k>=0 else -1))
    return out
