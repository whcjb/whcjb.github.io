---
layout: mhenry-preface
book_id: titus
book_name: 提多书
header-img: nt-hero-titus-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── titus 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F7F8D6 0%, #EEEFC8 30%,
        #F7F8D8 60%, #EFF0CC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2D2E0D; }

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
    color: #4E500D !important;
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
    color: #2D2E0D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(225,230,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(215,220,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(250,255,100,0.55);
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
        inset -1px 0 0 rgba(197,200,100,0.12),
        inset 0 -1px 0 rgba(197,200,100,0.15),
        0 12px 40px rgba(156,160,30,0.12);
    color: #676A1A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(175,180,40,0.55) !important;
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
    color: #3B3D0A !important;
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
        rgba(216,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(216,220,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(250,255,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(197,200,100,0.12),
        0 10px 36px rgba(156,160,30,0.13),
        0 2px 8px rgba(156,160,30,0.07);
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
    color: #686B1B;
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
    color: #2D2E0D;
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
    color: #4E500D;
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
    border-left: 3px solid rgba(235,240,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(194,200,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #4E500D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(250,255,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(156,160,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(250,255,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #7D801A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(235,240,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #8D902A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(194,200,30,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FEFFE8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(194,200,30,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(175,180,20,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #676A1A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(235,240,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(235,240,100,0.40) !important;
    color: #4E500D !important;
}
.font-size-ctrl button:hover {
    background: rgba(194,200,30,0.30) !important;
    color: #FEFFE8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(235,240,100,0.60) !important;
    color: #4E500D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(194,200,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(253,255,200,0.20) !important;
    border: 1px solid rgba(252,255,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(194,200,30,0.40) !important;
    color: #FEFFE8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(194,200,30,0.60) !important; }
.tts-speed { color: #676A1A !important; }
.tts-speed input[type="range"] { accent-color: #D4D94A !important; }
.tts-progress { background: rgba(252,255,180,0.35) !important; }
.tts-progress-fill { background: rgba(194,200,30,0.55) !important; }
.tts-highlight { background: rgba(194,200,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(235,240,100,0.35) !important;
    border-top: 1px solid rgba(235,240,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(215,220,60,0.55) !important;
    text-shadow: 0 0 12px rgba(249,255,80,0.40);
}
.mh-footer a[href$="/titus/"] {
    background: rgba(194,200,30,0.30) !important;
    border: 1px solid rgba(252,255,180,0.60) !important;
    color: #FEFFE8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(156,160,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/titus/"]:hover {
    background: rgba(194,200,30,0.50) !important;
}
.mh-footer a:not([href$="/titus/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(252,255,180,0.70) !important;
    color: #4E500D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(156,160,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/titus/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(156,160,30,0.18) !important;
}
.mh-footer p {
    color: rgba(175,180,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(235,240,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">提多书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>保罗致提多的这封书信在性质上与那两封写给提摩太的书信十分相近；提多与提摩太都是保罗所结的果子，都是他劳苦与受苦时的同伴；两人都担任"传福音的"之职——其工作是浇灌使徒所建立的众教会，也把众教会中所欠缺的事一一料理妥当。他们乃是"副使徒"，从事主的工作、且多在使徒的指导下——虽这指导不是专断辖管、乃是让他们仍以自身的谨慎与判断力同工（哥林多前书 16:10、12）。</p>

<p>关于提多，我们在圣经许多地方读到他的名号、品格与殷勤的果效——他是希腊人（加拉太书 2:3）。保罗称他"我的真儿子"（提多书 1:4）、"我的兄弟"（哥林多后书 2:13）、"我的同伴同工"（哥林多后书 8:23）——就是那"与保罗同一心灵、同一脚踪"之人。他曾与使徒一同上耶路撒冷（加拉太书 2:1），常在哥林多，保罗对哥林多教会有恳切的关切（哥林多后书 8:16）；保罗致哥林多的后书——很可能还有前书——都是藉他的手送去的（哥林多后书 8:16-18、23；9:2-4；12:18）。他曾与使徒同在罗马，此后往挞马太去（提摩太后书 4:10），此后圣经再无关于他的记载。所以按圣经看，他似乎并非一位定住的主教；若他真是这样的主教、又在那时期，那么他最劳苦服事之地——哥林多教会——就当最有权说他属于他们。</p>

<p>革哩底（今名 Candia，古称 Hecatompolis，因岛上有一百座城）是爱琴海口的一座大岛，福音在那里已有立足之地；保罗与提多曾在他们某次旅程中到过那里，栽培这一片新开的园地；但外邦的使徒既担着众教会的挂虑，就不能在此久住，所以留提多在那里一段时间，好把已开的工作继续下去。或许在这工作中他遇见了非同寻常的难处，保罗因此写下这封书信；但这与其说是为提多本人所需，不如说是为革哩底当地信徒的益处——好使提多藉使徒之劝勉与权柄所加强的一切努力，在他们中间更有分量、更有果效。</p>

<p>他所领受的托付是：要看各城中都有好牧者、要拒绝并挡住不合宜不配之人；要教导纯正的道理，指教各等人各尽本份；要把"神在基督里为人所设的白白恩典之救恩"陈明出来，同时又要显明凡信神并盼望从他得着永生的人，必须坚持"好行为"。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「等候至大的神和我们救主耶稣基督的荣耀显现。」</span>
  <span class="preface-closing-verse-ref">— 提多书 2:13 —</span>
</div>

</div>
