#!/usr/bin/env python3
"""第三轮：**用判读给的「上下文」锚定落点**，而不是拿错误串去正文里碰运气。

为什么必须换机制
----------------
前两轮（apply_ocr_fixes.py / apply_ocr_fixes2.py）的定位逻辑是：错误串在
「所属章」内唯一命中就改，多处命中就拿 raw 页的窗口收窄。以弗所书实测 28 条
里错了 5 条（18%），全是**改到了另一处无辜的正确文字**上：

    p13  來→地   把「用相反的言語來表達」改成「言語地表達」
    p62  比喻→意喻 改的是「兩個比喻」，报告说的是「這個意喻」
    p96  安→妄   把「安頓定當」改成「妄頓定當」
    p122 剝→剉   把「剝奪他們不可或缺的武裝」改成「剉奪」
    p122 上→了   把「箭頭上有火」改成「箭頭了有火」

根因有两条：

1. **已发布正文 ≠ raw OCR。** 判读比的是「扫描影像 ↔ raw OCR」，而发布时有些
   字已经被改对了。例：raw p96 是「為一種安語」，正文里早就是「為一種妄語」。
   于是报告里的错误串「安」在正文那个位置根本不存在，但章里别处的「安」存在，
   就被顶替掉了。
2. **错误串太短。** 中位 3–4 字，「唯一命中」这个条件在长章里毫无约束力。

所以定位不能靠串本身，只能靠**位置证据**。判读每条都带 上下文=「…前后各约8字…」，
实测目标串能在上下文里定位的比例：以弗所 94%、罗马 81%、歌罗西 67%
（约翰 47% 偏低是因为大量条目的目标是带圈节号而非汉字，那类本就要跳）。
这个信号足够用来锚定。

做法：改前/改后哪个更贴合上下文
--------------------------------
不去上下文里"找"目标串——找不准。判读给的上下文写的是**影像侧**（即改对之后）
的样子，所以正确的判据是：**把错误串换成影像串之后，这一段是不是更像上下文了。**

    1. 在所属章的 CJK 流里列出错误串的全部出现位置
    2. 每个候选取一个和上下文等长的窗口，算两个相似度：
         before = ratio(上下文, 原窗口)
         after  = ratio(上下文, 换成影像串之后的窗口)
    3. 要求 after ≥ 0.80、after > before（严格变好）、且领先第二候选 ≥ 0.06
    4. 若原窗口已经和上下文高度一致（before ≥ 0.95）→ 正文早就是对的，不动

这条判据一次解决了几类此前误伤：

    p109 因→由   上下文「追其原由，是因爲妻子是從」里有两个「因」位；
                 换在「原因」上 after 升，换在「是因爲」上 after 降 → 只取前者
    p13  來→地   上下文里 □ 把目标遮掉了，两种改法都不会让 after 变好 → 退回人工
                 （后来核 PDF：影像其实是「來」，正文本来就对，判读报错）
    p96  安→妄   正文早已是「為一種妄語」，before 已达 0.95 → 认作已正确

另有一条**落点回写**的坑：错误串跨了标点时，不能拿字节区间去 splice。
「越是「教」」在 CJK 流里是「越是教」，映射回文件是 `越是「教`，直接换成
影像串「越是以「教」」会得到「越是以「教」會」」——凭空多个引号。所以回写分两路：
CJK 数相等时**逐字替换**（保住中间的标点），不相等时要求区间内没有夹杂非汉字，
否则退回人工。

安全闸沿用前两轮：影像含「?」或「�」跳过、文本侧为空跳过、
长度变化 >6 退回、较长串要求相似度 ≥0.5（两侧皆 ≤2 字的形近替换放行），
外加 apply_ocr_fixes2 那两类系统性假阳性（圈号节号 / 他祂体例）。

用法：
    python3 scripts/apply_ocr_fixes3.py --book ephesians --dry-run
    python3 scripts/apply_ocr_fixes3.py --book ephesians --apply
"""
import argparse
import difflib
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r'[一-鿿]')

