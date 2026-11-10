#!/bin/bash
# AGES《霍尔丹罗马书》PDF：sabda.org 极慢且时断时续，两个镜像地址轮流、断点续传，直到完整（pdfinfo 能读）为止。
OUT="$HOME/Documents/论文/haldane/haldane_romans_ages.pdf"
URLS=("https://media.sabda.org/alkitab-11/V6F-Z/HAL_ROMA.PDF" "https://media.sabda.org/alkitab-10/LIBRARY/COMMENT/HAL_ROMA.PDF")
for i in $(seq 1 300); do
  u=${URLS[$((i % 2))]}
  proto=$([ $((i % 4)) -lt 2 ] && echo --http1.1 || echo --http2)
  curl -sL $proto -C - -m 900 -A "Mozilla/5.0" -o "$OUT" "$u"
  rc=$?; sz=$(stat -f%z "$OUT" 2>/dev/null || echo 0)
  echo "$(date '+%T') 第 $i 次 $proto rc=$rc 已有 $sz 字节"
  if pdfinfo "$OUT" >/dev/null 2>&1; then echo "=== 完成"; pdfinfo "$OUT" | grep -E "Title|Pages|Producer"; exit 0; fi
  sleep 20
done
echo "=== 放弃"
