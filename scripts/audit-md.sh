#!/usr/bin/env bash
# pdf-pipeline commit gate —— 一次跑完所有 md 发布产物检查
# 用法: bash scripts/audit-md.sh calvin/BOOK/N.md
# 对应 .claude/commands/pdf-pipeline/refs/audit-gates.md 整合脚本
# 注意: 全部用 BSD/GNU 通用的 -E(ERE)，不用 -P(macOS BSD grep 无 PCRE)
F=$1
[ -z "$F" ] && { echo "Usage: $0 <md_file>"; exit 1; }

echo "=== $F ==="
echo "1. **** count:     $(grep -c '\*\*\*\*' "$F")"
echo "2. <<<END:         $(grep -c '<<<END' "$F")"
echo "3. split italic:   $(grep -cE '\*[“”"]\*' "$F")"
# 4. front-matter 里被译成中文的键（行首非 ASCII + 冒号）；仅查 fm 区，避免正文中文句误报
fm4=$(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f' "$F" | grep -cE '^[^ -~]+[:：]')
echo "4. zh fm keys:     $fm4"
echo "5. calvin-script:  $(grep -c 'calvin-scripture' "$F")"
echo "6. long para:      $(awk 'NR>20 && length($0)>1500' "$F" | wc -l | tr -d ' ')"
echo "7. hyphen rem:     $(grep -cE '[[:alnum:]]+- [[:alnum:]]' "$F")"

ref=$(grep -oE '\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]' "$F" | grep -v ':$' | sort -u | wc -l | tr -d ' ')
def=$(grep -cE '^\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]: ' "$F")
echo "8. fn ref/def:     $ref / $def $([ "$ref" = "$def" ] && echo OK || echo MISMATCH)"

# 9 (Gate 5b): 独立 <p> 块漏 markdown 属性（含 markdown 却不处理 → 字面星号/[^fN]）
echo "9. <p> no md attr: $(grep -E '^<p [^>]*>' "$F" | grep -v 'markdown=' | grep -cE '\[\^[Ff]?[Tt]?[0-9]+\]|\*[^*]+\*')"
