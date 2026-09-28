#!/usr/bin/env python3
"""把整页比对报出来的差异，逐条过三道闸，能自动定案的写进 manual_fixes。

`isaiah_page_proofread.py` 一页报出的是**线索**（「我们 ||| 印面」），不是结论。
一千多页会攒出一两千条，逐条人看不现实，但也不能照单全收——模型读影像会错，
引号里引的词也可能不唯一。所以按 old-book-ocr §4 的三档证据分桶：

  ① 锚：`ours` 在已发布正文里必须**恰好出现一次**。找不到＝上一轮已经修过，
     或者模型引得太松；不唯一＝落盘会改错位置，一律不动。
  ② 证人：拿另外四到五份 IA 扫描件按**归一化串**找。
     `印面` 读数能在证人里找到、而 `我们` 找不到  →  自动采纳。
     两边都找得到  →  证人自相矛盾，人看。
     两边都找不到  →  多半是拉丁/德文/希腊，证人自己也崩，人看。
  ③ 判词典：只在证人不表态时兜底——`我们` 全是真词、`印面` 冒出非词，
     那就是往坏里改，除非是外文（拉丁词尾 -is/-us/-um/-ae 之类）。

只改标点的（两边剥掉标点数字后逐字相同）放宽到「证人不反对即可」——
标点在 OCR 里最不可靠，而证人的标点同样不可靠，非要证人点头就一条也过不了。

用法：
    python3 scripts/isaiah_page_adjudicate.py                 # 只看分桶结果
    python3 scripts/isaiah_page_adjudicate.py --write         # 自动采纳的写进 manual_fixes
    python3 scripts/isaiah_page_adjudicate.py --review        # 打印要人看的那一桶
"""
import argparse
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/isaiah'
LOG = ROOT / 'logs/alexander_isaiah_page_round1.tsv'
FIXES = ROOT / 'alexander_raw/isaiah/manual_fixes.tsv'
WIT = {1: sorted(glob.glob(str(ROOT / 'alexander_raw/isaiah/src/earlier*.txt'))),
       2: sorted(glob.glob(str(ROOT / 'alexander_raw/isaiah/src/later*.txt')))}

TAG = re.compile(r'<[^<>]+>')
WORD = re.compile(r"[A-Za-zæœÆŒ][A-Za-zæœÆŒ'’-]*")
# 拉丁/德文词尾：判词典不认，但不是错
FOREIGN_TAIL = re.compile(r'(is|us|um|ae|os|em|it|ur|ibus|orum|arum|en|er)$')


def norm(s):
    return re.sub(r'[^a-z0-9]', '', s.lower())


def punct_only(a, b):
    """两边剥掉标点数字之外的字符后逐字相同 = 只动了标点。"""
    keep = lambda s: re.sub(r'[^A-Za-zæœÆŒ]', '', s).lower()
    return keep(a) == keep(b)


_wit_cache = {}


def witness(vol):
    if vol not in _wit_cache:
        _wit_cache[vol] = [(Path(f).name[:20],
                            norm(open(f, encoding='utf-8', errors='ignore').read()))
                           for f in WIT[vol]]
    return _wit_cache[vol]


def published():
    return {p.stem: p.read_text(encoding='utf-8') for p in SRC.glob('*.md')}


def nmap(s):
    """归一化串 + 到原串的下标映射。"""
    out, idx = [], []
    for i, c in enumerate(s):
        if c.isalnum():
            out.append(c.lower())
            idx.append(i)
    return ''.join(out), idx


_PUBN = {}


def anchor(pub, ours, only_ch=None):
    """按**归一化串**在全书里定位，回到原串取真正的那一段。

    模型引的是它看到的词，不带我们的 markdown 标记，空白也未必一致
    （`*buttocks and lambs*` 引成 `buttocks and lambs`），字面 `count()`
    会把大半条线索判成「锚不上」。归一化之后再映射回去，取到的是
    **正文里实际的那一段**，标记原样保留，落盘才不会把斜体弄没。

    不唯一时向两边各扩 12 个字母把上下文带进锚，最多扩三轮。
    """
    if not _PUBN:
        for ch, t in pub.items():
            _PUBN[ch] = nmap(t)
    # 先按**字面**找，并且只在这一条线索所属的那一章里找。
    # 两件事都要紧：归一化会把正在修的那个标点抹掉（`the finite verb,` 与
    # `the finite verb.` 归一化后完全一样，全书 10 处，判成「不唯一」而丢掉）；
    # 不限章则常见短语动辄三五处。日志里本来就记着章号，用上它。
    scope = {only_ch: pub[only_ch]} if (only_ch and only_ch in pub) else pub
    lit = [(ch, t.count(ours)) for ch, t in scope.items() if ours in t]
    if sum(c for _, c in lit) == 1:
        ch = lit[0][0]
        i = pub[ch].index(ours)
        return (ch, pub[ch][i:i + len(ours)]), 1
    key = nmap(ours)[0]
    if not key:
        return None, 0
    for grow in range(4):
        found = []
        for ch in (scope if grow == 0 else pub):
            n, idx = _PUBN[ch]
            start = 0
            while True:
                k = n.find(key, start)
                if k < 0:
                    break
                found.append((ch, k, k + len(key)))
                start = k + 1
        if len(found) == 1:
            ch, a, b = found[0]
            n, idx = _PUBN[ch]
            lo = idx[max(0, a - grow * 12)]
            hi = idx[min(len(idx) - 1, b - 1 + grow * 12)] + 1
            return (ch, pub[ch][lo:hi]), 1
        if not found:
            return None, 0
        # 不唯一：把锚往两边扩，用第一处的上下文当模板行不通
        # （每一处上下文不同），改成直接放弃——扩锚要拿原始线索的上下文，
        # 这里没有，交给人看
        return None, len(found)
    return None, 0


