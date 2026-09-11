#!/usr/bin/env python3
"""把重新 OCR 出来的希伯来文/希腊文落回正文。

`isaiah_hebrew_ocr.py` 产出的是 (前文, 乱码, 后文, 读数)。落盘必须**按位置**，
不能按串全局替换：ABBYY 的拉丁误读是有损的，同一串乱码在不同地方可能来自
不同的希伯来词（`bs` 分别是 על / אל / כל）。所以每条都要靠前后文锚唯一定位，
定位不唯一就宁可不落。

跑在 extract 之后、repair 之前：repair 的 token 正则只认拉丁字母，希伯来字
对它是透明的，不会被当成残串去「修」。

    python3 scripts/isaiah_apply_hebrew.py            # 只报告
    python3 scripts/isaiah_apply_hebrew.py --apply    # 落盘
"""
import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw/isaiah/en_chapters'
TSV = [ROOT / 'alexander_raw/isaiah/hebrew_ocr.tsv',
       ROOT / 'alexander_raw/isaiah/hebrew_ocr_junk.tsv']
LOG = ROOT / 'logs/alexander_isaiah_hebrew_applied.tsv'

# 置信度门槛。实测 ≥80 的读数逐条看都站得住（את / על / ברית / הנה /
# ῥύσασϑε ἀδικούμενον）；65–75 那一档明显在硬凑（`xb` 读成 כא，其实是 לא），
# 留在数据文件里但不落盘。
MIN_CONF = 80
# 有别处高置信度读数背书时的下限
SELF_CONF = 70


def half_of_broken_word(flat, g, garb, lex):
    """这串是不是某个英文词被拆成两半里的一半。

    ABBYY 有时把行末的连字符整个吞掉：第 62 章 `unintel-ligible` 断在行末，
    XML 里上一行以 `unintel` 收尾、下一行以 `ligible` 起头，中间没有连字符，
    接词的哨兵就无从下手，正文里于是留下两个独立的词。`unintel` 判词典不认，
    正好落进希伯来候选，被读成 `מותט` 换掉了——`in some degree מותט ligible`。

    判据是**拼回去是不是词**：与前一个词或后一个词粘起来成词，就说明这串
    是半个英文词，不是希伯来活字。
    """
    nxt = re.match(r'\s+([A-Za-z]+)', flat[g + len(garb):])
    if nxt and is_word(garb + nxt.group(1), lex):
        return True
    prv = re.search(r'([A-Za-z]+)\s+$', flat[:g])
    return bool(prv and is_word(prv.group(1) + garb, lex))


def keep_italics(slice_, reading):
    """替换时把原文那一段自带的斜体星号留住。

    落盘是按**归一化后**的下标定位的，归一化把 `*` 抹掉了，所以被替换掉的
    那一段里如果夹着斜体标记，换上去的读数就把星号一并吃了——kramdown 那边
    星号成了单数，半截星号原样印在页面上。实测落希伯来这一步单独制造了
    5 篇不配对（38 / 45 / 48 / 7 / 9）。

    段首段尾的星号照原样接回去；星号落在**中间**说明这段横跨斜体边界，
    接不回去，宁可不换。
    """
    if '*' not in slice_:
        return reading
    if slice_.strip('*').count('*'):
        return None
    return ('*' if slice_.startswith('*') else '') + reading \
        + ('*' if slice_.endswith('*') else '')


def find_whole(flat, needle):
    """整词定位。**不能用裸 find**——`unintel` 会匹配进 `unintelligible` 里面。

    第 62 章踩过：`unintel-ligible` 断在行末，ABBYY 把前半截当成独立一个词，
    重扫把它读成希伯来文落了盘，正文就成了 `in some degree מותט ligible`。
    这串本来就在行尾，锚里 `after` 是空的，于是 `before + garbage` 作为
    **前缀**正好落在整词中间，裸 find 一路匹配过去，谁也拦不住。
    """
    out, start = [], 0
    while True:
        p = flat.find(needle, start)
        if p < 0:
            return out
        if ((p == 0 or not flat[p - 1].isalnum())
                and (p + len(needle) >= len(flat)
                     or not flat[p + len(needle)].isalnum())):
            out.append(p)
        start = p + 1


