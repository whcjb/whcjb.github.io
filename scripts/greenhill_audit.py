#!/usr/bin/env python3
"""格林希尔《以西结书释义》验收（old-book-ocr §4.1 / §4.3）。

    python3 scripts/greenhill_audit.py [基线提交]     # 默认基线 27aadbcb7c（重排本推补之前最后一个良好提交）

§4.1 逐词比对：基线 → 当前已发布正文，逐块比词；旧串全是真词、新串出现非词 = 越改越坏，列出待回退。
      「真词」= 判词典（web2 + 补充表 + 罗马数字）∪ 本书 TCP 录入本自证（同形出现 ≥2 次；录入本是人工录入，
      原书拼法以它为准）。希腊/希伯来字母 token 不判。
§4.3 规则自检：gap_review（看图读出）/ gap_approved（推补）/ tcp_fixes 每条在源文中是否命中；
      判读表有读法、源文里却找不到该缺字组的，静默失效，报警。
"""
import collections
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon as lx  # noqa: E402
import greenhill_common as gc  # noqa: E402

ROOT = gc.ROOT
OUT = ROOT / 'greenhill' / 'ezekiel'
NONLATIN = re.compile(r'[Ͱ-Ͽἀ-῿֐-׿]')
WORD = re.compile(r"[A-Za-zſ'’]+")


def plain(md):
    md = re.sub(r'\A---.*?---\n', '', md, flags=re.S)
    md = re.sub(r'<[^>]+>', ' ', md)
    return md.replace('*', '').split()


def corpus():
    """录入本自证：全部 TCP 源文的词频（缺字记号不计）。"""
    cnt = collections.Counter()
    for f in (gc.RAW / 'en_chapters').glob('*.md'):
        for t in plain(gc.read_src(f.stem)):
            for w in WORD.findall(t):
                cnt[w.lower().replace('ſ', 's').strip("'’")] += 1
    return cnt


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else '27aadbcb7c'
    lex = lx.build()
    cnt = corpus()

    def real(tok):
        if NONLATIN.search(tok) or gc.TOK.search(tok):
            return True
        ws = WORD.findall(tok)
        if not ws:
            return True                      # 数字、标点
        for w in ws:
            k = w.lower().replace('ſ', 's').strip("'’")
            if not k or cnt[k] >= 2 or lx.is_word(k, lex):
                continue
            return False
        return True

    # ── §4.1 ──
    bad, newnon, nblk = [], [], 0
    for f in sorted(OUT.glob('*.md')):
        rel = f.relative_to(ROOT).as_posix()
        try:
            old = subprocess.run(['git', 'show', f'{base}:{rel}'], cwd=ROOT, capture_output=True,
                                 text=True, check=True).stdout
        except subprocess.CalledProcessError:
            continue
        a, b = plain(old), plain(f.read_text(encoding='utf-8'))
        for op, i1, i2, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
            if op == 'equal':
                continue
            nblk += 1
            o, n = a[i1:i2], b[j1:j2]
            nn = [t for t in n if not real(t)]
            if not nn:
                continue
            if o and all(real(t) for t in o) and not any(gc.TOK.search(t) for t in o):   # 旧串含缺字记号＝本非全真词
                bad.append((f.stem, ' '.join(o), ' '.join(n)))
            else:
                newnon.append((f.stem, ' '.join(o)[:60], ' '.join(nn)))
    print(f'§4.1 基线 {base}：改动块 {nblk}；旧全真词→新出非词（须回退）{len(bad)}；新串含非词（旧串本非全真词）{len(newnon)}')
    for r in bad:
        print('  回退?', *r, sep=' | ')
    for r in newnon:
        print('  非词 ', *r, sep=' | ')

    # ── §4.3 ──
    sites = {s['gid']: s for s in json.loads((gc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))}
    present = collections.defaultdict(set)
    for f in (gc.RAW / 'en_chapters').glob('*.md'):
        md = gc.read_src(f.stem)
        for _, _, s, _ in gc.gap_groups(md):
            present[f.stem].add(s)
    dec = gc.decisions()
    dead = [g for g in dec if sites[g]['tcp'] not in present[sites[g]['slug']]]
    fixes = gc.tcp_fixes()
    pub = {f.stem: f.read_text(encoding='utf-8') for f in OUT.glob('*.md')}
    allpub = '\n'.join(pub.values())
    fix_dead = [(a, b) for a, b in fixes if a not in allpub and b not in allpub]
    left = sum(len(gc.TOK.findall(t)) for t in pub.values())
    print(f'§4.3 判读+推补 {len(dec)} 条：源文中找不到缺字组 {len(dead)}；tcp_fixes {len(fixes)} 条：原串改串都不在产物 {len(fix_dead)}；'
          f'产物剩余缺字记号 {left}')
    for g in dead:
        print('  失效', g, sites[g]['slug'], sites[g]['tcp'], dec[g])
    for a, b in fix_dead:
        print('  失效 fix', a[:50], '→', b[:50])


if __name__ == '__main__':
    main()
