#!/usr/bin/env python3
"""卡里尔缺部 OCR：抽章实读后的全书同类清理（old-book-ocr §4.5 第 4 步）。排在 caryl_ocr_manual.py 之后（人工改正表是照上下文纠错之后的文字记的，清理若排在前面会先改掉原串的一部分，改正表就对不上）。

    /usr/bin/python3 scripts/caryl_ocr_sweep.py              # 试跑：每条规则命中数与样例
    /usr/bin/python3 scripts/caryl_ocr_sweep.py --apply      # 落到各部 fixed/；改动记 caryl_raw/job_ocr/sweep.tsv

规则来自 2026-11-25 抽读第 9 部 31:7–8 一段（25 页，记错 235 条，平均每页约 12 处）。每条都只在纯文本上匹配，
不跨标签（旁注、页码锚点、存疑标记、经文框标签都不碰）：

  split   词中断开：相邻两截拼起来是本书 ≥ 5 次的词，且至少一截不是词，或后一截是常见后缀
          （direct ly、end lesse、out ward、unjust ly、oc asion）
  job     Job 读坏：Tob/fob/Sob/Jub/Iob/Jeb（含所有格 s）→ Job；小写 job 前面不是 a/the/his 时 → Job
  way     冠词、物主代词、形容词之后的 may/nay/var/mav → way（「the may」「good may」）；不碰 that/this/which may（情态动词）
  modal   人称代词之后的 mill/mil → will，mould → would，mas/vas → was，vere/mere → were
  saith   faith 前是人名（Job、David、God、Christ、the Lord…）或后是人名、he、the Lord → saith（长 s 读成 f）
  of      独立的 ef → of；er → or（两边都是英文词）
  tis     'Tis 开引号读错：「"Tis」「“ Tis」「“Tis」→「'Tis」
  isa     书卷缩写读坏：I/a. → Isa.，P/al. → Psal.，Plal. → Psal.
  head    漏进正文的页眉（「Chap. 31. An Exposition upon the Booke of JOB. Vers. 7.」）删掉
"""
import argparse
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_ctx as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
PARTS = ('p4', 'p6', 'p82', 'p9')
UNI = C.UNI
SUFFIX = {'ly', 'lesse', 'nesse', 'ward', 'wards', 'ing', 'ed', 'ment', 'ness', 'ful', 'full', 'ous'}
NAMES = r'(?:Job|David|God|Christ|Moses|Paul|Peter|Solomon|Isaiah|Jeremiah|Elihu|Eliphaz|Bildad|Zophar|the Lord|the Prophet|the Apostle|he|she|they|hee)'
DETS = r'(?:the|a|good|his|my|their|our|your|her|its|narrow|right|wrong|same|thy|thine|mine|old|new|plaine|straight|evill|crooked)'


