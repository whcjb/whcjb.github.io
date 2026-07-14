---
layout: mhenry-preface
book_id: numbers
book_name: 民数记
header-img: psalm-bg-forest.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6F8F5 0%, #C8EFEC 30%,
        #D8F8F5 60%, #CCF0ED 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D2E2B; }

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
    color: #0D504A !important;
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
    color: #0D2E2B;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,230,218,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,220,208,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,255,242,0.55);
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
        inset -1px 0 0 rgba(100,200,192,0.12),
        inset 0 -1px 0 rgba(100,200,192,0.15),
        0 12px 40px rgba(30,160,149,0.12);
    color: #1A6A63 !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,180,168,0.55) !important;
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
    color: #0A3D39 !important;
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
        rgba(100,220,210,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,220,210,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,255,244,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,200,192,0.12),
        0 10px 36px rgba(30,160,149,0.13),
        0 2px 8px rgba(30,160,149,0.07);
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
    color: #1C6962;
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
    color: #0D2E2B;
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
    color: #0D504A;
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
    border-left: 3px solid rgba(80,240,227,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,200,186,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D504A !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,255,244,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,160,149,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,255,244,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A8078 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,240,228,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A9088 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,200,186,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8FFFD !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,200,186,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,180,167,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A6A63;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,240,228,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,240,228,0.40) !important;
    color: #0D504A !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,200,186,0.30) !important;
    color: #E8FFFD !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,240,228,0.60) !important;
    color: #0D504A !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,200,186,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,255,250,0.20) !important;
    border: 1px solid rgba(180,255,249,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,200,186,0.40) !important;
    color: #E8FFFD !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,200,186,0.60) !important; }
.tts-speed { color: #1A6A63 !important; }
.tts-speed input[type="range"] { accent-color: #4AD9CD !important; }
.tts-progress { background: rgba(180,255,249,0.35) !important; }
.tts-progress-fill { background: rgba(30,200,186,0.55) !important; }
.tts-highlight { background: rgba(30,200,186,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,240,228,0.35) !important;
    border-top: 1px solid rgba(100,240,228,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,220,207,0.55) !important;
    text-shadow: 0 0 12px rgba(80,255,240,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(30,200,186,0.30) !important;
    border: 1px solid rgba(180,255,249,0.60) !important;
    color: #E8FFFD !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,160,149,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(30,200,186,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,255,249,0.70) !important;
    color: #0D504A !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,160,149,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,160,149,0.18) !important;
}
.mh-footer p {
    color: rgba(40,180,168,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,240,228,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">律法简介</div>
  <div class="preface-book-name">民数记</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>在我们所使用的圣经译本中1，摩西五经的书名都借用七十士希腊译本，那是已知的最古老旧约版本。但另外四卷书的书名都直接使用希腊语，唯有这卷书的书名翻成了英语，其中原因不得而知；拉丁语系的译者一般都这样做。否则，本书也大可使用希腊语书名，称为计算，好比第一卷称为创世，第二卷称为出埃及；或者都用英语，第一卷称为产生或起初，第二卷称为出来或逃离，就像这卷书称为民数。本书以此为名，是因为书中经常提到以色列民的数目；这也是实至名归，因为神给亚伯拉罕的应许奇妙成真，他的后裔果然像天上的星那样多。这个书名还与他们两次数点人数有关，一次是在西奈山（第 1 章），另一次是三十九年后在摩押平原（第 26 章）。
第一次被数的人当中，到了第二次数点时还活着的，不超过三人。本书又有历史故事，又有律法，几乎各占一半。
I.本书的故事包括：各支派的人数和列队（第1-4 章），坛和利未人的奉献礼（第7-8 章），行进
（第 9-10 章），发怨言、不信，被判旷野飘流四十年（第 11-14 章），可拉谋反（第 16-17
章），四十年中最后一年的故事（第 20-26 章），征服米甸人，两个支派定居（第 31-32 章），
行程概述（第 33 章）。II.本书还有许多律法条例：拿细耳人（第 5-6 章），祭司的职责（第 18-
19 章），节期（第 28-29 章），许愿（第 30 章），还有与定居迦南地相关的律例（第 27，34，
35，36 章）。诗篇95：10 中有一句话可概括本书大部份内容：四十年之久，我厌烦那世代；而希伯来书 4：1 则将此应用在我们身上：我们就当畏惧，免得我们似乎是赶不上了。当时有许多强国存在，住在坚固城里，但神圣的历史对此只字不提，这个弱小民族的故事却详细保存，他们住帐棚，奇怪地漂流在旷野，因为他们是圣约的民。正是：耶和华的份本是他的百姓；他的产业本是雅各（申命记32：9）。</p>
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
    color: rgba(60,220,207,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(80,255,240,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(120,255,244,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(100,200,192,0.10),
        0 10px 36px rgba(30,160,149,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(40,180,168,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #0A3D39;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(80,230,218,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(40,180,168,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(80,220,208,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(100,240,228,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(100,240,228,0.35) 100%);
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
        0 8px 28px rgba(30,160,149,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #0D2E2B !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(30,200,186,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(80,240,227,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(80,220,208,0.35);
}
</style>
