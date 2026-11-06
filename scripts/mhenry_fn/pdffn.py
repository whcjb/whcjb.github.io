# extract footnote (marker context, def) pairs from mhenry Chinese PDFs
import fitz,sys,json,re,os
from collections import Counter
def body_size(d):
    c=Counter()
    for pg in list(d)[:60]:
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']: c[round(s['size'],1)]+=len(s['text'])
    return c.most_common(1)[0][0] if c else 12
def page_spans(pg):
    sp=[]
    for b in pg.get_text('dict')['blocks']:
        for l in b.get('lines',[]):
            for s in l['spans']:
                if s['text']=='' : continue
                sp.append((round(s['size'],1),s['origin'][1],s['text']))
    return sp
def extract(path):
    d=fitz.open(path); bs=body_size(d)
    out=[]; stats=Counter(); tail=''
    for pno,pg in enumerate(d):
        sp=[]
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                for s in l['spans']:
                    if s['text'].strip()=='' or s['origin'][1]<45: continue
                    sp.append((round(s['size'],1),s['origin'][1],s['origin'][0],s['text']))
        body_y=[y for sz,y,x,t in sp if sz>=bs-0.5 and len(re.findall(r'[\u4e00-\u9fff]',t))>=2]
        maxy=max(body_y) if body_y else 0
        # footnote area: by lines (y), left-to-right
        foot=sorted([s for s in sp if s[1]>maxy+3],key=lambda s:(round(s[1]),s[2]))
        defs={};cur=None;lasty=None
        for sz,y,x,t in foot:
            tt=t.strip(); first=(lasty is None or abs(y-lasty)>3)
            if first: lasty=y
            mm=re.match(r'^(\d{1,2})([\u4e00-\u9fff“「《（].*)?$',tt) if first and sz<bs-0.5 else None
            if mm and int(mm.group(1))==(cur or 0)+1:
                cur=int(mm.group(1)); defs[cur]=mm.group(2) or ''
            elif cur is not None and sz<bs-0.5:
                defs[cur]+=t
        # body: group into lines by baseline of body-size spans
        bodysp=[s for s in sp if s[1]<=maxy+3]
        lines=sorted({round(y) for sz,y,x,t in bodysp if sz>=bs-0.5})
        def line_of(y):
            # superscripts sit a few points above the baseline
            c=[L for L in lines if -2<=L-y<=10]
            return min(c,key=lambda L:abs(L-y-4)) if c else None
        items=[]  # (line,x,kind,text)
        for sz,y,x,t in bodysp:
            tt=t.strip()
            if sz<bs-0.5 and tt.isdigit():
                L=line_of(y)
                if L is not None: items.append((L,x,'m',tt))
            else:
                L=line_of(y) if sz<bs-0.5 else round(y)
                if L is None: L=round(y)
                items.append((L,x,'t',t.replace(' ','')))
        items.sort(key=lambda z:(z[0],z[1]))
        ctx=tail; cands=[]
        for i,(L,x,k,t) in enumerate(items):
            if k=='m':
                nxt=next((z[3] for z in items[i+1:] if z[2]=='t'),'')
                prv=ctx.replace('⁂','')[-1:] 
                verse_like=(prv in '。！？；”」' or prv=='') and nxt[:1]>='\u4e00' and nxt[:1]<='\u9fff'
                cands.append({'n':int(t),'ctx':ctx,'page':pno+1,'verse_like':verse_like}); ctx=ctx+'⁂'
            else:
                ctx=(ctx+t)[-40:]
        tail=ctx
        K=len(defs)
        def seq(cs):
            e=1;sel=[]
            for c in cs:
                if c['n']==e and e<=K: sel.append(c); e+=1
            return sel
        if K and [c['n'] for c in cands]==list(range(1,K+1)): markers=cands
        elif K:
            markers=seq([c for c in cands if not c['verse_like']])
            if len(markers)<K: markers=seq(cands)
            stats['seqfilter']+=1
        else: markers=cands
        mnums=[m['n'] for m in markers]
        for m in markers:
            m['def']=re.sub(r'\s+',' ',defs.get(m['n'],'')).strip()
            stats['nodef' if not m['def'] else 'ok']+=1
            out.append(m)
        for k in defs:
            if k not in mnums:
                stats['orphan_def']+=1; out.append({'n':k,'ctx':None,'page':pno+1,'def':defs[k].strip()})
    return bs,stats,out
if __name__=='__main__':
    for p in sys.argv[1:]:
        bs,st,out=extract(p)
        print(os.path.basename(p),bs,dict(st))
