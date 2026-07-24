---
layout: mhenry-preface
book_id: jude
book_name: 犹大书
header-img: nt-hero-jude-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── jude 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #DCD6F8 0%, #CEC8EF 30%,
        #DDD8F8 60%, #D2CCF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #120D2E; }

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
    color: #180D50 !important;
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
    color: #120D2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(105,80,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(103,80,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(126,100,255,0.55);
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
        inset -1px 0 0 rgba(117,100,200,0.12),
        inset 0 -1px 0 rgba(117,100,200,0.15),
        0 12px 40px rgba(52,30,160,0.12);
    color: #271A6A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(63,40,180,0.55) !important;
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
    color: #120A3D !important;
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
        rgba(120,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(120,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(142,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(117,100,200,0.12),
        0 10px 36px rgba(52,30,160,0.13),
        0 2px 8px rgba(52,30,160,0.07);
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
    color: #281B6B;
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
    color: #120D2E;
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
    color: #180D50;
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
    border-left: 3px solid rgba(107,80,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(58,30,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #180D50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(142,120,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(52,30,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(142,120,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #2B1A80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(123,100,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #3B2A90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(58,30,200,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #ECE8FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(58,30,200,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(47,20,180,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #271A6A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(123,100,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(123,100,240,0.40) !important;
    color: #180D50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(58,30,200,0.30) !important;
    color: #ECE8FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(123,100,240,0.60) !important;
    color: #180D50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(58,30,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(209,200,255,0.20) !important;
    border: 1px solid rgba(192,180,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(58,30,200,0.40) !important;
    color: #ECE8FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(58,30,200,0.60) !important; }
.tts-speed { color: #271A6A !important; }
.tts-speed input[type="range"] { accent-color: #624AD9 !important; }
.tts-progress { background: rgba(192,180,255,0.35) !important; }
.tts-progress-fill { background: rgba(58,30,200,0.55) !important; }
.tts-highlight { background: rgba(58,30,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(123,100,240,0.35) !important;
    border-top: 1px solid rgba(123,100,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(87,60,220,0.55) !important;
    text-shadow: 0 0 12px rgba(109,80,255,0.40);
}
.mh-footer a[href$="/jude/"] {
    background: rgba(58,30,200,0.30) !important;
    border: 1px solid rgba(192,180,255,0.60) !important;
    color: #ECE8FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(52,30,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/jude/"]:hover {
    background: rgba(58,30,200,0.50) !important;
}
.mh-footer a:not([href$="/jude/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(192,180,255,0.70) !important;
    color: #180D50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(52,30,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/jude/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(52,30,160,0.18) !important;
}
.mh-footer p {
    color: rgba(63,40,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(123,100,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">犹大书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>这封书信被称为"普通书信"或"大公书信"（与少数几封同列），因为它并非直接写给某一个人、某一个家庭或某一个教会，而是写给当时所有的基督徒群体——他们当中有刚从犹太教归信的，也有从异教归信的；这封信对教会来说，一直、并且必将是大有用处的，只要基督信仰存在，也就是只要时间存在，这封信就有它持久而独特的功用。</p>

<p>这封信的总要旨与彼得后书第二章大致相同，那一章已经讲过了，所以本卷需要讲的就相对少些。这封信的用意是警告我们，要防备引诱者及其引诱，要使我们对真道（明明可见且至关重要的真道）怀有炽热的爱和真诚的关切，并且要使这种爱与真道紧密地与圣洁结合——而真诚不带偏见的弟兄之爱（即"仁爱"），乃是圣洁不可或缺的特征，也是圣洁不可分割的一支。</p>

<p>我们要持守、并要努力使别人也认识、不背离的真道，有两个显著的标志：—它是"如同耶稣里的真理"（以弗所书 4:21），它也是"合乎敬虔"（即随从敬虔）的真道（提多书 1:1）。福音是基督的福音。是他将福音启示给我们，他也是福音的核心主题；因此凡称自己为基督徒的人，都必须竭力从这福音中学习他位格、属性、职份的一切；对此漠不关心，无可推诿。我们也清楚知道：那一切必需的得救知识，是单单从哪一个源头汲取的。</p>

<p>而且，福音也是一种"敬虔的教导"。凡纵容人败坏私欲的教训，无论它有什么样的辩解和借口，都不可能出于神。教会中很快就兴起了对人灵魂危险至极的错谬。仆人睡着的时候，稗子就被撒了。但神护理的智慧和慈爱在于：当这些错谬开始明显地、公开地显露时，至少还有几位使徒在世，可以驳斥它们，警告他人提防它们。我们容易这样想：若我们生在使徒时代，必定能充分抵挡引诱者的诡计；可是事实上，使徒们的见证和警戒已经给了我们，那已经够了；如果连他们写下来的文字我们都不相信，那么即便我们当年与他们同时代、亲身与他们交谈，也未必会相信或留意他们口里所说的话。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「那能保守你们不失脚，叫你们无瑕无疵欢欢喜喜站在他荣耀之前的我们的救主独一的神。」</span>
  <span class="preface-closing-verse-ref">— 犹大书 1:24-25 —</span>
</div>

</div>
