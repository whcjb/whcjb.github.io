#!/usr/bin/env python3
"""
将撒迦利亚书水晶风格CSS推广到其他7本书的所有章节文件，
并更新各书的index.html custom_style。
"""

import re
import os

BASE_DIR = "/Users/yanpeifa/Documents/whcjb.github.io/mhenry"
ZECHARIAH_TEMPLATE = os.path.join(BASE_DIR, "zechariah/1.md")

# ─── 颜色替换配置 ────────────────────────────────────────────────────────────

BOOKS = {
    "jonah": {
        "name": "约拿书",
        # 背景渐变
        "bg": ["#D6F2E8", "#C8EDE0", "#D8F4EC", "#CCF0E6"],
        # 深色文字（6个hex）
        "dark": {
            "#0D1B2E": "#0D2E1B",
            "#081624": "#081E12",
            "#0D2A50": "#0D3A20",
            "#1A3A6A": "#1A4A2E",
            "#0A1E3D": "#0A1E14",
            "#1A4080": "#1A4A30",
            "#2A5090": "#2A5E3E",
        },
        # RGB替换：(old_r,old_g,old_b) -> (new_r,new_g,new_b)
        "rgb": {
            (80,140,230): (40,160,110),
            (80,140,220): (40,150,105),
            (100,160,255): (60,180,130),
            (100,140,200): (60,130,100),
            (30,80,160): (10,80,55),
            (40,100,180): (20,100,65),
            (100,150,220): (60,140,110),
            (120,180,255): (80,180,140),
            (80,150,240): (40,160,120),
            (30,100,200): (15,110,75),
            (100,160,240): (60,160,120),
            (180,210,255): (140,210,180),
            (200,225,255): (170,230,205),
            (60,130,220): (25,120,85),
            (80,160,255): (45,170,120),
        },
        "#E8F4FF": "#E8FFF4",
        "#4A90D9": "#2A8A60",
        # index.html custom_style颜色
        "index_bg": "linear-gradient(160deg, #D6F2E8 0%, #C8EDE0 30%, #D8F4EC 60%, #CCF0E6 100%)",
        "index_navbar_border": "rgba(140,210,180,0.40)",
        "index_nav_color": "#0D3A20",
        "index_btn_border": "rgba(60,160,120,0.65)",
        "index_btn_color": "#0D3A20",
        "index_btn_hover_bg": "rgba(15,110,75,0.38)",
        "index_btn_hover_border": "rgba(25,120,85,0.80)",
        "index_btn_hover_color": "#E8FFF4",
        "index_btn_shadow": "rgba(40,150,105,0.12)",
        "index_btn_hover_shadow": "rgba(15,110,75,0.22)",
        "index_preface_bg": "rgba(200,245,225,0.50)",
        "index_preface_border": "rgba(25,120,85,0.65)",
        "index_preface_color": "#082010",
        "index_preface_hover_bg": "rgba(15,110,75,0.45)",
        "index_section_border": "rgba(40,160,120,0.50)",
        "index_section_color": "#0A1E14",
        "index_col_shadow": "rgba(40,150,105,0.10)",
        "index_footer_border": "rgba(140,210,180,0.35)",
        "index_footer_color": "#1A4A2E",
    },
    "micah": {
        "name": "弥迦书",
        "bg": ["#F5EDD8", "#EDE0C8", "#F4ECD8", "#F0E4CC"],
        "dark": {
            "#0D1B2E": "#2E1A0A",
            "#081624": "#1E1008",
            "#0D2A50": "#3A2010",
            "#1A3A6A": "#4A3018",
            "#0A1E3D": "#281408",
            "#1A4080": "#382A18",
            "#2A5090": "#483A28",
        },
        "rgb": {
            (80,140,230): (180,120,40),
            (80,140,220): (170,115,38),
            (100,160,255): (210,160,60),
            (100,140,200): (160,120,70),
            (30,80,160): (120,70,15),
            (40,100,180): (140,90,20),
            (100,150,220): (170,130,65),
            (120,180,255): (200,160,80),
            (80,150,240): (180,130,40),
            (30,100,200): (150,95,20),
            (100,160,240): (180,140,60),
            (180,210,255): (220,185,120),
            (200,225,255): (240,210,150),
            (60,130,220): (160,110,30),
            (80,160,255): (190,145,45),
        },
        "#E8F4FF": "#FFF8E8",
        "#4A90D9": "#B87820",
        "index_bg": "linear-gradient(160deg, #F5EDD8 0%, #EDE0C8 30%, #F4ECD8 60%, #F0E4CC 100%)",
        "index_navbar_border": "rgba(220,185,120,0.40)",
        "index_nav_color": "#3A2010",
        "index_btn_border": "rgba(180,140,60,0.65)",
        "index_btn_color": "#3A2010",
        "index_btn_hover_bg": "rgba(150,95,20,0.38)",
        "index_btn_hover_border": "rgba(160,110,30,0.80)",
        "index_btn_hover_color": "#FFF8E8",
        "index_btn_shadow": "rgba(170,115,38,0.12)",
        "index_btn_hover_shadow": "rgba(150,95,20,0.22)",
        "index_preface_bg": "rgba(245,230,195,0.50)",
        "index_preface_border": "rgba(160,110,30,0.65)",
        "index_preface_color": "#281408",
        "index_preface_hover_bg": "rgba(150,95,20,0.45)",
        "index_section_border": "rgba(180,130,40,0.50)",
        "index_section_color": "#281408",
        "index_col_shadow": "rgba(170,115,38,0.10)",
        "index_footer_border": "rgba(220,185,120,0.35)",
        "index_footer_color": "#4A3018",
    },
    "nahum": {
        "name": "那鸿书",
        "bg": ["#ECD6F8", "#DFC8EF", "#EDD8F8", "#E4CCF0"],
        "dark": {
            "#0D1B2E": "#1E0D2E",
            "#081624": "#140820",
            "#0D2A50": "#220D3A",
            "#1A3A6A": "#301848",
            "#0A1E3D": "#180A26",
            "#1A4080": "#2A1840",
            "#2A5090": "#3A2854",
        },
        "rgb": {
            (80,140,230): (120,50,210),
            (80,140,220): (115,48,200),
            (100,160,255): (150,70,240),
            (100,140,200): (100,70,160),
            (30,80,160): (70,20,140),
            (40,100,180): (85,30,155),
            (100,150,220): (120,70,190),
            (120,180,255): (150,90,230),
            (80,150,240): (110,50,210),
            (30,100,200): (80,25,165),
            (100,160,240): (120,60,215),
            (180,210,255): (190,150,240),
            (200,225,255): (215,175,250),
            (60,130,220): (100,40,190),
            (80,160,255): (120,55,225),
        },
        "#E8F4FF": "#F4E8FF",
        "#4A90D9": "#7A30C0",
        "index_bg": "linear-gradient(160deg, #ECD6F8 0%, #DFC8EF 30%, #EDD8F8 60%, #E4CCF0 100%)",
        "index_navbar_border": "rgba(190,150,240,0.40)",
        "index_nav_color": "#220D3A",
        "index_btn_border": "rgba(120,60,215,0.65)",
        "index_btn_color": "#220D3A",
        "index_btn_hover_bg": "rgba(80,25,165,0.38)",
        "index_btn_hover_border": "rgba(100,40,190,0.80)",
        "index_btn_hover_color": "#F4E8FF",
        "index_btn_shadow": "rgba(115,48,200,0.12)",
        "index_btn_hover_shadow": "rgba(80,25,165,0.22)",
        "index_preface_bg": "rgba(225,195,250,0.50)",
        "index_preface_border": "rgba(100,40,190,0.65)",
        "index_preface_color": "#100818",
        "index_preface_hover_bg": "rgba(80,25,165,0.45)",
        "index_section_border": "rgba(110,50,210,0.50)",
        "index_section_color": "#180A26",
        "index_col_shadow": "rgba(115,48,200,0.10)",
        "index_footer_border": "rgba(190,150,240,0.35)",
        "index_footer_color": "#301848",
    },
    "habakkuk": {
        "name": "哈巴谷书",
        "bg": ["#F8E8D6", "#EFD8C8", "#F8ECD8", "#F0DECC"],
        "dark": {
            "#0D1B2E": "#2E160A",
            "#081624": "#1E0E08",
            "#0D2A50": "#3A1808",
            "#1A3A6A": "#4A2810",
            "#0A1E3D": "#280E08",
            "#1A4080": "#381A10",
            "#2A5090": "#482818",
        },
        "rgb": {
            (80,140,230): (200,95,30),
            (80,140,220): (190,90,28),
            (100,160,255): (230,120,40),
            (100,140,200): (170,100,50),
            (30,80,160): (140,55,10),
            (40,100,180): (160,70,15),
            (100,150,220): (185,110,40),
            (120,180,255): (220,145,60),
            (80,150,240): (200,105,28),
            (30,100,200): (165,72,12),
            (100,160,240): (200,120,35),
            (180,210,255): (235,185,130),
            (200,225,255): (250,210,165),
            (60,130,220): (175,80,20),
            (80,160,255): (205,100,28),
        },
        "#E8F4FF": "#FFF2E8",
        "#4A90D9": "#C06010",
        "index_bg": "linear-gradient(160deg, #F8E8D6 0%, #EFD8C8 30%, #F8ECD8 60%, #F0DECC 100%)",
        "index_navbar_border": "rgba(235,185,130,0.40)",
        "index_nav_color": "#3A1808",
        "index_btn_border": "rgba(200,120,35,0.65)",
        "index_btn_color": "#3A1808",
        "index_btn_hover_bg": "rgba(165,72,12,0.38)",
        "index_btn_hover_border": "rgba(175,80,20,0.80)",
        "index_btn_hover_color": "#FFF2E8",
        "index_btn_shadow": "rgba(190,90,28,0.12)",
        "index_btn_hover_shadow": "rgba(165,72,12,0.22)",
        "index_preface_bg": "rgba(250,220,185,0.50)",
        "index_preface_border": "rgba(175,80,20,0.65)",
        "index_preface_color": "#200A04",
        "index_preface_hover_bg": "rgba(165,72,12,0.45)",
        "index_section_border": "rgba(200,105,28,0.50)",
        "index_section_color": "#280E08",
        "index_col_shadow": "rgba(190,90,28,0.10)",
        "index_footer_border": "rgba(235,185,130,0.35)",
        "index_footer_color": "#4A2810",
    },
    "zephaniah": {
        "name": "西番雅书",
        "bg": ["#D6DBF5", "#C8CCEC", "#D8DCF5", "#CCCFEE"],
        "dark": {
            "#0D1B2E": "#0D1228",
            "#081624": "#080D1C",
            "#0D2A50": "#0D1835",
            "#1A3A6A": "#1A2248",
            "#0A1E3D": "#0A0E20",
            "#1A4080": "#1A2038",
            "#2A5090": "#2A2E4A",
        },
        "rgb": {
            (80,140,230): (60,85,195),
            (80,140,220): (58,80,185),
            (100,160,255): (75,100,230),
            (100,140,200): (70,85,155),
            (30,80,160): (25,50,140),
            (40,100,180): (30,60,155),
            (100,150,220): (70,95,180),
            (120,180,255): (85,115,215),
            (80,150,240): (60,95,200),
            (30,100,200): (28,65,165),
            (100,160,240): (68,100,205),
            (180,210,255): (155,175,230),
            (200,225,255): (175,195,245),
            (60,130,220): (45,80,185),
            (80,160,255): (60,100,210),
        },
        "#E8F4FF": "#EEF2FF",
        "#4A90D9": "#3A60C0",
        "index_bg": "linear-gradient(160deg, #D6DBF5 0%, #C8CCEC 30%, #D8DCF5 60%, #CCCFEE 100%)",
        "index_navbar_border": "rgba(155,175,230,0.40)",
        "index_nav_color": "#0D1835",
        "index_btn_border": "rgba(68,100,205,0.65)",
        "index_btn_color": "#0D1835",
        "index_btn_hover_bg": "rgba(28,65,165,0.38)",
        "index_btn_hover_border": "rgba(45,80,185,0.80)",
        "index_btn_hover_color": "#EEF2FF",
        "index_btn_shadow": "rgba(58,80,185,0.12)",
        "index_btn_hover_shadow": "rgba(28,65,165,0.22)",
        "index_preface_bg": "rgba(205,215,245,0.50)",
        "index_preface_border": "rgba(45,80,185,0.65)",
        "index_preface_color": "#080D1C",
        "index_preface_hover_bg": "rgba(28,65,165,0.45)",
        "index_section_border": "rgba(60,95,200,0.50)",
        "index_section_color": "#0A0E20",
        "index_col_shadow": "rgba(58,80,185,0.10)",
        "index_footer_border": "rgba(155,175,230,0.35)",
        "index_footer_color": "#1A2248",
    },
    "haggai": {
        "name": "哈该书",
        "bg": ["#F5F0D6", "#EDE8C8", "#F4F0D8", "#F0EAC8"],
        "dark": {
            "#0D1B2E": "#28200A",
            "#081624": "#1C1608",
            "#0D2A50": "#342A0A",
            "#1A3A6A": "#423410",
            "#0A1E3D": "#221A08",
            "#1A4080": "#322818",
            "#2A5090": "#423A26",
        },
        "rgb": {
            (80,140,230): (180,148,30),
            (80,140,220): (170,140,28),
            (100,160,255): (210,175,50),
            (100,140,200): (160,135,55),
            (30,80,160): (130,95,10),
            (40,100,180): (145,110,15),
            (100,150,220): (170,145,50),
            (120,180,255): (200,175,70),
            (80,150,240): (180,150,30),
            (30,100,200): (148,112,12),
            (100,160,240): (175,148,45),
            (180,210,255): (225,205,135),
            (200,225,255): (245,228,165),
            (60,130,220): (155,120,20),
            (80,160,255): (185,152,35),
        },
        "#E8F4FF": "#FFFAE8",
        "#4A90D9": "#B89018",
        "index_bg": "linear-gradient(160deg, #F5F0D6 0%, #EDE8C8 30%, #F4F0D8 60%, #F0EAC8 100%)",
        "index_navbar_border": "rgba(225,205,135,0.40)",
        "index_nav_color": "#342A0A",
        "index_btn_border": "rgba(175,148,45,0.65)",
        "index_btn_color": "#342A0A",
        "index_btn_hover_bg": "rgba(148,112,12,0.38)",
        "index_btn_hover_border": "rgba(155,120,20,0.80)",
        "index_btn_hover_color": "#FFFAE8",
        "index_btn_shadow": "rgba(170,140,28,0.12)",
        "index_btn_hover_shadow": "rgba(148,112,12,0.22)",
        "index_preface_bg": "rgba(245,235,185,0.50)",
        "index_preface_border": "rgba(155,120,20,0.65)",
        "index_preface_color": "#201808",
        "index_preface_hover_bg": "rgba(148,112,12,0.45)",
        "index_section_border": "rgba(180,150,30,0.50)",
        "index_section_color": "#221A08",
        "index_col_shadow": "rgba(170,140,28,0.10)",
        "index_footer_border": "rgba(225,205,135,0.35)",
        "index_footer_color": "#423410",
    },
    "malachi": {
        "name": "玛拉基书",
        "bg": ["#F5D6DC", "#EDC8CC", "#F4D8DC", "#F0CCCE"],
        "dark": {
            "#0D1B2E": "#280A0E",
            "#081624": "#1C0608",
            "#0D2A50": "#34080E",
            "#1A3A6A": "#421018",
            "#0A1E3D": "#200A0C",
            "#1A4080": "#301016",
            "#2A5090": "#401820",
        },
        "rgb": {
            (80,140,230): (180,40,60),
            (80,140,220): (170,38,57),
            (100,160,255): (210,55,80),
            (100,140,200): (155,60,70),
            (30,80,160): (130,15,30),
            (40,100,180): (148,20,38),
            (100,150,220): (170,65,75),
            (120,180,255): (200,80,100),
            (80,150,240): (175,40,60),
            (30,100,200): (150,18,35),
            (100,160,240): (175,55,70),
            (180,210,255): (220,160,170),
            (200,225,255): (240,185,195),
            (60,130,220): (155,25,45),
            (80,160,255): (185,45,65),
        },
        "#E8F4FF": "#FFE8EC",
        "#4A90D9": "#C02840",
        "index_bg": "linear-gradient(160deg, #F5D6DC 0%, #EDC8CC 30%, #F4D8DC 60%, #F0CCCE 100%)",
        "index_navbar_border": "rgba(220,160,170,0.40)",
        "index_nav_color": "#34080E",
        "index_btn_border": "rgba(175,55,70,0.65)",
        "index_btn_color": "#34080E",
        "index_btn_hover_bg": "rgba(150,18,35,0.38)",
        "index_btn_hover_border": "rgba(155,25,45,0.80)",
        "index_btn_hover_color": "#FFE8EC",
        "index_btn_shadow": "rgba(170,38,57,0.12)",
        "index_btn_hover_shadow": "rgba(150,18,35,0.22)",
        "index_preface_bg": "rgba(245,205,215,0.50)",
        "index_preface_border": "rgba(155,25,45,0.65)",
        "index_preface_color": "#180408",
        "index_preface_hover_bg": "rgba(150,18,35,0.45)",
        "index_section_border": "rgba(175,40,60,0.50)",
        "index_section_color": "#200A0C",
        "index_col_shadow": "rgba(170,38,57,0.10)",
        "index_footer_border": "rgba(220,160,170,0.35)",
        "index_footer_color": "#421018",
    },
}