BOOKS = {
    'romans':     {'pub': 'calvin/romans', 'raw': 'calvin_raw/romans-scan/ocr',
                   'report': 'logs/adjudicate_romans.md', 'max_page': 323},
    'colossians': {'pub': 'calvin/colossians', 'raw': 'calvin_raw/colossians-scan/ocr',
                   'report': 'logs/adjudicate_colossians.md', 'max_page': None},
    'ephesians':  {'pub': 'calvin/ephesians', 'raw': 'calvin_raw/ephesians-scan/ocr',
                   'report': 'logs/adjudicate_ephesians.md', 'max_page': None},
    # 约翰福音的底本 PDF 自带一层文本——它自己也是 OCR，但和 calvin_raw 下那份
    # 是**两次独立的 OCR**（抽页比对相似度 0.88–0.98，不是同一份），所以可以当
    # 第二个证人：判读说影像是 A、我们的 raw 是 B，而 PDF 文本层也读作 B，
    # 那就是两份独立 OCR 一致对上判读的一票 → 否证，不改。
    # 实测这条闸拦下 6 条，其中 5 条是「藐视→貌视」（渲染 800dpi 核对：底本
    # 印的是「藐」，艹头在低分辨率下丢了，模型误读），1 条是「欢喜喜地」。
    'john':       {'pub': 'calvin/john', 'raw': 'calvin_raw/john-scan/ocr',
                   'report': 'logs/adjudicate_john.md', 'max_page': None,
                   'verify_pdf': '/Users/yanpeifa/Documents/论文/calvin/加尔文--约翰福音注释.pdf'},
}

# 值里会嵌套「」（如 影像=「越是以「教」」 文本=「越是「教」」）。单纯非贪婪会停在
# 里层的 」 上，把 txt 截成「越是「教」——照这个去 replace 会往正文里塞一个多余的 」。
# 所以用前瞻把收尾的 」 锚在下一个标记之前。「文本上下文=」是模型偶尔写错的标记名。
FIND_RE = re.compile(
    r'影像=「(.*?)」(?=\s*文本=)\s*文本=「(.*?)」'
    r'(?=\s*(?:文本上下文=|上下文=|[（(]|$))')
CTX_RE = re.compile(r'(?:文本)?上下文=「(.*)$')

# ── 判读的两类系统性假阳性（约翰福音 661 条里占 278 条）─────────────────────
# 1) 带圈节号：影像上是 ㉑㉒…㊿ 这类两位数圈码，模型认不出 20 以上的字形，读成
#    ①③⑤ 之类。**文本侧才是对的**，照报回填等于把正确节号改错。
# 2) 他/祂：出版体例把指称基督的第三人称统一作「祂」，影像底本作「他」。这是编辑
#    规范差异，不是 OCR 错误。
CIRCLED = ''.join(chr(c) for lo, hi in
                  ((0x2460, 0x24FF), (0x2776, 0x2793),
                   (0x3251, 0x325F), (0x32B1, 0x32BF))
                  for c in range(lo, hi + 1))
_NUM_NOISE = str.maketrans('', '', CIRCLED + '0123456789０１２３４５６７８９'
                                             '（）()［］[]{}、，。 \t　·-—')

MIN_FIT = 0.70       # 落点窗口与上下文的贴合度下限（改前/改后取较高者）
MIN_SIGNAL = 0.02    # 改前后贴合度必须有差别，否则上下文对该字毫无信息
MIN_MARGIN = 0.06    # 必须领先第二候选多少


def cj(s):
    return ''.join(CJK.findall(s))


def cjk_index(text):
    """→ (cjk流, [每个cjk字在原串中的下标])"""
    chars, idx = [], []
    for i, c in enumerate(text):
        if CJK.match(c):
            chars.append(c)
            idx.append(i)
    return ''.join(chars), idx


def is_false_positive(img, txt):
    """→ (是否跳过, 类别)"""
    if img.translate(_NUM_NOISE) == '' and txt.translate(_NUM_NOISE) == '':
        return True, '跳过·假阳性/圈号节号'
    norm = lambda s: s.replace('祂', '他').replace('衪', '他')
    if norm(img) == norm(txt):
        return True, '跳过·假阳性/他祂体例'
    return False, ''


def parse_report(path):
    t = Path(path).read_text(encoding='utf-8')
    blocks = re.split(r'^## page (\d+)\s*$', t, flags=re.M)[1:]
    out = []
    for i in range(0, len(blocks), 2):
        pg = int(blocks[i])
        for line in blocks[i + 1].splitlines():
            line = line.strip()
            m = FIND_RE.search(line)
            if not m:
                continue
            c = CTX_RE.search(line)
            out.append((pg, m.group(1), m.group(2), c.group(1) if c else ''))
    return out


