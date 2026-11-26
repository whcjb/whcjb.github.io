#!/usr/bin/env python3
"""burroughs_raw/hosea/en_chapters/*.md（+ 判读表）→ burroughs/hosea/*.md

    python3 scripts/extract_burroughs.py --apply && python3 scripts/publish_burroughs_en.py            # 试跑
    python3 scripts/publish_burroughs_en.py --apply

耶利米·巴罗夫《何西阿书讲解》四卷（1650–1652）。共用 tcp_publish.Book：第 1–3 章一讲一页、第 4–13 章一段经文一页
（分页见 extract_burroughs.py），每章一页目录 `<章>.md`。卷首：四卷各自的书名页与致读者书；卷末：第四卷「校订者致读者」。
巴罗夫讲到 13:11 为止，书首页第 14 章标灰。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import burroughs_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_burroughs import LAST, NV, VOLS  # noqa: E402


def _meta(key):
    od = json.loads((tc.RAW / 'order.json').read_text(encoding='utf-8'))
    out = []
    for f in od[key]:
        chs = next(c for t, y, c in VOLS if t == f['tcp'])
        out.append((f['slug'], f['title'], f'Chapters {chs[0]}–{chs[-1]} · {f["year"]} · EEBO-TCP {f["tcp"]}'))
    return out


class Book(tcp_publish.Book):
    def build_pages(self):
        """第 1–3 章是讲章：标题、目录标签带讲次（同一节起头的有两三讲，光写节号分不开）。"""
        pages = super().build_pages()
        lec = {x['slug']: x['lecture'] for x in self.tc.order()['sections'] if 'lecture' in x}
        for p in pages:
            if p['slug'] in lec:
                p['short'] = f'Lecture {lec[p["slug"]]} · {p["short"]}'
                p['title'] = f'{p["title"]} · Lecture {lec[p["slug"]]}'
        return pages


def about_en(f):
    vols = '; '.join(f'Vol. {i} (ch. {c[0]}–{c[-1]}, {y}): {t}' for i, (t, y, c) in enumerate(VOLS, 1))
    return [
        '<p><b>About this text.</b> Burroughs preached through Hosea in weekly lectures at St Michael’s, Cornhill, London, '
        'from 1642 until his death in November 1646. The lectures were published in four volumes: chapters 1–3 in his '
        'lifetime (here in the collected edition of 1652), chapters 4–13 after his death, edited by Thomas Goodwin, '
        'William Greenhill, Sidrach Simpson, William Bridge and others. He reached Hosea 13:11; the rest of the prophecy '
        'was completed by others (Thomas Hall on 13:12–16, Edward Reynolds on chapter 14) and is not included here. '
        f'The text is the keyed transcription made by the Text Creation Partnership from the EEBO microfilms ({vols}), '
        'released under CC0. Original spelling and italics are retained; the long s is printed as s. Page numbers of the '
        'original are kept as in-page anchors; each volume is paged from 1. Chapters 1–3 are given one lecture to a page, '
        'with the verses each lecture takes up (a lecture often resumes in the middle of the verse where the last one '
        'stopped); chapters 4–13 are divided into passages of a few verses, following the sections of the original. '
        'Marginal notes are printed as footnotes. The tables of contents, indexes and booksellers’ advertisements are not '
        'included.</p>',
        f'<p><b>Illegible places.</b> The transcription is incomplete at {f["n"]} places: letters or words the keyers could not '
        'read from the film images, and the Greek and Hebrew, which they did not transcribe. None of these has yet been '
        'checked against the page images; they are shown <span class="jb-gap">in red</span>.</p>']


def about_zh(f):
    return [
        '<p class="jb-note-zh"><b>文本说明。</b>巴罗夫自 1642 年起在伦敦康希尔圣米迦勒堂（St Michael’s, Cornhill）的周间讲座上'
        '逐节讲解何西阿书，直到 1646 年 11 月去世。讲稿分四卷出版：第 1–3 章生前即出（此处用 1652 年合订本），'
        '第 4–13 章由古德温（Thomas Goodwin）、格林希尔（William Greenhill）、辛普森（Sidrach Simpson）、布里奇（William Bridge）'
        '等人在他身后整理刊行。他讲到 13:11 为止，其余由别人续完（13:12–16 霍尔 Thomas Hall，第 14 章雷诺兹 Edward Reynolds），'
        '本站未收。正文据 EEBO-TCP 对这四卷的人工录入本（A30572、A77979、A30574、A30575，CC0 公共领域授权），'
        '保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点，各卷页码自 1 起。'
        '第 1–3 章一讲一页，标出每讲所讲的经节（常从上一讲讲到的那节中间接着讲，故节段前后相叠）；'
        '第 4–13 章照原书分段，每页一段经文。页边旁注排成页底脚注。各卷目录、索引与书商广告未收。</p>',
        f'<p class="jb-note-zh">录入本不完整之处共 {f["n"]} 处，包括录入者读不出的字母和词，以及没有录入的希腊文、希伯来文；'
        '这些都还没有对照原书影像补出，正文中<span class="jb-gap">标红</span>留在明面。</p>']


BOOK = Book(
    tc=tc, NV={**NV, **LAST}, slug='burroughs', book='hosea', P='jb', layout='burroughs-chapter',
    author='Jeremiah Burroughs', years='1599–1646', name='Burroughs on Hosea', ref='Hosea',
    edition='An Exposition of the Prophesie of Hosea · London, 4 vols., 1650–1652',
    front=_meta('front'), back=_meta('back'), back_label='Appended Matter',
    all_chapters=list(range(1, 15)),
    about_en=about_en, about_zh=about_zh,
    witness_zh='原版影像',
    margin_footnotes=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