# ─── 从zechariah/1.md提取<style>块 ──────────────────────────────────────────

def extract_style_block(content):
    """提取<style>到</style>的完整块（含标签）"""
    m = re.search(r'(<style>.*?</style>)', content, re.DOTALL)
    return m.group(1) if m else None

def apply_color_replacements(css, book_id, cfg):
    """对CSS应用颜色替换"""
    result = css

    # 1. 背景渐变（hex颜色）
    bg_old = ["#D6E8F8", "#C8DCEF", "#D8ECF8", "#CCDFF0"]
    bg_new = cfg["bg"]
    for old, new in zip(bg_old, bg_new):
        result = result.replace(old, new)

    # 2. 深色hex文字颜色
    for old, new in cfg["dark"].items():
        result = result.replace(old, new)

    # 3. #E8F4FF 和 #4A90D9
    result = result.replace("#E8F4FF", cfg["#E8F4FF"])
    result = result.replace("#4A90D9", cfg["#4A90D9"])

    # 4. RGB值替换（精确匹配 r,g,b 格式，考虑空格）
    # 按照 (r,g,b) 或 (r, g, b) 的格式
    for (r_old, g_old, b_old), (r_new, g_new, b_new) in cfg["rgb"].items():
        # 匹配 rgba(...) 或颜色中的 r,g,b 部分
        # 尝试多种空格组合
        patterns = [
            (f"{r_old},{g_old},{b_old}", f"{r_new},{g_new},{b_new}"),
            (f"{r_old}, {g_old}, {b_old}", f"{r_new}, {g_new}, {b_new}"),
            (f"{r_old} ,{g_old} ,{b_old}", f"{r_new} ,{g_new} ,{b_new}"),
        ]
        for old_pat, new_pat in patterns:
            result = result.replace(old_pat, new_pat)

    # 5. 替换 book-specific footer CSS
    result = result.replace(
        'href$="/zechariah/"',
        f'href$="/{book_id}/"'
    )
    # 注释行
    result = result.replace(
        '/* ── zechariah 水晶透明风',
        f'/* ── {book_id} 水晶透明风'
    )
    # 容器注释
    result = result.replace(
        '/* 容器：冷蓝晶体渐变 */',
        '/* 容器：水晶渐变 */'
    )
    # 导航栏注释
    result = result.replace(
        '/* ── 顶部导航：水晶蓝主题 ── */',
        '/* ── 顶部导航：水晶主题 ── */'
    )
    result = result.replace(
        '/* ── TTS 朗读栏：水晶蓝主题 ── */',
        '/* ── TTS 朗读栏：水晶主题 ── */'
    )
    result = result.replace(
        '/* ── 页脚：水晶蓝主题 ── */',
        '/* ── 页脚：水晶主题 ── */'
    )

    return result

