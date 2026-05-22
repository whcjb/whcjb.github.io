---
layout: mhenry-preface
book_id: zephaniah
book_name: 西番雅书
header-img: mhenry-land-31.jpg
date: 2026-05-20 14:53
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── zephaniah 水晶透明风 ──────────────────────────── */

/* 容器：水晶渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6DBF5 0%, #C8CCEC 30%,
        #D8DCF5 60%, #CCCFEE 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D1228; }

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
    color: #0D1835 !important;
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
    color: #0D1228;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(60,85,195,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(58,80,185,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(75,100,230,0.55);
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
        inset -1px 0 0 rgba(70,85,155,0.12),
        inset 0 -1px 0 rgba(70,85,155,0.15),
        0 12px 40px rgba(25,50,140,0.12);
    color: #1A2248 !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(30,60,155,0.55) !important;
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
    color: #0A0E20 !important;
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
        rgba(70,95,180,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(70,95,180,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(85,115,215,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(70,85,155,0.12),
        0 10px 36px rgba(25,50,140,0.13),
        0 2px 8px rgba(25,50,140,0.07);
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
    color: #080D1C;
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
    color: #0D1228;
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
    color: #0D1835;
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
    border-left: 3px solid rgba(60,95,200,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(28,65,165,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D1835 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(85,115,215,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(25,50,140,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(85,115,215,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A2038 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(68,100,205,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A2E4A !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(28,65,165,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #EEF2FF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(28,65,165,0.65) !important;
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
    color: #1A2248;
}

/* ── 顶部导航：水晶主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(68,100,205,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(68,100,205,0.40) !important;
    color: #0D1835 !important;
}
.font-size-ctrl button:hover {
    background: rgba(28,65,165,0.30) !important;
    color: #EEF2FF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(68,100,205,0.60) !important;
    color: #0D1835 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(28,65,165,0.30) !important;
}

/* ── TTS 朗读栏：水晶主题 ── */
.tts-bar {
    background: rgba(175,195,245,0.20) !important;
    border: 1px solid rgba(155,175,230,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(28,65,165,0.40) !important;
    color: #EEF2FF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(28,65,165,0.60) !important; }
.tts-speed { color: #1A2248 !important; }
.tts-speed input[type="range"] { accent-color: #3A60C0 !important; }
.tts-progress { background: rgba(155,175,230,0.35) !important; }
.tts-progress-fill { background: rgba(28,65,165,0.55) !important; }
.tts-highlight { background: rgba(28,65,165,0.14) !important; }

/* ── 页脚：水晶主题 ── */
.mh-footer hr {
    border-color: rgba(68,100,205,0.35) !important;
    border-top: 1px solid rgba(68,100,205,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(45,80,185,0.55) !important;
    text-shadow: 0 0 12px rgba(60,100,210,0.40);
}
.mh-footer a[href$="/zephaniah/"] {
    background: rgba(28,65,165,0.30) !important;
    border: 1px solid rgba(155,175,230,0.60) !important;
    color: #EEF2FF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(25,50,140,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/zephaniah/"]:hover {
    background: rgba(28,65,165,0.50) !important;
}
.mh-footer a:not([href$="/zephaniah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(155,175,230,0.70) !important;
    color: #0D1835 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(25,50,140,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/zephaniah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(25,50,140,0.18) !important;
}
.mh-footer p {
    color: rgba(30,60,155,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(68,100,205,0.30) !important;
}
</style>

<p>这位先知被安排在被掳前小先知的最后，因为从时间上说他是最后一位；他出现在耶利米之前不久，耶利米在被掳的时候还活着。这位先知预言迦勒底人要全面毁灭犹大和耶路撒冷；他将他们的罪陈明在他们面前，就是惹怒神降灾给他们的罪；他呼吁他们悔改，警告邻国必有类似的毁灭临到，并给他们鼓舞人心的应许，说他们必在所定的日子从被掳之地回归，这也指向福音的恩典。第1节对这位先知和他说预言的日期略有介绍，我们不必在这里探究。</p>
