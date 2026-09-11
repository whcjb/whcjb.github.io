#!/usr/bin/env python3
"""把正文里的希伯来文/希腊文活字**重新 OCR 回来**。

以赛亚书的残留错字里，最大的一块一直被记成「无解」：Alexander 大量征引
希伯来原文与七十士译本，而 IA 那遍 ABBYY 是按拉丁字母跑的，希伯来活字被
读成一串拉丁乱码（`עזובת` → `raits`）。判词典、多证人、页面影像三条路都救
不了它——证人是同样按拉丁字母 OCR 的，影像只能告诉人「这里是希伯来文」。

**解法是对那几块重新跑一遍 OCR，换成希伯来文/希腊文模型。** 证据链是完整的：
ABBYY XML 里每个字符都带坐标，所以能精确定位到那几个字的外接框，从 PDF 原图
按 600dpi 裁出来，交给 tesseract 的 `heb` / `grc` 模型。实测第一例就读对了：
书页 332「utterly destroyed, raits is variously understood」那处，
tesseract -l heb 给出 `עזובת`，与人工翻影像读出的一致。

用生成式模型做 OCR 是明令禁止的（会「改词意」），这里用的是 tesseract，
与站内扫描件一贯的做法一致。

流程：
    XML 逐行 → 切 token → 判「像不像拉丁字母残渣」→ 相邻残渣合成一段
    → 取外接框 → PDF 裁图 600dpi → tesseract heb / grc → 取更像那套字母的
    → 写进 alexander_raw/isaiah/hebrew_ocr.tsv（带上下文锚，供 repair 阶段替换）

用法：
    python3 scripts/isaiah_hebrew_ocr.py --pages 400-420   # 先试一段
    python3 scripts/isaiah_hebrew_ocr.py                   # 全书
"""
import argparse
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word

NS = '{http://www.abbyy.com/FineReader_xml/FineReader6-schema-v1.xml}'
ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander_raw/isaiah/src'
OUT = ROOT / 'alexander_raw/isaiah/hebrew_ocr.tsv'
# 带 OCR 垃圾字符那一档单独出一份，见 --junk
OUT_JUNK = ROOT / 'alexander_raw/isaiah/hebrew_ocr_junk.tsv'
PDF = {'v1': Path.home() / 'Documents/论文/alexander/propheciesisaiah01alexuoft.pdf',
       'v2': Path.home() / 'Documents/论文/alexander/propheciesisaiah02alexuoft.pdf'}
XML = {'v1': SRC / 'v1.xml', 'v2': SRC / 'v2.xml'}
BODY = {'v1': (79, 730), 'v2': (47, 547)}

# 希伯来活字被按拉丁字母读出来时，ABBYY 常常在串里吐出非字母符号
# （`n^t`、`dwrj^ft`、`aa&evsia`、`oivon).y%`），它们是残渣的**正信号**。
# 一开始只列了 `^><|~` 五个，于是 `(aa&evsia`（其实是 ἀσϑένεια，grc 置信度 90）
# 因为那个 `&` 不在表里，连候选都算不上。凡是剥掉首尾标点后**里面**还留着
# 非字母数字字符的，一律算。
JUNK = re.compile(r'[^0-9A-Za-z]')
HEBREW = re.compile(r'[֐-׿]')
GREEK = re.compile(r'[Ͱ-Ͽἀ-῿]')
# 裁图时往外放一点，免得切掉字母的笔画
PAD = 8
DPI = 600


def looks_residue(tok, lex, junk_only=False):
    """候选：凡是判词典不认的拉丁串都算，**放宽比收紧划算**。

    第一版按字形收紧（词中大写 / 四连辅音 / 无元音），只捞到 2331 个候选，
    9444 个非词里 7113 个连试都没试过——`raits`（其实是 עזובת）就是被
    「它有元音」挡掉的。字形判据在这里根本不适用：拉丁字母误读希伯来字母
    的结果什么样都有。

    放宽的安全性不靠判据，靠**两台引擎对比**（见 emit）：拿同一张裁图分别
    跑拉丁与希伯来模型，拉丁活字上 `eng` 会读得又准又稳，希伯来活字上
    `eng` 只会吐垃圾而 `heb` 很稳。误判成本因此是多跑几次 tesseract，
    不是改错正文。
    """
    core = tok.strip(".,;:!?()[]'\"")
    if len(core) < 2 or not core.isascii():
        return False
    if JUNK.search(core):
        # 垃圾字符本身就说明这块活字 ABBYY 没读懂；只要还剩两个字母就值得一裁
        return len(re.sub(r'[^A-Za-z]', '', core)) >= 2
    if junk_only or not core.isalpha():
        return False
    return not is_word(core, lex)


def line_tokens(line):
    """一行 → [(文本, 左, 上, 右, 下)]，按空白切词"""
    cps = [c for c in line.iter(NS + 'charParams')]
    out, cur = [], []
    for c in cps:
        ch = c.text or ''
        if ch.strip():
            cur.append((ch, c))
        elif cur:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    toks = []
    for grp in out:
        txt = ''.join(ch for ch, _ in grp)
        box = (min(int(c.get('l')) for _, c in grp),
               min(int(c.get('t')) for _, c in grp),
               max(int(c.get('r')) for _, c in grp),
               max(int(c.get('b')) for _, c in grp))
        toks.append((txt, box))
    return toks


