#!/usr/bin/env python3
"""greenhill_raw/ezekiel/en_chapters/*.md（+ 判读表）→ greenhill/ezekiel/*.md

    python3 scripts/extract_greenhill.py --apply && python3 scripts/publish_greenhill_en.py            # 试跑
    python3 scripts/publish_greenhill_en.py --apply

威廉·格林希尔《以西结书释义》五卷（1645–1662）。共用 tcp_publish.Book：一段经文一页（页名 `<章>-<首节>`，
分段见 extract_greenhill.py），每章一页目录 `<章>.md`。卷首：五卷各自的书名页与献辞／致读者书，第一卷的
「致真理的爱慕者」「全书引言」，以及第一章前的总论（prolegomena）。
缺字按 gap_review.tsv（看图读出）回填；推断（P:）待用户同意后进 gap_approved.tsv。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import greenhill_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_greenhill import NV, VOLS  # noqa: E402

FRONT_SUB = {'prolegomena': 'The general preface to the whole exposition (Vol. I, 1645)'}


def front():
    od = json.loads((tc.RAW / 'order.json').read_text(encoding='utf-8'))
    out = []
    for f in od['front']:
        chs = next(c for t, y, c in VOLS if t == f['tcp'])
        sub = FRONT_SUB.get(f['slug'], f'Chapters {chs[0]}–{chs[-1]} · {f["year"]} · EEBO-TCP {f["tcp"]}')
        out.append((f['slug'], f['title'], sub))
    return out


def about_en(f):
    vols = '; '.join(f'Vol. {i} (ch. {c[0]}–{c[-1]}, {y}): {t}' for i, (t, y, c) in enumerate(VOLS, 1))
    return [
        '<p><b>About this text.</b> Greenhill delivered this exposition as weekly lectures in London and published it '
        f'in five volumes between 1645 and 1662. The text here is the keyed transcription of the first editions made by the '
        f'Text Creation Partnership from the EEBO microfilms ({vols}), released under CC0. Original spelling and italics are '
        'retained; the long s is printed as s. Page numbers of the original are kept as in-page anchors; each volume is '
        'paged from 1. The commentary is divided here into passages of a few verses each, following the sections of the '
        'original where the transcription marks them; the fourth volume (chapters 20–29), which has no such divisions in '
        'the transcription, is divided at the verses it quotes. The marginal heads of the original (<i>Note 1</i>, '
        '<i>Observ. 1</i> …) are shown as small tags. The errata lists, the tables of matters and of Scripture places, '
        'and the booksellers’ advertisements are not included.</p>',
        f'<p><b>Illegible places.</b> The transcription is incomplete at {f["n"]} places: letters or words the keyers could not '
        'read from the film images, and the Greek and Hebrew, which they did not transcribe. These are being checked against '
        'the EEBO film images of the same editions (Internet Archive). '
        f'{f["w"]} have been read from the page images so far; the rest remain marked <span class="gh-gap">in red</span>.</p>']


def about_zh(f):
    return [
        '<p class="gh-note-zh"><b>文本说明。</b>格林希尔在伦敦每周的「讲解讲座」上逐节讲解以西结书，1645 至 1662 年间分五卷出版：'
        '第一卷第 1–5 章（1645）、第二卷第 6–13 章（1649）、第三卷第 14–19 章（1651）、第四卷第 20–29 章（1658）、第五卷第 30–48 章（1662）。'
        '本站正文据 EEBO-TCP 对这五卷初版的人工录入本（A85666、A85667、A42015、A85668、A42016，CC0 公共领域授权），'
        '保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点，各卷页码自 1 起。'
        '每页一段经文：录入本标了分段的照原书分段，第四卷（第 20–29 章）录入本没有分段，按书中所引经文的节号切分。'
        '原书页边的纲目标记（Note 1、Observ. 1 等）在正文中以小标签显示。各卷勘误表、主题索引、经文索引与书商广告未收。</p>',
        f'<p class="gh-note-zh">录入本不完整之处共 {f["n"]} 处，包括录入者读不出的字母和词，以及没有录入的希腊文、希伯来文。'
        '正在逐处对照同版的 EEBO 胶片影像（Internet Archive）补出：'
        f'已看图读出 {f["w"]} 处，其余仍<span class="gh-gap">标红</span>留在明面。判读记录见 <code>greenhill_raw/ezekiel/gap_review.tsv</code>。</p>']


BOOK = tcp_publish.Book(
    tc=tc, NV=NV, slug='greenhill', book='ezekiel', P='gh', layout='greenhill-chapter',
    author='William Greenhill', years='1591–1671', name='Greenhill on Ezekiel', ref='Ezekiel',
    edition='An Exposition of the Prophet Ezekiel, with Useful Observations thereupon · '
            'London, 5 vols., 1645–1662',
    front=front(), back=[], back_label='',
    about_en=about_en, about_zh=about_zh,
    witness_zh='原版影像',
    conj_note_col=4,
    conj_intro_zh='以下各处录入本标为读不出，原版胶片影像上也被墨团、透印盖住。编者对照 1863 年爱丁堡 Nichol 重排本'
                  '（Sherman 编，另一实物排印，见 Internet Archive anexpositionofth00greeuoft）补出：重排本与编者推断同词的，'
                  '照原书拼法写；不同的，照重排本写（章节号换回原书体例）。重排本已改现代拼法，只能证词，不能证原书拼法。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
