#!/usr/bin/env python3
"""translate_johnstone.py —— 约翰斯通《腓立比书讲义》英文版 → 中文 raw。

Robert Johnstone, *Lectures Exegetical and Practical on the Epistle of Paul to
the Philippians* (Edinburgh, 1875)。

源取**已发布的英文页** johnstone/philippians/*.md，不取 johnstone_raw/.../en_chapters/：
后者是 repair 之前的中间产物，影像判读的收尾表（manual_fixes_final.tsv）落在
repair 之后，raw 里还留着那些残字。

CLI 调用统一走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 CLI_TRIM_FLAGS（不发工具定义、MCP、CLAUDE.md）。不要在这里自己拼
subprocess 调 claude。

输入  johnstone/philippians/{preface,introduction,1..30,translation,notes-1..4,polycarp}.md
缓存  johnstone_raw/philippians/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  johnstone_raw/philippians/zh_chapters/<sec>.md ← 翻完 chmod 444
时刻  johnstone_raw/philippians/zh_meta.json         ← 每篇真正调过模型那次的时刻

原样保留、不进模型的东西一律换成占位符 ⟦N⟧，译完再换回：
  <sup class="jh-fn" …>…</sup>      脚注号（整个元素）
  <p class="jh-note" …><a …>N</a> … </p>   脚注段的头尾标签
  <span class="jh-verse">、<br>、<span class="jh-dropcap">X</span> 等一切标签
占位符的个数与先后是硬校验：少一个、多一个、顺序乱了都判失败重译。

用法（项目根目录）：
    python3 -u scripts/translate_johnstone.py --dry-run --all
    python3 -u scripts/translate_johnstone.py --section preface --resume
    python3 -u scripts/translate_johnstone.py --range 1-5 --resume
    python3 -u scripts/translate_johnstone.py --all --resume
"""
import argparse
import json
import unicodedata
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402  复用 CLI/缓存/泄漏判据

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'johnstone' / 'philippians'
RAW = ROOT / 'johnstone_raw' / 'philippians'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
# 每篇**实际译完**的时刻。发布页面的 date 从这里按篇查，不取发布那一刻
# （一次发布 N 篇会写出 N 个相同时间戳）；也不用文件 mtime（重出产物、
# sed -i 都会把它抹平）。只在真正调过模型的那次写入。
META = RAW / 'zh_meta.json'
KEY_NS = 'JOHNSTONE_PHIL::'

FRONT = ['preface', 'introduction']
LECTURES = [str(i) for i in range(1, 31)]
BACK = ['translation', 'notes-1', 'notes-2', 'notes-3', 'notes-4', 'polycarp']
ALL = FRONT + LECTURES + BACK