def norm(text):
    """归一化到「只剩字母数字与单空格」，并保留到原文的下标映射。

    正文这一侧经过 cleanup（斜体变 `*`、断词接好、字面星号转义），与 ABBYY
    的行文本对不上，所以两边都要先抹掉这些差异再比。
    """
    out, idx = [], []
    prev_space = True
    for i, ch in enumerate(text):
        if ch.isalnum():
            out.append(ch)
            idx.append(i)
            prev_space = False
        elif not prev_space:
            out.append(' ')
            idx.append(i)
            prev_space = True
    return ''.join(out), idx


def main(apply_it):
    lex = build()
    # 必须 QUOTE_NONE：乱码串里有 `"`（`"tt`、`"ttss`），默认的 csv 引号规则
    # 会把它当成字段起始引号，整行的列就错位了——608 行只解析出 306 行。
    raw = [r for path in TSV if path.exists()
           for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t',
                                   quoting=csv.QUOTE_NONE)
           if r.get('conf', '').isdigit() and r.get('reading')]
    # **两遍扫描会撞车。** 主跑与 --junk 那一遍的候选判据有重叠，同一处
    # 会各出一行；照单全落就是同一个位置改两次，第二次拿改完的文本再改一遍，
    # 于是 `(from πρόφημι)` 变成 `(from πρόφημι)))`（导论正文第一行）。
    rows, seen = [], set()
    for r in raw:
        key = (r['vol'], r['scan_page'], r['before'], r['garbage'])
        if key in seen:
            continue
        seen.add(key)
        rows.append(r)
    # 语料自证：同一个读数在别处被高置信度接受过，这里 70 分也认。
    # `προφητῆς` 在导论里出现四次，置信度 77 / 82 / 88 各一次——同一个词，
    # 同一套活字，凭什么只认高的那两次。这是修拉丁误读时的第三道闸
    # （字形规则 → 判词典 → 全书自证）搬到这边来。
    strong = {r['reading'] for r in rows if int(r['conf']) >= MIN_CONF}
    chapters = {p.stem: p.read_text(encoding='utf-8') for p in RAW.glob('*.md')}
    keys = {k: norm(v) for k, v in chapters.items()}

    log, stat = [], {'applied': 0, 'lowconf': 0, 'notfound': 0, 'ambiguous': 0,
                     'halfword': 0}
    edits = {k: [] for k in chapters}
    for r in rows:
        if int(r['conf']) < MIN_CONF and not (int(r['conf']) >= SELF_CONF
                                              and r['reading'] in strong):
            stat['lowconf'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'lowconf'))
            continue
        # 末尾要 strip：norm 把标点换成空格，`after` 是 "The Vulgate," 时
        # 锚就以空格收尾，整词判定于是去看**下一个词的首字母**，永远是字母，
        # 于是全都判不过（实测 404 条锚失效）
        anchor = norm(f"{r['before']} {r['garbage']} {r['after']}")[0].strip()
        garb = norm(r['garbage'])[0].strip()
        if not garb or not anchor:
            continue
        hits = []
        for name, (flat, _) in keys.items():
            hits += [(name, q) for q in find_whole(flat, anchor)]
        if not hits:
            stat['notfound'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'notfound'))
            continue
        if len(hits) > 1:
            stat['ambiguous'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'ambiguous'))
            continue
        name, p = hits[0]
        flat, idx = keys[name]
        g = next((q for q in find_whole(flat, garb)
                  if p <= q <= p + len(anchor)), -1)
        if g < 0:
            stat['notfound'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'notfound'))
            continue
        if half_of_broken_word(flat, g, garb, lex):
            stat['halfword'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'halfword'))
            continue
        edits[name].append((idx[g], idx[g + len(garb) - 1] + 1, r['reading']))
        stat['applied'] += 1
        log.append((r['garbage'], r['reading'], r['conf'], 'applied'))

    if apply_it:
        for name, es in edits.items():
            if not es:
                continue
            text = chapters[name]
            for a, b, rep in sorted(es, reverse=True):     # 从后往前，下标不失效
                rep = keep_italics(text[a:b], rep)
                if rep is None:
                    continue
                text = text[:a] + rep + text[b:]
            (RAW / f'{name}.md').write_text(text, encoding='utf-8')

    LOG.parent.mkdir(exist_ok=True)
    with open(LOG, 'w', encoding='utf-8') as f:
        f.write('garbage\treading\tconf\tstatus\n')
        for row in log:
            f.write('\t'.join(str(x) for x in row) + '\n')
    print('希伯来/希腊落盘:', stat, '→', LOG)
    if not apply_it:
        print('（报告模式，没有落盘。要落盘加 --apply）')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    main(ap.parse_args().apply)
