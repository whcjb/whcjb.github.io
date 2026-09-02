#!/usr/bin/env python3
"""Regenerate _data/recent.yml, _data/page_N.yml, _data/pagination.yml
and pages/N/index.html for all content pages."""
import os, re, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER_PAGE = 10

def parse_fm(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m: return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^([\w-]+)\s*:\s*(.*)', line.expandtabs())
        if kv: fm[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return fm

items = []

def page_url(path):
    """按文件路径推 Jekyll URL —— 比拿 front matter 里的 book_id/chapter 拼靠谱：
    正式章节的 layout 是 calvin-en，其中 921 个根本没有 chapter 字段
    （导论、psalms-1/preface、2timothy、1john-en、jeremiah-2-en 等）。
    旧写法直接 fm['chapter'] KeyError，整个脚本跑不完。"""
    return '/' + os.path.relpath(path, REPO)[:-3].rstrip('/') + '/'


def chapter_title(fm, path, suffix):
    """有 chapter 用「书名 第N章」，没有就退回 title（导论页等）。"""
    name = fm.get('book_name') or fm.get('title') or os.path.basename(path)[:-3]
    if fm.get('chapter'):
        return f"{name} 第{fm['chapter']}章"
    if fm.get('title') and fm.get('book_name'):
        return f"{name} {fm['title']}"
    return name


# Calvin chapters（calvin-chapter 导论页 + calvin-en 正式章节）
for root, dirs, files in os.walk(os.path.join(REPO, 'calvin')):
    for f in sorted(files):
        if not f.endswith('.md'): continue
        path = os.path.join(root, f)
        fm = parse_fm(open(path).read())
        if not fm.get('date'): continue
        items.append({
            'type': 'calvin',
            'title': chapter_title(fm, path, '加尔文'),
            'subtitle': '加尔文圣经注释',
            'url': page_url(path),
            'date': fm['date'],
        })

# Matthew Henry chapters
for root, dirs, files in os.walk(os.path.join(REPO, 'mhenry')):
    for f in sorted(files):
        if not f.endswith('.md'): continue
        path = os.path.join(root, f)
        fm = parse_fm(open(path).read())
        if not fm.get('date'): continue
        items.append({
            'type': 'mhenry',
            'title': chapter_title(fm, path, '亨利'),
            'subtitle': '马太亨利圣经注释',
            'url': page_url(path),
            'date': fm['date'],
        })

# Hodge chapters —— 只收中译（hodge/<book>/zh/），英文版整批同一时间戳，
# 进时间线只会把当天其它内容挤掉。
HODGE_CN = {'1corinthians': '哥林多前书', '2corinthians': '哥林多后书'}
for book, cn in HODGE_CN.items():
    zh_dir = os.path.join(REPO, 'hodge', book, 'zh')
    if not os.path.isdir(zh_dir): continue
    for f in sorted(os.listdir(zh_dir)):
        if not f.endswith('.md'): continue
        fm = parse_fm(open(os.path.join(zh_dir, f)).read())
        if not fm.get('date'): continue
        items.append({
            'type': 'hodge',
            'title': f"贺智《{cn}注释》{fm.get('title', f[:-3])}",
            'subtitle': '查尔斯·贺智',
            'url': f"/hodge/{book}/zh/{f[:-3]}/",  # 目录固定，直接拼
            'date': fm['date'],
        })

# Blog posts
for f in os.listdir(os.path.join(REPO, '_posts')):
    if not f.endswith('.md'): continue
    fm = parse_fm(open(os.path.join(REPO, '_posts', f)).read())
    if not fm.get('title'): continue
    date_str = f[:10]
    slug = f[11:-3]
    items.append({
        'type': 'post',
        'title': fm['title'],
        'subtitle': fm.get('subtitle', ''),
        'url': '/' + date_str.replace('-', '/') + '/' + slug + '/',
        'date': date_str,
    })

items.sort(key=lambda x: x['date'], reverse=True)
total_pages = max(1, (len(items) + PER_PAGE - 1) // PER_PAGE)

def write_yml(path, item_list):
    lines = []
    for r in item_list:
        lines.append(f"- type: {r['type']}")
        lines.append(f"  title: \"{r['title']}\"")
        lines.append(f"  subtitle: \"{r['subtitle']}\"")
        lines.append(f"  url: \"{r['url']}\"")
        lines.append(f"  date: \"{r['date']}\"")
    open(path, 'w').write('\n'.join(lines) + '\n')

data_dir = os.path.join(REPO, '_data')

# recent.yml — page 1 (top 3)
write_yml(os.path.join(data_dir, 'recent.yml'), items[:PER_PAGE])

# page_N.yml for pages 2..N
for page_num in range(2, total_pages + 1):
    start = (page_num - 1) * PER_PAGE
    write_yml(os.path.join(data_dir, f'page_{page_num}.yml'), items[start:start + PER_PAGE])

# Remove stale page data files
for f in os.listdir(data_dir):
    m = re.match(r'^page_(\d+)\.yml$', f)
    if m and int(m.group(1)) > total_pages:
        os.remove(os.path.join(data_dir, f))

# pagination.yml
open(os.path.join(data_dir, 'pagination.yml'), 'w').write(
    f"total_pages: {total_pages}\n"
)

# Generate pages/N/index.html for pages 2..N
pages_dir = os.path.join(REPO, 'pages')
os.makedirs(pages_dir, exist_ok=True)

# Remove stale page dirs
for d in os.listdir(pages_dir):
    if d.isdigit() and int(d) > total_pages:
        shutil.rmtree(os.path.join(pages_dir, d))

for page_num in range(2, total_pages + 1):
    page_dir = os.path.join(pages_dir, str(page_num))
    os.makedirs(page_dir, exist_ok=True)
    open(os.path.join(page_dir, 'index.html'), 'w').write(
        f"---\nlayout: content-list\npage_num: {page_num}\ntotal_pages: {total_pages}\n---\n"
    )

print(f"Generated {total_pages} pages for {len(items)} items")
