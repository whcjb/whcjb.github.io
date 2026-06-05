---
layout: mhenry-preface
book_id: genesis
book_name: 创世记
header-img: psalm-bg-mountain.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F8F0D6 0%, #EFE5C8 30%,
        #F8F0D8 60%, #F0E7CC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E260D; }

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
    color: #503F0D !important;
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
    color: #2E260D;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(230,193,80,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(220,185,80,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(255,216,100,0.55);
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
        inset -1px 0 0 rgba(200,175,100,0.12),
        inset 0 -1px 0 rgba(200,175,100,0.15),
        0 12px 40px rgba(160,128,30,0.12);
    color: #6A561A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(180,145,40,0.55) !important;
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
    color: #3D300A !important;
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
        rgba(220,190,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(220,190,100,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(255,221,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(200,175,100,0.12),
        0 10px 36px rgba(160,128,30,0.13),
        0 2px 8px rgba(160,128,30,0.07);
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
    color: #69561C;
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
    color: #2E260D;
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
    color: #503F0D;
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
    border-left: 3px solid rgba(240,200,80,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(200,158,30,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #503F0D !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,221,120,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(160,128,30,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(255,221,120,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #80661A !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(240,205,100,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #90762A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(200,158,30,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFF9E8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(200,158,30,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(180,140,20,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #6A561A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(240,205,100,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(240,205,100,0.40) !important;
    color: #503F0D !important;
}
.font-size-ctrl button:hover {
    background: rgba(200,158,30,0.30) !important;
    color: #FFF9E8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(240,205,100,0.60) !important;
    color: #503F0D !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(200,158,30,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(255,241,200,0.20) !important;
    border: 1px solid rgba(255,236,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(200,158,30,0.40) !important;
    color: #FFF9E8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(200,158,30,0.60) !important; }
.tts-speed { color: #6A561A !important; }
.tts-speed input[type="range"] { accent-color: #D9B54A !important; }
.tts-progress { background: rgba(255,236,180,0.35) !important; }
.tts-progress-fill { background: rgba(200,158,30,0.55) !important; }
.tts-highlight { background: rgba(200,158,30,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(240,205,100,0.35) !important;
    border-top: 1px solid rgba(240,205,100,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(220,180,60,0.55) !important;
    text-shadow: 0 0 12px rgba(255,211,80,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(200,158,30,0.30) !important;
    border: 1px solid rgba(255,236,180,0.60) !important;
    color: #FFF9E8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(160,128,30,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(200,158,30,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255,236,180,0.70) !important;
    color: #503F0D !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(160,128,30,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(160,128,30,0.18) !important;
}
.mh-footer p {
    color: rgba(180,145,40,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(240,205,100,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">律法简介</div>
  <div class="preface-book-name">创世记</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>摆在我们面前的这本书就是圣经，或称为书，因为圣经一词原意就是书。称之为书，是因为此书绝无仅有，堪称史上最佳作品，是书中之书，在知识的穹苍里就像日头发光，而其它有价值的书不过是月亮星辰，反射日头的光辉。称之为圣，是因为此书由圣者写成，由圣灵引导，没有一点错谬，没有败坏的动机，其用意显而易见，就是在人间倡导圣洁。书中所写的是关乎神律法的大事，关乎福音的大事，好叫这些事切实可信，流传得更广更久远，传遍天涯海角，传到各个时代，并且传得更纯更完整，非民间传说或人的传统所能比拟。人若无视这些白纸黑字写下来的关乎平安的大事，若以为与自己毫无关涉（何西阿书8：12），就必被追讨。从摩西到圣约翰，这些受感之人笔下的经文将神的光渐渐显明出来，如同晨光照耀。如今神圣的正典既已完成，感谢赞美神，这些经文就在我们手中这本配得称颂的圣经里，叫我们在世的日子得以完全。书中的一字一句都是好的，放在一起则甚好。圣经如同灯照在暗处（彼得后书1：19）。这世界若没有圣经，诚然就是暗处。
摆在我们面前的这部份圣经称为旧约，内容关乎以色列民从创世以来一直到基督道成肉身之前大约四千年的事迹与丰碑，包括那段时期所显明的真理，所实施的律法，所表现的忠诚，所传讲的预言，以及关乎这个特殊群体的大事。凡是神认为对我们有益的，均一一记录在册。之所以称为约，是因为圣经郑重宣告神的遗嘱，关乎普世的人。立遗嘱人是耶稣，就是从创世以来被杀的羔羊（启示录 13：8）。神命定叫他死，遗嘱因他的死全面生效。之所以称为旧约，是相对新约而言。新约并不废弃旧约，也不取代旧约，而是完善旧约，成全旧约，叫旧约中所预表所预言的那更美的盼望成为现实。旧约仍有荣光，但新约的荣光更大（哥林多后书 3：9）。
摆在我们面前的这部份旧约称为摩西五经，就是摩西写的五卷书。摩西是耶和华的仆人，他超越众先知，预表至大的先知耶稣。主耶稣把旧约书卷分成摩西的律法、先知的书，和诗篇上所记的
（路加福音 24：44），后者也称为智慧书。我们在这里要看的就是摩西的律法，因为摩西五经的后四卷包含颁布给以色列民的律法，第一卷又包含颁布给亚当、挪亚和亚伯拉罕的律法。我们知道这五卷书是史上最早的文字，因为整卷创世记中从未提到有过文字记载，直到神吩咐摩西写在书上（出埃及记17：14）。有人认为摩西自己从未学过写字，直到神把写有十诫的石板给了他。
不过我们确信这几卷书是迄今所发现的最古老的文字，因而也最有权威告诉我们远古的事。
摆在我们面前的是摩西五经中的第一卷，也是最长的一卷，称为创世记。有人认为这是摩西在米甸的时候写的，旨在教导和安慰在埃及受苦的众弟兄。我倒觉得这是他在旷野的时候的作品，写于他与神在山上见面之后。很可能神在山上全面具体地指示他将此书写出来，他就领命照办。摩西写此书，完全照着在山上指示他的样式（出埃及记 25：40），就像他搭建会幕那样，只是所用的布料更为精致耐用。为此，书中所写的事都真实可信，其可信度远超过口传的传统；那口传的可能从亚当传到玛土撒拉，从玛土撒拉传到闪，从闪传到亚伯拉罕，又从亚伯拉罕传到雅各家。
“创世记”一词源自希腊文，原意是起初或家谱。以此为这卷书的书名很是恰当，因为此书关乎起初的历史，就是世界被造，罪和死进入世界，艺术的发明，列国兴起，尤其是关乎以色列民的栽种，以及它早期的光景。这也是家谱的历史，指亚当、挪亚、亚伯拉罕等人的家谱，并非无穷的家谱（提摩太前书1：4），乃是很有意义的家谱世代。新约的开头也用了这个词：耶稣基督的家谱（马太福音1：1）。旧约揭开我们的伤口，新约则告诉我们良药何在。神是应当称颂的！主啊，愿你开启我们的眼睛，好叫我们看见你律法的奇妙，看见福音的奇妙！</p>
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
    color: rgba(220,180,60,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(255,211,80,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(255,221,120,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(200,175,100,0.10),
        0 10px 36px rgba(160,128,30,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(180,145,40,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #3D300A;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(230,193,80,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(180,145,40,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(220,185,80,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(240,205,100,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(240,205,100,0.35) 100%);
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
        0 8px 28px rgba(160,128,30,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #2E260D !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(200,158,30,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(240,200,80,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(220,185,80,0.35);
}
</style>
