#!/usr/bin/env bash
# 亚历山大《诗篇注释》英文底本从 raw 到发布的完整链条。**顺序不能换**。
#
#   1 publish      en_chapters → alexander/psalms（已发布章节的 date 保留原值）
#   2 adjudicate   1850 三卷本第二证人 + MANUAL_TEXT + 希伯来/希腊重扫规则
#   3 hebrew       tesseract heb/grc 重扫的希伯来文按位置落回
#   4 image        1864 页面影像逐处判读（读数在 logs/alexander_image_readings*.tsv，
#                  过闸逻辑见脚本；不需要再调模型）
#   5 manual       裁图两遍互证与逐张读影像的那一批（alexander_raw/psalms/manual_fixes.tsv）
#                  ——这一步必须在最后：它的锚是按「前四步跑完」的形态取的
#
# 前两步的上游（extract → repair）不在这条链里，它们改的是 en_chapters，
# 而 en_chapters 已经入库。**只有重新 extract 或改 repair 规则时才需要**：
#   python3 scripts/extract_alexander_psalms.py
#   python3 scripts/repair_alexander_ocr.py psalms
# 跑完这两步以后，第 5 步的锚可能对不上（manual_fixes 会报「失效」），
# 按报出来的条目逐条重新定位——不要把报错当噪音跳过。
#
# 验收：整条链跑完，alexander/psalms/*.md 的正文应与跑之前逐字节相同
# （front matter 的 date 不变，publish 会沿用原值）。任何一处对不上，
# 都说明有一轮改动只落在了正文里、没落进脚本或数据——那正是这条链要防的事。
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/publish_alexander_en.py
python3 scripts/adjudicate_alexander_ocr.py --apply
python3 scripts/psalms_hebrew_apply.py --apply
python3 scripts/adjudicate_alexander_image.py --apply --replay
python3 scripts/apply_alexander_manual.py --apply
