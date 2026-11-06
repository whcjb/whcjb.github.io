import sys,pickle,re
from collections import defaultdict
D='/private/tmp/claude-502/-Users-yanpeifa-Documents-whcjb-github-io/cd7386b6-ad90-43f0-9d6c-3c3467ef6739/scratchpad/'
props=pickle.load(open(D+'props3.pkl','rb'))
SKIP={257,241,177}
WRITE='--write' in sys.argv
by=defaultdict(list)
for p in props:
    if p['kind']!='LOSS' or p['id'] in SKIP or p['book']=='john': continue
    by[p['file']].append(p)
plan=[]
for f,ps in by.items():
    s=open(f,encoding='utf-8').read()
    edits=[]
    for p in ps:
        pos=p['pos']; ins=p['ins'].strip()
        ins=re.sub(r'\s+\d{1,3}$','',ins)
        # inside a verse box? -> move to start of following commentary body
        vb=s.rfind('<div class="mh-verse"',0,pos); cl=s.rfind('</div>',0,pos)
        if vb>cl:
            ub=s.find('<div class="mh-unit-body">',pos)
            if ub<0: print('NO UNIT BODY',f,p['id']); continue
            pos=ub+len('<div class="mh-unit-body">')
            while s[pos]=='\n': pos+=1
            ins=ins.lstrip('」”’')
            if ins.endswith(('：','。')): ins=ins+'\n\n'
            mode='commentary-start'
        else: mode='inline'
        m=re.fullmatch(r'([IVX]+)\.(.+)',ins)
        if m and mode=='inline':
            ins='\n\n<div class="mh-l1"><span class="mh-label">'+m.group(1)+'.</span>\n\n'+m.group(2)+'\n</div>'
            mode='l1-block'
        edits.append((pos,ins,p['id'],mode))
    for pos,ins,i,mode in sorted(edits,reverse=True):
        s=s[:pos]+ins+s[pos:]
        plan.append((i,f,mode))
    if WRITE: open(f,'w',encoding='utf-8').write(s)
print(len(plan),'edits')
from collections import Counter
print(Counter(m for i,f,m in plan))
for i,f,m in plan:
    if m!='inline': print(i,f,m)
