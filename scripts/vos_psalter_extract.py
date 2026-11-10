#!/usr/bin/env python3
"""Vos, "Eschatology of the Psalter" (PTR 18, 1920) —— 从 Hildebrandt 录入本 PDF 抽结构。

底本：vos_raw/psalter/src/bel.pdf（biblicalelearning.org，逐页逐行照原刊排）
产物：vos_raw/psalter/extract.json
  paras: [{page, text}]   正文段落，*斜体*、[^n] 注号已标好，行末连字符已按规则处理
  notes: {n: text}        脚注（跨页续行已接上）
  hyphen_log: 行末连字符的处理记录（joined / kept / ambiguous）

版式：正文 13pt、脚注 11pt、正文注号 8.5pt 上标、脚注编号 7pt；段首缩进 x≈144，其余行 x≈108；
页眉（ESCHATOLOGY OF THE PSALTER / THE PRINCETON THEOLOGICAL REVIEW / 页码）在 y<50。
"""
import json
import re
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'vos_raw' / 'psalter'
SRC = RAW / 'src' / 'bel.pdf'

HEBREW_FONT = 'HebrewTh'


def words_dict():
    p = Path('/usr/share/dict/words')
    return {w.strip().lower() for w in p.read_text().split()} if p.exists() else set()


# 行末断在复合词处、字典判不了的，按本文他处写法定（pre-exilic、pre-prophetic 均带连字符）
HYPHEN_KEEP = {'pre-existence', 'throne-ascension'}


def in_dic(w, dic):
    w = w.lower()
    return any(x in dic for x in (w, w[:-1] if w.endswith('s') else w, w[:-2] if w.endswith('ed') else w,
                                  w[:-1] if w.endswith('d') else w, w[:-3] if w.endswith('ing') else w,
                                  w[:-2] if w.endswith('ly') else w, w[:-2] if w.endswith('es') else w))


def span_md(sp):
    t = sp['text']
    if 'Italic' in sp['font'] and t.strip():
        lead = t[:len(t) - len(t.lstrip())]
        trail = t[len(t.rstrip()):]
        return f'{lead}*{t.strip()}*{trail}'
    if HEBREW_FONT in sp['font']:
        return f'⟪heb:{t}⟫'
    return t


