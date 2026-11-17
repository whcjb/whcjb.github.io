#!/usr/bin/env python3
"""亚历山大《以赛亚书》英文页：捞希伯来/希腊文被 OCR 读成拉丁乱码的位置。

抽章实读 35 轮下来，剩下的错误六成是这一类：原书印的是希伯来词（或希腊词），
OCR 读成 `nx`、`b?`、`rvinxnsa`、`"pa`、`'ntes'?`、`tohn`……形态各不相同，
黑名单判据抓不住。这里反过来用「这个词英文里有没有」来判：

  • 词典 = /usr/share/dict/web2 + 全书出现 ≥3 次的词（人名、拉丁书名常反复出现）
  • 一个拉丁字母串若不在词典里，且满足下列之一，就列为可疑：
      cue   前一个词是引出原文的词（the verb / word / phrase / form / reads / of …）
      heb   前后 6 个词内有希伯来字母（乱码常与正确的希伯来词相邻）
      short 长度 ≤4 且不是常见缩写
  • 不管在不在词典，核心串里夹着 ? ! " ] } ; 这类符号的，一律列出（`b?`、`"pa`）
  • 希腊词里混进拉丁字母的（`ἐχαλοῦν` 不算，`ἔθνος o` 里孤立的 o 算 short）

输出 TSV：章、书页、行号、可疑串、类别、上下文。只列不改。
用法：python3 scripts/isaiah_garble_detector.py > $SCRATCHPAD/garble.tsv
"""
import collections
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGES = ROOT / 'alexander' / 'isaiah'

HEB = re.compile(r'[֐-׿]')
GRK = re.compile(r'[Ͱ-Ͽἀ-῿]')
TOKEN = re.compile(r'\S+')
CORE = re.compile(r"^[(\[*'\"‘“—–-]*(.*?)[)\].,;:*'\"’”?!—–-]*$")
CUE = {'verb', 'word', 'words', 'phrase', 'form', 'forms', 'noun', 'nouns', 'particle', 'reads', 'read',
       'reading', 'suffix', 'name', 'term', 'expression', 'preposition', 'root', 'adjective',
       'participle', 'infinitive', 'pronoun', 'translates', 'explains', 'takes', 'makes', 'gives',
       'give', 'make', 'take', 'explain', 'derives', 'derive', 'from', 'with', 'for', 'of', 'before',
       'after', 'construe', 'construes', 'synonymous', 'equivalent', 'version', 'rendering', 'textual',
       'marginal', 'article', 'conjunction', 'plural', 'singular', 'feminine', 'masculine', 'verbs',
       'and', 'or', 'between', 'to', 'like', 'by'}
ABBR = {'ch', 'vs', 'v', 'cf', 'ib', 'id', 'al', 'pp', 'p', 'sc', 'q', 'd', 'i', 'e', 'g', 'viz', 'etc',
        'ff', 'll', 'oh', 'lo', 'ye', 'thy', 'thee', 'thou', 'hath', 'doth', 'ad', 'loc', 'seq', 'vol',
        'tom', 'pt', 'ed', 'ii', 'iii', 'iv', 'vi', 'vii', 'viii', 'ix', 'xi', 'xii', 'xx', 'xl', 'lxx',
        'mss', 'ms', 'heb', 'gr', 'lat', 'sam', 'chr', 'chron', 'ps', 'prov', 'eccl', 'ecc', 'isa',
        'jer', 'ez', 'ezek', 'dan', 'hos', 'am', 'mic', 'nah', 'hab', 'zeph', 'hag', 'zech', 'mal',
        'matt', 'mt', 'rom', 'cor', 'gal', 'eph', 'phil', 'col', 'thess', 'tim', 'heb', 'jas', 'pet',
        'rev', 'gen', 'ex', 'exod', 'lev', 'num', 'deut', 'josh', 'jos', 'judg', 'ruth', 'neh', 'esth',
        'job', 'sol', 'cant', 'lam', 'joel', 'obad', 'jon', 'acts', 'luke', 'mark', 'john', 'isai',
        'u', 's', 'w', 'b', 'c', 'f', 'n', 'r', 't', 'x', 'a', 'o', 'de', 'la', 'le', 'du', 'et', 'in',
        'ex', 'per', 'qui', 'quae', 'quod', 'est', 'non', 'sunt', 'ab', 'cum', 'sed', 'ut', 'ne',
        'die', 'der', 'das', 'und', 'ist', 'mit', 'von', 'zu', 'auf', 'ein', 'eine', 'den', 'dem',
        'des', 'sie', 'er', 'es', 'wie', 'man', 'nicht', 'so', 'da', 'wo', 'je', 'il', 'au', 'en'}
ODD = re.compile(r'[A-Za-z][?!"\]};:][A-Za-z]|[?!"\]}][A-Za-z]|^[A-Za-z]{1,6}[?!]$|^["!][A-Za-z]|\d[A-Za-z]|[A-Za-z]\d')