SYSTEM = (
    "你是一位精通希腊文新约与改革宗解经传统的中文译者，正在翻译罗伯特·约翰斯通"
    "（Robert Johnstone）《腓立比书讲义：释经与实践》（1875 年，爱丁堡）。\n"
    "此书是苏格兰联合长老会牧者在讲台上逐段讲解腓立比书的讲章：每讲先引一段经文，"
    "再解释字义、梳理保罗的思路，然后转入劝勉与应用，语气是牧者对会众说话"
    "（常称「my brethren」「dear friends」）。书末另有作者自己的修订译文、"
    "逐章的希腊文注释，以及坡旅甲《致腓立比人书》的英译。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气。"
    "不可译成佶屈聱牙的欧化长句，也不可冲淡成白话通俗读物；"
    "讲台上的呼告语（我的弟兄们、亲爱的朋友们）照原样保留。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表脚注号或排版标签，**必须原样逐个保留**，"
    "个数、先后都与原文一致，放在中文里对应的位置（脚注号紧跟它所注的词或标点）\n"
    "3. 星号 `*` 是斜体标记，逐一保留，开合各一个，数量与位置都要与原文对应。"
    "斜体在此书里多半是作者在逐字讲解的那句经文，或他要强调的词\n"
    "4. **他引用钦定本（Authorized Version）经文时，一律照抄和合本**；"
    "但凡他说「more exactly」「literally」「rather」后给出的是他自己的直译，"
    "那就按他的英文字面译，不要换成和合本——两者的出入正是他要讲的东西。"
    "书末《修订译文》一篇整篇都是他自己的译文，也按字面译，不抄和合本\n"
    "5. 引号：英文的 ‘…’ 译作「…」，嵌在里面的 “…” 译作『…』\n"
    "6. `i. e.`→`即`，`e. g.`→`例如`，`&c.`→`……`（不作「等等」），"
    "`viz.`→`即`，`cf.`/`compare`→`参`，`ver.`/`vers.`→`第 N 节`\n"
    "7. 希腊文、拉丁文、德文一律保留原文，其后用圆括号附中文译义，"
    "如 πολιτεύεσθε（要行事为人，直译「尽你们公民的本分」）；"
    "整句拉丁引文保留原文，括注中文大意。希腊文**逐字照抄**，一个字母、一个"
    "重音符号都不许改（不要把钝音符 ὰ 改成锐音符 ά，不要用形近的拉丁字母代替希腊字母）；"
    "作者用英文拼法写的人名、词（Euodia、presbyter），照英文保留，不要自行换成希腊文\n"
    "8. 圣经书卷名、人名、地名一律用和合本标准译名：Paul→保罗，"
    "Timotheus/Timothy→提摩太，Epaphroditus→以巴弗提，Euodia/Euodias→友阿爹，"
    "Syntyche→循都基，Clement→革利免，Lydia→吕底亚，Silas→西拉，"
    "Philippi→腓立比，Macedonia→马其顿，Thessalonica→帖撒罗尼迦，"
    "Cæsar→该撒，Prætorium→御营\n"
    "8a. **凡音译出来的专名（人名、地名、民族与教派名），每篇首次出现时都要括注英文原名**，"
    "不分古今、不论中文是否早有定译："
    "莱特富特（Lightfoot）、迈耶（Meyer）、加尔文（Calvin）、路德（Luther）、"
    "坡旅甲（Polycarp）、西塞罗（Cicero）、布鲁图（Brutus）、尼禄（Nero）、"
    "甘吉提河（Gangites）、日内瓦湖（Geneva）、胡格诺派（Huguenot）。"
    "同一篇里第二次以后不再重复括注。"
    "只有第 8 条所说、和合本里本来就有的圣经人名地名（保罗、腓立比、马其顿）不括注\n"
    "9. 罗马数字章号一律转成阿拉伯数字，格式为「书卷名 章:节」："
    "Rom. viii. 28 → 罗马书 8:28；2 Cor. xii. 9 → 哥林多后书 12:9；"
    "chap. i. 21 → 第 1 章 21 节\n"
    "10. **不得把任何英文词原样留在中文句子里**。唯一的例外是作者正在讨论"
    "那个英文词本身（如钦定本的某个译词 *conversation*），此时保留原词、"
    "用 *斜体* 标出、随后括注中文义\n"
    "11. 术语务必精确、互不撞词：Authorized Version→钦定本　"
    "Revised Version→修订本　rendering→译法　original→原文　"
    "aorist→不定过去时　participle→分词　genitive→属格　dative→与格　"
    "article→冠词　construction→结构　reading（异文）→读法　"
    "MSS.→抄本　uncial→安色尔字体抄本\n"
    "12. 原文若有未清的 OCR 残字或不完整的引号，照上下文通顺处理，"
    "不要在译文里留英文残词，也不要另加说明"
)

