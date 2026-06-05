---
layout: mhenry-preface
book_id: psalms
book_name: 诗篇
header-img: psalm-bg-48.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zechariah 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6DCF8 0%, #C8CEEF 30%,
        #D8DDF8 60%, #CCD2F0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D132E; }

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
    color: #0D1850 !important;
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
    color: #0D132E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,105,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,103,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,126,255,0.55);
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
        inset -1px 0 0 rgba(100,117,200,0.12),
        inset 0 -1px 0 rgba(100,117,200,0.15),
        0 12px 40px rgba(30,52,160,0.12);
    color: #1A276A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,63,180,0.55) !important;
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
    color: #0A133D !important;
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
        rgba(100,120,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,120,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,143,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,117,200,0.12),
        0 10px 36px rgba(30,52,160,0.13),
        0 2px 8px rgba(30,52,160,0.07);
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
    color: #1C2A69;
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
    color: #0D132E;
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
    color: #0D1850;
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
    border-left: 3px solid rgba(80,107,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,58,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D1850 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,143,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,52,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,143,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A2B80 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,123,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A3B90 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,58,200,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8ECFF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,58,200,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,47,180,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A276A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,123,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,123,240,0.40) !important;
    color: #0D1850 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,58,200,0.30) !important;
    color: #E8ECFF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,123,240,0.60) !important;
    color: #0D1850 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,58,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,209,255,0.20) !important;
    border: 1px solid rgba(180,193,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,58,200,0.40) !important;
    color: #E8ECFF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,58,200,0.60) !important; }
