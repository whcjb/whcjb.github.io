---
layout: mhenry-preface
book_id: ecclesiastes
book_name: 传道书
header-img: psalm-bg-50.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6F5F8 0%, #C8ECEF 30%,
        #D8F5F8 60%, #CCEDF0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D2B2E; }

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
    color: #0D4A50 !important;
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
    color: #0D2B2E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,218,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,208,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,242,255,0.55);
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
        inset -1px 0 0 rgba(100,192,200,0.12),
        inset 0 -1px 0 rgba(100,192,200,0.15),
        0 12px 40px rgba(30,149,160,0.12);
    color: #1A636A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,168,180,0.55) !important;
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
    color: #0A393D !important;
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
        rgba(100,210,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,210,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,244,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,192,200,0.12),
        0 10px 36px rgba(30,149,160,0.13),
        0 2px 8px rgba(30,149,160,0.07);
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
    color: #1C6269;
    font-size: 1.05em;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", serif !important;
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
    color: #0D2B2E;
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
    color: #0D4A50;
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
    border-left: 3px solid rgba(80,227,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,186,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D4A50 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,244,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,149,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,244,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A7880 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,228,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A8890 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,186,200,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8FDFF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,186,200,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,167,180,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A636A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,228,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,228,240,0.40) !important;
    color: #0D4A50 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,186,200,0.30) !important;
    color: #E8FDFF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,228,240,0.60) !important;
    color: #0D4A50 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,186,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,250,255,0.20) !important;
    border: 1px solid rgba(180,249,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,186,200,0.40) !important;
    color: #E8FDFF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,186,200,0.60) !important; }
.tts-speed { color: #1A636A !important; }
.tts-speed input[type="range"] { accent-color: #4ACDD9 !important; }
.tts-progress { background: rgba(180,249,255,0.35) !important; }
.tts-progress-fill { background: rgba(30,186,200,0.55) !important; }
.tts-highlight { background: rgba(30,186,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,228,240,0.35) !important;
    border-top: 1px solid rgba(100,228,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,207,220,0.55) !important;
    text-shadow: 0 0 12px rgba(80,240,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(30,186,200,0.30) !important;
    border: 1px solid rgba(180,249,255,0.60) !important;
    color: #E8FDFF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,149,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(30,186,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,249,255,0.70) !important;
    color: #0D4A50 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,149,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,149,160,0.18) !important;
}
.mh-footer p {
    color: rgba(40,168,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,228,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">智慧简介</div>
  <div class="preface-book-name">传道书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>我们仍与那些快乐的臣子和仆人同列，仍侍立在所罗门面前听他的智慧话（列王纪上10：8）。<br/>这里要传给我们的是他智慧话中的精华，是直接受圣灵感动的话。但愿不要像他的臣子那样，只听一遍，不是听错就是忘记，听多了又觉得没有新鲜感；而是要念，要回顾，要反复思想，永远牢记。我们知道所罗门在作王的后期离弃了神（列王纪上11：1），这是他一生中的悲剧。我们可以知道他在中年写了箴言，那时他持守正直，又在晚年写了传道书（因为他在谈到老年人的重担和衰败的时候栩栩如生，第12 章），那时他藉着神的恩典在失足后重新站立起来。在箴言中他写的是自己的观察，在这里他写的则是自己的经验。正所谓空谈智慧只需数日，而教导智慧则需要多年。本书的题目和作者，我们会在第一节中碰到，这里只需注意以下几点：I. 这是一篇道，是写下来的讲道词；主题是（1：2），虚空的虚空，凡事都是虚空；这也是本文的教义，文中用了许多观点和具体实例来证明这点，且回应不同的看法，最后以勉励的形式指出实际应用，就是要记念造我们的主（12：1），要敬畏他，谨守他的诫命（12：13）。本书中诚然有许多晦暗的东西，很不好理解；有些内容一旦败坏之人强解就自取沉沦（彼得后书3：16），因为他们不能区分这到底是所罗门的观点，还是无神论者或吃喝玩乐之人的谬论。尽管如此，书中仍有许多简单明了的观点，足以证明（如果我们同意的话）这个世界的虚空，远不足以令我们喜乐；世界充满罪恶，只会令我们忧愁；同时也证明敬虔的智慧，以及在神在人面前尽责的真实安慰和满足。每一篇讲道词都应包含这些内容，一篇道若是用各种方式强调这些观点，那就必是一篇好道。II. 这是一篇忏悔的道，有点像大卫的某些诗篇。这是认罪的道，传道者为自己的愚昧和过犯而悲哀叹息，他曾以为能在世间之物中得到满足，甚至以为能在不该有的肉体享乐中得到满足；现在他发现这些东西比死还要苦涩。他的跌倒证明了人性的软弱：智慧人不要因他的智慧夸口（耶利米书9：23），也不要说，“我才不会做这样或那样的傻事，”所罗门这位世人中最有智慧的人，居然也做了这样的傻事。财主不要因他的财物夸口（耶利米书9：23），所罗门的财富成了巨大的网罗，给他带来极大的伤害，超过约伯的贫困所造成的伤害。他的悔改证明神的恩典能将一个如此远离神的人重新拯救回来；他的悔改也证明神丰富的怜悯，尽管他犯下这许多的罪仍然接纳他，为的是成就给大卫的应许，这应许就是倘若他的子孙有任何过犯，神必管教而不是抛弃不顾（撒母耳记下7：14，15）。因此，自以为站立得住的人要小心不要跌倒；已经跌倒的人要赶紧站起来，不要以为自己无可救药。III. 这是一篇非常实用且大有益处的道。所罗门悔改之后像他父亲那样反复思考，要把神的道指教给有过犯的人（诗篇51：13），要警示所有的人留心那些致命的绊脚石；这就是悔改所结的果子。世人根本性的错误（也是远离神的根源）与始祖所犯的错如出一辙，那就是他们希望能像诸神，用好作食物、悦人眼目且使人有智慧（创世纪3：6）的东西来自娱。这卷书就是要表明这样的想法是大错，我们的喜乐不在于能像诸神，不在于随心所欲，而在于尊造物主为神。道德哲学家们在人类福祉这个问题上争论不休。他们有许多不同的看法，而所罗门在本书中一锤定音，他强调敬畏神、谨守他的诫命才是人生的全部。他曾经尝试要从世上财富和肉体享乐中寻求满足，最终却宣告这一切都是虚空，都是捕风。然而许多人仍不把他的话当一回事，仍要亲自尝试做这危险的实验，最终必然丧命。所罗门首先表明，世人普遍以为能给人乐趣的东西，诸如学问、政治、肉体享乐、荣誉和权力、富贵和拥有等等，都是虚空。然后他给出良方要医治世人面对这些东西的烦恼。虽然不能完全治愈虚空，却能避免被这些东西所困扰，只要我们不要太在意这些东西，要好好享福但不要期望过高，凡事顺服神的旨意，特别要趁着年幼记念神，一辈子永远敬畏他、事奉他，并且要看到审判将会到来。</p>
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
    color: rgba(60,207,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(80,240,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(120,244,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(100,192,200,0.10),
        0 10px 36px rgba(30,149,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(40,168,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #0A393D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(80,218,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(40,168,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(80,208,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(100,228,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(100,228,240,0.35) 100%);
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
        0 8px 28px rgba(30,149,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #0D2B2E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(30,186,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(80,227,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(80,208,220,0.35);
}
</style>
