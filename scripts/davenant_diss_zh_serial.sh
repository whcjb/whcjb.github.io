#!/bin/bash
# 达文南特附卷《论基督之死》中译：一篇接一篇**串行**跑完，每篇译完即发布并提交。
#
# 单路（翻译只跑 1 路，见 translate_filibi.PARALLEL）。退出码：
#   42 = 会话额度用尽（已翻的段留在 zh_cache，续跑不重译）→ 整批停
#    3 = 译后闸两轮重译仍不合格 → 这一篇不发布，整批停，等人看
#
# 用法: nohup bash scripts/davenant_diss_zh_serial.sh 1 2 3 4 5 6 7 > 日志 2>&1 &
set -u
cd "$(dirname "$0")/.."
PIECES=${@:-"1 2 3 4 5 6 7"}

for n in $PIECES; do
  echo "=== diss$n 开始 $(date '+%F %T') ==="
  python3 -u scripts/translate_davenant.py --diss "$n" --resume --publish
  rc=$?
  echo "=== diss$n 结束 rc=$rc $(date '+%F %T') ==="
  [ $rc -ne 0 ] && { echo "停在 diss$n（rc=$rc）"; exit $rc; }

  # 英文附卷页挂上 zh_url（publish_davenant_appx 看到 <篇>/zh/index.md 就加）
  python3 scripts/publish_davenant_appx.py > /dev/null || { echo "appx 发布失败"; exit 1; }

  new_cache=$(git status --porcelain davenant_raw/colossians/zh_cache | awk '{print $2}')
  git add -- davenant/colossians/dissertation davenant/colossians/gallican.md \
    davenant_raw/colossians/zh_chapters/diss-$n.md davenant_raw/colossians/zh_meta.json $new_cache
  git commit -q -m "feat(davenant): 论基督之死中译 · $( [ "$n" = 0 ] && echo 致读者 || echo 第${n}章 )（自动发布）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01FNabi3cLWqncRdwGfXkpHL" -- \
    davenant/colossians/dissertation davenant/colossians/gallican.md \
    davenant_raw/colossians/zh_chapters/diss-$n.md davenant_raw/colossians/zh_meta.json $new_cache \
    && git push -q origin master && echo "✓ diss$n 已提交 $(git log --oneline -1)"
done
echo "ALL_DONE $(date '+%F %T')"
