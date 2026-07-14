---
layout: mhenry-preface
book_id: ezekiel
book_name: 以西结书
header-img: mhenry-land-21.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

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
    color: #271C69;
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
.mh-footer a[href$="/zechariah/"] {
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
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(58,30,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
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
.mh-footer a:not([href$="/zechariah/"]):hover {
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

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>
  <div class="preface-book-name">以西结书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>先知书关乎将来必成的事（启示录 1：19）；当我们进入先知书，就仿佛听见圣约翰所听见的呼声：你上到这里来（启示录 4：1）；可是当我们进入这卷先知书，那声音仿佛就成了：你上得再高一些；时间在推进（以西结说预言是在被掳之地，而耶利米说预言则是在被掳之前），我们上得也更高，神的荣耀也显得更壮观。圣所的水越来越深，不但深不可蹚，有些地方甚至深不可测；
但尽管如此，所流出来的分汊却使神的城欢喜；这城就是至高者居住的圣所（诗篇46：4）。至于摆在我们面前的这卷先知书，我们要探讨：I.本书的笔者：以西结。这个名字的意思是神的力量，
或作以神为力量。他在心里束起腰来，专心服事，神也赐他力量。神呼召谁，也必亲自赐他能力；
他赋予谁使命，也必赋予他履行使命的能力。以西结这个名字真实反映了神所说的：我使你的脸硬过他们的脸（3：8），神也果然说到做到。学识渊博的塞尔登1在他的书中写道，毕达哥拉斯2
说他曾拜在一位名叫那撒拉图斯·亚述利亚斯的门下，听他讲课，有古人认为此人就是以西结。
学者们同意二人所在的年代相仿，并且我们有理由相信有不少希腊哲学家熟悉圣经，因他们当中有不少耳熟能详的观点出自圣经。如果我们相信犹太人传说的话，以西结死在被掳到巴比伦的人手里，因他责备他们时不留情面；据说他被人在石头上活活拖死，脑浆迸裂。有一位阿拉伯历史学家说他被害死，埋在挪亚之子闪的墓穴里。II.本书的写作日期：地点和时间。本书的背景设在巴比伦，那是属神以色列的为奴之家；这卷书的预言在那里传讲，也在那里写成，先知本人和听这些预言的都是被掳到那里的人。旧约圣经笔者当中，在以色列地以外居住并说预言的，唯有以西结和但以理，也许可再加上约拿，他被派往尼尼微说预言。以西结说预言，是在被掳前期，但以理则是在被掳后期。被掳之人在受难时，神在他们当中兴起先知，表达了神对他们的善意和施恩的意图，叫他们在苦难前期放松大意时得劝诫（这是以西结的任务），又在苦难后期沮丧灰心时得安慰。主若想杀他们，必不会采取如此恰当合宜的措施来医治他们。III.本书的题材和内容。1.
书中有不少神秘、隐晦和难明之处，尤其是本书的开头和结尾部份，乃至犹太拉比们规定，年轻人要到三十岁才能阅读此书，免得他们在书中遇到难题，对圣经心生偏见；但我们在读到这些难明的部份时，只要本着谦卑和敬畏的心，潜心钻研，所遇到的结虽然未必都能解开，正如自然学科书卷未必能解释所有的自然现象，但仍可从中大有收获，正如从自然学科书卷中大有收获一般，
乃至信心得坚固，以我们所敬拜的神为盼望。2.书中的异象虽然深奥，可容大象畅游其中，但书中的信息却简单明了，可容羊羔涉水而过；这些异象和信息的主要意图是向神的百姓说明他们的过犯（以赛亚书 58：1），叫他们在被掳之地悔改，而不是埋怨。当时似乎常有人来听先知讲道，
因为书中说他们坐在他面前仿佛是神的民，听他的话（33：31）；也常有人来请教他，因为书中说有以色列的长老前来，通过他求问耶和华（14：1，3）。受欺压的被掳之人当中出了一位先知，
不但对他们大有好处，也是圣洁信仰的见证，是见证那些嘲讽他们、嘲讽圣洁信仰之欺压者的不是。3.书中的谴责和警告虽然尖锐直率，但接近结尾的部份也有安慰的话，叫人坚信神有大怜悯为他们存留；我们也会在那里见到有信息指向福音时代，并且要在弥赛亚的国度成全，尽管这位先知在这个话题上比别的先知说得少。展示耶和华的威严，是为了预备基督的道。既然律法是叫人知罪，那么律法就成了我们训蒙的师傅，引我们到基督那里（加拉太书3：24）。第1-3 章说的是几个异象，证明先知的资质；第4-24 章说的是谴责和警告；在这段经文和结尾部份的安慰话之间有一段信息，传给邻近以色列地的列国，预言他们的毁灭（第 25-35 章），为重振属神以色列和重建圣城圣殿铺平道路；关于重振以色列的预言则出现在第 36 章直到最后。若想得安慰，就须有信念。</p>
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
    color: rgba(87,60,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(109,80,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(142,120,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(117,100,200,0.10),
        0 10px 36px rgba(52,30,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(63,40,180,0.55);
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
        0 2px 14px rgba(105,80,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(63,40,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(103,80,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(123,100,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(123,100,240,0.35) 100%);
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
        0 8px 28px rgba(52,30,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #120D2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(58,30,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(107,80,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(103,80,220,0.35);
}
</style>
