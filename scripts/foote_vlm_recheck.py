#!/usr/bin/env python3
"""福特《路加福音讲义》整页转录与现行正文逐词再比（2026-11-13 用户令「上次读过的图直接拿来用」「继续做」）。

11-09 的整页转录（vlm/，正文词对齐覆盖 98.9%）当时只拿来改字。这里再比三样，落 `vlm_recheck_fixes.tsv`（静态表，
按位置从前往后、每条上下文取自前几条改完后的文本，故须在 foote_sweep --apply 之后按序落）：

  para   转录分段而我们没分（74）：插 `<!-- PAGE n -->` 起新段；开引号随新段走、收引号留前段（按段内引号奇偶），
         编号 `1.` `*5.*` `First.` 随新段走。看图抽 5 处均是原书分段（含引经文另起一行）
  punct  词间标点与转录不同、且 tesseract 同位与转录一致（238）：补漏的句点／逗号（`order"*`→`order."*`）、
         删杂点（`/` `€` `£` `%` `&`）、`1`→`!`／`?` 等；跨分段/页码标记、动到星号成空斜体、只差注号的不收
  ital   两段斜体间夹一两个词、转录作斜体＝引文被断开，合并（24）
  glue   逐词对齐时数目不等的小块（130）：孤立字母 I／V／t／J／f 等＝! ? 注号，按转录同位读法换（只差一个符号时只换字母、
         星号原样）；经文段节号（18L→18.、*2Q.*→28.）；残词（%ay%ng→saying、teas 08→was as）。注号链接 1264→1287
  hand   词尾 y/s 实为逗号（`Christy as`→`Christ, as`）等 6 条

生成脚本在会话草稿（vpunct.py／pclass.py／pfix2.py／build_recheck.py），表即数据。

    python3 scripts/foote_vlm_recheck.py --apply
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402

RULES = A.RAW / 'vlm_recheck_fixes.tsv'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    if a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