def rules():
    R = []
    # job
    R.append(('job', re.compile(r'\b(?:Tob|fob|Fob|Sob|Jub|Iob|Jeb|Ieb|lob|Iub)(\'?s?)\b'), lambda m: 'Job' + m.group(1)))
    R.append(('job', re.compile(r'(?<!\ba )(?<!\bthe )(?<!\bhis )\bjob(\'?s?)\b'), lambda m: 'Job' + m.group(1)))
    # way
    R.append(('way', re.compile(rf'\b({DETS}) (?:may|nay|var|mav)\b(?! be\b)'), lambda m: m.group(1) + ' way'))
    R.append(('way', re.compile(r'\b(out of (?:the|that|his|their|my) )(?:may|nay|man|var)\b'), lambda m: m.group(1) + 'way'))
    # modal
    R.append(('modal', re.compile(r'\b(I|we|wee|he|hee|they|ye|yee|you|thou|she|it|who|which) (mill|mil|mould|mas|vas|vere|mere)\b'),
              lambda m: m.group(1) + ' ' + {'mill': 'will', 'mil': 'will', 'mould': 'would', 'mas': 'was', 'vas': 'was',
                                            'vere': 'were', 'mere': 'were'}[m.group(2)]))
    # saith
    R.append(('saith', re.compile(rf'\b({NAMES}) faith\b'), lambda m: m.group(1) + ' saith'))
    R.append(('saith', re.compile(rf'([,;(] ?)faith (?={NAMES}\b)'), lambda m: m.group(1) + 'saith '))
    # of / or
    R.append(('of', re.compile(r'(?<=[a-z] )ef(?= [a-z])'), lambda m: 'of'))
    R.append(('of', re.compile(r'(?<=[a-z] )er(?= [a-z])'), lambda m: 'or'))
    # 'Tis
    R.append(('tis', re.compile(r'["“”]\s?Tis\b'), lambda m: "'Tis"))
    # 书卷缩写
    R.append(('isa', re.compile(r'\bI/a\.'), lambda m: 'Isa.'))
    R.append(('isa', re.compile(r'\bP[/l]al\.'), lambda m: 'Psal.'))
    # 漏进正文的页眉
    R.append(('head', re.compile(r'\bCha[pn][.,-]?\s?\d{1,2}\.?\s+An Ex\w*\s+u\w*\s+\w+\s+Boo?[sk]\w*\s+\S{1,3}\s?\S{0,3}\s+V\w{2,5}[.,]?\s?\d{0,2}\.?'),
              lambda m: ''))
    return R


RULES = rules()
RE_SPLIT = re.compile(r'\b([A-Za-z]{1,10}) ([a-z]{1,7})\b')


def split_fix(m):
    a, b = m.group(1), m.group(2)
    w = (a + b).lower()
    if UNI.get(w, 0) < 5:
        return None
    if UNI.get(a.lower(), 0) >= 20 and UNI.get(b, 0) >= 20 and b not in SUFFIX:
        return None                          # 两截都是常见词（in deed、a way…）：不合
    if b in SUFFIX or not UNI.get(a.lower(), 0) or not UNI.get(b, 0):
        return a + b
    return None


def sweep_text(pt, log, where):
    """纯文本段落上跑规则；返回新文本。"""
    def sub_split(m):
        r = split_fix(m)
        if r:
            log.append(('split', where, m.group(0), r))
            return r
        return m.group(0)
    pt = RE_SPLIT.sub(sub_split, pt)
    for name, rx, fn in RULES:
        def rep(m, name=name, fn=fn):
            new = fn(m)
            if new != m.group(0):
                log.append((name, where, m.group(0), new))
            return new
        pt = rx.sub(rep, pt)
    return pt


def sweep_md(md, log, where):
    """只改标签之间的纯文本片段（不跨标签），旁注 span 整个跳过。"""
    out, last = [], 0
    for m in re.finditer(r'<span class="cy-margin">.*?</span>|<[^>]+>|\{:[^}]*\}', md, re.S):
        out.append(sweep_text(md[last:m.start()], log, where))
        out.append(m.group(0))
        last = m.end()
    out.append(sweep_text(md[last:], log, where))
    return re.sub(r' {2,}', ' ', ''.join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', default='')
    a = ap.parse_args()
    log, outs = [], {}
    for p in PARTS:
        for f in sorted((BASE / p / 'fixed').glob('*.md')):
            outs[f] = sweep_md(f.read_text(encoding='utf-8'), log, f'{p}/{f.stem}')
    c = collections.Counter(x[0] for x in log)
    print('全书同类清理：' + '，'.join(f'{k} {v}' for k, v in c.most_common()), file=sys.stderr)
    for k in c:
        xs = [x for x in log if x[0] == k]
        step = max(1, len(xs) // 12)
        print(f'  [{k}] ' + ' | '.join(f'{x[2]}→{x[3]}' for x in xs[::step][:12]), file=sys.stderr)
    if a.show:
        for x in log:
            if x[0] == a.show:
                print('\t'.join(x))
    if a.apply:
        for f, md in outs.items():
            f.write_text(md, encoding='utf-8')
        (BASE / 'sweep.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')


if __name__ == '__main__':
    main()