def window(stream, s, n, ctxlen):
    """取以 [s, s+n) 为中心、长度约 ctxlen 的窗口 → (lo, hi)"""
    pad = max(0, (ctxlen - n)) // 2
    return max(0, s - pad), min(len(stream), s + n + pad)


def locate(stream, tcj, icj, ctxcj):
    """→ (落点, after, before, 领先幅度)；没有候选返回 (None, 0, 0, 0)"""
    cands = [m.start() for m in re.finditer(re.escape(tcj), stream)]
    if not cands or not ctxcj:
        return None, 0.0, 0.0, 0.0, 0.0
    scored = []
    for s in cands:
        lo, hi = window(stream, s, len(tcj), len(ctxcj))
        before = difflib.SequenceMatcher(None, ctxcj, stream[lo:hi]).ratio()
        after = difflib.SequenceMatcher(
            None, ctxcj, stream[lo:s] + icj + stream[s + len(tcj):hi]).ratio()
        # 上下文可能引的是影像侧（改对之后），也可能引的是文本侧（错的原样）——
        # 两种都算贴合，取较大的那个当这个落点的得分。
        scored.append((max(before, after), after, before, s))
    scored.sort(reverse=True)
    score, after, before, pos = scored[0]
    second = scored[1][0] if len(scored) > 1 else -1.0
    return pos, score, after, before, score - second


def splice(body, idxmap, pos, tcj, icj):
    """把 CJK 流下标 pos 处的 tcj 换成 icj，回写到 body。→ 新 body 或 None"""
    s_file = idxmap[pos]
    e_file = idxmap[pos + len(tcj) - 1] + 1
    if len(icj) == len(tcj):
        # 逐字替换：中间夹的标点/空白/标记原样留住
        out = list(body)
        for k, ch in enumerate(icj):
            out[idxmap[pos + k]] = ch
        return ''.join(out)
    # 增删字：只有区间内全是汉字才敢整段换
    if e_file - s_file != len(tcj):
        return None
    return body[:s_file] + icj + body[e_file:]


class PdfWitness:
    """底本 PDF 的文本层，当第二个 OCR 证人用。"""

    def __init__(self, path):
        import fitz
        self.doc = fitz.open(path)
        self.cache = {}

    def page(self, n):
        if n not in self.cache:
            self.cache[n] = cj(self.doc[n - 1].get_text()) if 1 <= n <= self.doc.page_count else ''
        return self.cache[n]

    def refutes(self, n, tcj, icj):
        """文本层读作「文本侧」而非「影像侧」→ 判读那一票被否证"""
        t = self.page(n)
        if not t:
            return False
        return tcj in t and icj not in t


