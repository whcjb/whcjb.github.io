#!/usr/bin/env python3
"""莱尔马太：e-Sword 本 + 1857 扫描件判读 → 定本 ryle_raw/matthew/sections.json

    python3 scripts/ryle_apply.py

依次做：
  1. 看图判读表 review.tsv 里 verdict=1857 的，按对齐位置换成原书文字（reading 栏）。
  2. 对齐位置上 1857 有 St.、e-Sword 删掉的（collation_diffs.tsv 的 st 类），补回 St.。
  3. 出处 ⟨Gen_12:3⟩ → 1857 写法 Gen. xii. 3：书卷缩写取同位 OCR（须是该卷合法缩写），
     否则取全书该卷最常见的写法；章号罗马数字，节号与 e-Sword 一致（录入本的数字比 OCR 可靠）。
  4. 整族拼写回改（ryle_common.GLOBAL_SPELLING，Savior→Saviour 等）。
  5. 零星手工修正（MANUAL，每条都写明依据）。
改动逐条记进 ryle_raw/matthew/applied.tsv，验收＝重跑后 sections.json 逐字节不变。
"""
import collections
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ryle_common import respell  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
SRC = RAW / 'esword_sections.json'
DIFF = RAW / 'collation_diffs.tsv'
REVIEW = RAW / 'review.tsv'
OUT = RAW / 'sections.json'
LOG = RAW / 'applied.tsv'

# e-Sword 书卷代号 → (全名, 1857 默认缩写, 允许的其他写法)
BOOKS = {
    'Gen': ('Genesis', 'Gen.', ['Genesis']), 'Exo': ('Exodus', 'Exod.', ['Exodus', 'Ex.']),
    'Lev': ('Leviticus', 'Lev.', []), 'Num': ('Numbers', 'Numb.', ['Num.']),
    'Deu': ('Deuteronomy', 'Deut.', []), 'Jos': ('Joshua', 'Josh.', ['Joshua']),
    'Jdg': ('Judges', 'Judges', ['Judg.']), 'Rut': ('Ruth', 'Ruth', []),
    '1Sa': ('1 Samuel', '1 Sam.', []), '2Sa': ('2 Samuel', '2 Sam.', []),
    '1Ki': ('1 Kings', '1 Kings', []), '2Ki': ('2 Kings', '2 Kings', []),
    '1Ch': ('1 Chronicles', '1 Chron.', []), '2Ch': ('2 Chronicles', '2 Chron.', []),
    'Neh': ('Nehemiah', 'Nehem.', ['Neh.']), 'Est': ('Esther', 'Esther', []), 'Job': ('Job', 'Job', []),
    'Psa': ('Psalms', 'Psalm', ['Psal.', 'Ps.', 'Psalms']), 'Pro': ('Proverbs', 'Prov.', ['Proverbs']),
    'Ecc': ('Ecclesiastes', 'Eccles.', ['Eccl.']), 'Son': ('Song of Solomon', 'Cant.', []),
    'Isa': ('Isaiah', 'Isaiah', ['Isa.', 'Isai.']), 'Jer': ('Jeremiah', 'Jer.', ['Jerem.', 'Jeremiah']),
    'Lam': ('Lamentations', 'Lam.', []), 'Eze': ('Ezekiel', 'Ezek.', ['Ezekiel']),
    'Dan': ('Daniel', 'Dan.', ['Daniel']), 'Hos': ('Hosea', 'Hosea', ['Hos.']), 'Joe': ('Joel', 'Joel', []),
    'Amo': ('Amos', 'Amos', []), 'Oba': ('Obadiah', 'Obad.', []), 'Jon': ('Jonah', 'Jonah', []),
    'Mic': ('Micah', 'Micah', ['Mic.']), 'Nah': ('Nahum', 'Nahum', []), 'Hab': ('Habakkuk', 'Hab.', []),
    'Zep': ('Zephaniah', 'Zeph.', []), 'Hag': ('Haggai', 'Hag.', []), 'Zec': ('Zechariah', 'Zech.', []),
    'Mal': ('Malachi', 'Mal.', []),
    'Mat': ('Matthew', 'Matt.', ['Matth.']), 'Mar': ('Mark', 'Mark', []), 'Luk': ('Luke', 'Luke', []),
    'Joh': ('John', 'John', []), 'Act': ('Acts', 'Acts', []), 'Rom': ('Romans', 'Rom.', []),
    '1Co': ('1 Corinthians', '1 Cor.', []), '2Co': ('2 Corinthians', '2 Cor.', []),
    'Gal': ('Galatians', 'Gal.', []), 'Eph': ('Ephesians', 'Ephes.', ['Eph.']),
    'Phi': ('Philippians', 'Phil.', ['Philipp.']), 'Col': ('Colossians', 'Col.', []),
    '1Th': ('1 Thessalonians', '1 Thess.', ['1 Thes.']), '2Th': ('2 Thessalonians', '2 Thess.', ['2 Thes.']),
    '1Ti': ('1 Timothy', '1 Tim.', []), '2Ti': ('2 Timothy', '2 Tim.', []), 'Tit': ('Titus', 'Tit.', ['Titus']),
    'Phm': ('Philemon', 'Philem.', []), 'Heb': ('Hebrews', 'Heb.', []), 'Jam': ('James', 'James', []),
    '1Pe': ('1 Peter', '1 Peter', ['1 Pet.']), '2Pe': ('2 Peter', '2 Peter', ['2 Pet.']),
    '1Jo': ('1 John', '1 John', []), '2Jo': ('2 John', '2 John', []), '3Jo': ('3 John', '3 John', []),
    'Jud': ('Jude', 'Jude', []), 'Rev': ('Revelation', 'Rev.', []),
}
REF = re.compile(r'⟨([1-3]?[A-Z][a-z]{1,2})_(\d+):([^⟩]+)⟩')

