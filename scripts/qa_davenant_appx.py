#!/usr/bin/env python3
"""附卷与索引的检查闸。正文那几道（Gate W/S）不适用，另立六道。

正文有 92 个节组的经文可以拿 KJV 逐节比（Gate S），附卷与索引没有经文块，
之前只验了脚注与标签配对——那只证明产物自洽，不证明它忠于底本。这里补上：

    Gate A  零丢失     产物词多重集 == OCR 原文（该块页范围）扣掉页眉页脚，
                       与正文 Gate W 同一套判据
    Gate B  编号连续   OBJECTION / REPLY / ARGUMENT 的序号必须 1..N 不断不重，
                       断号＝那一条被吞或被并进了上一段
    Gate C  页序单调   同一块内的页码标记必须不降；倒序＝段落被排错位
    Gate D  字母分区   索引的 A–Z 分隔必须按序出现，且该段条目首字母相符
    Gate E  条目带页码 索引条目必须含页码数字；不含的多半是回行被误判成新条目
    Gate F  目录对章   `contents-dissertation` 列的章题必须在附卷里找得到

用法: python3 scripts/qa_davenant_appx.py
"""
import collections
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
sys.path.insert(0, str(ROOT / 'scripts'))
import extract_davenant as E                        # noqa: E402
import extract_davenant_appx as A                   # noqa: E402
import extract_davenant_index as X                  # noqa: E402

PAGE_RE = re.compile(r'<!--v?\d*p?(\d+)(?:-(\d+))?-->')
TAGGED = re.compile(r'^\[([A-Z_]+)\] (.*)$')


def words(t):
    return collections.Counter(re.findall(r'[A-Za-z]+', t))


def parse(path):
    for ln in path.read_text(encoding='utf-8').splitlines():
        m = TAGGED.match(ln)
        if m:
            yield m.group(1), m.group(2)


def strip_pg(t):
    m = PAGE_RE.match(t)
    return (t[m.end():], int(m.group(1)),
            int(m.group(2) or m.group(1))) if m else (t, None, None)


def ocr_words(vol, lo, hi):
    """按提取器同一套规则，从 OCR 原文重建该页范围「应有」的词多重集。"""
    c = collections.Counter()
    joined = ''
    t = (RAW / f'vol{vol}_ocr.txt').read_text(encoding='utf-8')
    for n, body in re.findall(r'<!-- PAGE (\d+) -->\n(.*?)(?=\n<!-- PAGE |\Z)',
                              t, re.S):
        if not (lo <= int(n) <= hi):
            continue
        lines = [l for l in body.split('\n') if l.strip()]
        for _ in range(3):                    # 剥页眉
            if lines and (any(r.search(lines[0]) for r in A.HEAD_RES)
                          or E.JUNK_RE.match(lines[0])
                          or E.SPECK_RE.match(lines[0])):
                lines.pop(0)
                continue
            break
        for _ in range(2):                    # 剥页脚签名
            if lines and E.is_foot(lines[-1]):
                lines.pop()
                continue
            break
        for l in lines:
            joined = E.dehyph(joined, l) if joined else l
    c.update(re.findall(r'[A-Za-z]+', joined))
    return c


def gate_a(name, got, vol, lo, hi):
    gate_a_counter(name, got, ocr_words(vol, lo, hi))


def gate_a_counter(name, got, exp):
    miss, extra = exp - got, got - exp
    print(f'  Gate A 零丢失 {name}：产物 {sum(got.values()):,} 词 / '
          f'应有 {sum(exp.values()):,} 词')
    print(f'    应有而缺 {sum(miss.values()):,} · 多出 {sum(extra.values()):,}')
    if miss:
        print(f'    缺得最多: {dict(miss.most_common(8))}')
    if extra:
        print(f'    多得最多: {dict(extra.most_common(8))}')


