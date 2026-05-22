---
layout: mhenry-preface
book_id: micah
book_name: 弥迦书
header-img: mhenry-land-28.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── micah 水晶透明风 ──────────────────────────── */

/* 容器：水晶渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F5EDD8 0%, #EDE0C8 30%,
        #F4ECD8 60%, #F0E4CC 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #2E1A0A; }

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
    color: #3A2010 !important;
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
    color: #2E1A0A;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(180,120,40,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(170,115,38,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(210,160,60,0.55);
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
        inset -1px 0 0 rgba(160,120,70,0.12),
        inset 0 -1px 0 rgba(160,120,70,0.15),
        0 12px 40px rgba(120,70,15,0.12);
    color: #4A3018 !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(140,90,20,0.55) !important;
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
    color: #281408 !important;
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
        rgba(170,130,65,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(170,130,65,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(200,160,80,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(160,120,70,0.12),
        0 10px 36px rgba(120,70,15,0.13),
        0 2px 8px rgba(120,70,15,0.07);
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
    color: #1E1008;
    font-size: 0.97em;
    font-family: "Klee One", "STKaiti", "KaiTi", "楷体", serif !important;
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
    color: #2E1A0A;
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
    color: #3A2010;
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
    border-left: 3px solid rgba(180,130,40,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(150,95,20,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #3A2010 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(200,160,80,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(120,70,15,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(200,160,80,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #382A18 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(180,140,60,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #483A28 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(150,95,20,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFF8E8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(150,95,20,0.65) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,80,180,0.60) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #4A3018;
}

/* ── 顶部导航：水晶主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(180,140,60,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(180,140,60,0.40) !important;
    color: #3A2010 !important;
}
.font-size-ctrl button:hover {
    background: rgba(150,95,20,0.30) !important;
    color: #FFF8E8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,140,60,0.60) !important;
    color: #3A2010 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(150,95,20,0.30) !important;
}

/* ── TTS 朗读栏：水晶主题 ── */
.tts-bar {
    background: rgba(240,210,150,0.20) !important;
    border: 1px solid rgba(220,185,120,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(150,95,20,0.40) !important;
    color: #FFF8E8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(150,95,20,0.60) !important; }
.tts-speed { color: #4A3018 !important; }
.tts-speed input[type="range"] { accent-color: #B87820 !important; }
.tts-progress { background: rgba(220,185,120,0.35) !important; }
.tts-progress-fill { background: rgba(150,95,20,0.55) !important; }
.tts-highlight { background: rgba(150,95,20,0.14) !important; }

/* ── 页脚：水晶主题 ── */
.mh-footer hr {
    border-color: rgba(180,140,60,0.35) !important;
    border-top: 1px solid rgba(180,140,60,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(160,110,30,0.55) !important;
    text-shadow: 0 0 12px rgba(190,145,45,0.40);
}
.mh-footer a[href$="/micah/"] {
    background: rgba(150,95,20,0.30) !important;
    border: 1px solid rgba(220,185,120,0.60) !important;
    color: #FFF8E8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(120,70,15,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/micah/"]:hover {
    background: rgba(150,95,20,0.50) !important;
}
.mh-footer a:not([href$="/micah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(220,185,120,0.70) !important;
    color: #3A2010 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(120,70,15,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/micah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(120,70,15,0.18) !important;
}
.mh-footer p {
    color: rgba(140,90,20,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(180,140,60,0.30) !important;
}
</style>

<p>我们会在这卷先知书的第一节经文看到一些关于这位先知的情况，所以这里只需提及他与先知以赛亚是同时代人（只是他开始说预言比以赛亚稍晚），因而这两卷先知书有相似之处；两者都预言福音教会的发展和坚立，所用的词句也几乎相同，以致这话出自两位这样的见证人之口，句句都可定准（马太福音18：16）。比较以赛亚书2：2-3 和弥迦书4：1-2。以赛亚书说是论到犹大和耶路撒冷（以赛亚书1：1），弥迦书则说是论到撒马利亚和耶路撒冷（1：1），因为这卷先知书虽以犹大诸王在位年代为写作日期，但却关乎以色列国；他清楚预言以色列国正在濒临毁灭，
十个支派被掳，并且为之深感哀恸。这里所写的，只是他在三王在位期间多篇讲章的概要。整体内容是：I.叫罪人意识到自己的罪行，将他们的罪行一一列出，谴责以色列和犹大拜偶像、贪婪、
欺压人、藐视神的话，特别是谴责他们的官长滥用职权，包括政教两方面的官长，还向他们表明神的审判随时会向他们爆发，只因他们犯罪。II.安慰神的百姓，应许必有怜悯和拯救，特别是要他们坚信弥赛亚要来，坚信福音的恩典随着他。这卷预言书很精彩，因为它两次在很庄严的场合下被公开引用（证明它的权威），并且两次都预言将来的大事：1.一次是预言耶路撒冷毁灭（3：12），在旧约经文中被国中的长老所引用（耶利米书 26：17-18），用来证明耶利米所说的神的审判要临到耶路撒冷的预言并非虚言，并试图撤销对耶利米的起诉。他们说：弥迦预言锡安必被耕种像一块田，希西家没有因此将他治死，如今耶利米说了同样的话，为何要刑罚他呢？2.另一次是预言基督降生（5：2），在新约经文中被祭司长和民间的文士所引用，用来回答希律的问话：基督当生在何处（马太福音 2：5-6）。这再次表明众先知都为他作见证。</p>
