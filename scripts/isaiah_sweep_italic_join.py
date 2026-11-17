"""以赛亚书：经文斜体在 ; : , — ? ! 处被切成两段（`fadeth*; *the world`）→ 合回一段。
2026-11-17 第 24 章实读发现，全书 8 处抽样看图（37、26、15、22、51、29、66、14 章）原书斜体都跨标点连续。
只合两侧斜体段都 ≥2 词的（单词对举 *et*—*et*、*both*—*and* 不动）。幂等：python3 scripts/isaiah_sweep_italic_join.py [--apply]"""
import re, glob, sys
def join_line(line, log):
    segs = line.split('*')
    if len(segs) < 3:
        return line
    out = [segs[0]]
    i = 1
    while i < len(segs):
        # segs[i] 斜体，segs[i+1] 斜体间正文，segs[i+2] 下一段斜体
        if i + 2 < len(segs) and re.fullmatch(r'([;:,]|—|\?|!) ?', segs[i + 1]) \
                and len(segs[i].split()) >= 2 and len(segs[i + 2].split()) >= 2 \
                and re.search(r'[a-z]$', segs[i]) and re.match(r'[a-z]', segs[i + 2]):
            log.append(segs[i][-25:] + '|' + segs[i + 1] + '|' + segs[i + 2][:25])
            segs[i + 2] = segs[i] + segs[i + 1] + segs[i + 2]
            i += 2
            continue
        out.append(segs[i])
        if i + 1 < len(segs):
            out.append(segs[i + 1])
        i += 2
    return '*'.join(out)
if __name__ == '__main__':
    apply = '--apply' in sys.argv; log = []
    for p in sorted(glob.glob('alexander/isaiah/[0-9]*.md')):
        t = open(p).read(); fm, body = t.split('\n---\n', 1)
        nb = '\n'.join(join_line(l, log) for l in body.split('\n'))
        if apply and nb != body: open(p, 'w').write(fm + '\n---\n' + nb)
    print('合并', len(log))
    import random; random.seed(2)
    for x in random.sample(log, min(20, len(log))): print('  ', x)
