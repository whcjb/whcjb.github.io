#!/usr/bin/env python3
"""以赛亚书：第二轮窄检测器——宽口径检测器（isaiah_garble_detector）看不见的两类外文错。

第 36–39 轮复抽（PROOFREAD_STATUS）量出来，检测器首批之后残留的外文错主要是：

  A. **拉丁 / 德 / 法文错字**（olentcs、perpendiculuni、fovei、in Us、in ilia、ivie zum）。
     宽口径能列到一部分，但 isaiah_garble_verify 用英文模型复读裁图——英文模型照样读成
     同一个错字，于是判 latin 排除。这一类要拿**该语言的词表**判，不能拿英文模型判。
  B. **合法但错一个字母的希伯来词**（34:15 דיה 成了 היה、27:2 ענו 成了 עפו）。
     文字判据看不出来；但亚历山大讨论的词多半就在本节经文里，所以拿 WLC 本节 ±3 节比：
     正文里的词不在附近经文里、却和附近经文的某个词只差一个字母 → 可疑。

只出候选，不改正文。列与 isaiah_garble_detector --broad 相同（章 页 行 词 类 前词 后词 上下文），
可直接喂给 isaiah_garble_verify 裁图；kind 列带建议读法（`lat-variant:perpendiculum`）。
落盘前逐条看图（[[feedback_image_proof_before_apply]]）。

词表：拉丁 / 德 / 法 / 意 / 英从本机 tesseract 模型的词典 dawg 导出（combine_tessdata -u +
dawg2wordlist），缓存在 ~/.cache/isaiah_lex/。

用法：
    python3 scripts/isaiah_lexicon_detector.py > $S/lex.tsv            # 全书
    python3 scripts/isaiah_lexicon_detector.py --chapters 27,34,48,64   # 回测
"""
import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from isaiah_garble_detector import CORE, TOKEN, known, strip_markup   # noqa: E402
from isaiah_hebrew_closedset import WINDOW, cons, load_wlc                        # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUB = Path(__import__('os').environ.get('ISAIAH_PUB', ROOT / 'alexander/isaiah'))
FORMS = ROOT / 'alexander_raw/isaiah/ref/wlc_forms.txt'
CACHE = Path.home() / '.cache/isaiah_lex'
TESSDATA = Path('/opt/homebrew/share/tessdata')
ANCHOR = re.compile(r'id="isaiah-(\d+)-(\d+)"')
HEBTOK = re.compile(r'[א-ת֑-ׇ]+(?:[־א-ת֑-ׇ]+)*')

# 本书扫描件里实测过的 OCR 形近混淆（左 = 正文里的错，右 = 原字）
CONFUSE = [('ni', 'm'), ('rn', 'm'), ('in', 'm'), ('iu', 'm'), ('m', 'ni'), ('c', 'e'), ('e', 'c'),
           ('i', 't'), ('t', 'i'), ('l', 'i'), ('i', 'l'), ('li', 'h'), ('h', 'li'), ('h', 'b'), ('b', 'h'),
           ('ii', 'u'), ('u', 'ii'), ('Us', 'iis'), ('U', 'ii'), ('iv', 'w'), ('vv', 'w'), ('n', 'u'),
           ('u', 'n'), ('il', 'ill'), ('l', 'll'), ('f', 's'), ('s', 'f'), ('cl', 'd'), ('d', 'cl'),
           ('a', 'ä'), ('o', 'ö'), ('u', 'ü'), ('ss', 'ß'), ('a', 'à'), ('e', 'é'), ('e', 'è'),
           ('a', 'e'), ('o', 'e'), ('o', 'c'), ('c', 'o'), ('r', 'n'), ('n', 'r'), ('1', 'l'), ('0', 'o')]
# 外文段的提示词（单个斜体外文词前面常见）
CUE = {'vulgate', 'latin', 'german', 'french', 'dutch', 'luther', 'jerome', 'calvin', 'vitringa', 'cocceius',
       'grotius', 'gesenius', 'ewald', 'hitzig', 'knobel', 'umbreit', 'rosenmüller', 'augusti', 'castalio',
       'junius', 'montanus', 'clericus', 'maurer', 'hendewerk', 'version', 'renders', 'translates',
       'translated', 'paraphrase', 'explains', 'has', 'reads', 'says', 'calls', 'expression', 'phrase',
       'de', 'dewette', 'drechsler', 'michaelis', 'schmidius', 'forerius', 'vatablus', 'munster'}
LANGS = ('lat', 'deu', 'fra', 'ita')


def wordlist(lang):
    """tesseract 模型词典 → 词表（小写）。导出一次缓存。"""
    out = CACHE / f'{lang}.words'
    if not out.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        subprocess.run(['combine_tessdata', '-u', str(TESSDATA / f'{lang}.traineddata'), str(CACHE / f'{lang}.')],
                       check=True, capture_output=True)
        subprocess.run(['dawg2wordlist', str(CACHE / f'{lang}.lstm-unicharset'),
                        str(CACHE / f'{lang}.lstm-word-dawg'), str(out)], check=True, capture_output=True)
    return {w.strip().lower() for w in open(out, encoding='utf-8') if w.strip()}


