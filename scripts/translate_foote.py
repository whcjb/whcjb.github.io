#!/usr/bin/env python3
"""translate_foote.py —— 福特《路加福音讲义》英文版 foote/luke/lecture-<N>.md → 中文 raw。

质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用 translate_alexander_acts（最新一套闸）。
CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，自动带
--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

- 讲首经文段（ft-text）是钦定本 → 程序按讲首出处填和合本（assets/cuv.json），不送模型；
  出处标题「Luke 6:17–26」→「路加福音 6:17–26」；续讲「CONTINUED.」→「（续）」。
- 讲解段、注条逐段送模型；注号 <sup class="ft-fn">…</sup>、注条回链 <a class="ft-nsym">…</a> 整个一个占位
  （里面的 * † 是注号不是斜体）；长段按句切块（MAX_CHARS）。
- 短段（< SHORT_CTX，诗行、分条孤句）附前后段英文只供理解，不译；缓存键只取本段。

缓存  foote_raw/luke/zh_cache/<md5>.txt   ← 必须保留
输出  foote_raw/luke/zh_chapters/<N>.md   ← 翻完 chmod 444
时刻  foote_raw/luke/zh_meta.json         ← 每讲译完的真实时刻（发布按讲取，不用 mtime）

用法：python3 -u scripts/translate_foote.py --dry-run --all
      python3 -u scripts/translate_foote.py --section 20 --resume          # 单路；自动发布
      python3 -u scripts/translate_foote.py --section 20 --limit 3         # 试译前 3 段，只打印不写出
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf          # noqa: E402
import translate_alexander_acts as T   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'foote' / 'luke'
RAW = ROOT / 'foote_raw' / 'luke'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'FOOTE_LUKE::'
MAX_CHARS = 3200
SHORT_CTX = 300
N_LECT = 137

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'
# 注号与注条回链整个一个占位（同亚历山大使徒行传 aa-fnref 的处理）
T.RE_ANY = re.compile(r'<sup class="ft-(?:fn|vn)">.*?</sup>|<a class="ft-nsym"[^>]*>.*?</a>|' + T.RE_ANY.pattern)

SYSTEM = (
    "你是一位精通圣经与改革宗神学的中文译者，正在翻译詹姆斯·福特（James Foote）的《路加福音讲义》"
    "（Lectures on the Gospel according to Luke）。福特在苏格兰阿伯丁向会众逐段讲解路加福音，后扩写成书，共 137 讲。\n"
    "此书体例：每讲先列钦定本经文，再逐节讲解，最后归到应用和劝勉；常引其他福音书对照，大量引用圣经，"
    "偶引希腊文、拉丁文与古代作家，也常引亨利（Henry）、司各特（Scott）、多德里奇（Doddridge）、坎贝尔（Campbell）等注释家。"
    "文风是十九世纪苏格兰长老会的讲台散文，句子长、层层推进、语气庄重恳切，常直接向会众说话（my friends、you、let us）。"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系不能丢；"
    "向会众说话的口吻要保留（「弟兄姊妹」不要加，原文 my friends 译「朋友们」）。不要译成欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签或注号，**必须原样逐个保留**，个数、先后都与原文一致；注号紧跟它所注的词句\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。斜体多是他正在讲解的经文字句、书名、外文词；中文对应部分照样用 `*` 包，"
    "一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. 他引用经文（引号里的整句或斜体经文字句）一律照抄和合本措辞；只给出处、没有引经文的，只译出处，不补经文\n"
    "5. 经文出处：书卷名换和合本全称，章节换阿拉伯数字（Matt. ix. 20 → 马太福音 9:20；Luke viii. 43 → 路加福音 8:43；"
    "1 Cor. x. 16, 17 → 哥林多前书 10:16–17；Ps. li. 17 → 诗篇 51:17）；`chap. vii. 50` → 第 7 章 50 节；"
    "`the 25th verse` → 第 25 节；`the 9th chapter` → 第 9 章\n"
    "6. 希腊文、希伯来文、拉丁文**逐字照抄，一个字母、一个重音符号都不许改**，**原文里没有的希腊文、希伯来文一个字母也不许添**；"
    "希腊词后用圆括号附中文译义；整句拉丁引文保留原文，括注中文大意。英文诗句译成中文，不必押韵，分行照原文\n"
    "7. `&c.` → ……（不作「等等」）；`i.e.` → 即；`e.g.` → 例如；`viz.` → 即；注条里的 `Ibid.` → 同上；`in loc.` / `in locum` → 本处注释\n"
    "8. **凡音译出来的人名、地名（非和合本）、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "亨利（Henry）、司各特（Scott）、多德里奇（Doddridge）、坎贝尔（Campbell）、约瑟夫（Josephus）、加尔文（Calvin）、"
    "路德（Luther）、奥古斯丁（Augustine）。和合本里本来就有的圣经人名地名不括注。英文原文没写的原名不要补，不要编\n"
    "9. 术语全书一律、互不撞词：justification / justify → 称义；righteousness → 义；faith → 信心；grace → 恩典；"
    "the law → 律法；sin / sinner → 罪 / 罪人；atonement → 赎罪；propitiation → 挽回祭；redemption → 救赎；"
    "repentance → 悔改；conversion / converted → 归正 / 归正的；regeneration → 重生；sanctification → 成圣；"
    "election → 拣选；the gospel → 福音；the Saviour → 救主；our Lord → 我们的主；Messiah → 弥赛亚；"
    "ordinance(s) → 圣礼 / 典章（视上下文：the Lord's supper 等为圣礼，public ordinances 为公共聚会的蒙恩之道）；"
    "the Church → 教会；Popery / Papists → 天主教 / 天主教徒；Arminian → 阿民念派；"
    "from everlasting → 从亘古（「亘」不可写作「亡」）\n"
    "10. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "11. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的希腊拉丁文除外）\n"
    "12. 引号一律用中文弯引号 “ ” 与 ‘ ’（引文里再套引文用 ‘ ’），不用「」『』，也不用英文直引号"
)

_CUVD = None


def cuv(ch, v):
    global _CUVD
    if _CUVD is None:
        _CUVD = json.loads((ROOT / 'assets' / 'cuv.json').read_text(encoding='utf-8'))
    return _CUVD['42'][str(ch)][str(v)]


RE_HEAD = re.compile(r'^<h2 class="ft-head">Luke (\d+):(\d+)(?:–(?:(\d+):)?(\d+))?</h2>$')


def verse_range(head):
    m = RE_HEAD.match(head)
    c1, v1 = int(m.group(1)), int(m.group(2))
    c2 = int(m.group(3) or c1)
    v2 = int(m.group(4) or v1)
    out, c, v = [], c1, v1
    while (c, v) <= (c2, v2):
        try:
            cuv(c, v)
        except KeyError:
            c, v = c + 1, 1
            continue
        out.append((c, v))
        v += 1
    return out


def scripture_zh(vs):
    parts = []
    for i, (c, v) in enumerate(vs):
        num = '' if i == 0 else (f'<sup class="ft-vn">{v}</sup>' if c == vs[0][0] or v != 1 else f'<sup class="ft-vn">{c}:{v}</sup>')
        parts.append(num + cuv(c, v))
    return ' '.join(parts)


def head_zh(head):
    m = RE_HEAD.match(head)
    return '<h2 class="ft-head">路加福音 ' + head[len('<h2 class="ft-head">Luke '):]


def blocks(n):
    """→ [(kind, text, gid)]。kind: text（送模型）/ keep（原样或程序填好）。"""
    t = (SRC / f'lecture-{n}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].strip()
    out, vs, in_text = [], [], False
    for gid, b in enumerate(t.split('\n\n')):
        b = b.strip()
        if not b:
            continue
        if RE_HEAD.match(b):
            vs = verse_range(b)
            out.append(('keep', head_zh(b), gid))
            continue
        if b.startswith('<p class="ft-sub">'):
            out.append(('keep', '<p class="ft-sub">（续）</p>', gid))
            continue
        if b.startswith('<div class="ft-text"'):
            in_text = True
            out.append(('keep', b, gid))
            continue
        if in_text:
            if b == '</div>':
                in_text = False
                out.append(('keep', b, gid))
            else:
                out.append(('keep', scripture_zh(vs), gid))
            continue
        if not re.search(r'[A-Za-zΑ-ωἀ-ῼ]', re.sub(r'<[^>]+>', '', b)) or b.startswith('<div') or b.startswith('</div'):
            out.append(('keep', b, gid))
            continue
        if len(b) <= MAX_CHARS:
            out.append(('text', b, gid))
            continue
        pieces = re.split(r'([.?!][”"’)]?)\s+(?=[“"‘A-Z(*])', b)
        sents = [pieces[i] + (pieces[i + 1] if i + 1 < len(pieces) else '') for i in range(0, len(pieces), 2)]
        cur = ''
        for s in sents:
            if cur and len(cur) + len(s) + 1 > MAX_CHARS:
                out.append(('text', cur, gid)); cur = s
            else:
                cur = (cur + ' ' + s).strip()
        if cur:
            out.append(('text', cur, gid))
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
    base = ("把下面这段福特《路加福音讲义》的十九世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
            "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
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
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', b)).strip()


def run_section(n, resume, dry, publish, limit=0):
    bl = blocks(n)
    idx = [i for i, (k, _, _) in enumerate(bl) if k == 'text']
    todo = idx[:limit] if limit else idx
    keys = {tf.md5key(KEY_NS + T.mask(bl[i][1])[0]) for i in todo}
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    print(f'[{n}] 共 {len(bl)} 块，需翻译 {len(todo)} 段，已缓存 {hit}，待调用 {len(keys) - hit}，'
          f'约 {sum(len(bl[i][1]) for i in todo):,} 字符', flush=True)
    if dry:
        return len(keys) - hit, sum(len(bl[i][1]) for i in todo if not (CACHE / f'{tf.md5key(KEY_NS + T.mask(bl[i][1])[0])}.txt').exists())
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
        done[i] = T.unmask(translate_one(masked, resume, f'{n}#{c}', ctx), tags)
        if c % 10 == 0:
            print(f'  [{n}] {c}/{len(todo)} 段', flush=True)
    if limit:
        for i in sorted(done):
            print('-----', bl[i][1][:200], '\n=====', done[i][:600])
        return
    groups, order = {}, []
    for i, (k, b, gid) in enumerate(bl):
        if gid not in groups:
            groups[gid] = ''; order.append(gid)
        groups[gid] += done.get(i, b)
    body = '\n\n'.join(groups[g] for g in order)
    body, missing = T.annotate_terms(body, (SRC / f'lecture-{n}.md').read_text(encoding='utf-8'))
    if missing:
        print(f'    [names] {n}: 英文源里有 {missing}，译文里没有原名、也找不到已知中文写法，未自动补', flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{n}.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum((CACHE / f'{k}.txt').exists() for k in keys)
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    if str(n) not in meta or after > hit or not resume:
        meta[str(n)] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(n)


def autopublish(n):
    pub = ROOT / 'scripts' / 'publish_foote_zh.py'
    if not pub.exists():
        print('    [autopublish] publish_foote_zh.py 尚未就绪，只写 raw', flush=True)
        return
    try:
        r = subprocess.run([sys.executable, str(pub)], cwd=ROOT, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['foote/luke', 'foote_raw/luke/zh_chapters', 'foote_raw/luke/zh_cache', 'foote_raw/luke/zh_meta.json',
                 'foote_raw/luke/zh_translate_issues.log', 'foote_raw/luke/zh_italic_notes.log',
                 '_data/commentaries.yml', '_data/compare_sources.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(foote): 路加福音讲义中译 · 第 {n} 讲（自动发布）\n\n'
                            'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>', '--', *paths],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        if c.returncode == 0:
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
    secs = [str(c) for c in range(1, N_LECT + 1)] if a.all else a.section
    if not secs:
        ap.error('--section 或 --all')
    tot_calls = tot_chars = 0
    for s in secs:
        try:
            r = run_section(int(s), a.resume, a.dry_run, not a.no_publish, a.limit)
            if a.dry_run and r:
                tot_calls += r[0]; tot_chars += r[1]
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
