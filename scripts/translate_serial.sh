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
    1john)    PUBLISH=scripts/publish_1john_zh.py;    RAW_DIR=calvin_raw/1john/zh_chapters;  PUB_DIR=calvin/1john ;;
    jude)     PUBLISH=scripts/publish_jude_zh.py;     RAW_DIR=calvin_raw/jude/zh_chapters;  PUB_DIR=calvin/jude ;;
    genesis)  PUBLISH=scripts/publish_genesis_zh.py;  RAW_DIR=calvin_raw/genesis/zh_chapters; PUB_DIR=calvin/genesis ;;
    harmony-law-1) PUBLISH="scripts/publish_harmony_law_zh.py --vol 1"; RAW_DIR=calvin_raw/harmony-law-1/zh_chapters; PUB_DIR=calvin/harmony-law-1 ;;
    harmony-law-2) PUBLISH="scripts/publish_harmony_law_zh.py --vol 2"; RAW_DIR=calvin_raw/harmony-law-2/zh_chapters; PUB_DIR=calvin/harmony-law-2 ;;
    isaiah-1) PUBLISH=scripts/publish_isaiah_zh.py; RAW_DIR=calvin_raw/isaiah-1/zh_chapters; PUB_DIR=calvin/isaiah-1 ;;
    isaiah-2) PUBLISH=scripts/publish_isaiah_zh.py; RAW_DIR=calvin_raw/isaiah-2/zh_chapters; PUB_DIR=calvin/isaiah-2 ;;
    jeremiah-1) PUBLISH=scripts/publish_jeremiah_zh.py; RAW_DIR=calvin_raw/jeremiah-1/zh_chapters; PUB_DIR=calvin/jeremiah-1 ;;
    jeremiah-2) PUBLISH=scripts/publish_jeremiah_zh.py; RAW_DIR=calvin_raw/jeremiah-2/zh_chapters; PUB_DIR=calvin/jeremiah-2 ;;
    malachi)  PUBLISH=scripts/publish_malachi_zh.py;  RAW_DIR=calvin_raw/malachi/zh_chapters;  PUB_DIR=calvin/malachi ;;
    amos)     PUBLISH=scripts/publish_amos_zh.py; RAW_DIR=calvin_raw/amos/zh_chapters; PUB_DIR=calvin/amos ;;
    obadiah)  PUBLISH=scripts/publish_obadiah_zh.py; RAW_DIR=calvin_raw/obadiah/zh_chapters; PUB_DIR=calvin/obadiah ;;
    jonah)    PUBLISH=scripts/publish_jonah_zh.py; RAW_DIR=calvin_raw/jonah/zh_chapters; PUB_DIR=calvin/jonah ;;
    micah)    PUBLISH=scripts/publish_micah_zh.py; RAW_DIR=calvin_raw/micah/zh_chapters; PUB_DIR=calvin/micah ;;
    nahum)    PUBLISH=scripts/publish_nahum_zh.py; RAW_DIR=calvin_raw/nahum/zh_chapters; PUB_DIR=calvin/nahum ;;
    habakkuk) PUBLISH=scripts/publish_habakkuk_zh.py; RAW_DIR=calvin_raw/habakkuk/zh_chapters; PUB_DIR=calvin/habakkuk ;;
    zephaniah)PUBLISH=scripts/publish_zephaniah_zh.py; RAW_DIR=calvin_raw/zephaniah/zh_chapters; PUB_DIR=calvin/zephaniah ;;
    haggai)   PUBLISH=scripts/publish_haggai_zh.py; RAW_DIR=calvin_raw/haggai/zh_chapters; PUB_DIR=calvin/haggai ;;
    zechariah)PUBLISH=scripts/publish_zechariah_zh.py; RAW_DIR=calvin_raw/zechariah/zh_chapters; PUB_DIR=calvin/zechariah ;;
    joel)     PUBLISH=scripts/publish_joel_zh.py;     RAW_DIR=calvin_raw/joel/zh_chapters;     PUB_DIR=calvin/joel ;;
    lamentations) PUBLISH=scripts/publish_lamentations_zh.py; RAW_DIR=calvin_raw/lamentations/zh_chapters; PUB_DIR=calvin/lamentations ;;
    daniel)   PUBLISH=scripts/publish_daniel_zh.py;   RAW_DIR=calvin_raw/daniel/zh_chapters;   PUB_DIR=calvin/daniel ;;
    ezekiel)  PUBLISH=scripts/publish_ezekiel_zh.py;  RAW_DIR=calvin_raw/ezekiel/zh_chapters;  PUB_DIR=calvin/ezekiel ;;
    hosea)      PUBLISH=scripts/publish_hosea_zh.py;    RAW_DIR=calvin_raw/hosea/zh_chapters;      PUB_DIR=calvin/hosea ;;
    psalms-1) PUBLISH=scripts/publish_psalms_zh.py; RAW_DIR=calvin_raw/psalms-1/zh_chapters; PUB_DIR=calvin/psalms-1 ;;
    psalms-2) PUBLISH=scripts/publish_psalms_zh.py; RAW_DIR=calvin_raw/psalms-2/zh_chapters; PUB_DIR=calvin/psalms-2 ;;
     *) echo "unknown book: $BOOK"; exit 1 ;;
