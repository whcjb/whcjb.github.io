#!/usr/bin/env python3
"""translate_owen_psalm130.py —— 欧文《诗篇 130 篇实践讲解》英文版 owen/psalm130/<页>.md → 中文 raw。

照 translate_bonar 的路子：质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用 translate_alexander_acts；
短段附前后段英文；CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

英文页是 publish_owen_psalm130_en.py 生成的 HTML 段落，这里逐段送模型：
  - 段落 <p>、<p class="op-arg">（章前提要）、<h3 class="op-sub">（「规则一」等小标题）、<p class="op-center"> 逐段译；
  - 脚注号 <sup class="op-fn">…</sup> 换成 [^fN] 再遮；<em> 换成星号；<br> 是标签，照遮；
  - 页末脚注（.op-notes 里每条 <p id="fn-N">）只送注文；
  - 第 1 页诗篇 130 篇全文（<p class="op-verse">）由程序填和合本，不送模型。
页名、组名不送模型，由 owen_raw/psalm130/titles_zh.tsv 给（发布脚本用）。

缓存  owen_raw/psalm130/zh_cache/<md5>.txt   ← 必须保留
输出  owen_raw/psalm130/zh_chapters/<页>.md  ← 翻完 chmod 444
时刻  owen_raw/psalm130/zh_meta.json         ← 每页译完的时刻（发布按页查表）

用法：python3 -u scripts/translate_owen_psalm130.py --dry-run --all
      python3 -u scripts/translate_owen_psalm130.py --section 4 --resume      # 单路；自动发布
      python3 -u scripts/translate_owen_psalm130.py --section 4 --limit 3     # 试译前 3 段，只打印不写出
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
SRC = ROOT / 'owen' / 'psalm130'
RAW = ROOT / 'owen_raw' / 'psalm130'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'OWEN_PS130::'
MAX_CHARS = 3200
SHORT_CTX = 300
MIN_FREE = 300 * 2**20
ORDER = ['prefatory-note', 'to-the-reader'] + [str(n) for n in range(1, 40)]

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'

SYSTEM = (
    "你是一位熟悉清教徒神学与改革宗教义的中文译者，正在翻译约翰·欧文（John Owen, 1616–1683，英国清教徒神学家）"
    "的《诗篇 130 篇实践讲解》（A Practical Exposition upon Psalm CXXX，1668；Goold 编《欧文全集》第 6 卷）。\n"
    "此书体例：欧文按经节分组讲解诗篇 130 篇，主题是落在罪的深处的灵魂怎样认识「在神有赦免之恩」、怎样等候神。"
    "文中层层分点（First, Secondly…；1. 2. (1.) (2.)），先立命题，再证明，再作应用（Use）；常驳苏西尼派、天主教的说法，"
    "偶引拉丁、希腊、希伯来字词与教父、经院学者。文风是十七世纪清教徒的论述散文：句子极长、从句层叠、多用分号与破折号。\n"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系、分点层次不能丢。"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表脚注号或排版标签，**必须原样逐个保留**，个数、先后都与原文一致；脚注号紧跟它所注的词句\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。中文对应部分照样用 `*` 包，一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. 引用经文的原句（引号里的整句），一律照抄和合本措辞；欧文明说是自己的直译或另一种译法时"
    "（literally / properly / the word signifies / may be rendered 之类），按他的英文字面译，不换和合本。"
    "只给出处、没有引经文的，只译出处，不补经文。诗篇 130 篇各节照和合本："
    "1 耶和华啊，我从深处向你求告！2 主啊，求你听我的声音！愿你侧耳听我恳求的声音！"
    "3 主耶和华啊，你若究察罪孽，谁能站得住呢？4 但在你有赦免之恩，要叫人敬畏你。"
    "5 我等候耶和华，我的心等候，我也仰望他的话。6 我的心等候主，胜于守夜的等候天亮，胜于守夜的等候天亮。"
    "7 以色列啊，你当仰望耶和华！因他有慈爱，有丰盛的救恩。8 他必救赎以色列脱离一切的罪孽\n"
    "5. 经文出处：书卷名换和合本全称，罗马数字章号写成阿拉伯数字（Rom. xi. 20 → 罗马书 11:20；1 Cor. x. 12 → 哥林多前书 10:12；"
    "Ps. li. 4 → 诗篇 51:4）；`verse 5` / `ver. 5` → 第 5 节\n"
    "6. 希腊文、拉丁文、希伯来文**逐字照抄，一个字母、一个重音符号都不许改**，**原文里没有的希腊文、希伯来文一个字母也不许添**；"
    "希腊词、希伯来词后用圆括号附中文译义；整句拉丁引文、拉丁诗保留原文，后面括注中文大意\n"
    "7. `&c.` → ……（不作「等等」）；`i.e.` / `that is` → 即；`viz.` → 即；`q. d.` → 意思是说；"
    "分点照原文层次：First / Secondly / Thirdly → 第一、第二、第三；1. 2. 照写；(1.) (2.) 照写；"
    "`Use` 作小标题时 → 应用\n"
    "8. **凡音译出来的人名、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "奥古斯丁（Augustine）、哲罗姆（Jerome）、加尔文（Calvin）、伯拉纠（Pelagius）、苏西尼派（Socinians）。"
    "和合本里本来就有的圣经人名地名不括注。英文原文没写的原名不要补，不要编\n"
    "9. 术语全书一律、互不撞词：forgiveness → 赦免（「在神有赦免之恩」的赦免）；pardon → 饶恕；"
    "the depths → 深处；to mark iniquity → 究察罪孽；iniquity → 罪孽；transgression → 过犯；guilt → 罪疚；"
    "to fear God / the fear of God → 敬畏神；to wait → 等候；to hope → 仰望（经文）/ 盼望；plenteous redemption → 丰盛的救恩；"
    "mercy → 怜悯（经文 130:7 作慈爱）；lovingkindness → 慈爱；grace → 恩典；the soul → 灵魂；"
    "conviction(s) → 知罪（使人知罪的光照）；indwelling sin → 内住的罪；mortification → 治死（罪）；"
    "communion with God → 与神相交；assurance → 确据；peace → 平安；the law / legal → 律法 / 律法的；"
    "the gospel / evangelical → 福音 / 福音的；covenant of grace → 恩典之约；new covenant → 新约；"
    "justification → 称义；sanctification → 成圣；satisfaction (of Christ) → 补赎；propitiation → 挽回祭；"
    "atonement → 赎罪；Mediator → 中保；the Holy Ghost / the Spirit → 圣灵；desertion → 离弃；temptation → 试探；"
    "backsliding → 退后；apostasy → 背道；hypocrite → 假冒为善的人；professor(s) → 认信的人；saints → 圣徒；believers → 信徒；"
    "discovery (of forgiveness) → 显明；supportment → 扶持；Papists → 天主教徒；schoolmen → 经院学者；"
    "Socinians → 苏西尼派；Arminian → 阿民念派；from everlasting → 从亘古（「亘」不可写作「亡」）\n"
    "10. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "11. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的外文引文除外）\n"
    "12. 只有一个短语的小标题、章前提要（一串用破折号隔开的要点），译成简短的标题式短语，标点照原文"
)

class DiskLow(RuntimeError):
    pass


def check_disk():
    free = shutil.disk_usage(RAW).free
    if free < MIN_FREE:
        raise DiskLow(f'磁盘剩余 {free / 2**20:.0f} MB < {MIN_FREE / 2**20:.0f} MB')


RE_SUP = re.compile(r'<sup class="op-fn"><a href="#fn-(\d+)" id="fnref-\1">\1</a></sup>')
RE_NOTE = re.compile(r'^(<p id="fn-(\d+)"><a class="op-back" href="#fnref-\2">\2</a>)(.*)(</p>)$')
RE_OPEN = re.compile(r'<(p|h3)( class="op-(?:arg|sub|center|right)")?>')


def to_src(inner):
    """英文页段内 HTML → 送模型的形态（[^fN]、*斜体*）。"""
    inner = RE_SUP.sub(r'[^f\1]', inner)
    return re.sub(r'<em>(.*?)</em>', r'*\1*', inner)


def to_page(zh):
    zh = re.sub(r'\[\^f(\d+)\]', r'<sup class="op-fn"><a href="#fn-\1" id="fnref-\1">\1</a></sup>', zh)
    return re.sub(r'\*([^*\n]+)\*', r'<em>\1</em>', zh)


def split_long(b):
    if len(b) <= MAX_CHARS:
        return [b]
    pieces = re.split(r'([.?!][”"’)]?)\s+(?=[“"‘A-Z(*])', b)
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


def psalm130_cuv():
    """第 1 页诗篇本文：和合本诗 130 篇全文，版式照英文页「Verse 1. …<br>2. …」。"""
    cuv = json.load(open(ROOT / 'assets' / 'cuv.json', encoding='utf-8'))['19']['130']
    ls = [f'{"第 1 节．" if v == "1" else v + "．"}{cuv[v].replace(chr(0x3000), "")}' for v in sorted(cuv, key=int)]
    return '<p class="op-verse">' + '<br>'.join(ls) + '</p>'


def blocks(slug):
    """→ [(kind, text)]，kind: text（送模型）/ keep（原样）。按序拼回即成页面正文。

    普通段 <p> 以字母或逗号收尾（一句话断在两段）时，与下一段合成一个单元送模型，段落标签遮成占位符原样保留；
    提要、小标题不合并。"""
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].strip()
    items = []          # ('p', pre, src, post) | ('raw', line)；之间的分隔另记
    seps = []
    for bi, b in enumerate(t.split('\n\n')):
        for li, line in enumerate(b.split('\n')):
            if items:
                seps.append('\n' if li else '\n\n')
            m = RE_NOTE.match(line)
            if m:
                items.append(('note', m.group(1), to_src(m.group(3)), m.group(4)))
            elif line.startswith('<p class="op-verse">') and slug == '1':
                items.append(('raw', psalm130_cuv()))
            elif RE_OPEN.match(line) and line.endswith(('</p>', '</h3>')):
                op = RE_OPEN.match(line).group(0)
                cl = line[-5:] if line.endswith('</h3>') else '</p>'
                items.append(('p' if op == '<p>' else 'h', op, to_src(line[len(op):-len(cl)]), cl))
            else:
                items.append(('raw', line))
    out = []
    i = 0
    while i < len(items):
        if i:
            out.append(('keep', seps[i - 1]))
        it = items[i]
        if it[0] == 'raw':
            out.append(('keep', it[1])); i += 1
            continue
        pre, src, post = it[1], it[2], it[3]
        j = i
        while (it[0] == 'p' and j + 1 < len(items) and items[j + 1][0] == 'p'
               and re.search(r'[A-Za-z,]\s*$', T.RE_ANY.sub('', items[j][2]))
               and len(src) + len(items[j + 1][2]) < MAX_CHARS):
            src += items[j][3] + seps[j] + items[j + 1][1] + items[j + 1][2]
            j += 1
        out.append(('keep', pre))
        if not re.search(r'[A-Za-z]', T.RE_ANY.sub('', src)):
            out.append(('keep', from_src(src)))
        else:
            for k, piece in enumerate(split_long(src)):
                out.append(('text', piece))
        out.append(('keep', items[j][3]))
        i = j + 1
    return out


def from_src(src):
    return to_page(src)


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
    base = ("把下面这段欧文《诗篇 130 篇实践讲解》的十七世纪英文译成简体中文。"
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
               "希腊文逐字照抄、原文没有的不许添；**不得把任何英文词原样留在中文句子里**。"
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
    body, missing = T.annotate_terms(body, (SRC / f'{slug}.md').read_text(encoding='utf-8'))
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
    pub = ROOT / 'scripts' / 'publish_owen_psalm130_zh.py'
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['owen/psalm130', 'owen_raw/psalm130/zh_chapters', 'owen_raw/psalm130/zh_cache', 'owen_raw/psalm130/zh_meta.json',
                 'owen_raw/psalm130/zh_translate_issues.log', 'owen_raw/psalm130/zh_italic_notes.log',
                 '_data/commentaries.yml', '_data/compare_sources.yml', 'commentaries/psalms/index.html']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        name = {'prefatory-note': '编者说明', 'to-the-reader': '致读者'}.get(slug, f'第 {slug} 页')
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(owen): 诗篇 130 篇实践讲解中译 · {name}（自动发布）\n\n'
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
