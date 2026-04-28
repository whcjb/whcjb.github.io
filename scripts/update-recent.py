#!/usr/bin/env python3
"""Regenerate _data/recent.yml, _data/page_N.yml, _data/pagination.yml
and pages/N/index.html for all content pages."""
import os, re, shutil

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PER_PAGE = 3

def parse_fm(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m: return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^([\w-]+)\s*:\s*(.*)', line.expandtabs())
        if kv: fm[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return fm

items = []

# Calvin chapters
for root, dirs, files in os.walk(os.path.join(REPO, 'calvin')):
    for f in sorted(files):
        if not f.endswith('.md'): continue
        fm = parse_fm(open(os.path.join(root, f)).read())
        if not fm.get('date'): continue
        items.append({
            'type': 'calvin',
            'title': f"{fm['book_name']} 第{fm['chapter']}章",
            'subtitle': '加尔文圣经注释',
            'url': f"/calvin/{fm['book_id']}/{fm['chapter']}/",
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
