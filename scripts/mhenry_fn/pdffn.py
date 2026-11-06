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
        lines=[]
        for b in pg.get_text('dict')['blocks']:
            for l in b.get('lines',[]):
                ss=[(round(s['size'],1),s['origin'][1],s['text']) for s in l['spans'] if s['text'].strip()!='' and s['origin'][1]>=45]
                if ss: lines.append(ss)
        body_y=[y for ss in lines for sz,y,t in ss if sz>=bs-0.5 and not t.strip().isdigit()]
        maxy=max(body_y) if body_y else 0
        markers=[];defs={};cur=None;ctx=tail
        for ss in lines:
            for idx,(sz,y,t) in enumerate(ss):
                tt=t.strip()
                if y>maxy+3:   # footnote area
                    if tt.isdigit() and idx==0 and sz<bs-0.5:
                        cur=int(tt); defs[cur]=''
                    elif cur is not None and sz<bs-0.5:
                        defs[cur]+=t
                    continue
                if sz>=bs-0.5:
                    ctx=(ctx+t.replace(' ',''))[-40:]; continue
                if tt.isdigit():
                    markers.append({'n':int(tt),'ctx':ctx,'page':pno+1}); ctx=ctx+'⁂'
                else:
                    ctx=(ctx+t.replace(' ',''))[-40:]
        tail=ctx
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