def replace_style_in_file(filepath, new_style_block):
    """替换或插入文件中的<style>块"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    if '<style>' in content and '</style>' in content:
        # 替换现有style块
        new_content = re.sub(r'<style>.*?</style>', new_style_block, content, flags=re.DOTALL)
    else:
        # 在front matter后面插入（找到第二个---后面）
        # front matter: --- ... ---\n\n
        m = re.match(r'(---\n.*?---\n)', content, re.DOTALL)
        if m:
            fm = m.group(1)
            rest = content[len(fm):]
            # 确保有一个空行
            if rest.startswith('\n'):
                new_content = fm + '\n' + new_style_block + '\n' + rest
            else:
                new_content = fm + '\n' + new_style_block + '\n\n' + rest
        else:
            print(f"  WARNING: 无法找到front matter in {filepath}")
            return False

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def generate_index_custom_style(book_id, cfg):
    """生成index.html的custom_style内容"""
    bg = cfg["index_bg"]
    nb = cfg["index_navbar_border"]
    nc = cfg["index_nav_color"]
    bb = cfg["index_btn_border"]
    bc = cfg["index_btn_color"]
    bhb = cfg["index_btn_hover_bg"]
    bhbr = cfg["index_btn_hover_border"]
    bhc = cfg["index_btn_hover_color"]
    bs = cfg["index_btn_shadow"]
    bhs = cfg["index_btn_hover_shadow"]
    pb = cfg["index_preface_bg"]
    pbr = cfg["index_preface_border"]
    pc = cfg["index_preface_color"]
    phb = cfg["index_preface_hover_bg"]
    sb = cfg["index_section_border"]
    sc = cfg["index_section_color"]
    cs = cfg["index_col_shadow"]
    fb = cfg["index_footer_border"]
    fc = cfg["index_footer_color"]

    # 从dark颜色取一些
    dark_0d2a50 = cfg["dark"]["#0D2A50"]
    dark_1a3a6a = cfg["dark"]["#1A3A6A"]

    lines = [
        f'  body {{ background: {bg} !important; min-height: 100vh; }}',
        f'  .navbar-default {{ background: rgba(255,255,255,0.30) !important; backdrop-filter: blur(10px) !important; border-bottom: 1px solid {nb} !important; box-shadow: none !important; }}',
        f'  .navbar-default .navbar-nav > li > a {{ color: {nc} !important; }}',
        f'  .navbar-default .navbar-brand {{ color: {nc} !important; }}',
        f'  .intro-header {{ opacity: 0.85; }}',
        f'  .mhenry-chapter-btn--has-content {{ background: rgba(255,255,255,0.38) !important; border: 2px solid {bb} !important; color: {bc} !important; border-radius: 10px !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.70), 0 2px 8px {bs} !important; backdrop-filter: blur(8px) !important; font-weight: 600 !important; transition: background 0.2s, border-color 0.2s, color 0.2s !important; }}',
        f'  .mhenry-chapter-btn--has-content:hover {{ background: {bhb} !important; border-color: {bhbr} !important; color: {bhc} !important; box-shadow: 0 4px 16px {bhs} !important; }}',
        f'  .mhenry-chapter-btn--preface {{ background: {pb} !important; border-color: {pbr} !important; color: {pc} !important; }}',
        f'  .mhenry-chapter-btn--preface:hover {{ background: {phb} !important; border-color: {phb} !important; color: {bhc} !important; }}',
        f'  .mh-section-title {{ border-bottom: 2px solid {sb} !important; color: {sc} !important; }}',
        f'  .mh-book-chapters-col {{ background: rgba(255,255,255,0.22); border-radius: 16px; padding: 20px 16px 12px !important; box-shadow: inset 0 1px 0 rgba(255,255,255,0.60), 0 4px 24px {cs}; backdrop-filter: blur(12px); }}',
        f'  footer {{ background: rgba(255,255,255,0.20) !important; backdrop-filter: blur(8px) !important; border-top: 1px solid {fb} !important; }}',
        f'  footer .copyright, footer a {{ color: {fc} !important; }}',
    ]
    return '\n'.join(lines)

def update_index_html(filepath, book_id, cfg):
    """更新index.html的custom_style"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    new_style = generate_index_custom_style(book_id, cfg)

    if 'custom_style:' in content:
        # 替换整个custom_style块（到下一个YAML键或---）
        # custom_style: |\n  ...lines...\n直到下一个不以空格开头的行或---
        new_content = re.sub(
            r'custom_style: \|.*?(?=\n\w|\n---)',
            f'custom_style: |\n{new_style}',
            content,
            flags=re.DOTALL
        )
    else:
        # 在---前插入custom_style
        # 找到最后的---
        m = re.match(r'(---\n)(.*?)(---\n)', content, re.DOTALL)
        if m:
            new_content = m.group(1) + m.group(2) + f'custom_style: |\n{new_style}\n' + m.group(3) + content[m.end():]
        else:
            print(f"  WARNING: 无法解析front matter in {filepath}")
            return False

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