def variants(w):
    """单处形近替换得到的所有候选写法"""
    for a, b in CONFUSE:
        i = w.find(a)
        while i >= 0:
            yield w[:i] + b + w[i + len(a):]
            i = w.find(a, i + 1)


def chapter_lines(ch):
    t = (PUB / f'{ch}.md').read_text(encoding='utf-8').split('\n---\n', 1)[1]
    return t.split('\n')


# ───────────────────────── A. 拉丁 / 德 / 法 ─────────────────────────

def italic_segments(line):
    """→ [(是否斜体, 片段)]；* 成对切分（发布页的斜体标记）"""
    parts = line.split('*')
    return [(i % 2 == 1, s) for i, s in enumerate(parts)]


def detect_foreign(ch, lex, eng):
    out = []
    page = '?'
    for ln, line in enumerate(chapter_lines(ch), 1):
        pm = re.findall(r'<!-- PAGE (\d+) -->', line)
        if pm:
            page = pm[-1]
        flat = strip_markup(line)
        toks = TOKEN.findall(flat)
        cores = []
        for t in toks:
            m = CORE.match(t)
            cores.append((m.group(1) if m else t).strip("'’"))

        def lang_of(c):
            low = c.lower()
            if not re.fullmatch(r"[A-Za-zÀ-ÿ]+", c) or len(c) < 2:
                return set()
            return {l for l in LANGS if low in lex[l]}

        def is_eng(c):
            return known(re.sub(r"'s$", '', c.lower()), eng)

        # 外文证据：在某外文词表里、不是英文词、≥3 字母
        evid = [bool(lang_of(c)) and not is_eng(c) and len(c) >= 3 for c in cores]
        # 斜体区间：按 token 是否落在 *…* 里
        it, inside = [], False
        for t in toks:
            n = t.count('*')
            start_in = inside or t.startswith('*') or t.startswith('(*')
            it.append(start_in)
            if n % 2:
                inside = not inside
        # 斜体连续段
        spans, cur = [], []
        for i, flag in enumerate(it):
            if flag:
                cur.append(i)
            elif cur:
                spans.append(cur)
                cur = []
        if cur:
            spans.append(cur)
        for span in spans:
            words = [i for i in span if re.search(r'[A-Za-z]', cores[i])]
            if not words:
                continue
            ev = [i for i in words if evid[i]]
            if len(words) >= 2:
                foreign = len(ev) >= 2 or (len(ev) == 1 and len(words) <= 3)
            else:
                pre = {re.sub(r'\W', '', t.lower()) for t in toks[max(0, words[0] - 4):words[0]]}
                foreign = bool(ev) or (bool(pre & CUE) and not is_eng(cores[words[0]]))
            if not foreign:
                continue
            langs = collections.Counter(l for i in ev for l in lang_of(cores[i]))
            for i in words:
                c = cores[i]
                if not re.fullmatch(r"[A-Za-zÀ-ÿ]+", c) or (c[0].isupper() and len(c) > 3 and i != words[0]):
                    if not re.fullmatch(r"[A-Za-zÀ-ÿ]+", c) and re.search(r'[A-Za-z]', c) \
                            and not re.fullmatch(r"[A-Za-zÀ-ÿ'’-]+", c):
                        out.append((ch, page, ln, toks[i], 'lat-odd', i))
                    continue
                low = c.lower()
                if lang_of(c):
                    # 本身是外文词；但若形近改一处后是**更像这一段语言**的词、本身又不在主语言里，也列
                    main = langs.most_common(1)[0][0] if langs else 'lat'
                    if low not in lex[main]:
                        hit = next((v for v in variants(low) if v in lex[main]), None)
                        if hit:
                            out.append((ch, page, ln, toks[i], f'{main}-variant:{hit}', i))
                    continue
                if is_eng(c):
                    # 外文段里冒出来的英文常用短词（in Us magnopere）：形近改一处是纯外文词才列
                    if len(words) >= 2 and len(ev) >= 2:
                        main = langs.most_common(1)[0][0] if langs else 'lat'
                        hit = next((v for v in variants(low) if len(v) >= 3 and v in lex[main]
                                    and not is_eng(v)), None)
                        if hit:
                            out.append((ch, page, ln, toks[i], f'{main}-variant:{hit}', i))
                    continue      # 斜体英文词（译文）不管
                hit = None
                for l in ([langs.most_common(1)[0][0]] if langs else []) + list(LANGS):
                    hit = next((v for v in variants(low) if v in lex[l]), None)
                    if hit:
                        hit = f'{l}-variant:{hit}'
                        break
                out.append((ch, page, ln, toks[i], hit or 'lat-unknown', i))
        # 非斜体的拉丁长句（Saepe mihi mirari …）：连续 ≥3 个外文证据的段里，查夹在中间的非词
        run = []
        for i in range(len(toks) + 1):
            if i < len(toks) and not it[i] and (evid[i] or (run and not is_eng(cores[i]) and lang_of(cores[i]))):
                run.append(i)
                continue
            if len(run) >= 3:
                lo, hi = run[0], run[-1]
                for j in range(lo, min(hi + 2, len(toks))):
                    c = cores[j]
                    if it[j] or not re.fullmatch(r"[a-zà-ÿ]+", c) or lang_of(c):
                        continue
                    hit = next((f'{l}-variant:{v}' for l in LANGS for v in variants(c) if v in lex[l]), None)
                    if hit or not is_eng(c):
                        out.append((ch, page, ln, toks[j], hit or 'lat-unknown', j))
            run = []
    rows = []
    for ch_, page, ln, tok, kind, i in out:
        toks = TOKEN.findall(strip_markup(chapter_lines(ch_)[ln - 1]))
        rows.append((ch_, page, ln, tok, kind, toks[i - 1] if i else '', toks[i + 1] if i + 1 < len(toks) else '',
                     ' '.join(toks[max(0, i - 7):i + 6])))
    return rows


