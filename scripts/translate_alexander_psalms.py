#!/usr/bin/env python3
"""translate_alexander_psalms.py —— 亚历山大《诗篇注释》英文版 → 中文 raw。

源取**已发布的英文页** alexander/psalms/*.md，不取 alexander_raw/.../en_chapters/：
OCR 残字的判读修正（repair/adjudicate 两条线）落点都在已发布正文上，
raw 里还留着 `fi-uitfol`、`Thd wicked` 这类未清的字（见 adjudicate_alexander_ocr.py
的 SRC）。拿 raw 去翻等于把已经清掉的错字再翻一遍。

CLI 调用统一走 translate_filibi.call_claude → claude_usage.call_cli，
**自动带 CLI_TRIM_FLAGS**（--safe-mode / --strict-mcp-config /
--disallowedTools "*" / --system-prompt）：不发工具定义、MCP、CLAUDE.md、
skills、hooks —— 29,142 → 287 token/次。绝不要在本脚本里自己拼 subprocess
调 claude，那样会把整套上下文又带回去。

输入  alexander/psalms/{preface,1..150}.md      （已发布英文页，含 front matter）
缓存  alexander_raw/psalms/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  alexander_raw/psalms/zh_chapters/<sec>.md ← 翻完 chmod 444

原样保留、不进模型：
  <!-- psalm 1 | 书页 … -->  <!-- PAGE 17 -->        页码与出处标记
  <span class="ax-anchor" …></span>                  节号锚点
  <span class="ax-vnum">7 <span class="ax-veng">(6).</span></span>   节号本身

本卷的命根子是 **斜体**：Alexander 的体例是把自己对希伯来文的译文用斜体
嵌在解说里夹译夹注，原书不另设经文框。`*` 一旦丢了，读者就分不清哪句是经文、
哪句是他的解说。所以 structural_diff 把 `*` 计数当硬指标，不符即重译。

用法（项目根目录）：
    python3 -u scripts/translate_alexander_psalms.py --dry-run --section preface
    python3 -u scripts/translate_alexander_psalms.py --range 1-5 --resume
    python3 -u scripts/translate_alexander_psalms.py --all --resume
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402  复用 CLI/缓存

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander' / 'psalms'
RAW = ROOT / 'alexander_raw' / 'psalms'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
# 每篇**实际译完**的时刻。发布页面的 date 取这里，不取发布那一刻——
# 一次发布把 6 篇的时间戳写成同一分钟，等于没有信息（用户 2026-09-14 指出）。
# 为什么不直接用 zh_chapters/<sec>.md 的 mtime：改提示词、补括注都会重出文件，
# mtime 跟着变；连 zh_cache 的 mtime 也靠不住（一次 `sed -i` 就全抹平了）。
# 所以单独落一份，**只在真正调过模型的那次写入**，之后重出一律沿用。
META = RAW / 'zh_meta.json'

SYSTEM = (
    "你是一位精通希伯来文与改革宗解经传统的中文译者，正在翻译约瑟·亚历山大"
    "（Joseph Addison Alexander, 1809-1860，普林斯顿神学院东方与圣经文学教授）"
    "《诗篇注释》（1850，1864 年修订单卷本）。\n"
    "此书体例：先给每篇一段总论，再逐节给出他自己对希伯来文的译文，"
    "随即接上语法、词义、平行经文的辨析。文风是十九世纪普林斯顿的学术散文，"
    "句子长、层次多、用词精确而克制。译文要沉稳、准确、读得懂，"
    "不可译成佶屈聱牙的欧化长句，也不可冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. **星号 `*` 是全书的命根子**：斜体标出的是亚历山大自己对希伯来原文的"
    "译文（原书不另设经文框，斜体就是经文）。必须逐一保留 `*` 标记，"
    "数量与位置都与原文对应——斜体开合各算一个。切不可多加或漏掉\n"
    "3. 斜体里的经文按他的英文**字面**译，不要直接抄和合本：他的译法常与"
    "和合本不同，而那正是他下文要辨析的东西（如 *(Oh) the blessedness of "
    "the man!* 要译出「（哦）这人的有福！」的惊叹语气与复数形式，"
    "不能换成和合本的「这人便为有福」）。用词的语感向和合本靠，措辞从他\n"
    "4. 圆括号里的补字（如 *of wicked (men)*）是他补出原文所无、中译必需的词，"
    "保留圆括号：*恶人（们）的*\n"
    "5. `*i. e.*`→`*即*`，`i.e.`→`即`，`e. g.`→`例如`，`&c.`→`……`（不作「等等」），"
    "`viz.`→`即`，`cf.`→`参`，`sc.`→`即`\n"
    "6. 保留所有 HTML 标签与 HTML 注释不变，位置对应原文\n"
    "7. 希伯来文、希腊文、拉丁文一律保留原文，其后用圆括号附中文译义，"
    "如 חֶסֶד（慈爱）；整句拉丁引文保留原文，括注中文大意\n"
    "8. 圣经书卷名、人名、地名一律用和合本标准译名：Jehovah→耶和华，"
    "the Lord→主，Messiah→弥赛亚，David→大卫，Zion→锡安，"
    "Psalmist→诗人，Septuagint→七十士译本，Vulgate→武加大译本，"
    "Masoretic→马所拉\n"
    "8a. **凡音译出来的专名，每篇首次出现时都要括注原词**——包括两类：\n"
    "  (一) 近现代学者、释经家、译本编者的姓名："
    "亨斯滕伯格（Hengstenberg）、德维特（De Wette）、埃瓦尔德（Ewald）、"
    "格塞尼乌斯（Gesenius）、胡普费尔德（Hupfeld）、德里慈（Delitzsch）、"
    "罗森米勒（Rosenmüller）、奥尔斯豪森（Olshausen）、维特林加（Vitringa）、"
    "金希（Kimchi）、亚本·以斯拉（Aben Ezra）。\n"
    "  (二) 诗篇题注里的希伯来文术语与乐调名——和合本把它们**意译**了"
    "（Neginoth 作「用丝弦的乐器」、Nehiloth 作「用吹的乐器」），"
    "中文里根本没有这些音译，读者无从查起，所以音译后必须给原词："
    "尼吉纳（Neginoth）、尼希罗（Nehiloth）、玛斯基拉（Maschil）、"
    "米斯托（Michtam）、迦特（Gittith）、亚拉末（Alamoth）、"
    "希加约（Higgaion）、施迦庸（Shiggaion）。\n"
    "  音译只是一串陌生的字，读者对不上是谁、是什么，必须给出原词。"
    "同一篇里第二次以后就不再重复括注。\n"
    "8b. 下面这些**不**括注：圣经人名地名（大卫、亚萨、可拉、耶杜顿）；"
    "和合本已有音译的（细拉 Selah）；中文早有定译、读者一望即知的大名"
    "（路德、加尔文、奥古斯丁、耶柔米、屈梭多模）\n"
    "9. 罗马数字章号一律转成阿拉伯数字，格式为「书卷名 章:节」："
    "Psalm xxvi. 4, 5 → 诗篇 26:4, 5；Isa. xvii. 13 → 以赛亚书 17:13；"
    "Mat. iii. 12 → 马太福音 3:12。`ver. 1` → 「第 1 节」\n"
    "9a. `*The Lord,* Jehovah,` 是全书最常见的一个组合：斜体的 The Lord 是他"
    "自己对四字神名的译法，其后不带斜体的 Jehovah 是他给出的原文名。"
    "译作「*主，*耶和华，」——**不要对调**成「*耶和华，*即主」，"
    "那会把他刻意区分的「译文」与「原名」颠倒过来\n"
    "9b. **不得把任何英文词原样留在中文句子里**。唯一的例外是作者正在讨论"
    "那个英文词本身（如 *rage*、*ashes*），此时保留原词并用 *斜体* 标出、"
    "随后括注中文义\n"
    "10. 语文学术语务必精确、互不撞词：\n"
    "   parallelism→平行体　paraphrase→意译　version→译本　rendering→译法\n"
    "   preterite/past tense→过去时　future→将来时　participle→分词\n"
    "   suffix→词尾　root→字根　radical→词根字母　idiom→惯用语\n"
    "   figure→比喻／修辞　literal→字面　exegesis→解经　expositor→释经者\n"
    "   inscription/title→题注（诗篇篇首的那行）　Selah→细拉\n"
    "   the old dispensation→旧约的时代　covenant→约　\n"
    "11. 「the Happy Man」这类他特意大写的提法要一致地译（「有福之人」），"
    "全篇同一译法，不要一处一样\n"
    "12. 原文若有未清的 OCR 残字或未闭合的引号，照上下文通顺处理，"
    "不要在译文里留英文残词，也不要另加说明"
)

# 整行的 HTML 注释：`<!-- PAGE 17 -->` 常与其后的段落同属一个块（中间没有
# 空行），所以不能只在「整块都是注释」时跳过，还要把块首的注释行剥下来。
COMMENT_LINE = re.compile(r'^\s*<!--.*?-->\s*$')
RULE_LINE = re.compile(r'^(?:-{3,}|\*{3,}|_{3,})$')


def is_keep_block(b: str) -> bool:
    """整块没有实义文字（只有注释／分隔线）→ 原样保留，不进模型。

    这类块送进模型会得到「您似乎没有附上需要翻译的段落」之类的**对话式回复**，
    直接写进正文（曼顿那条线踩过）。
    """
    return all(COMMENT_LINE.match(ln) or RULE_LINE.match(ln.strip())
               for ln in b.split('\n') if ln.strip())

# 节号前缀：锚点 + .ax-vnum（内可嵌 .ax-veng 的英文节号）+ 可能跟一个开斜体的 ` *`
VNUM_PREFIX = re.compile(
    r'^(<span class="ax-anchor" id="[^"]*"></span>'
    r'<span class="ax-vnum">(?:[^<]|<span class="ax-veng">[^<]*</span>)*</span>)'
    r'( \*)?')

# 近现代学者／释经家姓名：每篇首次出现要括注英文原名。
# 音译只是一串陌生的字，中文读者对不上人——用户 2026-09-14 指出（「亨斯腾伯格」
# 通篇没给原名）。SYSTEM 里已经立了规矩，这张表是**兜底闸**：模型漏注时由
# annotate_terms() 按英文源补上，不必为此重跑翻译。
# 表里没有的名字仍由 SYSTEM 的 8a 条管，加进来只是为了能机器复核。
# 路德／加尔文／奥古斯丁这类中文早有定译的大名故意不进表（见 SYSTEM 8b）。
#
# **这张表只管亚历山大这条线**（用户 2026-09-14 定）：站内别的书早先各译各的，
# 同一个 Hengstenberg 有 6 种写法（亨斯滕伯格 44／亨斯登伯 34／亨斯滕贝格 25／
# 亨斯登伯格 22／亨斯坦贝格 2），Gesenius 有 3 种，calvin/genesis 一本里就并存
# 4 种。**不要顺手去扫全站改齐**——那是上百处已发布正文的改动，用户明确说先不动。
# 表里取的是站内最通行的那一种，好让新译的书与主流对得上。
# 查证过：改革宗圈子没有公开的译名规范（麦种、橡树都无公开体例；信望爱的
# 「改革宗神学名词清单」只管术语不管人名）；大陆的权威依据是新华社译名室
# 《世界人名翻译大辞典》，但手头没有电子版，逐条核不了，所以没照它改。
# 中文维基连 Hengstenberg 的条目都没有——这个人在中文里本就没有通行译法。
# 要括注原词的音译专名。值 = 已知的中文写法（能自动补），None = 只检测不自动补
# （不知道模型会译成什么字，猜着补等于在正文里乱改——宁可告警让人过一眼）。
ANNOTATE = {
    # 近现代学者／释经家
    'Hengstenberg': '亨斯滕伯格',
    'De Wette': '德维特',
    'Ewald': '埃瓦尔德',
    'Gesenius': '格塞尼乌斯',
    'Hupfeld': '胡普费尔德',
    'Delitzsch': '德里慈',
    'Rosenmüller': '罗森米勒',
    'Olshausen': '奥尔斯豪森',
    'Vitringa': '维特林加',
    'Kimchi': '金希',
    'Aben Ezra': '亚本·以斯拉',
    # 诗篇题注里的希伯来文术语与乐调名。和合本把它们**意译**了
    # （Neginoth 作「用丝弦的乐器」、Nehiloth 作「用吹的乐器」），中文里
    # 没有这些音译，读者看「尼希罗」三个字无从查起——用户 2026-09-14 指出。
    # Selah 不进表：和合本已有「细拉」，读者认得。
    # Jeduthun／Asaph／Korah 同理，和合本有「耶杜顿／亚萨／可拉」。
    'Neginoth': '尼吉纳',
    'Nehiloth': '尼希罗',
    'Maschil': None,
    'Michtam': None,
    'Gittith': None,
    'Alamoth': None,
    'Higgaion': None,
    'Shiggaion': None,
    'Sheminith': None,
    'Muth-labben': None,
    'Shoshannim': None,
    'Mahalath': None,
}


def annotate_terms(zh: str, en: str):
    """每篇首次出现的音译专名后补「（原词）」。返回 (正文, 未落实的词)。

    三步：原词已在译文里出现过 → 不动（模型自己注了，或整词照搬）；
    表里给了中文写法且找得到 → 在首次出现处插入；
    其余 → 记进 missing 告警，**不猜、不改正文**。
    幂等：插入点后已经是「（」就跳过，重跑不会叠括号。
    """
    missing = []
    for term, zh_form in ANNOTATE.items():
        if not re.search(r'\b' + re.escape(term) + r'\b', en, re.I):
            continue
        if re.search(re.escape(term), zh, re.I):      # 译文里已经有原词
            continue
        if not zh_form or zh_form not in zh:
            missing.append(term)
            continue
        i = zh.find(zh_form)
        j = i + len(zh_form)
        if zh[j:j + 1] == '（':
            continue
        zh = zh[:j] + f'（{term}）' + zh[j:]
    return zh, missing


# 模型没在翻译、而是在跟你说话的迹象。命中即判失败重试。
CHATTY_RE = re.compile(
    r'(您似乎|你似乎|请把原文|请提供|没有附上|未提供|无法翻译|'
    r'as an ai|i (?:cannot|can\'t|don\'t see)|please provide)', re.I)


def structural_diff(en: str, zh: str) -> str:
    """返回结构性差异说明；空字符串表示通过。只查**可机验**的硬结构。"""
    problems = []
    if en.count('*') != zh.count('*'):
        problems.append(f'斜体 * 数量不符 {en.count("*")} → {zh.count("*")}')
    en_c = re.findall(r'<!--.*?-->', en, re.S)
    zh_c = re.findall(r'<!--.*?-->', zh, re.S)
    if en_c != zh_c:
        problems.append(f'HTML 注释不符 {en_c} → {zh_c}')
    if '<span' in zh and '<span' not in en:
        problems.append('译文里凭空多出 <span>（节号锚点不该进模型）')
    stray = stray_english(zh)
    if stray:
        problems.append('漏译的英文词 ' + '、'.join(sorted(set(stray))[:5]))
    if CHATTY_RE.search(zh):
        problems.append('模型在对话而非翻译')
    if re.search(r'[A-Za-z]', en) and not re.search(r'[一-鿿]', zh) and len(en) > 40:
        problems.append('译文无汉字')
    return '；'.join(problems)


# 译文里**漏译的整词**：模型偶尔把一个英文词原样留在中文句子里
# （「推向了 past」「所表白之 confidence 的根据」）。structural_diff 只查星号、
# 锚点、注释，单个词溜得过去——用户 2026-09-14 查出 3 处。
# 判据必须排除两类**正当**的英文：
#   1. 斜体内的：Alexander 在讨论这个英文词本身（*ashes、means,* / *rage*）；
#   2. 紧跟括注的：`尼希罗（Nehiloth）` 这种原词对照。
# 剩下的「光溜溜落在中文句子里的英文常用词」才是漏译。
STRAY_EN = re.compile(r'(?<![（(A-Za-z])[A-Za-z][A-Za-z\'’-]{2,}(?![*）)A-Za-z])')


def stray_english(zh: str):
    """返回译文里疑似漏译的英文词。空列表表示干净。"""
    out = []
    for m in STRAY_EN.finditer(zh):
        s, e = m.start(), m.end()
        # 落在一对 * 之间的不算（Alexander 在讨论这个词本身）
        if zh.count('*', 0, s) % 2 == 1:
            continue
        # 两侧都是英文/标点的（整句英文引文）不算
        if re.search(r'[A-Za-z]\s*$', zh[:s]) or re.match(r'\s*[A-Za-z]', zh[e:]):
            continue
        out.append(m.group(0))
    return out


def translate_one(text: str, resume: bool, label: str = '') -> str:
    """带缓存 + 结构校验的单段翻译。key = 段落 md5。

    校验不过就重译一次（把问题点明写进 prompt）。仍不过则保留译文但记账到
    zh_translate_issues.log —— 不静默吞掉，也不因一段卡死整篇。
    缓存命中的旧译文同样过校验，早先跑出来的坏译文会自动重译。
    """
    key = tf.md5key('ALEX_PSA::' + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached):
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}',
              flush=True)

    base = ("把下面这段亚历山大《诗篇注释》的英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记；"
            "只输出译文。\n\n")
    out = re.sub(r'<<<[^>]*>>>', '',
                 tf.call_claude(base + text, timeout=600, label=label)).strip()

    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n"
               "重译下面这段。**必须逐一保留**原文中的 `*` 斜体标记"
               "（开合各一个，数量与位置都要对上）与 <!-- --> 注释；"
               "**不得把任何英文词原样留在中文句子里**——除非那个词正是"
               "作者在讨论的对象（此时用 *斜体* 标出并括注中文义）。"
               "只输出译文。\n\n")
        out2 = re.sub(r'<<<[^>]*>>>', '',
                      tf.call_claude(fix + text, timeout=600,
                                     label=label + '·retry')).strip()
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


def load_meta() -> dict:
    import json
    if META.exists():
        return json.loads(META.read_text(encoding='utf-8'))
    return {}


def stamp_meta(sec: str, called: bool) -> None:
    """记下这一篇译完的时刻。`called=False`（全走缓存）时不覆盖已有值。"""
    import json
    meta = load_meta()
    if sec in meta and not called:
        return
    now = subprocess_now()
    meta[sec] = now
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1,
                               sort_keys=True) + '\n', encoding='utf-8')


def subprocess_now() -> str:
    import subprocess
    return subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                          text=True, check=True).stdout.strip()


def body_of(sec: str) -> str:
    """已发布英文页 → 去掉 front matter 的正文。"""
    t = (SRC / f'{sec}.md').read_text(encoding='utf-8')
    if t.startswith('---\n'):
        t = t.split('\n---\n', 1)[1]
    return t.strip()


def split_units(raw: str):
    """raw md → [(kind, payload)]。kind='keep' 原样；'text' 需翻译。"""
    units = []
    for block in raw.split('\n\n'):
        b = block.strip()
        if not b:
            continue
        units.append(('keep' if is_keep_block(b) else 'text', b))
    return units


def _split_prefix(b: str):
    """拆出「原样保留的块首」与「送模型的正文」。

    块首两样东西都不进模型：
      1. 整行的 `<!-- PAGE 17 -->`（页码标记，与正文同块）；
      2. 节号锚点 + `.ax-vnum`（脚本注入的标记，模型碰了就乱）。
    节号前缀末尾的 ` *` 是开斜体标记，要**挪进**送模型的那段——否则模型收到的
    文本从半截斜体开始，`*` 计数也成了奇数，校验永远过不去。
    """
    lines = b.split('\n')
    head = []
    while lines and COMMENT_LINE.match(lines[0]):
        head.append(lines.pop(0).strip())
    prefix = ''.join(ln + '\n' for ln in head)
    rest = '\n'.join(lines).lstrip()
    m = VNUM_PREFIX.match(rest)
    if not m:
        return prefix, rest
    star = '*' if m.group(2) else ''
    return prefix + m.group(1) + ' ', star + rest[m.end():].lstrip()


def translate_block(b: str, resume: bool, label: str) -> str:
    prefix, text = _split_prefix(b)
    return prefix + translate_one(text, resume, label)


def run_section(name: str, resume: bool, dry: bool, publish: bool = True) -> None:
    src = SRC / f'{name}.md'
    if not src.exists():
        sys.exit(f'找不到 {src}')
    units = split_units(body_of(name))
    todo = [u for k, u in units if k == 'text']
    hit = sum(1 for t in todo
              if (CACHE / f'{tf.md5key("ALEX_PSA::" + _split_prefix(t)[1])}.txt').exists())
    print(f'[{name}] 共 {len(units)} 块，其中需翻译 {len(todo)} 段，'
          f'已缓存 {hit}，待调用 {len(todo) - hit}', flush=True)
    if dry:
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{name}.md'
    if dst.exists():                      # 翻译产物受 chmod 444 保护，重跑前解锁
        os.chmod(dst, 0o644)

    cached_keys = {tf.md5key('ALEX_PSA::' + _split_prefix(u)[1]) for u in todo}
    before = sum(1 for k in cached_keys if (CACHE / f'{k}.txt').exists())

    out, n = [], 0
    for kind, payload in units:
        if kind == 'keep':
            out.append(payload)
            continue
        n += 1
        out.append(translate_block(payload, resume, label=f'{name}#{n}'))
        if n % 10 == 0:
            print(f'  [{name}] {n}/{len(todo)} 段', flush=True)

    body, missing = annotate_terms('\n\n'.join(out), body_of(name))
    if missing:
        print(f'    [names] {name}: 英文源里有 {missing}，译文里既没有原词、'
              f'表里也没有已知中文写法，未自动补——请人工过一眼', flush=True)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)                  # 强保留
    # 这一趟真调过模型（缓存命中数变多，或本来就没全命中）才更新时间戳
    stamp_meta(name, called=before < len(cached_keys) or not resume)
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish()


def autopublish() -> None:
    """译完一篇立刻发布 + commit + push。

    别攒到最后：150 篇跑下来是以天计的，中途撞额度 / 断电 / 被 kill 都可能
    发生，攒着不发等于把已译好的成果一直悬在未发布状态。
    发布失败只告警不中断——翻译进度在缓存里，发布随时可以补跑。
    """
    import subprocess
    try:
        r = subprocess.run([sys.executable, 'scripts/publish_alexander_psalms_zh.py'],
                           cwd=ROOT, capture_output=True, text=True, timeout=300)
        print(r.stdout.rstrip(), flush=True)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[:200]}', flush=True)
            return
        subprocess.run(['git', 'add', 'alexander/psalms',
                        'alexander_raw/psalms/zh_chapters',
                        'alexander_raw/psalms/zh_cache'],
                       cwd=ROOT, check=False, timeout=60)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            'feat(alexander/psalms): 诗篇注释中译（自动发布）'],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            p = subprocess.run(['git', 'push', '-q', 'origin', 'master'],
                               cwd=ROOT, capture_output=True, text=True, timeout=300)
            print('    [autopublish] 已提交'
                  + ('并推送' if p.returncode == 0 else f'，推送失败 {p.stderr[:120]}'),
                  flush=True)
        else:
            print(f'    [autopublish] 无改动可提交（{c.stdout.strip()[:80]}）', flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', help='preface 或 1..150')
    ap.add_argument('--range', help='篇号区间，如 1-5')
    ap.add_argument('--all', action='store_true', help='序 + 全部 150 篇')
    ap.add_argument('--resume', action='store_true', help='命中缓存则不重调模型')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-publish', action='store_true',
                    help='只译不发布（默认每译完一篇就发布+commit+push）')
    a = ap.parse_args()

    if a.section:
        targets = [a.section]
    elif a.range:
        lo, hi = (int(x) for x in a.range.split('-'))
        targets = [str(i) for i in range(lo, hi + 1)]
    elif a.all:
        targets = ['preface'] + [str(i) for i in range(1, 151)]
    else:
        ap.error('要么 --section，要么 --range，要么 --all')

    tf.CACHE_DIR = CACHE
    tf.SYSTEM = SYSTEM
    CACHE.mkdir(parents=True, exist_ok=True)

    for name in targets:
        try:
            run_section(name, a.resume, a.dry_run,
                        publish=not (a.no_publish or a.dry_run))
        except tf.SessionLimitError as e:
            # 额度用尽时重试毫无意义，还照样计费。逐段缓存已落盘，
            # 额度恢复后 --resume 从缓存续跑即可。退出码 42 = 整批中止信号。
            print(f'\n✗ 会话额度用尽，于 [{name}] 中止：{str(e)[:160]}\n'
                  f'  已翻译的段落都在 {CACHE}，额度恢复后加 --resume 续跑。',
                  flush=True)
            sys.exit(42)


if __name__ == '__main__':
    main()
