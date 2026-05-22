---
layout: mhenry-preface
book_id: jonah
book_name: 约拿书
header-img: mhenry-land-27.jpg
date: 2026-05-20 10:38
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── jonah 水晶透明风 ──────────────────────────── */

/* 容器：水晶渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6F2E8 0%, #C8EDE0 30%,
        #D8F4EC 60%, #CCF0E6 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D2E1B; }

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
    color: #0D3A20 !important;
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
    color: #0D2E1B;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(40,160,110,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(40,150,105,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(60,180,130,0.55);
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
        inset -1px 0 0 rgba(60,130,100,0.12),
        inset 0 -1px 0 rgba(60,130,100,0.15),
        0 12px 40px rgba(10,80,55,0.12);
    color: #1A4A2E !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(20,100,65,0.55) !important;
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
    color: #0A1E14 !important;
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
        rgba(60,140,110,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(60,140,110,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(80,180,140,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(60,130,100,0.12),
        0 10px 36px rgba(10,80,55,0.13),
        0 2px 8px rgba(10,80,55,0.07);
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
    color: #081E12;
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
    color: #0D2E1B;
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
    color: #0D3A20;
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
    border-left: 3px solid rgba(40,160,120,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(15,110,75,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D3A20 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(80,180,140,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(10,80,55,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(80,180,140,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A4A30 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(60,160,120,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A5E3E !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(15,110,75,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8FFF4 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(15,110,75,0.65) !important;
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
    color: #1A4A2E;
}

/* ── 顶部导航：水晶主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(60,160,120,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(60,160,120,0.40) !important;
    color: #0D3A20 !important;
}
.font-size-ctrl button:hover {
    background: rgba(15,110,75,0.30) !important;
    color: #E8FFF4 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(60,160,120,0.60) !important;
    color: #0D3A20 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(15,110,75,0.30) !important;
}

/* ── TTS 朗读栏：水晶主题 ── */
.tts-bar {
    background: rgba(170,230,205,0.20) !important;
    border: 1px solid rgba(140,210,180,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(15,110,75,0.40) !important;
    color: #E8FFF4 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(15,110,75,0.60) !important; }
.tts-speed { color: #1A4A2E !important; }
.tts-speed input[type="range"] { accent-color: #2A8A60 !important; }
.tts-progress { background: rgba(140,210,180,0.35) !important; }
.tts-progress-fill { background: rgba(15,110,75,0.55) !important; }
.tts-highlight { background: rgba(15,110,75,0.14) !important; }

/* ── 页脚：水晶主题 ── */
.mh-footer hr {
    border-color: rgba(60,160,120,0.35) !important;
    border-top: 1px solid rgba(60,160,120,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(25,120,85,0.55) !important;
    text-shadow: 0 0 12px rgba(45,170,120,0.40);
}
.mh-footer a[href$="/jonah/"] {
    background: rgba(15,110,75,0.30) !important;
    border: 1px solid rgba(140,210,180,0.60) !important;
    color: #E8FFF4 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(10,80,55,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/jonah/"]:hover {
    background: rgba(15,110,75,0.50) !important;
}
.mh-footer a:not([href$="/jonah/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(140,210,180,0.70) !important;
    color: #0D3A20 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(10,80,55,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/jonah/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(10,80,55,0.18) !important;
}
.mh-footer p {
    color: rgba(20,100,65,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(60,160,120,0.30) !important;
}
</style>

<p>约拿书虽然列在圣经的先知书中，它实际上更像是历史书，而不是先知书；书中的预言只有一行字：再等四十日，尼尼微必倾覆了（3：4），其余的内容都是这句预言的始末。在这卷书前面以及这卷书的后面，有不少隐晦的预言，有许多难明的事，令学者们困惑，乃是成年人所吃的干粮
（希伯来书 5：14）；中间却安插了这个简单而宜人的故事，再软弱的人也能欣赏，乃是婴孩所吃的奶。这卷书的笔者可能就是约拿本人，他与摩西和别的受感笔者一样，将自己的错误记录下来，证明这些作品本意都是荣耀神，而不是荣耀自己。列王纪下 14：25 提到过这个约拿，那里说他是位于加利利的迦特希弗人；那城属于西布伦支派，位于以色列地偏远的角落；圣灵像风一样，随自己的意思吹（约翰福音 3：8），能在加利利轻易找到约拿，正如他在耶路撒冷轻易找到以赛亚。那里还说约拿是耶罗波安二在位王期间神向以色列施怜悯的使者，因为耶罗波安打胜仗，收回以色列边界之地，乃是正如耶和华藉他仆人先知约拿所说的。他在那里所说的预言没有记录下来，这段针对尼尼微的预言却记了下来，主要是因为另有一段故事以此为依据，而那段故事记下来，主要是为基督的缘故，约拿预表基督。这段故事含有人性软弱的精彩范例，体现在约拿身上，含有神施恩宽恕悔改罪人的精彩范例，体现在尼尼微人身上，也含有神施恩包容发怨言圣徒的精彩范例，体现在约拿身上。</p>