# 零星手工修正：(段, e-Sword 原文片段, 改作, 依据)。片段须在该段恰好出现一次。
MANUAL = [
    ('11:25', 'sent empty away empty."', 'sent empty away."',
     '1857 p.134 作 "sent empty away"；判读表 #53 补了前面的 empty，后面那个被对齐归进了出处一格，这里删掉'),
    ('24:15', 'Irenœus', 'Irenæus', '1857 p.341 脚注作 Irenæus（æ 连字），e-Sword 录成 œ'),
    # 出处：多条合写、节段，照 1857 原样（e-Sword 拆成逐条、统一了分隔符）
    ('1:1', '(Gen. xii. 3. Isaiah xi. 1.)', '(Gen. xii. 3; Isaiah xi. 1.)', '1857 p.21 两条之间是分号'),
    ('12:22', '(Psalm xxxix. 1. Psalm cxli. 3. James iii. 2.)', '(Psal. xxxix. 1, cxli. 3; James iii. 2.)',
     '1857 p.151 原作合写'),
    ('12:22', '(Heb. vi. 4—6, and Heb. x. 26—27.)', '(Heb. vi. 4—7, and x. 26, 27.)',
     '1857 原作 vi. 4—7, and x. 26, 27'),
    ('26:14', '(Mark ix. 48.)', '(Mark ix. 44.)', '1857 p.372 作 ix. 44（钦定本 9:44 与 9:48 同句，原书不误），e-Sword 改成 48'),
]
# 1857 出处误植、e-Sword 已改正的：沿用改正，书首页逐条列出（引文按钦定本核过）
REF_ERRATA = [
    ('14:1', 'Eccles. vi. 8', 'Eccles. v. 8', '引文 "he that is higher than the highest regardeth" 在传 5:8'),
    ('17:1', 'Luke xx. 20', 'Luke xx. 38', '引文 "not a God of the dead, but of the living" 在路 20:38'),
    ('21:12', 'Rom. ii. 20', 'Rom. xi. 20', '引文 "be not high-minded, but fear" 在罗 11:20'),
    ('24:1', 'Psal. lxviii. 6', 'Psal. lxvii. 6', '引文 "the earth shall yield her increase" 在诗 67:6'),
    ('25:31', 'James ii. 11', 'James ii. 20', '引文 "faith … being alone" 实在雅 2:17；此处沿用 e-Sword 的 2:20，待定'),
    ('27:57', 'Acts vii. 4', 'Acts viii. 4', '引文 "they that were scattered … preaching the word" 在徒 8:4'),
    ('28:11', 'Acts iii. 23', 'Acts viii. 23', '引文 "the gall of bitterness and bond of iniquity" 在徒 8:23'),
]


