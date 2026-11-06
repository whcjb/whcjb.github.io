import sys,pickle,re
D='/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/cd7386b6-ad90-43f0-9d6c-3c3467ef6739/scratchpad/'
sys.path.insert(0,D)
import restore
R=pickle.load(open(D+'textcmp.pkl','rb')); EV=pickle.load(open(D+'events.pkl','rb'))
NOISE=re.compile(r'目录|来源古旧福音|马太亨利')
props=[];n=0
for b in sorted(EV):
    r=R[b]; raw,pcj,pages=restore.pdf_raw(r['pdfs']); files,mcj=restore.md_index(b)
    P=r['P']; M=r['M']
    for kind,pa,pb,ma,mb in EV[b]:
        if kind=='BIG': print(f'BIG\t{b}\t{pa}-{pb}\t{ma}-{mb}'); continue
        if kind in ('LOSS','REPL'):
            lost=P[pa:pb]
            if NOISE.search(lost) or re.search(r'\.{6,}',raw[pcj[pa]:pcj[pb-1]+1]) or re.fullmatch(r'(箴言)?第[一二三四五六七八九十百零]+[章篇]',lost): continue
            if ma==0: continue
            f,off=mcj[ma-1]; f2,off2=mcj[ma] if ma<len(mcj) else (None,-1)
            if kind=='LOSS':
                pos,ins=restore.make_insert(raw,pcj,pa,pb,files,f,off+1,off2 if f2==f else -1)
            else:
                pos,ins=off+1,None
            n+=1
            props.append(dict(id=n,kind=kind,book=b,file=f,pos=pos,ins=ins,page=pages[pa],lost=lost,md=M[ma:mb]))
        else:
            n+=1; f,off=mcj[ma]
            props.append(dict(id=n,kind='INS',book=b,file=f,pos=off,ins=None,page=pages[min(pa,len(pages)-1)],lost='',md=M[ma:mb]))
pickle.dump(props,open(D+'props3.pkl','wb'))
for p in props:
    s=open(p['file'],encoding='utf-8').read(); pos=p['pos']
    lc=s[max(0,pos-14):pos].replace('\n','⏎'); rc=s[pos:pos+14].replace('\n','⏎')
    if p['kind']=='LOSS': print(f"#{p['id']}\tLOSS\t{p['file'][7:]}\tp{p['page'][1]}\t{lc}⟦{p['ins']}⟧{rc}")
    elif p['kind']=='REPL': print(f"#{p['id']}\tREPL\t{p['file'][7:]}\tp{p['page'][1]}\tPDF[{p['lost'][:120]}]\tMD[{p['md'][:120]}]")
    else: print(f"#{p['id']}\tINS\t{p['file'][7:]}\t{lc}[[{p['md'][:120]}]]")
