#!/usr/bin/env python3
"""translate_taylor.py —— 托马斯·泰勒《提多书注释》(剑桥 1612) 英文版 → 中文 raw。

骨架照搬 translate_jenkyn.py（含 2026-11-03 补的三道闸修正：希腊词尾形近拉丁字母按原文还原、
原文本就混写的词不算错、随原文逐字照抄的拉丁短词/带重音拉丁词不算漏译）。
CLI 调用统一走 translate_filibi.call_claude → claude_usage.call_cli，自动带 CLI_TRIM_FLAGS
（--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt 替换默认提示词：
不发工具定义、MCP、CLAUDE.md、skills、hooks）。不要在这里自己拼 subprocess 调 claude。

源取**已发布的英文页** taylor/titus/<slug>.md（判读补字、[推补] 已落进去）。
缺字记号 <span class="ty-gap">…</span> 整个是一个占位符；推补 <span class="ty-conj">[词]</span> 只遮标签，方括号里的词照译。

输入  taylor/titus/<slug>.md（篇目见 publish_taylor_en.build_pages）
缓存  taylor_raw/titus/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  taylor_raw/titus/zh_chapters/<slug>.md ← 翻完 chmod 444
时刻  taylor_raw/titus/zh_meta.json         ← 每篇真正调过模型那次的时刻

用法（项目根目录）：
    python3 -u scripts/translate_taylor.py --dry-run --all
    python3 -u scripts/translate_taylor.py --all --resume          # 单路；多路须用户特别指示
"""
import argparse
import json
import os
import re
import subprocess
import sys
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402  复用 CLI/缓存/泄漏判据

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'taylor' / 'titus'
RAW = ROOT / 'taylor_raw' / 'titus'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
ITALIC_LOG = RAW / 'zh_italic_notes.log'   # 斜体程序修/对数不同的记录，人工抽查用
META = RAW / 'zh_meta.json'
KEY_NS = 'TAYLOR_TITUS::'