esac
mkdir -p $RAW_DIR $(dirname $RAW_DIR)/zh_cache

# 串行锁：并发调用（如即时批次与定时批次重叠）时排队，避免 git index / push 竞争。
#
# 原来是 `while ! mkdir "$LOCK"; do sleep 30; done`，只保证互斥、不保证顺序：
# 锁一空是谁的 sleep 恰好先醒谁拿走，排最久的可能永远抢不上。真发生过两次——
# jeremiah-1 排 33 小时、daniel 排 10 小时 42 分，都是一章没跑成。
# 现在换成 scripts/fifo_lock.py 的取号排队，先到先得，排队者崩溃会被自动清号。
TICKET=$(python3 "$(dirname "$0")/fifo_lock.py" take "$BOOK" $$)
trap 'rm -f "$TICKET"' EXIT INT TERM
python3 "$(dirname "$0")/fifo_lock.py" wait "$TICKET"

for CH in "$@"; do
    echo "=== $(date '+%H:%M:%S') 开始 $BOOK ch${CH} ==="
    [ -f "$RAW_DIR/${CH}.md" ] && chmod 644 "$RAW_DIR/${CH}.md" 2>/dev/null || true
    # 普通失败跳过本章继续；缓存已存进度, 下次 --resume 续。
    # 退出码 42 是撞会话额度, 后面每章都会撞同一堵墙, 直接中止整批不再空烧。
    python3 -u scripts/translate_filibi.py --book $BOOK --chapter $CH --resume \
            > /tmp/${BOOK}_ch${CH}_translate.log 2>&1
    RC=$?
    if [ $RC -eq 42 ]; then
        echo "!!! $(date '+%H:%M:%S') $BOOK ch${CH} 撞会话额度, 中止整批"
        tail -3 /tmp/${BOOK}_ch${CH}_translate.log
        exit 42
    fi
    if [ $RC -ne 0 ]; then
        echo "!!! $(date '+%H:%M:%S') $BOOK ch${CH} 翻译失败(rc=$RC), 跳过 publish, 继续下一章"
        tail -5 /tmp/${BOOK}_ch${CH}_translate.log
        continue
    fi
    # 诗篇: 正文里是 fa/fc 死标记, 中文定义得单独译, 否则 publish 还原不出脚注
    case "$BOOK" in
        psalms-*)
            echo "=== $(date '+%H:%M:%S') $BOOK ch${CH} 译脚注定义 ==="
            # 不限 --chapters: 缓存命中的免费跳过, 顺带补上别的批次漏译的 code
            python3 -u scripts/translate_psalms_footnotes.py --vol "${BOOK#psalms-}" \
                > /tmp/${BOOK}_ch${CH}_fn.log 2>&1 \
                || echo "  (脚注翻译失败, 继续 publish)"
            ;;
    esac
    echo "=== $(date '+%H:%M:%S') $BOOK ch${CH} 翻译完成, 跑 publish ==="
    python3 $PUBLISH > /tmp/${BOOK}_ch${CH}_publish.log 2>&1
    chmod 444 "$RAW_DIR/${CH}.md" 2>/dev/null || true
    # commit + push
    git add "$PUB_DIR/" "$RAW_DIR/../zh_cache/" "$RAW_DIR/${CH}.md" 2>/dev/null || true
    case "$BOOK" in
        psalms-*) git add "$RAW_DIR/../zh_footnote_cache/" \
                          "$RAW_DIR/../zh_footnote_defs.json" 2>/dev/null || true ;;
    esac
    git commit -m "feat(${BOOK}/ch${CH}): 定时任务发布中译

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>" \
        > /tmp/${BOOK}_ch${CH}_commit.log 2>&1 || echo "  (no changes to commit)"
    git push origin master > /tmp/${BOOK}_ch${CH}_push.log 2>&1 || true
    echo "=== $(date '+%H:%M:%S') $BOOK ch${CH} 完成 ==="
done
echo "=== $(date '+%H:%M:%S') 全部完成: $BOOK $@ ==="
