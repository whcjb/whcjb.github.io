"""正文修复清单：脚注被拼进正文 / 页底丢行 / 跨页重复段。来源：中文 PDF。可重跑（已修则跳过）。"""
import re,sys,os
FIX=[
 # 页底脚注定义被拼进正文
 ('genesis/4','回到神面\n\n1约翰·莱特福（1602-1675）：英国传道人，犹太拉比学者，剑桥大学副校长。\n\n前寻求安慰','回到神面前寻求安慰'),
 ('joshua/preface','我们的主耶\n1约翰·莱福特（1602–1675）：英国神职人员，犹太拉比学者。\n2西蒙·帕特里克（1626-1707）：英国神学家，主教。\n3殉道者游斯丁：第二世纪护教学者。\n稣则拯救','我们的主耶稣则拯救'),
 ('judges/1','（第31-32 1约翰·莱福特（1602–1675）：英国神职人员，犹太拉比学者。 2西蒙·帕特里克（1626-1707）：英国神学家，主教。节）','（第31-32节）'),
 ('luke/2','带给世人。\n\n1多马·古德温（1600-1680）：英国新教神学家，传道人。\n\n</div>','带给世人。\n\n</div>'),
 ('luke/2','向世上\n\n1希勒尔（前113-8）：又称希勒尔长老，是犹太教宗教领袖，著名拉比。\n\n一切享乐','向世上一切享乐'),
 ('psalms/104','它的房奥维德（前43-后17）：古罗马诗人。屋','它的房屋'),
 ('zechariah/9','聪明和1钦定本将第1 节中「耶和华的默示应验在哈得拉地」译为「耶和华话语的重担落在哈得拉地」。\n\n计谋','聪明和计谋'),
 ('zechariah/12','耶路撒冷1钦定本将第16 节中的「强壮的」译为「勉强站立的」。 的诸多','耶路撒冷的诸多'),
 ('zechariah/13','也是1钦定本将第5 节中的「我从幼年作人的奴仆」译为「我从幼年向人学放牧」。\n\n这样','也是这样'),
 # 页底丢行（按 PDF 补回）
 ('nahum/2','战车无数，横冲直撞，\n\n跑如闪电','战车无数，横冲直撞，哪怕是在原本有足够空间的宽阔处，也争先恐后；铁车在日光照射下闪烁，好比夜间的火把，飞跑如闪电'),
 ('numbers/24','正所谓：既不能\n\n</div></div>','正所谓：既不能撼动上天，我就求助于地狱。\n\n</div></div>'),
 ('psalms/119','大卫在此迫切祷告的，\n\n（何西阿书14：2）','大卫在此迫切祷告的，是他的甘心祭蒙悦纳，不是囊中的甘心祭，而是口中的甘心祭，是他的祷告和赞美。嘴唇的牛犊（何西阿书14：2）'),
 ('lamentations/preface','还说原先只有第一、第二和</p>','还说原先只有第一、第二和'+open(os.path.join(os.path.dirname(__file__),'lamentations_preface_tail.txt'),encoding='utf-8').read()+'</p>'),
 # 书名页附注
 ('hebrews/preface','<div class="preface-sub">马太亨利注释 · 书卷导言</div>','<div class="preface-sub">马太亨利注释 · 书卷导言</div>\n  <div class="preface-sub">（由威廉·童编撰完成）</div>'),
]
def dedup_matthew5(s):
    # 跨页处拼进「钦定本将第」后把「种苦恨……有什么能比」整段重复了一遍
    c=s.find('\n\n钦定本将第种苦恨')
    if c<0: return s
    d=s.index('有什么能比',c)+5
    a=s.index('种苦恨，应当拔出来'); b=s.index('有什么能比',a)+5
    N=lambda x:re.sub(r'\s','',x)
    assert N(s[a:b])==N(s[c+len('\n\n钦定本将第'):d])
    return s[:c]+s[d:]
done=0
for f,old,new in FIX:
    p=f'mhenry/{f}.md'; s=open(p,encoding='utf-8').read()
    if old in new:          # 新文本包含旧文本：看新文本在不在
        if new in s: continue
    elif s.count(old)==0: continue   # 已修
    if s.count(old)==1: s=s.replace(old,new); open(p,'w',encoding='utf-8').write(s); done+=1
    else: sys.exit(f'NOT UNIQUE {f}: {old[:30]!r}')
p='mhenry/matthew/5.md'; s=open(p,encoding='utf-8').read(); s2=dedup_matthew5(s)
if s2!=s: open(p,'w',encoding='utf-8').write(s2); done+=1
print('applied',done)
