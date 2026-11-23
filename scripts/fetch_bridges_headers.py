#!/usr/bin/env python3
"""为毕列志《箴言书注释》各章下载独立的风景头图。

每章一张不同的图，与 mhenry(nt-bg-*)/calvin 的图池互不共用——见
memory: feedback_book_style_isolation（样式按书隔离）。

图源 Unsplash 搜索接口，按 alt_description 过滤掉人像/城市/室内等非风景题材。
产物：img/bridges-bg-NN.jpg + _data/bridges_image_provenance.yml（记 photo id
与作者，便于日后重新拉取或署名；沿用 _data/nt_image_provenance.yml 的做法）。

用法:
    python3 scripts/fetch_bridges_headers.py --list          # 只看候选，不下载
    python3 scripts/fetch_bridges_headers.py --count 34      # 下载（箴言）
    python3 scripts/fetch_bridges_headers.py --book ecclesiastes --count 14
        # 传道书：图名 bridges-eccl-bg-NN.jpg，来源记 _data/bridges_eccl_image_provenance.yml；
        # 关键词换成传道书的意象（日出日落、风、江河归海、落叶、四季），并排除箴言已用过的图
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


# 传道书 1:4–7「一代过去，一代又来…日头出来，日头落下…风往南刮…江河都往海里流」、3:1–8 定时、12 章衰老
BOOKS = {
    'proverbs': dict(prefix='bridges-bg', prov='bridges_image_provenance.yml', title='毕列志《箴言书注释》', queries=QUERIES),
    'ecclesiastes': dict(prefix='bridges-eccl-bg', prov='bridges_eccl_image_provenance.yml', title='毕列志《传道书释义》',
                         queries=['sunrise horizon', 'sunset sea', 'wind grass field', 'river to the sea',
                                  'autumn leaves forest', 'winter landscape', 'desert dunes', 'stormy sea',
                                  'evening clouds sky', 'vineyard hills', 'misty valley', 'spring meadow']),
}


def candidates(queries=QUERIES, exclude=()):
    seen, out = set(exclude), []
    for q in queries:
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


# ── 维基共享资源（2026-11-23 起 Unsplash napi 挂了 bot 验证，307→401，改用 Commons）──────────
# 取「风景类特色图片」分类，全是社群评选过的高质量照片，授权明确（CC BY-SA / PD），来源文件记作者与许可证以便署名。
COMMONS_API = 'https://commons.wikimedia.org/w/api.php'
COMMONS_CATS = ['Category:Featured_pictures_of_landscapes', 'Category:Featured_pictures_of_rivers',
                'Category:Featured_pictures_of_seas_and_oceans', 'Category:Featured_pictures_of_skies',
                'Category:Featured_pictures_of_deserts', 'Category:Featured_pictures_of_forests']
COMMONS_BAD = re.compile(r'\b(castle|ch[aâ]teau|church|chapel|temple|monastery|abbey|bridge|viaduct|village|town|city|'
                         r'house|building|tower|ruin|road|railway|train|person|people|man|woman|boat|ship|harbou?r|'
                         r'fort|palace|street|car|tent|hut|cabin|wind ?turbine|power|dam)\b', re.I)


def commons_candidates(themes, exclude=()):
    import urllib.request
    seen, out = set(exclude), []
    for cat in COMMONS_CATS:
        cont = {}
        for _ in range(4):
            q = dict(action='query', format='json', generator='categorymembers', gcmtitle=cat, gcmtype='file',
                     gcmlimit='200', prop='imageinfo', iiprop='url|size|extmetadata', iiurlwidth='1800', **cont)
            data = None
            for wait in (0, 10, 30, 60):             # Commons 对连发请求回 429，退避重试
                time.sleep(wait)
                r = subprocess.run(['curl', '-sS', '-m', '60', '-A', 'whcjb-site-image-fetch/1.0 (https://whcjb.github.io)',
                                    COMMONS_API + '?' + urllib.parse.urlencode(q)], capture_output=True, text=True)
                try:
                    data = json.loads(r.stdout)
                    break
                except ValueError:
                    continue
            if data is None:
                print(f'  !! {cat}: Commons 连续拒绝'); break
            for pg in data.get('query', {}).get('pages', {}).values():
                ii = (pg.get('imageinfo') or [{}])[0]
                m = ii.get('extmetadata', {})
                w, h = ii.get('width', 0), ii.get('height', 1)
                desc = re.sub(r'<[^>]+>', ' ', m.get('ImageDescription', {}).get('value', ''))
                text = pg['title'] + ' ' + desc
                lic = m.get('LicenseShortName', {}).get('value', '')
                if pg['title'] in seen or not (1.4 <= w / h <= 1.8) or w < 2400 or COMMONS_BAD.search(text):
                    continue
                if not re.search(r'CC BY|CC0|Public domain', lic, re.I):
                    continue
                theme = next((t for t, rx in themes if re.search(rx, text, re.I)), None)
                if not theme:
                    continue
                seen.add(pg['title'])
                out.append({'id': pg['title'], 'q': theme, 'alt': re.sub(r'\s+', ' ', desc).strip()[:90] or pg['title'],
                            'author': re.sub(r'<[^>]+>', '', m.get('Artist', {}).get('value', '?')).strip()[:60],
                            'license': lic, 'page': ii.get('descriptionurl', ''), 'url': ii.get('thumburl', '')})
            if 'continue' not in data:
                break
            cont = {k: v for k, v in data['continue'].items()}
            time.sleep(2)
    buckets = {}
    for c in out:
        buckets.setdefault(c['q'], []).append(c)
    mixed = []
    while any(buckets.values()):
        for q in list(buckets):
            if buckets[q]:
                mixed.append(buckets[q].pop(0))
    return mixed


ECCL_THEMES = [('日出日落', r'sun ?rise|sun ?set|dawn|dusk|twilight'), ('江河归海', r'river|estuary|delta|stream'),
               ('海', r'\bsea\b|ocean|coast|wave'), ('风与草', r'wind|grass|steppe|prairie|meadow'),
               ('秋', r'autumn|fall foliage|leaves'), ('冬', r'winter|snow|frost'), ('沙漠', r'desert|dune|sand'),
               ('云天', r'cloud|sky|storm|rainbow'), ('山谷雾', r'mist|fog|valley'), ('田野', r'field|vineyard|harvest')]


def yaml_str(s: str) -> str:
    """YAML 双引号标量：Unsplash 的 description 自带换行和引号，不清洗会把
    _data/*.yml 写坏，jekyll build 直接崩在 Psych::SyntaxError。"""
    s = re.sub(r'\s+', ' ', (s or '')).strip()
    return s.replace('\\', ' ').replace('"', "'").strip()


def download(item, dest: Path):
    src = item['url']
    if item['id'].startswith('File:'):                     # Commons：thumburl 已是 1800 宽
        r = subprocess.run(['curl', '-sS', '-L', '-m', '90', '-A', 'whcjb-site-image-fetch/1.0', '-o', str(dest), src])
        if r.returncode != 0 or not dest.exists() or dest.stat().st_size < 40_000:
            dest.unlink(missing_ok=True)
            raise RuntimeError(f'curl rc={r.returncode}')
        return dest.stat().st_size
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
    ap.add_argument('--book', default='proverbs', choices=sorted(BOOKS))
    ap.add_argument('--source', default='unsplash', choices=['unsplash', 'commons'])
    ap.add_argument('--pick', default='', help='逗号分隔的候选序号（--list 看过之后指定），按此顺序下载')
    args = ap.parse_args()
    global PREFIX, PROV
    bk = BOOKS[args.book]
    PREFIX, PROV = bk['prefix'], ROOT / '_data' / bk['prov']
    # 已被本站其他毕列志书卷用过的图不再取（各书背景互不相同）
    used = set()
    for f in (ROOT / '_data').glob('bridges*_image_provenance.yml'):
        if f != PROV:
            used |= set(re.findall(r'^    id: (\S+)', f.read_text(encoding='utf-8'), re.M))

    if args.source == 'commons':
        used = set()
        for f in (ROOT / '_data').glob('bridges*_image_provenance.yml'):
            if f != PROV:
                used |= set(re.findall(r'^    id: "?(File:[^"\n]+)', f.read_text(encoding='utf-8'), re.M))
        cands = commons_candidates(ECCL_THEMES, used)
    else:
        cands = candidates(bk['queries'], used)
    if args.pick:
        cands = [cands[int(i)] for i in args.pick.split(',')]
    print(f'候选 {len(cands)} 张（已过滤人像/城市/竖图）')
    if args.list:
        for k, c in enumerate(cands[:60]):
            print(f'  [{k:2d}] {c["q"]:6s} {c.get("license", ""):14s} {c["author"][:18]:20s} {c["alt"][:70]}')
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

    lines = [f'# {bk["title"]}各章头图来源（Unsplash）。',
             '# 由 scripts/fetch_bridges_headers.py 下载；每章一张，与 nt-bg-*/calvin 图池不共用。',
             ('# 来源维基共享资源（Commons 特色图片），署名与许可证见各条 author / license / page。'
              if args.source == 'commons' else '# 重新拉取：https://images.unsplash.com/photo-{id}?w=1800&q=80'),
             'images:']
    for name, c in prov:
        lines.append(f'  {name}:')
        lines.append(f'    id: {c["id"]}')
        lines.append(f'    author: "{yaml_str(c["author"])}"')
        lines.append(f'    alt: "{yaml_str(c["alt"])}"')
        if c.get('license'):
            lines.append(f'    license: "{yaml_str(c["license"])}"')
            lines.append(f'    page: "{yaml_str(c["page"])}"')
    PROV.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(f'\n下载 {n} 张，来源已记入 {PROV.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
