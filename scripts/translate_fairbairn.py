#!/usr/bin/env python3
"""translate_fairbairn.py —— 费尔贝恩《教牧书信》(爱丁堡 1874) 提摩太前书目录 → 中文 raw。

提前目录下放着：全书序言、导论四节（三卷共用）、提前「原文与译文」、提前第 1–6 章注释、附录 A–C（三卷共用）。
质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存、自动发布骨架全部复用 translate_alexander_acts（最新一套闸），
这里只换路径、缓存命名空间、提示词、分块与发布。CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

源取已发布的英文页 fairbairn/1timothy/<slug>.md：
  - 节首 `<b class="fb-ver">Vers. 1, 2.</b> <em>…</em>` 是**费尔贝恩自己的译文**（不是钦定本），照他的英文译出，不换和合本；
  - 「原文与译文」页：希腊文段（fb-gk）原样保留不送模型，只译他的英译（fb-en）；章标题程序换中文；
  - 缺文占位（fb-lost，本站英文页自己加的说明）程序换成中文说明，不送模型。

缓存  fairbairn_raw/pastoral/zh_cache/<md5>.txt   ← 必须保留
输出  fairbairn_raw/pastoral/zh_chapters/1timothy/<slug>.md ← 翻完 chmod 444
时刻  fairbairn_raw/pastoral/zh_meta.json        ← 键 1timothy/<slug>

用法：python3 -u scripts/translate_fairbairn.py --dry-run --all
      python3 -u scripts/translate_fairbairn.py --all --resume        # 单路
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
import translate_alexander_acts as T   # noqa: E402  复用全部质检闸与 run_section 骨架

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'fairbairn_raw' / 'pastoral'
CACHE = RAW / 'zh_cache'
# 卷由 --book 选（默认提前）；两卷可各开一路并行：译完时刻各记一个文件，免得两个进程同时改一个 json 互相覆盖
BOOK = '1timothy'
for _i, _a in enumerate(sys.argv):
    if _a == '--book' and _i + 1 < len(sys.argv):
        BOOK = sys.argv[_i + 1]
SRC = ROOT / 'fairbairn' / BOOK
OUT_DIR = RAW / 'zh_chapters' / BOOK
META = RAW / ('zh_meta.json' if BOOK == '1timothy' else f'zh_meta_{BOOK}.json')
KEY_NS = 'FAIRBAIRN_PASTORAL::'
MAX_CHARS = 3200

NCH = {'1timothy': 6, 'titus': 3, '2timothy': 4}[BOOK]
# 序言、导论、附录三卷共用，放在提前目录下，只随提前译
SLUGS = ((['preface'] + [f'introduction-{n}' for n in range(1, 5)] if BOOK == '1timothy' else []) + ['text']
         + [str(c) for c in range(1, NCH + 1)] + ([f'appendix-{L}' for L in 'abc'] if BOOK == '1timothy' else []))

SYSTEM = (
    "你是一位精通希腊文与改革宗解经传统的中文译者，正在翻译帕特里克·费尔贝恩（Patrick Fairbairn, 1805–1874，"
    "苏格兰自由教会神学家，格拉斯哥自由教会学院院长）的《教牧书信》（The Pastoral Epistles: The Greek Text and "
    "Translation, with Introduction, Expository Notes, and Dissertations，爱丁堡 1874）。\n"
    "此书体例：先有序言与导论（作者问题、写作时地、提摩太与提多生平），再给希腊原文与他自己的英译，"
    "然后逐节注释：每段先用斜体引出他自己译的经文（Vers. 1, 2. *Paul, an apostle…*），再辨析希腊文词义、语法、异文，"
    "评述德、英各家解经（Huther、De Wette、Ellicott、Alford 等），并论教会职分、异端、敬虔等题目；书末有几篇附录专论。"
    "文风是十九世纪苏格兰的学术散文，论证严谨、句子长而层次分明。"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系不能丢。"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标签（节号、锚点、粗体外壳等），**必须原样逐个保留**，个数、先后都与原文一致\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。斜体多是他所讲解的经文字词、他自己的译法、书名、外文词。"
    "中文里对应的部分照样用 `*` 包起来，一处对一处，不要并、不要增，不要只包一个字或标点\n"
    "4. **节首斜体与他所引的「他自己的译法」照他的英文译出，不要换成和合本**——那是他要辨析的东西；"
    "他引用别处经文（引号里的整句，不是他在讨论的本段译法）时照抄和合本；只给出处的只译出处，不补经文\n"
    "5. 经文出处：书卷名换和合本全称，章节数字照原样（Romans 1:1 → 罗马书 1:1；1Co 1:1 → 哥林多前书 1:1；"
    "2 Timothy 3:16 → 提摩太后书 3:16；Titus 2:10 → 提多书 2:10）；`Vers. 1, 2.` / `Ver. 8.` → 第 1、2 节 / 第 8 节；"
    "`ver. 5` → 第 5 节；`chap. 3` → 第 3 章；`p. 85` / `pp. 85–86` → 第 85 页 / 第 85–86 页；"
    "`comp.` / `cf.` → 参；`ib.` / `ibid.` → 同上；`l.c.` → 同前引处\n"
    "6. 希腊文、希伯来文、拉丁文、德文**逐字照抄，一个字母、一个重音符号都不许改**，"
    "**原文里没有的希腊文、希伯来文一个字母也不许添**——专名括注只写英文原名，不写希腊文写法；不替原文补词尾、冠词、介词。"
    "希腊词后用圆括号附中文译义，如 πιστὸς ὁ λόγος（这话是可信的）；整句拉丁、德文引文保留原文，括注中文大意\n"
    "7. `&c.` → ……（不作「等等」）；`i.e.` → 即；`e.g.` → 例如；`viz.` → 即\n"
    "8. **凡音译出来的人名、地名、学派与教派名、书名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "胡特尔（Huther）、德威特（De Wette）、埃利科特（Ellicott）、阿尔福德（Alford）、维辛格（Wiesinger）、"
    "鲍尔（Baur）、施莱尔马赫（Schleiermacher）、金口约翰（Chrysostom）、狄奥多勒（Theodoret）、哲罗姆（Jerome）、"
    "奥古斯丁（Augustine）、加尔文（Calvin）、诺斯底派（Gnostics）、马吉安（Marcion）。"
    "和合本里本来就有的圣经人名地名（提摩太、提多、以弗所、革哩底、许米乃、亚历山大）不括注。英文原文没写的原名不要补，不要编\n"
    "9. 术语全书一律、互不撞词：bishop / overseer（ἐπίσκοπος）→ 监督；pastor（他用来译 ἐπίσκοπος 时）→ 牧者；"
    "presbyter / elder → 长老；deacon → 执事；deaconess → 女执事；widow → 寡妇；"
    "the church → 教会；office → 职分；ordination → 按立；laying on of hands → 按手；"
    "godliness（εὐσέβεια）→ 敬虔；sound doctrine → 纯正的道理；faithful saying → 可信的话；"
    "heresy / heretic → 异端 / 异端分子；Gnosticism → 诺斯底主义；asceticism → 禁欲主义；"
    "the Pastoral Epistles → 教牧书信；apostle / apostolic → 使徒 / 使徒的；grace → 恩典；faith → 信心；"
    "salvation / Saviour → 救恩 / 救主；mediator → 中保；from everlasting → 从亘古（「亘」不可写作「亡」）；"
    "Arminian → 阿民念派\n"
    "10. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "11. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的希腊拉丁德文除外）"
)

# 复用的闸与骨架读模块全局：改指到本书
T.SRC, T.RAW, T.OUT_DIR, T.CACHE, T.META, T.KEY_NS = SRC, RAW, OUT_DIR, CACHE, META, KEY_NS
T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED = RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt'

CN_NUM = '〇一二三四五六'
LOST_ZH = '<p class="fb-lost"><b class="fb-ver">第 {v} 节</b>　本节注释（原书第 {pp} 页）在本站所据的录入本中缺失。</p>'


def body_of(slug: str) -> str:
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    t = t.split('\n---\n', 1)[1].strip()
    t = re.sub(r'<em>\s*([^<>]*?)\s*</em>', r'*\1*', t)      # 斜体转星号，模型按星号对位（发布时转回）
    return t


def units_of(slug: str):
    out = []
    for block in body_of(slug).split('\n\n'):
        b = block.strip()
        if not b:
            continue
        m = re.match(r'<p class="fb-lost"><b class="fb-ver">Vers?\. (\d+)\.</b>.*?pp?\. ([\d–-]+)\).*</p>$', b, re.S)
        if m:
            out.append(('keep', LOST_ZH.format(v=m.group(1), pp=m.group(2))))
            continue
        if b.startswith('<div class="fb-par"'):        # 原文与译文：一章一块，希腊文保留，只译英译
            for ln in b.split('\n'):
                h = re.match(r'<h3>CHAPTER ([IVX]+)</h3>$', ln)
                if h:
                    out.append(('keep', f'<h3>第{_cn(_roman(h.group(1)))}章</h3>'))
                elif ln.startswith('<div class="fb-en">'):
                    out.append(('text', ln))
                else:
                    out.append(('keep', ln))
            continue
        out.append(('keep' if T.is_keep_block(b) else 'text', b))
    return out


def _roman(s):
    v = {'I': 1, 'V': 5, 'X': 10}
    return sum(-v[a] if b != ' ' and v.get(b, 0) > v[a] else v[a] for a, b in zip(s, s[1:] + ' '))


def _cn(n):
    return CN_NUM[n] if n < 7 else str(n)


def chunks(units):
    """太长的段按句切块（缓存键按块），译完拼回。返回 [(kind, text, gid)]，同 gid 拼接不加分隔。"""
    out = []
    for gid, (k, b) in enumerate(units):
        if k != 'text' or len(b) <= MAX_CHARS:
            out.append((k, b, gid))
            continue
        pieces = re.split(r'([.?!][”"’)]?)\s+(?=[“"A-Z(<⟦*])', b)
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


def translate_one(text: str, resume: bool, label: str) -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not T.structural_diff(text, cached) or key in T.accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {T.structural_diff(text, cached)[:90]}', flush=True)
    base = ("把下面这段费尔贝恩《教牧书信》的十九世纪英文译成简体中文。"
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


def run_section(slug: str, resume: bool, dry: bool, publish: bool) -> int:
    units = units_of(slug)
    ch = chunks(units)
    todo = [(i, b) for i, (k, b, _) in enumerate(ch) if k == 'text']
    keys = {tf.md5key(KEY_NS + T.mask(b)[0]) for _, b in todo}
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    print(f'[{slug}] 共 {len(units)} 块（切成 {len(ch)}），需翻译 {len(todo)} 段，已缓存 {hit}，'
          f'待调用 {len(keys) - hit}，约 {sum(len(b) for _, b in todo):,} 字符', flush=True)
    if dry:
        return 0
    done = {}
    for n, (i, b) in enumerate(todo, 1):
        masked, tags = T.mask(b)
        done[i] = T.unmask(translate_one(masked, resume, f'{slug}#{n}'), tags)
        if n % 10 == 0:
            print(f'  [{slug}] {n}/{len(todo)} 段', flush=True)
    joiner = '\n' if slug == 'text' else '\n\n'
    groups, order = {}, []
    for i, (k, b, gid) in enumerate(ch):
        if gid not in groups:
            groups[gid] = ''; order.append(gid)
        groups[gid] += done.get(i, b)
    body = joiner.join(groups[g] for g in order)
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
    key = f'{BOOK}/{slug}'
    if key not in meta or after > hit or not resume:
        meta[key] = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
        META.write_text(json.dumps(meta, ensure_ascii=False, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)
    if publish:
        autopublish(slug)
    return 1


def autopublish(slug: str) -> None:
    """译完一篇立刻发布 + commit + push；只提交本书路径。失败只告警，不中断翻译。"""
    try:
        r = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'publish_fairbairn_zh.py')], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print(f'    [autopublish] 发布失败 {r.stderr[-300:]}', flush=True)
            return
        paths = ['fairbairn', 'fairbairn_raw/pastoral/zh_chapters', 'fairbairn_raw/pastoral/zh_cache',
                 'fairbairn_raw/pastoral/zh_meta.json', f'fairbairn_raw/pastoral/zh_meta_{BOOK}.json',
                 'fairbairn_raw/pastoral/en_meta.json',
                 'fairbairn_raw/pastoral/zh_translate_issues.log', '_data/commentaries.yml', '_data/compare_sources.yml']
        paths = [p for p in paths if (ROOT / p).exists()]
        subprocess.run(['git', 'add', '--', *paths], cwd=ROOT, check=False, timeout=120)
        bk = {'1timothy': '提前', 'titus': '提多', '2timothy': '提后'}[BOOK]
        c = subprocess.run(['git', 'commit', '-q', '-m', f'feat(fairbairn): 教牧书信中译 · {bk} {slug}（自动发布）\n\n'
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
    ap.add_argument('--book', default='1timothy', choices=['1timothy', 'titus', '2timothy'])
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    slugs = SLUGS if a.all else a.section
    if not slugs:
        ap.error('--section 或 --all')
    for s in slugs:
        try:
            run_section(s, a.resume, a.dry_run, not a.no_publish)
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