def gate_b(items):
    """编号是**按章**重新起头的（每章各有自己的 ARGUMENT 1..N），所以要
    按章切开看。只报「同一章内不是 1,2,3… 连着走」的。"""
    runs, cur = collections.defaultdict(list), None
    for tag, txt in items:
        body, pg, _ = strip_pg(txt)
        # 序数后缀要一起吃掉：原书写 `ARGUMENT 1st.`，`\b` 卡在 `1` 后面
        # 匹配不上，这一条就漏出去，编号看着像是从 2 起头的。
        m = re.match(r'(OBJECTION|REPLY|ARGUMENT|ANSWER)\s+(\d{1,3})'
                     r'(?:st|nd|rd|th)?[.,\s]', body)
        if not m:
            continue
        n = int(m.group(2))
        key = m.group(1)
        if not runs[key] or n != runs[key][-1][-1] + 1:
            runs[key].append([n])             # 起新的一串
        else:
            runs[key][-1].append(n)
    print('  Gate B 编号连续：')
    for k, rs in sorted(runs.items()):
        broken = [r for r in rs if r[0] != 1]
        total = sum(len(r) for r in rs)
        flag = ''
        if broken:
            flag = f'   <<< {len(broken)} 串不是从 1 起：' + \
                   ', '.join(f'{r[0]}–{r[-1]}' for r in broken[:4])
        print(f'    {k:10} 共 {total:3} 条，分 {len(rs)} 章{flag}')


def gate_c(items):
    """页序单调。脚注排在各自页的末尾、按页归章，天然不与正文同序，排除。"""
    bad = 0
    last, cur = 0, None
    for tag, txt in items:
        if tag == 'SEC':
            last, cur = 0, txt.split('|')[0]
            continue
        if tag in ('FN', 'END', 'CITE'):
            continue
        _, a, b = strip_pg(txt)
        if a is None:
            continue
        if a < last:
            bad += 1
            if bad <= 5:
                print(f'    页码倒退 {cur}: {last} → {a}')
        last = b or a
    print(f'  Gate C 页序单调：倒退 {bad} 处')


def gate_d_e(items):
    """Gate D 改判「该并没并」，不判「首字母对不对」。

    索引是悬挂缩进：条目顶格、回行缩进。回行被误判成新条目时，它多半以
    小写字母、标点或页码起头——`II. 15; what knowledge was in`、
    `ful, and what evil, 68`。按首字母比对分区字母是没用的：同一字母段里
    本来就有大量合法的回行，实测 964 条里报 295 条，全是噪声。
    """
    n = orphan = no_page = 0
    ex, blk = [], None
    for tag, txt in items:
        if tag == 'SEC':
            blk = txt.split('|')[0]
            continue
        if tag != 'E' or blk in ('contents-dissertation', 'errata'):
            continue                      # 目次的编号小节与勘误条目本就这样起头
        body = strip_pg(txt)[0].strip()
        if not body:
            continue
        n += 1
        # 「无页码」要扣掉两类本来就没有阿拉伯页码的：交叉引用
        # （`Abstinence, see Fastings.` / `…ibid.`）与罗马数字页码
        # （`Introduction, p. lxxii.`）。不扣的话报出来的数字里九成是噪声。
        if not re.search(r'\d', body) \
                and not re.search(r'\b(see|ibid)\b', body, re.I) \
                and not re.search(r'\bp\.\s*[ivxlc]+\.', body, re.I):
            no_page += 1
        if re.match(r'^[a-z]|^[,;:)\]]|^\d+[,;.]', body):
            orphan += 1
            if len(ex) < 6:
                ex.append(body[:52])
    print(f'  Gate D 该并没并：{n} 条里 {orphan} 条以小写/标点/页码起头')
    for e in ex:
        print(f'    {e}')
    print(f'  Gate E 条目带页码：既无页码又非交叉引用的 {no_page} / {n}')


