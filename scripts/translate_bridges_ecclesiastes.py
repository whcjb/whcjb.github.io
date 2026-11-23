#!/usr/bin/env python3
"""translate_bridges_ecclesiastes.py —— 布里奇斯《传道书释义》英文页 bridges/ecclesiastes/<页>.md → 中文 raw。

照 translate_knox_psalm6 的路子：质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用 translate_alexander_acts；
短段附前后段英文；CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

英文页是 publish_bridges_ecclesiastes_en.py 生成的 HTML 段落：
  - <p class="ec-verse">（经文段，可连排几节）**不送模型**：每节由程序填和合本（assets/cuv.json），
    节号 span 原样保留；英文里的边注异读（marg. / M. R.）丢掉——和合本自带「或译」小注；
  - <p>（解经）、<p class="ec-poem">（引诗，行间 <br>）、<p class="bg-center">（序言落款）逐段送模型；
  - 小型大写 <span class="ec-sc"> 中文无对应，送模型前去掉标签只留字。
  - 每章的系统提示附上本章和合本经文，解经里引到本章经文时照抄和合本措辞。

缓存  bridges_raw/ecclesiastes/zh_cache/<md5>.txt   ← 必须保留
输出  bridges_raw/ecclesiastes/zh_chapters/<页>.md  ← 翻完 chmod 444
时刻  bridges_raw/ecclesiastes/zh_meta.json         ← 每页译完的时刻（发布按页查表）

用法：python3 -u scripts/translate_bridges_ecclesiastes.py --dry-run --all
      python3 -u scripts/translate_bridges_ecclesiastes.py --section 6 --limit 3        # 试译前 3 段，只打印不写出
      python3 -u scripts/translate_bridges_ecclesiastes.py --section 6 --resume --max-seconds 540
        # 单路；前台分段跑（到时在段与段之间停下，exit 5，缓存已落盘，再跑 --resume 续上）；整页译完自动发布
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf          # noqa: E402
import translate_alexander_acts as T   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'bridges' / 'ecclesiastes'
RAW = ROOT / 'bridges_raw' / 'ecclesiastes'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'BRIDGES_ECCL::'
MAX_CHARS = 3200
SHORT_CTX = 300
MIN_FREE = 300 * 2**20
ORDER = ['preface'] + [str(n) for n in range(1, 13)]
CUV = json.loads((ROOT / 'assets' / 'cuv.json').read_text(encoding='utf-8'))['21']   # 传道书

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'

SYSTEM_BASE = (
    "你是一位熟悉改革宗神学与清教徒传统的中文译者，正在翻译查理·毕列志（Charles Bridges，1794–1869，"
    "英国圣公会福音派牧师）的《传道书释义》（An Exposition of the Book of Ecclesiastes，1860）。\n"
    "此书体例：逐段讲解传道书经文，先释经义，再转到属灵应用与劝勉；常引清教徒与教父的话（单引号）、"
    "大量串引经文（双引号，后附出处）；多用破折号连缀短语、感叹与反问，语气恳切、带牧者的温度。"
    "书中「the Preacher」专指所罗门（传道者）。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，破折号串起的短语照中文习惯处理，"
    "逻辑关系不能丢。不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（如诗行之间的换行），**必须原样逐个保留**，个数、先后都与原文一致\n"
    "3. 引用经文的原句（双引号里的），能对上和合本某节的，一律照抄和合本措辞（引到传道书本章经文的，照下面所附本章和合本）；"
    "毕列志明显是在转述、意译或把几节揉在一起的，按他的英文字面译，不硬套和合本。只给出处、没有引经文的，只译出处，不补经文\n"
    "4. 经文出处：书卷名换和合本全称，章节照写阿拉伯数字，格式「（箴言 3:5）」「（马太福音 18:3、4）」"
    "「（列王纪上 4:30–33）」；Comp. → 参；Ib. → 同上；with → 并；marg. / M. R. → 小字（边注异读）；"
    "Ecclesiastes / Eccles. / Chap.（指本书）→ 传道书；ver. / v. → 节\n"
    "5. 拉丁文、希腊文、希伯来文逐字照抄，原文里没有的一个字母也不许添\n"
    "6. `&c.` → ……（不作「等等」）\n"
    "7. **凡音译出来的人名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "奥古斯丁（Augustine）、雷诺兹主教（Bp. Reynolds）。和合本里本来就有的圣经人名地名不括注（所罗门、大卫、约伯）。"
    "英文原文没写的原名不要补，不要编。常引作者的中文名全书一律：Bp. Hall → 霍尔主教；Bp. Reynolds → 雷诺兹主教；"
    "Bp. Taylor → 泰勒主教；Bp. Patrick → 帕特里克主教；Bp. Hopkins → 霍普金斯主教；Henry → 亨利；"
    "Scott / Mr. Scott → 司各特；Cotton → 科顿；Geier → 盖尔；Mercer → 梅西耶；Holden → 霍尔登；"
    "Wardlaw → 沃德洛；Serranus / Serran → 塞拉努斯；Lavater → 拉瓦特；Diodati → 迪奥达蒂；Witsius → 维特修斯；"
    "Charnock → 查诺克；Leighton → 雷登；Luther → 路德；Calvin → 加尔文；Bacon / Lord Bacon → 培根；"
    "Bonar → 博纳尔（与本站博纳尔诸书同）\n"
    "8. 术语全书一律、互不撞词：vanity → 虚空；vexation of spirit → 捕风；under the sun → 日光之下；"
    "the Preacher（所罗门）→ 传道者；preacher / minister（今日的传道人）→ 传道人；wisdom → 智慧；"
    "folly → 愚昧；madness → 狂妄；the fool → 愚昧人；the wise man → 智慧人；Providence → 神的护理（护理）；"
    "Divine Teaching → 神的教导；grace → 恩典；godliness → 敬虔；the world → 世界；worldling → 属世的人；"
    "covetousness → 贪心；Mammon → 玛门；the Gospel → 福音；the Saviour → 救主；child of God → 神的儿女；"
    "eternity → 永恒；judgment → 审判；conscience → 良心；repentance → 悔改；faith → 信心；mercy → 怜悯；"
    "the Church → 教会；the Christian → 基督徒；the ungodly → 不敬虔的人；the righteous → 义人；"
    "Inspiration → 默示；the Sacred Canon → 圣经正典\n"
    "9. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "10. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的外文引文除外）\n"
    "11. 引诗（赞美诗）译成整齐的中文诗行，行数与原文相同，行间的占位符照原样保留在对应位置；末行若是出处（Olney Hymns…），照译出处\n"
)


def system_for(slug):
    if not slug.isdigit():
        return SYSTEM_BASE
    vv = CUV[slug]
    text = ' '.join(f'{v} {vv[v]}' for v in sorted(vv, key=int))
    return SYSTEM_BASE + f"\n附：传道书第 {slug} 章和合本（解经里引到这些经文时照抄）：\n{text}\n"


class DiskLow(RuntimeError):
    pass


class TimeUp(RuntimeError):
    pass


def check_disk():
    free = shutil.disk_usage(RAW).free
    if free < MIN_FREE:
        raise DiskLow(f'磁盘剩余 {free / 2**20:.0f} MB < {MIN_FREE / 2**20:.0f} MB')


QUOTES = str.maketrans({'「': '“', '」': '”', '『': '‘', '』': '’'})
RE_OPEN = re.compile(r'<p( class="(?:ec-verse|ec-poem|bg-center)")?>')
RE_SC = re.compile(r'<span class="ec-sc">(.*?)</span>')
RE_VN = re.compile(r'<span class="ec-vn" id="v(\d+)">([^<]*)</span>')


def to_src(inner):
    return RE_SC.sub(r'\1', inner)


def verse_zh(inner, slug):
    """经文段 → 和合本。保留节号 span（含编者补的 [12.]），每节正文换成和合本该节。"""
    out = []
    for m in RE_VN.finditer(inner):
        v = m.group(1)
        out.append(f'<span class="ec-vn" id="v{v}">{m.group(2)}</span> {CUV[slug][v]}')
    if not out:
        raise SystemExit(f'[{slug}] 经文段认不出节号：{inner[:120]!r}')
    return ''.join(out)                  # 中文节与节之间不留空格


def split_long(b):
    if len(b) <= MAX_CHARS:
        return [b]
    pieces = re.split(r'([.?!;][”"’)]?)\s+(?=[“"‘A-Z(*])', b)
    sents = [pieces[i] + (pieces[i + 1] if i + 1 < len(pieces) else '') for i in range(0, len(pieces), 2)]
    out, cur = [], ''
    for s in sents:
        if cur and len(cur) + len(s) + 1 > MAX_CHARS:
            out.append(cur); cur = s
        else:
            cur = (cur + ' ' + s).strip()
    if cur:
        out.append(cur)
    return out


def body_of(slug):
    return (SRC / f'{slug}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].strip()


def blocks(slug):
    """→ [(kind, text)]，kind: text（送模型）/ keep（原样）。按序拼回即成页面正文。"""
    out = []
    for n, b in enumerate(body_of(slug).split('\n\n')):
        if n:
            out.append(('keep', '\n\n'))
        m = RE_OPEN.match(b)
        if not m or not b.endswith('</p>'):
            raise SystemExit(f'[{slug}] 认不出的块：{b[:120]!r}')
        inner = b[len(m.group(0)):-4]
        out.append(('keep', m.group(0)))
        if m.group(1) and 'ec-verse' in m.group(1):
            out.append(('keep', verse_zh(inner, slug)))
        else:
            src = to_src(inner)
            if 'ec-poem' in (m.group(1) or ''):
                out.append(('text', src))          # 诗不拆
            else:
                out += [('text', piece) for piece in split_long(src)]
        out.append(('keep', '</p>'))
    return out


def ctx_block(ctx):
    if not ctx:
        return ''
    return ("【上下文】下面是这段前后的原文，只帮助理解这段在说什么，**不要翻译、不要输出、不要评论**：\n"
            f"<上下文>\n{ctx}\n</上下文>\n\n【要翻译的这段】\n")


def translate_one(text, resume, label, ctx=''):
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not T.structural_diff(text, cached) or key in T.accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {T.structural_diff(text, cached)[:90]}', flush=True)
    base = ("把下面这段毕列志《传道书释义》的英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 ⟦N⟧ 占位符；"
            "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    check_disk()
    raw = tf.call_claude(base + ctx_block(ctx) + text, timeout=900, label=label)
    out = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(raw)), text), text, label)
    diff = T.structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        with T.BAD_LOG.open('a', encoding='utf-8') as fh:
            fh.write(f'[{label}·first] {diff[:120]}\n  RAW: {raw[:400]!r}\n')
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** ⟦N⟧ 占位符（个数与先后都要对上）；"
               "原文没有的外文不许添；**不得把任何英文词原样留在中文句子里**。"
               "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
        for k in (1, 2):
            out2 = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(
                tf.call_claude(fix + ctx_block(ctx) + text, timeout=900, label=f'{label}·retry{k}'))), text),
                text, f'{label}·retry{k}')
            if not T.structural_diff(text, out2):
                out = out2
                break
            if not T.is_severe(T.structural_diff(text, out2)) or T.is_severe(diff):
                out, diff = out2 or out, T.structural_diff(text, out2 or out)
        else:
            with T.BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {T.structural_diff(text, out)}\n  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')
            if T.is_severe(T.structural_diff(text, out)):
                raise T.SevereTranslation(f'{label}: {T.structural_diff(text, out)[:120]}')
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out


def plain(b):
    return re.sub(r'\s+', ' ', T.RE_ANY.sub(' ', b)).strip()


def run_section(slug, resume, dry, publish, limit=0, deadline=0):
    tf.SYSTEM = system_for(slug)
    bl = blocks(slug)
    idx = [i for i, (k, _) in enumerate(bl) if k == 'text']
    todo = idx[:limit] if limit else idx
    keys = {tf.md5key(KEY_NS + T.mask(bl[i][1])[0]) for i in todo}
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    chars = sum(len(bl[i][1]) for i in todo)
    print(f'[{slug}] 需翻译 {len(todo)} 段，已缓存 {hit}，待调用 {len(keys) - hit}，约 {chars:,} 字符', flush=True)
    if dry:
        return len(keys) - hit, sum(len(bl[i][1]) for i in todo
                                    if not (CACHE / f'{tf.md5key(KEY_NS + T.mask(bl[i][1])[0])}.txt').exists())
    done = {}
    for c, i in enumerate(todo, 1):
        b = bl[i][1]
        masked, tags = T.mask(b)
        cached = (CACHE / f'{tf.md5key(KEY_NS + masked)}.txt').exists()
        if deadline and not cached and time.time() > deadline:
            raise TimeUp(f'{slug} 第 {c}/{len(todo)} 段前到时，已缓存的段下次 --resume 直接取用')
        ctx = ''
        if len(plain(b)) < SHORT_CTX:
            p = idx.index(i)
            prev = plain(bl[idx[p - 1]][1])[-600:] if p > 0 else ''
            nxt = plain(bl[idx[p + 1]][1])[:600] if p + 1 < len(idx) else ''
            ctx = (('【前】' + prev + '\n') if prev else '') + (('【后】' + nxt) if nxt else '')
        # 模型偶尔在一段里自行分段（空行）；正文是 <p> 内的 HTML，空行会让 kramdown 截断 <p>，拼页面时去掉段内换行
        done[i] = re.sub(r'\s*\n\s*', '', T.unmask(translate_one(masked, resume, f'{slug}#{c}', ctx), tags))
        # 引号体例全书一律照原书分工：经文用 “”，人言引语用 ‘’。各段分送模型，约一成段落漂成「」『』，拼页面时统一
        done[i] = done[i].translate(QUOTES)
        if c % 10 == 0:
            print(f'  [{slug}] {c}/{len(todo)} 段', flush=True)
    if limit:
        for i in sorted(done):
            print('-----', bl[i][1][:300], '\n=====', done[i][:700])
        return
    body = ''.join(done.get(i, t) for i, (k, t) in enumerate(bl))
    body, missing = T.annotate_terms(body, body_of(slug))
    if missing:
        print(f'    [names] {slug}: 英文源里有 {missing}，译文里没有原名、也找不到已知中文写法，未自动补', flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{slug}.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum((CACHE / f'{k}.txt').exists() for k in keys)
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    if slug not in meta or after > hit or not resume:
        meta[slug] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(slug)


def autopublish(slug):
    pub = ROOT / 'scripts' / 'publish_bridges_ecclesiastes_zh.py'
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['bridges/ecclesiastes', 'bridges_raw/ecclesiastes/zh_chapters', 'bridges_raw/ecclesiastes/zh_cache',
                 'bridges_raw/ecclesiastes/zh_meta.json', 'bridges_raw/ecclesiastes/zh_translate_issues.log',
                 'bridges_raw/ecclesiastes/zh_italic_notes.log', '_data/commentaries.yml', '_data/compare_sources.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        label = '序言' if slug == 'preface' else f'第 {slug} 章'
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(bridges/ecclesiastes): 传道书释义中译 · {label}（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', '--', *paths],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
            ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT, capture_output=True, text=True, timeout=300)
            if ps.returncode != 0:          # 别的会话刚推过：先 rebase 再推一次
                subprocess.run(['git', 'pull', '-q', '--rebase', '--autostash', 'origin', 'master'], cwd=ROOT,
                               capture_output=True, text=True, timeout=300)
                ps = subprocess.run(['git', 'push', '-q', 'origin', 'master'], cwd=ROOT, capture_output=True, text=True, timeout=300)
            print('    [autopublish] 已提交' + ('并推送' if ps.returncode == 0 else f'，推送失败 {ps.stderr[:160]}'), flush=True)
    except Exception as e:                                   # noqa: BLE001
        print(f'    [autopublish] 异常，已跳过：{e}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', action='append', default=[])
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--no-publish', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='试译：只译前 N 段，只打印不写出')
    ap.add_argument('--max-seconds', type=int, default=0, help='前台分段跑：到时在段与段之间停下（exit 5）')
    a = ap.parse_args()
    secs = ORDER if a.all else a.section
    if not secs:
        ap.error('--section 或 --all')
    deadline = time.time() + a.max_seconds if a.max_seconds else 0
    tot_calls = tot_chars = 0
    for s in secs:
        try:
            r = run_section(s, a.resume, a.dry_run, not a.no_publish, a.limit, deadline)
            if a.dry_run and r:
                tot_calls += r[0]; tot_chars += r[1]
        except TimeUp as e:
            print(f'⏸ 到时停下：{e}', flush=True)
            sys.exit(5)
        except DiskLow as e:
            print(f'⛔ 磁盘空间不足，中止：{e}', flush=True)
            sys.exit(43)
        except T.SevereTranslation as e:
            print(f'⛔ [{s}] 有段落重试后仍不合格，本篇不写出、不发布：{e}', flush=True)
            sys.exit(3)
        except RuntimeError as e:
            if 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)
            raise
    if a.dry_run:
        print(f'合计待调用 {tot_calls} 段，约 {tot_chars:,} 字符', flush=True)


if __name__ == '__main__':
    main()
