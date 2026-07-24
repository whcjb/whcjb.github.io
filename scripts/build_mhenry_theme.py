#!/usr/bin/env python3
"""
build_mhenry_theme.py — 为每卷马太亨利书卷推导「主题色」，写到 _data/mhenry_theme.json。

主题色来源（单一真相 = 书卷自身的正文样式）：
  - 水晶风书卷：读该卷章节 md 里 `#mhenry-col { background: linear-gradient(...) }`
    的第一个浅色 hex → 取其色相 (hue)。
  - 钻石风书卷（叙事/福音/大书信 13 卷）：无 inline 背景，用统一银蓝 hue=212。
  - 其余（默认暖金）：hue=40。

每卷输出经文弹框（scripture-popup 水晶模式）需要的四个值：
  accent  — 深色强调（边条/标题/节号）
  vnum    — 节号色（略深）
  bg      — 弹框磨砂底（该色相极浅 tint，带透明度）
  border  — 内描边（accent 低透明度）
"""

import colorsys
import json
import os
import re

BASE = os.path.join(os.path.dirname(__file__), "..", "mhenry")
OUT = os.path.join(os.path.dirname(__file__), "..", "_data", "mhenry_theme.json")

DIAMOND = {
    "matthew", "mark", "luke", "john", "acts", "romans",
    "1corinthians", "2corinthians", "philemon", "hebrews",
    "1peter", "2peter", "revelation",
}
DIAMOND_HUE = 212      # 银蓝
DEFAULT_HUE = 40       # 暖金


def hex_to_hue(h):
    h = h.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    hue, l, s = colorsys.rgb_to_hls(r, g, b)
    return hue * 360, s


def hsl_hex(hue, s, l):
    r, g, b = colorsys.hls_to_rgb(hue / 360, l, s)
    return "#{:02X}{:02X}{:02X}".format(round(r * 255), round(g * 255), round(b * 255))


def hsl_rgba(hue, s, l, a):
    r, g, b = colorsys.hls_to_rgb(hue / 360, l, s)
    return "rgba({},{},{},{})".format(round(r * 255), round(g * 255), round(b * 255), a)


def book_hue(book_dir):
    """从章节 md 提取 #mhenry-col 背景第一个 hex 的色相；无则 None。"""
    for name in ("1.md", "preface.md", "2.md"):
        p = os.path.join(book_dir, name)
        if not os.path.isfile(p):
            continue
        txt = open(p, encoding="utf-8").read()
        m = re.search(r"#mhenry-col\s*\{[^}]*?linear-gradient\([^)]*?(#[0-9A-Fa-f]{6})",
                      txt, re.DOTALL)
        if m:
            hue, sat = hex_to_hue(m.group(1))
            # 近中性（饱和度极低）视为无有效色相
            if sat < 0.05:
                return None
            return hue
    return None


def theme_for_hue(hue, silver=False):
    if silver:
        # 银蓝：低饱和
        return {
            "accent": hsl_hex(hue, 0.42, 0.40),
            "vnum":   hsl_hex(hue, 0.42, 0.36),
            "bg":     hsl_rgba(hue, 0.45, 0.965, 0.86),
            "border": hsl_rgba(hue, 0.42, 0.40, 0.40),
            "hue":    round(hue, 1),
        }
    return {
        "accent": hsl_hex(hue, 0.60, 0.42),
        "vnum":   hsl_hex(hue, 0.58, 0.38),
        "bg":     hsl_rgba(hue, 0.60, 0.965, 0.86),
        "border": hsl_rgba(hue, 0.60, 0.42, 0.42),
        "hue":    round(hue, 1),
    }


def main():
    themes = {}
    for entry in sorted(os.listdir(BASE)):
        d = os.path.join(BASE, entry)
        if not os.path.isdir(d) or entry.endswith("-en"):
            continue
        hue = book_hue(d)
        if hue is not None:
            themes[entry] = theme_for_hue(hue)
            src = "crystal"
        elif entry in DIAMOND:
            themes[entry] = theme_for_hue(DIAMOND_HUE, silver=True)
            src = "diamond"
        else:
            themes[entry] = theme_for_hue(DEFAULT_HUE)
            src = "default"
        print("  {:16s} {:8s} hue={:.0f} accent={}".format(
            entry, src, themes[entry]["hue"], themes[entry]["accent"]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(themes, f, ensure_ascii=False, indent=1, sort_keys=True)
    print("\n写出 {} 卷 → {}".format(len(themes), os.path.relpath(OUT)))


if __name__ == "__main__":
    main()
