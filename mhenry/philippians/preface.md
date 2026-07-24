---
layout: mhenry-preface
book_id: philippians
book_name: 腓立比书
header-img: nt-hero-philippians-preface.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── philippians 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F8D6DE 0%, #EFC8D2 30%,
        #F8D8E0 60%, #F0CCD5 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E0D15; }

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
    color: #500D1E !important;
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
    color: #2E0D15;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(230,80,117,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(220,80,115,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(255,100,139,0.55);
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
        inset -1px 0 0 rgba(200,100,125,0.12),
        inset 0 -1px 0 rgba(200,100,125,0.15),
        0 12px 40px rgba(160,30,62,0.12);
    color: #6A1A2E !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(180,40,75,0.55) !important;
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
    color: #3D0A17 !important;
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
        rgba(220,100,130,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(220,100,130,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(255,120,154,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(200,100,125,0.12),
        0 10px 36px rgba(160,30,62,0.13),
        0 2px 8px rgba(160,30,62,0.07);
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
    color: #6B1B2F;
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
    color: #2E0D15;
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
    color: #500D1E;
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
    border-left: 3px solid rgba(240,80,120,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(200,30,72,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #500D1E !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,120,154,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(160,30,62,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(255,120,154,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #801A33 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(240,100,135,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #902A43 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(200,30,72,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFE8EE !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(200,30,72,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(180,20,60,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #6A1A2E;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(240,100,135,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(240,100,135,0.40) !important;
    color: #500D1E !important;
}
.font-size-ctrl button:hover {
    background: rgba(200,30,72,0.30) !important;
    color: #FFE8EE !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(240,100,135,0.60) !important;
    color: #500D1E !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(200,30,72,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(255,200,214,0.20) !important;
    border: 1px solid rgba(255,180,199,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(200,30,72,0.40) !important;
    color: #FFE8EE !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(200,30,72,0.60) !important; }
.tts-speed { color: #6A1A2E !important; }
.tts-speed input[type="range"] { accent-color: #D94A6E !important; }
.tts-progress { background: rgba(255,180,199,0.35) !important; }
.tts-progress-fill { background: rgba(200,30,72,0.55) !important; }
.tts-highlight { background: rgba(200,30,72,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(240,100,135,0.35) !important;
    border-top: 1px solid rgba(240,100,135,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(220,60,100,0.55) !important;
    text-shadow: 0 0 12px rgba(255,80,124,0.40);
}
.mh-footer a[href$="/philippians/"] {
    background: rgba(200,30,72,0.30) !important;
    border: 1px solid rgba(255,180,199,0.60) !important;
    color: #FFE8EE !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(160,30,62,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/philippians/"]:hover {
    background: rgba(200,30,72,0.50) !important;
}
.mh-footer a:not([href$="/philippians/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255,180,199,0.70) !important;
    color: #500D1E !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(160,30,62,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/philippians/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(160,30,62,0.18) !important;
}
.mh-footer p {
    color: rgba(180,40,75,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(240,100,135,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">腓立比书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>腓立比乃是马其顿西部的首邑（"马其顿一方的头城"，使徒行传 16:12）。此城之名取自马其顿名王腓立——他曾重修美化之——此后又成为罗马之殖民地。此地附近有腓立平原（Campi Philippici），因几场著名之战闻名——尤利乌斯·凯撒与庞培大帝之战、奥古斯都与安东尼一方与卡西乌斯与布鲁图斯另一方之战。但在基督徒中间它最引人瞩目之处乃是这封书信——此信是保罗在罗马作囚犯时（主后 62 年）所写。</p>

<p>保罗似乎对腓立比之教会有极特别的怜爱——因这教会乃是他亲自作器皿栽种起来的；他虽然对众教会都有挂虑，就此教会又有一份"父亲般的温柔特别关心"。**对于那些神使用我们为之行善之人，我们当以此为鼓励与约束，去研究如何为他们再多行些善**。他视他们为儿女；既已藉福音生他们，就愿藉同一福音养育培育他们。</p>

<p>I. **他以非常之方式被召往腓立比传福音**（使徒行传 16:9）——"夜间保罗见了异象，有一个马其顿人站着求他说：请你过到马其顿来帮助我们！"他看见神走在他前面，就得着鼓励，用一切方法把在他们中间已开始之善工继续下去、又在已下之根基上建造。</p>

<p>II. **在腓立比他受了极多苦**——被鞭打、被下在木狗里（使徒行传 16:23-24）；然而他并没有因所受之苦待，就减少对此地之爱。**我们绝不当因仇敌加于我们之苦待，就减少对朋友之爱**。</p>

<p>III. **那教会之开端极小**——只有吕底亚、狱卒和几个人归主——但保罗并未因此灰心。**若起初未见果效，将来仍可有；末后之工可能比先前更多**。**我们不当因起初微小之开端而灰心**。</p>

<p>IV. 从此书信中许多段落可见：**腓立比之教会渐渐长成兴旺之教会**，尤其众弟兄对保罗极其恩待。他既得着他们之属地之物，就以属灵之物为回报。他在第 4:18 节确认已收到他们所送之礼；这时无别的教会与他有"授受之交往"（4:15）；他也在此书信中给了他们"先知的赏赐、使徒的赏赐"——这远比千万金银更宝贵。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「我靠着那加给我力量的，凡事都能做。」</span>
  <span class="preface-closing-verse-ref">— 腓立比书 4:13 —</span>
</div>

</div>
