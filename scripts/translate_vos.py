#!/usr/bin/env python3
"""translate_vos.py —— 霍志恒（Geerhardus Vos）"Eschatology of the Psalter"（PTR 18, 1920）英文 → 中文 raw。

质检闸、<译文> 标签、占位符遮盖、严重问题不入缓存等机制全部复用 translate_alexander_acts（← candlish ← …）：
这里只换路径、缓存命名空间、提示词与分块。CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，
自动带 --safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

源取已校定发布的英文页 vos/psalter/index.md：
  - 正文段落太长的按句切成 ≤ MAX_CHARS 的块，译完按原段拼回（中文不加空格）；
  - 脚注 `[^n]: …` 一条一块，`[^n]:` 前缀不送模型；正文里的注号 `[^n]` 与页码锚点、希伯来文外壳都遮成 ⟦N⟧；
  - 经文出处的罗马数字章号先由程序转成阿拉伯数字（Ps. xlvi. 10 → Ps. 46:10），模型只管把书卷名译成和合本书名。

缓存  vos_raw/psalter/zh_cache/<md5>.txt   ← 必须保留
输出  vos_raw/psalter/zh_chapters/index.md ← 翻完 chmod 444
时刻  vos_raw/psalter/zh_meta.json

用法：python3 -u scripts/translate_vos.py --dry-run
      python3 -u scripts/translate_vos.py --resume            # 单路
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
import translate_alexander_acts as T   # noqa: E402  复用全部质检闸

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'vos' / 'psalter' / 'index.md'
RAW = ROOT / 'vos_raw' / 'psalter'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'
META = RAW / 'zh_meta.json'
KEY_NS = 'VOS_PSALTER::'
MAX_CHARS = 2600

# 复用的闸函数读模块全局：改指到本书
T.CACHE, T.BAD_LOG, T.ITALIC_LOG, T.ACCEPTED, T.KEY_NS, T.RAW = (
    CACHE, RAW / 'zh_translate_issues.log', RAW / 'zh_italic_notes.log', RAW / 'zh_accepted.txt', KEY_NS, RAW)
# 注号 [^n] 也遮成占位符
T.RE_ANY = re.compile(r'\[\^\d+\]|' + T.RE_ANY.pattern)

SYSTEM = (
    "你是一位精通希伯来文、德文与改革宗神学的中文译者，正在翻译霍志恒（Geerhardus Vos, 1862–1949，"
    "普林斯顿神学院首任圣经神学教授）的长文《诗篇的末世论》（Eschatology of the Psalter，"
    "《普林斯顿神学评论》1920 年 1 月）。\n"
    "此文是专题论文，不是逐节注释：先论诗篇是以色列对神作为的「主观回应」，故必有末世盼望；"
    "再逐一检讨威尔豪森学派、衮克尔与格雷斯曼学派、「集体解释」等批判学说对诗篇末世论与弥赛亚诗篇的处理；"
    "最后讲诗篇末世论对当时教会的教训。脚注多引德文著作。"
    "文风是二十世纪初普林斯顿的学术散文，句子长、论证层层推进、用词精确。"
    "译文要沉稳、准确、读得懂：先求意思对，再求通顺，最后才是文气；长句可以拆，但逻辑关系（因果、让步、转折）不能丢。"
    "不要译成佶屈聱牙的欧化长句，也不要冲淡成通俗读物。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 形如 ⟦3⟧ 的占位符代表排版标记（脚注注号、原刊页码锚点、希伯来文外壳），**必须原样逐个保留**，"
    "个数、先后都与原文一致；注号紧跟在它所注的那个词或那句话后面，页码锚点放在对应位置\n"
    "3. 星号 `*` 是斜体标记，开合各一个、必须成对。斜体多是书名、刊名或拉丁、德文词语；"
    "中文里对应的部分照样用 `*` 包起来，一处对一处，不要并、不要增\n"
    "4. 原文引用经文（引号里的整句）一律照抄和合本，神的名 Jehovah 照和合本作「耶和华」；"
    "只给出处、没有引经文的，只译出处，不要自己补经文\n"
    "5. 经文出处已转成阿拉伯数字（Ps. 46:10；Pss. 20:7; 44:6），只把书卷名换成和合本全称："
    "Ps./Pss. → 诗篇；Isa. → 以赛亚书；Jer. → 耶利米书；Hab. → 哈巴谷书；Mic. → 弥迦书；Am. → 阿摩司书；"
    "Ex. → 出埃及记；Gen. → 创世记；2 Sam. → 撒母耳记下；1 Kings / 2 Kings → 列王纪上 / 列王纪下；"
    "Mk. → 马可福音；Rom. → 罗马书；2 Cor. → 哥林多后书；Gal. → 加拉太书；1 Thess. → 帖撒罗尼迦前书；Rev. → 启示录。"
    "冒号、逗号、分号、连字号照原样（诗篇 20:7；44:6），不要改写成「第几篇第几节」。"
    "`vs. 7-20` → 第 7–20 节；`p. 344` / `pp. 344, 387` → 第 344 页 / 第 344、387 页；`note 2` → 注 2；"
    "`ff.` → 以下；`cfr.` → 参；`ibid.` → 同上；`a. o.` → 等；`vol.` → 卷\n"
    "6. 希伯来文、拉丁文、德文**逐字照抄**，一个字母、一个变音符号都不许改，**原文里没有的希伯来文、希腊文一个字母也不许添**；"
    "拉丁短语与德文引句后用圆括号附中文意译，如 in theatro mundi（在世界的舞台上）。"
    "德文书名、刊名照抄原文并保留斜体，不译；作者名照第 7 条处理\n"
    "7. **凡音译出来的人名、学派名，每段首次出现都要括注原名（照本段英文的拼法）**："
    "威尔豪森（Wellhausen）、衮克尔（Gunkel）、格雷斯曼（Gressmann）、切恩（Cheyne）、施塔德（Stade）、"
    "塞林（Sellin）、贝特根（Baethgen）、斯门德（Smend）、罗伊（Roy）、比尔（Beer）。"
    "和合本里本来就有的圣经人名（大卫、亚萨、以探、马利亚）不括注。英文原文没写的原名不要补，不要编\n"
    "8. 术语全篇一律、互不撞词：eschatology → 末世论；eschatological → 末世的（作形容词）/ 末世论的（指学说时）；"
    "the Psalter → 诗篇（指全书）；a Psalm → 一篇诗；the Psalmist(s) → 诗人；"
    "redemption → 救赎；redemptive → 救赎的；consummation → 终末的成全；"
    "Messiah / Messianic → 弥赛亚 / 弥赛亚的；the Anointed (of Jehovah) → （耶和华的）受膏者；kingship → 王权；King-Psalms → 君王诗；"
    "theophany → 神的显现；theocentric → 以神为中心的；collective / collectivistic → 集体的 / 集体主义的；"
    "the congregation of Israel → 以色列会众；criticism / critics → 批判学 / 批判学者；exilic / post-exilic / pre-exilic → 被掳时期的 / 被掳后的 / 被掳前的；"
    "piety → 敬虔；devotion / devotional → 灵修 / 灵修的；objective / subjective → 客观的 / 主观的；"
    "covenant of works → 行为之约；diatheke → diatheke（约）；the Church → 教会；from everlasting → 从亘古（「亘」不可写作「亡」）\n"
    "9. 称神、基督、圣灵的代词一律用「他」（和合本体例），不用「祂」\n"
    "10. **不得把任何英文词原样留在中文句子里**（专名后括注的原名、照抄的德文拉丁书名除外）"
)

ROMAN = {'i': 1, 'v': 5, 'x': 10, 'l': 50, 'c': 100}


def roman(s: str) -> int:
    n = 0
    for a, b in zip(s, s[1:] + ' '):
        v = ROMAN[a]
        n += -v if b in ROMAN and ROMAN[b] > v else v
    return n


BOOK = r'(?:Psalms|Pss|Ps|Isa|Jer|Hab|Mic|Am|Ex|Gen|Sam|Kings|Mk|Rom|Cor|Gal|Thess|Rev)\.?'
RE_BOOK = re.compile(rf'\b(?:{BOOK}|Dan\.)(?=\s)'
                     # 不带书卷名的出处串（本文里都是诗篇）：从第一个「罗马数字. 节号」或「罗马数字 ;」起
                     r'|(?<![A-Za-z])(?=(?:[ivxlc]{2,}|[vx])\.\s*\d)|(?<=following: )(?=[ivxlc]+;)')
# 出处串里的一项：罗马数字章号（后跟 . 或 , 或串尾），可带节号（7 / 5-8 / 4, 5 / 47 ff.）
RE_RITEM = re.compile(r'([ivxlc]+)(?:\.|,(?=\s*\d))?(?![A-Za-z])((?:\s*\d+(?:\s*-\s*\d+)?(?:\s*,\s*\d+(?:\s*-\s*\d+)?)*)(?:\s*ff\.)?)?')
RE_RSEP = re.compile(r'\s*(?:;|,|\band\b|\bcfr\.|\([^()]{1,40}\))\s*')


def arabic_refs(t: str) -> str:
    """书卷缩写后的一串罗马数字章号转阿拉伯数字：Pss. xx. 7; xliv. 6 → Pss. 20:7; 44:6。
    逐项扫：项之间只认 ; , and cfr.，碰到别的词即止（cfr 的 c、vs. 的 v 不当罗马数字）。"""
    out, pos = [], 0
    for m in RE_BOOK.finditer(t):
        if m.start() < pos:
            continue
        out.append(t[pos:m.end()])
        k = m.end()
        while True:
            ws = re.match(r'\s+', t[k:])
            k2 = k + (ws.end() if ws else 0)
            it = RE_RITEM.match(t, k2)
            if not it or not re.fullmatch(r'[ivxlc]+', it.group(1)) or it.end() == k2:
                break
            ch = roman(it.group(1)); vs = (it.group(2) or '').strip()
            out.append(t[k:k2] + (f'{ch}:{vs}' if vs else f'{ch}'))
            k = it.end()
            # 原书句点：章号后若无节号，保留原来的 . （句末或 Ps. xxiv. this…）
            if not vs and t[it.start(1) + len(it.group(1)):it.start(1) + len(it.group(1)) + 1] == '.' and not re.match(r'\s*(?:;|,|and\b)', t[k:]):
                out.append('.')
            e = k                                   # 连续的分隔成分：「; cfr.」「 (but cfr. v. 16);」
            while True:
                sep = RE_RSEP.match(t, e)
                if not sep or sep.end() == e:
                    break
                e = sep.end()
            if e == k or not re.match(r'[ivxlc]+(?:[.,;\s]|$)', t[e:]):
                break
            out.append(t[k:e]); k = e
        pos = k
    out.append(t[pos:])
    t = ''.join(out)
    for x, y in REF_FIXUPS:                         # 扫描器接不上的个别写法
        t = t.replace(x, y)
    return t


# 规则扫不到、硬扫又容易误伤的三处，逐条列明（照原刊读定的章号）
REF_FIXUPS = [
    ('such Psalms as ii. and cx. to', 'such Psalms as 2 and 110 to'),
    ('89:38. 51; cx; cxxxii.', '89:38. 51; 110; 132.'),
]


def blocks():
    """→ [(kind, text, para_id)]；kind: text / keep / note。长段按句切块，同一段的块共用 para_id。"""
    t = SRC.read_text(encoding='utf-8').split('---', 2)[2].strip()
    out = []
    for pid, b in enumerate(t.split('\n\n')):
        b = b.strip()
        if not b:
            continue
        if b.startswith('<div class="vs-source"') or b.startswith('<p class="vs-sign"'):
            out.append(('keep', b, pid))
            continue
        if b.startswith('[^'):                      # 脚注区：一行一条
            for ln in b.split('\n'):
                m = re.match(r'(\[\^\d+\]:) (.*)', ln)
                out.append(('note', m.group(1) + ' ' + arabic_refs(m.group(2)), f'n{m.group(1)}'))
            continue
        b = arabic_refs(b)
        if len(b) <= MAX_CHARS:
            out.append(('text', b, pid))
            continue
        pieces = re.split(r'([.?!][”"’]?)\s+(?=[“"A-Z⟦<])', b)
        sents = [pieces[k] + (pieces[k + 1] if k + 1 < len(pieces) else '') for k in range(0, len(pieces), 2)]
        cur = ''
        for s in sents:
            if cur and len(cur) + len(s) + 1 > MAX_CHARS:
                out.append(('text', cur, pid)); cur = s
            else:
                cur = (cur + ' ' + s).strip()
        if cur:
            out.append(('text', cur, pid))
    return out


def translate_one(text: str, resume: bool, label: str) -> str:
    key = tf.md5key(KEY_NS + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not T.structural_diff(text, cached) or key in T.accepted_keys():
            return cached
        print(f'    [cache-reject] {label}: {T.structural_diff(text, cached)[:90]}', flush=True)
    base = ("把下面这段霍志恒《诗篇的末世论》的英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；逐一保留 `*` 斜体标记与 ⟦N⟧ 占位符；"
            "把译文完整放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n")
    out = T.fix_italics(T.restore_greek(T.tidy(T.take_tagged(tf.call_claude(base + text, timeout=900, label=label))), text),
                        text, label)
    diff = T.structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n重译下面这段。**必须逐一保留** ⟦N⟧ 占位符（个数与先后都要对上）；"
               "希伯来文逐字照抄、原文没有的不许添；**不得把任何英文词原样留在中文句子里**。"
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--limit', type=int, default=0, help='只译前 N 块（试译用）')
    a = ap.parse_args()
    tf.SYSTEM = SYSTEM
    bl = blocks()
    todo = [(i, b) for i, b in enumerate(bl) if b[0] in ('text', 'note')]
    if a.limit:
        todo = todo[:a.limit]
    keys = [tf.md5key(KEY_NS + T.mask(b[1] if b[0] == 'text' else b[1].split(' ', 1)[1])[0]) for _, b in todo]
    hit = sum((CACHE / f'{k}.txt').exists() for k in keys)
    chars = sum(len(b[1]) for _, b in todo)
    print(f'[vos] 共 {len(bl)} 块，需翻译 {len(todo)} 块（正文 {sum(b[0]=="text" for _, b in todo)}、'
          f'脚注 {sum(b[0]=="note" for _, b in todo)}），已缓存 {hit}，约 {chars:,} 字符', flush=True)
    if a.dry_run:
        return
    zh = {}
    for n, (i, (kind, text, pid)) in enumerate(todo, 1):
        if kind == 'note':
            pre, body = text.split(' ', 1)
        else:
            pre, body = '', text
        masked, tags = T.mask(body)
        try:
            z = T.unmask(translate_one(masked, a.resume, f'vos#{n}'), tags)
        except T.SevereTranslation as e:
            print(f'⛔ [vos#{n}] 重试后仍不合格，不写出、不发布：{e}', flush=True)
            sys.exit(3)
        except RuntimeError as e:
            if 'limit' in str(e).lower():
                print(f'⛔ 额度用尽，中止：{e}', flush=True)
                sys.exit(42)
            raise
        zh[i] = (pre + ' ' + z) if pre else z
        if n % 10 == 0:
            print(f'  [vos] {n}/{len(todo)} 块', flush=True)
    if a.limit:
        for i in sorted(zh):
            print('-----', bl[i][1][:160], '\n=====', zh[i][:400])
        return
    # 拼回：同段的块直接相连；段与段空行；脚注逐行
    parts, prev_pid, notes = [], None, []
    for i, (kind, text, pid) in enumerate(bl):
        piece = zh.get(i, text)
        if kind == 'note':
            notes.append(piece)
        elif pid == prev_pid:
            parts[-1] += piece
        else:
            parts.append(piece)
        prev_pid = pid
    body = '\n\n'.join(parts) + ('\n\n' + '\n'.join(notes) if notes else '')
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / 'index.md'
    if dst.exists():
        os.chmod(dst, 0o644)
    dst.write_text(body + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)
    stamp = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    META.write_text(json.dumps({'index': stamp}, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)


if __name__ == '__main__':
    main()
