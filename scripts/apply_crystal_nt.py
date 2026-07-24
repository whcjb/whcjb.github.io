#!/usr/bin/env python3
"""
将撒迦利亚书（zechariah）单色蓝「水晶透明风」模板，通过 HSL 色相旋转，
推广到 14 卷「中文原缺、经流水线补齐」的新约书卷，每卷一个独立主题色相。

与旧版 apply_crystal_style.py 的区别：
  - 旧版按书手工列出每个颜色映射（会漏掉模板里的部分蓝色，导致蓝色残留）。
  - 本版对模板里「所有」颜色统一做色相旋转，中性色(白/近灰 S≈0)自动不受影响，
    因此每卷都是干净的单色相水晶配色，且每卷完全独立（inline per-file，样式隔离）。

模板来源：
  - 章节 <style> 块        ← mhenry/zechariah/1.md
  - index.html custom_style ← mhenry/zechariah/index.html

处理对象：每卷的所有 *.md（含 preface.md）+ index.html。
"""

import re
import os
import colorsys

BASE_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/mhenry"
CHAPTER_TEMPLATE = os.path.join(BASE_DIR, "zechariah/1.md")
INDEX_TEMPLATE = os.path.join(BASE_DIR, "zechariah/index.html")

# ─── 14 卷新约书卷的目标色相（HSL 色相角，0-360） ────────────────────────────
# 相邻书卷色相尽量拉开；相关书信（帖前后/提前后/约一二三）成同系但可区分。
BOOKS = {
    "1john":          {"name": "约翰一书", "hue": 0},    # 深红 · 爱
    "2timothy":       {"name": "提摩太后书", "hue": 20},  # 橙
    "1timothy":       {"name": "提摩太前书", "hue": 42},  # 琥珀
    "titus":          {"name": "提多书",   "hue": 62},   # 金
    "james":          {"name": "雅各书",   "hue": 90},   # 橄榄绿 · 行为
    "galatians":      {"name": "加拉太书", "hue": 158},  # 翠绿 · 自由
    "1thessalonians": {"name": "帖撒罗尼迦前书", "hue": 193}, # 青
    "2thessalonians": {"name": "帖撒罗尼迦后书", "hue": 214}, # 蓝
    "colossians":     {"name": "歌罗西书", "hue": 232},  # 靛
    "jude":           {"name": "犹大书",   "hue": 250},  # 石板靛 · 警戒
    "ephesians":      {"name": "以弗所书", "hue": 285},  # 紫罗兰 · 荣耀
    "3john":          {"name": "约翰三书", "hue": 305},  # 品红紫
    "2john":          {"name": "约翰二书", "hue": 325},  # 玫红
    "philippians":    {"name": "腓立比书", "hue": 345},  # 玫瑰 · 喜乐
}


# ─── 颜色工具：把任意颜色旋转到目标色相（保留 S、L） ──────────────────────────

def _shift_rgb(r, g, b, hue_deg):
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    nh = hue_deg / 360.0
    nr, ng, nb = colorsys.hls_to_rgb(nh, l, s)
    return round(nr * 255), round(ng * 255), round(nb * 255)


def shift_colors(css, hue_deg):
    """把 CSS 文本里所有 #RRGGBB 与 rgb()/rgba() 颜色旋转到 hue_deg。
    中性色 (S≈0，如 white) 自动保持不变。"""

    def hex_repl(m):
        r = int(m.group(1), 16)
        g = int(m.group(2), 16)
        b = int(m.group(3), 16)
        nr, ng, nb = _shift_rgb(r, g, b, hue_deg)
        return "#{:02X}{:02X}{:02X}".format(nr, ng, nb)

    css = re.sub(r'#([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})([0-9A-Fa-f]{2})\b',
                 hex_repl, css)

    def rgb_repl(m):
        prefix = m.group(1)          # 'rgb(' or 'rgba('
        r, g, b = int(m.group(2)), int(m.group(3)), int(m.group(4))
        rest = m.group(5)            # 剩余部分（可能含 alpha）
        nr, ng, nb = _shift_rgb(r, g, b, hue_deg)
        return "{}{},{},{}{}".format(prefix, nr, ng, nb, rest)

    css = re.sub(
        r'(rgba?\()\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)([^)]*\))',
        rgb_repl, css)

    return css


