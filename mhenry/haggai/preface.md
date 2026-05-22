---
layout: mhenry-preface
book_id: haggai
book_name: 哈该书
header-img: mhenry-land-37.jpg
date: 2026-05-20 17:14
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── haggai 水晶透明风 ──────────────────────────── */

/* 容器：水晶渐变 */
#mhenry-col {
    background: linear-gradient(160deg,
        #F5F0D6 0%, #EDE8C8 30%,
        #F4F0D8 60%, #F0EAC8 100%) !important;
    min-height: 100vh;
    padding-bottom: 40px !important;
}

/* 全局文字色 */
#mhenry-col { color: #28200A; }

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
    color: #342A0A !important;
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
    color: #28200A;
    letter-spacing: 0.16em;
    text-align: center;
    background: transparent;
    border-bottom: none;
    text-shadow:
        0 1px 0 rgba(255,255,255,0.95),
        0 2px 12px rgba(180,148,30,0.25);
}
#mhenry-col > h2::after {
    content: '◆';
    display: block;
    font-size: 0.38em;
    color: rgba(170,140,28,0.45);
    margin: 12px auto 0;
    letter-spacing: 0;
    text-shadow: 0 0 10px rgba(210,175,50,0.55);
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
        inset -1px 0 0 rgba(160,135,55,0.12),
        inset 0 -1px 0 rgba(160,135,55,0.15),
        0 12px 40px rgba(130,95,10,0.12);
    color: #423410 !important;
    line-height: 2;
    font-family: "Ma Shan Zheng", "STKaiti", "KaiTi", "楷体", cursive !important;
    font-size: 0.96em;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-overview::before {
    content: '◆  本章综述  ◆' !important;
    display: block !important;
    color: rgba(145,110,15,0.55) !important;
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
    color: #221A08 !important;
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
        rgba(170,145,50,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}
.mh-date-heading::after {
    background: linear-gradient(to left,
        rgba(170,145,50,0.3) 0%,
        rgba(255,255,255,0.9) 100%);
}

/* 经节卡片：水晶棱面效果 */
.mh-unit {
    margin: 0 0 24px;
    border: 1px solid rgba(255,255,255,0.72);
    border-top: 2px solid rgba(200,175,70,0.55);
    border-radius: 16px;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        inset -1px -1px 0 rgba(160,135,55,0.12),
        0 10px 36px rgba(130,95,10,0.13),
        0 2px 8px rgba(130,95,10,0.07);
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
    color: #1C1608;
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
    color: #28200A;
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
    color: #342A0A;
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
    border-left: 3px solid rgba(180,150,30,0.55) !important;
    border-radius: 0 12px 12px 0 !important;
    border-bottom: none !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l1 > .mh-label {
    background: rgba(148,112,12,0.20) !important;
    backdrop-filter: blur(8px) !important;
    color: #342A0A !important;
    font-weight: 800 !important;
    font-size: 0.88em !important;
    padding: 1px 11px !important;
    border-radius: 20px !important;
    border: 1px solid rgba(200,175,70,0.55) !important;
    margin-right: 8px !important;
    box-shadow: 0 1px 6px rgba(130,95,10,0.12) !important;
    vertical-align: middle;
}

/* 1. 2. 3. 次级（二级） */
#mhenry-col .mh-l2 {
    margin: 10px 0 6px 0;
    padding: 8px 0;
    background: rgba(255,255,255,0.14) !important;
    border: none !important;
    border-left: 2px solid rgba(200,175,70,0.40) !important;
    border-radius: 0 8px 8px 0 !important;
    line-height: 1.95;
    text-align: justify;
    letter-spacing: 0.02em;
}
#mhenry-col .mh-l2 > .mh-label {
    color: #322818 !important;
    font-weight: 700 !important;
    margin-right: 6px;
}

/* （1）（2）三级 */
#mhenry-col .mh-l3 {
    margin: 6px 0 4px 0;
    padding: 4px 0;
    border: none !important;
    border-left: 1px dashed rgba(175,148,45,0.40) !important;
    line-height: 1.9;
    text-align: justify;
}
#mhenry-col .mh-l3 > .mh-label {
    color: #423A26 !important;
    font-weight: 600;
    margin-right: 4px;
}

/* 展开按钮 */
#mhenry-col .mh-expand-tab,
#mhenry-col .mh-unit > .mh-verse .mh-expand-tab {
    background: rgba(148,112,12,0.40) !important;
    backdrop-filter: blur(8px);
    border-left: 1px solid rgba(255,255,255,0.30) !important;
    color: #FFFAE8 !important;
}
#mhenry-col .mh-expand-tab:hover {
    background: rgba(148,112,12,0.65) !important;
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
    color: #423410;
}

