#!/usr/bin/env python3
"""加尔文《撒母耳记上讲章》拉丁文本：OCR 判读（由 extract_calvin_1sam.py 在出 units.json 前调用）。

按 old-book-ocr 的分层做，所有判据往「宁可不改」一侧偏：

  ① 字形：印本拉丁文不带重音，文字层里的 é è à â ô ü 之类是 OCR 噪点，去掉（去掉后须在词表里）；
     元音后的分音符（Israël、Isaï）是印本原有的，保留。
  ② 第二证人按位置：主文本（PDF 文字层）与 tesseract 证人逐栏对齐，一对一替换处，
     主文本的词不在词表里、证人那一处在词表里、且两者只差一两个字（或属已知字形混淆）→ 用证人的字。
     两边都是真词（ilia/illa、ilium/illum 这种）只在白名单里的混淆对才改，其余照录、记账。
  ③ 仍不在词表里的：字形混淆规则（rn↔m、c↔e、o↔c、8→s、1→l …）生成候选，词表里**唯一**命中才改。
  其余一律照录，进 residue 账，留待看图。

词表：wooorm/dictionaries 的拉丁文 hunspell 词典 unmunch 展开（约 1800 万词形），只取与本书两份 OCR 相交的部分
缓存进 calvin_sermons_raw/1samuel/lexicon_hits.txt（入库）；专名与本书惯用词另靠语料自证（两份 OCR 都多次出现）。
"""
import collections
import difflib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'calvin_sermons_raw' / '1samuel'
FORMS = RAW / 'lexicon' / 'forms.txt'          # unmunch 产物，不入库（见 PROVENANCE）
HITS = RAW / 'lexicon_hits.txt'

WORD = re.compile(r"[A-Za-zÀ-ÿ0-9]+(?:'[A-Za-z]+)?")
# 两边都是真词时，仍可按证人改的混淆对（主文本 → 证人）：只收 OCR 典型误读、且错形在神学拉丁文里几乎不会出现的
REAL_WORD_SWAPS = {
    ('ilia', 'illa'), ('ilium', 'illum'), ('ilio', 'illo'), ('ilias', 'illas'), ('ilios', 'illos'),
    ('ilii', 'illi'), ('ilis', 'illis'), ('turn', 'tum'), ('earn', 'eam'), ('quern', 'quem'),
    ('hie', 'hic'), ('hue', 'huc'), ('nee', 'nec'), ('tarnen', 'tamen'), ('decern', 'decem'),
}
# 必改表：拉丁文里不存在（或在本书语境里不可能出现）的 OCR 错形，两份 OCR 一起读错也照改。
# ilia（腹股沟）/ ilium（特洛伊）在加尔文讲章里不会出现，本书全是 illa / illum 的 ll→li 误读。
FORCE = {'tarnen': 'tamen', 'tarn': 'tam', 'nee': 'nec', 'hie': 'hic', 'hue': 'huc', 'turn': 'tum', 'earn': 'eam',
         'quern': 'quem', 'decern': 'decem', 'saltern': 'saltem', 'ilia': 'illa', 'ilium': 'illum', 'ilio': 'illo',
         'iliis': 'illis', 'ilii': 'illi', 'ilias': 'illas', 'ilios': 'illos', 'iliud': 'illud', 'ilius': 'illius',
         # 第二批（2026-11-11）：全书判读后两份 OCR 一起读错、仍不在词表的高频错形；正形在本书出现次数是错形的 5 倍以上
         'donee': 'donec', 'hune': 'hunc', 'banc': 'hanc', 'lam': 'iam', 'ulis': 'illis', 'uli': 'illi', 'ot': 'et',
         'sie': 'sic', 'ao': 'ac', 'ideirco': 'idcirco', 'hoe': 'hoc', 'hino': 'hinc', 'haee': 'haec', 'ant': 'aut',
         'saneti': 'sancti', 'lesu': 'iesu', 'hano': 'hanc', 'ct': 'et', 'yero': 'vero', 'our': 'cur', 'yerbis': 'verbis',
         'tameu': 'tamen', 'ipsins': 'ipsius', 'yeluti': 'veluti', 'qnod': 'quod', 'augustias': 'angustias', 'tuno': 'tunc',
         'soriptura': 'scriptura', 'neqne': 'neque', 'etiarn': 'etiam', 'el': 'ei', 'efc': 'etc', 'discamns': 'discamus',
         'dieitur': 'dicitur', 'denm': 'deum', 'cnim': 'enim'}
