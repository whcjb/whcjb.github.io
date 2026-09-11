#!/usr/bin/env bash
# 以赛亚书从 ABBYY XML 到发布的完整链条。**顺序不能换**，每一步都建立在上一步之上。
#
#   1 extract        XML → en_chapters（斜体、断词、段落、页码都在这一步定）
#   2 apply_hebrew   把 tesseract heb/grc 重读出来的希伯来/希腊文按位置落回
#                    必须在 repair 之前：repair 的 token 正则只认拉丁字母，
#                    希伯来字对它透明，不会被当成残串去「修」
#   3 repair         字形规则 → 词典闸 → 全书自证，三道闸修拉丁误读
#   4 publish        en_chapters → alexander/isaiah（已发布章节的 date 保留原值）
#   5 adjudicate     九份独立扫描件多数表决，改的是**已发布正文**
#   6 backlog        分桶算账，看还剩多少要人判
#   7 rescan         拿 tesseract 重扫剩下那批待判串——这是**第二个证人**，
#                    认的是同一份 PDF 原图、坐标来自 ABBYY charParams，
#                    不像九份 IA 证人那样会锚撞车。必须排在 backlog 之后：
#                    它要读 backlog 出的待判清单才知道扫哪些
#   8 backlog        重扫落盘后再算一次账
#
# 中间任何一步改了脚本，都要从那一步往后重跑——en_chapters 与 alexander/isaiah
# 都是 in-place 改写，跳步会把上一轮的结果当成输入叠加。
#
# hebrew_ocr.tsv 本身由 scripts/isaiah_hebrew_ocr.py 单独生成（要跑一个多钟头），
# 不在这条链里；它是数据，不是环节。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/extract_alexander_isaiah.py
python3 scripts/isaiah_apply_hebrew.py --apply
python3 scripts/repair_alexander_ocr.py isaiah
python3 scripts/publish_alexander_en.py isaiah
python3 scripts/adjudicate_alexander_isaiah.py --apply
python3 scripts/isaiah_backlog.py
python3 scripts/isaiah_english_rescan.py
python3 scripts/isaiah_english_rescan.py --apply
python3 scripts/isaiah_backlog.py