def roman(n):
    out = ''
    for v, s in ((100, 'c'), (90, 'xc'), (50, 'l'), (40, 'xl'), (10, 'x'), (9, 'ix'), (5, 'v'), (4, 'iv'), (1, 'i')):
        while n >= v:
            out += s
            n -= v
    return out


def segments(d):
    """按 collate 的词流顺序列出所有文本段：段落被 ⟦fn⟧ 切开，脚注就地插入。
    返回 [(sec_idx, kind, idx, start, end)]，kind=p 指 paras[idx] 的 [start:end]，n 指 notes[idx] 全文。"""
    segs = []
    for si, s in enumerate(d['sections']):
        ni = 0
        for pi, p in enumerate(s['paras']):
            pos = 0
            for m in re.finditer('⟦fn⟧', p):
                segs.append((si, 'p', pi, pos, m.start()))
                segs.append((si, 'n', ni, 0, len(s['notes'][ni])))
                ni += 1
                pos = m.end()
            segs.append((si, 'p', pi, pos, len(p)))
    return segs


TOK = re.compile(r'[^\s⟨⟩—]+')


def key(w):
    return re.sub(r'[^a-z0-9]', '', w.lower())


def token_index(d):
    """全书 e-Sword 词流（与 ryle_collate.es_tokens 同口径）→ [(sec_idx, kind, idx, start, end)]。"""
    out = []
    for si, kind, idx, a, b in segments(d):
        s = d['sections'][si]
        text = (s['paras'] if kind == 'p' else s['notes'])[idx]
        for m in TOK.finditer(text, a, b):
            if key(m.group(0).replace('⟪', '').replace('⟫', '').replace('*', '')):
                out.append((si, kind, idx, m.start(), m.end()))
    return out


