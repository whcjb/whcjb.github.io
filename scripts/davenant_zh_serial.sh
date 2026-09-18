#!/bin/bash
# 达文南特《歌罗西书注释》中译：一章接一章**串行**跑完。
#
# 为什么要串行：翻译走的是 claude CLI，多个进程并行会抢同一份会话额度，
# 撞墙之后每次重试照样计费（见 translate_filibi 里 SessionLimitError 那段）。
# 所以这里先等在跑的那一章退出，再一章一章往下。
#
# 退出码：42 = 会话额度用尽（已翻的段都留在 zh_cache，续跑不会重译）。
#
# 用法: nohup bash scripts/davenant_zh_serial.sh 3 1 2 > 日志 2>&1 &
#       参数是**还要跑**的章号（已经在跑的那一章也可以写上，脚本会先等它）。
set -u
cd "$(dirname "$0")/.."
CHAPTERS=${@:-"1 2"}

while pgrep -f "translate_davenant.py --chapter" > /dev/null; do sleep 30; done

for n in $CHAPTERS; do
  # 已经跑完的章（缓存全命中）跳过重译：dry-run 报 0 缺口就不必再调 CLI
  need=$(python3 -u scripts/translate_davenant.py --chapter "$n" --dry-run 2>/dev/null \
         | head -1 | sed -E 's/.*需译 ([0-9]+).*缓存命中 ([0-9]+).*/\1 \2/')
  set -- $need
  if [ "${1:-1}" = "${2:-0}" ]; then
    echo "=== ch$n 全部命中缓存，跳过 $(date '+%F %T') ==="
    continue
  fi
  echo "=== ch$n 开始 $(date '+%F %T')（需译 ${1:-?} / 命中 ${2:-?}）==="
  python3 -u scripts/translate_davenant.py --chapter "$n" --resume --publish
  rc=$?
  echo "=== ch$n 结束 rc=$rc $(date '+%F %T') ==="
  [ $rc -eq 42 ] && { echo "会话额度用尽，停在 ch$n；额度恢复后重跑本脚本即可续"; exit 42; }
  [ $rc -ne 0 ] && { echo "ch$n 失败 rc=$rc，停"; exit $rc; }
done
echo "ALL_DONE $(date '+%F %T')"