SYSTEM = (
    "你是一位精通改革宗神学与早期近代英语的中文译者，正在翻译英格兰清教徒传道人托马斯·泰勒"
    "（Thomas Taylor, 1576–1633）《提多书注释》（A Commentarie vpon the Epistle of S. Paul written to Titus，"
    "剑桥 1612 年初版），原为他在剑桥所讲。泰勒按经文逐段讲解：先释经义（the meaning），再列教义（doctrines）"
    "与应用（uses），条目层层编号，好用比喻，多引教父与经院学者，并与天主教徒（Papists）辩驳。\n"
    "原文是 1610 年代英文：拼法古旧（u/v、i/j 混用：vpon=upon，haue=have，Iewes=Jews，Iesus=Jesus；"
    "-nesse=-ness，onely=only，sinne=sin，then 常作 than；doth/hath，-eth/-est）；"
    "所有格常不加撇号；长句多分号与冒号。要按意思读懂后译成现代中文。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气。条目编号、层次照原文；"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（原书页码、经文框、节号标签、旁注外壳、原书缺字记号等），"
    "**必须原样逐个保留**，个数、先后都与原文一致，放在中文里对应的位置。"
    "有的占位符是原书**缺字处**，紧挨着残缺的字母（如 ⟦4⟧o、ab⟦5⟧sement）："
    "占位符照留，残字母不要输出，按上下文把句子译通\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。原文斜体的部分（人名、书名、拉丁词、引文、强调语），"
    "中文里对应的词照样用 `*` 包起来，一处对一处：不要把相邻两处斜体并成一处，不要自己增添斜体，"
    "不要只包一个「第」字、数字或标点\n"
    "4. **凡引用圣经经文，一律照抄和合本**；他用 KJV 或自己的译法，与和合本措辞不同时仍以和合本为准；"
    "但凡他说 that is / i. e. 后给出的是自己的解释，按他的英文译；"
    "**原文只给出处、没有引经文的，只译出处，不要自己补出经文**\n"
    "5. 经文框里被讲解的经文（单独一段的提多书经文）照抄和合本该节；"
    "节号标签 Ver. 1. / Vers. 10, 11. → 第 1 节 / 第 10–11 节；CHAP. I. → 第一章\n"
    "6. 方括号 [ ] 里的词是编者推补的（原书此处缺损），照样译出，**方括号原样保留**\n"
    "7. `&c.` → ……（不作「等等」）；`v.` / `ver.` / `verse` → 第 N 节；`Chap.` → 第 N 章；"
    "`i. e.` / `that is` → 即\n"
    "8. 拉丁文、希腊文、希伯来文一律保留原文，其后用圆括号附中文译义，如 *Gratia gratis data*（白白赐下的恩典）；"
    "希腊文、希伯来文逐字照抄，一个字母、一个重音符号都不许改\n"
    "9. 圣经书卷名、人名、地名用和合本标准译名：Titus→提多，Paul→保罗，Timothy→提摩太，Crete/Creet→克里特，"
    "Cretians→克里特人，Nicopolis→尼哥波立，Zenas→西纳，Apollos→亚波罗，Artemas→亚提马，Tychicus→推基古，Moses→摩西\n"
    "10. 经文出处一律转成「书卷名 章:节」：Rom. 8.28. → 罗马书 8:28；1 Cor. 3.6. → 哥林多前书 3:6；"
    "Psal. 32.1. → 诗篇 32:1；Prov. 18.10. → 箴言 18:10；Heb. 10.22. → 希伯来书 10:22；"
    "Iob → 约伯记；Ioh. → 约翰福音；Isa./Esay → 以赛亚书；Mat. → 马太福音；Luk. → 路加福音；"
    "Matth. 5.23, 24. → 马太福音 5:23-24\n"
    "11. **凡音译出来的专名（人名、地名、民族与教派名），每篇首次出现都要括注英文原名**，"
    "不分古今、不论中文是否早有定译：奥古斯丁（Augustine）、伯尔纳（Bernard）、屈梭多模（Chrysostom）、"
    "塞涅卡（Seneca）、普鲁塔克（Plutarch）、加尔文（Calvin）、路德（Luther）、耶稣会士（Jesuits）。"
    "缩写形式照样括注全名或原写法，如 Aug. → 奥古斯丁（Aug.）。同一篇里第二次以后不再重复括注。"
    "只有和合本里本来就有的圣经人名地名（提多、保罗、克里特）不括注\n"
    "12. 术语精确、互不撞词：justification→称义　sanctification→成圣　regeneration→重生　"
    "election/the Elect→拣选/选民　calling→蒙召　grace→恩典　faith→信心　hope→盼望　the Gospel→福音　"
    "the Law→律法　Mediator→中保　the Word→道　Ministers→传道人　Sacraments→圣礼　carnal→属肉体的　"
    "Saints→圣徒　holiness→圣洁　godlinesse→敬虔　vertue→德行　knowledge→知识　temperance→节制　"
    "patience→忍耐　charity→爱　Elders→长老　Bishop→监督　sound doctrine→纯正的道理　"
    "false teachers→假师傅　Papists→天主教徒　the Pope→教皇　Doctrine→教义　Vse→应用\n"
    "13. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」，全书前后一致\n"
    "13b. **注意中文词的褒贬色彩**：原文是正面的神学说法，不得用带贬义的中文词（据为己有、霸占、攫取、侵吞……）。"
    "appropriate / appropriating faith 指信心把基督与应许领受过来归给自己——译「领受归己」「领受为己有」，"
    "如 personal, appropriating, and assured faith → 个人的、领受归己的、确信的信心；"
    "只有原文是僭取、侵占的负面义（arrogate、usurp、take to himself what is not his）才译「据为己有」。"
    "personal faith / personal interest → 个人的信心 / 切身的利害（不作「亲身的」）\n"
    "14. **不得把任何英文词原样留在中文句子里**；印本里偶有的排印错字，按上下文读通后译出，"
    "不要留残词，也不要另加说明"
)

RE_GAP = re.compile(r'<span class="ty-gap"[^>]*>.*?</span>')
RE_TAG = re.compile(r'<[^<>]{1,400}>')
RE_IAL = re.compile(r'\{:[^}\n]*\}')          # kramdown 属性行，整个一个占位
RE_ANY = re.compile(RE_GAP.pattern + '|' + RE_TAG.pattern + '|' + RE_IAL.pattern)
RE_PH = re.compile(r'⟦(\d+)⟧')


def mask(text: str):
    tags = []

    def put(m):
        tags.append(m.group(0))
        return f'⟦{len(tags)}⟧'
    # 一趟扫完，编号跟着出现顺序走；缺字记号连同里面的 ▪ 整个一个占位
    return RE_ANY.sub(put, text), tags


def unmask(text: str, tags):
    return RE_PH.sub(lambda m: tags[int(m.group(1)) - 1]
                     if 0 < int(m.group(1)) <= len(tags) else m.group(0), text)


def is_keep_block(b: str) -> bool:
    """整块只有标签 / 标题外壳、没有要译的文字 → 原样保留，不进模型。"""
    return not re.search(r'[A-Za-zΑ-ωἀ-ῼ]', RE_TAG.sub('', b))