def load_tsv(p):
    return list(csv.DictReader(p.open(encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))


def ref_abbrevs(diff_rows):
    """出处行：e-Sword 代号与同位 OCR 缩写配对，统计每卷 1857 的常见写法。"""
    pair = {}
    cnt = collections.defaultdict(collections.Counter)
    for r in diff_rows:
        if r['cat'] != 'ref':
            continue
        codes = re.findall(r'([1-3]?[A-Z][a-z]{1,2})_\d', r['esword'])
        names = re.findall(r'((?:[1-3]\s?)?[A-Z][a-z]+\.?)\s*(?:[ivxlcIl1]+|[A-Z]{1,4})[.,]', r['ocr1857'])
        if len(codes) != len(names):
            continue
        # 本行 e-Sword 词里第几个是出处 → 词流序号
        idxs = [int(r['es_idx']) + j for j, w in enumerate(r['esword'].split()) if re.search(r'_\d', w)]
        for ti, c, n in zip(idxs, codes, names):
            n = re.sub(r'^([1-3])(?=[A-Z])', r'\1 ', n)
            if c in BOOKS and n in [BOOKS[c][1]] + BOOKS[c][2]:
                pair[ti] = n
                cnt[c][n] += 1
    return pair, cnt


def main():
    d = json.loads(SRC.read_text(encoding='utf-8'))
    toks = token_index(d)
    diff_rows = load_tsv(DIFF)
    review = load_tsv(REVIEW)
    log = []
    edits = collections.defaultdict(list)     # (si, kind, idx) -> [(start, end, new, why)]

    def text_of(si, kind, idx):
        s = d['sections'][si]
        return (s['paras'] if kind == 'p' else s['notes'])[idx]

    # 1. 看图判读
    for r in review:
        if r['verdict'] != '1857':
            continue
        i = int(r['es_idx'])
        n = len(r['esword'].split())
        why = f"看图判读 #{r['id']}（1857 p.{r['page_bbox'].split()[0]}）"
        if n == 0:                                   # 插入：放在第 i 个词之前
            si, kind, idx, a, _ = toks[i]
            edits[(si, kind, idx)].append((a, a, r['reading'] + ' ', why))
            continue
        first, last = toks[i], toks[i + n - 1]
        si, kind, idx, a, _ = first
        b = last[4]
        assert last[:3] == first[:3], r
        old = text_of(si, kind, idx)[a:b]
        lead = re.match(r'[*⟪]*', old).group(0)
        trail = re.search(r'[*⟫]*$', old).group(0)
        new = (lead + r['reading'] + trail) if r['reading'] else ''
        if not new:                                  # 删词：连同后一个空格
            t = text_of(si, kind, idx)
            if b < len(t) and t[b] == ' ':
                b += 1
            elif a > 0 and t[a - 1] == ' ':
                a -= 1
        edits[(si, kind, idx)].append((a, b, new, why))

    # 2. St.
    for r in diff_rows:
        if r['cat'] == 'st':
            si, kind, idx, a, _ = toks[int(r['es_idx'])]
            edits[(si, kind, idx)].append((a, a, 'St. ', f"补回 St.（1857 p.{r['page_bbox'].split()[0]} 同位有）"))

    # 3. 出处：作为编辑一起落（偏移以 e-Sword 原文计）
    pair, cnt = ref_abbrevs(diff_rows)
    default = {c: (cnt[c].most_common(1)[0][0] if cnt[c] else BOOKS[c][1]) for c in BOOKS}
    start2tok = {(si, kind, idx, a): n for n, (si, kind, idx, a, _) in enumerate(toks)}
    nref = collections.Counter()
    for si, s in enumerate(d['sections']):
        for kind, arr in (('p', s['paras']), ('n', s['notes'])):
            for idx, tx in enumerate(arr):
                for m in REF.finditer(tx):
                    c, ch, vs = m.group(1), int(m.group(2)), m.group(3)
                    if c not in BOOKS:
                        raise SystemExit(f'未知书卷代号 {c}')
                    ti = start2tok.get((si, kind, idx, m.start() + 1))
                    ab = pair.get(ti)
                    nref['same-pos' if ab else 'default'] += 1
                    vs = re.sub(r'\s*[-–]\s*', '—', vs)
                    edits[(si, kind, idx)].append((m.start(), m.end(), f'{ab or default[c]} {roman(ch)}. {vs}',
                                                   None))

    # 落 1、2、3
    for (si, kind, idx), es in edits.items():
        s = d['sections'][si]
        arr = s['paras'] if kind == 'p' else s['notes']
        t = arr[idx]
        es.sort(key=lambda e: (e[0], e[1]))
        for a, b, new, why in reversed(es):
            if why:
                log.append((f"{s['ch']}:{s['v1']}", why, t[a:b], new))
            t = t[:a] + new + t[b:]
        arr[idx] = t

    # 4. 拼写族
    n_sp = 0
    for s in d['sections']:
        for arr in (s['paras'], s['notes']):
            for i, t in enumerate(arr):
                nt = respell(t)
                n_sp += sum(1 for x, y in zip(t.split(), nt.split()) if x != y)
                arr[i] = nt
    d['preface'] = [respell(p) for p in d['preface']]

    # 5. 手工
    for sec, old, new, why in MANUAL:
        s = next(x for x in d['sections'] if f"{x['ch']}:{x['v1']}" == sec)
        hits = [(arr, i) for arr in (s['paras'], s['notes']) for i, t in enumerate(arr) if old in t]
        assert len(hits) == 1 and hits[0][0][hits[0][1]].count(old) == 1, (sec, old, len(hits))
        arr, i = hits[0]
        arr[i] = arr[i].replace(old, new)
        log.append((sec, '手工：' + why, old, new))

    # 版式：序言落款两行；24:36 一段原书经文框印到 51 节（e-Sword 误作 46）
    d['preface'] = [x for p in d['preface'] for x in
                    (p.replace('*Helmingham Rectory,December,* 1856.', '*Helmingham Rectory,*\n*December,* 1856.')
                     .split('\n'))]
    for s in d['sections']:
        if (s['ch'], s['v1']) == (24, 36):
            s['v2'] = 51

    OUT.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')
    with LOG.open('w', encoding='utf-8') as f:
        f.write('sec\twhy\tesword\tnow\n')
        for row in log:
            f.write('\t'.join(x.replace('\t', ' ').replace('\n', ' ') for x in row) + '\n')
    c = collections.Counter(w.split('（')[0].split('#')[0] for _, w, _, _ in log)
    print(dict(c), f'出处 {dict(nref)}，拼写族 {n_sp} 处 →', OUT)
    print('出处缩写（1857 同位读出的常见写法）：', {k: dict(v) for k, v in cnt.items() if len(v) > 1})


if __name__ == '__main__':
    main()
