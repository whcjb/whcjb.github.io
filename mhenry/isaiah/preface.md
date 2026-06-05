---
layout: mhenry-preface
book_id: isaiah
book_name: 以赛亚书
header-img: psalm-bg-52.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6D6F8 0%, #C8C8EF 30%,
        #D8D8F8 60%, #CCCCF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D0D2E; }

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
    color: #0D0D50 !important;
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
    color: #0D0D2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,80,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,80,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,100,255,0.55);
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
        inset -1px 0 0 rgba(100,100,200,0.12),
        inset 0 -1px 0 rgba(100,100,200,0.15),
        0 12px 40px rgba(30,30,160,0.12);
    color: #1A1A6A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,40,180,0.55) !important;
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
    color: #0A0A3D !important;
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
        rgba(100,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,100,200,0.12),
        0 10px 36px rgba(30,30,160,0.13),
        0 2px 8px rgba(30,30,160,0.07);
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
    color: #1C1C69;
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
    color: #0D0D2E;
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
    color: #0D0D50;
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
    border-left: 3px solid rgba(80,80,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,30,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D0D50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,120,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,30,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,120,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A1A80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,100,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A2A90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,30,200,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8E8FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,30,200,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,20,180,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A1A6A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,100,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,100,240,0.40) !important;
    color: #0D0D50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,30,200,0.30) !important;
    color: #E8E8FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,100,240,0.60) !important;
    color: #0D0D50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,30,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,200,255,0.20) !important;
    border: 1px solid rgba(180,180,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,30,200,0.40) !important;
    color: #E8E8FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,30,200,0.60) !important; }