CHATTY_RE = re.compile(
    # 2026-11-09 收紧：只认「对着人说话、讨原文」的搭配。裸的「未提供 / 没有附上 / 无法翻译 / 你似乎」是正当译文
    # （「叙事本身未提供足够的材料」、加尔文祷文「你似乎一时将我们抛弃」），使徒行传 9#20 曾因此三次被拦。
    # 回归：15.1 万块缓存新增误报 0、旧误报 8 处放行、真对话 4 处仍抓；注入 3000 次全抓
    r'((?:您|你)似乎(?:没有|没|忘|只|未|漏|并未|是想)|请把原文|请提供(?:原文|文本|英文|内容|需要|要翻译|待译)|'
    r'(?:没有附上|未附上|未提供|没有提供|没提供)(?:任何)?(?:原文|文本|英文|内容|需要翻译|要翻译|待译)|'
    r'无法翻译(?:这段|此段|该段|您|你|所提供|空白)|'
    r'as an ai|i (?:cannot|can\'t|don\'t see)|please provide)', re.I)
# 拉丁字母含 À-ɏ（Latin-1 补充 + 扩展 A/B）：早期印本拉丁文用 ē ō ū ā 表示省略的 m/n
# （probationē、Excōmunicatio、mendaciū），只认 ASCII 会把词切碎、碎片被当成漏译（2026-11-03 提多书 3:10 两次误拦）
STRAY_EN = re.compile(r'(?<![（(A-Za-zÀ-ɏ])[A-Za-zÀ-ɏ][A-Za-zÀ-ɏ\'’-]{2,}(?![*）)A-Za-zÀ-ɏ])')
GREEK = r'Ͱ-Ͽἀ-῿'
RE_GREEK_TOK = re.compile(rf'[{GREEK}̀-ͯ]+')
RE_MIXED = re.compile(rf'[{GREEK}]+[A-Za-z]+|[A-Za-z]+[{GREEK}]+')
LATIN_OK = re.compile(r'[A-Za-z]')


EN_COMMON = set("""
the and that this with which have from they their them there these those were been being would could should
shall will what when where while whom whose because therefore however wherefore whereas although though
also only even very more most such than then thus into upon unto about after before against among between
through without within under over again other another every each both either neither nothing something
anything everything someone people thing things time times reason reasons place first second third last
word words make made take taken give given come came know known think thought say said same your yours
ours his hers its our not but for are was has had can may must might shall him her who how why all any
keep fine translate translation translated italic italics output note rule here good right well just like
faith love grace sin sinners sinner god lord christ spirit holy church world life death heart soul man men
""".split())


def stray_english(zh: str, en: str):
    """光溜溜落在中文句子里的英文词。斜体内、括注里、原文里本就有的拉丁词都不算。"""
    en_words = {w.lower() for w in re.findall(r'[A-Za-zÀ-ɏ]{3,}', en)}
    out = []
    for m in STRAY_EN.finditer(zh):
        s, e = m.start(), m.end()
        if zh.count('*', 0, s) % 2 == 1:
            # 斜体里多是保留的拉丁原文，一般放行；但常见英语词（拉丁文里不出现）又不在原文里 → 漏译或模型自语
            # （2026-11-03 注入测试：斜体内漏译 84/397 全漏抓）
            if not (m.group(0).lower() in EN_COMMON and m.group(0).lower() not in en_words):
                continue
        if re.search(r'[A-Za-z]\s*$', zh[:s]) or re.match(r'\s*[A-Za-z]', zh[e:]):
            continue
        # 带重音的拉丁词被 ASCII 判据切碎（1-3-2 `ipsâ vitâ` → `ips` `vit`）：紧挨着 à-ÿ 的片段是拉丁原文
        if re.match(r'[À-ɏ]', zh[e:e + 1]) or re.search(r'[À-ɏ]$', zh[:s]):
            continue
        # 短词在原文里有、且紧邻的词也是原文里的词（拉丁引文被模型顺手规范了拼写：mendaciū→mendacium）
        if len(m.group(0)) < 4 and m.group(0).lower() in en_words:
            near = re.findall(r'[A-Za-z]{3,}', zh[max(0, s - 24):s] + ' ' + zh[e:e + 24])
            if any(w.lower() in en_words and len(w) >= 4 for w in near):
                continue
        # 印本把一个词排断（ipsâ vit â），模型接回成 vitâ：去掉原文空格后能找到即是照抄
        toks = re.findall(r'[A-Za-zÀ-ɏ]+', en.lower())
        if len(m.group(0)) >= 4 and re.search(r'[À-ɏ]', m.group(0)) \
                and m.group(0).lower() in {x + y for x, y in zip(toks, toks[1:])}:
            continue
        # 拉丁缩写被模型展开（probationē → probationem）：原文有 ≥6 字母的同词干、只是词尾多一两个字母
        wl = m.group(0).lower()
        if any(len(x) >= 6 and wl.startswith(x) and len(wl) - len(x) <= 2 for x in en_words):
            continue
        # 短词随一段原文逐字照抄（1-11-3 旁注 `Deo & parenti non redditur aquivalens.` 原样保留）
        if len(m.group(0)) < 4 and (zh[s:s + 14] in en or zh[max(0, e - 14):e] in en) and len(zh[s:s + 14]) >= 12:
            continue
        out.append(m.group(0))
    # 拉丁整句引文：连续多个英文词出现，多半是保留的拉丁原文，不算漏译
    # 原文里带句点的缩写（旁注引书 *Pet. Dam.*、*Bed.*、*Aqu.*）照录不译，三个字母的也放过
    abbr = {w.lower() for w in re.findall(r'\b([A-Z][a-z]{1,3})\.', en)}
    return [w for w in out if (w.lower() not in en_words or len(w) < 4) and w.lower() not in abbr]


