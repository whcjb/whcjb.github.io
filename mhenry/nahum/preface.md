---
layout: mhenry-preface
book_id: nahum
book_name: 那鸿书
header-img: mhenry-land-29.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── nahum 水晶透明风 ──────────────────────────── */

/* 容器：水晶渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #ECD6F8 0%, #DFC8EF 30%,
        #EDD8F8 60%, #E4CCF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #1E0D2E; }

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
    color: #220D3A !important;
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
    color: #1E0D2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(120,50,210,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(115,48,200,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(150,70,240,0.55);
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
        inset -1px 0 0 rgba(100,70,160,0.12),
        inset 0 -1px 0 rgba(100,70,160,0.15),
        0 12px 40px rgba(70,20,140,0.12);
    color: #301848 !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(85,30,155,0.55) !important;
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
    color: #180A26 !important;
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
        rgba(120,70,190,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(120,70,190,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(150,90,230,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,70,160,0.12),
        0 10px 36px rgba(70,20,140,0.13),
        0 2px 8px rgba(70,20,140,0.07);
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
    color: #140820;
    font-size: 0.97em;
    font-family: "LXGW WenKai", "STKaiti", "KaiTi", "楷体", serif !important;
    font-weight: 600;
    letter-spacing: 0.03em;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.55);
}

/* 注释块：磨砂水晶 */
.mh-unit-body {
    padding: 22px 0 20px !important;
    background: rgba(255,255,255,0.28);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    line-height: 2.05;
    color: #1E0D2E;
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
    color: #220D3A;
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
    border-left: 3px solid rgba(110,50,210,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(80,25,165,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #220D3A !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(150,90,230,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(70,20,140,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(150,90,230,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #2A1840 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(120,60,215,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #3A2854 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(80,25,165,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #F4E8FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(80,25,165,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,80,180,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #301848;
}

/* ── 顶部导航：水晶主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(120,60,215,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(120,60,215,0.40) !important;
    color: #220D3A !important;
}
.font-size-ctrl button:hover {
    background: rgba(80,25,165,0.30) !important;
    color: #F4E8FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(120,60,215,0.60) !important;
    color: #220D3A !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(80,25,165,0.30) !important;
}

/* ── TTS 朗读栏：水晶主题 ── */
.tts-bar {
    background: rgba(215,175,250,0.20) !important;
    border: 1px solid rgba(190,150,240,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(80,25,165,0.40) !important;
    color: #F4E8FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(80,25,165,0.60) !important; }
.tts-speed { color: #301848 !important; }
.tts-speed input[type="range"] { accent-color: #7A30C0 !important; }
.tts-progress { background: rgba(190,150,240,0.35) !important; }
.tts-progress-fill { background: rgba(80,25,165,0.55) !important; }
.tts-highlight { background: rgba(80,25,165,0.14) !important; }

/* ── 页脚：水晶主题 ── */
.mh-footer hr {
    border-color: rgba(120,60,215,0.35) !important;
    border-top: 1px solid rgba(120,60,215,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(100,40,190,0.55) !important;
    text-shadow: 0 0 12px rgba(120,55,225,0.40);
}
.mh-footer a[href$="/nahum/"] {
    background: rgba(80,25,165,0.30) !important;
    border: 1px solid rgba(190,150,240,0.60) !important;
    color: #F4E8FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(70,20,140,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/nahum/"]:hover {
    background: rgba(80,25,165,0.50) !important;
}
.mh-footer a:not([href$="/nahum/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(190,150,240,0.70) !important;
    color: #220D3A !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(70,20,140,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/nahum/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(70,20,140,0.18) !important;
}
.mh-footer p {
    color: rgba(85,30,155,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(120,60,215,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>
  <div class="preface-book-name">那鸿书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>这位先知的名字意思是安慰者；安慰是所有先知的职责所在：你们要安慰，安慰我的百姓（以赛亚书 40：1）；即便这位先知花了大量篇幅预言尼尼微要毁灭，致令亚述惊恐，但他所说的，仍是以色列十个支派的安慰，那时他们也许刚刚被掳去亚述。那鸿所在的年代和说预言的年代很不能确定，但最有可能是在希西家的时候；他预言尼尼微要毁灭，是以色列被亚述王掳去之后（那是希西家作王第九年），西拿基立入侵犹大之前（那是希西家作王第十四年），因为第一章似乎提到了那次军事行动，也提到他吃了败仗；这段预言也许比这场战事稍早一点，其目的是在那兵荒马乱的日子鼓励神的百姓。学识渊博的休伊特1猜想本书另外两章的信息是那鸿在很多年以后传递的，可能是玛拿西作王期间；犹太人的年表通常将他归在那个时代，接近基亚克萨雷斯2和尼布甲尼撒攻陷尼尼微、制伏亚述王朝的时候，也就是犹大首次被掳以前不久。那鸿有可能口述过很多关于以色列和犹大的预言，我们知道约拿有过这样的口述（列王纪下14：25），只是除了关于尼尼微的预言，其余的没有写成文字；尼尼微虽是大城，并且历史悠久，但若不是以色列的神对它有些在乎，也许圣经根本不会提到它。</p>
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
    color: rgba(115,48,200,0.4);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(150,70,240,0.5);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(130,60,210,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(80,30,150,0.1),
        0 10px 36px rgba(50,15,120,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(80,30,150,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #120A3D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(130,60,210,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(80,30,150,0.5);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(115,48,200,0.4);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(150,70,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(150,70,240,0.35) 100%);
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
        0 8px 28px rgba(50,15,120,0.1);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #1A0D2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(80,30,150,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(150,70,240,0.3);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(115,48,200,0.35);
}
</style>
