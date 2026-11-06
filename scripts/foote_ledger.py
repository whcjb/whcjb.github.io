#!/usr/bin/env python3
"""福特《路加福音讲义》OCR 残字分账（skill：每轮报分账表，不要只报一个非词率）。

    python3 scripts/foote_ledger.py            # 读 foote_raw/luke/en_chapters/

分类（互斥，按顺序判）：
  verified   已核实原样：两个证人（第 3 版、tesseract）任一同位一致（confirm）的 token
  foreign    外文与活字残渣：token 含非 ASCII 字母，或两侧紧邻非 ASCII 字母的 token（希腊引文一片）
  fragment   两字母以内的碎片
  note       脚注区（注文本身满是出处缩写）里的非词
  pending    正文待判
"""
import csv
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from alexander_lexicon import build, is_word  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'foote_raw' / 'luke' / 'en_chapters'
ADJ = [ROOT / 'logs' / 'foote_adjudicate.tsv', ROOT / 'logs' / 'foote_adjudicate_tess.tsv']
TOK = re.compile(r"\S+")


def main():
    lex = build()
    from repair_alexander_ocr import foote_kjv_words
    lex |= foote_kjv_words()
    verified = set()
    for adj in ADJ:
        if adj.exists():
            for r in csv.DictReader(open(adj, encoding='utf-8'), delimiter='\t'):
                if r['kind'] == 'confirm':
                    verified.add((r['lecture'], r['from'].lower()))
    c = Counter()
    for p in sorted(SRC.glob('*.md')):
        text = re.sub(r'<!--.*?-->', ' ', p.read_text(encoding='utf-8'))
        body, _, notes = text.partition('\n---\n')
        for zone, part in (('body', body), ('note', notes)):
            raw = TOK.findall(part)
            for i, rt in enumerate(raw):
                w = rt.strip('.,;:!?()[]"\'“”‘’*\\—-^•«»')
                if not re.search(r'[A-Za-z]', w) or len(re.sub(r'[^A-Za-z]', '', w)) < 1:
                    continue
                # 复合词（fellow-creatures、Sabbath-day）拆开逐段判；钦定本路加词形算真词
                if all(is_word(x, lex) for x in re.split(r'[-–]', w) if x):
                    continue
                c['total'] += 1
                ctx = ' '.join(raw[max(0, i - 1):i + 2])
                if (p.stem, w.lower()) in verified:
                    c['verified'] += 1
                elif re.search(r'[^\x00-\x7f]', ctx.replace('', '').replace('—', '').replace('’', '').replace('‘', '')):
                    c['foreign'] += 1
                elif len(re.sub(r'[^A-Za-z]', '', w)) <= 2:
                    c['fragment'] += 1
                elif zone == 'note':
                    c['note'] += 1
                else:
                    c['pending'] += 1
    for k in ('total', 'verified', 'foreign', 'fragment', 'note', 'pending'):
        print(f'{k:9s} {c[k]:6d}')


if __name__ == '__main__':
    main()
