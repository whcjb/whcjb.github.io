---
layout: mhenry-preface
book_id: judges
book_name: 士师记
header-img: psalm-bg-36.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F8F5D6 0%, #EFECC8 30%,
        #F8F5D8 60%, #F0EDCC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E2B0D; }

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
    color: #504A0D !important;
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
    color: #2E2B0D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(230,218,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(220,208,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(255,242,100,0.55);
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
        inset -1px 0 0 rgba(200,192,100,0.12),
        inset 0 -1px 0 rgba(200,192,100,0.15),
        0 12px 40px rgba(160,149,30,0.12);
    color: #6A631A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(180,168,40,0.55) !important;
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
    color: #3D390A !important;
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
        rgba(220,210,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(220,210,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(255,244,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(200,192,100,0.12),
        0 10px 36px rgba(160,149,30,0.13),
        0 2px 8px rgba(160,149,30,0.07);
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
    color: #69621C;
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
    color: #2E2B0D;
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
    color: #504A0D;
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
    border-left: 3px solid rgba(240,227,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(200,186,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #504A0D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,244,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(160,149,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(255,244,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #80781A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(240,228,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #90882A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(200,186,30,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFFDE8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(200,186,30,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(180,167,20,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #6A631A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(240,228,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(240,228,100,0.40) !important;
    color: #504A0D !important;
}
.font-size-ctrl button:hover {
    background: rgba(200,186,30,0.30) !important;
    color: #FFFDE8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(240,228,100,0.60) !important;
    color: #504A0D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(200,186,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(255,250,200,0.20) !important;
    border: 1px solid rgba(255,249,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(200,186,30,0.40) !important;
    color: #FFFDE8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(200,186,30,0.60) !important; }
.tts-speed { color: #6A631A !important; }
.tts-speed input[type="range"] { accent-color: #D9CD4A !important; }
.tts-progress { background: rgba(255,249,180,0.35) !important; }
.tts-progress-fill { background: rgba(200,186,30,0.55) !important; }
.tts-highlight { background: rgba(200,186,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(240,228,100,0.35) !important;
    border-top: 1px solid rgba(240,228,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(220,207,60,0.55) !important;
    text-shadow: 0 0 12px rgba(255,240,80,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(200,186,30,0.30) !important;
    border: 1px solid rgba(255,249,180,0.60) !important;
    color: #FFFDE8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(160,149,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(200,186,30,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255,249,180,0.70) !important;
    color: #504A0D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(160,149,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(160,149,30,0.18) !important;
}
.mh-footer p {
    color: rgba(180,168,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(240,228,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">历史简介</div>
  <div class="preface-book-name">士师记</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>这卷书希伯来文名叫士师记，亚兰文和阿拉伯文的版本则称作以色列民的士师记；那民的审判很特别，他们的士师也很特别，其职任与别国的审判者有很大差异。七十士译本的书名是士师记。
本书说的是士师治理时期的以色列国民史，从俄陀聂到以利，按神的意思摘录而成，传给我们。
按照莱福特博士1的计算，这段历史跨越299 年，其中犹大的俄陀聂40 年，便雅悯的以笏 80 年，
拿弗他利的巴拉 40 年，玛拿西的基甸 40 年，他儿子亚比米勒 3 年，以萨迦的陀拉 23 年，玛拿西的睚珥 22 年，玛拿西的耶弗他 6 年，犹大的以比赞 7 年，西布伦的以伦10 年，以法莲的押顿
8 年，但支派的参孙 20 年，一共 299 年。至于在别国之下为奴的那些年，例如本书提到伊矶伦欺压他们十八年，雅宾二十年，还有其他，这些应该都与各士师时期重叠。这里的士师似乎来自八个不同的支派，士师的荣誉由多个支派共享，直到最后以犹大为中心。以利和撒母耳这两位士师不在本书范围，他们属于利未支派。流便、西缅、迦得和亚设支派似乎没有士师。本书直到第十六章，都按时间顺序讲述士师的故事。最后五章讲一些特别值得纪念的事件，这些事件都发生在士师秉政的时候（路得记1：1），但具体发生在哪个士师时代，则不能确定；这些故事编排在书的后面，免得整体故事描述被打断。关于这个时期以色列国的情形：I.这样的子民，有如此全备的律法和丰富的应许，其现状却不如想象中那样优秀，甚至是乏善可陈。他们败坏之极，又被邻国欺压之极，整卷书中，不论是打仗还是内务，都与当年凯旋进入迦南时的情形相差甚远。我们能说什么好呢？神借此向我们表示，日光之下的人或物何其不完美，真是可叹，这是要叫我们在另一个世界寻求完美的圣洁和喜乐，而不是这个世界。不过：II.尽管我们的史学家用大量篇幅描写他们受苦受难，那地仍有信仰的痕迹，无论多少人受引诱，走上偶像的歧途，会幕的服事仍在按摩西律法所规定的继续进行，并且仍有许多人参加。史学家们一般不写国中属于常态的日常司法和商业活动，只写战争和动乱，但读者应当从多方面考虑，才能平衡这些故事的阴暗面。III.这段时期，各支派似乎大都处于自治自理的状态，各自为政，没有共同的领袖或领导小组，导致相互之间许多分歧，以致成不了大国，也成不了大事。IV.士师治理并非常态，而是随机出现；书中说以笏得胜后，国中太平八十年（3：30），巴拉得胜后，国中太平四十年（5：31），但没有说这段时间他们是否还在治理，甚至不知他们是否还活着；然而，他们和其他士师的兴起，都是受神的灵感动，在特定情形下进行某项特定的服事，抗击以色列的仇敌，摒弃以色列的偶像；士师的主要职能就是这两件事。但女先知底波拉在策划打仗的事以前，却是全以色列的士师（4：4）。
V.士师秉政期间，从特殊意义来说，神才是以色列的王；正如撒母耳所言，那时众人正闹着要推翻这样的治理体系（撒母耳记上 12：12）。神要试验他们，看自己的律法和宪法能否维持他们的秩序，事实证明当以色列中没有王，各人任意而行（21：25）。所以他在士师阶段的后期，将士师秉政的现象变得更加常态化，更为普遍，最后把他们交给了他所喜悦的大卫；直到那时，以色列才开始兴旺；我们真该因各级官员的缘故感谢神，他们都是神的用人，是与我们有益的（罗马书13：4）。以色列士师当中有四人出现在新约圣经里：基甸，巴拉，参孙和耶弗他（希伯来书11：32）。学识渊博的帕特里克主教2认为本书的笔者是先知撒母耳。</p>
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
    color: rgba(220,207,60,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(255,240,80,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(255,244,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(200,192,100,0.10),
        0 10px 36px rgba(160,149,30,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(180,168,40,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #3D390A;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(230,218,80,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(180,168,40,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(220,208,80,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(240,228,100,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(240,228,100,0.35) 100%);
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
        0 8px 28px rgba(160,149,30,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #2E2B0D !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(200,186,30,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(240,227,80,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(220,208,80,0.35);
}
</style>
