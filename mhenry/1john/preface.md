---
layout: mhenry-preface
book_id: 1john
book_name: 约翰一书
header-img: nt-hero-1john-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── 1john 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F8D6D6 0%, #EFC8C8 30%,
        #F8D8D8 60%, #F0CCCC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E0D0D; }

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
    color: #500D0D !important;
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
    color: #2E0D0D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(230,80,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(220,80,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(255,100,100,0.55);
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
        inset -1px 0 0 rgba(200,100,100,0.12),
        inset 0 -1px 0 rgba(200,100,100,0.15),
        0 12px 40px rgba(160,30,30,0.12);
    color: #6A1A1A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(180,40,40,0.55) !important;
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
    color: #3D0A0A !important;
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
        rgba(220,100,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(220,100,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(255,120,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(200,100,100,0.12),
        0 10px 36px rgba(160,30,30,0.13),
        0 2px 8px rgba(160,30,30,0.07);
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
    color: #6B1B1B;
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
    color: #2E0D0D;
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
    color: #500D0D;
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
    border-left: 3px solid rgba(240,80,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(200,30,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #500D0D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,120,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(160,30,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(255,120,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #801A1A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(240,100,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #902A2A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(200,30,30,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFE8E8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(200,30,30,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(180,20,20,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #6A1A1A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(240,100,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(240,100,100,0.40) !important;
    color: #500D0D !important;
}
.font-size-ctrl button:hover {
    background: rgba(200,30,30,0.30) !important;
    color: #FFE8E8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(240,100,100,0.60) !important;
    color: #500D0D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(200,30,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(255,200,200,0.20) !important;
    border: 1px solid rgba(255,180,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(200,30,30,0.40) !important;
    color: #FFE8E8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(200,30,30,0.60) !important; }
.tts-speed { color: #6A1A1A !important; }
.tts-speed input[type="range"] { accent-color: #D94A4A !important; }
.tts-progress { background: rgba(255,180,180,0.35) !important; }
.tts-progress-fill { background: rgba(200,30,30,0.55) !important; }
.tts-highlight { background: rgba(200,30,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(240,100,100,0.35) !important;
    border-top: 1px solid rgba(240,100,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(220,60,60,0.55) !important;
    text-shadow: 0 0 12px rgba(255,80,80,0.40);
}
.mh-footer a[href$="/1john/"] {
    background: rgba(200,30,30,0.30) !important;
    border: 1px solid rgba(255,180,180,0.60) !important;
    color: #FFE8E8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(160,30,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/1john/"]:hover {
    background: rgba(200,30,30,0.50) !important;
}
.mh-footer a:not([href$="/1john/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255,180,180,0.70) !important;
    color: #500D0D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(160,30,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/1john/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(160,30,30,0.18) !important;
}
.mh-footer p {
    color: rgba(180,40,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(240,100,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">约翰一书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>虽然教会一脉相承的传统都见证这封书信出于使徒约翰之手，但我们仍可以再观察一些佐证，可以进一步加强（在有些人看来甚至胜过）那传统的确凿性。看起来这位执笔人乃是众使徒之一员，因为他对中保位格——尤其是他人性那部分的位格——有着可触可感、深切的确信："论到从起初原有的生命之道，就是我们所听见、所看见、亲眼看过、亲手摸过的"（第 1 节）。这里他暗指主向多马所给的复活凭据，即叫多马摸钉痕和肋旁——这一段正是约翰所记的。他必是当主在复活的同一天显现并向众门徒展示手和肋旁那时（约翰福音 20:20）在场的门徒之一。</p>

<p>不过，为使我们能确知这是哪一位使徒，几乎每一位文体批评家、或对论证风格和气质有判断力的人，都会判定这封书信与那卷以使徒约翰命名的福音书出自同一作者之手。他们对救赎主称号与特征的用语奇妙地一致："道"、"生命"、"光"；他的名乃是神的道。请将本书 1:1 和 5:7 与约翰福音 1:1 及启示录 19:13 相比较。他们也都同样地宣扬神对我们的爱（本书 3:1 和 4:9；约翰福音 3:16），同样地谈到我们的重生、或称"由神而生"（本书 3:9；4:7；5:1；约翰福音 3:5-6）。最后（不再多举例了，比较这封信和那卷福音便可见），他们都同样地暗指、或应用了那卷福音书所独自记载的那一段——主救赎主肋旁被刺、流出水和血（本书 5:6）。这样看来，这封书信显然与那福音书出自同一支笔。我所知的，是任何福音书的文本或内里历史都未像约翰福音那样清清楚楚地把作者交代给我们：在那里（即第 21 章 24 节）那神圣的历史家这样自我标明："为这些事作见证、并且记载这些事的就是这门徒；我们也知道他的见证是真的。"那么这位门徒是谁呢？乃是彼得所问"这人将来如何"那一位，也是主回答说"我若要他等到我来的时候，与你何干"那一位（第 22 节）。又是第 20 节里以三种特征描述的：1. 他是耶稣所爱的那门徒，主特别亲密的朋友；2. 他也是晚餐中靠在主胸膛上的那一位；3. 他也是问主"主啊，卖你的是谁？"的那一位。既然可以确信那门徒就是约翰，那么教会也可以同样确信：那卷福音和这封书信都出自蒙爱的约翰之手。</p>

<p>这封书信被称为"普通书信"，因为它没有具体写给某一间特别的教会。它如同一封通函（或巡视的训诫），寄给好几间教会（有人说是巴提亚地区的），目的是要坚固他们持守对主基督的忠心、以及关于他位格和职任的神圣教义，以防各样引诱者；并激发他们以爱神爱人——尤其是彼此相爱——来美化这教义，因他们都源于神，由同一元首联合起来，奔向同一个永生。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「神就是爱。」</span>
  <span class="preface-closing-verse-ref">— 约翰一书 4:8 —</span>
</div>

</div>
