#!/bin/bash
# Usage: schedule_translate.sh HH:MM <book> <ch1> [ch2] ...
# 用墙钟(date +%s)轮询等到目标时刻，然后串行跑 translate_serial.sh。
# 相比 `sleep N && cmd` 的关键差别：
#   - sleep 是 CLOCK_MONOTONIC，macOS 系统挂起时暂停 → 会错过目标时刻好几个小时
#   - 这里每 30s 检查一次 date +%s，即便挂起苏醒后立刻纠偏 (最多晚 30s)
set -e
cd /Users/yanpeifa/Documents/whcjb.github.io

TIME=$1        # e.g. 19:02
shift
BOOK=$1
shift
# 剩余 args = 章节号

LOG=/tmp/schedule_${BOOK}.log

TARGET=$(date -j -f "%Y-%m-%d %H:%M:%S" "$(date +%Y-%m-%d) $TIME:00" +%s)
NOW=$(date +%s)
if [ $NOW -ge $TARGET ]; then
    TARGET=$((TARGET + 86400))   # 目标时刻已过 → 排到明天
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') 排定 $BOOK $@ 于 $(date -r $TARGET '+%Y-%m-%d %H:%M:%S') (PID=$$)" > $LOG

while [ $(date +%s) -lt $TARGET ]; do
    sleep 30
done

echo "$(date '+%Y-%m-%d %H:%M:%S') 到点，开始跑 translate_serial.sh $BOOK $@" >> $LOG
bash /Users/yanpeifa/Documents/whcjb.github.io/scripts/translate_serial.sh $BOOK "$@" >> $LOG 2>&1
echo "$(date '+%Y-%m-%d %H:%M:%S') 完成 $BOOK $@" >> $LOG
