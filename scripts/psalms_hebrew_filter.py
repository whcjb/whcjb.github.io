#!/usr/bin/env python3
"""筛 hebrew_ocr.tsv：只留下可信的重扫读数，其余留在账上不动。

三类要挡（都是实跑出来的）：

  同形字映射   tesseract 的希腊模型会把拉丁字母映成**视觉相同的希腊大写**
               （`pp.`→`ΡΡ`、`ex-`→`ΘΧ-`、`sub-`→`Βαὺ-`、`(7NI)`→`ΟΝ)`）。
               这本书里真正的希腊文引文一律是带变音符的小写
               （`ἐρχόμενος` `σαβαώθ` `ποιμαίνω` `ὁμοιότητα`），
               判据就是**大写占比**，不是置信度——`pp.`→`ΡΡ` 置信度 90。
  英文断词碎片 行末断开的 `sub-` `neces-` `pro-` `mean-`，尾巴带连字符。
  串太短       两三个字母的裁图信息量不够，`oi`→`οἵ` 置信度 97 也不能信。
"""
import csv
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TSV = ROOT / 'alexander_raw/psalms/hebrew_ocr.tsv'

HEB = re.compile(r'[֐-׿]')
GRC = re.compile(r'[Ͱ-Ͽἀ-῿]')
GRC_UPPER = re.compile(r'[Α-ΩἈ-῿]')
DIACRITIC = re.compile(r'[ἀ-῿΄-ΆΈ-Ώά-ώ]')

MIN_CONF = {'heb': 78, 'grc': 82}


def keep(row):
    garbage, script, reading, conf = row['garbage'], row['script'], row['reading'], int(row['conf'])
    if conf < MIN_CONF[script]:
        return False, f'置信度 {conf} 低于 {MIN_CONF[script]}'
    core = garbage.strip('.,;:()[]{}\'"')
    letters = re.sub(r'[^A-Za-z]', '', core)
    if core.endswith('-') or core.startswith('-'):
        return False, '英文行末断词碎片'
    if len(letters) < 3 and not re.search(r'[^0-9A-Za-z\s]', core):
        return False, f'串太短（{core!r}）'
    if script == 'heb':
        if len(HEB.findall(reading)) < 2:
            return False, '希伯来字母不足 2 个'
    else:
        g = GRC.findall(reading)
        if len(g) < 3:
            return False, '希腊字母不足 3 个'
        upper = len(GRC_UPPER.findall(reading))
        if upper / len(g) > 0.4:
            return False, f'大写占比 {upper}/{len(g)}，多半是同形字映射'
        if not DIACRITIC.search(reading):
            return False, '没有变音符，多半是同形字映射'
    return True, ''


def main():
    # QUOTE_NONE：残渣串里满是 `"` `'`（`""jy` `T\\'^Q^i`），csv 默认会把它们
    # 当引号，把相邻字段并到一起
    rows = list(csv.DictReader(open(TSV, encoding='utf-8'), delimiter='\t',
                               quoting=csv.QUOTE_NONE))
    good, drop = [], []
    for r in rows:
        ok, why = keep(r)
        (good if ok else drop).append((r, why))
    print(f'总 {len(rows)} 条 → 采信 {len(good)}，弃 {len(drop)}')
    if '-v' in sys.argv:
        print('\n── 弃 ──')
        for r, why in drop:
            print(f"  {r['script']} c{r['conf']:<3} {r['garbage'][:24]!r:<26} → "
                  f"{r['reading'][:20]!r:<22} {why}")
    out = TSV.with_name('hebrew_ocr_accepted.tsv')
    with open(out, 'w', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys(), delimiter='\t',
                           quoting=csv.QUOTE_NONE, quotechar='', escapechar='\\')
        w.writeheader()
        for r, _ in good:
            w.writerow(r)
    print(f'→ {out}')


if __name__ == '__main__':
    main()
