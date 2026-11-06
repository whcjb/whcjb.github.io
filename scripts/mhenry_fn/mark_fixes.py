"""手工补标记：PDF 该页脚注定义用正文字号、自动抽取拿不到定义的几处。可重跑。
插入上标后整章按位置重编号、页底重排。"""
import re
MARKS=[
 # (文件, 标记前的锚文本（唯一）, 定义)
 ('psalms/104','怜悯就越大。奥维德','奥维德（前43-后17）：古罗马诗人。'),
 ('hebrews/preface','（由威廉·童','威廉·童（1662–1727）：英国长老会传道人；十三位续写马太亨利圣经注释书的作者之一，负责续写希伯来书和启示录的注释。'),
]
SEP='<aside class="mhenry-footnotes">'
for f,anchor,d in MARKS:
    p=f'mhenry/{f}.md'; s=open(p,encoding='utf-8').read()
    pre,sep,post=s.partition(SEP)
    assert pre.count(anchor)==1,(f,anchor)
    i=pre.index(anchor)+len(anchor)
    if pre.startswith('<sup>',i): continue          # 已标
    k=i
    while k<len(pre) and pre[k].isdigit(): k+=1     # 吃掉原有的普通数字标记
    defs=re.findall(r'<p><sup>\d+</sup>\s*(.*?)</p>',post.partition('</aside>')[0],re.S) if sep else []
    pre=pre[:i]+'<sup>NEW</sup>'+pre[k:]
    order=[];out=[];last=0;n=0
    for m in re.finditer(r'<sup>(\d+|NEW)</sup>',pre):
        n+=1; out.append(pre[last:m.start()]+f'<sup>{n}</sup>'); last=m.end()
        order.append(d if m.group(1)=='NEW' else defs[int(m.group(1))-1])
    out.append(pre[last:]); pre=''.join(out)
    aside='\n'.join(f'<p><sup>{i}</sup> {x}</p>' for i,x in enumerate(order,1))
    if sep:
        s=pre+SEP+'\n'+aside+'\n'+post[post.index('</aside>'):]
    else:
        blk=SEP+'\n'+aside+'\n</aside>\n'
        j=pre.index('<div class="preface-closing">') if '<div class="preface-closing">' in pre else len(pre)
        s=pre[:j]+blk+'\n'+pre[j:]
    open(p,'w',encoding='utf-8').write(s); print('marked',f)
