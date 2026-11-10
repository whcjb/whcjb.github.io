#!/bin/bash
# 精简本地预览：只构建指定目录（外加首页、历代解经、站点公共资源），其余大书卷目录排除。
# 用途：改版面 / _data / layout 时不必等 3 分钟全量重建。线上（GitHub Pages）不受影响。
#
#   scripts/serve_lite.sh                    # 只看历代解经（commentaries）
#   scripts/serve_lite.sh vos alexander      # 另外带上 vos、alexander 目录
#   PORT=4002 scripts/serve_lite.sh vos      # 换端口（默认 4002，不和全量预览 4001 抢）
#
# 做法：生成临时配置 _config_lite.yml，把「内容目录」中未点名的全部加进 exclude，
# 用 `--config _config.yml,_config_lite.yml` 叠加（Jekyll 合并时数组整体覆盖，所以要带上原 exclude）。
set -e
cd "$(dirname "$0")/.."
PORT=${PORT:-4002}
KEEP=" commentaries $* "
python3 - "$KEEP" <<'PY'
import sys, yaml, pathlib
keep = set(sys.argv[1].split())
base = yaml.safe_load(open('_config.yml'))
exc = list(base.get('exclude', []))
# 内容目录：含 .md/.html、不以 _ 开头、不是站点公共资源
common = {'css', 'js', 'img', 'fonts', 'assets', 'pwa', 'search', 'creeds', 'pages', 'commentaries'}
for d in sorted(pathlib.Path('.').iterdir()):
    n = d.name
    if not d.is_dir() or n.startswith(('_', '.')) or n in common or n in keep or n.endswith('_raw'):
        continue
    if any(d.rglob('*.md')) or any(d.rglob('*.html')):
        exc.append(n)
exc += ['_posts']
yaml.safe_dump({'exclude': exc, 'incremental': False}, open('_config_lite.yml', 'w'), allow_unicode=True)
print('排除', len(exc), '项；保留：', ' '.join(sorted(keep)))
PY
exec bundle exec jekyll serve --port "$PORT" --config _config.yml,_config_lite.yml --destination _site_lite