STRONG = {'verb', 'word', 'noun', 'phrase', 'form', 'particle', 'suffix', 'preposition', 'root', 'reads',
          'read', 'reading', 'term', 'participle', 'infinitive', 'pronoun', 'adjective', 'name'}


def known(low, dic):
    """词典查词，带最简单的词形还原（复数、-ed、-ing、-ly、-er）和连字符拆分。"""
    if low in dic:
        return True
    if '-' in low:
        return all(known(x, dic) for x in low.split('-') if x)
    for suf, rep in (('s', ''), ('es', ''), ('ed', ''), ('ed', 'e'), ('ing', ''), ('ing', 'e'), ('ly', ''),
                     ('er', ''), ('ies', 'y'), ('ied', 'y'), ('ers', ''), ('ness', ''), ('ment', '')):
        if low.endswith(suf) and low[:-len(suf)] + rep in dic:
            return True
        if low.endswith(suf) and len(low) > 5 and low[:-len(suf) - 1] == low[:-len(suf)][:-1] \
                and low[:-len(suf) - 1] in dic:      # harassing / stopped 双写
            return True
    return False


def trigram_model(dic):
    c = collections.Counter()
    for w in dic:
        w = f'^{w}$'
        for i in range(len(w) - 2):
            c[w[i:i + 3]] += 1
    return c


def oddness(low, tri):
    """词里最罕见的三字母组出现次数（英文词典里）；越小越像乱码。"""
    w = f'^{low}$'
    return min((tri[w[i:i + 3]] for i in range(len(w) - 2)), default=0)


def load_dict():
    words = set()
    for f in ('/usr/share/dict/web2', '/usr/share/dict/words', '/usr/share/dict/propernames'):
        try:
            words |= {w.strip().lower() for w in open(f, encoding='latin-1')}
        except OSError:
            pass
    return words


def strip_markup(line):
    line = re.sub(r'<!--.*?-->', ' ', line)
    line = re.sub(r'<[^>]+>', ' ', line)
    return line


FUNC = {'the', 'a', 'an', 'his', 'its', 'our', 'my', 'thy', 'their', 'this', 'that', 'it', 'him', 'her',
        'them', 'us', 'me', 'he', 'she', 'we', 'they', 'you', 'be', 'is', 'was', 'are', 'not', 'all', 'any',
        'one', 'two', 'god', 'man', 'men', 'own', 'way', 'law', 'day', 'war', 'sin', 'sea', 'end', 'new',
        'old', 'and', 'or', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'as', 'so', 'no', 'if', 'but', 'who',
        'how', 'why', 'out', 'up', 'off', 'now', 'yet', 'may', 'can', 'see', 'say', 'has', 'had', 'did',
        'do', 'go', 'let', 'put', 'set', 'use', 'own', 'too', 'few', 'far', 'ch', 'vs', 'v'}


def broad(texts, freq, dic):
    """宽口径：给 isaiah_garble_verify 用。只要沾一点边就列，真假交给三引擎裁图对读。"""
    out = []
    for ch in sorted(texts):
        page = '?'
        for ln, line in enumerate(texts[ch].split('\n'), 1):
            pm = re.findall(r'<!-- PAGE (\d+) -->', line)
            if pm:
                page = pm[-1]
            toks = TOKEN.findall(strip_markup(line))
            for i, tok in enumerate(toks):
                if HEB.search(tok) or GRK.search(tok) or not re.search(r'[A-Za-z]', tok):
                    continue
                m = CORE.match(tok)
                core = m.group(1) if m else tok
                raw = tok.strip('*(),.;:')
                low = core.lower()
                prev = re.sub(r'[^a-z]', '', toks[i - 1].lower()) if i else ''
                nxt_raw = toks[i + 1] if i + 1 < len(toks) else ''
                kind = None
                if re.search(r'[A-Za-z][?!"\]}][A-Za-z]|[?!"\]}\[][A-Za-z]|^["!][A-Za-z]|[A-Za-z]\?[),;:]|[A-Za-z]\?$', raw) \
                        and not (raw.endswith('?') and nxt_raw[:1].isupper()) and not raw.startswith('"'):
                    kind = 'odd'
                elif re.search(r'^"[a-z]', raw):
                    kind = 'odd-quote'
                elif not re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", core):
                    if re.search(r'[A-Za-z]\d|\d[A-Za-z]', core) and not re.fullmatch(r'\d+[a-z]|\d+(st|nd|rd|th)', core):
                        kind = 'digit-mix'
                elif len(core) == 1 and core not in 'aAIO' and prev not in ('ch', 'v', 'vs', 'p') \
                        and not (tok.rstrip('*),').endswith('.') and prev not in STRONG):   # i. e. / q. d. / p. 23
                    kind = 'single'
                elif core == 'a' and (tok.endswith(',') or tok.endswith('.') or prev in STRONG):
                    kind = 'single'
                elif prev in STRONG and core.islower() and freq[low] < 40 and low not in FUNC:
                    kind = 'strong-cue'
                elif prev in CUE and core.islower() and len(core) <= 4 and low not in FUNC and freq[low] < 40:
                    kind = 'cue-short'
                elif re.fullmatch(r'[ivxlcdm]+', low) or low in ABBR:
                    pass
                elif not known(re.sub(r"'s$", '', low), dic) and (freq[low] < 3 or len(core) <= 4) \
                        and not (core[0].isupper() and len(core) > 4):
                    kind = 'unknown'     # 短乱码（nx、ns、ps）全书反复出现，不能拿频次放行
                elif len(core) <= 5 and freq[low] < 60 and low not in FUNC and (
                        prev in STRONG | CUE | {'the', 'reads', 'explains', 'takes', 'makes', 'gives', 'derives',
                                                'that', 'than', 'as'}) and (
                        re.match(r'[,.;:)]', tok[len(tok.rstrip(',.;:)*')):] or 'x')
                        or re.sub(r'\W', '', nxt_raw.lower()) in {'is', 'as', 'in', 'has', 'may', 'means', 'to',
                                                                 'which', 'from', 'refers', 'here', 'and', 'or'}):
                    kind = 'real-word'   # 恰好是英文词的乱码：the fit refers / of tab, / Ewald gives toto its
                if kind:
                    nxt = toks[i + 1] if i + 1 < len(toks) else ''
                    prv = toks[i - 1] if i else ''
                    ctx = ' '.join(toks[max(0, i - 7):i + 6])
                    out.append((ch, page, ln, tok, kind, prv, nxt, ctx))
    return out


