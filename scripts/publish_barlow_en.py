#!/usr/bin/env python3
"""barlow_raw/2timothy/en_chapters/*.md（+ 判读表、缺页补录）→ barlow/2timothy/*.md

    python3 scripts/publish_barlow_en.py            # 试跑
    python3 scripts/publish_barlow_en.py --apply

约翰·巴洛《提摩太后书第一章讲解》1625。一节一页（页名 `1-<节>`），另有全章导论一页。共用逻辑在 tcp_publish.py。

录入本 16 处「缺 2 页」（`〈MISSING:N〉`）：据 1625 年胶片影像补录的文字放 supplied/N.md，发布时换进去，
外包 `.bl-supplied` 并加一行说明；还没补录的照样留一行红字说明缺了哪两页。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import barlow_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_barlow import NV  # noqa: E402

SUPPLIED = tc.RAW / 'supplied'
RE_MISS = re.compile(r'〈MISSING:(\d+)〉')


def supplied(m):
    n = int(m.group(1))
    f = SUPPLIED / f'{n}.md'
    if not f.exists():
        return (f'\n\n<p class="bl-supplied-note bl-gap">[Two pages of the 1625 edition are missing from the '
                f'transcription here (TCP gap {n}). 录入本此处缺两页，待据胶片影像补录。]</p>\n\n')
    body = f.read_text(encoding='utf-8').strip()
    return ('\n\n<div class="bl-supplied" markdown="1">\n\n<p class="bl-supplied-note">Two pages missing from the '
            'EEBO-TCP transcription, supplied here from the page images of the 1625 edition (录入本缺此两页，据 1625 年'
            '胶片影像补录).</p>\n\n' + body + '\n\n</div>\n\n')


class Barlow(tcp_publish.Book):
    def load_page(self, slug):
        md = super().load_page(slug)
        md = RE_MISS.sub(supplied, md)
        return re.sub(r'\n{3,}', '\n\n', md)


def about_en(f):
    return [
        '<p><b>About this text.</b> EEBO-TCP A04220 (London: I. D[awson] for Iohn Bellamie, 1625; STC 1434; the '
        'engraved title is dated 1624), keyed by hand from the EEBO microfilm; CC0. This edition covers the first '
        'chapter of 2 Timothy only. Original spelling and italics are retained; the long s is printed as s. Page '
        'numbers of the original are kept as in-page anchors. The film used by the keyers lacked sixteen openings '
        '(two pages each); those pages are supplied from the grayscale scan of the 1625 edition and marked with a '
        'dashed rule.</p>',
        f'<p><b>Illegible places.</b> The keyers marked {f["n"]} places they could not read. {f["w"]} were read from '
        f'the grayscale scan of the 1625 edition (Internet Archive), place by place against the page image; '
        f'{f["c"]} are editorial conjectures shown <span class="bl-conj">[in brackets]</span>. {f["left"]} places '
        'still unread remain marked <span class="bl-gap">in red</span>; all are listed below.</p>']


def about_zh(f):
    return [
        '<p class="bl-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A04220（伦敦 1625 年，STC 1434；'
        '刻版扉页作 1624 年）。这一版只讲提摩太后书第一章。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。'
        '录入所据的胶片漏拍了十六个对开（每处两页），这些页据 1625 年本的胶片灰度扫描补录，正文中以左侧虚线标出。'
        f'录入本有 {f["n"]} 处读不出的字，{f["w"]} 处对照胶片灰度扫描（Internet Archive）逐处看图读出；'
        f'{f["c"]} 处为编者推补，以 <span class="bl-conj">[方括号]</span> 另色标出；仍读不出的 {f["left"]} 处标红留在明面。'
        '推补与读不出的都逐条列在下表，判读记录见 <code>barlow_raw/2timothy/</code>。</p>']


BOOK = Barlow(
    tc=tc, NV=NV, slug='barlow', book='2timothy', P='bl', layout='barlow-chapter',
    author='John Barlow', years='b. 1580/81', name='Barlow on 2 Timothy 1', ref='2 Timothy',
    edition='An Exposition of the Second Epistle of the Apostle Paul to Timothy, the First Chapter · '
            'London: I. D[awson] for Iohn Bellamie, 1625',
    front=[('title', 'Title Page', 'London, 1624/25'),
           ('dedication', 'Epistle Dedicatory', 'To the Mayor and Magistrates of Plymouth'),
           ('to-the-reader', 'The Epistle to the Reader', ''),
           ('contents', 'The Principal Heads Handled', 'Doctrines, with pages'),
           ('introduction', 'The Scope and Analysis of the Epistle', '')],
    back=[],
    back_label='',
    about_en=about_en, about_zh=about_zh,
    witness_zh='1625 年本的胶片灰度扫描',
    author_note='chapter 1',
    coauthor=('Thomas Hall (1610–1665) · chapters 3–4', '/hall/2timothy/',
              'A Practical and Polemical Commentary … upon the Third and Fourth Chapters of the Latter Epistle '
              'of Saint Paul to Timothy · London, 1658'),
    all_chapters=[1, 2, 3, 4], others={3: ('Hall', '/hall/2timothy/3/'), 4: ('Hall', '/hall/2timothy/4/')},
    companion_zh='巴洛这一版只讲第一章。第三、四章见本站所收霍尔《提摩太后书第三、四章注释》（1658）；'
                 '第二章巴洛 1632 年对开本有讲解，但没有录入本，本站暂缺。')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