# 每篇首次出现要括注原名的音译专名。值 = 已知中文写法（能自动补；元组＝几种
# 写法都可能出现，补在本篇最先出现的那一处），None = 只检测、不自动补（不知道
# 模型会写成什么字，猜着补等于乱改正文）。
# 2026-10-19 用户定：古代人物、地名、加尔文路德这类定译名也一律括注——「谁知道
# 你说的是谁，音译又不准确」。只有和合本里本来就有的圣经人名地名不注。
# 写法带上后面的「河」「山」「派」「广场」，免得括号插进专名中间。
# 只管这一本书，不去统一全站别的书（见 translate_alexander_isaiah.py 的说明）。
ANNOTATE = {
    'Lightfoot': '莱特富特',
    'Ellicott': '埃利科特',
    'Alford': '阿尔福德',
    'Meyer': '迈耶',
    'De Wette': '德维特',
    'Winer': '威纳',
    'Jelf': '耶尔夫',
    'Trench': '特伦奇',
    'Bengel': '本格尔',
    'Beza': '伯撒',
    'Grotius': '格劳秀斯',
    'Rosenmüller': '罗森米勒',
    'Wieseler': None,
    'Howson': None,
    'Conybeare': None,
    'Van Hengel': None,
    'Rilliet': None,
    'Hackett': None,
    'Tischendorf': None,
    'Lachmann': None,
    'Storr': None,
    'Baur': None,
    'Schwegler': None,
    'Zumpt': None,
    'Eadie': None,
    'Brown': None,
    # ── 古今人物（多为中文已有定译、模型照旧规则没括注的）──
    'Polycarp': '坡旅甲',
    'Ignatius': '依纳爵',
    'Luther': '路德',
    'Calvin': '加尔文',
    'Chrysostom': '屈梭多模',
    'Zuingli': '慈运理',
    'Eusebius': '优西比乌',
    'Valens': '瓦伦斯',
    'Zosimus': '佐西末',
    'Nero': '尼禄',
    'Augustus': ('亚古士督', '奥古斯都'),
    'Trajan': '图拉真',
    'Hadrian': '哈德良',
    'Brutus': '布鲁图',
    'Cassius': '卡西乌斯',
    'Mark Antony': '马克·安东尼',
    'Octavianus Cæsar': '屋大维·该撒',
    'Agricola': '阿格里科拉',
    'Cicero': '西塞罗',
    'Seneca': '塞涅卡',
    'Tacitus': '塔西佗',
    'Socrates': '苏格拉底',
    'Plato': '柏拉图',
    'Homer': '荷马',
    'Herodotus': '希罗多德',
    'Sophocles': '索福克勒斯',
    'Philo': '斐洛',
    'Josephus': '约瑟夫',
    'Diognetus': '《*致丢格那妥书*》',
    'Phidippides': '斐迪庇第斯',
    # ── 地名、民族、教派、赛会 ──
    'Gangites': '甘吉提河',
    'Archipelago': '多岛海',
    'Athos': '阿陀斯山',
    'Troy': '特洛伊',
    'Marathon': '马拉松',
    'Eleusis': '厄琉息斯',
    'Isthmian': ('伊斯米亚', '地峡'),
    'Olympic': '奥林匹亚',
    'Palatine Hill': '巴拉丁山',
    'Piedmontese': '皮埃蒙特',
    'Waldenses': '韦尔多派',
    'Huguenot': '胡格诺派',
    'Vilvorde': '维尔福德',
    'Geneva': '日内瓦湖',
    'Rhone': '罗讷河',
    'Arve': '阿尔沃河',
    'Crimea': '克里米亚',
    'Madagascar': '马达加斯加',
    'Rajpootana': '拉杰普塔纳',
    'Kingston': '金斯顿',
    'Brighton': '布莱顿',
    'Aberdeen': '亚伯丁',
    'Edinburgh': '爱丁堡',
    'Grassmarket': '草市广场',
    'Bothwell Bridge': '博斯韦尔桥',
    'Galashiels': '加拉希尔斯',
    'Falkirk': '福尔柯克',
    'Biggar': '比格尔',
}

# ── 占位符 ────────────────────────────────────────────────────────────────
# 脚注号（正文的上标、脚注段开头的回跳号）整个元素一个占位；其余标签各一个
# 占位。模型看到的只有 ⟦N⟧。
RE_SUP = re.compile(r'<sup class="jh-fn"[^>]*>.*?</sup>|<a class="jh-back"[^>]*>.*?</a>')
RE_TAG = re.compile(r'<[^<>]{1,300}>')
RE_PH = re.compile(r'⟦(\d+)⟧')
RE_ANY = re.compile(RE_SUP.pattern + '|' + RE_TAG.pattern)


def mask(text: str):
    tags = []

    def put(m):
        tags.append(m.group(0))
        return f'⟦{len(tags)}⟧'
    # 一趟扫完，编号跟着出现顺序走（先扫脚注号再扫标签会编出 ⟦2⟧⟦1⟧⟦3⟧）
    return RE_ANY.sub(put, text), tags


def unmask(text: str, tags):
    return RE_PH.sub(lambda m: tags[int(m.group(1)) - 1]
                     if 0 < int(m.group(1)) <= len(tags) else m.group(0), text)


def is_keep_block(b: str) -> bool:
    """整块只有标签、没有要译的文字 → 原样保留，不进模型。

    这类块送进模型会得到「您似乎没有附上需要翻译的段落」之类的对话式回复，
    直接写进正文（曼顿那条线踩过）。
    """
    return not re.search(r'[A-Za-zΑ-ωἀ-ῼ]', RE_TAG.sub('', b))


CHATTY_RE = re.compile(
    r'(您似乎|你似乎|请把原文|请提供|没有附上|未提供|无法翻译|'
    r'as an ai|i (?:cannot|can\'t|don\'t see)|please provide)', re.I)