def main():
    doc = fitz.open(SRC)
    body_lines, note_lines = [], []          # (page, x, text, is_note_start, note_no)
    for pno, page in enumerate(doc, start=1):
        for b in page.get_text('dict')['blocks']:
            for l in b.get('lines', []):
                spans = [s for s in l['spans']]
                txt = ''.join(s['text'] for s in spans)
                if not txt.strip():
                    continue
                y = l['bbox'][1]
                if y < 50:                    # 页眉
                    continue
                if pno == 1 and y < 200:      # 刊名、Public Domain、篇名、作者
                    continue
                main_size = max((s['size'] for s in spans if s['text'].strip() and HEBREW_FONT not in s['font']), default=0)
                if re.fullmatch(r'\s*\d+\s*', txt) and main_size >= 12 and y > 640:
                    continue                  # 页脚页码（首页）
                if 'This material is cited' in txt or 'Please report any errors' in txt \
                        or 'thildebrandt' in txt:
                    continue
                # 录入本把注 5 跨到第 6 页的两行误排成 13pt，按原刊归回脚注
                if pno == 6 and txt.lstrip().startswith(('De Origine Carminum', '26 ff')):
                    main_size = 11
                if main_size <= 11.5:         # 脚注区
                    first = spans[0]
                    m_no = None
                    if first['size'] <= 7.5 and re.fullmatch(r'\s*\d+\s*', first['text']):
                        m_no = int(first['text'])
                        spans = spans[1:]
                    md = ''.join(span_md(s) for s in spans)
                    note_lines.append((pno, md, m_no))
                else:
                    parts = []
                    for s in spans:
                        if s['size'] <= 9 and re.fullmatch(r'\s*\d+\s*', s['text']):
                            parts.append(f'[^{int(s["text"])}]')
                        else:
                            parts.append(span_md(s))
                    body_lines.append((pno, l['bbox'][0], ''.join(parts)))

    dic = words_dict()
    hyphen_log = []
    all_text = ' '.join(t for _, _, t in body_lines) + ' ' + ' '.join(t for _, t, _ in note_lines)

    def join_lines(lines, start_pg=None):
        """lines: [(page, text)] → 一段文字；行末连字符：并成字典词则接，否则保留连字符。
        start_pg 给定时标原刊页码：换页处插 ⟦pN⟧（断词跨页则落在该词之后）。"""
        out = ''
        prev_pg = start_pg
        for i, (pg, t) in enumerate(lines):
            t = t.strip()
            mark = start_pg is not None and pg != prev_pg
            prev_pg = pg
            if not out:
                out = (f'⟦p{pg}⟧' if mark else '') + t
                continue
            if mark:
                base = len(out)
                if re.search(r'[A-Za-zÀ-ÿ]-$', out):
                    w = re.match(r'[*]?[A-Za-zÀ-ÿ]+[*]?', t)
                    cut = w.end() if w else 0
                    t = t[:cut] + f'⟦p{pg}⟧' + t[cut:]
                else:
                    t = f'⟦p{pg}⟧' + t
            m = re.search(r'([A-Za-zÀ-ÿ]+)-$', out)
            if m:
                head = m.group(1)
                tail = re.match(r'[*]?([A-Za-zÀ-ÿ]+)', t)
                tail_w = tail.group(1) if tail else ''
                joined = (head + tail_w).lower()
                hyph = f'{head}-{tail_w}'
                if re.search(rf'\b{re.escape(hyph)}\b', all_text.replace(f'{head}- ', '§')):
                    out = out + t; how = 'kept(self-evidence)'
                elif hyph in HYPHEN_KEEP:
                    out = out + t; how = 'kept(list)'
                elif in_dic(joined, dic):
                    out = out[:-1] + t; how = 'joined'
                elif len(head) >= 4 and head.lower() in dic and len(tail_w) >= 4 and in_dic(tail_w, dic):
                    out = out + t; how = 'kept(compound)'     # world-tempest, Psalm-singing, council-chamber
                elif head[:1].isupper() and tail_w[:1].isupper():
                    out = out + t; how = 'kept(caps)'
                else:
                    out = out[:-1] + t; how = 'joined(ambiguous)'
                hyphen_log.append({'page': pg, 'head': head, 'tail': tail_w, 'how': how})
            elif out.endswith('—'):
                out = out + t
            else:
                out = out + ' ' + t
        return re.sub(r'\s+', ' ', out)

    # 正文分段：x≈144 为段首
    paras, cur = [], []
    for pg, x, t in body_lines:
        if x > 130 and cur:
            paras.append(cur); cur = []
        cur.append((pg, t))
    if cur:
        paras.append(cur)
    paras_out, last_pg = [], 0
    for p in paras:
        paras_out.append({'page': p[0][0], 'text': join_lines(p, start_pg=last_pg)})
        last_pg = p[-1][0]

    # 脚注：带编号的行起新注，否则接到上一条（跨页续注）
    notes, order = {}, []
    cur_no = None
    buf = {}
    for pg, md, no in note_lines:
        if no is not None:
            cur_no = no
            order.append(no)
            buf[no] = [(pg, md)]
        elif cur_no is not None:
            buf[cur_no].append((pg, md))
    for no in order:
        notes[no] = join_lines(buf[no])

    out = {'source': 'bel.pdf (Hildebrandt transcription of PTR 18:1-43)',
           'paras': paras_out, 'notes': notes, 'note_order': order, 'hyphen_log': hyphen_log}
    (RAW / 'extract.json').write_text(json.dumps(out, ensure_ascii=False, indent=1))
    refs = re.findall(r'\[\^(\d+)\]', ' '.join(p['text'] for p in paras_out))
    print(f'paras {len(paras_out)}  notes {len(notes)}  refs {len(refs)}')
    print('note numbers in order:', order)
    print('refs in order        :', [int(r) for r in refs])
    from collections import Counter
    print(Counter(h['how'] for h in hyphen_log))


if __name__ == '__main__':
    main()
