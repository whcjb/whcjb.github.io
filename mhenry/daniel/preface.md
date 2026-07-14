---
layout: mhenry-preface
book_id: daniel
book_name: 但以理书
header-img: mhenry-land-22.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #ECD6F8 0%, #E1C8EF 30%,
        #ECD8F8 60%, #E3CCF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #220D2E; }

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
    color: #370D50 !important;
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
    color: #220D2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(175,80,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(169,80,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(198,100,255,0.55);
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
        inset -1px 0 0 rgba(163,100,200,0.12),
        inset 0 -1px 0 rgba(163,100,200,0.15),
        0 12px 40px rgba(112,30,160,0.12);
    color: #4D1A6A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(129,40,180,0.55) !important;
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
    color: #2A0A3D !important;
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
        rgba(176,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(176,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(206,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(163,100,200,0.12),
        0 10px 36px rgba(112,30,160,0.13),
        0 2px 8px rgba(112,30,160,0.07);
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
    color: #4D1C69;
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
    color: #220D2E;
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
    color: #370D50;
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
    border-left: 3px solid rgba(181,80,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(138,30,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #370D50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(206,120,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(112,30,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(206,120,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #5B1A80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(189,100,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #6B2A90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(138,30,200,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #F7E8FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(138,30,200,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(121,20,180,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #4D1A6A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(189,100,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(189,100,240,0.40) !important;
    color: #370D50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(138,30,200,0.30) !important;
    color: #F7E8FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(189,100,240,0.60) !important;
    color: #370D50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(138,30,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(235,200,255,0.20) !important;
    border: 1px solid rgba(228,180,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(138,30,200,0.40) !important;
    color: #F7E8FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(138,30,200,0.60) !important; }
.tts-speed { color: #4D1A6A !important; }
.tts-speed input[type="range"] { accent-color: #A54AD9 !important; }
.tts-progress { background: rgba(228,180,255,0.35) !important; }
.tts-progress-fill { background: rgba(138,30,200,0.55) !important; }
.tts-highlight { background: rgba(138,30,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(189,100,240,0.35) !important;
    border-top: 1px solid rgba(189,100,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(161,60,220,0.55) !important;
    text-shadow: 0 0 12px rgba(191,80,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(138,30,200,0.30) !important;
    border: 1px solid rgba(228,180,255,0.60) !important;
    color: #F7E8FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(112,30,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(138,30,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(228,180,255,0.70) !important;
    color: #370D50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(112,30,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(112,30,160,0.18) !important;
}
.mh-footer p {
    color: rgba(129,40,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(189,100,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>
  <div class="preface-book-name">但以理书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>以西结书形容耶路撒冷一片凄凉，满目萧条，但也欢喜展望将来再度辉煌。但以理书在这点上可说是锦上添花。以西结告诉我们他在被掳前期所看见、所预见的，但以理则告诉我们他在被掳后期所看见、所预见的。神使用了不同的手，所作的工却相同。在可怜的被掳之人当中出了一位先知，后来又出一位，告诉他们要到几时，这实在是一种安慰，说明神没有抛弃他们。我们要探讨的是：I.关于这位先知：他的希伯来名是但以理，意思是神的审判；他的迦勒底名是伯提沙撒。他属于犹大支派，可能是王室宗亲。他年少时就崭露头角，又有智慧又虔诚。以西结和他是同时期人，但年龄比他大很多；他在斥责推罗王自欺的时候，把但以理说成是神的出口：看哪，你比但以理更有智慧（以西结书28：3）。他称赞但以理的祷告大有功效，还把挪亚、但以理和约伯三人看作是在天上影响力最大的人（以西结书 14：14）。但以理年轻出名，晚年也享有盛誉。有的犹太拉比不愿承认他是高层次的先知，所以把他的书归在圣录，而不是先知书卷，还不愿他们的门徒太过在意他的书。他们声称这是因为他不像耶利米或别的先知那样生活艰苦，而是过着像王子一般的生活，是国中的大官；其实他和别的先知一样也受逼迫（第6 章），也和别的先知一样刻苦己心，不吃美味（10：3），也在先知之灵的权势下昏迷不醒（8：27）。他们还声称这是因为他是在外邦写成此书，在外邦得异象，不在以色列本土；倘若因为这个原因，那以西结也该从先知书卷中被剔除才是。其实真正的原因，是但以理十分清楚地说出了弥赛亚降临的时间，令犹太人不得不信，于是他们干脆不听。不过约瑟夫1却称他是最大的先知之一，就连天使迦百列也称他为大蒙眷爱的（但以理书 10：11）。但以理长期活跃在世上屈指可数的几位大君王的宫廷和谋士团中，包括尼布甲尼撒、塞鲁士和大利乌；若有人把与天相通的特权仅限于空想家，限于整天冥思苦想的人，那就错了；但以理是宦官，又是政治家，又是实干家，试问有谁比他更明白神的心意呢？圣灵像风，随着意思吹（约翰福音3：8）。若有人以忙于世务为由，不常亲近神，那么但以理就要定他有罪。有人认为他后来回到耶路撒冷，成了希腊会堂的主事，但圣经从未提及；
多数人认为他日子满足，死在波斯的书珊城。II.关于这卷书。前六章经文是叙事性的，平铺直叙；后六章则是预言性的，其中有很多隐晦难明的，但若能全面了解各国历史，尤其是从但以理时代直到弥赛亚降临的犹太历史，就能相对容易明白一些。我们的救主也表示但以理预言的含义不容易读懂，他说：读这经的人须要会意（马太福音 24：15）。第一章和第二章的前三节用希伯来语写成，接下来直到第八章用迦勒底语，再下来直到最后又用希伯来语。布罗顿先生2注释道，
迦勒底人善待但以理，在他有所求的时候给他凉水喝，而不是给他御酒，神就不忘赏赐他们，使他们教他学会的语言有幸出现在神的书中，传遍天下，直到今日。按照他的计算，但以理的圣卷从迦勒底的巴别攻陷耶路撒冷开始，那时他自己被掳，直写到奥秘的巴别罗马最终毁灭耶路撒冷为止，因他的预言时间范围很广，涵盖那个时代（9：27）。苏撒拿寓言和彼勒与大龙的寓言3都攀扯上了但以理，但那些都是次经故事，我们觉得不可信，并且这些寓言从未出现在希伯来文和迦勒底文的圣经里，只在希腊文的圣经，就连犹太人也不承认。本书有些故事和预言涉及迦勒底王朝的后期，有些则涉及波斯王朝的开头。但以理替尼布甲尼撒所解的梦，以及他自己的异象，
则指向希腊王朝和罗马王朝，尤其指向犹太人在安条克统治下的苦难，这些都大大有助于他们提早预备，正如他锁定弥赛亚降临的准确时间，大大有助于等候以色列安慰者的人，也大大有助于我们，可以坚固我们的信心，坚信那就是将要来的那位，不必等候别人。</p>
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
    color: rgba(161,60,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(191,80,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(206,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(163,100,200,0.10),
        0 10px 36px rgba(112,30,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(129,40,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #2A0A3D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(175,80,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(129,40,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(169,80,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(189,100,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(189,100,240,0.35) 100%);
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
        0 8px 28px rgba(112,30,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #220D2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(138,30,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(181,80,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(169,80,220,0.35);
}
</style>