.tts-speed { color: #1A276A !important; }
.tts-speed input[type="range"] { accent-color: #4A62D9 !important; }
.tts-progress { background: rgba(180,193,255,0.35) !important; }
.tts-progress-fill { background: rgba(30,58,200,0.55) !important; }
.tts-highlight { background: rgba(30,58,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,123,240,0.35) !important;
    border-top: 1px solid rgba(100,123,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,87,220,0.55) !important;
    text-shadow: 0 0 12px rgba(80,109,255,0.40);
}
.mh-footer a[href$="/zechariah/"] {
    background: rgba(30,58,200,0.30) !important;
    border: 1px solid rgba(180,193,255,0.60) !important;
    color: #E8ECFF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,52,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zechariah/"]:hover {
    background: rgba(30,58,200,0.50) !important;
}
.mh-footer a:not([href$="/zechariah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,193,255,0.70) !important;
    color: #0D1850 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,52,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zechariah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,52,160,0.18) !important;
}
.mh-footer p {
    color: rgba(40,63,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,123,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">智慧简介</div>
  <div class="preface-book-name">诗篇</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>摆在我们面前的是整卷旧约圣经中最上乘、最优秀的部份之一；因其中不仅多有神和他的律法，也多有基督和他的福音，故而堪称两约的摘要或总纲。以色列的历史我们研习了很久，它把我们带到军营，带到议事厅，得以欣赏并学习神的知识。约伯记把我们领进学校，用关乎神和天意的有益辩论来款待我们。本书则把我们带进圣所，使我们不再与人、与政客、与哲学家或世上的辩士打交道，而是与神相通，使我们的灵魂在他里面得安慰，得安息，我们的心向他提升，向他敞开。我们可在圣山上如此与神交往，乃至人人都会说：我们在这里真好（马太福音17：4）；若有人不这样说，那就是不明白自己的利益所在。现在让我们来看看：I.本书的标题。1.称为诗篇；路加福音24：44 用了这样的标题。希伯来文标题的原意是赞美诗，因其中有很多这样的诗；不过诗篇这个词意思更广泛，泛指一切有韵律、能诵唱的作品，其内容可以是赞美性的，也可以是历史性的，教导性的，或祈求性的。尽管歌声往往是喜乐之声，但诗歌的意图广泛得多，可帮助记忆，也可表达并激发除喜乐以外的各种情感。祭司的曲调有欢乐的，也有悲哀的；诗歌乃是神所设定，其意图就在于此，因为我们不但要赞美神，也要用诗章、颂词、灵歌，彼此教导，互相劝戒（歌罗西书3：16），也教导并劝诫自己。2.称为诗篇书卷；圣彼得是这样说的（使徒行传1：20）。这是一本诗篇集，是所有受感而成之诗的集成，这些诗作于不同时代，不同背景，没有互相引用，也不互相依赖；这样就便于保存，不致散落，也便于会众服事之用。可见我们所事奉的主何其美善，智慧的道路何其可悦，他不仅吩咐我们边作工边唱歌，还给我们足够的缘由如此行，甚至把歌词放在我们口中，把歌曲交在我们手里。<br/>II.本书的作者。诗篇无疑出自那可称颂的圣灵。这些都是灵歌，是圣灵所指教的话语。诗篇的笔者大都是耶西的儿子大卫，因而他也称为以色列的美歌者（撒母耳记下23：1）。有的诗在标题中没有提他的名，却在别处说明是他所写，譬如第2 篇（使徒行传4：25），第96 和105 篇（历代志上第16 章）。有一首注明是摩西的祷告（第90 篇）；有的注明由亚萨所写，历代志下29：30 说大卫和亚萨的诗词颂赞耶和华，还称他为先见，就是先知。有的似乎是很久以后写成的，譬如第137 篇，作于被掳巴比伦的时候；但大多数仍是大卫本人所写，他精通诗歌和音乐，又被兴起，受装备，被激发，在属神的会众中建立诗歌礼仪，就如摩西和亚伦在他们的时代被兴起，受装备，被激发，建立了祭祀礼仪；祭祀礼仪早已过时，但诗歌礼仪犹存，并要存到时间的末了，且在那时淹没在永恒的颂歌中。由此大卫预表基督；基督出于大卫，不出于摩西，因为他来，就是要废去祭祀（摩西家族很快衰亡），建立喜乐和赞美，且要永存，而大卫家在基督里必将没有穷尽。<br/>III.本书的范围。1.有助于操练自然信仰，在世人的灵魂深处挑旺虔诚的火，以神为造物主，为主宰，为君王，为恩主。约伯记有助于证明关乎神的完美和主权的首要原则，诗篇则帮助我们藉着祷告和赞美，藉着宣告对他的渴慕、倚靠，和全然委身交托，将这些首要原则运用出来。圣经在别处表示神无限超越人，乃是人的主宰，诗篇则表示尽管如此，他仍与我们这些满身罪孽、活在地上的虫交往，我们在人生各样境遇中，仍有与他相通的途径；若不能与他相通，那就是我们的错。2.意在传扬启示信仰的卓越性，并且以最怡人的有力方式，将启示信仰推荐给世人。整卷诗篇几乎不提礼仪性的律法。尽管祭物和祭祀还要持续很多代，但在诗篇中却被说成是神所不喜悦的（40：6；51：16），说成是相对而言极小的事，是将来要废去的事。而神的话语和律法，就是与道德和永远义务相关的部份，则贯穿始终，并得到发扬和尊崇，是别处所不能比拟的。基督乃是启示信仰的桂冠和中心，是那蒙福建筑的根基、房角石和头块石头；本书以预表和预言的形式清楚谈到他，谈到他受苦和随之而来的荣耀，谈到他要在世上建立国度，而神与大卫所立的关乎他国度的约，则要应验在基督的国度。本书对神的话语、诫命和判语、他的约和约中那些又大又宝贵的应许推崇备至，并且推荐给我们，作我们的向导和支柱，乃是我们永远的产业。<br/>IV.本书的作用。圣经都是神的默示，都能将神的光传输到我们的意念中，也都于我们有益，但诗篇在这方面尤其突出，它将神的生命和能力，将圣洁的温暖，带入我们的情感。圣经各书卷中最能帮助圣徒灵修的，非本书莫属，自从成书以来，自从部份章节交与伶长用于会众敬拜以来，在历代教会一向如此。1.本书用来吟唱，作用很大。我们固然可在大卫的诗篇以外寻找诗章和灵歌，但却没有必要。希伯来语的韵律规则，就连学者都不能确定，但这些诗若翻译出来，就该按各国语言的韵律，至少要能唱出来，使教会得造就。我们唱大卫的诗，竟然能和大卫时代和其他虔诚的犹大王时代一样，向神献上同样的赞美，我觉得这是我们的极大安慰。这些圣诗何其丰富，何其优美，乃至永不枯竭，永不过时。2.本书由基督的传道人念诵并开启，作用很大，因其中含有伟大卓越的真理，含有关乎善恶的标准。我们的主耶稣向门徒诠释诗篇，福音的诗篇，开启他们的悟性（他拿着大卫的钥匙；启示录3：7），使他们明白（路加福音24：44）。3.本书由所有的义人念诵并默想，作用很大。这是满溢的泉源，人人都可从中欢然取水。（1）诗人的经历很有用，可引导、劝诫并鼓励我们。他常把他的灵魂和神之间的交往告诉我们，让我们知道我们可对神有何指望，也知道神对我们有何指望，有何要求，知道如何行才能蒙他恩典的悦纳。大卫是个合神心意的人，所以人若在某种程度上与他同心，便可盼望得更新，藉着神的恩典，按着神的形象；有许多人因为自己的良心见证而大得安慰，乃至他们发自内心，向大卫的祈祷和赞美说声阿们。（2）诗人的言辞也很有用，圣灵以此扶持我们祷告中的软弱，因为我们不知道如何正确祷告。无论是首次归向神，还是平时来到神的面前，我们都蒙引导，用言语祷告（何西阿书14：2），就是用这些言语，用圣灵所指教的言语。若能熟悉大卫的诗篇（理当熟悉），那么无论因何来到施恩座前，或认罪，或祈求，或感恩，我们都能借用这些言语来表达；无论有何虔诚之心在里面动工，无论是圣洁的渴慕还是盼望，是忧愁还是欢喜，我们都可在那里找到合宜的言辞穿戴停当，说出不被定罪的话来。若能将其中最合宜、最生动的敬虔言辞整理起来，加以条理化，归纳出一些祷告的主题来，方便使用，就不失为一件美事。我们也可选用一首上乘的诗，有时选这首，有时选那首，用在祷告中，就是在心里仔细思量每一节经文，将所产生的默想献给神。学识渊博的哈蒙德博士1在他的诗篇释义前言中（第29 段）指出：「诗中原有的生命和活力阐明、激发并维系了不少内在敬虔的重点；带着这些重点读其中的几首，胜过诵读整卷，因为信仰服事中最应该规避的，就是信仰服事沦为无精打采的背诵。」如圣奥古斯丁2所言，我们的心灵若与诗中的情感相吻合，那时便可在使用诗中言辞的时候确信必蒙神的悦纳。诗篇这卷书不仅帮助我们灵修，帮助我们表达内心的情感，不仅指教我们如何以赞美为祭献上，乃至荣耀神，也是我们日常生活中行事为人的指南，教导我们如何按正路而行，乃至最终得着神的救恩（50：23）。诗篇在旧约会众当中的作用尚且如此，对我们基督徒而言，其作用犹胜基督降世之前的人；这是因为大卫的诗歌和摩西律法一样，都有基督福音的诠释，因而我们更容易明白，是基督的福音把我们带进幔内；所以，有了大卫的祷告和赞美，再加上保罗书信中的祷告，再加上启示录里的新歌，我们便可在这善工中得到充分的装备；圣经一旦完成，属神的人就完全。<br/>至于本书的分段，我们不必过于拘泥；各诗之间并无联系（或联系极少），各诗所出现的顺序也没有明显的讲究；不过各诗顺序似乎自古就是如此，现在的第二篇在使徒时代也是第二篇（使徒行传13：33）。拉丁文版将第9 和第10 篇合为一篇；所有天主教的作家都引用拉丁版，因而自那以后的诗，其编号都比我们的版本小一号，我们的第11 篇相当于他们的第10 篇，我们的第119 篇相当于他们的第118 篇。但他们又将第147 篇分为两篇，凑满150 篇。有人试图按内容将诗篇归类，但同一首诗往往内容多样化，很难明确归类。不过许多人在灵修中把那七首忏悔诗算为同类，就是第6、32、38、51、102、130 和143 篇。诗篇共分为五卷，每一卷的结尾都是阿们，阿们，或哈利路亚；第一卷结尾在第41 篇，第二卷结尾在第72 篇，第三卷在第89 篇，第四卷在第106 篇，第五卷在第150 篇。有的将诗篇分成三卷，每卷五十篇；也有的将之分成六十段，一个月中每天念诵两段，一段在早晨，一段在晚上。愿良善的基督徒自己分段，只要能增加熟悉度便可，乃至在各样场合随时使用，在灵里吟唱，带着悟性吟唱。</p>
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
    color: rgba(60,87,220,0.40);
    margin: 24px 0 18px;
    text-shadow: 0 0 16px rgba(80,109,255,0.50);
    letter-spacing: 0;
}

/* 标题块 */
.preface-title-block {
    text-align: center;
    margin-bottom: 6px;
    padding: 0;
    background: rgba(255,255,255,0.28);
    border: 1px solid rgba(255,255,255,0.70);
    border-top: 2px solid rgba(120,143,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.85),
        inset -1px -1px 0 rgba(100,117,200,0.10),
        0 10px 36px rgba(30,52,160,0.12);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
}
.preface-label {
    font-size: 11px;
    letter-spacing: 0.40em;
    color: rgba(40,63,180,0.55);
    font-weight: 700;
    margin-bottom: 10px;
    text-transform: uppercase;
}
.preface-book-name {
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    font-size: 2.2em;
    color: #0A133D;
    letter-spacing: 0.20em;
    line-height: 1.2;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 14px rgba(80,105,230,0.22);
    margin-bottom: 10px;
}
.preface-sub {
    font-size: 12px;
    color: rgba(40,63,180,0.50);
    letter-spacing: 0.18em;
}

/* 分隔线 */
.preface-divider {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 20px 0 18px;
    color: rgba(80,103,220,0.40);
    font-size: 12px;
}
.preface-divider::before,
.preface-divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(to right,
        rgba(255,255,255,0.9) 0%,
        rgba(100,123,240,0.35) 100%);
}
.preface-divider::after {
    background: linear-gradient(to left,
        rgba(255,255,255,0.9) 0%,
        rgba(100,123,240,0.35) 100%);
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
        0 8px 28px rgba(30,52,160,0.10);
}
.preface-body p {
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", cursive !important;
    font-size: 1.05em !important;
    line-height: 2.1 !important;
    color: #0D132E !important;
    text-indent: 2em;
    text-align: justify;
    letter-spacing: 0.03em;
    margin-bottom: 0 !important;
}
/* 首字下沉 */
.preface-body p::first-letter {
    font-size: 3em;
    font-family: "Ma Shan Zheng", "STKaiti", cursive;
    color: rgba(30,58,200,0.65);
    float: left;
    line-height: 0.78;
    margin: 6px 6px 0 0;
    text-shadow: 0 2px 10px rgba(80,107,240,0.30);
}

/* 结尾装饰 */
.preface-closing {
    text-align: center;
    margin-top: 22px;
    font-size: 10px;
    letter-spacing: 0.15em;
    color: rgba(80,103,220,0.35);
}
</style>
