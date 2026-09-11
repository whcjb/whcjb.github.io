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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'alexander_raw/isaiah/en_chapters'
TSV = [ROOT / 'alexander_raw/isaiah/hebrew_ocr.tsv',
       ROOT / 'alexander_raw/isaiah/hebrew_ocr_junk.tsv']
LOG = ROOT / 'logs/alexander_isaiah_hebrew_applied.tsv'

# 置信度门槛。实测 ≥80 的读数逐条看都站得住（את / על / ברית / הנה /
# ῥύσασϑε ἀδικούμενον）；65–75 那一档明显在硬凑（`xb` 读成 כא，其实是 לא），
# 留在数据文件里但不落盘。
MIN_CONF = 80


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
    # 必须 QUOTE_NONE：乱码串里有 `"`（`"tt`、`"ttss`），默认的 csv 引号规则
    # 会把它当成字段起始引号，整行的列就错位了——608 行只解析出 306 行。
    rows = [r for path in TSV if path.exists()
            for r in csv.DictReader(open(path, encoding='utf-8'), delimiter='\t',
                                    quoting=csv.QUOTE_NONE)
            if r.get('conf', '').isdigit() and r.get('reading')]
    chapters = {p.stem: p.read_text(encoding='utf-8') for p in RAW.glob('*.md')}
    keys = {k: norm(v) for k, v in chapters.items()}

    log, stat = [], {'applied': 0, 'lowconf': 0, 'notfound': 0, 'ambiguous': 0}
    edits = {k: [] for k in chapters}
    for r in rows:
        if int(r['conf']) < MIN_CONF:
            stat['lowconf'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'lowconf'))
            continue
        anchor, _ = norm(f"{r['before']} {r['garbage']} {r['after']}")
        garb, _ = norm(r['garbage'])
        if not garb or not anchor:
            continue
        hits = []
        for name, (flat, idx) in keys.items():
            start = 0
            while True:
                p = flat.find(anchor, start)
                if p < 0:
                    break
                hits.append((name, p))
                start = p + 1
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
        g = flat.find(garb, p)
        if g < 0 or g > p + len(anchor):
            stat['notfound'] += 1
            log.append((r['garbage'], r['reading'], r['conf'], 'notfound'))
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
