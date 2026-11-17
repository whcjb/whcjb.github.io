import re,glob,sys
def fix(seg,c):
    seg,n1=re.subn(r'(?<![\d:])(\d{1,3}):(\d{1,3})\b',r'\1: \2',seg)
    seg,n4=re.subn(r'(\d: \d{1,3})\.(\d{1,3}: \d)',r'\1. \2',seg)      # 1.65: 14 → 1. 65: 14
    seg,n3=re.subn(r' +— +','—',seg)
    seg,n2=re.subn(r'(?<=\S) +—|— +(?=\S)','—',seg)
    seg,n3=re.subn(r' +— +','—',seg)
    c[0]+=n1;c[1]+=n2+n3;c[2]+=n4
    return seg
if __name__=='__main__':
    apply='--apply' in sys.argv; c=[0,0,0]
    for p in sorted(glob.glob('alexander/isaiah/[0-9]*.md')):
        t=open(p).read(); fm,body=t.split('\n---\n',1)
        parts=re.split(r'(<[^>]+>|<!--.*?-->)',body)
        nb=''.join(x if x.startswith('<') else fix(x,c) for x in parts)
        if apply and nb!=body: open(p,'w').write(fm+'\n---\n'+nb)
    print('冒号补空格',c[0],'破折号去空格',c[1],'出处点后补空格',c[2])
