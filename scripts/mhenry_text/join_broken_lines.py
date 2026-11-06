"""mhenry：注释正文在句中被换行/空行断开（多为 PDF 跨页处），接回。经文框（诗行）不动。可重跑。
判据：断点前一字为汉字或「，、（“「」，后一字为汉字或「，。、；：）”」」，中间只有换行。"""
import re,glob,sys
WRITE='--write' in sys.argv
PAT=re.compile(r'([一-鿿，、（“「])\n+([一-鿿，。、；：）”」])')
tot=0;files=0
for p in sorted(glob.glob('mhenry/*/*.md')):
    if p.split('/')[1].endswith('-en'): continue
    s=open(p,encoding='utf-8').read()
    body,sep,rest=s.partition('<aside class="mhenry-footnotes">')
    out=[];last=0;n=0
    # 只处理经文框、样式、脚本之外的部分
    for m in re.finditer(r'<div class="mh-verse"[^>]*>.*?</div>|<style.*?</style>|<script.*?</script>|\A---\n.*?\n---\n',body,re.S):
        seg=body[last:m.start()]
        seg,k=PAT.subn(r'\1\2',seg); n+=k
        out.append(seg); out.append(m.group(0)); last=m.end()
    seg,k=PAT.subn(r'\1\2',body[last:]); n+=k; out.append(seg)
    if n:
        tot+=n; files+=1
        if WRITE: open(p,'w',encoding='utf-8').write(''.join(out)+sep+rest)
print('joins',tot,'files',files)