HOMO = dict(zip('aAbBeEhHiIkKmMnNoOpPtTuUxXyYzZvs',
                'ααββεεηηιικκμμννοορρττυυχχυυζζνσ'))


def restore_greek(zh: str, en: str) -> str:
    """模型把希腊词后半截写成形近的拉丁字母（`ἀποδιορίζοντES` `δένδρa` `στῆσαI` `ἐποικοδom`，
    犹大书首轮 5 篇卡在这上面，重译两次照样犯）。在原文里找「希腊前缀相同、总长相同」的希腊词，
    唯一命中才原样换回——只是把原文那个词抄回来，不猜；对不上就留给结构闸去拦。"""
    nfc = lambda x: unicodedata.normalize('NFC', x)
    src = set(RE_GREEK_TOK.findall(nfc(en)))

    def fix(m):
        w = m.group(0)
        g = re.match(rf'[{GREEK}̀-ͯ]+', w)
        if not g or w in en:
            return w
        pre = nfc(g.group(0))
        cand = [t for t in src if t.startswith(pre) and len(t) == len(nfc(w)) and t != pre]
        if len(cand) > 1:
            # 同前缀同长的不止一个（κατανύσσω / κατάνυξις）：拉丁字母按字形对回希腊字母、去重音后逐字比
            base = lambda x: ''.join(c for c in unicodedata.normalize('NFD', x.lower())
                                     if not unicodedata.combining(c)).replace('ς', 'σ')
            look = base(''.join(HOMO.get(c, c) for c in nfc(w)))
            cand = [t for t in cand if base(t) == look]
        return cand[0] if len(cand) == 1 else w
    return re.sub(rf'[{GREEK}̀-ͯ]+[A-Za-z]{{1,4}}[{GREEK}̀-ͯ]*', fix, zh)


RE_EN_RUN = re.compile(r"[A-Za-z][A-Za-z'’]*(?:[ ,.;:]+[A-Za-z][A-Za-z'’]*){3,}")
EN_FUNC = {'the', 'with', 'and', 'this', 'that', 'here', 'is', 'are', 'i', 'will', 'you', 'your', 'answer',
           'translation', 'translate', 'output', 'only', 'alone', 'bare', 'below', 'following', 'text', 'rule'}


# 白名单字符：汉字、中文标点、ASCII、拉丁扩展、希腊、希伯来、常用标点与符号。
# 名单外又不在原文里的 → 模型吐的垃圾（2026-11-03 普查五书：🧠 ⓘ ╋ ︰ ℰ ᐅ 变体选择符 零宽空格、韩文「징兆」、制表线「─」）
OK_CHARS = re.compile(r'[\u0000-\u007F\u00A0-\u024F\u02B0-\u036F\u0370-\u03FF\u0590-\u05FF\u1E00-\u1FFF'
                      r'\u2010-\u2027\u2030-\u205E\u2160-\u2188\u2190-\u22FF\u25A0-\u25FF\u27E6-\u27EF'
                      r'\u2E00-\u2E7F\u2E80-\u2FDF\u3000-\u303F\u31C0-\u31EF\u3400-\u4DBF\u4E00-\u9FFF'
                      r'\uF900-\uFAFF\uFF00-\uFFEF\u2116\u2122]')


# 已知形近错字（模型偶尔把生僻字写成形近常用字；统计扫描误报太多，发现一个收一个）
KNOWN_TYPOS = {'亡古': '亘古'}


def odd_chars(zh: str, en: str):
    """名单外、原文也没有的字符。零宽空格夹在两个斜体星号之间（*​*）是有用的，放过。"""
    t = zh.replace('*\u200b*', '**')
    return sorted({c for c in t if not OK_CHARS.match(c) and c not in en})


_CUV = None


