#!/bin/bash
# 2026-11-10 用户令：各书只差的辅助页（扉页、序言、索引、勘误表）一并译完。串行跑，任何一步失败即停。
cd "$(dirname "$0")/.."
set -e
step() { echo; echo "=== $(date '+%F %T') $*"; "$@"; }
step python3 -u scripts/batch_prefill.py --module translate_adams --section alphabetical-index
step python3 -u scripts/translate_adams.py --resume --section title1 --section title2 --section alphabetical-index --section errata
step python3 -u scripts/batch_prefill.py --module translate_petter --section alphabetical-table
step python3 -u scripts/translate_petter.py --resume --section title --section preface --section alphabetical-table
step python3 -u scripts/translate_jones.py --book 2john --resume --section errata
step python3 -u scripts/translate_jones.py --book 3john --resume --section errata
step python3 -u scripts/translate_alexander_acts.py --resume --section title-1 --section title-2
echo; echo "=== $(date '+%F %T') 全部完成"
