#!/bin/bash
# 串行翻译 1thess ch3 → ch4 → ch5
# 每章翻完后自动 publish + chmod 444
set -e
cd /Users/yanpeifa/Documents/whcjb.github.io

for CH in 3 4 5; do
    echo "=== $(date '+%H:%M:%S') 开始 ch${CH} ==="
    # unlock raw if exists (rerun 支持)
    [ -f "calvin_raw/1thessalonians/zh_chapters/${CH}.md" ] && \
        chmod 644 "calvin_raw/1thessalonians/zh_chapters/${CH}.md" 2>/dev/null || true
    python3 -u scripts/translate_filibi.py --book 1thess --chapter $CH --resume \
        > /tmp/1thess_ch${CH}_translate.log 2>&1
    echo "=== $(date '+%H:%M:%S') ch${CH} 翻译完成, 跑 publish ==="
    # 每 5 章都可跑一次 publish (它会 detect 已译章节)
    python3 scripts/publish_1thess_zh.py > /tmp/1thess_ch${CH}_publish.log 2>&1
    chmod 444 "calvin_raw/1thessalonians/zh_chapters/${CH}.md" 2>/dev/null || true
    echo "=== $(date '+%H:%M:%S') ch${CH} 完成 ==="
done
echo "=== $(date '+%H:%M:%S') 全部完成 ==="
