#!/usr/bin/env python3
"""translate_leighton.py —— 雷登《彼得前书实用注释》(1693/94) 英文版 → 中文 raw。

骨架照搬 translate_hutcheson.py（CLI 调用、缓存、结构闸、自动发布都一样），换书目、提示词，
另加两样：缺字记号整块当占位符（不交模型），音译专名每篇首次括注原名的程序兜底。

源取**已发布的英文页** leighton/1peter/<slug>.md（看图判读的补字已落进去），不取 en_chapters/。
缺字记号 <span class="lt-gap">▪</span> 整个是一个占位符：模型看不见 ▪ • ◊，译文里原样还回。

输入  leighton/1peter/<slug>.md（slug 见 leighton_raw/1peter/pages_en.json）
缓存  leighton_raw/1peter/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  leighton_raw/1peter/zh_chapters/<slug>.md ← 翻完 chmod 444
时刻  leighton_raw/1peter/zh_meta.json         ← 每篇真正调过模型那次的时刻

用法（项目根目录）：
    python3 -u scripts/translate_leighton.py --dry-run --all
    python3 -u scripts/translate_leighton.py --section 1-1 --resume
    python3 -u scripts/translate_leighton.py --all --resume          # 单路；多路须用户特别指示
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
SRC = ROOT / 'leighton' / '1peter'
RAW = ROOT / 'leighton_raw' / '1peter'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
KEY_NS = 'LEIGHTON_1PETER::'

SYSTEM = (
    "你是一位精通改革宗神学与早期近代英语的中文译者，正在翻译苏格兰牧者罗伯特·雷登"
    "（Robert Leighton, 1611–1684）《彼得前书实用注释》（A Practical Commentary upon the First Epistle "
    "General of St. Peter，卷一 1693 年约克、卷二 1694 年伦敦）。这是他在纽巴特尔牧会时讲解彼得前书的讲稿，"
    "灵修式释经：把经文的意思与敬虔的操练紧密连在一起，文笔典雅、温厚、多警句。\n"
    "原文是十七世纪英文：拼法古旧（Iesus=Jesus，vnto=unto，vs=us，then 常作 than，'tis=it is，"
    "doth/hath，-eth/-est，onely=only，soule=soul，sinne=sin，beleeve=believe）；u/v、i/j 混用；"
    "长句多分号。要按意思读懂后译成现代中文。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气。保留作者的温厚与警句的力度，"
    "但不要译成佶屈聱牙的欧化长句，也不要冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（页码、经文框、节号标签、旁注外壳、原书缺字记号等），"
    "**必须原样逐个保留**，个数、先后都与原文一致，放在中文里对应的位置。"
    "有的占位符是原书**缺字处**，紧挨着残缺的字母（如 ⟦4⟧o、ab⟦5⟧sement）："
    "占位符照留，残字母不要输出，按上下文把句子译通\n"
    "3. 星号 `*` 是斜体标记，逐一保留，开合各一个\n"
    "4. **凡引用圣经经文，一律照抄和合本**；他用 KJV 或自己的译法，与和合本措辞不同时仍以和合本为准；"
    "但凡他说 that is / i. e. 后给出的是自己的解释，按他的英文译；"
    "**原文只给出处、没有引经文的，只译出处，不要自己补出经文**\n"
    "5. 经文框里被讲解的经文（单独一段的彼得前书经文）照抄和合本该节；"
    "节号标签 Verse. 5. / verse 1. / Verses 8, 9. → 第 5 节 / 第 1 节 / 第 8–9 节\n"
    "6. 方括号 [ ] 里的词是编者推补的（原书此处缺损），照样译出，**方括号原样保留**\n"
    "7. `&c.` → ……（不作「等等」）；`v.` / `ver.` / `verse` → 第 N 节；`Chap.` → 第 N 章；"
    "`i. e.` / `that is` → 即\n"
    "8. 拉丁文、希腊文、希伯来文一律保留原文，其后用圆括号附中文译义，如 *Gratia gratis data*（白白赐下的恩典）；"
    "希腊文、希伯来文逐字照抄，一个字母、一个重音符号都不许改\n"
    "9. 圣经书卷名、人名、地名用和合本标准译名：Peter→彼得，Pontus→本都，Galatia→加拉太，"
    "Cappadocia→加帕多家，Asia→亚西亚，Bithynia→庇推尼，Babylon→巴比伦，Silvanus→西拉，Marcus→马可，"
    "Sarah/Sara→撒拉，Noah/Noe→挪亚，Abraham→亚伯拉罕，David→大卫，Moses→摩西，Paul→保罗\n"
    "10. 经文出处一律转成「书卷名 章:节」：Rom. 8.28. → 罗马书 8:28；1 Cor. 3.6. → 哥林多前书 3:6；"
    "Psal. 32.1. / Psa. 18.1. → 诗篇 32:1 / 诗篇 18:1；Prov. 18.10. → 箴言 18:10；Heb. 10.22. → 希伯来书 10:22；"
    "Iob → 约伯记；Ioh. → 约翰福音；Isa. → 以赛亚书；Mat. → 马太福音；"
    "Matth. 5.23, 24. → 马太福音 5:23-24\n"
    "11. **凡音译出来的专名（人名、地名、民族与教派名），每篇首次出现都要括注英文原名**，"
    "不分古今、不论中文是否早有定译：奥古斯丁（Augustine）、伯尔纳（Bernard）、屈梭多模（Chrysostom）、"
    "塞涅卡（Seneca）、普鲁塔克（Plutarch）、加尔文（Calvin）、路德（Luther）、冉森派（Jansenists）。"
    "缩写形式照样括注全名或原写法，如 Aug. → 奥古斯丁（Aug.）。同一篇里第二次以后不再重复括注。"
    "只有和合本里本来就有的圣经人名地名（彼得、本都、巴比伦）不括注\n"
    "12. 术语精确、互不撞词：justification→称义　sanctification→成圣　regeneration→重生　"
    "election/the Elect→拣选/选民　grace→恩典　faith→信心　hope→盼望　the Gospel→福音　"
    "the Law→律法　Mediator→中保　the Word→道　Ministers→传道人　ordinances→圣礼与敬拜的规条（视上下文）　"
    "Sacraments→圣礼　carnal→属肉体的　Saints→圣徒　holiness→圣洁　obedience→顺服　"
    "patience→忍耐　inheritance→基业　sprinkling→洒\n"
    "13. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」，全书前后一致\n"
    "14. **不得把任何英文词原样留在中文句子里**；印本里偶有的排印错字，按上下文读通后译出，"
    "不要留残词，也不要另加说明"
)

RE_GAP = re.compile(r'<span class="lt-gap"[^>]*>.*?</span>')
RE_TAG = re.compile(r'<[^<>]{1,400}>')
RE_ANY = re.compile(RE_GAP.pattern + '|' + RE_TAG.pattern)
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
STRAY_EN = re.compile(r'(?<![（(A-Za-zæœÆŒ])[A-Za-zæœÆŒ][A-Za-zæœÆŒ\'’-]{2,}(?![*）)A-Za-zæœÆŒ])')
GREEK = r'Ͱ-Ͽἀ-῿'
RE_GREEK_TOK = re.compile(rf'[{GREEK}̀-ͯ]+')
RE_MIXED = re.compile(rf'[{GREEK}]+[A-Za-z]+|[A-Za-z]+[{GREEK}]+')
LATIN_OK = re.compile(r'[A-Za-z]')


def stray_english(zh: str, en: str):
    """光溜溜落在中文句子里的英文词。斜体内、括注里、原文里本就有的拉丁词都不算。"""
    en_words = {w.lower() for w in re.findall(r'[A-Za-z]{3,}', en)}
    out = []
    for m in STRAY_EN.finditer(zh):
        s, e = m.start(), m.end()
        if zh.count('*', 0, s) % 2 == 1:
            continue
        if re.search(r'[A-Za-z]\s*$', zh[:s]) or re.match(r'\s*[A-Za-z]', zh[e:]):
            continue
        out.append(m.group(0))
    # 拉丁整句引文：连续多个英文词出现，多半是保留的拉丁原文，不算漏译
    return [w for w in out if w.lower() not in en_words or len(w) < 4]


def structural_diff(en: str, zh: str) -> str:
    problems = []
    if RE_MIXED.findall(zh):
        problems.append('希腊文混入拉丁字母 ' + '、'.join(RE_MIXED.findall(zh)[:4]))
    nfc = lambda s: unicodedata.normalize('NFC', s)
    src = set(RE_GREEK_TOK.findall(nfc(en)))
    extra = [w for w in RE_GREEK_TOK.findall(nfc(zh)) if len(w) > 1 and w not in src]
    if extra:
        problems.append('原文没有的希腊词 ' + '、'.join(extra[:4]))
    if en.count('*') != zh.count('*'):
        problems.append(f'斜体 * 数量不符 {en.count("*")} → {zh.count("*")}')
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
    if '→' in zh and '→' not in en:
        problems.append('起稿残留（→）')
    sents = [x for x in re.split(r'[。！？；]', zh) if len(x) >= 20]
    dup = [x for x in set(sents) if sents.count(x) > 1]
    if dup:
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


def tidy(zh: str) -> str:
    zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
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
    """只剩「斜体 * 数量不符」算轻微（多是模型把相邻斜体并成一段）；其余都算严重。"""
    return bool(diff) and any(not p.startswith('斜体 * 数量不符') for p in diff.split('；'))


def translate_one(text: str, resume: bool, label: str = '') -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached) or key in accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}', flush=True)

    base = ("把下面这段雷登《彼得前书实用注释》的十七世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；只输出译文。\n\n")
    out = tidy(tf.call_claude(base + text, timeout=900, label=label))
    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** `*` 斜体标记"
               "（开合各一个）与 ⟦N⟧ 占位符（个数与先后都要对上）；希腊文逐字照抄；"
               "**不得把任何英文词原样留在中文句子里**。只输出译文。\n\n")
        # 重试两次，取第一个合格的；都不合格就取「只剩斜体问题」的那一版
        for n in (1, 2):
            out2 = tidy(tf.call_claude(fix + text, timeout=900, label=f'{label}·retry{n}'))
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
    return t.split('\n---\n', 1)[1].strip() if t.startswith('---\n') else t.strip()


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
# 键 = 英文源里的正则（雷登常写缩写 Aug. / Bern.），值 = (括注里写什么, 中文写法元组)。
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
    只 add / commit 雷登这几条路径，不碰工作区别的改动；失败只告警，不中断翻译。"""
    pub = ROOT / 'scripts' / 'publish_leighton_zh.py'
    if not pub.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['leighton/1peter', 'leighton_raw/1peter/zh_chapters', 'leighton_raw/1peter/zh_cache',
                 'leighton_raw/1peter/zh_meta.json', '_data/leighton_1peter.json', '_data/leighton_1peter_zh.json',
                 '_data/compare_sources.yml', '_data/commentaries.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(leighton): 彼得前书实用注释中译 · {slug}（自动发布）\n\n'
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
    return [p['slug'] for p in json.loads(PAGES.read_text(encoding='utf-8'))]


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