def edits(ours, img):
    """逐词对齐，取出最小改动对。"""
    import difflib
    a, b = ours.split(), img.split()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        out.append((' '.join(a[i1:i2]), ' '.join(b[j1:j2])))
    return out


def apply_edits(orig, ed):
    """把逐词改动落到正文实际那一段上；任何一处不唯一就整条放弃。"""
    cur = orig
    for old, new in ed:
        if not old:
            return None                      # 纯插入，定位不了，人看
        if cur.count(old) != 1:
            return None
        cur = cur.replace(old, new, 1)
    return cur if cur != orig else None


def read_log():
    rows = []
    if not LOG.exists():
        return rows
    for line in LOG.read_text(encoding='utf-8').splitlines():
        f = line.split('\t')
        if len(f) < 4 or not f[1].isdigit():
            continue
        vol, pg, ch = int(f[0]), int(f[1]), f[2]
        for cell in f[4:]:
            if '|||' not in cell:
                continue
            ours, img = (x.strip() for x in cell.split('|||', 1))
            if ours and img and ours != img:
                rows.append((vol, pg, ch, ours, img))
    return rows


def existing_fixes():
    if not FIXES.exists():
        return set()
    return {l.split('\t')[0] for l in FIXES.read_text(encoding='utf-8').splitlines()
            if l.strip() and not l.startswith('#')}


def judge(vol, ours, img, pub, only_ch=None):
    """返回 (桶, 理由, old, new)。"""
    got, n = anchor(pub, ours, only_ch)
    if got is None:
        why = ('正文里找不到（多半已修过，或模型引得太松）' if n == 0
               else f'正文里出现 {n} 次，落盘会改错位置')
        return 'anchor', why, None, None
    ch, orig = got
    new = apply_edits(orig, edits(ours, img))
    if new is None:
        return 'anchor', '逐词改动落不回正文那一段（引得太松或纯插入）', None, None

    wit = witness(vol)
    no, ni = norm(ours), norm(img)
    if not ni:
        return 'review', '读数归一化后为空', orig, new
    ok_img = [n for n, t in wit if ni in t]
    ok_our = [n for n, t in wit if no in t]

    if punct_only(ours, img):
        # 只动标点：证人不反对就行（证人的标点本来也不可信）
        if ok_our and not ok_img:
            return 'review', f'证人 {len(ok_our)} 份支持我们的写法', orig, new
        return 'accept', f'只动标点；证人支持读数 {len(ok_img)}/{len(wit)}', orig, new

    if ok_img and not ok_our:
        return 'accept', f'证人 {len(ok_img)}/{len(wit)} 支持读数', orig, new
    if ok_img and ok_our:
        return 'review', f'两种写法证人都有（读数 {len(ok_img)}、我们 {len(ok_our)}）', orig, new
    if ok_our and not ok_img:
        return 'review', f'证人 {len(ok_our)}/{len(wit)} 支持**我们**的写法，读数可疑', orig, new

    # 证人两边都不认：多半外文或乱码，交判词典兜底
    sys.path.insert(0, str(ROOT / 'scripts'))
    from alexander_lexicon import build, is_word
    lex = _lex(build)
    ow = WORD.findall(ours)
    nw = WORD.findall(img)
    if ow and nw and all(is_word(w, lex) for w in ow) \
            and not all(is_word(w, lex) for w in nw):
        bad = [w for w in nw if not is_word(w, lex)]
        if all(FOREIGN_TAIL.search(w.lower()) for w in bad):
            return 'review', f'读数是外文词 {bad}，判词典不认，要人看', orig, new
        return 'review', f'真词改成非词 {bad}，可疑', orig, new
    return 'review', '证人两边都锚不上', orig, new


_LEX = []


def _lex(build):
    if not _LEX:
        _LEX.append(build())
    return _LEX[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--review', action='store_true')
    a = ap.parse_args()

    pub = published()
    done = existing_fixes()
    buckets = {'accept': [], 'review': [], 'anchor': []}
    seen = set()
    for vol, pg, ch, ours, img in read_log():
        if ours in done or ours in seen:
            continue
        seen.add(ours)
        b, why, old, new = judge(vol, ours, img, pub, ch)
        buckets[b].append((vol, pg, ch, old or ours, new or img, why))

    for k, name in (('accept', '自动采纳'), ('review', '要人看'), ('anchor', '锚不上')):
        print(f'{name}：{len(buckets[k])} 条')
    if a.review:
        for vol, pg, ch, ours, img, why in buckets['review']:
            print(f'  v{vol} p{pg} ch{ch}  {ours!r}\n      → {img!r}\n      {why}')
    if a.write and buckets['accept']:
        with FIXES.open('a', encoding='utf-8') as fh:
            fh.write('\n# 整页比对自动定案（isaiah_page_adjudicate.py，三道闸见脚本注释）\n')
            for vol, pg, ch, ours, img, why in buckets['accept']:
                fh.write(f'{ours}\t{img}\tpage-v{vol}p{pg}: {why}\n')
        print(f'已写入 {len(buckets["accept"])} 条 → {FIXES}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
