---
layout: mhenry-preface
book_id: galatians
book_name: 加拉太书
header-img: nt-hero-galatians-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── galatians 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6F8EC 0%, #C8EFE1 30%,
        #D8F8EC 60%, #CCF0E3 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D2E22; }

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
    color: #0D5037 !important;
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
    color: #0D2E22;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,230,175,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,220,169,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,255,198,0.55);
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
        inset -1px 0 0 rgba(100,200,163,0.12),
        inset 0 -1px 0 rgba(100,200,163,0.15),
        0 12px 40px rgba(30,160,112,0.12);
    color: #1A6A4D !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,180,129,0.55) !important;
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
    color: #0A3D2A !important;
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
        rgba(100,220,176,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,220,176,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,255,206,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,200,163,0.12),
        0 10px 36px rgba(30,160,112,0.13),
        0 2px 8px rgba(30,160,112,0.07);
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
    color: #1B6B4E;
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
    color: #0D2E22;
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
    color: #0D5037;
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
    border-left: 3px solid rgba(80,240,181,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,200,138,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D5037 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,255,206,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,160,112,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,255,206,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A805B !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,240,189,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A906B !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,200,138,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8FFF7 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,200,138,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,180,121,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A6A4D;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,240,189,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,240,189,0.40) !important;
    color: #0D5037 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,200,138,0.30) !important;
    color: #E8FFF7 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,240,189,0.60) !important;
    color: #0D5037 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,200,138,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,255,235,0.20) !important;
    border: 1px solid rgba(180,255,228,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,200,138,0.40) !important;
    color: #E8FFF7 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,200,138,0.60) !important; }
.tts-speed { color: #1A6A4D !important; }
.tts-speed input[type="range"] { accent-color: #4AD9A5 !important; }
.tts-progress { background: rgba(180,255,228,0.35) !important; }
.tts-progress-fill { background: rgba(30,200,138,0.55) !important; }
.tts-highlight { background: rgba(30,200,138,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,240,189,0.35) !important;
    border-top: 1px solid rgba(100,240,189,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,220,161,0.55) !important;
    text-shadow: 0 0 12px rgba(80,255,191,0.40);
}
.mh-footer a[href$="/galatians/"] {
    background: rgba(30,200,138,0.30) !important;
    border: 1px solid rgba(180,255,228,0.60) !important;
    color: #E8FFF7 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,160,112,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/galatians/"]:hover {
    background: rgba(30,200,138,0.50) !important;
}
.mh-footer a:not([href$="/galatians/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,255,228,0.70) !important;
    color: #0D5037 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,160,112,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/galatians/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,160,112,0.18) !important;
}
.mh-footer p {
    color: rgba(40,180,129,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,240,189,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">加拉太书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>保罗这封书信不像其他几封那样是致某一城之教会或众教会的，而是致一整个地区或省份之教会的——加拉太就是这样一处地方。极有可能：这些加拉太人最初就是藉他的传道归信基督的；即便他不是栽种者，至少他也曾浇灌这些教会——这从本书信本身可见，也从使徒行传 18:23 可见——他"就离开那里，挨次经过加拉太和弗吕家地方，坚固众门徒"。</p>

<p>他与他们同在时，他们向他本人与他的传道表达了极大的敬重与爱；但他离开他们没有多久，就有一些"犹太化的教师"混进他们中间，藉着他们的手段与暗示，加拉太人不久就对这两方——保罗本人与他的传道——都持了较低的看法。这些假教师所主要意图的乃是把他们从"那在耶稣里的真理"上拉走，特别是在"称义"这大教义上——他们粗劣地歪曲了它，主张必须把"守摩西律法"加到"信基督"上才能得称义。为更好地实现这一图谋，他们尽力贬低这位使徒的品格与名声，又要在他之废墟上抬起自己——把他描绘为"就算被认作使徒也远逊别人"、尤其不配得像彼得、雅各、约翰那样的敬重（他们自称的正是那几位的跟从者）。在这两方面上，他们的成功可惜太大了。</p>

<p>这就是他写此书信的由来。他在书中表达自己极大的关切——他们竟这么快就任凭自己"从福音之信上被引开"；他辩护自己作为使徒的品格与权柄，抵挡仇敌对他的攻击，说明他的差委与教义都是从神而来，说他就任何一件事而言都不亚于最上等的使徒（哥林多后书 11:5）。他又立起并维持"因信称义、不靠律法之工"这一福音大教义，并解开他们心中可能就此产生的一些难处。既已立定此重要教义，他就劝他们要在基督"释放他们所得之自由"里站立得稳，警戒他们不可滥用此自由，给他们几样必要的劝告与指导。最后以两幅对照的画像结束此书——一是"迷惑他们之假教师"的公正描绘，另一是自己心境与举止的对比。这一切之中，他的大范围与用意乃是：**挽回那些已被引偏之人，稳固那些可能仍在动摇之人，坚固那些持守正直之人**。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「我已经与基督同钉十字架。」</span>
  <span class="preface-closing-verse-ref">— 加拉太书 2:20 —</span>
</div>

</div>