def main():
    dic = load_dict()
    tri = trigram_model(dic)
    texts = {}
    freq = collections.Counter()
    for p in glob.glob(str(PAGES / '[0-9]*.md')):
        ch = int(Path(p).stem)
        t = open(p, encoding='utf-8').read().split('\n---\n', 1)[1]
        texts[ch] = t
        for tok in TOKEN.findall(strip_markup(t)):
            m = CORE.match(tok)
            if m and m.group(1):
                freq[m.group(1).lower()] += 1
    if '--broad' in sys.argv:
        out = broad(texts, freq, dic)
        for r in out:
            print('\t'.join(map(str, r)))
        print(f'# 宽口径 {len(out)} 处', collections.Counter(r[4] for r in out), file=sys.stderr)
        return
    out = []
    for ch in sorted(texts):
        page = '?'
        for ln, line in enumerate(texts[ch].split('\n'), 1):
            pm = re.findall(r'<!-- PAGE (\d+) -->', line)
            if pm:
                page = pm[-1]
            toks = TOKEN.findall(strip_markup(line))
            for i, tok in enumerate(toks):
                if HEB.search(tok):
                    continue
                m = CORE.match(tok)
                core = m.group(1) if m else tok
                if not core:
                    continue
                kind = None
                if GRK.search(core):
                    if re.search(r'[A-Za-z]', core):
                        kind = 'greek-mix'
                elif ODD.search(core.replace("'s", '')) and not re.fullmatch(r'\d+[a-z]?|[A-Za-z]+\d*', core):
                    kind = 'odd-char'
                elif re.fullmatch(r"[A-Za-z][A-Za-z'’-]*", core):
                    low = core.lower().replace('’', "'")
                    base = re.sub(r"'s$", '', low)
                    prev = re.sub(r'\W', '', toks[i - 1]).lower() if i else ''
                    near = ' '.join(toks[max(0, i - 6):i + 7])
                    italic = tok.startswith('*') or tok.endswith('*') or tok.startswith('(*')
                    def unknown(j):
                        mm = CORE.match(toks[j]) if 0 <= j < len(toks) else None
                        w = (mm.group(1) if mm else '').lower()
                        return bool(re.fullmatch(r"[a-z'-]+", w)) and not known(w, dic) and freq[w] < 3
                    # 外文短语（拉丁/德/法引文）：左右各三个词里还有 ≥2 个不认识的词，乱码则多半孤立在英文里
                    foreign = sum(unknown(j) for j in (i - 3, i - 2, i - 1, i + 1, i + 2, i + 3)) >= 2
                    if prev in STRONG and len(core) <= 6 and core.islower() and not italic and freq[low] < 30:
                        kind = 'strong-cue'      # 「the verb tab」「the suffix in fins」——真词也列
                    elif known(base, dic) or freq[low] >= 3 or base in ABBR or foreign:
                        continue
                    elif core[0].isupper() and len(core) > 4:
                        continue
                    elif oddness(base, tri) < 3:
                        kind = 'gibberish'
                    elif HEB.search(near) and len(core) <= 6 and not italic:
                        kind = 'heb-near'
                    elif prev in CUE and len(core) <= 6 and not italic:
                        kind = 'cue'
                if kind:
                    ctx = ' '.join(toks[max(0, i - 7):i + 6])
                    out.append((ch, page, ln, tok, kind, ctx))
    for r in out:
        print('\t'.join(map(str, r)))
    print(f'# 共 {len(out)} 处', collections.Counter(r[4] for r in out), file=sys.stderr)


if __name__ == '__main__':
    main()
