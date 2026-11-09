#!/usr/bin/env python3
"""translate_alexander_acts.py —— 约瑟·亚历山大《使徒行传释义》(纽约 1857) 英文版 → 中文 raw。

照搬 translate_alexander_matthew.py（同一作者、同一套页面结构，类名 am- → aa-），只换书名、路径、提示词里的书卷体例。

骨架与全部质检闸照搬 translate_candlish.py（← attersoll ← taylor ← jenkyn；含 2026-11-03 起的 <译文> 标签、
白名单字符、重复起稿放行重引经文、残留标签等判据）。CLI 调用统一走 translate_filibi.call_claude →
claude_usage.call_cli（自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt）。

源取**已发布的英文页** alexander/acts/<N>.md（斜体、经文头、脚注都已补回）。本书与坎德利什不同的三处：
  - 斜体在页面里是 <em>…</em>，送模型前转成 *…*（发布时 publish_alexander_acts_zh 转回）；
  - 每节前的经文头（<p class="aa-head">）**不送模型**，由程序填入和合本该节（assets/cuv.json），免得凭记忆走样；
  - 章末脚注 <div class="aa-notes"> 拆成一条一块送译。

输入  alexander/acts/<N>.md（preface / introduction / 1…28；扉页不译）
缓存  alexander_raw/acts/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  alexander_raw/acts/zh_chapters/<N>.md  ← 翻完 chmod 444
时刻  alexander_raw/acts/zh_meta.json        ← 每篇真正调过模型那次的时刻

用法（项目根目录）：
    python3 -u scripts/translate_alexander_acts.py --dry-run --section 3
    python3 -u scripts/translate_alexander_acts.py --section 3 --resume     # 单路；多路须用户特别指示
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
SRC = ROOT / 'alexander' / 'acts'
RAW = ROOT / 'alexander_raw' / 'acts'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
ITALIC_LOG = RAW / 'zh_italic_notes.log'   # 斜体程序修/对数不同的记录，人工抽查用
META = RAW / 'zh_meta.json'
KEY_NS = 'ALEXANDER_ACTS::'

SYSTEM = (
    "你是一位精通希腊文与改革宗解经传统的中文译者，正在翻译约瑟·亚历山大"
    "（Joseph Addison Alexander, 1809–1860，普林斯顿神学院教授）《使徒行传释义》"
    "（The Acts of the Apostles Explained，纽约 1857 年，两卷）。\n"
    "此书体例：每章先给一段分析性的解题；再逐节先印钦定本经文（这部分程序另填和合本，不在你的输入里），"
    "随即辨析希腊文的词义、语法、时态、异文，比较威克里夫以来各英文译本的译法，并引平行经文。"
    "文风是十九世纪普林斯顿的学术散文，句子长、层次多、用词精确而克制。"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气。不要译成佶屈聱牙的欧化长句，"
    "也不要冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（注号链接、锚点等），**必须原样逐个保留**，个数、先后都与原文一致，"
    "放在中文里对应的位置（注号紧跟在它所注的那个词或那句话后面）\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。**斜体标出的是他正在讲解的经文字词，或他自己给出的译法**"
    "（*Repent*, literally *change your mind* …）。中文里对应的词照样用 `*` 包起来，一处对一处，"
    "不要把相邻两处斜体并成一处，不要自己增添斜体，不要只包一个字或标点。"
    "斜体里是钦定本经文字词的，用和合本该处的对应措辞；是他自己的直译、另译（literally / more exactly / "
    "i. e. / or 之后），按他的英文字面译出，不要换成和合本——那正是他要辨析的东西\n"
    "4. 原文引用别处经文时（引号里的整句），照抄和合本；只给出处、没有引经文的，只译出处，不要自己补经文\n"
    "5. 经文出处照录原写法的数字：`(3:2)` → （3:2）；`see below, on 21:25` → 见下文 21:25 注；"
    "`see above, on 1:20` → 见上文 1:20 注；`v. 2` / `vs. 5, 6` → 第 2 节 / 第 5、6 节；"
    "带书卷名的转和合本书名：Luke 1:15 → 路加福音 1:15；Rom. 8:35 → 罗马书 8:35；"
    "Isai. → 以赛亚书；Mal. → 玛拉基书；Ps. → 诗篇；Gen. → 创世记；Ex. → 出埃及记；Matt. → 马太福音；不带书卷名的是使徒行传本书，照录章节数字。"
    "脚注里原书的旧写法「章, 节. 节」（`Luke 1, 15. 35. 2, 25.`）一律改成「章:节, 节」：路加福音 1:15, 35；2:25\n"
    "6. 希腊文、希伯来文、拉丁文一律保留原文，**逐字照抄，一个字母、一个重音符号都不许改**，"
    "其后用圆括号附中文译义，如 μετανοεῖτε（你们要悔改）；整句拉丁引文保留原文，括注中文大意\n"
    "7. `&c.` → ……（不作「等等」）；`i. e.` → 即；`e. g.` → 例如；`viz.` → 即；`cf.` → 参\n"
    "8. 圣经书卷名、人名、地名用和合本标准译名：John the Baptist→施洗的约翰，Elias/Elijah→以利亚，"
    "Esaias→以赛亚，Pharisees→法利赛人，Sadducees→撒都该人，Jordan→约旦河，Judea→犹太，Galilee→加利利，"
    "Jerusalem→耶路撒冷，Abraham→亚伯拉罕，Messiah→弥赛亚，the Holy Ghost/Spirit→圣灵，Cesarea→该撒利亚，Cesar→该撒，Festus→非斯都，Felix→腓力斯，Agrippa→亚基帕，Antioch→安提阿，Barnabas→巴拿巴，Stephen→司提反，Cornelius→哥尼流，Timotheus→提摩太，Gallio→迦流，Lysias→吕西亚，Sanhedrim/Council→公会，Pentecost→五旬节，Gentiles→外邦人，the Twelve→十二使徒；和合本使徒行传里出现的人名地名一律照和合本写法\n"
    "9. 译本与抄本名：Wiclif→威克里夫译本，Tyndale→丁道尔译本，Cranmer→克兰麦译本，Geneva→日内瓦译本，"
    "Rheims/Rhemish→兰斯译本，the Authorized/English Version→钦定本，Vulgate→武加大译本，Septuagint→七十士译本，"
    "Peshito→别西大译本，Codex Vaticanus/the Vatican (manuscript)→梵蒂冈抄本，uncial→安色尔字体（抄本）\n"
    "10. **凡音译出来的专名（人名、地名、教派名、书名），每篇首次出现都要括注英文原名**，不论中文是否早有定译："
    "约瑟夫（Josephus）、拉赫曼（Lachmann）、蒂申多夫（Tischendorf）、罗宾逊（Robinson）、本格尔（Bengel）、"
    "爱色尼派（Essenes）、奥古斯丁（Augustine）、加尔文（Calvin）、路德（Luther）。"
    "同一篇第二次以后不再括注。只有和合本里本来就有的圣经人名地名不括注\n"
    "11. 术语精确、互不撞词：repentance→悔改　baptism→洗礼　baptize→施洗　kingdom of heaven→天国　"
    "righteousness→义　fulfil→成就　prophecy→预言　type→预表　Messiahship→弥赛亚身份　apostle/apostolical→使徒/使徒的　"
    "the historian→这位史家（指路加）　the Evangelist→福音书作者　theocracy→神治　Sanhedrim→公会　immersion→浸水　"
    "Apostolical Church History→使徒教会史　"
    "Arminian→阿民念派　from everlasting→从亘古（「亘」不可写作「亡」）\n"
    "12. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "13. **不得把任何英文词原样留在中文句子里**（斜体里他讲解的英文译法要译出来，不可照留英文）"
)

# 注号链接 <sup class="aa-fnref"><a>*</a></sup> 与章末回链 <a class="aa-fnback">*</a> 整个一个占位：
# 里面的 * † 是注号不是斜体，露给模型会被当成斜体标记
RE_GAP = re.compile(r'<sup class="aa-fnref">.*?</sup>|<a class="aa-fnback"[^>]*>.*?</a>')
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
    r'(您似乎|你似乎|请把原文|请提供|没有附上|未提供|无法翻译|'
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

    base = ("把下面这段亚历山大《使徒行传释义》的十九世纪英文译成简体中文。"
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


_CUVD = None


def cuv_verse(ch: int, v: int) -> str:
    global _CUVD
    if _CUVD is None:
        _CUVD = json.loads((ROOT / 'assets' / 'cuv.json').read_text(encoding='utf-8'))
    return _CUVD['44'][str(ch)][str(v)]


RE_HEAD = re.compile(r'^<p class="aa-head"><span class="aa-vn">([^<]*)</span>(.*)</p>$', re.S)


def head_zh(ch: int, block: str) -> str:
    """经文头换成和合本：节号标签 `3.` / `3, 4.` / `5–10.`；英文页把几个经文头拼成一段时（`… 4. And …`），
    中文同样第二节起在节文前写「4.」。"""
    m = RE_HEAD.match(block)
    lab = m.group(1)
    nums = [int(x) for x in re.findall(r'\d+', lab)]
    vv = list(range(nums[0], nums[1] + 1)) if '–' in lab and len(nums) == 2 else nums
    parts = [cuv_verse(ch, vv[0])] + [f'{v}. {cuv_verse(ch, v)}' for v in vv[1:]]
    return f'<p class="aa-head"><span class="aa-vn">{lab}</span> ' + ' '.join(parts) + '</p>'


def body_of(slug: str) -> str:
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    t = t.split('\n---\n', 1)[1].strip() if t.startswith('---\n') else t.strip()
    t = re.sub(r'<em>([^<>]*)</em>', r'*\1*', t)            # 斜体转星号，模型按星号对位
    # 章末脚注一条一块（外壳 div 单独成块原样保留）
    t = re.sub(r'(<div class="aa-notes">)\n', r'\1\n\n', t)
    t = re.sub(r'</p>\n(?=<p id="acts-\d+-fn)', '</p>\n\n', t)
    t = re.sub(r'</p>\n</div>', '</p>\n\n</div>', t)
    return t


def units_of(slug: str):
    out = []
    ch = int(slug) if slug.isdigit() else 0
    for block in body_of(slug).split('\n\n'):
        b = block.strip()
        if not b:
            continue
        if RE_HEAD.match(b):
            out.append(('keep', head_zh(ch, b)))
        else:
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
    r'\bAug(?:ustine|\.)': ('Augustine', ('奥古斯丁',)),
    r'\bJerome\b': ('Jerome', ('哲罗姆', '耶柔米')),
    r'\bJosephus\b': ('Josephus', ('约瑟夫', '约瑟夫斯')),
    r'\bCalvin\b': ('Calvin', ('加尔文',)),
    r'\bLuther\b': ('Luther', ('路德',)),
    r'\bBengel\b': ('Bengel', ('本格尔', '本革尔')),
    r'\bLachmann\b': ('Lachmann', ('拉赫曼',)),
    r'\bTischendorf\b': ('Tischendorf', ('蒂申多夫',)),
    r'\bEssenes\b': ('Essenes', ('爱色尼派', '艾赛尼派')),
    r'\bHorace\b': ('Horace', ('贺拉斯',)),
    r'\bCicero\b': ('Cicero', ('西塞罗',)),
    r'\bOvid\b': ('Ovid', ('奥维德',)),
    r'\bErasmus\b': ('Erasmus', ('伊拉斯谟',)),
    r'\bHomer\b': ('Homer', ('荷马',)),
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
    pub = ROOT / 'scripts' / 'publish_alexander_acts_zh.py'
    if not pub.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['alexander/acts', 'alexander_raw/acts/zh_chapters', 'alexander_raw/acts/zh_cache',
                 'alexander_raw/acts/zh_meta.json', 'alexander_raw/acts/en_meta.json',
                 'alexander_raw/acts/zh_translate_issues.log', '_data/compare_sources.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(alexander): 使徒行传释义中译 · {slug}（自动发布）\n\n'
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
    return ['preface', 'introduction'] + [str(n) for n in range(1, 29)]


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
