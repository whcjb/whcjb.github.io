---
layout: mhenry-preface
book_id: 2kings
book_name: 列王记下
header-img: psalm-bg-41.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F2D6F8 0%, #E9C8EF 30%,
        #F3D8F8 60%, #EACCF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #280D2E; }

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
    color: #450D50 !important;
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
    color: #280D2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(205,80,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(197,80,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(229,100,255,0.55);
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
        inset -1px 0 0 rgba(183,100,200,0.12),
        inset 0 -1px 0 rgba(183,100,200,0.15),
        0 12px 40px rgba(138,30,160,0.12);
    color: #5D1A6A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(157,40,180,0.55) !important;
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
    color: #340A3D !important;
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
        rgba(200,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(200,100,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(232,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(183,100,200,0.12),
        0 10px 36px rgba(138,30,160,0.13),
        0 2px 8px rgba(138,30,160,0.07);
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
    color: #5B1C69;
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
    color: #280D2E;
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
    color: #450D50;
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
    border-left: 3px solid rgba(213,80,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(172,30,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #450D50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(232,120,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(138,30,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(232,120,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #6F1A80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(217,100,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #7F2A90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(172,30,200,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FBE8FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(172,30,200,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(153,20,180,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #5D1A6A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(217,100,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(217,100,240,0.40) !important;
    color: #450D50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(172,30,200,0.30) !important;
    color: #FBE8FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(217,100,240,0.60) !important;
    color: #450D50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(172,30,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(246,200,255,0.20) !important;
    border: 1px solid rgba(242,180,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(172,30,200,0.40) !important;
    color: #FBE8FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(172,30,200,0.60) !important; }
.tts-speed { color: #5D1A6A !important; }
.tts-speed input[type="range"] { accent-color: #C14AD9 !important; }
.tts-progress { background: rgba(242,180,255,0.35) !important; }
.tts-progress-fill { background: rgba(172,30,200,0.55) !important; }
.tts-highlight { background: rgba(172,30,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(217,100,240,0.35) !important;
    border-top: 1px solid rgba(217,100,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(193,60,220,0.55) !important;
    text-shadow: 0 0 12px rgba(226,80,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(172,30,200,0.30) !important;
    border: 1px solid rgba(242,180,255,0.60) !important;
    color: #FBE8FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(138,30,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(172,30,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(242,180,255,0.70) !important;
    color: #450D50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(138,30,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(138,30,160,0.18) !important;
}
.mh-footer p {
    color: rgba(157,40,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(217,100,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">历史简介</div>
  <div class="preface-book-name">列王记下</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>列王纪下是列王纪上的延续；七十士译本从撒母耳记起算，称此书为列王四书。有人觉得本书应该从列王纪上最后一章第51 节开始，那里提到亚哈谢开始作王。前书的开头相当辉煌，谈到以色列国在国土完整时期的荣耀，这卷书的结局却相当悲哀，国家分裂成两个国，很久以后，以色列国率先凋零，接着就是犹大国；国家分裂，自我相残，终必灭亡。但是前书的后半部份出现了以利亚的异能，堪称前书的亮点，而后书的前半部份出现了以利沙的异能，堪称后书的亮点。这些先知的光芒盖过了王的光芒，所以他们的事迹被载入史册。本书的大意是：I.以利亚吩咐天火降下，又在火中升天（第 1-2 章）。II.以利沙多行神迹，为王，也为百姓，为以色列人，也为外邦人（第 3-7 章）。III.哈薛和耶户受膏；哈薛兴起，是为了管教以色列，耶户兴起，则是为了摧毁亚哈家和巴力偶像崇拜（第 8-10 章）。IV.犹大和以色列的几代君王（第 11-16 章）。V.十个支派沦陷被掳（第17 章）。VI.希西家的辉煌时期（第18-20 章）。VII.玛拿西的暴政；约西亚的德政
（第 21-23 章）。VIII.耶路撒冷毁于巴比伦王之手（第 24-25 章）。这段历史有许多段落印证了所罗门的高见：公义使邦国高举，罪恶是人民的羞辱（箴言 14：34）。</p>
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
    color: rgba(193,60,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(226,80,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(232,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(183,100,200,0.10),
        0 10px 36px rgba(138,30,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(157,40,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #340A3D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(205,80,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(157,40,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(197,80,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(217,100,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(217,100,240,0.35) 100%);
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
        0 8px 28px rgba(138,30,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #280D2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(172,30,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(213,80,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(197,80,220,0.35);
}
</style>
