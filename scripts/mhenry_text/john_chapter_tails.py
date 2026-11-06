"""约翰福音：每章文件结尾在句中截断，PDF 中直到下一章标题前的文字缺失。按 PDF（马太亨利圣经注释-约翰福音.pdf）补回。可重跑。"""
import fitz,re,sys,os
PDF='/Users/yanpeifa/Documents/论文/matthew_henry/马太亨利圣经注释-约翰福音.pdf'
WRITE='--write' in sys.argv
ISC=lambda c:'一'<=c<='鿿'
d=fitz.open(PDF)
# 正文：去页眉页脚与页码，逐行保留，供分段
lines=[]
for pg in d:
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            t=''.join(s['text'] for s in l['spans']).strip()
            if not t or t=='马太亨利圣经注释 - 约翰福音' or re.fullmatch(r'\d{1,4}',t): continue
            lines.append(t)
MARK=re.compile(r'^(?:[IVX]+\.|\d+\.|\(\d+\.\)|\[\d+\.\]|第[一二三四五六七八九十]+，)')
raw='';starts=set()
for t in lines:
    if MARK.match(t): starts.add(len(raw))
    raw+=t
cj=[i for i,c in enumerate(raw) if ISC(c)]; P=''.join(raw[i] for i in cj)
HEADS=[]
_pos=0
for t in lines:
    k=raw.find(t,_pos); _pos=k+len(t)
    mm=re.fullmatch(r'第\s*(\d+)\s*章',t)
    if mm: HEADS.append((int(mm.group(1)),k))
def chap_head(n,after):  # PDF 中「第n 章」独立成行（跳过目录）
    for m,k in HEADS:
        if m==n and k>after: return k
    return -1
SEP='<aside class="mhenry-footnotes">'
for n in range(1,22):
    p=f'mhenry/john/{n}.md'; s=open(p,encoding='utf-8').read()
    body,sep,rest=s.partition(SEP)
    m=re.search(r'((?:\s|</div>|</p>)*)$',body); end=len(body)-len(m.group(1))
    tailtxt=body[:end]
    tc=''.join(c for c in re.sub(r'<[^>]+>','',tailtxt[-400:]) if ISC(c))[-14:]
    occ=[x.end() for x in re.finditer(re.escape(tc),P)]
    if len(occ)!=1: print(n,'anchor occ',len(occ),tc); continue
    a=cj[occ[0]-1]+1
    nxt=chap_head(n+1,a) if n<21 else len(raw)
    if nxt<0 or nxt<a: print(n,'no next head'); continue
    add=raw[a:nxt].strip()
    addc=''.join(c for c in add if ISC(c))
    if len(addc)<6: continue
    if addc[:20] in ''.join(c for c in body if ISC(c)): continue   # 已补
    # 分段：PDF 中以条目标号起行处
    # 站内最后一个汉字之后已有的标点/出处，补入时不再重复
    plain=re.sub(r'<[^>]+>','',tailtxt)
    k=max(i for i,c in enumerate(plain) if ISC(c))
    have=plain[k+1:].strip()
    j=a
    while j<nxt and raw[j]==' ': j+=1
    if have and raw[j:j+len(have)]==have: a=j+len(have)
    out=[];last=a
    for st in sorted(x for x in starts if a<x<nxt):
        out.append(raw[last:st]); last=st
    out.append(raw[last:nxt])
    paras=[x.strip() for x in out if x.strip()]
    ins=paras[0]+''.join('\n\n'+x for x in paras[1:])
    if body[end:].lstrip().startswith('</p>'):
        # 段落用 <p> 包的章节
        new=tailtxt+paras[0]+''.join('</p>\n<p>'+x for x in paras[1:])
    else:
        new=tailtxt+ins
    print(n,'+',len(addc),'字 |',repr(tailtxt[-20:]),'⟦',add[:40],'…',add[-30:],'⟧')
    if WRITE: open(p,'w',encoding='utf-8').write(new+body[end:]+sep+rest)