def cuv_text() -> str:
    """简体和合本全文去标点连成一串，用来认「这一句是不是照抄的经文」。"""
    global _CUV
    if _CUV is None:
        d = json.loads((Path(__file__).resolve().parent.parent / 'assets' / 'cuv.json').read_text(encoding='utf-8'))
        _CUV = ''.join(re.sub(r'[^\u4e00-\u9fff]', '', v)
                       for bk in d.values() for ch in bk.values() for v in ch.values())
    return _CUV


def en_repeats(en: str) -> bool:
    """原文里有没有本来就重复出现的片段（连续 6 词以上）——重复引同一节经文。"""
    w = re.findall(r"[a-z]+", en.lower())
    seen = set()
    for i in range(len(w) - 5):
        g = tuple(w[i:i + 6])
        if g in seen:
            return True
        seen.add(g)
    return False


def scripture_repeat(dup, en: str) -> bool:
    """译文里重复的句子是否都是照抄的和合本经文、且原文本身就重引了经文。
    约翰一书第 27 讲一段把诗 66:18–20 先引一遍、又在一位古人的话里引一遍，
    忠实的译文必然两次出现「他并没有推却我的祷告……」，三次重试都被当成重复起稿拦下。
    只放行这一种；原文没重复、或重复的不是经文原句，照旧拦。"""
    if not en_repeats(en):
        return False
    cuv = cuv_text()
    for x in dup:
        k = re.sub(r'[^\u4e00-\u9fff]', '', x)
        if len(k) < 8 or k not in cuv:
            return False
    return True


def structural_diff(en: str, zh: str) -> str:
    problems = []
    # 原文里本来就混写的（1-17 `hypostaticῶs`：印本用 ῶ 表 ō）照抄是对的，不算
    mixed = [w for w in RE_MIXED.findall(zh) if w not in en]
    if mixed:
        problems.append('希腊文混入拉丁字母 ' + '、'.join(mixed[:4]))
    nfc = lambda s: unicodedata.normalize('NFC', s)
    src = set(RE_GREEK_TOK.findall(nfc(en)))
    extra = [w for w in RE_GREEK_TOK.findall(nfc(zh)) if len(w) > 1 and w not in src]
    if extra:
        problems.append('原文没有的希腊词 ' + '、'.join(extra[:4]))
    # 斜体对数不同不算结构问题、不重译（2026-10-27 用户：斜体要一遍过，不要重译）。
    # 实测雷登+亚当斯首轮被打回的 296 段里 261 段只是斜体对数不同、星号都成对，重译换不来实质改进；
    # 落单的星号在 translate_one 里由 fix_italics 程序修，不调模型。
    # 模型在译文前后自加的英文话（腓利门书 to-the-reader：`Answer with the bare translation alone.`）。
    # 「连续多个英文词＝保留的拉丁引文」那条放行会放过它；拉丁引文里几乎不出现英语虚词，按虚词个数认
    for run in RE_EN_RUN.findall(zh):
        ws = re.findall(r"[a-z']+", run.lower())
        if len(ws) >= 4 and sum(w in EN_FUNC for w in ws) >= 2 and run.strip(' .,;:') not in en:
            problems.append('模型自语 ' + run.strip()[:60])
            break
    typo = [w for w in KNOWN_TYPOS if w in zh]
    if typo:
        problems.append('已知错字 ' + '、'.join(f'{w}→{KNOWN_TYPOS[w]}' for w in typo))
    odd = odd_chars(zh, en)
    if odd:
        problems.append('异常字符 ' + ' '.join(f'{c}(U+{ord(c):04X})' for c in odd[:4]))
    pe, pz = RE_PH.findall(en), RE_PH.findall(zh)
    if pe != pz:
        problems.append(f'占位符不符 {pe} → {pz}')
    stray = stray_english(zh, en)
    if stray:
        problems.append('漏译的英文词 ' + '、'.join(sorted(set(stray))[:5]))
    if CHATTY_RE.search(zh):
        problems.append('模型在对话而非翻译')
    # 起稿残留：模型先写一句草稿（「约翰一书 3:18 → 见 1 约翰一书 3:18」）再从头重写，
    # 两版都留在输出里——星号、占位符都对得上，旧闸看不见（试译第 1 章 1:22 抓到）
    tag = re.search(r'</?[^<>⟦⟧\s]{1,20}>', zh)
    if tag and tag.group(0) not in en:      # 取标签漏网的 <译文> 之类
        problems.append(f'残留标签 {tag.group(0)}')
    if '→' in zh and '→' not in en:
        problems.append('起稿残留（→）')
    sents = [x for x in re.split(r'[。！？；]', zh) if len(x) >= 20]
    dup = [x for x in set(sents) if sents.count(x) > 1]
    if dup and not scripture_repeat(dup, en):
        problems.append('同一句出现两次（重复起稿）：' + dup[0][:20])
    leak = tf.output_leak(zh)
    if leak:
        problems.append(leak)
    # 第 2-5 章抓到的三种：思考过程整段漏出（<thinking> / Count asterisks…）、
    # 半路自我纠正（「——不对，须照抄：」后再写一遍）、只吐半句就停（4:19 只剩 ἐν ἀγαthinking）
    m = re.search(r'</?thinking|——不对|不对，须|须照抄|\bHmm\b|Count asterisks', zh)
    if m and not re.search(re.escape(m.group(0)), en):
        problems.append(f'模型自语「{m.group(0)}」')
    if len(en) > 200 and len(re.findall(r'[一-鿿]', zh)) < len(en) * 0.1:   # 经文框/卷首页正常比例也只有 0.14 上下
        problems.append(f'疑似截断（原文 {len(en)} 字符，译文汉字 {len(re.findall(r"[一-鿿]", zh))}）')
    if re.search(r'[A-Za-z]{4}', en) and not re.search(r'[一-鿿]', zh):
        problems.append('译文无汉字')
    return '；'.join(problems)