def gate_f(items):
    """目录列的章题，要在**已发布的附卷页**的 subtitle 里找得到。

    目录与正文是两处独立 OCR 出来的同一批标题，互为证人：对不上就说明
    至少有一边读坏了，或者某一章根本没抽出来。
    """
    subs = []
    for f in sorted((ROOT / 'davenant' / 'colossians' / 'dissertation').glob('*.md')):
        m = re.search(r'^subtitle:\s*"(.*)"$', f.read_text(encoding='utf-8'), re.M)
        if m:
            subs.append(m.group(1).lower())
    miss, titles_ch = [], []
    for g, t in items:
        if g != 'E':
            continue
        body = strip_pg(t)[0]
        # 目录行是 `IV. 章题 …… 页码`，把序号、引点、页码剥掉
        key = re.sub(r'^\s*[IVXLivxl\d]{1,5}[.,]?\s*', '', body)
        key = re.sub(r'[.\s]{3,}.*$|\s+\d+\s*\.?\s*$', '', key)
        key = ' '.join(re.sub(r'[^a-z ]', ' ', key.lower()).split())
        if len(key.split()) < 3 or not re.match(r'^\s*[IVXL]{1,5}[.,]', body):
            continue                      # 只看章级（罗马数字起头）那几条
        titles_ch.append(body)
        if not any(difflib.SequenceMatcher(None, key, sub).ratio() > 0.55
                   for sub in subs):
            miss.append(body[:58])
    # 目次与章头是原书自己写的两套说法（目次 `V. The Confirmation of the
    # doctrine, and objections answered`，章头 `ANSWERS TO OBJECTIONS`），
    # 对不上不等于出错。这道闸只报**数目**与配不上的清单，供人看，不判死。
    print(f'  Gate F 目录对章：已发布章题 {len(subs)} 个，'
          f'目次章级条目 {len(titles_ch)} 条，字面配不上 {len(miss)} 条（供核，非判错）')


def gate_g():
    """渲染层校验（old-book-ocr skill §3.4）。正文对不等于页面对。

    斜体是从像素上量出来贴回去的，最容易出的错是「跑飞」——归一化没到
    不动点，`<em>` 从一处一路开到页尾。四项都很便宜：
      · `<em>` 开闭配平
      · `<em>` 内容首尾不带空白（带空白＝边界贴错了位置）
      · 锚点 id 不重复（重复则页内跳转跳错地方）
      · 锚点总数（每轮比对，数字必须稳定）
    """
    pages = sorted((ROOT / 'davenant' / 'colossians').rglob('*.md'))
    bad_em = bad_ws = dup = anchors = 0
    for f in pages:
        t = f.read_text(encoding='utf-8')
        if t.count('<em>') != t.count('</em>'):
            bad_em += 1
            print(f'    <em> 不配平: {f.name}')
        for m in re.finditer(r'<em>(.*?)</em>', t, re.S):
            if m.group(1) != m.group(1).strip():
                bad_ws += 1
                if bad_ws <= 5:
                    print(f'    <em> 边界带空白: {f.name} {m.group(1)[:40]!r}')
        ids = re.findall(r'id="([^"]+)"', t)
        anchors += len(ids)
        for k, n in collections.Counter(ids).items():
            if n > 1:
                dup += 1
                print(f'    锚点 id 重复: {f.name} {k} ×{n}')
    print(f'  Gate G 渲染层：页面 {len(pages)}，锚点 {anchors}，'
          f'<em> 不配平 {bad_em}，边界带空白 {bad_ws}，重复 id {dup}')


def main():
    appx = list(parse(RAW / 'davenant_colossians_appendix.txt'))
    idx = list(parse(RAW / 'davenant_colossians_index.txt'))

    print('《论基督之死》+ 法国之争')
    got = words(' '.join(strip_pg(t)[0] for g, t in appx if g != 'SEC'))
    # ⚠️ 按卷分开比。附卷绝大多数在卷二，但 Addenda 在卷一末尾（p632–634）；
    # 早先这里用写死的 `A.VOL` 与全体 lo/hi，加进 Addenda 之后 lo 会变成
    # 632、hi 还是 578，区间直接倒过来，Gate A 的「应有」成了空集。
    exp_all = collections.Counter()
    for v in sorted({pc['vol'] for pc in A.PIECES}):
        lo = min(p['lo'] for p in A.PIECES if p['vol'] == v)
        hi = max(p['hi'] for p in A.PIECES if p['vol'] == v)
        exp_all += ocr_words(v, lo, hi)
    gate_a_counter('附卷全体', got, exp_all)
    gate_b(appx)
    gate_c(appx)

    print('\n六种索引 + ERRATA')
    gotx = words(' '.join(strip_pg(t)[0] for g, t in idx if g == 'E'))
    gate_a('索引全体', gotx, 2, min(p['lo'] for p in X.PIECES),
           max(p['hi'] for p in X.PIECES))
    gate_c(idx)
    gate_d_e(idx)
    print()
    gate_g()

    cont = []
    keep = False
    for g, t in idx:
        if g == 'SEC':
            keep = t.split('|')[0] == 'contents-dissertation'
            continue
        if keep:
            cont.append((g, t))
    gate_f(cont)
    return 0


if __name__ == '__main__':
    sys.exit(main())
