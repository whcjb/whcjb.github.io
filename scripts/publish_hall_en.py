#!/usr/bin/env python3
"""hall_raw/2timothy/en_chapters/*.md（+ 判读表，见 hall_common.py）→ hall/2timothy/*.md

    python3 scripts/publish_hall_en.py            # 试跑
    python3 scripts/publish_hall_en.py --apply

托马斯·霍尔《提摩太后书第三、四章注释》1658。一段经文一页（页名 `<章>-<首节>`），每章一页目录；
第三章第 8 节后插的加尔文《驳放纵派》第七章译文单独一页。共用逻辑在 tcp_publish.py。
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import hall_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_hall import NV  # noqa: E402


def about_en(f):
    return [
        '<p><b>About this text.</b> EEBO-TCP A45335 (London: E. Tyler for John Starkey, 1658; Wing H436), keyed by '
        'hand from the EEBO microfilm; CC0. Hall expounds only the last two chapters of 2 Timothy. Original spelling '
        'and italics are retained; the long s is printed as s. Page numbers of the original are kept as in-page '
        'anchors.</p>',
        f'<p><b>Illegible places.</b> The keyers marked {f["n"]} places they could not read from the film images. '
        f'{f["w"]} were read from the grayscale scan of the same film (Internet Archive), place by place against the '
        f'page image; {f["c"]} are editorial conjectures shown <span class="hl-conj">[in brackets]</span>. '
        f'{f["left"]} places still unread remain marked <span class="hl-gap">in red</span>; all are listed below.</p>']


def about_zh(f):
    return [
        '<p class="hl-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A45335（伦敦 1658 年，Wing H436，'
        'EEBO 缩微胶片）。霍尔只讲提摩太后书第三、四章。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。'
        f'录入本有 {f["n"]} 处读不出的字，{f["w"]} 处对照同一卷胶片的灰度扫描（Internet Archive）逐处看图读出；'
        f'{f["c"]} 处为编者推补，以 <span class="hl-conj">[方括号]</span> 另色标出；仍读不出的 {f["left"]} 处标红留在明面。'
        '推补与读不出的都逐条列在下表，判读记录见 <code>hall_raw/2timothy/</code>。</p>']


BOOK = tcp_publish.Book(
    tc=tc, NV=NV, slug='hall', book='2timothy', P='hl', layout='hall-chapter',
    author='Thomas Hall', years='1610–1665', name='Hall on 2 Timothy 3–4', ref='2 Timothy',
    edition='A Practical and Polemical Commentary … upon the Third and Fourth Chapters of the Latter Epistle '
            'of Saint Paul to Timothy · London: E. Tyler for John Starkey, 1658',
    front=[('title', 'Title Page', 'London, 1658'),
           ('epistle-to-reader', 'An Epistle to the Reader', 'Edmund Calamy'),
           ('dedication', 'Epistle Dedicatory', 'To the City of Worcester'),
           ('to-the-reader', 'To the Reader', 'Thomas Hall'),
           ('to-the-reader-2', 'To the Reader', 'John Ley'),
           ('books', 'Books Formerly Published by the Author', ''),
           ('errata', 'Errata', '')],
    extra=[('3-8', '3-8-calvin', 'Calvin against the Libertines', 'Calvin, Against the Libertines, ch. 7')],
    back=[('postscript', 'Post-script', 'The subscription of the Epistle'),
          ('questions', 'Questions Discussed', 'Cases of conscience, with pages'),
          ('texts', 'Texts Explained', 'Scripture index'),
          ('subject-index', 'A Table of the Principal Things', 'Subject index'),
          ('starkey', 'Books Sold by John Starkey', 'Publisher’s list')],
    back_label='Post-script and Tables',
    about_en=about_en, about_zh=about_zh,
    witness_zh='同一卷胶片的灰度扫描',
    author_note='chapters 3–4',
    coauthor=('John Barlow (b. 1580/81) · chapter 1', '/barlow/2timothy/',
              'An Exposition of the Second Epistle of the Apostle Paul to Timothy, the First Chapter · London, 1625'),
    all_chapters=[1, 2, 3, 4], others={1: ('Barlow', '/barlow/2timothy/1/')},
    companion_zh='霍尔只讲第三、四章。第一章见本站所收巴洛《提摩太后书第一章讲解》（1625）；'
                 '第二章巴洛 1632 年对开本有讲解，但没有录入本，本站暂缺。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