# 漏译的整词：光溜溜落在中文句子里的英文词。斜体内（作者在讨论这个词本身）、
# 紧跟括注（原名对照）、整句英文引文都不算。
STRAY_EN = re.compile(r'(?<![（(A-Za-zæœÆŒ])[A-Za-zæœÆŒ][A-Za-zæœÆŒ\'’-]{2,}(?![*）)A-Za-zæœÆŒ])')


def stray_english(zh: str):
    out = []
    for m in STRAY_EN.finditer(zh):
        s, e = m.start(), m.end()
        if zh.count('*', 0, s) % 2 == 1:
            continue
        if re.search(r'[A-Za-z]\s*$', zh[:s]) or re.match(r'\s*[A-Za-z]', zh[e:]):
            continue
        out.append(m.group(0))
    return out


GREEK = r'\u0370-\u03ff\u1f00-\u1fff'
RE_GREEK_TOK = re.compile(rf'[{GREEK}\u0300-\u036f]+')
RE_MIXED = re.compile(rf'[{GREEK}]+[A-Za-z]+|[A-Za-z]+[{GREEK}]+')
# 人工逐条核过、确认无误却过不了硬校验的译文（例：模型照规则把作者正在讨论的
# 英文词标了斜体，星号数因而多出一对）。列在这里，--resume 时不再当坏缓存重译。
ACCEPTED = RAW / 'zh_accepted.txt'


def accepted_keys():
    if not ACCEPTED.exists():
        return set()
    return {ln.split()[0] for ln in ACCEPTED.read_text(encoding='utf-8').splitlines()
            if ln.strip() and not ln.startswith('#')}


def tidy(zh: str) -> str:
    """译文落盘前的统一：人名括注一律用圆括号（模型时而写〔Lightfoot〕／［Green］）。"""
    return re.sub(r'[〔［]([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .\'’-]*)[〕］]', r'（\1）', zh)


def structural_diff(en: str, zh: str) -> str:
    """返回结构性差异说明；空字符串表示通过。只查可机验的硬结构。"""
    problems = []
    # 希腊文必须照原文逐字抄：模型会把个别字母换成形近的拉丁字母（ἐκοπίASA、
    # ταῦTα，全书 22 处），会把钝音符改成锐音符（ἀλλὰ→ἀλλά），还会把作者
    # 写成英文拼法的人名自己「还原」成希腊文（Euodia→Εὐοδία）。2026-10-16 查出。
    mixed = RE_MIXED.findall(zh)
    if mixed:
        problems.append('希腊文混入拉丁字母 ' + '、'.join(mixed[:4]))
    nfc = lambda s: unicodedata.normalize('NFC', s)   # ώ 有 U+03CE / U+1F7D 两种编码
    src = set(RE_GREEK_TOK.findall(nfc(en)))
    extra = [w for w in RE_GREEK_TOK.findall(nfc(zh)) if len(w) > 1 and w not in src]
    if extra:
        problems.append('原文没有的希腊词 ' + '、'.join(extra[:4]))
    if en.count('*') != zh.count('*'):
        problems.append(f'斜体 * 数量不符 {en.count("*")} → {zh.count("*")}')
    pe, pz = RE_PH.findall(en), RE_PH.findall(zh)
    if pe != pz:
        problems.append(f'占位符不符 {pe} → {pz}')
    stray = stray_english(zh)
    if stray:
        problems.append('漏译的英文词 ' + '、'.join(sorted(set(stray))[:5]))
    if CHATTY_RE.search(zh):
        problems.append('模型在对话而非翻译')
    leak = tf.output_leak(zh)
    if leak:
        problems.append(leak)
    if re.search(r'[A-Za-z]{4}', en) and not re.search(r'[一-鿿]', zh):
        problems.append('译文无汉字')
    return '；'.join(problems)


