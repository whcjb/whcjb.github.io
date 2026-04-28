#!/usr/bin/env python3
"""Regenerate _data/recent.yml with the 3 most recent items from all content."""
import os, re, sys

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
items = []

def parse_fm(content):
    m = re.match(r'^---\n(.*?)\n---', content, re.DOTALL)
    if not m: return {}
    fm = {}
    for line in m.group(1).splitlines():
        kv = re.match(r'^([\w-]+)\s*:\s*(.*)', line.expandtabs())
        if kv:
            fm[kv.group(1)] = kv.group(2).strip().strip('"').strip("'")
    return fm

for root, dirs, files in os.walk(os.path.join(repo, "calvin")):
    for f in files:
        if not f.endswith(".md"): continue
        fm = parse_fm(open(os.path.join(root, f)).read())
        if not fm.get("date"): continue
        items.append({
            "type": "calvin",
            "title": f"{fm['book_name']} 第{fm['chapter']}章",
            "subtitle": "加尔文圣经注释",
            "url": f"/calvin/{fm['book_id']}/{fm['chapter']}/",
            "date": fm["date"]
        })

for f in os.listdir(os.path.join(repo, "_posts")):
    if not f.endswith(".md"): continue
    fm = parse_fm(open(os.path.join(repo, "_posts", f)).read())
    if not fm.get("title"): continue
    date_str = f[:10]
    items.append({
        "type": "post",
        "title": fm["title"],
        "subtitle": fm.get("subtitle", ""),
        "url": "/" + date_str.replace("-", "/") + "/" + f[11:-3] + "/",
        "date": date_str
    })

items.sort(key=lambda x: x["date"], reverse=True)
recent = items[:3]

lines = []
for r in recent:
    lines.append(f"- type: {r['type']}")
    lines.append(f"  title: \"{r['title']}\"")
    lines.append(f"  subtitle: \"{r['subtitle']}\"")
    lines.append(f"  url: \"{r['url']}\"")
    lines.append(f"  date: \"{r['date']}\"")

open(os.path.join(repo, "_data/recent.yml"), "w").write("\n".join(lines) + "\n")
