#!/usr/bin/env python3
"""translate_knox_psalm6.py —— 诺克斯《苦难者的堡垒：诗篇第六篇讲解》英文页 knox/psalm6/part-N.md → 中文 raw。

照 translate_owen_psalm130 的路子：质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用 translate_alexander_acts；
短段附前后段英文；CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

英文页是 publish_knox_psalm6_en.py 生成的 HTML 段落，这里逐段送模型：
  - <p>、<p class="kx-quote">（整段引经）、<p class="kx-sign">（落款）、<h3 class="kx-sec">（信头、论旨标题）逐段译；
  - 注号 <sup class="kx-fn">…</sup> 换成 [^fN] 再遮；<em> 换成星号；
  - 页末注（.kx-notes）不送模型：六条注有四条是给古词作的英文释义（horrible → Alarming 之类），
    照译没有意义，由发布脚本 publish_knox_psalm6_zh.NOTES_ZH 手写中文注。

缓存  knox_raw/psalm6/zh_cache/<md5>.txt   ← 必须保留
输出  knox_raw/psalm6/zh_chapters/<页>.md  ← 翻完 chmod 444（只有正文，不含注）
时刻  knox_raw/psalm6/zh_meta.json         ← 每页译完的时刻（发布按页查表）

用法：python3 -u scripts/translate_knox_psalm6.py --dry-run --all
      python3 -u scripts/translate_knox_psalm6.py --section part-1 --limit 3     # 试译前 3 段，只打印不写出
      python3 -u scripts/translate_knox_psalm6.py --section part-1 --resume      # 单路；自动发布
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf          # noqa: E402
import translate_alexander_acts as T   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'knox' / 'psalm6'
RAW = ROOT / 'knox_raw' / 'psalm6'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'KNOX_PS6::'
MAX_CHARS = 3200
SHORT_CTX = 300
MIN_FREE = 300 * 2**20
ORDER = ['part-1', 'part-2']

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'

SYSTEM = (
    "你是一位熟悉宗教改革史与改革宗教义的中文译者，正在翻译约翰·诺克斯（John Knox，约 1514–1572，苏格兰改教家）"
    "的《苦难者的堡垒：诗篇第六篇讲解》（A Fort for the Afflicted, in an Exposition upon the Sixth Psalm，1554）。\n"
    "此书体例：这是一封写给岳母伊丽莎白·鲍斯（Elizabeth Bowes）的长信，她长年陷在良心的惊惧里，疑心自己不是神的选民；"
    "诺克斯当时因玛丽女王复辟天主教、弥撒重立而逃离英格兰。他逐节讲诗篇第 6 篇：大卫在病中饮了神忿怒的杯，"
    "神的选民在属灵的十字架下怎样哀诉、怎样仍抓住神；讲解中不断转过来直接劝慰收信人（beloved mother / dearly beloved）。"
    "文风是十六世纪中叶的英文：多倒装（Plain it is that… / Evident it is…），句子长、多分号与破折号，语气恳切。\n"
    "译文要沉稳、准确、读得懂、有书信的温度：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系不能丢。"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "古词按十六世纪的意思译，不按今义：ingine → 禀性、天性；commoved → 激动、动怒；dolours → 愁苦；abject → 被弃；"
    "let（妨碍）/ letteth → 拦阻；absolve（a treatise）→ 写完；entreat（对待）→ 待；prevent → 抢先；"
    "sometimes（从前）→ 从前、一度；presently → 眼下；assuredly → 确实；singular battle → 单打独斗；"
    "manly reason → 人的理性；horrible → 可怕的、骇人的；the idol（指弥撒）→ 那偶像。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表注号或排版标签，**必须原样逐个保留**，个数、先后都与原文一致；注号紧跟它所注的词句\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。中文对应部分照样用 `*` 包，一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. 引用经文的原句（引号里或斜体的整句），能对上和合本某节的，一律照抄和合本措辞；"
    "诺克斯明显是在转述、意译或把几节揉在一起的，按他的英文字面译，不硬套和合本。"
    "只给出处、没有引经文的，只译出处，不补经文。诗篇第 6 篇各节照和合本："
    "1 耶和华啊，求你不要在怒中责备我，也不要在烈怒中惩罚我！2 耶和华啊，求你可怜我，因为我软弱。耶和华啊，求你医治我，因为我的骨头发战。"
    "3 我心也大大地惊惶。耶和华啊，你要到几时才救我呢？4 耶和华啊，求你转回搭救我！因你的慈爱拯救我。"
    "5 因为，在死地无人记念你，在阴间有谁称谢你？6 我因唉哼而困乏；我每夜流泪，把床榻漂起，把褥子湿透。"
    "7 我因忧愁眼睛干瘪，又因我一切的敌人眼睛昏花。8 你们一切作孽的人，离开我吧！因为耶和华听了我哀哭的声音。"
    "9 耶和华听了我的恳求；耶和华必收纳我的祷告。10 我的一切仇敌都必羞愧，大大惊惶；他们必要退后，忽然羞愧"
    "（诺克斯所据英译与和合本措辞不同时——如「who laudeth thee in the pit」——仍照和合本该节）\n"
    "5. 经文出处：书卷名换和合本全称，罗马数字章号写成阿拉伯数字（Psalm 88 → 诗篇 88 篇；Job 9 → 约伯记 9 章；"
    "Rom. viii. → 罗马书 8 章）\n"
    "6. 拉丁文、希腊文、希伯来文逐字照抄，原文里没有的一个字母也不许添\n"
    "7. `&c.` → ……（不作「等等」）；分点照原文层次：First / Secondly / Thirdly → 第一、第二、第三\n"
    "8. **凡音译出来的人名、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "伯拉纠（Pelagius）、奥古斯丁（Augustine）。和合本里本来就有的圣经人名地名不括注（大卫、约伯、希西家）。"
    "英文原文没写的原名不要补，不要编\n"
    "9. 称呼照原信：beloved mother / dear mother → 亲爱的母亲；mother → 母亲；dearly beloved → 亲爱的；"
    "beloved in the Lord → 主内亲爱的；J. K. 照写\n"
    "10. 术语全书一律、互不撞词：the elect / God's elect / chosen → 选民 / 神的选民 / 蒙拣选的人；"
    "the reprobate → 被弃绝的人；the cross → 十字架；the spiritual cross → 属灵的十字架；"
    "wrath → 忿怒；displeasure → 不悦（经文 6:1 作「烈怒」）；anger → 怒气；the flesh → 肉体；the spirit → 灵；"
    "the inward man → 里面的人；repentance → 悔改；faith → 信心；hope → 盼望；mercy → 怜悯；grace → 恩典；"
    "temptation → 试探；affliction → 苦难；trouble → 患难；tribulation → 苦难；comfort → 安慰；"
    "conscience → 良心；idolatry / idolaters → 拜偶像 / 拜偶像的人；the devil / Satan → 魔鬼 / 撒但；"
    "the Holy Ghost → 圣灵；Christ Jesus → 基督耶稣；the Gospel → 福音；the Evangel → 福音；"
    "hell → 地狱；death → 死；the pit → 阴间（经文）/ 坑；congregation → 会众；salvation → 救恩\n"
    "11. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "12. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的外文引文除外）\n"
    "13. 信头、标题（全大写的一行）译成简短的标题式短语；落款（Yours with sorrowful heart / Watch and pray）照书信格式简译"
)


class DiskLow(RuntimeError):
    pass


def check_disk():
    free = shutil.disk_usage(RAW).free
    if free < MIN_FREE:
        raise DiskLow(f'磁盘剩余 {free / 2**20:.0f} MB < {MIN_FREE / 2**20:.0f} MB')


RE_SUP = re.compile(r'\s*<sup class="kx-fn"><a href="#fn-(\d+)" id="fnref-\1">\1</a></sup>')
RE_OPEN = re.compile(r'<(p|h3)( class="kx-(?:sec|quote|sign)")?>')


def to_src(inner):
    """英文页段内 HTML → 送模型的形态（[^fN]、*斜体*）。注号前的空格去掉，让它紧贴所注的词。"""
    inner = RE_SUP.sub(r'[^f\1]', inner)
    return re.sub(r'<em>(.*?)</em>', r'*\1*', inner)


def to_page(zh):
    zh = re.sub(r'\[\^f(\d+)\]', r'<sup class="kx-fn"><a href="#fn-\1" id="fnref-\1">\1</a></sup>', zh)
    return re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', zh)


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
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].strip()
    return t.split('\n\n<div class="kx-notes">')[0]


def blocks(slug):
    """→ [(kind, text)]，kind: text（送模型）/ keep（原样）。按序拼回即成页面正文（不含页末注）。"""
    out = []
    for n, b in enumerate(body_of(slug).split('\n\n')):
        if n:
            out.append(('keep', '\n\n'))
        m = RE_OPEN.match(b)
        cl = '</h3>' if b.endswith('</h3>') else '</p>'
        if not m or not b.endswith(cl):
            raise SystemExit(f'[{slug}] 认不出的块：{b[:120]!r}')
        src = to_src(b[len(m.group(0)):-len(cl)])
        out.append(('keep', m.group(0)))
        if not re.search(r'[A-Za-z]', T.RE_ANY.sub('', src)):
            out.append(('keep', to_page(src)))
        else:
            out += [('text', piece) for piece in split_long(src)]
        out.append(('keep', cl))
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
    base = ("把下面这段诺克斯《诗篇第六篇讲解》的十六世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
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


def run_section(slug, resume, dry, publish, limit=0):
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
        ctx = ''
        if len(plain(b)) < SHORT_CTX:
            p = idx.index(i)
            prev = plain(bl[idx[p - 1]][1])[-600:] if p > 0 else ''
            nxt = plain(bl[idx[p + 1]][1])[:600] if p + 1 < len(idx) else ''
            ctx = (('【前】' + prev + '\n') if prev else '') + (('【后】' + nxt) if nxt else '')
        masked, tags = T.mask(b)
        done[i] = to_page(T.unmask(translate_one(masked, resume, f'{slug}#{c}', ctx), tags))
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
    pub = ROOT / 'scripts' / 'publish_knox_psalm6_zh.py'
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['knox/psalm6', 'knox_raw/psalm6/zh_chapters', 'knox_raw/psalm6/zh_cache', 'knox_raw/psalm6/zh_meta.json',
                 'knox_raw/psalm6/zh_translate_issues.log', 'knox_raw/psalm6/zh_italic_notes.log',
                 '_data/commentaries.yml', '_data/compare_sources.yml', 'commentaries/psalms/index.html']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(knox): 诗篇第六篇讲解中译 · 第 {slug[-1]} 部分（自动发布）\n\n'
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
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    secs = ORDER if a.all else a.section
    if not secs:
        ap.error('--section 或 --all')
    tot_calls = tot_chars = 0
    for s in secs:
        try:
            r = run_section(s, a.resume, a.dry_run, not a.no_publish, a.limit)
            if a.dry_run and r:
                tot_calls += r[0]; tot_chars += r[1]
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
