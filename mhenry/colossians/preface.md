---
layout: mhenry-preface
book_id: colossians
book_name: 歌罗西书
header-img: nt-hero-colossians-preface.jpg
date: 2026-07-01 15:42
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── colossians 水晶透明风 ──────────────────────────── */

/* 容器：冷蓝晶体渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #D6DBF8 0%, #C8CDEF 30%,
        #D8DCF8 60%, #CCD1F0 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #0D112E; }

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
    color: #0D1650 !important;
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
    color: #0D112E;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(80,100,230,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(80,99,220,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(100,121,255,0.55);
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
        inset -1px 0 0 rgba(100,113,200,0.12),
        inset 0 -1px 0 rgba(100,113,200,0.15),
        0 12px 40px rgba(30,47,160,0.12);
    color: #1A256A !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(40,59,180,0.55) !important;
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
    color: #0A113D !important;
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
        rgba(100,116,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(100,116,220,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(120,138,255,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(100,113,200,0.12),
        0 10px 36px rgba(30,47,160,0.13),
        0 2px 8px rgba(30,47,160,0.07);
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
    color: #1B266B;
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
    color: #0D112E;
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
    color: #0D1650;
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
    border-left: 3px solid rgba(80,101,240,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(30,53,200,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #0D1650 !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(120,138,255,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(30,47,160,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(120,138,255,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #1A2880 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(100,119,240,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #2A3890 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(30,53,200,0.85) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #E8EBFF !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(30,53,200,0.95) !important;
}
#mhenry-col .mh-unit.mh-expanded .mh-expand-tab {
    background: rgba(20,41,180,0.30) !important;
}

/* 脚注 */
.mhenry-footnotes {
    background: rgba(255,255,255,0.25);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 14px 16px;
    border: 1px solid rgba(255,255,255,0.50);
    color: #1A256A;
}

/* ── 顶部导航：水晶蓝主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(100,119,240,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(100,119,240,0.40) !important;
    color: #0D1650 !important;
}
.font-size-ctrl button:hover {
    background: rgba(30,53,200,0.30) !important;
    color: #E8EBFF !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(100,119,240,0.60) !important;
    color: #0D1650 !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(30,53,200,0.30) !important;
}

/* ── TTS 朗读栏：水晶蓝主题 ── */
.tts-bar {
    background: rgba(200,207,255,0.20) !important;
    border: 1px solid rgba(180,190,255,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(30,53,200,0.40) !important;
    color: #E8EBFF !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(30,53,200,0.60) !important; }
.tts-speed { color: #1A256A !important; }
.tts-speed input[type="range"] { accent-color: #4A5DD9 !important; }
.tts-progress { background: rgba(180,190,255,0.35) !important; }
.tts-progress-fill { background: rgba(30,53,200,0.55) !important; }
.tts-highlight { background: rgba(30,53,200,0.14) !important; }

/* ── 页脚：水晶蓝主题 ── */
.mh-footer hr {
    border-color: rgba(100,119,240,0.35) !important;
    border-top: 1px solid rgba(100,119,240,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(60,81,220,0.55) !important;
    text-shadow: 0 0 12px rgba(80,103,255,0.40);
}
.mh-footer a[href$="/colossians/"] {
    background: rgba(30,53,200,0.30) !important;
    border: 1px solid rgba(180,190,255,0.60) !important;
    color: #E8EBFF !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(30,47,160,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/colossians/"]:hover {
    background: rgba(30,53,200,0.50) !important;
}
.mh-footer a:not([href$="/colossians/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(180,190,255,0.70) !important;
    color: #0D1650 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(30,47,160,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/colossians/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(30,47,160,0.18) !important;
}
.mh-footer p {
    color: rgba(40,59,180,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(100,119,240,0.30) !important;
}
</style>

<div class="preface-wrap">

<div class="preface-emblem">✠</div>

<div class="preface-title-block">
  <div class="preface-label">书信简介</div>
  <div class="preface-book-name">歌罗西书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◇</span></div>

<div class="preface-body">
<p>歌罗西乃是弗吕家一大城，距老底嘉和希拉波立不远——这些城在第 4:13 节被同时提及。此城如今已埋在废墟中，其纪念大部分被此书信保存下来。**本书信之目的乃是警戒他们防备犹太狂热者之危险**——那些人极力要人守礼仪律法之必要——**又要坚固他们，免受外邦人哲学与他们基督徒之原理混杂之扰**。他极其满意于他们之坚立与恒定，又鼓励他们持守。**本书与致以弗所人书、致腓立比人书大约同时写成——就是主后 62 年——地点也相同**（当时他在罗马作囚犯）。**他在被囚中并非闲着**，**神之道也没有被捆锁**。</p>

<p>这封书信如同致罗马人书一样，写给他从未见过、也从未有个人相识之人。**歌罗西之教会不是由保罗之服事栽起来的，乃是由以巴弗——或以巴弗提——一位福音使者、就是他所差在外邦人中传福音之人所栽的**；然而：</p>

<p>I. **歌罗西有一兴旺之教会，又是众教会中出色而闻名之一**。**人或许以为——除了保罗亲手栽种的教会——别无兴旺之教会**；**但此处有一以巴弗所栽之兴旺教会**。**神有时喜悦用那些名声较小、恩赐较低者之服事——为他的教会大大成就工作**。**神用他所喜用之手，并不拘限于著名之人——好叫"这莫大之能显是从神来的，不是从我们来的"**（哥林多后书 4:7）。</p>

<p>II. **虽保罗未曾栽这教会，他却并未因此忽略之**；**在他所写的众书信中，他也没有对这教会与他其他教会作任何差别**。**歌罗西人——那些藉以巴弗之服事归主之人——在他心中亲切一如腓立比人、或任何藉他自己服事归主之人**。**他如此把尊重加于一位不如自己出色之传道人，又教导我们不可自私，不当把凡"不归自己"之荣视为失去**。**我们从他之榜样学得——不当以浇灌他人所栽之物、或在他人所奠之根基上建造为羞**——**如他自己作智慧之工头奠了根基，别人在其上建造**（哥林多前书 3:10）。</p>
</div>

<div class="preface-closing">
  ✠  &ensp; ◇  &ensp; ✠
  <span class="preface-closing-verse">「凡你们所做的，或说话或行事，都要奉主耶稣的名。」</span>
  <span class="preface-closing-verse-ref">— 歌罗西书 3:17 —</span>
</div>

</div>