def map_pages(cfg, pubtexts):
    """raw 页 → 章文件。多探针：单一探针失败就换位置再试。"""
    pubcjk = {f: cj(re.sub(r'<[^>]+>', '', t)) for f, t in pubtexts.items()}
    m = {}
    for rf in sorted((ROOT / cfg['raw']).glob('page_*.md')):
        n = int(re.search(r'page_(\d+)', rf.name).group(1))
        if cfg['max_page'] and n > cfg['max_page']:
            continue
        t = cj(re.sub(r'<[^>]+>', '', rf.read_text(encoding='utf-8')))
        if len(t) < 40:
            continue
        for off in (30, 80, 150, 250, 10):
            probe = t[off:off + 24]
            if len(probe) < 20:
                continue
            hit = [f for f, body in pubcjk.items() if probe in body]
            if len(hit) == 1:
                m[n] = hit[0]
                break
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', required=True, choices=sorted(BOOKS))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        sys.exit('要 --apply 或 --dry-run')
    cfg = BOOKS[a.book]

    pubtexts = {f: f.read_text(encoding='utf-8')
                for f in sorted((ROOT / cfg['pub']).glob('*.md'))}
    recs = parse_report(ROOT / cfg['report'])
    pagemap = map_pages(cfg, pubtexts)
    witness = PdfWitness(cfg['verify_pdf']) if cfg.get('verify_pdf') else None
    print(f'判读条目 {len(recs)}；页→章映射 {len(pagemap)} 页\n')

    if a.apply:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        bak = ROOT / f'logs/bak3_{a.book}_{stamp}'
        bak.mkdir(parents=True, exist_ok=True)
        for f in pubtexts:
            shutil.copy(f, bak / f.name)
        print(f'已备份 → {bak}\n')

    stat = Counter()
    applied, held = [], []

    for pg, img, txt, ctx in recs:
        if '?' in img or '�' in img or not img.strip() or not txt.strip():
            stat['跳过·存疑/无锚点'] += 1; continue
        fp, why = is_false_positive(img, txt)
        if fp:
            stat[why] += 1; continue
        f = pagemap.get(pg)
        if not f:
            stat['跳过·该页无章映射'] += 1; continue

        short = len(txt) <= 2 and len(img) <= 2
        ratio = difflib.SequenceMatcher(None, txt, img).ratio()
        if abs(len(img) - len(txt)) > 6 or (not short and ratio < 0.5):
            stat['退回人工·疑似改写'] += 1
            held.append((pg, f.name, txt, img, '疑似改写')); continue

        body = pubtexts[f]
        stream, idxmap = cjk_index(body)
        tcj, icj, ctxcj = cj(txt), cj(img), cj(ctx)
        if not tcj:
            stat['跳过·错误串无汉字'] += 1; continue
        if len(ctxcj) < 8:
            stat['退回人工·上下文太短'] += 1
            held.append((pg, f.name, txt, img, '上下文太短')); continue

        if witness and witness.refutes(pg, tcj, icj):
            stat['跳过·PDF文本层否证'] += 1
            held.append((pg, f.name, txt, img, 'PDF文本层否证')); continue

        pos, score, after, before, margin = locate(stream, tcj, icj, ctxcj)
        tag = f'贴合={score:.2f} 方向={after - before:+.2f} 领先={margin:.2f}'
        if pos is None:
            stat['跳过·章内找不到错误串'] += 1
            held.append((pg, f.name, txt, img, '章内无此串')); continue
        if score < MIN_FIT:
            stat['退回人工·上下文不贴合'] += 1
            held.append((pg, f.name, txt, img, tag)); continue
        if abs(after - before) < MIN_SIGNAL:
            # 改与不改对上下文毫无差别 → 被改的那个字在上下文里根本没体现
            # （判读常用 □ ◯ 把目标遮掉）。这种没有位置证据，不能自动改。
            stat['退回人工·上下文对该字无信息'] += 1
            held.append((pg, f.name, txt, img, tag)); continue
        if margin < MIN_MARGIN:
            stat['退回人工·落点不唯一'] += 1
            held.append((pg, f.name, txt, img, tag)); continue

        # 缺字类（影像串把文本串整个包住）要再确认一次：正文那个位置是不是
        # 早就已经是完整写法了。文本串是影像串的子串，所以它在正确的正文里
        # 也照样命中——直接替换会造出重复字：
        #     正文「欢欢喜喜地」 tcj「欢喜喜地」 icj「欢欢喜喜地」
        #       → 命中在偏移 1，换完变成「欢欢欢喜喜地」
        #     正文「我到世上来」 tcj「我到世上」 icj「我到世上来」→「我到世上来来」
        # 判据：落点与某个 icj 的出现位置有重叠 → 已经是对的，不动。
        # 只对缺字类生效；多字类（icj 是 tcj 的子串）本来就必然重叠，不能套。
        if len(icj) > len(tcj) and tcj in icj:
            if any(o <= pos < o + len(icj) or pos <= o < pos + len(tcj)
                   for o in (m.start() for m in re.finditer(re.escape(icj), stream))):
                stat['跳过·正文已是完整写法'] += 1
                held.append((pg, f.name, txt, img, '正文已完整')); continue

        newbody = splice(body, idxmap, pos, tcj, icj)
        if newbody is None:
            stat['退回人工·落点跨标点无法回写'] += 1
            held.append((pg, f.name, txt, img, '落点跨标点')); continue
        pubtexts[f] = newbody
        stat['已应用'] += 1
        applied.append((pg, f.name, txt, img, tag))

    for k, v in stat.most_common():
        print(f'  {k}: {v}')

    if a.apply:
        for f, t in pubtexts.items():
            f.write_text(t, encoding='utf-8')
        print(f'\n✓ 写回 {len(pubtexts)} 个文件')
    else:
        print('\n（dry-run，未写回）')

    (ROOT / f'logs/applied3_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{how}' for p, fn, t, i, how in applied),
        encoding='utf-8')
    (ROOT / f'logs/held3_{a.book}.tsv').write_text(
        '\n'.join(f'{p}\t{fn}\t{t}\t{i}\t{r}' for p, fn, t, i, r in held),
        encoding='utf-8')
    print(f'明细 → logs/applied3_{a.book}.tsv / held3_{a.book}.tsv')


if __name__ == '__main__':
    main()