# ───────────────────────── B. 希伯来：与附近经文差一个字母 ─────────────────────────

def edit1(a, b):
    """a、b 只差一处替换 / 增删一个字母"""
    if a == b:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) == 1
    if abs(len(a) - len(b)) != 1:
        return False
    s, l = (a, b) if len(a) < len(b) else (b, a)
    return any(l[:i] + l[i + 1:] == s for i in range(len(l)))


def detect_hebrew(ch, V, forms):
    out = []
    page, verse = '?', 0
    chap_words = {c for (cc, _), ws in V.items() if cc == ch for _, c in ws}
    # 本章注释里每个希伯来辅音串出现几次。亚历山大讨论的词会反复提；
    # OCR 错一个字母的那一处是孤例（27 章 עפו 1 次，而 ענו 本章出现 3 次）
    body = '\n'.join(chapter_lines(ch))
    seen = collections.Counter(cons(w) for w in HEBTOK.findall(body) for w in re.split('\u05BE', w))
    for ln, line in enumerate(chapter_lines(ch), 1):
        pm = re.findall(r'<!-- PAGE (\d+) -->', line)
        if pm:
            page = pm[-1]
        a = ANCHOR.search(line)
        if a:
            verse = int(a.group(2))
        near = {}
        for v in range(verse - WINDOW, verse + WINDOW + 1):
            for f, c in V.get((ch, v), []):
                near.setdefault(c, f)
        flat = strip_markup(line)
        toks = TOKEN.findall(flat)
        for i, t in enumerate(toks):
            if not re.search(r'[א-ת]', t):
                continue
            for piece in re.split(r'[־]', t):
                c = cons(piece)
                if len(c) < 2 or c in near or c in chap_words:
                    continue
                if len(c) >= 3 and c[0] in 'ובכלמהש' and (c[1:] in near or c[1:] in chap_words):
                    continue
                cand = sorted({w for w in near if len(w) >= 2 and edit1(c, w)}, key=lambda w: -len(w))
                if not cand or seen[c] != 1 or max(seen[w] for w in cand) < 2:
                    continue      # 回测：不加这道，4 章 55 条只中 2 条；加了 7 条中 1 条
                # 正文这个词在全部 39 卷里都没有 → 更可疑；有 → 也可能是别卷引文，照样列，分档
                grade = 'heb-1edit' if c not in forms else 'heb-1edit-real'
                out.append((ch, page, ln, t, f'{grade}:{"/".join(cand[:3])}', toks[i - 1] if i else '',
                            toks[i + 1] if i + 1 < len(toks) else '', ' '.join(toks[max(0, i - 7):i + 6])))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapters')
    ap.add_argument('--only', choices=('foreign', 'hebrew'))
    a = ap.parse_args()
    chs = [int(x) for x in a.chapters.split(',')] if a.chapters else list(range(1, 67))
    rows = []
    if a.only != 'hebrew':
        lex = {l: wordlist(l) for l in LANGS}
        # 「英文」只认两家都收的常用词：tesseract 英文词典混进了 zum / iis / est，
        # 系统 web2 又收了大量冷僻拉丁词形，单用哪家都会把外文段判成英文
        eng = wordlist('eng') & {w.strip().lower() for w in open('/usr/share/dict/words', encoding='latin-1')}
        for ch in chs:
            rows += detect_foreign(ch, lex, eng)
    if a.only != 'foreign':
        V = load_wlc()
        forms = {cons(l) for l in open(FORMS, encoding='utf-8') if not l.startswith('#')}
        for ch in chs:
            rows += detect_hebrew(ch, V, forms)
    seen = set()
    for r in rows:
        k = (r[0], r[2], r[3])
        if k in seen:
            continue
        seen.add(k)
        print('\t'.join(map(str, r)))
    print('#', collections.Counter(r[4].split(':')[0] for r in rows), file=sys.stderr)


if __name__ == '__main__':
    main()
