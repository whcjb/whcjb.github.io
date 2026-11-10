#!/bin/bash
# 霍志恒《诗篇的末世论》中译：单路翻译 → 发布中英两页 → 只提交本书路径并推送
cd "$(dirname "$0")/.."
python3 -u scripts/translate_vos.py --resume || exit $?
python3 scripts/publish_vos_psalter_zh.py || exit $?
python3 scripts/publish_vos_psalter.py || exit $?
P=(vos/psalter vos_raw/psalter/zh_chapters vos_raw/psalter/zh_cache vos_raw/psalter/zh_meta.json)
[ -f vos_raw/psalter/zh_translate_issues.log ] && P+=(vos_raw/psalter/zh_translate_issues.log)
git add -- "${P[@]}" && git commit -q -m "feat(vos): 霍志恒《诗篇的末世论》中译上线（自动发布）

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- "${P[@]}" && git push -q origin master && echo "[autopublish] 已提交并推送"
