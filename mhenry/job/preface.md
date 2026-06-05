---
layout: mhenry-preface
book_id: job
book_name: 约伯记
header-img: psalm-bg-47.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6EDF8 0%, #C8E2EF 30%,
        #D8EDF8 60%, #CCE4F0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D232E; }

/* 顶部导航栏：玻璃面板 */
.mh-nav-bar {
    background: rgba(255,255,255,0.30) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border-bottom: 1px solid rgba(255,255,255,0.60) !important;
    border-radius: 0 !important;
    margin-bottom: 0 !important;
    padding-top: 10px !important;
    padding-bottom: 10px !important;
}
.mh-nav-bar a {
    color: #0D3A50 !important;
    font-size: 13px;
    text-decoration: none;
}
.mh-nav-bar a:hover { text-decoration: underline; }

/* 章节标题 */
#mhenry-col > h2 {
    padding: 36px 20px 10px;
    margin: 0;
    font-size: 1.55em;
    font-weight: 800;
    color: #0D232E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,180,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,173,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,203,255,0.55);
}

/* 章节综述：水晶玻璃卡 */
.mh-overview {
    margin: 2px 0 32px;
    padding: 24px 20px;
    background: rgba(255,255,255,0.22) !important;
    backdrop-filter: blur(18px);
    -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(255,255,255,0.72) !important;
    border-top: none !important;
    border-radius: 0 0 18px 18px !important;
    box-shadow:
        inset 1px 0 0 rgba(255,255,255,0.80),
        inset -1px 0 0 rgba(100,167,200,0.12),
        inset 0 -1px 0 rgba(100,167,200,0.15),
        0 12px 40px rgba(30,117,160,0.12);
    color: #1A4F6A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,133,180,0.55) !important;
    font-size: 10px !important;
    letter-spacing: 0.35em;
    font-weight: 700;
    margin-bottom: 14px;
}

/* 日期标题：flex 两侧水晶分隔线 */
.mh-date-heading {
    display: flex !important;
    align-items: center;
    gap: 14px;
    margin: 44px 0 16px;
    padding: 6px 0;
    background: rgba(255,255,255,0.22) !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    border: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    color: #0A2C3D !important;
    font-size: 0.9em;
    font-weight: 800;
    letter-spacing: 0.12em;
    line-height: 1.4;
    white-space: nowrap;
    text-shadow: 0 1px 0 rgba(255,255,255,0.7);
}
.mh-date-heading::before,
.mh-date-heading::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(100,180,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,180,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,210,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,167,200,0.12),
        0 10px 36px rgba(30,117,160,0.13),
        0 2px 8px rgba(30,117,160,0.07);
    overflow: clip;
    backdrop-filter: blur(2px);
    -webkit-backdrop-filter: blur(2px);
}

/* 经文块：水晶透明 */
.mh-unit > .mh-verse {
    padding: 18px 20px;
    padding-right: calc(5% + 22px);
    background: rgba(255,255,255,0.22) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border-left: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.45);
    border-radius: 0;
    line-height: 2.1;
    color: #1C4F69;
    font-size: 1.05em;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", serif !important;
    font-weight: 400;
    letter-spacing: 0.05em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}

/* 注释块：磨砂水晶 */
.mh-unit-body {
    padding: 22px 0 20px !important;
    background: rgba(255,255,255,0.28);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    line-height: 2.05;
    color: #0D232E;
    font-size: 0.97em;
    font-family: "Klee One", "STKaiti", "KaiTi", "楷体", serif !important;
    border-radius: 0 0 15px 15px;
    border-left: none !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.60);
}
.mh-unit-body > p {
    margin: 0 0 0.9em;
    text-align: justify;
    text-indent: 2em;
    font-size: 0.96em;
    letter-spacing: 0.02em;
}
.mh-unit-body > p:last-child { margin-bottom: 0; }
.mh-unit-body > p b,
.mh-unit-body > p strong {
    color: #0D3A50;
    font-weight: 700;
}
.mh-unit-body .mh-l1 > p,
.mh-unit-body .mh-l2 > p,
.mh-unit-body .mh-l3 > p { text-indent: 0; }

