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
import collections
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


def reprint_counts():
    """推补表各类条数 + 重排本核对后仍未落的（删去 / 两本冲突）。首页说明照此生成，表改首页跟着变。"""
    appr = {r[0]: r[2] for r in tc._tsv('gap_approved.tsv')}
    chk = tc._tsv('reprint_check.tsv')
    k = collections.Counter(appr.values())
    return dict(same=k['重排本同'], alt=k['重排本改'], ctx=k['正文旁证'],
                gone=sum(1 for r in chk if r[3] == '缺' and r[0] not in appr),
                clash=sum(1 for r in chk if r[3] == '异' and r[0] not in appr),
                checked=len(chk))


def about_en(f):
    r = reprint_counts()
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
        'read from the film images, and the Greek and Hebrew, which they did not transcribe. They have been filled in two steps.</p>',
        '<p>(1) <b>Read from the film.</b> Each place was checked against the EEBO film images of the same editions (Internet Archive): '
        f'{f["w"]} could be read there and are printed as plain text.</p>',
        f'<p>(2) <b>Checked against a second copy.</b> At {r["checked"]} places the film itself is blotted or show-through covers the '
        'letters, and only a conjecture was possible. The film, and the TCP keyers who worked from it, are one and the same copy, so '
        'each conjecture was checked against a copy printed from a different original: the Edinburgh reprint of 1863 '
        '(J. Nichol, ed. James Sherman; Internet Archive <i>anexpositionofth00greeuoft</i>). '
        f'{f["c"]} places are filled from that check and shown in <span class="gh-conj">[brackets]</span>: '
        f'{r["same"]} where the reprint has the same word as the conjecture (the original spelling is kept); '
        f'{r["alt"]} where the reprint differs and is followed (chapter and verse numbers restored to the original style); '
        f'{r["ctx"]} where the reprint drops the passage but its English rendering or verse range confirms the conjecture. '
        'The reprint modernises spelling, so it confirms the word, not the original spelling.</p>',
        f'<p>(3) <b>Still open.</b> The remaining places stay <span class="gh-gap">in red</span>. They include {r["gone"]} '
        'where the reprint omits the Latin, Greek or marginal note altogether (every one checked on the reprint’s page images), '
        f'{r["clash"]} where the film and the reprint disagree, and the places in Volumes I–II, for which no film of the same '
        'edition is available.</p>']

def about_zh(f):
    r = reprint_counts()
    return [
        '<p class="gh-note-zh"><b>文本说明。</b>格林希尔在伦敦每周的「讲解讲座」上逐节讲解以西结书，1645 至 1662 年间分五卷出版：'
        '第一卷第 1–5 章（1645）、第二卷第 6–13 章（1649）、第三卷第 14–19 章（1651）、第四卷第 20–29 章（1658）、第五卷第 30–48 章（1662）。'
        '本站正文据 EEBO-TCP 对这五卷初版的人工录入本（A85666、A85667、A42015、A85668、A42016，CC0 公共领域授权），'
        '保留原书拼写与斜体，长 ſ 作 s；印本页码保留为页内锚点，各卷页码自 1 起。'
        '每页一段经文：录入本标了分段的照原书分段，第四卷（第 20–29 章）录入本没有分段，按书中所引经文的节号切分。'
        '原书页边的纲目标记（Note 1、Observ. 1 等）在正文中以小标签显示。各卷勘误表、主题索引、经文索引与书商广告未收。</p>',
        f'<p class="gh-note-zh">录入本不完整之处共 {f["n"]} 处，包括录入者读不出的字母和词，以及没有录入的希腊文、希伯来文。分两步补：</p>',
        '<p class="gh-note-zh">①<b>看胶片读出。</b>逐处对照同版的 EEBO 胶片影像（Internet Archive），'
        f'看得清的 {f["w"]} 处直接补成正文，不加标记。</p>',
        f'<p class="gh-note-zh">②<b>对照另一实物。</b>其中 {r["checked"]} 处胶片本身就被墨团、透印盖住，只能推断。'
        'TCP 录入本也是照这同一份胶片录的，两者算不得两个证据；所以这些推断逐条对照了另一本实物排出的书——'
        '1863 年爱丁堡 Nichol 重排本（James Sherman 编，Internet Archive <i>anexpositionofth00greeuoft</i>），逐页看图。'
        f'据此补出 {f["c"]} 处，正文以<span class="gh-conj">[方括号]</span>另色标出：'
        f'重排本与推断同词的 {r["same"]} 处，照原书拼法写；重排本与推断不同的 {r["alt"]} 处，照重排本写（章节号换回原书写法）；'
        f'重排本删去原文、但正文所留英译或节号区间与推断相合的 {r["ctx"]} 处，照推断写。'
        '重排本已改现代拼法，只能证明是哪个词，不能证明原书怎么拼。逐条依据见下表，核对记录见 '
        '<code>greenhill_raw/ezekiel/reprint_check.tsv</code>。</p>',
        f'<p class="gh-note-zh">③<b>仍读不出的</b>照旧<span class="gh-gap">标红</span>留在明面，其中有：重排本把拉丁文、希腊文或旁注整句删去、'
        f'无可对照的 {r["gone"]} 处（都已逐页看图核实）；胶片残字与重排本对不上、尚待定夺的 {r["clash"]} 处；'
        '以及第一、二卷——网上没有这两卷同版的胶片。判读记录见 <code>greenhill_raw/ezekiel/gap_review.tsv</code>。</p>']

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
