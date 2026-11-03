#!/usr/bin/env python3
"""dickson_raw/matthew/en_chapters/*.md（+ 判读表、缺页补录）→ dickson/matthew/*.md

    python3 scripts/publish_dickson_en.py            # 试跑
    python3 scripts/publish_dickson_en.py --apply

大卫·迪克森《马太福音简释》1651（第三版）。一段经文一页（页名 `<章>-<首节>`），每章一页目录。
共用逻辑在 tcp_publish.py。

录入本第五章 23 节后缺原书 pp. 52–53（`〈MISSING:1〉`）：据 1647 年初版胶片影像补录的文字放 supplied/1.md，
发布时换进去，外包 `.dk-supplied` 并加一行说明；还没补录时照样留一行红字说明缺了哪两页。
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dickson_common as tc  # noqa: E402
import tcp_publish  # noqa: E402
from extract_dickson import NV  # noqa: E402

SUPPLIED = tc.RAW / 'supplied'
RE_MISS = re.compile(r'〈MISSING:(\d+)〉')
MISSING_PAGES = {1: 'pp. 52–53'}


def supplied(m):
    n = int(m.group(1))
    f = SUPPLIED / f'{n}.md'
    pp = MISSING_PAGES[n]
    if not f.exists():
        return (f'\n\n<p class="dk-supplied-note dk-gap">[{pp} of the 1651 edition are missing from the '
                f'transcription here (TCP gap {n}). 录入本此处缺原书 {pp}，待据 1647 年初版胶片影像补录。]</p>\n\n')
    body = f.read_text(encoding='utf-8').strip()
    return (f'\n\n<div class="dk-supplied" markdown="1">\n\n<p class="dk-supplied-note">{pp} of the 1651 edition are '
            'missing from the EEBO-TCP transcription; supplied here from the page images of the first edition '
            f'(Glasgow, 1647). 录入本缺原书 {pp}，据 1647 年格拉斯哥初版胶片影像补录。</p>\n\n' + body + '\n\n</div>\n\n')


class Dickson(tcp_publish.Book):
    def load_page(self, slug):
        md = super().load_page(slug)
        md = RE_MISS.sub(supplied, md)
        return re.sub(r'\n{3,}', '\n\n', md)


def about_en(f):
    return [
        '<p><b>About this text.</b> EEBO-TCP A35949 (the third edition, London: for Ralph Smith, 1651; Wing D1400), '
        'keyed by hand from the EEBO microfilm; CC0. Original spelling and italics are retained; the long s is printed '
        'as s. Page numbers of the original are kept as in-page anchors. Verse headings misprinted in the source '
        '(10:19 as 29; 12:8–9 as 18 and 8; 12:27 as 17) are left as printed; pages are named by the true verse. '
        'Pages 52–53 (on Matthew 5:24–30) are missing from the transcription.</p>',
        f'<p><b>Illegible places.</b> The keyers marked {f["n"]} places they could not read from the film images. '
        f'{f["w"]} have been read from the page images so far; {f["c"]} are editorial conjectures shown '
        f'<span class="dk-conj">[in brackets]</span>. The rest remain marked <span class="dk-gap">in red</span>.</p>']


def about_zh(f):
    return [
        '<p class="dk-note-zh"><b>文本说明。</b>本书据 EEBO-TCP 人工录入本 A35949（第三版，伦敦 1651 年，Wing D1400，'
        'EEBO 缩微胶片）。保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点。原书有几处经文头节号印错'
        '（10:19 印作 29；12:8、9 印作 18、8；12:27 印作 17），正文照录，页名按真节号。'
        '录入本缺原书第 52–53 页（马太福音 5:24–30 的讲解），待据 1647 年格拉斯哥初版的胶片影像补录。'
        f'录入本有 {f["n"]} 处读不出的字，目前已看图读出 {f["w"]} 处；{f["c"]} 处为编者推补，以 '
        '<span class="dk-conj">[方括号]</span> 另色标出；其余标红留在明面，待对照 Internet Archive 所藏 1651、1647 '
        '两版胶片灰度扫描逐处判读。判读记录见 <code>dickson_raw/matthew/</code>。</p>']


BOOK = Dickson(
    tc=tc, NV=NV, slug='dickson', book='matthew', P='dk', layout='dickson-chapter',
    author='David Dickson', years='1583?–1663', name='Dickson on Matthew', ref='Matthew',
    edition='A Brief Exposition of the Evangel of Jesus Christ according to Matthew · '
            'the third edition, London: for Ralph Smith, 1651',
    front=[('title', 'Title Page', 'London, 1651'),
           ('dedication', 'Epistle Dedicatory', 'To the Earl of Loudoun, Chancellor of Scotland'),
           ('to-the-reader', 'To the Honest-Hearted Reader', ''),
           ('titles', 'The Titles of the Book', 'The New Testament; the Gospel according to Matthew')],
    back=[],
    back_label='',
    about_en=about_en, about_zh=about_zh,
    witness_zh='1651、1647 两版的胶片灰度扫描')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    BOOK.publish(a.apply)


if __name__ == '__main__':
    main()
