#!/usr/bin/env python3
"""证人判不动的残留串，回到 1864 页面影像上逐处判读。

分工：
  `psalms_residue_witness.py`  1850 三卷本按位置读，**免费**，先跑，收掉大头
  本脚本                        证人给不出／字母对不上／两版排印可能本来就不同
                                的那批，裁出该行的影像再判

三步，与全书那一轮同一套口径：
  1 `--build`  按 `<!-- PAGE n -->` 定位书页（pdf_index = 书页 + 3），
               在 PDF 文本层里用上下文锚确认落在对的一页上，裁出该行及上下一行
  2 `--round N` 把裁图连同这一处的 OCR 残串交给模型，只问「影像上印的是什么」。
               跑两遍，两遍**独立**（互相看不见），一致才算过闸
  3 `--apply`  过闸的写进 manual_fixes.tsv 并落回正文

闸有三道，任何一道不过就留在账上不动：
  两遍一致    读数不一致 → 不动
  标点级      读数与残串剥掉标点后必须逐字相同。这批残留的毛病都在标点上，
              放开这一条就等于让模型重写正文（它很乐意顺手"改通顺"）
  尾部归一    正文里这串后面本来就跟着标点的，读数尾巴上的标点要剥掉，
              否则写出 `xliii. 4.,` 这种双标点——静默，事后只能靠眼睛捡

用法：
    python3 scripts/psalms_residue_crop.py --build
    python3 scripts/psalms_residue_crop.py --round 1
    python3 scripts/psalms_residue_crop.py --round 2
    python3 scripts/psalms_residue_crop.py --apply
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_alexander_image as A
import alexander_lexicon as L
from psalms_residue_witness import TAIL, letters, read_spans

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
OFFSET = 3
PRINTED = ROOT / 'alexander_raw/psalms/printed_as_is.txt'
FIXES = ROOT / 'alexander_raw/psalms/manual_fixes.tsv'
META = ROOT / 'logs/alexander_psalms_residue_crop.json'
CROPS = ROOT / 'logs/residue_crops'
PAGE_RE = re.compile(r'<!-- PAGE (\d+) -->')

SYSTEM = (
    'You are a careful palaeographer proof-reading a 19th-century printed book '
    '(Alexander, "The Psalms Translated and Explained", 1864).\n'
    'You get a tight crop of a few printed lines, and ONE spot where the OCR is '
    'suspected wrong. Report what the IMAGE actually shows at that spot.\n'
    'Rules:\n'
    '1. Output exactly one line:  reading=<what is printed>\n'
    '2. Reproduce the punctuation EXACTLY — commas, periods, quotation marks, '
    'dashes and hyphens are the whole point of this check.\n'
    '3. If the OCR string is in fact correct as printed, output  reading=OK\n'
    '4. If you cannot make it out or cannot find the spot, output  reading=?\n'
    '   Never guess, never infer from context.\n'
    '5. Report only the word/phrase at that spot, nothing else.\n'
    '6. Keep 19th-century spelling (shews, connexion) — do NOT modernise.'
)


# ── 1 裁图 ────────────────────────────────────────────────────────────────
def build():
    import fitz
    vocab = L.build()
    asis = set()
    if PRINTED.exists():
        for line in PRINTED.open(encoding='utf-8'):
            asis.update(line.split('#')[0].split())
    items = read_spans(vocab, asis)
    doc = fitz.open(PDF)
    CROPS.mkdir(parents=True, exist_ok=True)
    meta, miss = [], 0
    for n, it in enumerate(items):
        raw = it['raw']
        pages = [(m.start(), int(m.group(1))) for m in PAGE_RE.finditer(raw)]
        page = next((pg for pos, pg in reversed(pages) if pos < it['a']), None)
        if page is None:
            miss += 1
            continue
        before = re.findall(r'[A-Za-z]{3,}', raw[max(0, it['a'] - 90):it['a']])
        anchor = ' '.join(before[-3:])
        out = CROPS / f'r{n:03d}.png'
        idx = crop(doc, page, anchor, it['span'], out)
        if idx is None:
            miss += 1
            continue
        ctx = re.sub(r'\s+', ' ', raw[max(0, it['a'] - 60):it['b'] + 60])
        meta.append(dict(n=n, file=out.name, sec=it['sec'], span=it['span'],
                         ctx=ctx, page=page, pdf=idx,
                         nxt=raw[it['b']] if it['b'] < len(raw) else '',
                         prev=raw[max(0, it['a'] - 4):it['a']].replace('*', '')))
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding='utf-8')
    print(f'裁出 {len(meta)} 处，定位失败 {miss} 处 → {CROPS}')


def crop(doc, page_no, anchor, span, out, dpi=400):
    """在候选页里找到这一行，裁出它及上下各一行。

    先按残串本身搜：PDF 文本层与 en_chapters 同出一份 ABBYY OCR，同一个残串
    在那边一模一样，命中最准；搜不到（被跨行拆开、或后续修复改过）再退回上下文锚。
    """
    import fitz
    for cand in (page_no, page_no + 1, page_no - 1):
        idx = cand + OFFSET
        if not (0 <= idx < doc.page_count):
            continue
        p = doc[idx]
        rects = (p.search_for(span) or p.search_for(anchor)
                 or (p.search_for(anchor.split()[-1]) if anchor else None))
        if not rects:
            continue
        r = rects[0]
        clip = fitz.Rect(0, max(0, r.y0 - 26), p.rect.x1, min(p.rect.y1, r.y1 + 26))
        p.get_pixmap(dpi=dpi, clip=clip).save(out)
        return idx
    return None


# ── 2 判读 ────────────────────────────────────────────────────────────────
def ask(png, it):
    text = (f'The OCR text reads «{it["span"]}» here:\n…{it["ctx"]}…\n\n'
            f'What does the image actually show in place of «{it["span"]}»? '
            f'Reproduce the punctuation exactly.')
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': text}]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config',
           '--disallowedTools', '*', '--input-format', 'stream-json',
           '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True,
                       text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f'rc={r.returncode} {r.stderr[:160]}')
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:160])
            m = re.search(r'reading\s*=\s*(.+)', str(o.get('result') or ''))
            return (m.group(1).strip().strip('«»「」') if m else '?'), \
                float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result')


def run(rnd):
    meta = json.loads(META.read_text(encoding='utf-8'))
    out = ROOT / f'logs/alexander_psalms_residue_round{rnd}.tsv'
    done = {l.split('\t')[0] for l in out.open(encoding='utf-8')} if out.exists() else set()
    total, fails = 0.0, 0
    with out.open('a', encoding='utf-8') as fh:
        for k, it in enumerate(meta, 1):
            if str(it['n']) in done:
                continue
            try:
                res, cost = ask((CROPS / it['file']).read_bytes(), it)
                fails = 0
            except Exception as e:                        # noqa: BLE001
                print(f'  #{it["n"]} 失败 {e}', flush=True)
                fails += 1
                if fails >= 5:
                    sys.exit('✗ 连续 5 次失败，中止（已判读的已落盘，重跑续上）')
                time.sleep(4)
                continue
            total += cost
            fh.write(f'{it["n"]}\t{it["sec"]}\t{it["span"]}\t{res}\n')
            fh.flush()
            if k % 20 == 0:
                print(f'[{k}/{len(meta)}] ${total:.2f}', flush=True)
    print(f'完成 ${total:.2f} → {out}')


# ── 3 落盘 ────────────────────────────────────────────────────────────────
def load_round(rnd):
    p = ROOT / f'logs/alexander_psalms_residue_round{rnd}.tsv'
    d = {}
    if p.exists():
        for line in p.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            if len(f) >= 4:
                d[f[0]] = f[3]
    return d


def normalise(read, it):
    """把读数的两端与正文对齐。

    右边：正文里这串后面本来就跟着标点的，读数尾巴上的标点要剥掉，
          否则写出 `xliii. 4.,` 这种双标点。
    左边：正文里这串前面已经有的破折号/括号，读数里再带一个就重了
          （`*(^As)` 读成 `(As`，照抄成 `((As`）。
    """
    if not read or read == 'OK':
        return read
    if it['nxt'] in ',.;:!?)':
        read = read.rstrip(TAIL)
    if read[:1] in ('—', '–', '-', '(') and read[0] in it['prev']:
        read = read[1:].lstrip()
    return read


def apply_gates(apply=False):
    meta = json.loads(META.read_text(encoding='utf-8'))
    r1, r2 = load_round(1), load_round(2)
    stat, add, hold = Counter(), [], []
    for it in meta:
        k = str(it['n'])
        a, b = r1.get(k, ''), r2.get(k, '')
        if not a or not b or a == '?' or b == '?':
            stat['读不出'] += 1
            continue
        # 两边界归一要**先做再比**：一遍读 `for`、二遍读 `—for`，说的是同一件事
        # ——那个破折号我们已经印在斜体外面了。不先归一，这类全被判成「两遍不一致」。
        a, b = normalise(a, it), normalise(b, it)
        if a != b:
            stat['两遍不一致'] += 1
            hold.append((it, a, b, '两遍不一致'))
            continue
        read = a
        if read == 'OK' or read == it['span']:
            stat['印面如此'] += 1
            continue
        if letters(read) != letters(it['span']):
            stat['不是标点级'] += 1
            hold.append((it, a, b, '读数动到了字母，不采信'))
            continue
        stat['可改'] += 1
        add.append((it, read))
    print('，'.join(f'{k} {v}' for k, v in stat.most_common()))
    for it, a, b, why in hold:
        print(f'  留账 [{it["sec"]}] {it["span"]!r} 一遍={a!r} 二遍={b!r}  {why}')
    if not apply:
        for it, read in add[:20]:
            print(f'  [{it["sec"]}] {it["span"]!r} → {read!r}')
        return
    n = 0
    with FIXES.open('a', encoding='utf-8') as fh:
        for it, read in add:
            p = SRC / f'{it["sec"]}.md'
            t = p.read_text(encoding='utf-8')
            old, new = it['span'], read
            if t.count(old) != 1:
                i = t.find(it['ctx'][:20].strip())
                head = it['ctx'][:20]
                if t.count(head + old) != 1:
                    print(f'  跳过 [{it["sec"]}] {old!r} 定位不唯一')
                    continue
                old, new = head + old, head + read
            fh.write(f'{it["sec"]}\t{old}\t{new}\timage1864: 裁图两遍一致，标点级\n')
            p.write_text(t.replace(old, new, 1), encoding='utf-8')
            n += 1
    print(f'落盘 {n} 处')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--round', type=int, choices=(1, 2))
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if a.build:
        build()
    elif a.round:
        run(a.round)
    elif a.apply or a.dry_run:
        apply_gates(apply=a.apply)
    else:
        ap.error('要 --build / --round N / --apply')


if __name__ == '__main__':
    main()
