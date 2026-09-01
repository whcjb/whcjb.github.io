#!/bin/bash
# 贺智《哥林多前书》英译中，串行一路。
#   bash scripts/translate_hodge_batch.sh [book]
# 已有中文页的章自动跳过，所以"续跑"就是原样再执行一次。
# 退出码 42 = 会话额度用尽 → 中止，已翻段落都在 zh_cache 里，恢复后重跑即续。
# ⚠️ 变量一律写 ${x}：$x 后紧跟中文标点时 bash 会把多字节首字节吞进变量名。
set -u
cd "$(dirname "$0")/.."
BOOK=${1:-1corinthians}

secs="preface $(ls hodge/${BOOK}/[0-9]*.md 2>/dev/null | sed 's#.*/##;s#\.md##' | sort -n | tr '\n' ' ')"
total=$(echo ${secs} | wc -w | tr -d ' ')
i=0
echo "▶ 贺智 ${BOOK}  ${total} 节  $(date '+%F %T')"
for s in ${secs}; do
  i=$((i + 1))
  if [ -f "hodge/${BOOK}/zh/${s}.md" ]; then
    echo "── [${i}/${total}] ${s} 已有中文页，跳过"; continue
  fi
  echo "════════ [${i}/${total}] ${BOOK}/${s}  $(date '+%F %T') ════════"
  python3 -u scripts/translate_hodge.py --book "${BOOK}" --sections "${s}" --resume --publish
  rc=$?
  if [ ${rc} -eq 42 ]; then
    echo "!! 会话额度用尽，中止。已翻段落已入 zh_cache，恢复后原样重跑即续。"; exit 42
  fi
  if [ ${rc} -ne 0 ]; then echo "!! ${BOOK}/${s} 失败 rc=${rc}，中止。"; exit "${rc}"; fi
done
echo "════════ 全部完成  $(date '+%F %T') ════════"