# 字形混淆（错形片段 → 正形片段）
CONFUSIONS = [('rn', 'm'), ('m', 'rn'), ('c', 'e'), ('e', 'c'), ('o', 'c'), ('c', 'o'), ('8', 's'), ('1', 'l'),
              ('1', 'i'), ('l', 'i'), ('i', 'l'), ('ii', 'u'), ('u', 'ii'), ('n', 'u'), ('u', 'n'), ('li', 'h'),
              ('h', 'li'), ('fi', 'f'), ('ri', 'n'), ('in', 'm'), ('m', 'in'), ('0', 'o'), ('6', 'e'), ('t', 'f'),
              ('f', 't'), ('cl', 'd'), ('d', 'cl'), ('y', 'v'), ('Y', 'V'), ('O', 'C'), ('G', 'C'), ('$', 's')]


def strip_accents(w):
    """去掉 OCR 加上的重音；元音后的分音符（Israël / Isaï）保留。"""
    out = []
    for i, ch in enumerate(w):
        if ch in 'ëï' and i > 0 and w[i - 1].lower() in 'aeou':
            out.append(ch)
            continue
        d = unicodedata.normalize('NFD', ch)
        out.append(''.join(c for c in d if unicodedata.category(c) != 'Mn'))
    return ''.join(out)


def norm(w):
    return strip_accents(w).lower().replace('ë', 'e').replace('ï', 'i')


class Lexicon:
    def __init__(self, corpus_words, extra=()):
        need = {norm(w) for w in corpus_words}
        need |= {c for w in list(need) for c in variants(w)}
        need |= set(extra)
        if HITS.exists() and not FORMS.exists():
            self.words = set(HITS.read_text(encoding='utf-8').split())
        else:
            self.words = set()
            with FORMS.open(encoding='utf-8', errors='ignore') as f:
                for ln in f:
                    w = ln.strip().lower()
                    if w in need:
                        self.words.add(w)
            HITS.write_text('\n'.join(sorted(self.words)) + '\n', encoding='utf-8')
        self.corpus = collections.Counter()

    def ok(self, w):
        n = norm(w)
        return n in self.words or self.corpus.get(n, 0) >= 4 or n.isdigit()


def variants(w):
    """单处字形混淆生成的候选（只换一处）。"""
    out = set()
    for a, b in CONFUSIONS:
        a2, b2 = a.lower(), b.lower()
        start = 0
        while True:
            i = w.find(a2, start)
            if i < 0:
                break
            out.add(w[:i] + b2 + w[i + len(a2):])
            start = i + 1
    return out


CAPITALIZED = set()      # 本书里大写形明显多于小写形的词（专名），由 Repairer 初始化


def match_case(src, new):
    if src[:1].isupper() or norm(new) in CAPITALIZED:                 # 专名（loannis → Ioannis：大写 I 读成 l）
        return new[:1].upper() + new[1:]
    return new


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def close(a, b):
    """证人替换的相近度：长词差两处以内、短词（≤4）差一处以内。"""
    return lev(a, b) <= (2 if min(len(a), len(b)) > 4 else 1)