def translate_one(text: str, resume: bool, label: str = '') -> str:
    """带缓存 + 结构校验的单段翻译。text 已经过 mask。key = 段落 md5。

    校验不过就重译一次（把问题写进 prompt）。仍不过则保留译文但记账到
    zh_translate_issues.log——不静默吞掉，也不因一段卡死整篇。
    缓存命中的旧译文同样过校验，坏译文会自动重译。
    """
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if key in accepted_keys() or not structural_diff(text, cached):
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}',
              flush=True)

    base = ("把下面这段约翰斯通《腓立比书讲义》的英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
            "只输出译文。\n\n")
    out = tidy(re.sub(r'<<<[^>]*>>>', '',
                      tf.call_claude(base + text, timeout=600, label=label)).strip())

    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n"
               "重译下面这段。**必须逐一保留** `*` 斜体标记（开合各一个）与 ⟦N⟧ 占位符；"
               "希腊文一个字母、一个重音都不许改，照原文逐字抄"
               "（个数与先后都要对上）；**不得把任何英文词原样留在中文句子里**——"
               "除非那个词正是作者在讨论的对象（此时用 *斜体* 标出并括注中文义）。"
               "只输出译文。\n\n")
        out2 = tidy(re.sub(r'<<<[^>]*>>>', '',
                           tf.call_claude(fix + text, timeout=600,
                                          label=label + '·retry')).strip())
        if not structural_diff(text, out2):
            out = out2
        else:
            out = out2 or out
            BAD_LOG.parent.mkdir(parents=True, exist_ok=True)
            with BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {structural_diff(text, out)}\n'
                         f'  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')

    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out


def annotate_terms(zh: str, en: str):
    """每篇首次出现的音译专名后补「（原名）」。返回 (正文, 未落实的名字)。

    原名已在译文里 → 不动；表里有中文写法且找得到 → 首次出现处插入；
    其余 → 记进 missing 告警，不猜、不改正文。插入点后已是「（」就跳过（幂等）。
    """
    missing = []
    for term, zh_form in ANNOTATE.items():
        if not re.search(r'\b' + re.escape(term) + r'\b', en):
            continue
        if re.search(re.escape(term), zh):
            continue
        forms = (zh_form,) if isinstance(zh_form, str) else (zh_form or ())
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


def body_of(sec: str) -> str:
    t = (SRC / f'{sec}.md').read_text(encoding='utf-8')
    if t.startswith('---\n'):
        t = t.split('\n---\n', 1)[1]
    return t.strip()


def front_matter(sec: str) -> dict:
    t = (SRC / f'{sec}.md').read_text(encoding='utf-8')
    fm = {}
    if t.startswith('---\n'):
        for ln in t.split('\n---\n', 1)[0].splitlines()[1:]:
            k, _, v = ln.partition(':')
            fm[k.strip()] = v.strip().strip('"')
    return fm


# 书末的印刷所落款（MURRAY AND GIBB … STATIONERY OFFICE）不译。
IMPRINT = re.compile(r'MURRAY AND GIBB|^THE END\.$')


def units_of(sec: str):
    """正文 → [(kind, block, sep)]。kind='keep' 原样；'text' 送模型。

    脚注区 `<div class="jh-notes">` 是一个块里一行一条脚注（单换行分隔），
    整块送进去就是几十条脚注一次译，占位符一多模型必乱——按行拆开，
    每条脚注各自一个单元，拼回时用单换行（sep）。
    """
    out = []
    for block in body_of(sec).split('\n\n'):
        b = block.strip()
        if not b:
            continue
        if b.startswith('<div class="jh-notes">'):
            lines = b.split('\n')
            for i, ln in enumerate(lines):
                sep = '\n' if i < len(lines) - 1 else '\n\n'
                out.append(('keep' if is_keep_block(ln) else 'text', ln, sep))
            continue
        kind = 'keep' if is_keep_block(b) or IMPRINT.search(RE_TAG.sub('', b)) else 'text'
        out.append((kind, b, '\n\n'))
    return out


def translate_block(b: str, resume: bool, label: str) -> str:
    masked, tags = mask(b)
    return unmask(translate_one(masked, resume, label), tags)


def load_meta() -> dict:
    return json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}


def stamp_meta(sec: str, called: bool) -> None:
    """记下这一篇译完的时刻。全走缓存（called=False）时不覆盖已有值。"""
    meta = load_meta()
    if sec in meta and not called:
        return
    meta[sec] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                               text=True, check=True).stdout.strip()
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1,
                               sort_keys=True) + '\n', encoding='utf-8')


