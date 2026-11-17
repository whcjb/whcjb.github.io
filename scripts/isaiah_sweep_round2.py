"""以赛亚书：第 8 章实读（2026-11-17）带出的几类全书清理。幂等，可重跑。
  1 开引号被星号夹住  *'* X → 'X
  2 希腊 ἐν 被读成 lv/iv
  3 经文出处冒号两侧空格  10 : 8 → 10: 8（全书主流）
  4 希伯来词排成斜体  *ארץ* → ארץ（原书希伯来从不斜体）
  5 斜体经文里整段 (or X) 没分开  *A (or B) C* → *A* (or *B*) *C*（原书 or 正体、异读斜体；8:1、8:5 看图）
  6 德文变音丢失（逐词核过上下文）
"""
import re, glob, sys
UMLAUT = [('(fur unseren Geschmack', '(für unseren Geschmack'), ('aller Gotter)', 'aller Götter)'),
          ('wollt ihrnicht horen?', 'wollt ihr nicht hören?'), (') Furst, with still less', ') Fürst, with still less'),
          ('Michaelis and Doderlein,', 'Michaelis and Döderlein,'), ('(wurde selteii)', '(wurde selten)')]
def or_in_italic(line):
    segs = line.split('*')
    for i in range(1, len(segs), 2):
        s = segs[i]
        if '(or ' not in s:
            continue
        s2 = re.sub(r' ?\(or ([^*()]+)\) ?', lambda m: f'* (or *{m.group(1)}*) *', s)
        segs[i] = s2
    out = '*'.join(segs)
    out = re.sub(r'(?<![*])\*\*(?![*])', '', out)          # 段首/段尾产生的空斜体
    out = re.sub(r'\* \(or', ' (or', out) if False else out
    return out
def fix(body, c):
    body, n = re.subn(r"(?<=[\s(—])\*(['\"])\* ?(?=[A-Za-z])", r'\1', body); c[0] += n
    body, n = re.subn(r"(?<![A-Za-z])[li]v (?=[Ͱ-Ͽἀ-῿])", 'ἐν ', body); c[1] += n
    body, n = re.subn(r'(\d) : (\d)', r'\1: \2', body); c[2] += n
    body, n = re.subn(r'\*([֐-׿][֐-׿ ]*[֐-׿]|[֐-׿])\*', r'\1', body); c[3] += n
    new = '\n'.join(or_in_italic(l) for l in body.split('\n')); c[4] += sum(a != b for a, b in zip(body.split('\n'), new.split('\n'))); body = new
    for a, b in UMLAUT:
        if a in body: body = body.replace(a, b); c[5] += 1
    return body
if __name__ == '__main__':
    apply = '--apply' in sys.argv; c = [0]*6
    for p in sorted(glob.glob('alexander/isaiah/[0-9]*.md')):
        t = open(p).read(); fm, body = t.split('\n---\n', 1)
        nb = fix(body, c)
        if apply and nb != body: open(p, 'w').write(fm + '\n---\n' + nb)
    print('引号', c[0], 'ἐν', c[1], '冒号', c[2], '斜体希伯来', c[3], '(or)行', c[4], '变音', c[5])