RE_TAGGED = re.compile(r'<译文>(.*?)</译文>', re.S)


def take_tagged(raw: str) -> str:
    """只取 <译文>…</译文> 里的内容。模型没处可想时会把推敲（This is an index entry /
    Rule: … / Hmm）写进输出，各书约 3–6% 的调用因此重试；2026-11-03 回放 24 段曾自语的原文：
    不加标签不合格 4 段，开原生思考 4 段（自语反而 3 次），加标签两遍 48 次 0 段。
    模型漏了标签就原样返回，交给 structural_diff 把关。"""
    m = RE_TAGGED.findall(raw)
    if m:   # 开标签写了两次（「<译文>.\n\n<译文>三、…</译文>」，约翰一书第 10 讲）：取最后一个开标签之后
        return m[-1].rsplit('<译文>', 1)[-1].strip()
    if '<译文>' in raw:                       # 只写了开标签：取其后
        raw = raw.rsplit('<译文>', 1)[1]
    return raw.replace('</译文>', '').strip()


def tidy(zh: str) -> str:
    zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
    # 只有一行标题、其余全是占位符的块，模型常当成问答，开头冒出「答案：」（腓利门书 to-the-reader）
    zh = re.sub(r'^(?:答案|译文|翻译|中文译文|Answer|Translation)\s*[:：]\s*', '', zh)
    zh = re.sub(r'[〔［]([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .\'’-]*)[〕］]', r'（\1）', zh)
    # &c. 一律省略号（全站通则）
    zh = re.sub(r'(等等|等语|云云)(?=[」』。，；：）\s]|$)', '……', zh)
    return zh


# 人工逐段核过、确认无误却过不了结构闸的译文（多为模型把相邻两段斜体并成一段）。
# 列在这里，--resume 时不再当坏缓存重译。一行一个 md5 key，# 后是说明。
ACCEPTED = RAW / 'zh_accepted.txt'


def accepted_keys():
    if not ACCEPTED.exists():
        return set()
    return {ln.split()[0] for ln in ACCEPTED.read_text(encoding='utf-8').splitlines()
            if ln.strip() and not ln.startswith('#')}


class SevereTranslation(Exception):
    """重试后仍有严重结构问题的段落：不写缓存，整篇不发布，等人处理。"""


def is_severe(diff: str) -> bool:
    """斜体已不进 structural_diff（见 fix_italics）；保留此判断兼容旧日志格式：只剩斜体问题算轻微，其余都算严重。"""
    return bool(diff) and any(not p.startswith('斜体 * 数量不符') for p in diff.split('；'))


def fix_italics(zh: str, en: str, label: str) -> str:
    """斜体只做程序修、不重译：星号落单（奇数个）→ 去掉本段全部斜体标记；对数与原文不同 → 只记一笔待抽查。"""
    if zh.count('*') % 2:
        note = f'斜体 * 落单（{zh.count("*")} 个），已去掉本段斜体'
        zh = zh.replace('*', '')
    elif zh.count('*') != en.count('*'):
        note = f'斜体对数不同 {en.count("*") // 2} → {zh.count("*") // 2} 对（未重译，待抽查）'
    else:
        return zh
    with ITALIC_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'[{label}] {note}\n')
    return zh


