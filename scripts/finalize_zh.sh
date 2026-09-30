#!/bin/zsh
# 中译跑完后的收尾：锚点 → 经文索引 → 总目文案 → 全站索引 → 提交推送。
#
# 为什么要脚本化：这几步每次都一样，漏一步就少一样东西，而且翻译要跑十几个
# 小时，收尾时人未必在。用法是把它挂在翻译进程后面：
#
#   (wait_for_pid; scripts/finalize_zh.sh durham) &
#
# 参数：作者 id（durham / spurgeon）。每个作者的锚点脚本不同，见下。
set -e
cd "$(dirname "$0")/.."
AUTHOR="$1"
case "$AUTHOR" in
  durham)   BOOK=revelation; CH_TOTAL=22; NAME_ZH='达拉谟《启示录注释》'
            ANCHOR="python3 scripts/add_durham_verse_anchors.py" ;;
  spurgeon) BOOK=matthew;    CH_TOTAL=28; NAME_ZH='司布真《天国的福音——马太福音通俗释经》'
            ANCHOR="python3 scripts/add_hodge_verse_anchors.py --author spurgeon --book matthew" ;;
  *) echo "用法: finalize_zh.sh <durham|spurgeon>" >&2; exit 2 ;;
esac

echo "=== [$AUTHOR/$BOOK] 收尾开始 $(date '+%F %T')"

# 0. 中文书首页。没有它，中文章节虽然生成了也没有入口——英文书首页的
#    「中文版 →」会点成 404（2026-09-30 用户发现达拉谟与司布真两本都缺）。
if [ ! -f "$AUTHOR/$BOOK/zh/index.html" ]; then
  mkdir -p "$AUTHOR/$BOOK/zh"
  cat > "$AUTHOR/$BOOK/zh/index.html" <<EOF
---
layout: $AUTHOR-book
book_id: $BOOK
book_name: "$NAME_ZH"
chapters: $CH_TOTAL
has_preface: true
zh: true
---
EOF
  echo "  生成中文书首页 $AUTHOR/$BOOK/zh/index.html"
fi

# 1. 标点归一（翻译落盘时已内置，这里再扫一遍兜底；嵌套/不成对的文件会跳过并报出）
python3 scripts/normalize_zh_quotes.py "$AUTHOR/$BOOK/zh" || true

# 2. 中文页节锚点 + 中英两侧经文索引
eval "$ANCHOR"
python3 scripts/build_hodge_verse_index.py --book "$BOOK"

# 3. audit：任何一项非 0 都打印出来，但不中断收尾
echo "--- audit-md"
for f in "$AUTHOR/$BOOK/zh"/*.md; do
  r=$(bash scripts/audit-md.sh "$f" | awk '/^[1-9]\./{print $NF}' | tr '\n' ' ')
  case "$r" in *[1-9]*) echo "  $f: $r" ;; esac
done

# 4. 全站索引（历代解经 / 对照源 / 首页最新 / sitemap）
python3 scripts/build_commentaries_index.py | tail -2
python3 scripts/update-recent.py | tail -1
python3 scripts/build_sitemap.py | tail -1

# 5. 亚历山大以赛亚书的中译只译了 3 章，生成器却按 min/max 写成 ch_to 40，
#    挂上去是三十多条死链。本次不纳入，等那本书自己决定。
python3 - <<'PY'
import pathlib
p=pathlib.Path('_data/compare_sources.yml'); s=p.read_text(encoding='utf-8')
line='    - {key: alexander, author: alexander, lang: zh, label: "亚历山大注释", url_tpl: "/alexander/isaiah/zh/__CH__/", accent: "#7d2f2f", ch_from: 1, ch_to: 40}\n'
if line in s: p.write_text(s.replace(line,'',1),encoding='utf-8'); print('  摘掉 isaiah zh 对照条目')
p=pathlib.Path('_data/commentaries.yml'); s=p.read_text(encoding='utf-8')
new='- {author: alexander, path: "/alexander/isaiah/zh/", url_tpl: "/alexander/isaiah/zh/__CH__/"'
old='- {author: alexander, path: "/alexander/isaiah/", url_tpl: "/alexander/isaiah/__CH__/"'
if new in s: p.write_text(s.replace(new,old),encoding='utf-8'); print('  isaiah 入口改回英文页')
PY

# 6. 提交推送。只收本作者的目录与全站索引，绝不带上别的会话在改的文件。
git add "$AUTHOR/" "${AUTHOR}_raw/" _data/ pages/ sitemap.xml
N=$(git diff --cached --name-only | wc -l | tr -d ' ')
CH=$(ls "$AUTHOR/$BOOK/zh"/[0-9]*.md 2>/dev/null | wc -l | tr -d ' ')
git commit -q -m "feat($AUTHOR/$BOOK): 中译全本上线（$CH 章）

翻译由 scripts/translate_$AUTHOR.py 跑完后自动收尾（scripts/finalize_zh.sh）：
标点归一 → 节锚点 → 中英经文索引 → audit → 全站索引 → 提交。
CLI 走 CLI_TRIM_FLAGS，不发工具定义/MCP/CLAUDE.md/skills/hooks。

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
git push -q origin master
echo "=== [$AUTHOR/$BOOK] 收尾完成，已推送（$N 个文件，$CH 章中译） $(date '+%F %T')"
