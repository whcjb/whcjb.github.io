#!/usr/bin/env python3
"""脚注体检：证人里的每一条脚注，现在在哪。

三个去向——摘进了 NOTES、还卡在正文、两边都找不到。
卡在正文的那些会把句子从中间劈开，是最要紧的一类。
"""
import glob, re, os, difflib, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VLM = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'vlm')
CH = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'en_chapters')
RE_FN = re.compile(r'^\s*\[FN:[^\]]*\]\s*(.+)$')
# 认 div 的**开头**就行。写死整串属性的后果：div 上的 markdown="1" 一撤，
# 这里就一条都切不出来，体检报「118 条全卡在正文」——假警报。
SPLIT = '<div class="jh-notes"'


def words(s):
    return [w.lower() for w in re.findall(r"[A-Za-z]{2,}", s)]


def hit(w, hay):
    sm = difflib.SequenceMatcher(None, w, hay, autojunk=False)
    return sum(b.size for b in sm.get_matching_blocks()) / len(w)


def main():
    foots = {}
    for f in sorted(glob.glob(VLM + '/*.txt')):
        fs = [m.group(1).strip() for m in
              (RE_FN.match(l) for l in open(f, encoding='utf-8'))
              if m and len(m.group(1).strip()) >= 8]
        if fs:
            foots[int(os.path.basename(f)[:-4])] = fs
    files = sorted(glob.glob(CH + '/*.md'))
    body = ''.join(open(p, encoding='utf-8').read().split(SPLIT)[0] for p in files)
    notes = ''.join(x.split('</div>')[0] for p in files
                    for x in open(p, encoding='utf-8').read().split(SPLIT)[1:])
    bw, nw = words(body), words(notes)
    ok = stuck = gone = 0
    for leaf, fs in sorted(foots.items()):
        for t in fs:
            w = words(t)
            if not w:
                continue
            if hit(w, nw) >= 0.7:
                ok += 1
            elif hit(w, bw) >= 0.7:
                stuck += 1
                print(f'  ⚠️ 仍在正文  p.{leaf:<4} {t[:76]}')
            else:
                gone += 1
                print(f'  ·  两边都没  p.{leaf:<4} {t[:76]}')
    print(f'脚注 {ok + stuck + gone} 条：NOTES {ok} / 仍在正文 {stuck} / 两边都没 {gone}')
    return 1 if stuck else 0


if __name__ == '__main__':
    sys.exit(main())