def translate_one(text: str, resume: bool, label: str = '') -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached) or key in accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}', flush=True)

    base = ("把下面这段泰勒《提多书注释》的十七世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    out = fix_italics(restore_greek(tidy(take_tagged(tf.call_claude(base + text, timeout=900, label=label))), text),
                      text, label)
    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留**"
               " ⟦N⟧ 占位符（个数与先后都要对上）；希腊文逐字照抄；"
               "**不得把任何英文词原样留在中文句子里**。把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
        # 重试两次，取第一个合格的；都不合格就取「只剩斜体问题」的那一版
        for n in (1, 2):
            out2 = fix_italics(restore_greek(tidy(take_tagged(tf.call_claude(fix + text, timeout=900, label=f'{label}·retry{n}'))), text),
                               text, f'{label}·retry{n}')
            if not structural_diff(text, out2):
                out = out2
                break
            if not is_severe(structural_diff(text, out2)) or is_severe(diff):
                out, diff = out2 or out, structural_diff(text, out2 or out)
        else:
            with BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {structural_diff(text, out)}\n'
                         f'  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')
            # 严重问题（自语/截断/重复起稿/希腊文走样/占位符错）不进缓存、不发布：
            # 第 1 章与第 2-5 章两次都是「记一笔日志、照样发布」，坏译文直接上了网站
            if is_severe(structural_diff(text, out)):
                raise SevereTranslation(f'{label}: {structural_diff(text, out)[:120]}')
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out


def body_of(slug: str) -> str:
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    t = t.split('\n---\n', 1)[1].strip() if t.startswith('---\n') else t.strip()
    # 扉页排版 span：拆掉外壳只留字，<i> 改成星号（否则「E<span sc>pistle</span>」一个词三个占位符）
    for _ in range(2):
        t = re.sub(r'<span class="(?:sc|ls)">([^<>]*)</span>', r'\1', t)
    t = re.sub(r'<i>([^<>]*)</i>', r'*\1*', t)
    # 页顶「In this section」目录是英文页按英文小标题生成的；中文页由 publish_jenkyn_zh 按译好的小标题重生成
    return re.sub(r'<nav class="jk-ctoc">.*?</nav>\n*', '', t, flags=re.S).strip()


def units_of(slug: str):
    out = []
    for block in body_of(slug).split('\n\n'):
        b = block.strip()
        if b:
            out.append(('keep' if is_keep_block(b) else 'text', b))
    return out


def load_meta() -> dict:
    return json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}


def stamp_meta(slug: str, called: bool) -> None:
    meta = load_meta()
    if slug in meta and not called:
        return
    meta[slug] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                                text=True, check=True).stdout.strip()
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n',
                    encoding='utf-8')


# 每篇首次出现要括注原名的音译专名（2026-10-19 用户：古今人名、地名、定译名一律括注）。
# 键 = 英文源里的正则（旁注常写缩写 Aug. / Bern.），值 = (括注里写什么, 中文写法元组)。
# 中文写法带后缀，免得括号插进专名中间。译文里已有原名 → 不动；找不到中文写法 → 只告警，不改正文。
ANNOTATE = {
    r'\bAug(?:ustine|ust|\.)': ('Augustine', ('奥古斯丁',)),
    r'\bBern(?:ard|\.)': ('Bernard', ('伯尔纳', '贝尔纳')),
    r'\bChrysost': ('Chrysostom', ('屈梭多模',)),
    r'\bSeneca\b|\bSen\.': ('Seneca', ('塞涅卡',)),
    r'\bPlutarch': ('Plutarch', ('普鲁塔克',)),
    r'\bPlato\b': ('Plato', ('柏拉图',)),
    r'\bAristotle\b|\bArist\.': ('Aristotle', ('亚里士多德',)),
    r'\bCicero\b|\bTully\b': ('Cicero', ('西塞罗',)),
    r'\bTertull': ('Tertullian', ('德尔图良', '特土良')),
    r'\bCyprian': ('Cyprian', ('居普良', '西普里安')),
    r'\bAmbrose\b|\bAmbros\.': ('Ambrose', ('安波罗修',)),
    r'\bHierom|\bJerom': ('Jerome', ('哲罗姆', '耶柔米')),
    r'\bGregor': ('Gregory', ('格列高利',)),
    r'\bBasil\b': ('Basil', ('巴西尔',)),
    r'\bNazian': ('Nazianzen', ('拿先斯的格列高利', '拿先斯')),
    r'\bAeschyl': ('Aeschylus', ('埃斯库罗斯',)),
    r'\bHomer\b': ('Homer', ('荷马',)),
    r'\bCalvin\b': ('Calvin', ('加尔文',)),
    r'\bLuther\b': ('Luther', ('路德',)),
    r'\bEpiph': ('Epiphanius', ('伊皮法纽', '爱比法尼', '埃皮法尼乌斯')),
    r'\bKempis\b': ('Thomas à Kempis', ('肯培斯', '坎普滕的托马斯')),
}


