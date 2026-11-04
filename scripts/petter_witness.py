#!/usr/bin/env python3
"""佩特《马可福音注释》(1661, EEBO-TCP A54583) 缺字清单。gaps 一步照搬 dickson_witness.py。

    python3 scripts/petter_witness.py gaps     # en_chapters → gap_sites.json（每组缺字 + 上下文）

影像证人尚未找（2026-11-04）：判读要原书影像，找到后照 dickson_witness 补 build / match / sheets。
**落盘规则（memory feedback_no_guess_inference_needs_approval）：只有看图读出的才落；
推断写 P:xx，列清单待用户同意。**
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import petter_common as rc  # noqa: E402

RAW = rc.RAW
NCTX = 8


def gaps():
    sites = []
    main_total = 0
    od = rc.order()
    prev_tail = []
    facs = None
    pnum = None
    for slug in od['order']:
        if True:
            md = rc.read_src(slug)
            margins = [(m.start(), m.end()) for m in re.finditer(r'<span class="pt-margin"[^>]*>.*?</span>', md, re.S)]
            blank = md
            for a, b in margins:
                blank = blank[:a] + ' ' * (b - a) + blank[b:]
            pbs = [(m.start(), int(m.group(1))) for m in re.finditer(r'<span class="pt-pb"[^>]*data-facs="(\d+)"', md)]
            pns = [(m.start(), m.group(1)) for m in re.finditer(r'<span class="pt-pb"[^>]*data-p="(\d+)"', md)]
            for a, b, s, isnote in rc.gap_groups(md):
                f = next((x for p, x in reversed(pbs) if p < a), facs)
                pn = next((x for p, x in reversed(pns) if p < a), pnum)
                extra = {}
                if isnote:
                    na, nb = next((x, y) for x, y in margins if x <= a < y)
                    left = rc.flat_words(md[na:a])
                    right = rc.flat_words(md[b:nb])
                    stream = 'note'
                    # 旁注挂在正文的哪一处：正文上下文，旁注自己定位不到时用它找行
                    extra = {'mleft': (prev_tail + rc.flat_words(blank[:na]))[-NCTX:],
                             'mright': rc.flat_words(blank[nb:])[:NCTX]}
                else:
                    left = prev_tail + rc.flat_words(blank[:a])
                    right = rc.flat_words(blank[b:])
                    stream = 'main'
                sites.append({'gid': len(sites), 'slug': slug, 'stream': stream,
                              'tcp': s, 'left': left[-NCTX:], 'right': right[:NCTX], 'facs': f, 'page': pn,
                              'i': main_total + len(rc.flat_words(blank[:a])), **extra})
            if pbs:
                facs = pbs[-1][1]
            if pns:
                pnum = pns[-1][1]
            w = rc.flat_words(blank)
            prev_tail = w[-NCTX:]
            main_total += len(w)
    (RAW / 'gap_sites.json').write_text(json.dumps(sites, ensure_ascii=False, indent=0), encoding='utf-8')
    (RAW / 'main_words.json').write_text(json.dumps(main_total), encoding='utf-8')
    c = collections.Counter(s['stream'] for s in sites)
    print(f'缺字组 {len(sites)}  {dict(c)}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['gaps'])
    a = ap.parse_args()
    if a.cmd == 'gaps':
        gaps()


if __name__ == '__main__':
    main()
