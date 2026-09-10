#!/usr/bin/env python3
"""按 token 定位并裁出 1864 扫描件的对应行，供人眼（或读图）判读。

为什么要走影像：OCR 判不动的地方，两份 OCR 往往在**同一处**都读崩了
（`icine` / `ivine` 其实都是 wine），拿一份崩的去改另一份崩的没有意义。
PDF 的文本层是同一份 ABBYY OCR，也不算第三方——只有页面影像是。

PDF 与 XML 的页序**本身就错位**（584 页 vs 590 页，PROVENANCE 记过），
所以不按页序号套，而是：正文里的 `<!-- PAGE n -->` 给出**书页页码**，
再用页眉里印的页码标定出 PDF 页序的偏移（实测 pdf_index = 书页 + 3），
最后仍用文本层搜锚点确认落在了对的一页上。
"""
import argparse, re, sys
from pathlib import Path
import fitz

ROOT = Path(__file__).resolve().parent.parent
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
OFFSET = 3          # pdf_index = 书页页码 + OFFSET，由页眉标定


def book_page(chapter, token):
    """token 落在书上第几页：取它前面最近的一个 <!-- PAGE n --> 标记。"""
    text = (ROOT / f'alexander/psalms/{chapter}.md').read_text(encoding='utf-8')
    i = text.find(token)
    if i < 0:
        return None, None
    pages = [(m.start(), int(m.group(1))) for m in re.finditer(r'<!-- PAGE (\d+) -->', text)]
    page = next((p for pos, p in reversed(pages) if pos < i), None)
    # 锚：token 前面几个只含字母的词，用来在 PDF 文本层里确认页码没搞错
    before = re.findall(r'[A-Za-z]{3,}', text[max(0, i - 90):i])
    return page, ' '.join(before[-3:])


def crop(doc, page_no, anchor, token, out, dpi=400):
    """在候选页里找锚点，裁出它所在的行及上下各一行。"""
    # 先按残串本身搜：PDF 的文本层与我们手上的 en_chapters 同出一份 ABBYY
    # OCR，同一个残串在那边一模一样，命中最准。搜不到（被跨行拆开、或
    # repair 已经改过）再退回上下文锚。
    for cand in (page_no, page_no + 1, page_no - 1):
        idx = cand + OFFSET
        if not (0 <= idx < doc.page_count):
            continue
        p = doc[idx]
        rects = p.search_for(token) or p.search_for(anchor) or p.search_for(anchor.split()[-1])
        if not rects:
            continue
        r = rects[0]
        clip = fitz.Rect(0, max(0, r.y0 - 26), p.rect.x1, min(p.rect.y1, r.y1 + 26))
        p.get_pixmap(dpi=dpi, clip=clip).save(out)
        return idx
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('targets', nargs='+', help='形如 105:Uood，篇号:token')
    ap.add_argument('--out', default='/tmp')
    args = ap.parse_args()
    doc = fitz.open(PDF)
    for t in args.targets:
        ch, tok = t.split(':', 1)
        page, anchor = book_page(ch, tok)
        if page is None:
            print(f'{t}\t正文里找不到这个 token'); continue
        out = f'{args.out}/pg_{ch}_{tok[:12]}.png'
        idx = crop(doc, page, anchor, tok, out)
        print(f'{t}\t书页 {page}\tPDF {idx}\t锚 {anchor!r}\t{out if idx else "定位失败"}')


if __name__ == '__main__':
    main()
