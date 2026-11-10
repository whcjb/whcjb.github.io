#!/usr/bin/env python3
"""translate_haldane.py —— 霍尔丹《罗马书释义》英文版 haldane/romans/<章>.md → 中文 raw。

质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存全部复用 translate_alexander_acts（最新一套闸，含 2026-11-10
修的截断判据、罗马数字放行、希腊词怪字符还原）。CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

与费尔贝恩不同：霍尔丹节首引的是**钦定本经文**（不是他自己的译法）→ 节首经文由程序填和合本该节（assets/cuv.json），
不送模型；「Ver. 1.」→「第 1 节」。章首概述、注释段落、脚注逐段送模型；长段按句切块（MAX_CHARS）。
录入本缺正文的脚注说明（hd-fnmiss）程序换中文，不送模型。

缓存  haldane_raw/romans/zh_cache/<md5>.txt   ← 必须保留
输出  haldane_raw/romans/zh_chapters/<章>.md  ← 翻完 chmod 444
时刻  haldane_raw/romans/zh_meta.json

用法：python3 -u scripts/translate_haldane.py --dry-run --all
      python3 -u scripts/translate_haldane.py --section 13 --resume      # 单路；自动发布
      python3 -u scripts/translate_haldane.py --section 1 --limit 3      # 试译前 3 段，只打印不写出
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
SRC = ROOT / 'haldane' / 'romans'
RAW = ROOT / 'haldane_raw' / 'romans'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'HALDANE_ROMANS::'
MAX_CHARS = 3200

T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'
T.RE_ANY = re.compile(r'\[\^f\d+\]|' + T.RE_ANY.pattern)        # 脚注号也遮

SYSTEM = (
    "你是一位精通希腊文与改革宗神学的中文译者，正在翻译罗伯特·霍尔丹（Robert Haldane, 1764–1842，苏格兰平信徒宣教家）"
    "的《罗马书释义》（Exposition of the Epistle to the Romans，1835–1839，附对麦克奈特、斯图尔特、托卢克三家注释的评论）。\n"
    "此书体例：每章先有章首概述，再逐节讲解。讲解重教义、重应用，常辨析希腊文词义，并屡屡驳斥当时的新派释经"
    "（斯图尔特 Moses Stuart、托卢克 Tholuck、麦克奈特 Macknight，以及苏西尼派、阿民念派）。"
    "文风是十九世纪苏格兰的讲道式学术散文，句子长、论证层层推进、语气庄重而热切。"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系不能丢。"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签或脚注号，**必须原样逐个保留**，个数、先后都与原文一致；脚注号紧跟它所注的词句\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。斜体多是他所讲解的经文字词、书名、外文词；中文对应部分照样用 `*` 包，"
    "一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. 他引用经文（引号里的整句或斜体经文字词）一律照抄和合本措辞；只给出处、没有引经文的，只译出处，不补经文\n"
    "5. 经文出处：书卷名换和合本全称，章节数字照原样（Romans 3:21 → 罗马书 3:21；Acts 13:9 → 使徒行传 13:9；"
    "1 Corinthians 9:1 → 哥林多前书 9:1）；`ver. 5` / `verse 5` → 第 5 节；`chap. 3` → 第 3 章\n"
    "6. 希腊文、希伯来文、拉丁文**逐字照抄，一个字母、一个重音符号都不许改**，**原文里没有的希腊文、希伯来文一个字母也不许添**；"
    "希腊词后用圆括号附中文译义，如 δικαιοσύνη θεοῦ（神的义）；整句拉丁引文保留原文，括注中文大意\n"
    "7. `&c.` → ……（不作「等等」）；`i.e.` → 即；`e.g.` → 例如；`viz.` → 即\n"
    "8. **凡音译出来的人名、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "斯图尔特（Mr. Stuart）、托卢克（Mr. Tholuck）、麦克奈特（Dr. Macknight）、加尔文（Calvin）、路德（Luther）、"
    "奥古斯丁（Augustine）、苏西尼派（Socinians）、阿民念派（Arminians）、伯拉纠派（Pelagians）。"
    "和合本里本来就有的圣经人名地名不括注。英文原文没写的原名不要补，不要编\n"
    "9. 术语全书一律、互不撞词：justification / justify → 称义 / 称……为义；righteousness of God → 神的义；"
    "righteousness → 义；imputation / impute → 归算 / 归给；faith → 信心；grace → 恩典；the law → 律法；"
    "works → 行为；sin / sinner → 罪 / 罪人；atonement → 赎罪；propitiation → 挽回祭；redemption → 救赎；"
    "election / the elect → 拣选 / 选民；predestination → 预定；sanctification → 成圣；adoption → 儿子的名分；"
    "covenant of works → 行为之约；federal head / representative → 代表元首 / 代表；original sin → 原罪；"
    "the Gospel → 福音；the Apostle → 使徒（指保罗）；Socinian → 苏西尼派；neology / neologian → 新派神学 / 新派神学家；"
    "from everlasting → 从亘古（「亘」不可写作「亡」）；Arminian → 阿民念派\n"
    "10. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "11. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的希腊拉丁文除外）"
)

MISSING_ZH = '<span class="hd-fnmiss">此条脚注的正文，本站所据录入本缺（原书有）。</span>'
_CUVD = None


def cuv(ch, v):
    global _CUVD
    if _CUVD is None:
        _CUVD = json.loads((ROOT / 'assets' / 'cuv.json').read_text(encoding='utf-8'))
    return _CUVD['45'][str(ch)][str(v)]


RE_LEMMA = re.compile(r'^<b class="hd-ver">Vers?\. (\d+)(?:–(\d+))?\.</b>(?: <em>.*</em>)?$')


def blocks(ch):
    """→ [(kind, text, gid)]。kind: text（送模型）/ keep（原样或程序填好）。同 gid 的块拼回时直接相连。"""
    t = (SRC / f'{ch}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1].strip()
    t = re.sub(r'<em>([^<>]*)</em>', r'*\1*', t)             # 斜体转星号，模型按星号对位
    out = []
    for gid, b in enumerate(t.split('\n\n')):
        b = b.strip()
        if not b:
            continue
        lines = b.split('\n')
        # 节首经文：`<b class="hd-ver">Ver. 1.</b> *…*` + `{: .hd-lemma}` → 和合本
        m = RE_LEMMA.match(re.sub(r'\*([^*]*)\*', r'<em>\1</em>', lines[0]))
        if m and len(lines) == 2 and lines[1].startswith('{:'):
            v1, v2 = int(m.group(1)), int(m.group(2) or m.group(1))
            lab = f'第 {v1} 节' if v1 == v2 else f'第 {v1}–{v2} 节'
            vs = [cuv(ch, v1)] + [f'{v} {cuv(ch, v)}' for v in range(v1 + 1, v2 + 1)]
            out.append(('keep', f'<b class="hd-ver">{lab}</b> *{" ".join(vs)}*\n{lines[1]}', gid))
            continue
        if b == 'Introduction\n{: .hd-intro-h}':
            out.append(('keep', '章首概述\n{: .hd-intro-h}', gid))
            continue
        fn = re.match(r'^(\[\^f\d+\]:) (.*)$', b, re.S)
        if fn:
            body = fn.group(2)
            if 'hd-fnmiss' in body:
                out.append(('keep', f'{fn.group(1)} {MISSING_ZH}', gid))
            else:
                out.append(('text', b, gid))
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


def translate_one(text, resume, label):
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not T.structural_diff(text, cached) or key in T.accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {T.structural_diff(text, cached)[:90]}', flush=True)
    base = ("把下面这段霍尔丹《罗马书释义》的十九世纪英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
            "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    out = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(tf.call_claude(base + text, timeout=900, label=label))), text),
                        text, label)
    diff = T.structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** ⟦N⟧ 占位符（个数与先后都要对上）；"
               "希腊文逐字照抄、原文没有的不许添；**不得把任何英文词原样留在中文句子里**。"
               "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
        for n in (1, 2):
            out2 = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(tf.call_claude(fix + text, timeout=900, label=f'{label}·retry{n}'))), text),
                                 text, f'{label}·retry{n}')
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


def run_section(ch, resume, dry, publish, limit=0):
    bl = blocks(ch)
    todo = [(i, b) for i, (k, b, _) in enumerate(bl) if k == 'text']
    if limit:
        todo = todo[:limit]
    def payload(b):
        m = re.match(r'^(\[\^f\d+\]:) (.*)$', b, re.S)
        return (m.group(1) + ' ', m.group(2)) if m else ('', b)
    keys = {tf.md5key(KEY_NS + T.mask(payload(b)[1])[0]) for _, b in todo}
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    print(f'[{ch}] 共 {len(bl)} 块，需翻译 {len(todo)} 段，已缓存 {hit}，待调用 {len(keys) - hit}，'
          f'约 {sum(len(b) for _, b in todo):,} 字符', flush=True)
    if dry:
        return
    done = {}
    for n, (i, b) in enumerate(todo, 1):
        pre, body = payload(b)
        masked, tags = T.mask(body)
        done[i] = pre + T.unmask(translate_one(masked, resume, f'{ch}#{n}'), tags)
        if n % 10 == 0:
            print(f'  [{ch}] {n}/{len(todo)} 段', flush=True)
    if limit:
        for i in sorted(done):
            print('-----', bl[i][1][:200], '\n=====', done[i][:500])
        return
    groups, order = {}, []
    for i, (k, b, gid) in enumerate(bl):
        if gid not in groups:
            groups[gid] = ''; order.append(gid)
        groups[gid] += done.get(i, b)
    body = '\n\n'.join(groups[g] for g in order)
    body, missing = T.annotate_terms(body, (SRC / f'{ch}.md').read_text(encoding='utf-8'))
    if missing:
        print(f'    [names] {ch}: 英文源里有 {missing}，译文里没有原名、也找不到已知中文写法，未自动补', flush=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{ch}.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    after = sum((CACHE / f'{k}.txt').exists() for k in keys)
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    if str(ch) not in meta or after > hit or not resume:
        meta[str(ch)] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(ch)


def autopublish(ch):
    try:
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_haldane_zh.py')], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['haldane', 'haldane_raw/romans/zh_chapters', 'haldane_raw/romans/zh_cache', 'haldane_raw/romans/zh_meta.json',
                 'haldane_raw/romans/en_meta.json', 'haldane_raw/romans/zh_translate_issues.log',
                 '_data/commentaries.yml', '_data/compare_sources.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(haldane): 罗马书释义中译 · 第 {ch} 章（自动发布）\n\n'
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
    secs = [str(c) for c in range(1, 17)] if a.all else a.section
    if not secs:
        ap.error('--section 或 --all')
    for s in secs:
        try:
            run_section(int(s), a.resume, a.dry_run, not a.no_publish, a.limit)
        except T.SevereTranslation as e:
            print(f'⛔ [{s}] 有段落重试后仍不合格，本篇不写出、不发布：{e}', flush=True)
            sys.exit(3)
        except RuntimeError as e:
            if 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)
            raise


if __name__ == '__main__':
    main()
