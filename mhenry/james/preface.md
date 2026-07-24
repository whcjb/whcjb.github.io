---
layout: mhenry-preface
book_id: james
book_name: 雅各书
header-img: nt-hero-james-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── james 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #E7F8D6 0%, #DCEFC8 30%,
        #E8F8D8 60%, #DEF0CC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #1E2E0D; }

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
    color: #2F500D !important;
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
    color: #1E2E0D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(155,230,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(150,220,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(178,255,100,0.55);
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
        inset -1px 0 0 rgba(150,200,100,0.12),
        inset 0 -1px 0 rgba(150,200,100,0.15),
        0 12px 40px rgba(95,160,30,0.12);
    color: #426A1A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(110,180,40,0.55) !important;
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
    color: #243D0A !important;
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
        rgba(160,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(160,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(188,255,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(150,200,100,0.12),
        0 10px 36px rgba(95,160,30,0.13),
        0 2px 8px rgba(95,160,30,0.07);
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
    color: #436B1B;
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
    color: #1E2E0D;
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
    color: #2F500D;
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
    border-left: 3px solid rgba(160,240,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(115,200,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #2F500D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(188,255,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(95,160,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(188,255,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #4D801A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(170,240,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #5D902A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(115,200,30,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #F3FFE8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(115,200,30,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(100,180,20,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #426A1A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(170,240,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(170,240,100,0.40) !important;
    color: #2F500D !important;
}
.font-size-ctrl button:hover {
    background: rgba(115,200,30,0.30) !important;
    color: #F3FFE8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(170,240,100,0.60) !important;
    color: #2F500D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(115,200,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(227,255,200,0.20) !important;
    border: 1px solid rgba(218,255,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(115,200,30,0.40) !important;
    color: #F3FFE8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(115,200,30,0.60) !important; }
.tts-speed { color: #426A1A !important; }
.tts-speed input[type="range"] { accent-color: #92D94A !important; }
.tts-progress { background: rgba(218,255,180,0.35) !important; }
.tts-progress-fill { background: rgba(115,200,30,0.55) !important; }
.tts-highlight { background: rgba(115,200,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(170,240,100,0.35) !important;
    border-top: 1px solid rgba(170,240,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(140,220,60,0.55) !important;
    text-shadow: 0 0 12px rgba(168,255,80,0.40);
}
.mh-footer a[href$="/james/"] {
    background: rgba(115,200,30,0.30) !important;
    border: 1px solid rgba(218,255,180,0.60) !important;
    color: #F3FFE8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(95,160,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/james/"]:hover {
    background: rgba(115,200,30,0.50) !important;
}
.mh-footer a:not([href$="/james/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(218,255,180,0.70) !important;
    color: #2F500D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(95,160,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/james/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(95,160,30,0.18) !important;
}
.mh-footer p {
    color: rgba(110,180,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(170,240,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">雅各书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>本书信的执笔人不是西庇太的儿子雅各；因为那位雅各已在基督教会在分散于各地的犹太人中扎根到本书所暗示的这种程度之前，就被希律杀害了（使徒行传 12 章）。执笔人乃是另一位雅各——亚勒腓的儿子，与基督是姑表亲，也是十二使徒之一（马太福音 10:3）。他被称为"教会的柱石"（加拉太书 2:9），本书信的正典地位一旦被动摇，就等同于松动了一块根基石。</p>

<p>本书信被称为"普通书信"（general epistle），有人认为是因它不是写给某一位特定的个人或某一间特定的教会，而更像是我们所说的"通函"。另有人认为称为"普通"或"大公"（catholic），是要与伊格那丢、巴拿巴、坡旅甲以及初期时代其他名人所写但未在教会中普遍受纳、不属正典的书信有别；本书则不然。优西比乌告诉我们，本书"与其他大公书信一同在众教会中普遍诵读"。</p>

<p>本书的执笔人雅各因其极大的敬虔，被称为"义人"。他在自己所催促别人所当有的美德上，本身就是一个卓越的榜样。他因其公义、节制、敬虔之深受敬重，以至于犹太历史家约瑟夫记录说，耶路撒冷被毁的原因之一乃是"雅各在其中殉道"。我们提这一点，是要让人对这样一位圣洁卓越之人所写的话更加重视。</p>

<p>本书写成的时期不确定。它的用意是要责备基督徒——他们在信与行上的大幅退步——并要制止那些威胁毁去一切实用敬虔之放纵教义的传播。作者的一个特别用心也是要唤醒犹太民族，意识到即将临到他们的那审判之大、之近；又要在众真基督徒可能遇到的灾难与逼迫中，扶持他们尽本份。本书所立的真理甚为重大、必须要持守；所定的实行规矩，就像它所处的时代一样，是我们的时代也当遵行的。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「你们不要单单听道，自己欺哄自己，总要行道。」</span>
  <span class="preface-closing-verse-ref">— 雅各书 1:22 —</span>
</div>

</div>
