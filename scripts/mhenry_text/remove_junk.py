"""mhenry 正文清理（2026-11-06，对照中文 PDF 全书比对所得）：
1) 早期抽取把页底脚注（或其残段）拼进了正文；2) 小标题文字残留在上一单元末尾。可重跑。"""
import re,glob,sys
SPLICE=[  # (文件, 要删的原文) —— 前后文本直接接上
 ('1kings/17','\n\n1钦定本将第1节下半句译为：这几年必不降露，不下雨，除非我发话。\n\n'),
 ('2samuel/20','\n\n1萨利克法：中世纪以来西欧通行的限制女性继承王位的法典。\n\n'),
 ('acts/4','\n\n1多种翻译本（包括钦定本）26：23中的“首先”修饰“死里复活”：就是基督必须受害，并且首先从死里复活，要把光明的道传给百姓和外邦人。\n\n'),
 ('acts/5','\n\n1多种译本（包括钦定本）将5：1的开头译为：然而，有一个人…。\n\n'),
 ('acts/6','\n\n1钦定本将以赛亚书9：3上半句译为：你使这国民繁多，不加增喜乐。\n\n'),
 ('daniel/5','\n\n1钦定本将传道书2：26上半句译为：神把智慧、知识，和喜乐赐给在他眼中看为善的人。\n\n'),
 ('deuteronomy/13','\n\n1钦定本将第13节中的“匪类”译为“彼列之子”。\n\n'),
 ('genesis/2','\n\n1钦定本将箴言15：32中“轻看自己的生命”译为“轻看自己的灵魂”。\n\n'),
 ('genesis/6','\n\n1这是钦定本诗篇25：14的翻译。和合本译为：耶和华与敬畏他的人亲密。\n\n'),
 ('psalms/107','\n\n1钦定本将申命记32：10中的「环绕他」译为「领他绕圈子」。\n\n'),
 ('1chronicles/25','\n\n数按服事记在下面。\n\n'),
 ('jeremiah/20','\n\n仍看我为尊贵」。\n\n'),
 ('matthew/11','\n\n耶和华眼中仍得荣耀”。\n\n'),
 ('luke/6','\n作「安息日」，与和合本相同。'),
 ('luke/6','\n\n亚兰文的「奋锐党」相似。'),
 ('matthew/12','：英国神职人员。'),
 ('psalms/33','\n摘自使徒信经。'),
 ('psalms/40','\n\n的羔羊。'),
]
SPLICE_KEEP_BREAK=[  # 删后保留段落分隔
 ('matthew/18','\n\n1钦定本将约伯记12：5译为“安逸的人心里藐视行将滑脚的人，当他们是蜡烛。”\n\n'),
 ('psalms/119','\n\n1钦定本将希伯来书3：10中的「心里常常迷糊」译为：心里常常错谬。\n\n'),
]
TAIL_EXTRA={  # 标题残留后面还拖着下一段经文开头的，连同删到单元末尾
 'matthew/20','psalms/103','psalms/95','romans/7'}
TAIL_SKIP={'psalms/53','philemon/1'}
done=0
def save(f,s): open(f'mhenry/{f}.md','w',encoding='utf-8').write(s)
for f,old in SPLICE+SPLICE_KEEP_BREAK:
    s=open(f'mhenry/{f}.md',encoding='utf-8').read()
    body,sep,rest=s.partition('<aside class="mhenry-footnotes">')
    c=body.count(old)
    if c==0: continue
    if c>1: sys.exit(f'NOT UNIQUE {f} {old[:20]!r}')
    body=body.replace(old,'\n\n' if (f,old) in SPLICE_KEEP_BREAK else ''); save(f,body+sep+rest); done+=1
# 重复的标题标签
for f in ['matthew/23']:
    s=open(f'mhenry/{f}.md',encoding='utf-8').read()
    s2=re.sub(r'(<div class="mh-date-heading">([^<]+)</div>)(\s*)<div class="mh-date-heading">\2</div>',r'\1',s)
    if s2!=s: save(f,s2); done+=1
# 标题残留
for p in sorted(glob.glob('mhenry/*/*.md')):
    f=p[7:-3]
    if f.split('/')[0].endswith('-en') or f in TAIL_SKIP: continue
    s=open(p,encoding='utf-8').read(); changed=False
    for m in reversed(list(re.finditer(r'<div class="mh-date-heading">(.*?)</div>',s))):
        H=m.group(1).strip()
        if len(H)<3: continue
        # 回溯到单元末尾正文
        j=m.start()
        mm=re.search(r'((?:\s|</div>)*)$',s[:j]); end=j-len(mm.group(1))
        seg=s[max(0,end-len(H)-120):end]
        # 允许空格差异（「主前840年」/「主前840 年」）
        pat=r'\s*'.join(re.escape(c) for c in H.replace(' ',''))
        mm=list(re.finditer(pat,seg))
        if not mm: continue
        mk=mm[-1]; k=mk.start()
        start=end-len(seg)+k
        after=s[end-len(seg)+mk.end():end]
        H=mk.group(0)
        if f.startswith('romans/'):
            if after not in ('</p>',) and not (f in TAIL_EXTRA): continue
            # <p>H</p> 整段 或 段尾附着
            if s[start-3:start]=='<p>' and after=='</p>': start-=3; end=end
            else: end=end-len('</p>') if after.endswith('</p>') else end
        elif after.strip() and f not in TAIL_EXTRA:
            # 标题后拖着的文字若在下一个经文框里出现（漏进来的第1节），一起删
            nb=re.search(r'<div class="mh-verse">\n(.*?)</div>',s[m.end():],re.S)
            cj=lambda x:''.join(c for c in x if '\u4e00'<=c<='\u9fff')
            if not (nb and len(cj(after))>=6 and cj(after)[:30] in cj(nb.group(1))): continue
        # 吃掉前面的空行
        while start>0 and s[start-1]=='\n': start-=1
        s=s[:start]+s[end:]; changed=True
    if changed: save(f,s); done+=1
print('changed',done)