/* ── 顶部导航：水晶主题 ── */
.font-size-ctrl {
    border: 1px solid rgba(175,148,45,0.60) !important;
    border-radius: 8px !important;
}
.font-size-ctrl button {
    background: rgba(255,255,255,0.40) !important;
    border-right: 1px solid rgba(175,148,45,0.40) !important;
    color: #342A0A !important;
}
.font-size-ctrl button:hover {
    background: rgba(148,112,12,0.30) !important;
    color: #FFFAE8 !important;
}
button[onclick="toggleCalvinCompare()"] {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(175,148,45,0.60) !important;
    color: #342A0A !important;
    border-radius: 8px !important;
}
button[onclick="toggleCalvinCompare()"]:hover {
    background: rgba(148,112,12,0.30) !important;
}

/* ── TTS 朗读栏：水晶主题 ── */
.tts-bar {
    background: rgba(245,228,165,0.20) !important;
    border: 1px solid rgba(225,205,135,0.45) !important;
    border-radius: 10px !important;
    backdrop-filter: blur(8px) !important;
    -webkit-backdrop-filter: blur(8px) !important;
}
.tts-btn {
    background: rgba(148,112,12,0.40) !important;
    color: #FFFAE8 !important;
    border-radius: 6px !important;
}
.tts-btn:hover { background: rgba(148,112,12,0.60) !important; }
.tts-speed { color: #423410 !important; }
.tts-speed input[type="range"] { accent-color: #B89018 !important; }
.tts-progress { background: rgba(225,205,135,0.35) !important; }
.tts-progress-fill { background: rgba(148,112,12,0.55) !important; }
.tts-highlight { background: rgba(148,112,12,0.14) !important; }

/* ── 页脚：水晶主题 ── */
.mh-footer hr {
    border-color: rgba(175,148,45,0.35) !important;
    border-top: 1px solid rgba(175,148,45,0.35) !important;
    margin-top: 0;
}
.mh-footer > div:first-child {
    color: rgba(155,120,20,0.55) !important;
    text-shadow: 0 0 12px rgba(185,152,35,0.40);
}
.mh-footer a[href$="/haggai/"] {
    background: rgba(148,112,12,0.30) !important;
    border: 1px solid rgba(225,205,135,0.60) !important;
    color: #FFFAE8 !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.50),
        0 2px 10px rgba(130,95,10,0.20) !important;
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    transition: background 0.15s;
}
.mh-footer a[href$="/haggai/"]:hover {
    background: rgba(148,112,12,0.50) !important;
}
.mh-footer a:not([href$="/haggai/"]) {
    background: rgba(255,255,255,0.35) !important;
    border: 1px solid rgba(225,205,135,0.70) !important;
    color: #342A0A !important;
    border-radius: 8px !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.80),
        0 2px 8px rgba(130,95,10,0.12) !important;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    transition: background 0.15s, box-shadow 0.15s;
}
.mh-footer a:not([href$="/haggai/"]):hover {
    background: rgba(255,255,255,0.55) !important;
    box-shadow:
        inset 1px 1px 0 rgba(255,255,255,0.90),
        0 4px 14px rgba(130,95,10,0.18) !important;
}
.mh-footer p {
    color: rgba(145,110,15,0.60) !important;
}
.mh-footer > div:last-child {
    border-top: 1px dashed rgba(175,148,45,0.30) !important;
}
</style>

<p>被掳巴比伦这件事，无论是在历史书还是在先知书，都是犹太会众事务的精彩转折。它在我们救主的家谱是一个显著的里程碑（马太福音 1:17）。我们先前学过的十二位先知中的九位生活在被掳以前，并在那时说预言，他们大都在各自的预言中提到了被掳，预言这是对耶路撒冷罪恶的公义惩罚。而最后三位（先知的灵到他们为止暂告一个段落，直到在基督的先锋身上复兴）则生活在被掳回归以后，并在那时说预言，不是刚回归的时候，而是过了一段时候。哈该和撒迦利亚在回归以后十八年几乎同时出现，那时圣殿重建的工程被仇敌耽搁，又被友人忽略。以斯拉记 5:1 说：那时，先知哈该和易多的孙子撒迦利亚奉以色列神的名向犹大和耶路撒冷的犹大人说劝勉的话，批评他们的错误，鼓励他们重启耽搁已久的善工，克服困难，勇敢向前。哈该比撒迦利亚早两个月；撒迦利亚兴起，是为了支持他，要凭两三个人的口作见证，句句都可定准（马太福音 18:16）。不过撒迦利亚事奉的时间较长；哈该有记录的预言都在四个月内完成，在大利乌王第二年的六月初和九月底之间。撒迦利亚的预言则延续到两年以后（撒迦利亚书 7:1）。神的工人当中，有的得了领头的荣誉，有的则得了持久的荣誉。犹太人把大公会成员的荣誉归给这两位先知（就是他们所谓的大公会）；大公会成立于被掳回归以后。有一点我们更加肯定，那就是他们的荣誉在于预言基督，这才是更大的荣誉。哈该说他是这殿后来的荣耀（2:9），撒迦利亚则说他是人，是大卫的苗裔（撒迦利亚书 3:8）。在他们的预言里，晨星的光辉更明亮，胜过先前的先知书，因为他们所在的时代更接近公义的日头升起，已能看见他的日子临近了。七十士译本把哈该当作诗篇第 138 篇的笔者，又把撒迦利亚当作诗篇第 146、147 和 148 篇的笔者。</p>

<p>本章在前言以后：1. 责备犹太人在圣殿重建的事上拖延懈怠，惹动神用饥荒和缺粮的方式与他们相争；勉励他们重启善工，积极投入（第 1-11 节）。2. 这段讲章大有果效，众人果然重新开工，并且一心一意，于是先知奉神的名，激发并鼓励他们，确保神与他们同在（第 12-15 节）。</p>

<p>责备犹太人；神与犹太人相争；先知的劝言（主前 520 年）</p>

<p>1 大利乌王第二年六月初一日，耶和华的话藉先知哈该向犹大省长撒拉铁的儿子所罗巴伯和约撒答的儿子大祭司约书亚说：2 万军之耶和华如此说：「这百姓说，建造耶和华殿的时候尚未来到。」3 那时耶和华的话临到先知哈该说：4「这殿仍然荒凉，你们自己还住天花板的房屋吗？5 现在万军之耶和华如此说：你们要省察自己的行为。6 你们撒的种多，收的却少；你们吃，却不得饱；喝，却不得足；穿衣服，却不得暖；得工钱的，将工钱装在破漏的囊中。」7 万军之耶和华如此说：「你们要省察自己的行为。8 你们要上山取木料，建造这殿，我就因此喜乐，且得荣耀。这是耶和华说的。9 你们盼望多得，所得的却少；你们收到家中，我就吹去。这是为甚么呢？因为我的殿荒凉，你们各人却顾（原文是奔）自己的房屋。这是万军之耶和华说的。10 所以为你们的缘故，天就不降甘露，地也不出产。11 我命干旱临到地土、山冈、五谷、新酒、和油，并地上的出产、人民、牲畜，以及人手一切劳碌得来的。」</p>

<p>犹太人在巴比伦的时候哀叹不见他们的异象，不再有先知（诗篇 74:9）；那是他们所受的公义审判，因为他们嘲笑先知，虐待先知。他们出埃及的时候有先知（何西阿书 12:13），但他们回归的时候，我们却不见有先知。那是神藉着他的灵直接激动他们离开（以斯拉记 1:5）；神虽动用众先知，但并非离不开他们，没有先知，他照样能做工。不过旧约先知的灯尚有一些荣耀的光辉需要发出，然后才熄灭；那时耶和华的言语稀少，不常有默示（如先知时代刚开始的时候一样；撒母耳记上 3:1）；哈该是当时第一位以天上特使的身份出现的。在波斯第三任君王大利乌期间，就是他在位第二年，这位先知奉差遣出现；耶和华的话临到他，又通过他临到犹太人的几位首领，这里提到他们的名字（第 1 节）。1. 有政务方面的主要负责人撒拉铁的儿子所罗巴伯，他出自大卫家，是犹太人从被掳之地回归时的最高长官。2. 有教务方面的主要负责人约撒答的儿子约书亚，当时的大祭司。他们都是大人物，也都是义人，可是当他们犯错的时候，仍需要有人激发他们尽本份。当百姓也犯错的时候，他们就应当被提醒，以致能利用他们的权柄和影响力，纠正百姓的错误。众先知作为特别使者，其职责不在于废去政教两方面的一般规章制度，而在于努力使这两方面更有效，以达到制定这些制度的目的，这两方面都需要扶持。请注意看：</p>