# ─── 主程序 ─────────────────────────────────────────────────────────────────

def main():
    # 读取zechariah模板
    with open(ZECHARIAH_TEMPLATE, 'r', encoding='utf-8') as f:
        template_content = f.read()

    zech_style = extract_style_block(template_content)
    if not zech_style:
        print("ERROR: 无法从zechariah/1.md提取style块")
        return

    print(f"成功提取zechariah CSS模板 ({len(zech_style)} 字节)")
    print()

    total_modified = 0

    for book_id, cfg in BOOKS.items():
        book_dir = os.path.join(BASE_DIR, book_id)
        if not os.path.isdir(book_dir):
            print(f"WARNING: 目录不存在: {book_dir}")
            continue

        # 生成该书的CSS
        book_style = apply_color_replacements(zech_style, book_id, cfg)

        # 处理所有章节文件
        files = [f for f in os.listdir(book_dir) if f.endswith('.md')]
        modified_count = 0

        for fname in sorted(files):
            fpath = os.path.join(book_dir, fname)
            success = replace_style_in_file(fpath, book_style)
            if success:
                modified_count += 1
                print(f"  ✓ {book_id}/{fname}")
            else:
                print(f"  ✗ {book_id}/{fname} (失败)")

        # 处理index.html
        index_path = os.path.join(book_dir, "index.html")
        if os.path.exists(index_path):
            success = update_index_html(index_path, book_id, cfg)
            if success:
                modified_count += 1
                print(f"  ✓ {book_id}/index.html")
            else:
                print(f"  ✗ {book_id}/index.html (失败)")

        total_modified += modified_count
        print(f"  → {book_id} ({cfg['name']}): 修改了 {modified_count} 个文件")
        print()

    print(f"全部完成，共修改 {total_modified} 个文件")

    # 验证：检查每个文件是否有style块
    print()
    print("── 验证检查 ──")
    all_ok = True
    for book_id in BOOKS:
        book_dir = os.path.join(BASE_DIR, book_id)
        if not os.path.isdir(book_dir):
            continue
        files = [f for f in os.listdir(book_dir) if f.endswith('.md')]
        for fname in sorted(files):
            fpath = os.path.join(book_dir, fname)
            with open(fpath, 'r', encoding='utf-8') as f:
                c = f.read()
            has_style = '<style>' in c and '</style>' in c
            if not has_style:
                print(f"  MISSING STYLE: {book_id}/{fname}")
                all_ok = False
    if all_ok:
        print("  所有 .md 文件均包含 <style> 块 ✓")


if __name__ == "__main__":
    main()
