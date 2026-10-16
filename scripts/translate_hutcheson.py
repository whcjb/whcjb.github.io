#!/usr/bin/env python3
"""translate_hutcheson.py —— 赫奇森《约翰福音注释》(1657) 英文版 → 中文 raw。

骨架照搬 translate_perkins.py（CLI 调用、缓存、结构闸、自动发布都一样），只换书目与提示词。

源取**已发布的英文页** hutcheson/john/<slug>.md（缺字补字、推补都已落进去），
不取 hutcheson_raw/john/en_chapters/（补字之前的抽取产物）。
编者推补在英文页里是 <span class="hc-conj">[word]</span>：标签进占位符，方括号与里面的词
交模型——词照译、方括号原样保留，中文页上照样标为推补。

输入  hutcheson/john/<slug>.md（slug 见 hutcheson_raw/john/pages_en.json）
缓存  hutcheson_raw/john/zh_cache/<md5>.txt   ← 必须保留，重跑成本极高
输出  hutcheson_raw/john/zh_chapters/<slug>.md ← 翻完 chmod 444
时刻  hutcheson_raw/john/zh_meta.json         ← 每篇真正调过模型那次的时刻

用法（项目根目录）：
    python3 -u scripts/translate_hutcheson.py --dry-run --all
    python3 -u scripts/translate_hutcheson.py --section 1-1 --resume
    python3 -u scripts/translate_hutcheson.py --all --resume [--jobs 3]
夜间守护：scripts/sched_hutcheson_zh.py（每夜 20:00–次日 03:00）
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
SRC = ROOT / 'hutcheson' / 'john'
RAW = ROOT / 'hutcheson_raw' / 'john'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
BAD_LOG = RAW / 'zh_translate_issues.log'
META = RAW / 'zh_meta.json'
PAGES = RAW / 'pages_en.json'
KEY_NS = 'HUTCHESON_JOHN::'

SYSTEM = (
    "你是一位精通改革宗神学与早期近代英语的中文译者，正在翻译苏格兰盟约派牧师乔治·赫奇森"
    "（George Hutcheson, 1615–1674）《约翰福音注释》（An Exposition of the Gospel of Jesus Christ "
    "according to John，1657 年伦敦初版）。\n"
    "原文是 1657 年的英文，带苏格兰用语：拼法古旧（beleeve=believe，then 常作 than，emprove=improve，"
    "onely=only，sonne=son，dayes=days，-nesse=-ness），词尾 -eth/-est；苏格兰词如 tryst（约定相会/凑在一起）、"
    "dittay（起诉书、罪状）、exerce（操练、试炼）、aggreage（加重、夸大）、kithe（显出）、"
    "registrate（记录在案）、by-gones（过往的事）、premit（先提出）。要按意思读懂后译成现代中文。\n"
    "体例是逐节释经：每段先列出被讲解的经文，再说明这几节在全章中的位置与大意，然后分条列出教训"
    "（Doctrine 1. / Learn, 1. 2. 3. / Whence learn），偶有 Consider 1. 2.（「试想」）。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气。不要译成"
    "佶屈聱牙的欧化长句，也不要冲淡成白话通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（页码、经文节号段落、旁注、花饰首字、推补标记等），"
    "**必须原样逐个保留**，个数、先后都与原文一致，放在中文里对应的位置\n"
    "3. 星号 `*` 是斜体标记，逐一保留，开合各一个；`**N**` 是经文节号的粗体，原样保留\n"
    "4. **凡引用圣经经文，一律照抄和合本**；他用 KJV，与和合本措辞不同时仍以和合本为准；"
    "但凡他说 that is / to wit 后给出的是自己的解释，按他的英文译\n"
    "5. 每段开头被讲解的经文（以加粗节号 **N** 开头的经文行）照抄和合本该节，节号照原文保留\n"
    "6. 方括号 [ ] 里的词是编者据上下文推补的（原书此处缺损），照样译出，**方括号原样保留**，"
    "如 [bulk] → [担子]、[further] → [更进一步]\n"
    "7. `Doctrine` / `Doct.` → 教训；`Learn` / `Whence learn` → 由此可学：；`Consider` → 试想；"
    "`i. e.` / `that is` / `to wit` → 即；`&c.` → ……（不作「等等」）；`v.` / `ver.` / `verse` → 第 N 节；"
    "`Chap.` → 第 N 章\n"
    "8. 拉丁文、希腊文一律保留原文，其后用圆括号附中文译义，如 *eximiè & singulariter*（格外地、特别地）；"
    "希腊文逐字照抄，一个字母、一个重音符号都不许改\n"
    "9. 圣经书卷名、人名、地名用和合本标准译名：John→约翰，John the Baptist→施洗约翰，"
    "Peter/Simon/Cephas→彼得/西门/矶法，Nathanael→拿但业，Nicodemus→尼哥底母，Lazarus→拉撒路，"
    "Martha→马大，Mary Magdalene→抹大拉的马利亚，Thomas→多马，Judas→犹大，Pilate→彼拉多，"
    "Caiaphas→该亚法，Annas→亚那，Capernaum→迦百农，Cana→迦拿，Samaria/Sychar→撒玛利亚/叙加，"
    "Bethany→伯大尼，Ierusalem/Hierusalem/Jerusalem→耶路撒冷，Galilee→加利利，Judea/Jury→犹太\n"
    "10. 经文出处一律转成「书卷名 章:节」：Joh. 3.16. → 约翰福音 3:16；Rom. 8.28. → 罗马书 8:28；"
    "1 Cor. 1.13. → 哥林多前书 1:13；Psal. 32.1. → 诗篇 32:1；Matth. 5.23, 24. → 马太福音 5:23-24；"
    "本书内的 chap. 3.35. → 第 3 章 35 节；ver. 14. → 第 14 节\n"
    "11. 教父与古人用通行中文译名：Augustine→奥古斯丁，Chrysostome→屈梭多模，Ierome→哲罗姆，"
    "Cyril→西里尔，Ebion→伊便尼，Cerinthus→克林妥，Luther→路德，Calvin→加尔文；"
    "近代学者与人物音译后**每篇首次出现括注英文原名**，如卡拉米（Calamy）、特拉普（Trapp）\n"
    "12. 术语精确、互不撞词：justification→称义　sanctification→成圣　regeneration→重生　"
    "calling→呼召（职业意义作「本分」或「职分」）　election/the Elect→拣选/选民　"
    "reprobation→弃绝　adoption→儿子的名分　grace→恩典　faith→信心　the Gospel→福音　"
    "the Law→律法　Mediatour/Mediator→中保　Godhead→神性　the Word→道　"
    "Ministers→传道人　ordinances→圣礼与敬拜的规条（视上下文）　Sacraments→圣礼　"
    "carnal→属肉体的　professours→认信的人　Saints→圣徒\n"
    "13. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」，全书前后一致\n"
    "14. **不得把任何英文词原样留在中文句子里**；印本里偶有的排印错字，按上下文读通后译出，"
    "不要留残词，也不要另加说明"
)

RE_TAG = re.compile(r'<[^<>]{1,400}>')
RE_PH = re.compile(r'⟦(\d+)⟧')


def mask(text: str):
    tags = []

    def put(m):
        tags.append(m.group(0))
        return f'⟦{len(tags)}⟧'
    return RE_TAG.sub(put, text), tags


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
    leak = tf.output_leak(zh)
    if leak:
        problems.append(leak)
    if re.search(r'[A-Za-z]{4}', en) and not re.search(r'[一-鿿]', zh):
        problems.append('译文无汉字')
    return '；'.join(problems)


def tidy(zh: str) -> str:
    zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
    zh = re.sub(r'[〔［]([A-Za-zÀ-ÿ][A-Za-zÀ-ÿ .\'’-]*)[〕］]', r'（\1）', zh)
    # &c. 一律省略号（全站通则）
    zh = re.sub(r'(等等|等语|云云)(?=[」』。，；：）\s]|$)', '……', zh)
    return zh


def translate_one(text: str, resume: bool, label: str = '') -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached):
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}', flush=True)

    base = ("把下面这段赫奇森《约翰福音注释》的 1657 年英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；只输出译文。\n\n")
    out = tidy(tf.call_claude(base + text, timeout=900, label=label))
    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** `*` 斜体标记"
               "（开合各一个）与 ⟦N⟧ 占位符（个数与先后都要对上）；希腊文逐字照抄；"
               "**不得把任何英文词原样留在中文句子里**。只输出译文。\n\n")
        out2 = tidy(tf.call_claude(fix + text, timeout=900, label=label + '·retry'))
        if not structural_diff(text, out2):
            out = out2
        else:
            out = out2 or out
            with BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {structural_diff(text, out)}\n'
                         f'  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')
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
    只 add / commit 赫奇森这几条路径，不碰工作区别的改动；失败只告警，不中断翻译。"""
    pub = ROOT / 'scripts' / 'publish_hutcheson_zh.py'
    if not pub.exists():
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True,
                           text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['hutcheson/john', 'hutcheson_raw/john/zh_chapters', 'hutcheson_raw/john/zh_cache',
                 'hutcheson_raw/john/zh_meta.json', '_data/hutcheson_john.json', '_data/hutcheson_john_zh.json',
                 '_data/compare_sources.yml', '_data/commentaries.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m',
                            f'feat(hutcheson): 约翰福音注释中译 · {slug}（自动发布）\n\n'
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
    ap.add_argument('--jobs', type=int, default=3)
    ap.add_argument('--no-publish', action='store_true')
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    slugs = all_slugs() if a.all else a.section
    if not slugs:
        ap.error('--section 或 --all')
    for s in slugs:
        if a.resume and not a.dry_run and (OUT_DIR / f'{s}.md').exists():
            units = units_of(s)
            keys = {tf.md5key(KEY_NS + mask(b)[0]) for k, b in units if k == 'text'}
            if all((CACHE / f'{k}.txt').exists() for k in keys):
                continue
        try:
            run_section(s, a.resume, a.dry_run, a.jobs, not a.no_publish)
        except RuntimeError as e:
            if 'session limit' in str(e).lower() or 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)          # 用量汇总由 claude_usage 的 atexit 打印
            raise


if __name__ == '__main__':
    main()