.tts-speed { color: #1A1A6A !important; }
.tts-speed input[type="range"] { accent-color: #4A4AD9 !important; }
.tts-progress { background: rgba(180,180,255,0.35) !important; }
.tts-progress-fill { background: rgba(30,30,200,0.55) !important; }
.tts-highlight { background: rgba(30,30,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,100,240,0.35) !important;
    border-top: 1px solid rgba(100,100,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,60,220,0.55) !important;
    text-shadow: 0 0 12px rgba(80,80,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(30,30,200,0.30) !important;
    border: 1px solid rgba(180,180,255,0.60) !important;
    color: #E8E8FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,30,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(30,30,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,180,255,0.70) !important;
    color: #0D0D50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,30,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,30,160,0.18) !important;
}
.mh-footer p {
    color: rgba(40,40,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,100,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>
  <div class="preface-book-name">以赛亚书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>人但凡知道“先知”一词的含义，都知道这是个很了不起的头衔。然而在世人眼里，许多有此声誉的人仿佛很刻薄。先知十分熟悉天上的事，也十分热衷于天上的事，因而他们在地上有权柄。
先知的预言就是神的启示（彼得后书 1：20，21），因为神的启示常常藉着异梦、声音或异象先传递给先知，再由先知传递给世人（民数记 12：6）。诚然有一次神在西乃山上向数千以色列人直接说话，结果吓得那些人惊恐万状，迫切恳求神，以后向他们说话时还是像过去那样，通过像他们那样的凡人来说话。人不用威严惊吓，也不用势力重压（约伯记33：7）。神允准了他们的请求（他说：他们所说的都是，申命记5：27，28）。于是双方同意，事就这样定了，就是说我们不会再像那些以色列人那样听到神亲口说话，只能通过先知，由他们直接领受神的指示，并负责传递给教会。在旧约正典开始形成以前就有了先知，他们就是教会的圣经。我们的救主似乎承认亚伯是先知（马太福音 23：31，35）。以诺是先知，他最先预言末后的刑罚，末日的审判：看哪，主带著他的千万圣者降临（犹大书1：14）。挪亚是传义道之人（彼得后书 2：5）。神提到亚伯拉罕时说：他是先知（创世纪 20：7）。雅各预言将来的事（创世纪 49：1）。不但如此，
所有的族长都被称为先知：不可恶待我的先知（诗篇 105：15）。摩西是无与伦比的先知，在所有旧约先知中最为杰出，因为神与他面对面说话（申命记 34：10）。他也是第一位使用文字的先知，奠定了圣经文字的第一块基石。连协助他管理百姓的人也具备先知的灵，在那时被圣灵大大充满（民数记 11：25）。然而在摩西死后的好几代人中，耶和华的灵往往是作为争战之灵，而不是先知之灵，在以色列民中显现作工，受感之人往往表现在行为而不是言语；我指的是士师时期。
那时耶和华的灵临到俄陀聂、基甸、参孙等，他们为国效力，用的是刀剑而不是笔杆子。那时天上的信息通过天使传给百姓，就如传给基甸和玛挪亚那样（士师记 2：1）。整卷士师记没有提到过先知，唯有底波拉例外，她被称为女先知。那时耶和华言语稀少，不常有默示（撒母耳记上 3：1）。百姓有摩西律法，不久前才写完，让他们好好研读吧。可是撒母耳复兴了先知的职分，他开创了一个新纪元，也称为新的教会时代。那是一个光明时代，先知一个接一个出现，层出不穷，
一直持续到被掳之后不久，由玛拉基完成旧约正典，然后先知的职分中断了将近 400 年，直到那伟大的先知、主的开路先锋到来。有些先知受圣灵感动记录教会历史，却没有署名。他们的名字被提及，只是用来证明那些历史记载的可靠性，因为当时的历史记录就是由先知写的，譬如迦得，
易多等。大卫和诗篇其他作者是先知，他们写圣诗供教会使用。在他们以后，圣经常提到先知奉差遣去办一些具体的事，或从事一些特定的公共事务，最著名的莫过于以色列国的以利亚和以利沙。不过这些先知没有留下文字，留给我们的只有当时历史书里的一些碎片，除了以利亚写过一封信以外（历代志下21：12），就再也没有他们自己写的东西了（我记得是这样）。然而到了犹大和以色列国的晚期，神开始指示他的先知仆人将他们的讲稿或讲道大纲写下来并加以发表。这些先知的写作日期，有许多已无法确定，但最早出现在被掳之前约 200 年，就是乌西雅做犹大王、
耶罗波安二世做以色列王的时候，也就是约阿施在圣殿的外院杀了耶何耶大的儿子撒迦利亚之后不久。他们可以杀先知，却无法扼杀先知的预言，而存留至今的预言就成了控告他们的证据。何西亚是第一位使用文字的先知。约珥、阿摩司和俄巴底亚也大约在同时期发表了各自的预言。以赛亚晚一些，只是稍晚一些，但他的预言书却排在前面，因为篇幅最长，其中论及众先知都见证的那一位也最多。由于论到基督的内容很多，以赛亚被后世冠以福音先知的美名，实在是当之无愧。有些古人甚至称他为第五福音书的作者。关于这卷书的标题，我们在后面会讨论（第 1 节），
这里只提几个要点：
I.关于这位先知本身。他（我们若相信犹太传说的话）出身于皇室宗亲，家父（据说）是乌西雅王的兄弟。可以肯定，他常在宫中行走，尤其在希西家时代，这在希西家的故事里可以看到。以赛亚书比起其他先知书来显得尤为奇特，尤为优雅，有些地方特别华丽，高耸入云，许多人觉得这样的写作风格与他的出身有关。神的灵有时很会利用先知的特殊才华来成就自己的旨意，因为先知不是圣灵用来传话的传声筒，而是说话的人。圣灵藉他们说话，用他们的自然能力，起到光和火的作用，叫他们达到超然的境界。
II.关于这卷先知书。这卷书超然卓绝，大有益处。在当时对神的教会来说已是如此，定人的罪，
引导人恪守本分，安慰患难中的人。书中提到教会经历的两次大灾难，以及随之而来的安慰。一次发生在与以赛亚同期的西拿基立入侵，另一次是后来发生的巴比伦掳掠。书中满有百姓在这些灾难中急需的帮助和鼓励，恩典的福音比比皆是。福音书所引用的旧约先知书，要数这卷书最多，
恐怕其他先知书全部加起来都不如这卷书多。而论到见证基督，包括他由童贞女所生（第 7 章）
以及他的受难（第 53 章），以赛亚书更是首屈一指。这卷书的开头部分主要斥责罪孽，重申审判，
后面则满有恩言和安慰的话。这样的写法，基督的灵过去在先知书中沿用过，今天仍在沿用，先悔改后得安慰，蒙福得安慰的人须先认罪悔改。毫无疑问，以赛亚讲过很多篇道，也向百姓传递过很多信息，其中很多没有收集在这卷书里，就好比基督的许多信息没有记载下来一样。有可能那些信息比今天所读到的更广泛更全面，但满有无穷智慧的神知道要留下多少信息才适合我们这末世的人（哥林多前书 10：11）。这些先知书和有关基督的历史书，都是要叫我们信耶稣是基督，
是神的儿子，并且叫我们信了他，就可以因他的名得生命（约翰福音20：31）。因为有福音传给我们，像传给他们一样，且比传给当时的人更清楚，好叫我们有信心与所听见的道调和（希伯来书4：2）！</p>
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
    color: rgba(60,60,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(80,80,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(120,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(100,100,200,0.10),
        0 10px 36px rgba(30,30,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(40,40,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #0A0A3D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(80,80,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(40,40,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(80,80,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(100,100,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(100,100,240,0.35) 100%);
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
        0 8px 28px rgba(30,30,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #0D0D2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(30,30,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(80,80,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(80,80,220,0.35);
}
</style>