def run_section(sec: str, resume: bool, dry: bool, publish: bool = True) -> None:
    if not (SRC / f'{sec}.md').exists():
        sys.exit(f'找不到 {SRC / sec}.md')
    units = units_of(sec)
    todo = [b for k, b, _ in units if k == 'text']
    keys = {tf.md5key(KEY_NS + mask(b)[0]) for b in todo}
    hit = sum(1 for k in keys if (CACHE / f'{k}.txt').exists())
    print(f'[{sec}] 共 {len(units)} 块，需翻译 {len(todo)} 段，已缓存 {hit}，'
          f'待调用 {len(keys) - hit}，约 {sum(len(b) for b in todo):,} 字符', flush=True)
    if dry:
        return

    # 标题也译：发布端要用（前言/导论/第 N 讲 · 标题）
    fm = front_matter(sec)
    title_zh = translate_one(fm.get('title', sec), resume, f'{sec}#title')

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{sec}.md'
    if dst.exists():                      # 产物受 chmod 444 保护，重跑前解锁
        os.chmod(dst, 0o644)
    out, n = [], 0
    for kind, b, sep in units:
        if kind == 'keep':
            out.append(b + sep)
            continue
        n += 1
        out.append(translate_block(b, resume, f'{sec}#{n}') + sep)
        if n % 10 == 0:
            print(f'  [{sec}] {n}/{len(todo)} 段', flush=True)

    body, missing = annotate_terms(''.join(out).strip(), body_of(sec))
    if missing:
        print(f'    [names] {sec}: 英文源里有 {missing}，译文里既没有原名、'
              f'表里也没有已知中文写法，未自动补——请人工过一眼', flush=True)
    dst.write_text(f'<!-- title: {title_zh} -->\n\n' + body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum(1 for k in keys if (CACHE / f'{k}.txt').exists())
    stamp_meta(sec, called=after > hit or not resume)
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(sec)


def autopublish(sec: str) -> None:
    """译完一篇立刻发布 + commit + push。

    别攒到最后：全书译完以小时计，中途撞额度 / 被 kill 都可能发生，攒着不发
    等于把已译好的成果一直悬在未发布状态。发布失败只告警不中断——翻译进度在
    缓存里，发布随时可补跑。git 只加约翰斯通这几条路径，不碰工作区别的改动。
    """
    try:
        r = subprocess.run([sys.executable, 'scripts/publish_johnstone_zh.py'],
                           cwd=ROOT, capture_output=True, text=True, timeout=600)
        print('    ' + r.stdout.strip(), flush=True)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        subprocess.run(['git', 'add', 'johnstone/philippians',
                        'johnstone_raw/philippians/zh_chapters',
                        'johnstone_raw/philippians/zh_cache',
                        'johnstone_raw/philippians/zh_meta.json'],
                       cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(johnstone): 腓立比书讲章中译 · {sec}（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>',
                            # 只提交自己这几条路径：不带路径的 commit 会把别的会话
                            # 暂存的文件一起带走（2026-10-16 赫奇森整批被带进珀金斯的提交）
                            '--', 'johnstone/philippians', 'johnstone_raw/philippians/zh_chapters', 'johnstone_raw/philippians/zh_cache', 'johnstone_raw/philippians/zh_meta.json'],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'],
                                cwd=ROOT, capture_output=True, text=True, timeout=300)
            print('    [autopublish] 已提交' + ('并推送' if ps.returncode == 0
                  else f'，推送失败 {ps.stderr[:160]}'), flush=True)
        else:
            print(f'    [autopublish] 无改动可提交 {c.stdout.strip()[:80]}', flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', help='preface / introduction / 1..30 / translation / notes-1..4 / polycarp')
    ap.add_argument('--range', help='讲次区间，如 1-5')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true', help='命中缓存则不重调模型')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-publish', action='store_true', help='只译不发布')
    a = ap.parse_args()

    if a.section:
        targets = [a.section]
    elif a.range:
        lo, hi = (int(x) for x in a.range.split('-'))
        targets = [str(i) for i in range(lo, hi + 1)]
    elif a.all:
        targets = ALL
    else:
        ap.error('要么 --section，要么 --range，要么 --all')

    tf.CACHE_DIR = CACHE
    tf.SYSTEM = SYSTEM
    for sec in targets:
        try:
            run_section(sec, a.resume, a.dry_run, publish=not (a.no_publish or a.dry_run))
        except tf.SessionLimitError as e:
            # 额度用尽时重试只会空转计费。逐段缓存已落盘，恢复后 --resume 续跑。
            print(f'\n✗ 会话额度用尽，于 [{sec}] 中止：{str(e)[:160]}\n'
                  f'  已译段落都在 {CACHE}，额度恢复后加 --resume 续跑。', flush=True)
            sys.exit(42)


if __name__ == '__main__':
    main()
