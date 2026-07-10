#!/bin/bash
# Usage: translate_serial.sh <book_key> <ch1> [ch2] [ch3] ...
# 例: translate_serial.sh 1timothy 2 3
# 会串行跑 --book <book_key> --chapter N --resume, 每章翻完 publish + chmod + jekyll build + git commit + push
set -e
cd /Users/yanpeifa/Documents/whcjb.github.io
BOOK=$1
shift

# publish 脚本名和 book_key 完全匹配
# 1timothy → publish_1timothy_zh.py, 2timothy → publish_2timothy_zh.py, etc.
case "$BOOK" in
    1timothy) PUBLISH=scripts/publish_1timothy_zh.py; RAW_DIR=calvin_raw/1timothy/zh_chapters; PUB_DIR=calvin/1timothy ;;
    2timothy) PUBLISH=scripts/publish_2timothy_zh.py; RAW_DIR=calvin_raw/2timothy/zh_chapters; PUB_DIR=calvin/2timothy ;;
    titus)    PUBLISH=scripts/publish_titus_zh.py;    RAW_DIR=calvin_raw/titus/zh_chapters;         PUB_DIR=calvin/titus ;;
    philemon) PUBLISH=scripts/publish_philemon_zh.py; RAW_DIR=calvin_raw/philemon/zh_chapters;      PUB_DIR=calvin/philemon ;;
    hebrews)  PUBLISH=scripts/publish_hebrews_zh.py;  RAW_DIR=calvin_raw/hebrews/zh_chapters;       PUB_DIR=calvin/hebrews ;;
    1thess)   PUBLISH=scripts/publish_1thess_zh.py;    RAW_DIR=calvin_raw/1thessalonians/zh_chapters; PUB_DIR=calvin/1thessalonians ;;
    2thess)   PUBLISH=scripts/publish_2thess_zh.py;    RAW_DIR=calvin_raw/2thessalonians/zh_chapters; PUB_DIR=calvin/2thessalonians ;;
    james)    PUBLISH=scripts/publish_james_zh.py;    RAW_DIR=calvin_raw/james/zh_chapters;   PUB_DIR=calvin/james ;;
    1peter)   PUBLISH=scripts/publish_1peter_zh.py;   RAW_DIR=calvin_raw/1peter/zh_chapters; PUB_DIR=calvin/1peter ;;
    2peter)   PUBLISH=scripts/publish_2peter_zh.py;   RAW_DIR=calvin_raw/2peter/zh_chapters; PUB_DIR=calvin/2peter ;;
    *) echo "unknown book: $BOOK"; exit 1 ;;
esac
mkdir -p $RAW_DIR $(dirname $RAW_DIR)/zh_cache

for CH in "$@"; do
    echo "=== $(date '+%H:%M:%S') 开始 $BOOK ch${CH} ==="
    [ -f "$RAW_DIR/${CH}.md" ] && chmod 644 "$RAW_DIR/${CH}.md" 2>/dev/null || true
    python3 -u scripts/translate_filibi.py --book $BOOK --chapter $CH --resume \
        > /tmp/${BOOK}_ch${CH}_translate.log 2>&1
    echo "=== $(date '+%H:%M:%S') $BOOK ch${CH} 翻译完成, 跑 publish ==="
    python3 $PUBLISH > /tmp/${BOOK}_ch${CH}_publish.log 2>&1
    chmod 444 "$RAW_DIR/${CH}.md" 2>/dev/null || true
    # commit + push
    git add "$PUB_DIR/" "$RAW_DIR/../zh_cache/" "$RAW_DIR/${CH}.md" 2>/dev/null || true
    git commit -m "feat(${BOOK}/ch${CH}): 定时任务发布中译

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>" \
        > /tmp/${BOOK}_ch${CH}_commit.log 2>&1 || echo "  (no changes to commit)"
    git push origin master > /tmp/${BOOK}_ch${CH}_push.log 2>&1 || true
    echo "=== $(date '+%H:%M:%S') $BOOK ch${CH} 完成 ==="
done
echo "=== $(date '+%H:%M:%S') 全部完成: $BOOK $@ ==="
