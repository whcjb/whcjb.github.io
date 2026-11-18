#!/usr/bin/env python3
# 用法：/usr/bin/python3 scripts/isaiah_symbol_dropped.py
# PDF 文字层里夹在两英文词间的纯符号残渣（^ \ 1:^3），正文却把两英文词直接相连（左右各两词 6-gram 对位）→ 外文整词被吞
import re,glob,fitz,sys
from pathlib import Path
from collections import Counter
words=set(w.strip().lower() for w in open('/usr/share/dict/words'))
norm=lambda s:re.sub(r'[^a-z]','',s.lower())
md=''
for f in sorted(glob.glob('alexander/isaiah/*.md')):
    t=open(f).read()
    t=re.sub(r'<[^>]+>','',t).replace('*','')
    md+=' '+t
mdtok=[(norm(x) or ('X' if re.search(r'[^\W\d_]',x) else '')) for x in re.findall(r'\S+',md)]
mdtok=[x for x in mdtok if x]
mdbi=Counter(zip(mdtok,mdtok[1:]))
md4=set(zip(mdtok,mdtok[1:],mdtok[2:],mdtok[3:],mdtok[4:],mdtok[5:]))
out=[]
pdfbi=Counter()
pages=[]
for vol,pdf,off in [('v1','propheciesisaiah01alexuoft.pdf',78),('v2','propheciesisaiah02alexuoft.pdf',46)]:
    doc=fitz.open(str(Path.home()/'Documents/论文/alexander'/pdf))
    for pg in doc:
        ws=[w[4] for w in pg.get_text('words')]
        pages.append((vol,pg.number+1-off,ws))
        n=[norm(w) for w in ws]
        pdfbi.update(zip(n,n[1:]))
mdw=set(mdtok)
def isword(a):
    return a in words or a in mdw and len(a)>3 or (a.endswith('s') and a[:-1] in words) or (a.endswith('ed') and (a[:-2] in words or a[:-1] in words)) or (a.endswith('ing') and a[:-3] in words)
def junk(w):
    a=norm(w)
    if not a: return bool(re.search(r'[\^<>=\\|{}~&$#@*_\]\[]',w))
    if re.search(r'[0-9^<>=\\|{}~&$#@*_]|[a-z][A-Z]',w): return True
    return not isword(a) and not w[0].isupper()
for vol,p,ws in pages:
    n=[norm(w) for w in ws]
    for i in range(1,len(ws)-1):
        L,R=n[i-1],n[i+1]
        if len(L)<2 or len(R)<2 or not isword(L) or not isword(R): continue
        if not junk(ws[i]): continue
        if ws[i-1][-1:] in '.;:' : continue
        if '&' in ws[i]: continue
        j=[x for x in n[max(0,i-6):i-1] if x][-2:]; k=[x for x in n[i+2:i+8] if x][:2]
        if len(j)==2 and len(k)==2 and (j[0],j[1],L,R,k[0],k[1]) in md4:
            out.append((vol,p,' '.join(ws[max(0,i-4):i+5])))
for o in out: print(*o)
print(len(out),file=sys.stderr)
