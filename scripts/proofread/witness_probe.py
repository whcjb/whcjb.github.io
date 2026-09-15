"""校对用：拿另外几份 IA 扫描件给一处改正投票。

从 stdin 读 `旧串<TAB>新串`，每行打印两边各有几份证人读得出来。
数字的含义：**新的比旧的多**就说明多数证人站在改正这边。

    python3 scripts/proofread/witness_probe.py <<'EOF'
    might be spared in manycases	might be spared in many cases
    EOF

标点与变音符这一档它判不了（归一化会抹掉），那种要翻页面影像，
用同目录的 crop_line.py。
"""
import re, sys, unicodedata
from pathlib import Path
SRC = Path('alexander_raw/isaiah/src')
WIT = {p.name: re.sub(r'\s+', ' ', p.read_text(encoding='utf-8', errors='replace'))
       for p in sorted(SRC.glob('*.txt'))}

def norm(s):
    s = unicodedata.normalize('NFKD', s)
    s = re.sub(r'[*_\\]', '', s)
    s = re.sub(r'[^A-Za-z0-9]+', ' ', s).strip().lower()
    return s

def probe(phrase):
    n = norm(phrase)
    pat = re.compile(r'\s*'.join(re.escape(w) for w in n.split()), re.I)
    hits = []
    for name, t in WIT.items():
        tn = re.sub(r'[^A-Za-z0-9]+', ' ', unicodedata.normalize('NFKD', t))
        if pat.search(tn):
            hits.append(name.split('.')[0][:22])
    return hits

if __name__ == '__main__':
    for line in sys.stdin:
        line = line.rstrip('\n')
        if not line.strip() or line.startswith('#'):
            continue
        a, b = line.split('\t')
        ha, hb = probe(a), probe(b)
        print(f'{len(ha)}旧/{len(hb)}新  {a[:46]!r} -> {b[:46]!r}  新证人={hb[:4]}')
