---
layout: mhenry-preface
book_id: jeremiah
book_name: 耶利米书
header-img: psalm-bg-53.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F0F8D6 0%, #E5EFC8 30%,
        #F0F8D8 60%, #E7F0CC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #262E0D; }

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
    color: #3F500D !important;
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
    color: #262E0D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(193,230,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(185,220,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(216,255,100,0.55);
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
        inset -1px 0 0 rgba(175,200,100,0.12),
        inset 0 -1px 0 rgba(175,200,100,0.15),
        0 12px 40px rgba(128,160,30,0.12);
    color: #566A1A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(145,180,40,0.55) !important;
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
    color: #303D0A !important;
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
        rgba(190,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(190,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(221,255,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(175,200,100,0.12),
        0 10px 36px rgba(128,160,30,0.13),
        0 2px 8px rgba(128,160,30,0.07);
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
    color: #56691C;
    font-size: 1.05em;
    font-family: "LXGW WenKai", "STKaiti", "KaiTi", "楷体", serif !important;
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
    color: #262E0D;
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
    color: #3F500D;
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
    border-left: 3px solid rgba(200,240,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(158,200,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #3F500D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(221,255,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(128,160,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(221,255,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #66801A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(205,240,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #76902A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(158,200,30,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #F9FFE8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(158,200,30,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(140,180,20,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #566A1A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(205,240,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(205,240,100,0.40) !important;
    color: #3F500D !important;
}
.font-size-ctrl button:hover {
    background: rgba(158,200,30,0.30) !important;
    color: #F9FFE8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(205,240,100,0.60) !important;
    color: #3F500D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(158,200,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(241,255,200,0.20) !important;
    border: 1px solid rgba(236,255,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(158,200,30,0.40) !important;
    color: #F9FFE8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(158,200,30,0.60) !important; }
.tts-speed { color: #566A1A !important; }
.tts-speed input[type="range"] { accent-color: #B5D94A !important; }
.tts-progress { background: rgba(236,255,180,0.35) !important; }
.tts-progress-fill { background: rgba(158,200,30,0.55) !important; }
.tts-highlight { background: rgba(158,200,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(205,240,100,0.35) !important;
    border-top: 1px solid rgba(205,240,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(180,220,60,0.55) !important;
    text-shadow: 0 0 12px rgba(211,255,80,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(158,200,30,0.30) !important;
    border: 1px solid rgba(236,255,180,0.60) !important;
    color: #F9FFE8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(128,160,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(158,200,30,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(236,255,180,0.70) !important;
    color: #3F500D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(128,160,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(128,160,30,0.18) !important;
}
.mh-footer p {
    color: rgba(145,180,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(205,240,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>
  <div class="preface-book-name">耶利米书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>旧约先知书和新约书信一样，其编排顺序都按篇幅长短，而不是按时间顺序：排在前面的是最长的，不是最早的。和以赛亚同时代的有好几位先知和圣经笔者，譬如弥迦，有比他稍早的，譬如何西阿、约珥和阿摩司，也有比他稍晚的，譬如哈巴谷和那鸿；但耶利米书在以赛亚书完成之后很多年才开始动笔，却因其篇幅的缘故，排在以赛亚书之后。神的话语最多的地方，所花的功夫也应该最多，但神的话语即便少一点，也不可轻看，更不可不看。关于预言的概要，我们无需多言，但关于耶利米这位先知，却有几点值得注意：I.他很年轻的时候就当了先知；既开始得早，所以他说这话就是经验之谈：人在幼年负轭，这原是好的（耶利米哀歌3：27），指事奉的轭，也指受苦的轭。耶柔米1指出以赛亚比他要年长不少，故而有炭沾他的口，要除掉他的罪孽（以赛亚书6：7），而神在伸手按耶利米口的时候（耶利米书 1：9），却没有说要除掉他的罪孽，因他那时还年轻，罪孽不多。II.他当先知当了很久，有人算下来有五十年之久，也有人说是四十年。
他从约西亚作王第十三年开始说预言，当时在那位好王治下诸事平安，后来则要对付一个个恶王；我们开始事奉神的时候也许风平浪静，但无人知道何时会狂风骤起。III.他是个责备人的先知，奉神的名，奉差遣揭露雅各的罪孽，警告他们神的审判即将临到；有解经家注意到，因为这个缘故，他说话的风格或语气与以赛亚和其他一些先知相比，显得更直接，更尖锐，更不讲情面。人若奉差遣揭露罪孽，就当放下世人的委婉言语。若要叫罪人悔改，最好的办法就是直言不讳。IV.他是个流泪的先知；他得此称呼，不仅因为他写了耶利米哀歌，也因为他向来心怀悲愤，
眼看着自己的百姓犯罪，眼看着使地荒凉的审判即将临到他们。正因为如此，那些把救主看作是先知的，都觉得他在众先知当中最像耶利米（马太福音 16：14），因他多受痛苦，常经忧患（以赛亚书 53：3）。V.他是个受苦的先知。他受自己同胞的逼迫，比任何一位先知都多，这些我们在这卷书中可以看到；他所处的时代，传道的时代，正处犹太人被迦勒底人毁灭的前夕，当时犹太人的特性似乎和他们被罗马人所毁灭之前的特性十分相似，那时他们杀了主耶稣，又逼迫他的门徒，不得神的喜悦，且与众人为敌，神的忿怒临在他们身上已经到了极处（帖撒罗尼迦前书2：15-16）。耶利米的故事来到最后，是余剩的犹太人强迫他和他们一同下埃及去；根据犹太人和基督徒的传说，他后来在埃及殉道。霍丁格引用了阿拉伯史学家艾尔玛金的说法，说耶利米在埃及继续说预言，谴责埃及人和别国的人，最后被石头打死；还说很多年以后亚历山大在进入埃及时，把耶利米的骸骨找了出来，安葬在亚历山大城。本书前十九章的预言像是他平时讲道的摘要，从广义上谴责罪孽，宣告审判；后面的则更为具体，更有针对性，其中还讲述当时所发生的一些事件，但不按时间顺序。书中不只是有警告，也不乏恩典的应许；凡悔改的，必蒙怜悯，犹太人必蒙拯救离开被掳之地；有的应许清楚指向弥赛亚国度。次经作品中保存了一封信，据说是耶利米写给被掳巴比伦之人的，信中警告他们不可拜偶像，揭露偶像的虚无以及拜偶像之人的愚昧。这封信出现在巴录书2第 4 章。不过那信很可能不是耶利米所写，我认为其中找不到一点像耶利米作品那样的生命和精意。马加比二书32：4 也提到耶利米的故事，说在迦勒底人毁灭耶路撒冷时，耶利米按神的指示，将约柜和香坛带到了尼波山，安放在山上一个洞穴里，然后堵上了门；但跟他一同前往的人，虽在那里作了记号，后来却没能找到。他责备他们不该去找，说那地方不可公开，直到神再次聚集他百姓的时候。我认为这故事也不可信，尽管那里说是记录在册。
我们在阅读耶利米预言时，不由得感叹那时代的人对他的预言竟如此不闻不顾，愿我们吸取教训，多多关注才是，因为这些预言写下来，也是叫我们学功课，是警告我们，警告我们的地土。</p>
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
    color: rgba(180,220,60,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(211,255,80,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(221,255,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(175,200,100,0.10),
        0 10px 36px rgba(128,160,30,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(145,180,40,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #303D0A;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(193,230,80,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(145,180,40,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(185,220,80,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(205,240,100,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(205,240,100,0.35) 100%);
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
        0 8px 28px rgba(128,160,30,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #262E0D !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(158,200,30,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(200,240,80,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(185,220,80,0.35);
}
</style>
