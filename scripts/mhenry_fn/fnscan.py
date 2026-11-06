import re,glob,sys,json
CJK=r'一-鿿'
PREV_OK=re.compile(r'[一-鿿）」”》』\)\]’]')
NEXT_OK=re.compile(r'[一-鿿，。；！？、）」”》：\(（—…\s<]|$')
def protected_spans(s):
    sp=[]
    for m in re.finditer(r'<style.*?</style>|<script.*?</script>|<div class="mh-verse"[^>]*>.*?</div>|<[^>]+>|^#[^\n]*$|\A---\n.*?\n---\n',s,re.S|re.M):
        sp.append((m.start(),m.end()))
    return sp
def scan(s):
    body,sep,fn=s.partition('<aside class="mhenry-footnotes">')
    nd=len(re.findall(r'<p><sup>\d+</sup>',fn))
    sp=protected_spans(body)
    def prot(i): return any(a<=i<b for a,b in sp)
    c=[]
    for m in re.finditer(r'(?<![0-9])(\d{1,2})(?![0-9])',body):
        i,j=m.start(),m.end()
        if prot(i): continue
        p=body[i-1] if i else ''; n=body[j] if j<len(body) else ''
        n2=body[j:j+2]
        if not PREV_OK.match(p): continue
        if p=='第': continue
        if not NEXT_OK.match(n): continue
        if n in '节章篇年月日岁次个位': continue
        if re.match(r'：\d|:\d|[\.．]',n2) or n in '.．-–': continue
        if p in '（(' : continue
        # "（1）" list
        if p=='（' or (n=='）' and body[i-1:i]=='（'): continue
        c.append((i,j,m.group(1)))
    return body,fn,nd,c
if __name__=='__main__':
    res={'ok':[],'bad':[]}
    for f in sorted(glob.glob('mhenry/*/*.md')):
        if f.split('/')[1].endswith('-en'): continue
        s=open(f,encoding='utf-8').read()
        if 'mhenry-footnotes' not in s: continue
        body,fn,nd,c=scan(s)
        nsup=len(re.findall(r'<sup>\d+</sup>',body))
        res['ok' if len(c)+nsup==nd else 'bad'].append((f,nd,len(c),nsup))
    print('ok',len(res['ok']),'bad',len(res['bad']))
    for r in res['bad']: print(*r)
