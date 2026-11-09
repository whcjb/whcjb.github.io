#!/usr/bin/env python3
"""translate_petter.py —— 乔治·佩特《马可福音注释》(伦敦 1661) 英文版 → 中文 raw。

骨架照搬 translate_rollock.py（同一套质检闸：模型自语 / 残留标签 / 重复起稿放行重引经文 / 希腊词尾还原 /
拉丁音标词 / 斜体内漏译 / 垃圾字符 / 已知错字；译文装进 <译文> 标签只取标签内）。
CLI 调用统一走 translate_filibi.call_claude → claude_usage.call_cli，自动带 CLI_TRIM_FLAGS
（--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt 替换默认提示词）。不要自己拼 subprocess。

英文版一讲一页，翻译也按讲：slug = 讲首节（'1-1'、'1-4b'）或卷首篇名（'preface'）。
源取**已发布的英文页** petter/mark/<slug>.md：
  - 缺字记号 <span class="pt-gap">…</span> 整个一个占位符；
  - 页边纲目标签 <span class="pt-mark">Observ. 2</span> 先按 MARK_ZH 程序译成中文，再整个一个占位符；
  - 经文出处标签 <span class="pt-ref">Mark 1. 1.</span> 程序转成「马可福音 1:1」，整个一个占位符；
  - 编者推补 <span class="pt-conj">[grant me]</span> 与页边旁注 pt-margin：外壳两个占位符，里面的字照译（推补保留方括号）。

输入  petter/mark/<slug>.md
缓存  petter_raw/mark/zh_cache/<md5>.txt     ← 必须保留，重跑成本极高
输出  petter_raw/mark/zh_chapters/<slug>.md  ← 翻完 chmod 444
时刻  petter_raw/mark/zh_meta.json           ← {"<slug>": 译完时刻}

用法（项目根目录）：
    python3 -u scripts/translate_petter.py --dry-run --chapter 1
    python3 -u scripts/translate_petter.py --chapter 1 --resume     # 单路；多路须用户特别指示
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402  复用 CLI/缓存/泄漏判据

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'petter' / 'mark'
RAW = ROOT / 'petter_raw' / 'mark'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
ITALIC_LOG = RAW / 'zh_italic_notes.log'
META = RAW / 'zh_meta.json'
KEY_NS = 'PETTER_MARK::'

SYSTEM = (
    "你是一位精通改革宗神学与早期近代英语的中文译者，正在翻译英国清教徒牧师乔治·佩特（George Petter，?–1654，"
    "萨塞克斯郡布雷德 Brede 教区牧师）的《马可福音注释》（A Learned, Pious, and Practical Commentary upon the Gospel "
    "according to St. Mark，伦敦 1661，身后由其弟出版）。这是他 1618 年起在本堂逐主日讲解马可福音的讲章：每讲先引经文，"
    "逐语解说，再分条列出观察（Observ.）、教义（Doctr.）、理由（Reas.）、应用（Use），并设问答（Quest./Answ.）、"
    "驳异议（Object.）；口吻是讲台上的劝勉，常直接对会众说话。\n"
    "原文是 1620 年代的英文（1661 年排印）：拼法古旧（-nesse=-ness，onely=only，then 常作 than，doth/hath，-eth/-est，"
    "Austin=奥古斯丁）；所有格常不加撇号；长句多分号与冒号。要按意思读懂后译成现代中文。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；条目编号与层次照原文；"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（原书页码、经文框、页边纲目标签、页边旁注外壳、编者推补外壳、首字下沉框、原书缺字记号等），"
    "**必须原样逐个保留**，个数、先后都与原文一致，放在中文里对应的位置。"
    "一对占位符夹着几个字的（⟦5⟧June 7. 1618.⟦6⟧ 是页边旁注；⟦7⟧[grant me]⟦8⟧ 是编者推补），"
    "把中间的字译出、两个占位符照留、**不要外加括号**；推补的方括号 [ ] 原样保留，把方括号连同里面的中文放在两个占位符之间。"
    "页边旁注里的讲道日期译成「1618 年 6 月 7 日」这样的格式（月份：Jan./Janu.=1 Febr.=2 March=3 April=4 May=5 June=6 "
    "July=7 Aug.=8 Sept.=9 Octob.=10 Nov.=11 Dec.=12）。"
    "有的占位符是原书**缺字处**：占位符照留，按上下文把句子译通\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。原文斜体的部分（人名、书卷名、拉丁词、引文、强调语），"
    "中文里对应的词照样用 `*` 包起来，一处对一处：不要把相邻两处斜体并成一处，不要自己增添斜体，"
    "不要只包一个「第」字、数字或标点\n"
    "4. **凡引用圣经经文，一律照抄和合本**；他用 KJV 或自己的译法，与和合本措辞不同时仍以和合本为准；"
    "但凡他说 that is / i. e. / q. d. 后给出的是自己的解释、意译或复述，按他的英文译；"
    "**原文只给出处、没有引经文的，只译出处，不要自己补出经文**\n"
    "5. 每讲开头经文框里被讲解的马可福音经文照抄和合本该节；"
    "正文里逐语解说时引的经文片段（*The beginning of the Gospel*] 之类，以 ] 收尾）照和合本相应字句，保留 ] 符号\n"
    "6. 纲目用语全书一译：Observ./Obser. → 观察，Doctr./Doct. → 教义，Use/Ʋse → 应用，Reas./Reason → 理由，"
    "Quest. → 问，Answ. → 答，Object. → 异议，Caution → 提醒，Note → 注意，Rule → 规则；"
    "带编号的照写编号（*Observ.* 2. → *观察* 2.；*Use* 1. → *应用* 1.）\n"
    "7. `&c.` → ……（不作「等等」）；`v.` / `ver.` / `verse` → 第 N 节；`Chap.` → 第 N 章；"
    "`i. e.` / `that is` → 即 / 就是；`viz.` → 就是\n"
    "8. 拉丁文、希腊文、希伯来文一律保留原文，其后用圆括号附中文译义，如 *Tanquam Breviator Ejus*（如同他的节略者）；"
    "希腊文、希伯来文逐字照抄，一个字母、一个重音符号都不许改\n"
    "9. 圣经书卷名、人名、地名用和合本标准译名：Jesus→耶稣，John the Baptist→施洗的约翰，Esaias/Isaiah→以赛亚，"
    "Elias→以利亚，Pharisees→法利赛人，Sadduces→撒都该人，Scribes→文士，Galilee→加利利，Jordan→约旦河，"
    "Capernaum→迦百农，Nazareth→拿撒勒，Judea→犹太，Jerusalem→耶路撒冷，Simon→西门，Andrew→安得烈，"
    "James→雅各，Zebedee→西庇太，Peter→彼得，Moses→摩西，Herod→希律\n"
    "10. 经文出处一律转成「书卷名 章:节」：Rom. 8. 28. → 罗马书 8:28；1 *Cor.* 2. 2. → 哥林多前书 2:2；"
    "*Joh.* 17. 3. → 约翰福音 17:3；*Phil.* 3. 8. → 腓立比书 3:8；*Matth.* 3. 1. → 马太福音 3:1；"
    "*Luk.* → 路加福音；*Esay* → 以赛亚书；*Psal.* → 诗篇；*Mal.* → 玛拉基书；书卷名两侧的斜体星号去掉\n"
    "11. **凡音译出来的专名（人名、地名、民族与教派名、著作名），每篇首次出现都要括注英文原名**，"
    "不分古今、不论中文是否早有定译：奥古斯丁（Austin）、哲罗姆（Hierom）、屈梭多模（Chrysostom）、"
    "伯撒（Beza）、加尔文（Calvin）、耶稣会士（Jesuits）；原名取原文实际的拼法。同一篇里第二次以后不再重复括注。"
    "只有和合本里本来就有的圣经人名地名不括注\n"
    "12. 术语精确、互不撞词：justification→称义　sanctification→成圣　regeneration→重生　"
    "election/the Elect→拣选/选民　effectual calling→有效的呼召　calling（职分）→呼召/职分　grace→恩典　faith→信心　"
    "repentance→悔改　remission of sins→赦罪　the Gospel→福音　the Law→律法　Mediator→中保　the Word→道　"
    "the Ministry→圣职/传道职分　Ministers→传道人　Sacraments→圣礼　Saints→圣徒　holiness→圣洁　"
    "godliness→敬虔　Papists→天主教徒　the Pope→教皇　Popish→天主教的　the kingdom of heaven/of God→天国/神的国　"
    "baptism→洗礼　the Devil→魔鬼　Christ's natures→基督的神性/人性\n"
    "13. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」，全书前后一致；称神一律用「神」，不用「上帝」\n"
    "13b. **注意中文词的褒贬色彩**：原文是正面的神学说法，不得用带贬义的中文词（据为己有、霸占、攫取、侵吞……）。"
    "appropriate / appropriating faith 指信心把基督与应许领受过来归给自己——译「领受归己」；"
    "只有原文是僭取、侵占的负面义（arrogate、usurp）才译「据为己有」\n"
    "14. **不得把任何英文词原样留在中文句子里**；印本里偶有的排印错字，按上下文读通后译出，"
    "不要留残词，也不要另加说明"
)

# 页边纲目标签：程序直译，整个一个占位符（全书 5,778 个，交给模型只会多出占位符负担与译法漂移）
MARK_ZH = [(r'Observ|Obser', '观察'), (r'Doctr?|Doct', '教义'), (r'Ʋse|Use', '应用'), (r'Reasons?|Reas|Rat', '理由'),
           (r'Quest', '问'), (r'Answ|Ans', '答'), (r'Object', '异议'), (r'Caution', '提醒'), (r'Point', '要点'),
           (r'Note', '注意'), (r'Rule', '规则')]


def mark_zh(m):
    s = m.group(2)
    for pat, zh in MARK_ZH:
        if re.match(rf'(?:{pat})\b', s):
            num = re.search(r'\d+', s)
            return f'{m.group(1)}{zh}{(" " + num.group(0)) if num else ""}</span>'
    return m.group(0)


# 经文出处标签 Mark 1. 1. / Mark 1. 4, 5. → 马可福音 1:1 / 1:4–5
def ref_zh(m):
    nums = re.findall(r'\d+', m.group(2))
    if m.group(2).strip().startswith('Mark') and len(nums) >= 2:
        v = nums[1] + (f'–{nums[-1]}' if len(nums) > 2 else '')
        return f'{m.group(1)}马可福音 {nums[0]}:{v}</span>'
    return m.group(0)


RE_GAP = re.compile(r'<span class="pt-(?:gap|mark|ref)"[^>]*>.*?</span>')
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
    if re.search(r'【上下文】|<上下文>|【要翻译的这段】|（本段）', zh):      # 附给短段的上下文被吐进译文
        problems.append('上下文泄漏进译文')
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


SHORT_CTX = 300   # 短于此的段落附上前后文（只供理解、不译）


def ctx_block(ctx: str) -> str:
    """孤零零一句话的段落（分条「5. Lastly, …」、一句应用）模型看不到上下文，就在输出里自语
    （第 1 章 1-4#12 / 1-4b#16 / 1-6#19：Context… irrelevant… instructions，三次同类）。
    附上前后段的英文供理解，明说不译；缓存键只取要译的那段，附不附上下文不影响已有缓存。"""
    if not ctx:
        return ''
    return ("【上下文】下面是这段前后的原文，只帮助理解这段在说什么，**不要翻译、不要输出、不要评论**：\n"
            f"<上下文>\n{ctx}\n</上下文>\n\n【要翻译的这段】\n")


def translate_one(text: str, resume: bool, label: str = '', ctx: str = '') -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached) or key in accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}', flush=True)

    base = ("把下面这段佩特《马可福音注释》的十七世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    raw = tf.call_claude(base + ctx_block(ctx) + text, timeout=900, label=label)
    out = fix_italics(restore_greek(tidy(take_tagged(raw)), text), text, label)
    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        # 第一遍偶发吐几十 token 的废话（<reasoning_effort>、Placeholder →、只剩一个字；第 1 章 3/700 次，
        # 同段重放 15 次复现不出）——原始输出存下来备查，重译照常
        with BAD_LOG.open('a', encoding='utf-8') as fh:
            fh.write(f'[{label}·first] {diff[:120]}\n  RAW: {raw[:400]!r}\n')
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留**"
               " ⟦N⟧ 占位符（个数与先后都要对上）；希腊文逐字照抄；"
               "**不得把任何英文词原样留在中文句子里**。把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
        # 重试两次，取第一个合格的；都不合格就取「只剩斜体问题」的那一版
        for n in (1, 2):
            out2 = fix_italics(restore_greek(tidy(take_tagged(tf.call_claude(fix + ctx_block(ctx) + text, timeout=900, label=f'{label}·retry{n}'))), text),
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
    # 首字下沉：字母并回原词，留空框（中文首字由 publish_petter_zh 装回）
    t = re.sub(r'<span class="pt-dropcap">([^<>]*)</span>', r'<span class="pt-dropcap"></span>\1', t)
    # 页边纲目标签、经文出处标签：程序直译后整个当占位符（见 MARK_ZH / ref_zh）
    t = re.sub(r'(<span class="pt-mark">)([^<]*)</span>', mark_zh, t)
    t = re.sub(r'(<span class="pt-ref">)([^<]*)</span>', ref_zh, t)
    return t.strip()


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
        ctx = ''
        if len(re.sub(r'⟦\d+⟧', '', masked)) < SHORT_CTX:
            plain = lambda t: re.sub(r'\s+', ' ', RE_ANY.sub(' ', t)).strip()
            before = plain(units[idx[j - 1]][1])[-500:] if j > 0 else ''
            after = plain(units[idx[j + 1]][1])[:300] if j + 1 < len(idx) else ''
            ctx = '\n'.join(x for x in (('……' + before) if before else '', ('（本段）'), (after + '……') if after else '') if x)
        return i, unmask(translate_one(masked, resume, f'{slug}#{j + 1}', ctx), tags)

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
    pub = ROOT / 'scripts' / 'publish_petter_zh.py'
    if not pub.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['petter/mark', 'petter_raw/mark/zh_chapters', 'petter_raw/mark/zh_cache',
                 'petter_raw/mark/zh_meta.json', 'petter_raw/mark/en_meta.json',
                 '_data/compare_sources.yml', '_data/commentaries.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(petter): 马可福音注释中译 · {slug}（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',
                            # 只提交自己这几条路径：不带路径的 commit 会把别的会话暂存的文件一起带走
                            '--', *paths],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            # Pages 一次构建要 4–5 分钟；每篇（约 3 分钟）都推，新推送会把排队的构建取消，
            # 结果一次都部署不成。所以只在距上次推送满 PUSH_GAP 秒时推，其余留到章末 flush_push()
            if time.time() - last_push_time() >= PUSH_GAP:
                print('    [autopublish] 已提交' + push_now(), flush=True)
            else:
                print('    [autopublish] 已提交（攒着，稍后统一推送）', flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


PUSH_GAP = 900
PUSH_STAMP = ROOT / 'logs' / '.petter_last_push'


def last_push_time() -> float:
    try:
        return float(PUSH_STAMP.read_text())
    except (OSError, ValueError):
        return 0.0


def push_now() -> str:
    ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT,
                        capture_output=True, text=True, timeout=300)
    if ps.returncode == 0:
        PUSH_STAMP.write_text(str(time.time()))
        return '并推送'
    return f'，推送失败 {ps.stderr[:160]}'


def flush_push() -> None:
    """章末/中止前把攒下的提交推上去。"""
    ahead = subprocess.run(['git', 'rev-list', '--count', 'origin/master..master'], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()
    if ahead and ahead != '0':
        print(f'[autopublish] 推送攒下的 {ahead} 个提交' + push_now(), flush=True)


def all_slugs():
    import publish_petter_en as P
    return [p['slug'] for p in P.BOOK.build_pages()]


def chapter_slugs(ch):
    import publish_petter_en as P
    return [p['slug'] for p in P.BOOK.build_pages() if p.get('ch') == ch]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--jobs', type=int, default=1)   # 只准 1 路，多路须用户特别指示
    ap.add_argument('--no-publish', action='store_true')
    ap.add_argument('--chapter', type=int, action='append', default=[])
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    import claude_usage
    claude_usage.STRICT_STOP = True   # 中途异常停止的输出直接重采样（见 claude_usage.call_cli）
    slugs = all_slugs() if a.all else a.section + [x for c in a.chapter for x in chapter_slugs(c)]
    if not slugs:
        ap.error('--section / --chapter 或 --all')
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
                flush_push()
                sys.exit(42)          # 用量汇总由 claude_usage 的 atexit 打印
            raise
    if not a.no_publish and not a.dry_run:
        flush_push()
    if severe:
        print('\n⛔ 以下段落未通过，所在篇未发布：\n  ' + '\n  '.join(severe), flush=True)
        sys.exit(3)


if __name__ == '__main__':
    main()
