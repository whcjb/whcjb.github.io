#!/bin/bash
# 霍尔丹《罗马书释义》底本抓取：StudyLight（代号 hal，BibleSupport 录入本）经互联网档案馆快照取原始 HTML；
# 1874 年第九版扫描本 OCR 当对照证人。档案馆暂时下线时每 2 分钟重试，最多 3 小时。
cd "$(dirname "$0")/.."
OUT=haldane_raw/romans/src
for i in $(seq 1 90); do
  code=$(curl -s -m 30 -o /dev/null -w "%{http_code}" "https://archive.org/wayback/available?url=studylight.org")
  [ "$code" = "200" ] && curl -s -m 30 "https://archive.org/wayback/available?url=studylight.org" | grep -q archived_snapshots && break
  echo "$(date '+%T') 档案馆未恢复（$code），2 分钟后重试"; sleep 120
done
echo "$(date '+%T') 档案馆可用，取快照索引"
curl -s -m 120 "http://web.archive.org/cdx/search/cdx?url=studylight.org/commentaries/eng/hal/*&fl=original,timestamp,statuscode&filter=statuscode:200&collapse=urlkey" > $OUT/cdx.txt
wc -l $OUT/cdx.txt
grep -iE "/hal/(romans(-[0-9]+)?)\.html" $OUT/cdx.txt | sort -k1,1 -k2,2r | awk '!seen[$1]++' > $OUT/pages.txt
cat $OUT/pages.txt
while read url ts code; do
  name=$(echo "$url" | sed -E 's#.*/hal/##')
  [ -s "$OUT/studylight/$name" ] && continue
  curl -sL -m 180 -o "$OUT/studylight/$name" "http://web.archive.org/web/${ts}id_/${url}"
  echo "取 $name $(wc -c < $OUT/studylight/$name) 字节"; sleep 3
done < $OUT/pages.txt
curl -sL -m 600 -o $OUT/scan/expositionofthee00halduoft_djvu.txt "https://archive.org/download/expositionofthee00halduoft/expositionofthee00halduoft_djvu.txt"
echo "扫描 OCR $(wc -c < $OUT/scan/expositionofthee00halduoft_djvu.txt) 字节"
echo "=== 完成"
