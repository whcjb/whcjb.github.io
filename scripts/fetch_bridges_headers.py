#!/usr/bin/env python3
"""为毕列志《箴言书注释》各章下载独立的风景头图。

每章一张不同的图，与 mhenry(nt-bg-*)/calvin 的图池互不共用——见
memory: feedback_book_style_isolation（样式按书隔离）。

图源 Unsplash 搜索接口，按 alt_description 过滤掉人像/城市/室内等非风景题材。
产物：img/bridges-bg-NN.jpg + _data/bridges_image_provenance.yml（记 photo id
与作者，便于日后重新拉取或署名；沿用 _data/nt_image_provenance.yml 的做法）。

用法:
    python3 scripts/fetch_bridges_headers.py --list          # 只看候选，不下载
    python3 scripts/fetch_bridges_headers.py --count 34      # 下载
"""
import argparse, json, re, subprocess, time, urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / 'img'
PROV = ROOT / '_data/bridges_image_provenance.yml'
PREFIX = 'bridges-bg'

QUERIES = ['mountain landscape', 'valley', 'forest path', 'lake sunrise',
           'meadow hills', 'river valley', 'desert landscape', 'sea cliff',
           'autumn forest', 'misty mountains', 'wheat field', 'olive grove']

GOOD = re.compile(r'\b(mountain|valley|forest|lake|river|sea|ocean|coast|cliff|'
                  r'field|meadow|hill|tree|sky|cloud|sunset|sunrise|desert|dune|'
                  r'lagoon|waterfall|glacier|snow|grass|landscape|shore|island)\b', re.I)
BAD = re.compile(r'\b(person|people|man|woman|men|women|girl|boy|child|face|'
                 r'portrait|city|building|urban|street|car|room|interior|food|'
                 r'dog|cat|selfie|crowd|hand|phone|laptop|tattoo)\b', re.I)

# ⚠️ 必须用 curl 自带的 UA：带 Mozilla UA 请求 napi 会被 307 重定向到验证页
# （随后 401）；裸 curl 直接 200。所以这里走 subprocess 而非 urllib。
def fetch_json(url):
    r = subprocess.run(['curl', '-sS', '-m', '30', '-H', 'Accept-Version: v1', url],
                       capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(f'curl rc={r.returncode} {r.stderr[:80]}')
    return json.loads(r.stdout)


def candidates():
    seen, out = set(), []
    for q in QUERIES:
        for page in (1, 2):
            url = ('https://unsplash.com/napi/search/photos?query='
                   + urllib.parse.quote(q) + f'&per_page=30&page={page}')
            try:
                data = fetch_json(url)
            except Exception as e:
                print(f'  !! {q} p{page}: {e}')
                continue
            for r in data.get('results', []):
                pid = r.get('id')
                alt = (r.get('alt_description') or '') + ' ' + (r.get('description') or '')
                if not pid or pid in seen:
                    continue
                if BAD.search(alt) or not GOOD.search(alt):
                    continue
                if (r.get('width') or 0) < (r.get('height') or 1):
                    continue                      # 只要横图，竖图铺满会裁掉主体
                seen.add(pid)
                out.append({'id': pid, 'alt': alt.strip()[:90], 'q': q,
                            'author': (r.get('user') or {}).get('name') or '?',
                            'url': (r.get('urls') or {}).get('raw') or ''})
            time.sleep(0.6)
    # 按关键词轮转打散：否则前 34 张全是 mountain（候选是按 query 顺序追加的），
    # 33 章的背景要看得出差别。
    buckets = {}
    for c in out:
        buckets.setdefault(c['q'], []).append(c)
    mixed, i = [], 0
    while any(buckets.values()):
        for q in list(buckets):
            if buckets[q]:
                mixed.append(buckets[q].pop(0))
    return mixed


def yaml_str(s: str) -> str:
    """YAML 双引号标量：Unsplash 的 description 自带换行和引号，不清洗会把
    _data/*.yml 写坏，jekyll build 直接崩在 Psych::SyntaxError。"""
    s = re.sub(r'\s+', ' ', (s or '')).strip()
    return s.replace('\\', ' ').replace('"', "'").strip()


def download(item, dest: Path):
    src = item['url']
    src = (src + ('&' if '?' in src else '?') + 'w=1800&q=80&fm=jpg&fit=max'
           if src else f"https://images.unsplash.com/photo-{item['id']}?w=1800&q=80")
    r = subprocess.run(['curl', '-sS', '-L', '-m', '90', '-o', str(dest), src])
    if r.returncode != 0 or not dest.exists():
        raise RuntimeError(f'curl rc={r.returncode}')
    size = dest.stat().st_size
    if size < 40_000:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f'too small: {size}')
    return size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--count', type=int, default=34)
    ap.add_argument('--list', action='store_true')
    args = ap.parse_args()

    cands = candidates()
    print(f'候选 {len(cands)} 张（已过滤人像/城市/竖图）')
    if args.list:
        for c in cands[:40]:
            print(f'  {c["id"]:14s} {c["author"][:18]:20s} {c["alt"]}')
        return

    prov, n = [], 0
    for c in cands:
        if n >= args.count:
            break
        dest = IMG / f'{PREFIX}-{n+1:02d}.jpg'
        try:
            size = download(c, dest)
        except Exception as e:
            print(f'  !! {c["id"]}: {e}')
            continue
        n += 1
        prov.append((dest.name, c))
        print(f'  ✓ {dest.name}  {size//1024}KB  {c["author"][:16]:18s} {c["alt"][:52]}')
        time.sleep(0.4)

    lines = ['# 毕列志《箴言书注释》各章头图来源（Unsplash）。',
             '# 由 scripts/fetch_bridges_headers.py 下载；每章一张，与 nt-bg-*/calvin 图池不共用。',
             '# 重新拉取：https://images.unsplash.com/photo-{id}?w=1800&q=80',
             'images:']
    for name, c in prov:
        lines.append(f'  {name}:')
        lines.append(f'    id: {c["id"]}')
        lines.append(f'    author: "{yaml_str(c["author"])}"')
        lines.append(f'    alt: "{yaml_str(c["alt"])}"')
    PROV.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'\n下载 {n} 张，来源已记入 {PROV.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