# ─── 模板读取 ────────────────────────────────────────────────────────────────

def read_chapter_template():
    with open(CHAPTER_TEMPLATE, encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'<style>.*?</style>', content, re.DOTALL)
    if not m:
        raise SystemExit("ERROR: 无法从 zechariah/1.md 提取 <style> 块")
    return m.group(0)


def read_index_custom_style():
    """提取 zechariah/index.html 的 custom_style 块正文（不含 'custom_style: |'）。"""
    with open(INDEX_TEMPLATE, encoding='utf-8') as f:
        content = f.read()
    m = re.search(r'custom_style: \|\n(.*?)(?=\n---)', content, re.DOTALL)
    if not m:
        raise SystemExit("ERROR: 无法从 zechariah/index.html 提取 custom_style")
    return m.group(1)


# ─── 写入 ────────────────────────────────────────────────────────────────────

def build_chapter_style(template, book_id, hue):
    css = shift_colors(template, hue)
    css = css.replace('href$="/zechariah/"', 'href$="/{}/"'.format(book_id))
    css = css.replace('/* ── zechariah 水晶透明风',
                      '/* ── {} 水晶透明风'.format(book_id))
    return css


def replace_style_in_md(filepath, style_block):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    if '<style>' in content and '</style>' in content:
        new_content = re.sub(r'<style>.*?</style>', style_block, content,
                             flags=re.DOTALL)
    else:
        m = re.match(r'(---\n.*?\n---\n)', content, re.DOTALL)
        if not m:
            print("  WARNING: 无 front matter：{}".format(filepath))
            return False
        fm = m.group(1)
        rest = content[len(fm):]
        rest = rest.lstrip('\n')
        new_content = fm + '\n' + style_block + '\n\n' + rest

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


def update_index_html(filepath, book_id, index_style):
    with open(filepath, encoding='utf-8') as f:
        content = f.read()

    if 'custom_style:' in content:
        new_content = re.sub(
            r'custom_style: \|\n.*?(?=\n---)',
            'custom_style: |\n' + index_style,
            content, flags=re.DOTALL)
    else:
        # 在 front matter 结束的 --- 前插入
        m = re.match(r'(---\n.*?\n)(---\n)', content, re.DOTALL)
        if not m:
            print("  WARNING: index 无 front matter：{}".format(filepath))
            return False
        new_content = (m.group(1) + 'custom_style: |\n' + index_style + '\n'
                       + m.group(2) + content[m.end():])

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True


def main():
    chapter_template = read_chapter_template()
    index_template = read_index_custom_style()
    print("模板：章节 <style> {} 字节；index custom_style {} 字节\n".format(
        len(chapter_template), len(index_template)))

    total = 0
    for book_id, cfg in BOOKS.items():
        book_dir = os.path.join(BASE_DIR, book_id)
        if not os.path.isdir(book_dir):
            print("WARNING: 目录不存在 {}".format(book_dir))
            continue

        hue = cfg["hue"]
        chapter_style = build_chapter_style(chapter_template, book_id, hue)
        index_style = shift_colors(index_template, hue)

        n = 0
        for fname in sorted(f for f in os.listdir(book_dir) if f.endswith('.md')):
            if replace_style_in_md(os.path.join(book_dir, fname), chapter_style):
                n += 1
                print("  ✓ {}/{}".format(book_id, fname))

        idx = os.path.join(book_dir, "index.html")
        if os.path.exists(idx) and update_index_html(idx, book_id, index_style):
            n += 1
            print("  ✓ {}/index.html".format(book_id))

        total += n
        print("  → {} ({}) hue={}°: {} 个文件\n".format(
            book_id, cfg["name"], hue, n))

    print("完成，共修改 {} 个文件".format(total))


if __name__ == "__main__":
    main()
