set -e
cd "$(dirname "$0")/.."
echo "=== 1/4 正文抽取 ==="; python3 scripts/extract_davenant.py
echo "=== 2/4 正文发布 ==="; python3 scripts/publish_davenant_en.py
echo "=== 3/4 附卷 ===";     python3 scripts/extract_davenant_appx.py && python3 scripts/publish_davenant_appx.py
echo "=== 4/4 索引 ===";     python3 scripts/extract_davenant_index.py && python3 scripts/publish_davenant_index.py
echo "ALL_DONE"
