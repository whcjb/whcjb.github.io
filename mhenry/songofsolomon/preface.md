---
layout: mhenry-preface
book_id: songofsolomon
book_name: 雅歌
header-img: psalm-bg-51.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F8D6E4 0%, #EFC8D8 30%,
        #F8D8E5 60%, #F0CCDB 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E0D1B; }

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
    color: #500D29 !important;
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
    color: #2E0D1B;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(230,80,142,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(220,80,138,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(255,100,165,0.55);
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
        inset -1px 0 0 rgba(200,100,142,0.12),
        inset 0 -1px 0 rgba(200,100,142,0.15),
        0 12px 40px rgba(160,30,84,0.12);
    color: #6A1A3B !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(180,40,98,0.55) !important;
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
    color: #3D0A1F !important;
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
        rgba(220,100,150,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(220,100,150,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(255,120,176,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(200,100,142,0.12),
        0 10px 36px rgba(160,30,84,0.13),
        0 2px 8px rgba(160,30,84,0.07);
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
    color: #691C3C;
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
    color: #2E0D1B;
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
    color: #500D29;
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
    border-left: 3px solid rgba(240,80,147,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(200,30,101,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #500D29 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(255,120,176,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(160,30,84,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(255,120,176,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #801A44 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(240,100,158,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #902A54 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(200,30,101,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFE8F2 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(200,30,101,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(180,20,87,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #6A1A3B;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(240,100,158,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(240,100,158,0.40) !important;
    color: #500D29 !important;
}
.font-size-ctrl button:hover {
    background: rgba(200,30,101,0.30) !important;
    color: #FFE8F2 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(240,100,158,0.60) !important;
    color: #500D29 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(200,30,101,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(255,200,223,0.20) !important;
    border: 1px solid rgba(255,180,211,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(200,30,101,0.40) !important;
    color: #FFE8F2 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(200,30,101,0.60) !important; }
.tts-speed { color: #6A1A3B !important; }
.tts-speed input[type="range"] { accent-color: #D94A86 !important; }
.tts-progress { background: rgba(255,180,211,0.35) !important; }
.tts-progress-fill { background: rgba(200,30,101,0.55) !important; }
.tts-highlight { background: rgba(200,30,101,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(240,100,158,0.35) !important;
    border-top: 1px solid rgba(240,100,158,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(220,60,127,0.55) !important;
    text-shadow: 0 0 12px rgba(255,80,153,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(200,30,101,0.30) !important;
    border: 1px solid rgba(255,180,211,0.60) !important;
    color: #FFE8F2 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(160,30,84,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(200,30,101,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(255,180,211,0.70) !important;
    color: #500D29 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(160,30,84,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(160,30,84,0.18) !important;
}
.mh-footer p {
    color: rgba(180,40,98,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(240,100,158,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">智慧简介</div>
  <div class="preface-book-name">雅歌</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>我们坚信圣经都是神所默示的（提摩太后书3：16），在世人中有利于扶持和发展神国的利益。<br/>即便其中有些难明白的，圣经仍大有益处，而那无学问、不坚固的人强解，就自取沉沦（彼得后书3：16）。我们相信本书出自神，相信灵意解释本书，这可以从犹太教会和基督教会的历史悠久的双重见证得到证实。对犹太教会而言，神的圣言交托他们（罗马书3：2），他们从不怀疑本书的权威性；基督教会也十分乐于承继这样的信任和尊荣。I. 我们一方面必须承认，若是问一个几乎未读过此书的人，就像问那个太监一样，你所念的，你明白吗？他定然会说，没有人指教我，怎能明白呢（使徒行传8：30）？圣经中的历史书和先知书之间有许多相似之处，但所罗门的雅歌却与他父亲大卫的诗篇大不相同。雅歌没有提到神的名，从未在新约被引用，没有信仰的言辞或虔诚的灵修，其中的信息不是藉着异象传递，也没有启示的痕迹。要把这卷书当成活的香气叫人活（哥林多后书2：16），似乎比圣经中其他的书卷都难，而若是带着世俗眼光和败坏心态来读此书，这简直就是死的香气叫他死，好比一朵有毒的花。因此犹太学者们不建议他们的年轻人在三十岁以前读此书，免得污秽了最纯洁、最神圣之物。从天而降的火要吞噬欲望之火（说起来真可怕！），这天火是专门为祭坛预备的。II. 我们另一方面也必须承认，借助于许多诚实的注释，我们明白这卷书实际上是光彩夺目且大有能力的天光，非常适合激发众圣徒敬虔真诚的情感，激发他们渴慕神，加增他们在主里的喜悦，帮助他们与神相通。这卷书是一则寓言，其中的字句叫那些只停留在字面而不深入领会的人去死，但其中的精义却叫人活（哥林多后书3：6；约翰福音6：63）。这卷书是一个比喻，叫不喜爱神的事的人更加看不懂神的事，也叫喜爱神的事的人更容易看懂也更喜乐（马太福音13：14，16）。有属灵经历的基督徒在这卷书中找到自己的经历；他们能看明白，而那些在属灵的事上没有分的人却不明白，也不能品味。这卷书是一首歌，是婚姻之歌，藉着新郎和新妇之间的爱情表白，表达神与一群特殊的剩余之民之间的互爱。这卷书是一首田园诗，为了更生动地体现谦和与天真，新郎和新妇被塑造成牧羊人和牧羊女。1. 犹太教会通常按灵意解释这首歌。它一开始就是为犹太教会写的，似乎在亚兰文意译本中以及最早的犹太解经家中也是如此解释。神视以色列民为自己的新妇，与他们立约，那是一个婚约。他在许多方面证明自己爱他们，也要求他们尽心尽性地爱他。拜偶像常被视为灵意上的奸淫，这首歌就是为杜绝偶像而写，表达神喜爱以色列民，也表达以色列民应当喜爱神，应当忠实于他。尽管他有时似乎向他们隐藏，也要等候神藉着所应许的弥赛亚重新显明自己。2. 这首歌在基督教会更应按灵意解释，因为神的爱藉着福音降世且与人交通，比在律法之下更加丰盛，更加自由，天与地之间的交通显得更真实。神有时称自己为犹太教会的丈夫（以赛亚书64：5；何西亚书2：16，19），且喜悦自己的新妇（以赛亚书62：4，5）。但圣经更多地将基督视为教会的新郎（马太福音25：1；罗马书7：4；哥林多后书11：2；以弗所书5：32），视教会为新妇，乃羔羊的新妇（启示录19：7；21：2，9）。根据这个比喻，基督与教会之间，尤其是基督与信徒之间那丰富的互敬互爱在此表露无遗。开启这卷书的最佳钥匙是诗篇第45 篇，那首诗在新约里应用在基督身上，所以这卷书也理应如此。也许我们需要费一些功夫才能明白圣灵在此书中的几个地方到底是什么意思；不像大卫的诗歌，许多地方连最平凡的人也能明白；这里有些是浅水滩，有些则高深得可以使大象游泳。然而，一旦意义被解开，就能激发我们内心的敬虔和真诚。同样的真理若在圣经其他书卷中显而易见，而若是来自这卷书则带有更加可悦的能力。我们研习这卷书的时候，不但要像摩西和约书亚那样把脚上的鞋脱下来，甚至忘记自己还有身体，因为我们所站之地是圣地（出埃及记3：5），还要像约翰那样，上到这里来（启示录4：1）。要展开我们的翅膀，优雅地飞向天边，直到我们凭着信心和圣洁的爱进入至圣所（希伯来书10：19），因为这不是别的，乃是神的殿，也是天的门（创世纪28：17）。</p>
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
    color: rgba(220,60,127,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(255,80,153,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(255,120,176,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(200,100,142,0.10),
        0 10px 36px rgba(160,30,84,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(180,40,98,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #3D0A1F;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(230,80,142,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(180,40,98,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(220,80,138,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(240,100,158,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(240,100,158,0.35) 100%);
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
        0 8px 28px rgba(160,30,84,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #2E0D1B !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(200,30,101,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(240,80,147,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(220,80,138,0.35);
}
</style>