class Repairer:
    def __init__(self, witness_path, primary_words):
        self.wit = {}
        for ln in Path(witness_path).read_text(encoding='utf-8').splitlines():
            r = json.loads(ln)
            t = re.sub(r'-\n\s*(?=[a-zà-ÿ])', '', r['text'])          # 证人也先接连字符
            self.wit[(r['vol'], r['page'], r['col'])] = WORD.findall(t)
        wit_words = [w for ws in self.wit.values() for w in ws]
        # 疏排拆开的词（capsel lam、s ci am us、tan to）：相邻 2–4 截的拼合也查词表
        joins = set()
        pn = [norm(w) for w in primary_words]
        for i in range(len(pn)):
            for k in (2, 3, 4):
                seg = pn[i:i + k]
                if len(seg) == k and (k == 2 or all(len(x) <= 3 for x in seg)):
                    joins.add(''.join(seg))
        self.lex = Lexicon(primary_words + wit_words, joins)
        # 语料自证：主文本、证人各出现 ≥2 次的词形（专名、本书惯用拼法）
        pc = collections.Counter(norm(w) for w in primary_words)
        wc = collections.Counter(norm(w) for w in wit_words)
        self.lex.corpus = collections.Counter({w: min(pc[w], wc[w]) * 2 for w in pc if wc.get(w, 0) >= 2 and pc[w] >= 2})
        self.freq = pc + wc
        up = collections.Counter(norm(w) for w in primary_words if w[:1].isupper())
        CAPITALIZED.update(w for w, n in up.items() if n >= 5 and n > 4 * (pc[w] - n))
        self.log = []

    def fix_word(self, p, w, where):
        """主文本词 p，证人对位词 w（可为 None）→ (新词, 动作)；不改返回 (p, None)。"""
        f = FORCE.get(norm(p))
        if f:
            return match_case(p, f), 'force'
        sa = strip_accents(p)
        if sa != p and self.lex.ok(sa):
            p2, act = sa, 'accent'
        else:
            p2, act = p, None
        if self.lex.ok(p2):
            if w and (norm(p2), norm(w)) in REAL_WORD_SWAPS and norm(p2) != norm(w):
                return match_case(p2, strip_accents(w).lower() if p2.islower() else strip_accents(w)), 'swap'
            return p2, act
        # 不在词表里
        if w:
            ws = strip_accents(w)
            if self.lex.ok(ws) and close(norm(p2), norm(ws)):
                return match_case(p2, ws if not p2.islower() else ws.lower()), 'witness'
        if w and norm(w) == norm(p2):              # 两份 OCR 读法一致：只有看图能推翻，规则不动它
            return p2, ('residue' if not act else act + '+residue')
        cands = {c for c in variants(norm(p2)) if c in self.lex.words}
        if w and norm(w) in cands:
            return match_case(p2, norm(w)), 'rule+witness'
        # 只凭规则（没有证人支持）：候选唯一、且在本书语料里出现过（两份 OCR 合计 ≥3 次），才改
        cands = {c for c in cands if self.freq.get(c, 0) >= 3}
        if len(cands) == 1 and len(p2) >= 4:
            return match_case(p2, cands.pop()), 'rule'
        return p2, ('residue' if not act else act + '+residue')

    def join_split(self, text, key):
        """段内相邻 2–4 截以单空格隔开、拼起来是词表里的词、且其中至少一截不是词 → 并（两截都是真词的一律不并：a Deo ≠ aDeo）。"""
        ms = list(WORD.finditer(text))
        out, i, pos = [], 0, 0
        while i < len(ms):
            done = False
            for k in (4, 3, 2):
                grp = ms[i:i + k]
                if len(grp) < k:
                    continue
                if any(text[grp[j].end():grp[j + 1].start()] != ' ' for j in range(k - 1)):
                    continue
                if k > 2 and not all(len(g.group(0)) <= 3 for g in grp):
                    continue
                pieces = [g.group(0) for g in grp]
                if any(norm(x) in FORCE for x in pieces) or any(x[:1].isupper() for x in pieces[1:]):
                    continue                          # 已知错形（Ulis / quern）由必改表处理；后截大写不是一个词
                j = ''.join(pieces)
                if norm(j) in self.lex.words and any(not self.lex.ok(x) for x in pieces):
                    out.append(text[pos:grp[0].start()] + j)
                    pos = grp[-1].end()
                    self.log.append((key[0], key[1], key[2], ' '.join(pieces), '', j, 'join'))
                    i += k
                    done = True
                    break
            if not done:
                i += 1
        out.append(text[pos:])
        return ''.join(out)

    def repair_column(self, key, segs_list):
        """segs_list：本栏各行的 segs [[(text, italic), …], …]，原地改写。"""
        wit = self.wit.get(key, [])
        for ri, segs in enumerate(segs_list):
            segs_list[ri] = [(self.join_split(t, key), it) for t, it in segs]
        toks = []          # (row, seg, start, end, word)
        for ri, segs in enumerate(segs_list):
            for si, (t, it) in enumerate(segs):
                for m in WORD.finditer(t):
                    toks.append((ri, si, m.start(), m.end(), m.group(0)))
        pn = [norm(t[4]) for t in toks]
        wn = [norm(w) for w in wit]
        sm = difflib.SequenceMatcher(None, pn, wn, autojunk=False)
        pair = {}
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == 'replace' and i2 - i1 == j2 - j1:
                for k in range(i2 - i1):
                    pair[i1 + k] = wit[j1 + k]
            elif op == 'equal':
                for k in range(i2 - i1):
                    pair[i1 + k] = wit[j1 + k]
        edits = collections.defaultdict(list)
        for i, (ri, si, a, b, word) in enumerate(toks):
            new, act = self.fix_word(word, pair.get(i), key)
            if act:
                self.log.append((key[0], key[1], key[2], word, pair.get(i) or '', new, act))
            if new != word:
                edits[(ri, si)].append((a, b, new))
        for (ri, si), es in edits.items():
            t, it = segs_list[ri][si]
            for a, b, new in sorted(es, reverse=True):
                t = t[:a] + new + t[b:]
            segs_list[ri][si] = (t, it)

    def write_log(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write('vol\tpage\tcol\tprimary\twitness\tresult\taction\n')
            for r in self.log:
                f.write('\t'.join(str(x) for x in r) + '\n')
        c = collections.Counter(r[6] for r in self.log)
        return c
