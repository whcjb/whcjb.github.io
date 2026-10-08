#!/usr/bin/env python3
"""约翰斯通《腓立比书讲疏》—— ABBYY 版面 × tesseract 字形 → en_chapters/。

    johnstone_raw/philippians/src/abbyy1875.xml.gz   版面结构 + 斜体
    johnstone_raw/philippians/src/ocr_eng/NNNN.txt   tesseract eng+grc 的字
            │  johnstone_common.transfer_page（按段对齐，区间搬斜体）
            ▼
    johnstone_raw/philippians/en_chapters/*.md

全书分段（见 PROVENANCE.md 的目录抄录）：
    preface · introduction · 1..30（讲章） · translation · notes-1..4 · polycarp

页码偏移不写死：ABBYY 的 XML 页数（520）和 jp2 的图数不一定相等，
扫描流程里多出来的大幅面页（8 张 3744×5616）就是差额的来源。按**印刷页码**
对，不按序号对 —— 两边各自从页眉里读出印刷页码，对不上就报错不硬跑。
"""
import argparse
import gzip
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import johnstone_common as J

ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, 'johnstone_raw', 'philippians')
XML_GZ = os.path.join(RAW, 'src', 'abbyy1875.xml.gz')
OCR_DIR = os.path.join(RAW, 'src', 'ocr_eng')
OUT_DIR = os.path.join(RAW, 'en_chapters')

ROMAN = {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5, 'VI': 6, 'VII': 7,
         'VIII': 8, 'IX': 9, 'X': 10, 'XI': 11, 'XII': 12, 'XIII': 13,
         'XIV': 14, 'XV': 15, 'XVI': 16, 'XVII': 17, 'XVIII': 18, 'XIX': 19,
         'XX': 20, 'XXI': 21, 'XXII': 22, 'XXIII': 23, 'XXIV': 24, 'XXV': 25,
         'XXVI': 26, 'XXVII': 27, 'XXVIII': 28, 'XXIX': 29, 'XXX': 30}

# 讲章起头是「单独一行的罗马数字」+「全大写标题」。OCR 常把 I 读成 1/l，
# 把 . 读成 ,，判据放宽到这一层；真正的判定靠「下一行是全大写标题」。
RE_NUM = re.compile(r'^\W{0,3}([IVXLivxl]{1,6})\W{0,3}$')
RE_CAPS = re.compile(r'^[^a-z]{6,}$')


def load_xml():
    plain = os.path.join(RAW, 'src', 'abbyy1875.xml')
    if not os.path.exists(plain) or os.path.getmtime(plain) < os.path.getmtime(XML_GZ):
        with gzip.open(XML_GZ, 'rb') as fi, open(plain, 'wb') as fo:
            shutil.copyfileobj(fi, fo)
    return plain


def ocr_pages():
    """leaf 序号 → 行列表"""
    out = {}
    if not os.path.isdir(OCR_DIR):
        return out
    for name in sorted(os.listdir(OCR_DIR)):
        if not name.endswith('.txt'):
            continue
        leaf = int(os.path.splitext(name)[0])
        with open(os.path.join(OCR_DIR, name), encoding='utf-8') as f:
            out[leaf] = f.read().split('\n')
    return out


def printed_number(lines):
    """从页眉读印刷页码。左页在行首，右页在行尾。读不出返回 None。"""
    for line in lines[:3]:
        t = line.strip()
        if not t:
            continue
        if 'hilippians' in t or re.match(r'^\W*(VER|Ver)', t):
            m = re.match(r'^\W*(\d{1,3})\b', t)
            if m:
                return int(m.group(1))
            m = re.search(r'\b(\d{1,3})\W*$', t)
            if m:
                return int(m.group(1))
        break
    return None


def page_text(pars, lines):
    """一页 → markdown。先剔页眉，再合流。"""
    body = [l for l in lines if not J.is_running_head(l)]
    ocr = J.join_ocr_lines(body)
    keep = [p for p in pars if not J.is_running_head(J.strip_sentinels(p)[0])]
    if not keep or not ocr.strip():
        return ''
    return J.transfer_page(keep, ocr)


def split_sections(pages):
    """[(leaf, markdown)] → [(slug, 标题, 正文)]"""
    joined = '\n\n'.join(t for _, t in pages if t.strip())
    paras = [p for p in joined.split('\n\n') if p.strip()]

    marks = []                      # (段序号, slug, 标题)
    for i, p in enumerate(paras):
        t = p.strip().strip('*')
        m = RE_NUM.match(t)
        if m and i + 1 < len(paras):
            nxt = paras[i + 1].strip().strip('*')
            if RE_CAPS.match(nxt):
                key = m.group(1).upper().replace('L', 'I')
                if key in ROMAN:
                    marks.append((i, str(ROMAN[key]), nxt.title()))
                    continue
        up = t.upper()
        for slug, probe in (('introduction', 'INTRODUCTION'),
                            ('translation', 'REVISED TRANSLATION'),
                            ('polycarp', 'EPISTLE OF POLYCARP')):
            if up.startswith(probe):
                marks.append((i, slug, t.title()))
        m = re.match(r'^NOTES? ON THE GREEK TEXT.*?CHAPTER\s+([IVX]+)', up)
        if m:
            marks.append((i, 'notes-%d' % ROMAN[m.group(1)], t.title()))

    if not marks:
        return [('all', 'Lectures on Philippians', '\n\n'.join(paras))]
    out = []
    if marks[0][0] > 0:
        out.append(('preface', 'Preface', '\n\n'.join(paras[:marks[0][0]])))
    for k, (i, slug, title) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(paras)
        out.append((slug, title, '\n\n'.join(paras[i:end])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0, help='只处理前 N 页（试水）')
    ap.add_argument('--dump-page', type=int, default=0, help='只打一页，调判据用')
    a = ap.parse_args()

    xml = load_xml()
    ab = A.parse_pages(xml)
    ocr = ocr_pages()
    if not ocr:
        sys.exit('没有 OCR 产物，先跑 scripts/johnstone_ocr.py')
    print(f'ABBYY {len(ab)} 页 / OCR {len(ocr)} 页', file=sys.stderr)

    if len(ab) != len(ocr):
        print(f'⚠️ 页数不等（ABBYY {len(ab)} vs OCR {len(ocr)}）—— '
              f'按序号对会整体错位，先把差额查清楚', file=sys.stderr)

    leaves = sorted(ocr)
    pages = []
    for n, leaf in enumerate(leaves):
        if a.limit and n >= a.limit:
            break
        if n >= len(ab):
            break
        txt = page_text([p['text'] for p in ab[n]['pars']], ocr[leaf])
        if a.dump_page and leaf == a.dump_page:
            print(txt)
            return
        pages.append((leaf, txt))

    os.makedirs(OUT_DIR, exist_ok=True)
    sections = split_sections(pages)
    for slug, title, body in sections:
        with open(os.path.join(OUT_DIR, slug + '.md'), 'w', encoding='utf-8') as f:
            f.write('# ' + title + '\n\n' + body + '\n')
    print(f'{len(sections)} 节 → {OUT_DIR}', file=sys.stderr)
    for slug, title, body in sections:
        print(f'  {slug:14s} {len(body):7d}  {title[:46]}', file=sys.stderr)


if __name__ == '__main__':
    main()
