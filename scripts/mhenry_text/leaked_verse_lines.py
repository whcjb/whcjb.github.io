"""mhenry：单元注释末尾漏进了下一单元第一节经文（紧随的经文框里又出现一次）——删掉漏入的那行。可重跑。
判据：注释正文最后一行以节号开头，其汉字串（≥8字）出现在下一个经文框里。"""
import re,glob,sys
ISC=lambda c:'一'<=c<='鿿'
CJK=lambda t:''.join(c for c in t if ISC(c))
WRITE='--write' in sys.argv
tot=0
for p in sorted(glob.glob('mhenry/*/*.md')):
    if p.split('/')[1].endswith('-en'): continue
    s=open(p,encoding='utf-8').read()
    body,sep,rest=s.partition('<aside class="mhenry-footnotes">')
    cuts=[]
    for m in re.finditer(r'<div class="mh-verse">\n(.*?)</div>',body,re.S):
        vb=CJK(m.group(1))
        pre=body[:m.start()]
        # 上一单元正文末尾：跳过结束标签、标题
        t=re.sub(r'(\s|</div>|<div class="mh-date-heading">[^<]*</div>|<div class="mh-unit">)+$','',pre)
        nl=t.rfind('\n'); line=t[nl+1:]
        # 行内：也可能接在句末同一行（" 1「…"）
        mm=re.search(r'(?:^|(?<=[。）」”！？]) )(\d+(?:-\d+)?\s*[「“]?[^\n]*)$',line)
        if not mm: continue
        leak=mm.group(1); c=CJK(leak)
        if len(c)<6 or c[:min(len(c),40)] not in vb: continue
        start=nl+1+mm.start(1); end=len(t)
        # 连同前面的空格/换行
        while start>0 and t[start-1] in ' \n': start-=1
        cuts.append((start,end,leak))
    if not cuts: continue
    for a,b,leak in sorted(cuts,reverse=True):
        tot+=1; print(p[7:],'|',repr(body[max(0,a-15):a]),'⟦',leak[:70],'⟧')
        body=body[:a]+body[b:]
    if WRITE: open(p,'w',encoding='utf-8').write(body+sep+rest)
print('total',tot)