def ocr(png, lang, psm='7'):
    """→ (读数, 平均置信度)

    要置信度是因为：ABBYY 读对了的德文/拉丁文（`Todesschrecken`）也可能被
    形状判据误判成残渣，硬拿希腊模型去读，它会**硬凑**出一串希腊字母
    （`Τοαϊοεεοἠγοοίοη`）。这种硬凑的置信度很低，真正的希腊文则很高。
    """
    r = subprocess.run(['tesseract', png, 'stdout', '-l', lang, '--psm', psm,
                        'tsv'], capture_output=True, text=True)
    words, confs = [], []
    for line in r.stdout.splitlines()[1:]:
        f = line.split('\t')
        if len(f) < 12 or not f[11].strip():
            continue
        try:
            c = float(f[10])
        except ValueError:
            continue
        if c < 0:
            continue
        words.append(f[11])
        confs.append(c)
    text = re.sub(r'[|\s]+', ' ', ' '.join(words)).strip(' .,|')
    return text, (sum(confs) / len(confs) if confs else 0.0)


def main(page_range=None, junk_only=False):
    lex = build()
    rows = []
    n_page = 0
    for vol in ('v1', 'v2'):
        lo, hi = BODY[vol]
        doc = fitz.open(PDF[vol])
        ctx = ET.iterparse(XML[vol], events=('end',))
        idx = 0
        for _, el in ctx:
            if el.tag != NS + 'page':
                continue
            idx += 1
            if not (lo <= idx <= hi) or (page_range and not
                                         (page_range[0] <= idx <= page_range[1])):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[idx - 1]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            jobs = []
            for line in el.iter(NS + 'line'):
                toks = line_tokens(line)
                run = []
                for k, (txt, box) in enumerate(toks + [(None, None)]):
                    # 一段最多并四个词：判据放宽之后，连着几个专名会被并成
                    # 一大段，裁图跨度太大反而读不准
                    if (txt is not None and looks_residue(txt, lex, junk_only)
                            and len(run) < 4):
                        run.append((txt, box))
                        continue
                    if run:
                        j = crop(run, toks, page, sx, sy, vol, idx)
                        if j:
                            jobs.append(j)
                        run = []
            el.clear()
            # tesseract 是子进程，等它的时候 GIL 是放开的，所以线程池就够用。
            # 判据放宽之后候选涨到上万，串行跑要几个钟头。
            if jobs:
                with ThreadPoolExecutor(8) as pool:
                    rows.extend(r for r in pool.map(judge, jobs) if r)
            n_page += 1
            if n_page % 25 == 0:
                print(f'{vol} 扫描页 {idx}：累计读出 {len(rows)} 段', flush=True)
        doc.close()
    out = OUT_JUNK if junk_only else OUT
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write('vol\tscan_page\tbefore\tgarbage\tafter\tscript\treading\tconf\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(f'读出 {len(rows)} 段 → {out}')


def crop(run, toks, page, sx, sy, vol, scan_page):
    """裁图 + 记下上下文锚，交给 judge 去读"""
    garbage = ' '.join(t for t, _ in run)
    l = min(b[0] for _, b in run) - PAD
    t = min(b[1] for _, b in run) - PAD
    r = max(b[2] for _, b in run) + PAD
    b = max(b[3] for _, b in run) + PAD
    clip = fitz.Rect(l * sx, t * sy, r * sx, b * sy)
    if clip.width <= 0 or clip.height <= 0:
        return None
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as fh:
        png = fh.name
    page.get_pixmap(dpi=DPI, clip=clip).save(png)
    # 上下文锚：同一行里这段前后的词，用来在正文里唯一定位。
    # **必须按位置替换，不能按串全局替换**——同一串拉丁乱码可能来自不同的
    # 希伯来词（`bs` 在不同地方分别是 על / אל / כל），ABBYY 的误读是有损的。
    i = toks.index(run[0])
    j = toks.index(run[-1])
    clean = lambda x: re.sub(r'[\t\r\n]+', ' ', x).strip()
    return dict(png=png, vol=vol, scan_page=scan_page, garbage=clean(garbage),
                before=clean(' '.join(t for t, _ in toks[max(0, i - 4):i])),
                after=clean(' '.join(t for t, _ in toks[j + 1:j + 3])))


def judge(job):
    png, garbage = job['png'], job['garbage']
    (heb, ch_), (grc, cg) = ocr(png, 'heb'), ocr(png, 'grc')
    nh, ng = len(HEBREW.findall(heb)), len(GREEK.findall(grc))
    # 置信度门槛 65：低于这个的多半是模型在硬凑
    if nh >= 2 and ch_ >= 65 and (ch_ >= cg or ng < 2):
        script, reading, conf = 'heb', heb, ch_
    elif ng >= 2 and cg >= 65:
        script, reading, conf = 'grc', grc, cg
    else:
        Path(png).unlink(missing_ok=True)
        return None
    # 两台引擎对比：拉丁活字上 `eng` 读得又准又稳，希伯来活字上它只会吐垃圾。
    # 所以 `eng` 也很自信、且读出的正是 ABBYY 那串字母时，说明页面上印的
    # 本来就是拉丁字母（专名、德文、拉丁文），不能拿希伯来读数去换。
    eng, ce = ocr(png, 'eng')
    Path(png).unlink(missing_ok=True)
    a = re.sub(r'[^A-Za-z]', '', eng).lower()
    b = re.sub(r'[^A-Za-z]', '', garbage).lower()
    if ce >= 80 and a and SequenceMatcher(None, a, b).ratio() >= 0.6:
        return None
    clean = lambda x: re.sub(r'[\t\r\n]+', ' ', x).strip()
    return (job['vol'], job['scan_page'], job['before'], garbage, job['after'],
            script, clean(reading), round(conf))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help='只跑这段扫描页，如 400-420')
    ap.add_argument('--junk', action='store_true',
                    help='只跑带 ^ > < | ~ 的那一档，补主跑漏掉的')
    a = ap.parse_args()
    pr = tuple(int(x) for x in a.pages.split('-')) if a.pages else None
    main(pr, a.junk)