/* I. II. 大纲（一级） */
#mhenry-col .mh-l1 {
    margin: 26px 0 12px;
    padding: 12px 0;
    background: rgba(255,255,255,0.18) !important;
    border: none !important;
    border-left: 3px solid rgba(80,187,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,143,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D3A50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,210,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,117,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,210,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A5E80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,193,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A6E90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,143,200,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8F7FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,143,200,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,127,180,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A4F6A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,193,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,193,240,0.40) !important;
    color: #0D3A50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,143,200,0.30) !important;
    color: #E8F7FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,193,240,0.60) !important;
    color: #0D3A50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,143,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,237,255,0.20) !important;
    border: 1px solid rgba(180,230,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,143,200,0.40) !important;
    color: #E8F7FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,143,200,0.60) !important; }
.tts-speed { color: #1A4F6A !important; }
.tts-speed input[type="range"] { accent-color: #4AA9D9 !important; }
.tts-progress { background: rgba(180,230,255,0.35) !important; }
.tts-progress-fill { background: rgba(30,143,200,0.55) !important; }
.tts-highlight { background: rgba(30,143,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,193,240,0.35) !important;
    border-top: 1px solid rgba(100,193,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,167,220,0.55) !important;
    text-shadow: 0 0 12px rgba(80,197,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(30,143,200,0.30) !important;
    border: 1px solid rgba(180,230,255,0.60) !important;
    color: #E8F7FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,117,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(30,143,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,230,255,0.70) !important;
    color: #0D3A50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,117,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,117,160,0.18) !important;
}
.mh-footer p {
    color: rgba(40,133,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,193,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">智慧简介</div>
  <div class="preface-book-name">约伯记</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>约伯记这卷书自成一体，与其它书卷不相连，所以要单独查考。不少希伯来文圣经抄本将此书排在诗篇之后，有些更是将其排在箴言之后。也许因为这点，一些学者猜想这是以赛亚或更晚期的先知写的。但是此书的题材看起来相当古老，我们有理由认为这应该是更早期的作品，因此此书排在智慧书卷集的首位十分合宜。另外，这是一卷说教型的书，将其排在前面，引出灵修型的诗篇和实用型的箴言也十分恰当。因为若不认识神，如何敬拜神、顺服神呢？关于这卷书：I. 我们肯定此书的写成是神的感动，尽管我们不能肯定执笔人是谁。犹太人虽然不是约伯的朋友（他对以色列国来说是外邦人），但神的圣言交托他们（罗马书3：2），他们就忠实保留下来，且一向将此书放在神圣的正典中。有一位使徒曾提及这段历史（雅各书5：11），另一位使徒曾引用了其中一句（5：13），且冠以“经上记着说”（哥林多前书3：19），如同引用其他经文一样。不少古人认为这段历史是摩西在米甸所写，送给在埃及受苦的弟兄，支持和安慰重负之下的人，要他们盼望神必在适当的时候拯救他们，兴旺他们，就像他拯救这位坚忍的受苦者一样。有人猜这卷书原来是用阿拉伯文写的，后来由所罗门或某位受感的作者翻译成希伯来文（胡里艾先生就是这么认为）（译者注：胡里艾是十七世纪法国新教领袖），为犹太教会所用。但我认为此书的执笔者最有可能是以利户，至少他写了对话部分，因为（32：15，16）他说的话汇合了史学家和辩论家的言辞。摩西也许写了前面两章和最后一章，诠释了这些对话。因为这几章经文中多次称神为耶和华，而在对话部分除了第十二章第九节，没有一次是这样称呼的。这个名称在摩西以前的族长时代鲜为人知（出埃及记6：3）。若是约伯自己所写，那么一些犹太作者就承认约伯是外邦人中的先知。若是以利户所写，那么以利户就有先知的灵，因为他的言语满怀；他里面的灵激动他（约伯记32：18）。<br/>II. 我们肯定此书中的故事基本上是历史事实，不是虚构，尽管对话采用诗的形式。约伯这个人物真实存在，这是毫无疑问的。先知以西结曾将他与挪亚和但以理同列（以西结书14：14）。我们在这里读到的叙述，包括他的亨通和敬虔、他独特的苦难和典型的坚忍、他与朋友之间的对话、神在旋风中对他说的话，以及他最终恢复亨通的环境，这些都无疑是真实的。不过受感的执笔者可以自由发挥，用自己的语言来表达约伯和他朋友的对话。<br/>III. 我们肯定此书十分古老，尽管我们不能确定约伯具体生活的时代，也不十分确定此书的写作时间。但书中皓发明显，就是远古的迹象。我们有理由相信它的年代与创世记相仿，圣洁的约伯应该与以撒和雅各为同时代人。他虽然不像他们那样承继应许之地迦南，却与他们一起羡慕一个更美的家乡，就是在天上（希伯来书11：16）。也许他是亚伯拉罕的兄弟拿鹤的后代。拿鹤的长子名叫乌斯（创世记22：21），家中的信仰似乎持续了一段日子（创世记31：53）。在那里神不但称为亚伯拉罕的神，也称为拿鹤的神。约伯生活的年代早于人的年岁缩短到七十或八十岁（就是摩西时代），早于只在一个祭坛上献祭的时代，也早于各国不认识神、不敬拜真神的时代。在约伯时代没有偶像崇拜，即便是崇拜日月，也会受到审判官的严惩（31：26-28）。在他生活的时代，神被称为全能者而不是耶和华神，因为神在此书中被称为全能者达三十多次。在他生活的年代，神的知识不是通过文字传递而是通过口传，例如8：8；21：29；15：18；5：1 等。我们有理由相信他生活的年代早于摩西，因为这里只字不提以色列民出埃及，也不提律法颁布。有一个地方似乎可以理解为法老淹死：他以能力搅动大海；他藉知识打伤拉哈伯（26：12）。圣经中常称埃及为拉哈伯（诗篇87：4；89：10；以赛亚书51：9）。不过那也可能指傲慢的海浪。因此我们认为此书将我们带回到了族长时代。我们肃然起敬，不仅因为此书的权威性，也因为它的古老年代。<br/>IV. 我们肯定此书对教会大有益处，为每一位良善的基督徒造福，尽管书中多有暗晦难明的地方。<br/>也许我们无法确定其中每一个字句的确切含义，连评论家们也都伤透脑筋。但其中也有许多明确的内容，整体来看足以使人得益处，值得我们好好研习。<br/>1. 这首高贵的长诗以十分清晰生动的方式向我们展现了至少五个方面：（1）此书展现了原始神学的丰碑。书中那激烈、亢长又有学识的辩论，展现了最早的自然之光的大原则，也就是信仰的基础。不但辩论各方都同意这一点，都对此深信不疑，而且都明显将之奉为永恒的真理，奉为意义深远且不容置疑的真理。有谁能比此书更清晰、更完全、更尊崇、更精彩地论及神的存在，论及他荣耀的特性和完美、深不可测的智慧、不可抗拒的能力、无法测度的荣耀、刚正不变的公义以及他不容挑战的主权？书中以赞美的口吻描述神创造世界，管理世界，不是因为风景独好，而是叫人心生敬畏和事奉的心志，谦卑顺服造我们的主，主神，统治者。道德方面的善恶从未如此贴近生活（善之完美和恶之丑陋），神的审判法则从未如此不容质疑地得到坚立，就是义人必享福乐，恶人必遭灾难（以赛亚书3：10-11）。这些绝不是供学者研究的学术课题，也不是叫百姓惧怕的国家机器。都不是，此书所展现的是十分明确的神圣真理，是任何一个时代有智慧有头脑的人都顺服的真理。（2）此书展现了外邦人敬虔的范例。这位伟大的圣者可能不是亚伯拉罕的后裔，而是拿鹤的后裔。即使他是亚伯拉罕的后裔，也不是以撒的后裔，而是被打发往东方去的某个庶出的儿子的后裔（创世记25：6）。即使他是以撒的后裔，也不是雅各的后裔，而是以扫的后裔。<br/>总之他不属于特殊圣约的范围，不是以色列人，也不是皈依犹太教者，但却无人像他那样虔诚。<br/>除他以外，世上没有那样的天之骄子。因此远在圣彼得还未明白以前，这点就已经是不争的事实：原来，各国中那敬畏主、行义的人都为主所悦纳（使徒行传10：35）。除了本国的子民（马太福音8：11，12），神尚有四散的子民（约翰福音11：52）。（3）此书展现了对天意的诠释，对许多又难又隐晦的问题作出清楚满意的解释。恶人亨通、义人受难，这一向被认为是书中最大的两个难点，但这些事的结局（但以理书12：8）都符合神的智慧、纯全和良善。（4）此书展现了坚忍的范例，就是在最痛苦的患难中紧紧倚靠神。理查德·布拉克摩男爵（译者注：十七世纪英国诗人）注释过此书，在前言里他妙笔生辉地把约伯写成史诗般的英雄。他写道：“他在苦难中显得勇敢，在困境中显得坚定，在地狱之恶所发出的最大限度的挑衅下，仍持守自己的道德，持守自己的品格，因而他以最高贵的方式展现了坚忍的风范。这样的品格绝不逊色于冲锋陷阵的英雄。”（5）此书展现了基督的形象，具体细节我们在后面会谈到。简单来说，约伯是伟大的受苦者，他被倒空，被降为卑，为的是更大的荣耀。照样基督降卑自己，好叫我们升高。学识渊博的帕特里克主教不止一次引用圣耶柔米所言，论到约伯是基督的预表。他因那摆在前面的喜乐，就轻看羞辱，忍受了十字架的苦难（希伯来书12：2）。他暂时受人的逼迫也受魔鬼的逼迫，神仿佛也曾离弃了他。但他却被高举，且为加增他苦难的朋友作了中保。使徒雅各一提到约伯的忍耐，就立即想起主给他的结局，就是约伯所预表的主耶稣的结局（正如有些人这样理解）（雅各书5：11）。<br/>2. 在这卷书中我们看到，（1）约伯受苦的过程，以及在苦难中的忍耐，第1，2 章，其中不乏人的软弱，第3 章。（2）他与朋友们就苦难问题展开的辩论，其中， [1] 辩论的对手是以利法，比勒达和琐法。[2] 回应者是约伯。[3] 仲裁者先是以利户，第32-37 章，后是神，第38-41 章。（3）结局是约伯重获尊荣，再度兴旺，第42 章。总而言之，我们看到义人多有苦难，但耶和华救他脱离这一切（诗篇34：19），叫他们的信心既被试验，就可以得著称赞、荣耀、尊贵（彼得前书1：7）。</p>
</div>

<div class="preface-closing">✦ &ensp; ✦ &ensp; ✦</div>

</div>

<style>
/* ── 前言装饰 ── */
.mhenry-preface-body { padding: 8px 20px 24px !important; }

.preface-wrap {
    margin: 12px 0 32px;
    padding: 0;
}

/* 顶部星形装饰 */
.preface-emblem {
    text-align: center;
    font-size: 22px;
    color: rgba(60,167,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(80,197,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(120,210,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(100,167,200,0.10),
        0 10px 36px rgba(30,117,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(40,133,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #0A2C3D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(80,180,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(40,133,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(80,173,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(100,193,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(100,193,240,0.35) 100%);
}

/* 正文区 */
.preface-body {
    background: rgba(255,255,255,0.22);
    border: 1px solid rgba(255,255,255,0.60);
    border-radius: 14px;
    padding: 0;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 8px 28px rgba(30,117,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #0D232E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(30,143,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(80,187,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(80,173,220,0.35);
}
</style>
