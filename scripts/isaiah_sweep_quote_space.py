import re,glob,sys
L=r"A-Za-zÀ-ÿ"
def para(s,log,p):
    # 双引号：段内偶数个才处理，奇数位=开（删其后空格）、偶数位=收（删其前空格）
    pos=[m.start() for m in re.finditer(r'"',s)]
    edits=[]
    if pos and len(pos)%2==0:
        for k,i in enumerate(pos):
            if k%2==0 and s[i+1:i+2]==' ' and re.match(r'[ \*'+L+r']',s[i+2:i+3] or 'x') and s[i+2:i+3]!=' ':
                edits.append((i+1,i+2))
            if k%2==1 and i>0 and s[i-1]==' ' and i>1 and re.match(r'[.,;:!?'+L+r'*)]',s[i-2]):
                edits.append((i-1,i))
    # 单引号：跳过词内撇号与名词所有格；状态机
    st=0
    for m in re.finditer(r"'",s):
        i=m.start(); a=s[i-1] if i else ' '; b=s[i+1] if i+1<len(s) else ' '
        if re.match('['+L+']',a) and re.match('['+L+']',b): continue      # don't / God's
        if a in ' (—\n' and b==' ' :            # 空格包夹：按状态
            if st==0:
                if re.match('[*'+L+']',s[i+2:i+3] or ''): edits.append((i+1,i+2))
                st=1
            else:
                st=0
            continue
        if a in ' (—\n' or i==0: st=1; continue
        if re.match('['+L+r'.,;:!?*)]',a) and b in ' .,;:)—\n': 
            if st==1: st=0
            continue
    if st!=0:   # 段末未闭合：单引号部分不可靠，只保留双引号编辑
        edits=[e for e in edits if s[e[0]-1]=='"' or s[e[1]]=='"']
    for a,b in sorted(set(edits),reverse=True):
        log.append((p,s[max(0,a-25):b+25].replace('\n',' ')))
        s=s[:a]+s[b:]
    return s
if __name__=='__main__':
    apply='--apply' in sys.argv; log=[]
    for p in sorted(glob.glob('alexander/isaiah/[0-9]*.md')):
        t=open(p).read(); fm,body=t.split('\n---\n',1)
        nb='\n'.join(para(x,log,p) for x in body.split('\n'))
        if apply and nb!=body: open(p,'w').write(fm+'\n---\n'+nb)
    print('改',len(log))
    import random; random.seed(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 1)
    for p,s in random.sample(log,min(40,len(log))): print(p[-6:],repr(s))