def annotate_terms(zh: str, en: str):
    """每篇首次出现的音译专名后补「（原名）」。幂等：插入点后已是「（」就跳过。返回 (正文, 未落实)。"""
    missing = []
    for pat, (term, forms) in ANNOTATE.items():
        if not re.search(pat, en):
            continue
        if term in zh or re.search(r'（[^（）]*(?:' + pat + r')[^（）]*）', zh):   # 已括注（含缩写 Aug.）
            continue
        hits = [(zh.find(f), f) for f in forms if f in zh]
        if not hits:
            missing.append(term)
            continue
        i, f = min(hits)
        j = i + len(f)
        if zh[j:j + 1] == '（':
            continue
        zh = zh[:j] + f'（{term}）' + zh[j:]
    return zh, missing


def run_section(slug: str, resume: bool, dry: bool, jobs: int, publish: bool) -> None:
    units = units_of(slug)
    todo = [b for k, b in units if k == 'text']
    keys = {tf.md5key(KEY_NS + mask(b)[0]) for b in todo}
    hit = sum(1 for k in keys if (CACHE / f'{k}.txt').exists())
    print(f'[{slug}] 共 {len(units)} 块，需翻译 {len(todo)} 段，已缓存 {hit}，'
          f'待调用 {len(keys) - hit}，约 {sum(len(b) for b in todo):,} 字符', flush=True)
    if dry:
        return 0
    idx = [i for i, (k, _) in enumerate(units) if k == 'text']

    def work(j):
        i = idx[j]
        masked, tags = mask(units[i][1])
        return i, unmask(translate_one(masked, resume, f'{slug}#{j + 1}'), tags)

    done = {}
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        for n, (i, zh) in enumerate(ex.map(work, range(len(idx))), 1):
            done[i] = zh
            if n % 10 == 0:
                print(f'  [{slug}] {n}/{len(idx)} 段', flush=True)
    body = '\n\n'.join(done.get(i, b) for i, (_, b) in enumerate(units))
    body, missing = annotate_terms(body, body_of(slug))
    if missing:
        print(f'    [names] {slug}: 英文源里有 {missing}，译文里没有原名、也找不到已知中文写法，未自动补', flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{slug}.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum(1 for k in keys if (CACHE / f'{k}.txt').exists())
    stamp_meta(slug, called=after > hit or not resume)
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(slug)
    return 1


def autopublish(slug: str) -> None:
    """译完一篇立刻发布 + commit + push（翻完自动收尾，不等人提醒）。
    只 add / commit 詹金这几条路径，不碰工作区别的改动；失败只告警，不中断翻译。"""
    pub = ROOT / 'scripts' / 'publish_taylor_zh.py'
    if not pub.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['taylor/titus', 'taylor_raw/titus/zh_chapters', 'taylor_raw/titus/zh_cache',
                 'taylor_raw/titus/zh_meta.json', 'taylor_raw/titus/en_meta.json',
                 '_data/compare_sources.yml', '_data/commentaries.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(taylor): 提多书注释中译 · {slug}（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',
                            # 只提交自己这几条路径：不带路径的 commit 会把别的会话暂存的文件一起带走
                            '--', *paths],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT,
                                capture_output=True, text=True, timeout=300)
            print('    [autopublish] 已提交' + ('并推送' if ps.returncode == 0
                  else f'，推送失败 {ps.stderr[:160]}'), flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


def all_slugs():
    import publish_taylor_en as P
    return [p['slug'] for p in P.build_pages()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--jobs', type=int, default=1)   # 只准 1 路，多路须用户特别指示
    ap.add_argument('--no-publish', action='store_true')
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    slugs = all_slugs() if a.all else a.section
    if not slugs:
        ap.error('--section 或 --all')
    severe = []
    for s in slugs:
        if a.resume and not a.dry_run and (OUT_DIR / f'{s}.md').exists():
            units = units_of(s)
            # 缓存都在、且都过得了结构闸（或已人工认可）才整篇跳过；只看「在不在」会把坏缓存永远留住
            acc = accepted_keys()

            def ok(b):
                f = CACHE / f'{tf.md5key(KEY_NS + b)}.txt'
                return f.exists() and (tf.md5key(KEY_NS + b) in acc
                                       or not structural_diff(b, f.read_text(encoding='utf-8')))
            if all(ok(mask(b)[0]) for k, b in units if k == 'text'):
                continue
        try:
            run_section(s, a.resume, a.dry_run, a.jobs, not a.no_publish)
        except SevereTranslation as e:
            severe.append(str(e))
            print(f'⛔ [{s}] 有段落重试后仍不合格，本篇不写出、不发布：{e}', flush=True)
        except RuntimeError as e:
            if 'session limit' in str(e).lower() or 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)          # 用量汇总由 claude_usage 的 atexit 打印
            raise
    if severe:
        print('\n⛔ 以下段落未通过，所在篇未发布：\n  ' + '\n  '.join(severe), flush=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
