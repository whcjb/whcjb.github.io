#!/bin/bash
# 欧文《希伯来书注释》批量中译 —— 按 scripts/owen_tasks.txt 的顺序串行跑。
#
#   bash scripts/translate_owen_batch.sh
#
# 清单里已经有中文页（<页目录>/zh/index.md）的自动跳过，所以"续跑"就是原样
# 再执行一次，不必记进度、不必传起始点。进程被 kill、断电都不会错乱。
#
# 其余设计同前：串行（并发只会更快撞额度）、排 fifo_lock 队列、每篇跑完立刻
# 发布、退出码 42（额度用尽）中止整批交给看守处理。
#
# ⚠️ 变量一律写成 ${x}：$x 后面紧跟中文标点时，bash 会把多字节的头一个字节
#    当成变量名的一部分（实测报 `FROM<0xef>: unbound variable`、`rc<0xef>`）。
set -u
cd "$(dirname "$0")/.."
LIST=${1:-scripts/owen_tasks.txt}

TICKET=$(python3 scripts/fifo_lock.py take "owen-batch" $$)
trap 'rm -f "${TICKET}"' EXIT INT TERM
python3 scripts/fifo_lock.py wait "${TICKET}"

total=$(grep -c . "${LIST}")
i=0
echo "▶ 批量中译 ${total} 篇  $(date '+%F %T')"
while IFS= read -r src; do
  [ -n "${src}" ] || continue
  i=$((i + 1))
  [ -f "${src}" ] || { echo "── [${i}/${total}] ${src} 不存在，跳过"; continue; }
  zh="${src%/index.md}/zh/index.md"
  if [ -f "${zh}" ]; then
    echo "── [${i}/${total}] ${src} 已有中文页，跳过"
    continue
  fi
  echo "════════ [${i}/${total}] ${src}  $(date '+%F %T') ════════"
  TRANSLATE_PARALLEL=1 python3 -u scripts/translate_owen.py \
      --page "${src}" --resume --publish
  rc=$?
  if [ ${rc} -eq 42 ]; then
    echo "!! 会话额度用尽，中止整批。已翻段落已入 zh_cache，恢复后原样重跑即可续。"
    exit 42
  fi
  if [ ${rc} -ne 0 ]; then
    echo "!! ${src} 失败 rc=${rc}，中止。修好后原样重跑。"
    exit "${rc}"
  fi
done < "${LIST}"
echo "════════ 全部完成  $(date '+%F %T') ════════"
