---
layout: mhenry-preface
book_id: proverbs
book_name: 箴言
header-img: psalm-bg-49.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

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
    color: #43691C;
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
.mh-footer a[href$="/zechariah/"] {
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
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(115,200,30,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
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
.mh-footer a:not([href$="/zechariah/"]):hover {
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

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">智慧简介</div>
  <div class="preface-book-name">箴言</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>摆在我们面前的是，I. 一位新作者，或应该称为执笔人，或干脆就叫做笔（若是你愿意这么叫），被圣灵所使用，要把神的意念显明给我们，被神的手指（即是神的灵）所驱动写作，他就是所罗门。经他之手写出了圣经的这卷书以及接下来的两卷，传道书和雅歌，一篇道和一首歌。有人认为他年轻时写雅歌，中年时写箴言，晚年时写传道书。在雅歌的标题里他只称自己为所罗门，可能因为这是他登王位之前所写，在年轻时就被圣灵充满。在箴言的标题里他称自己为以色列王大卫儿子所罗门，因为那时他统治整个以色列。在传道书的标题里他称自己为在耶路撒冷作王、大卫的儿子，可能那时他对其他支派的影响力下降，大部分时间呆在耶路撒冷。关于这个作者我们注意到，1. 他是王，也是王之子。圣经排在箴言以前的书卷，其执笔人多半是世上显赫之人，诸如摩西和约书亚，撒母耳和大卫，现在又是所罗门；但是在他之后，受感的作者大部分是穷先知，为世上无地位之人，因为日子将到，神拣选了世上愚拙的，叫有智慧的羞愧；又拣选了世上软弱的，叫那强壮的羞愧（哥林多前书1：27）；他要用贫穷人传福音。所罗门是非常富有的王，他管辖的疆界辽阔；他是卓越的君王，同时也精心研究神的事，他是先知，也是先知之子。将信仰和信仰的律法教导给世上最伟大的君王，这并不贬低他们的身价。2. 为了回应他在登上王位之时的祷告，神赐给他非常丰富的智慧和知识。他的祷告很经典：求你赐我智慧（列王纪上3：9）；神的回应非常令人鼓舞：所罗门不仅得到他所求的，你所没有求的，我也赐给你（列王纪上3：13）。我们在这里看到他如何使用神赐给他的智慧；他不仅用智慧管理自己，用智慧管辖他的王国，也把智慧的法则教导给别人，流传给后代。我们就是要这样把神托付给我们的天资毫无保留地使用出来。3. 他也犯错，在这卷书里他教导别人走神的正途，在晚年自己却离弃了。在列王纪上11 章里有他的故事，那是可悲的故事。这样一卷书的执笔人竟然背弃了神的道。不要在迦特报告（撒母耳记下1：20）。让那些最显赫最有用的人受到警示，不要自大，不要自以为稳妥；也让我们都学会，不要因为教师自己没有做到就轻看良善的教训。<br/>II. 一种新的写作方法，神的智慧用箴言的形式教给我们，就是本身含有完整意思且互相不关联的短句。我们已经见过神的律法书、历史书、诗歌集，现在是神的箴言；无穷的智慧通过各种方式教导给我们，通过一切途径给我们益处，倘若我们还是在愚昧中灭亡，那真是没有借口。用箴言教导，1. 是古代的教学法。在希腊人中这是最远古的教法；古希腊七贤士中每一位都有自认为有价值的箴言使他赖以成名。这些句子被刻在石柱上，被视为来自天上而大受尊敬。譬如，“认识你自己”被认为是来自天上的箴言。2. 是简单明了的教学法，教师和学生都不会觉得痛苦，对理解力和记忆力的要求也不高。亢长难明的八股文不仅叫写文章的人绞尽脑汁，读者看起来也很头疼；而意思明确、短小精悍的箴言则很容易懂也很容易记。大卫的灵修和所罗门的教训都用箴言形式，这种表达方式很适合传讲圣洁的事，祷告和讲道都是这样。3. 是很有用的教学法，很能达到既定的目的。Mashal 这个字，在这里就是箴言的意思，其字根的意思是支配或管辖，因为充满智慧的重要短句给后人带来很大的能力和影响；用箴言教导人能抓住听众的心。我们很容易发现这个世界是如何受箴言管辖。古人有句俗语说（撒母耳记上24：13），或（像我们常说）俗话说，这些都在大多数人心中形成他们的观念，主宰他们的决定。古人的大量智慧就是通过谚语传给后代的；有人认为能从一个民族的谚语形式来判断这个民族的脾性和特点。平时对话中的箴言就像是哲学中的成语，法律中的格言，数学中的定律，没有人会争辩，只会大家抢着要把箴言弄到自己这边来。但是也有许多叫人败坏的俗语，只会败坏人的思想，刚硬人的心去犯罪。魔鬼有他的俗语，世界和属世的事有它们的俗语，那是对神和信仰的抱怨（譬如以西结书12：22；18：2）；神也有他的俗语，为的是保护我们免受那些坏俗语的毒害。神的俗语充满智慧和良善，要叫我们也获得智慧和良善。所罗门的这些箴言不仅仅是古人智慧言语的集成（有人这么认为），也是神的灵透过所罗门写下来的。最前面的那句箴言（1：7）与神最早对人说的话相同（约伯记28：28，敬畏主就是智慧）；所以虽然所罗门很伟大，一提起他的作品就立刻提到他的名字，但是，看哪！<br/>在这里有一人比所罗门更大（路加福音11：31）。是神藉着所罗门在这里向我们说话：我是说，这是向我们说话，因为这些箴言都是为教训我们写的（罗马书15：4），当所罗门对他儿子说话的时候，他的劝勉都像是劝你们如同劝儿子（希伯来书12：5）。在我们灵修中没有哪本书比大卫的诗篇更有用，照样在我们日常交谈中没有哪本书比所罗门的箴言更管用。大卫称神的诫命为极其宽广（诗篇119：96），所罗门的箴言也是极其宽广，短短的句子包含完整的属神的伦理、政治和经济，揭露一切的恶，传扬一切的美德，制定法则要我们在一切关系和条件下以及待人处事时管好自己。博学的赫尔主教从所罗门的箴言和传道书中总结出一套哲学道德体系。这卷书的前面九章可看作是引言，用以勉励世人毫无拦阻地学习并应用智慧的法则。接下来就是所罗门箴言的第一卷（第10-24 章），后面是第二卷（第25-29 章），再后面是亚古珥的预言（第30 章），最后是利慕伊勒的言语（第31 章）。这些章节的内容是一致的，都是要引导我们正确处理人际关系，以致最终我们能看见主的救赎。对这些法则的最好注释就是遵行这些法则。</p>
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
    color: rgba(140,220,60,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(168,255,80,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(188,255,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(150,200,100,0.10),
        0 10px 36px rgba(95,160,30,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(110,180,40,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #243D0A;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(155,230,80,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(110,180,40,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(150,220,80,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(170,240,100,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(170,240,100,0.35) 100%);
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
        0 8px 28px rgba(95,160,30,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #1E2E0D !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(115,200,30,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(160,240,80,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(150,220,80,0.35);
}
</style>
