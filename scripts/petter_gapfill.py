#!/usr/bin/env python3
"""佩特《马可福音注释》缺字 → 语料自证候选（old-book-ocr 第 ① 层），本地运行，不看图、不耗模型额度。

    python3 scripts/petter_gapfill.py            # 试跑：分档统计 + 抽样
    python3 scripts/petter_gapfill.py --write    # 写 gap_corpus.tsv

判据照搬 hutcheson_gapfill.judge：缺字词按已知字母成模式，在「本书语料 ∪ 系统词典 web2」里找候选；
唯一候选且本书 ≥3 次 → lex；多候选时前后邻词三元搭配唯一且 ≥2 次 → ctx；缺整词／含数字／非纯字母／
已知字母 < 3 一律不碰。一组缺字含几个词时逐词判，任一词判不了整组不出。

产物 gap_corpus.tsv：gid / 读法 / 证据 / 与看图判读（gap_review.tsv）是否一致。
**全部是推断，待用户同意**（memory feedback_no_guess_inference_needs_approval）：同意的行抄进 gap_approved.tsv。
看图读法与语料读法一致的，两层证据互证，列在前面供整批过目。
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import petter_common as pc  # noqa: E402

WEB2 = Path('/usr/share/dict/web2')
PUNCT = '.,;:?!()[]\'"*'
OUT = pc.RAW / 'gap_corpus.tsv'


def plain(md):
    md = re.sub(r'<span class="pt-(?:pb|mark)"[^>]*>(?:[^<]*)</span>', ' ', md)
    md = re.sub(r'<[^>]+>', ' ', md)
    return md.replace('*', '')


def build_corpus():
    freq, forms, tri = collections.Counter(), collections.defaultdict(collections.Counter), collections.Counter()
    for slug in pc.order()['order']:
        words = re.findall(r"[A-Za-z]+|\S", plain(pc.read_src(slug)))
        al = [w for w in words]
        for w in al:
            if w.isalpha():
                freq[w.lower()] += 1
                forms[w.lower()][w] += 1
        for k in range(len(al) - 2):
            a, b, c = al[k:k + 3]
            if a.isalpha() and b.isalpha() and c.isalpha():
                tri[(a.lower(), b.lower(), c.lower())] += 1
    return freq, forms, tri


def load_lex():
    by_len = collections.defaultdict(set)
    if WEB2.exists():
        for w in WEB2.read_text(encoding='utf-8').split():
            if w.islower():
                by_len[len(w)].add(w)
    return by_len


def judge(word, lw, rw, freq, forms, tri, lex):
    if re.search(r'〈|▪', word):
        return None, 'skip:非字母缺口'
    lead = len(word) - len(word.lstrip(PUNCT))
    trail = len(word) - len(word.rstrip(PUNCT))
    core = word[lead:len(word) - trail] if trail else word[lead:]
    if '•' not in core:
        return word, 'keep'
    if re.search(r'\d', core):
        return None, 'skip:含数字'
    if not re.fullmatch(r'[A-Za-zƲ•\'-]+', core) or "'" in core or '-' in core:
        return None, 'skip:非纯字母'
    if len(re.sub('•', '', core)) < 3:
        return None, 'skip:已知字母<3'
    core_l = core.replace('Ʋ', 'U')
    rx = re.compile('^' + ''.join('.' if c == '•' else re.escape(c.lower()) for c in core_l) + '$')
    cands = sorted({w for w in freq if rx.match(w)} | {w for w in lex.get(len(core), ()) if rx.match(w)})
    if not cands:
        return None, 'none:无候选'
    pick = ev = None
    if len(cands) == 1 and freq[cands[0]] >= 3:
        pick, ev = cands[0], f'lex:{cands[0]}×{freq[cands[0]]}'
    elif len(cands) == 1:
        return None, f'rare:{cands[0]}×{freq[cands[0]]}'
    else:
        if lw and rw:
            hits = [(c, tri[(lw, c, rw)]) for c in cands if tri[(lw, c, rw)]]
            if len(hits) == 1 and hits[0][1] >= 2:
                pick, ev = hits[0][0], f'ctx:{lw} {hits[0][0]} {rw}×{hits[0][1]}'
        if not pick:
            return None, 'ambig:' + '/'.join(f'{c}×{freq[c]}' for c in sorted(cands, key=lambda c: -freq[c])[:4])
    out = []
    for i, c in enumerate(core):
        if c != '•':
            out.append(c)
            continue
        ch = pick[i]
        if i == 0:
            best = forms[pick].most_common(1)
            ch = best[0][0][0] if best else ch
        elif core[:i].isupper() and len(core) > 1 and core.replace('•', '').isupper():
            ch = ch.upper()
        out.append(ch)
    return word[:lead] + ''.join(out) + (word[len(word) - trail:] if trail else ''), ev


def ocr_reads():
    """本地 tesseract（petter_bim_ocr，约 400 ppi）在缺字定位处读出的词：作为第二道证据，在多候选里挑。"""
    f = pc.RAW / 'witness_locs.json'
    if not f.exists():
        return {}
    return {r['gid']: r['bim'].get('read', '') for r in json.loads(f.read_text(encoding='utf-8'))
            if 'bim' in r and not r['bim'].get('est')}


def ocr_pick(word, ocr, freq, lex, forms):
    """多候选时：OCR 读到的词里有一个与录入本字母模式吻合（长 s 作 f、u/v、i/j 折平）且是本书语料词，取它。"""
    lead = len(word) - len(word.lstrip(PUNCT))
    trail = len(word) - len(word.rstrip(PUNCT))
    core = (word[lead:len(word) - trail] if trail else word[lead:]).replace('Ʋ', 'U')
    if '•' not in core or not re.fullmatch(r'[A-Za-z•]+', core) or len(re.sub('•', '', core)) < 2:
        return None
    rx = re.compile('^' + ''.join('.' if c == '•' else re.escape(c.lower()) for c in core) + '$')
    hits = set()
    for t in re.findall(r'[A-Za-zſ]+', ocr):
        t2 = t.lower().replace('ſ', 's')
        for v in {t2, t2.replace('f', 's')}:
            if rx.match(v) and freq[v] >= 3:
                hits.add(v)
    if len(hits) != 1:
        return None
    pick = hits.pop()
    out = ''.join(pick[i] if c == '•' else c for i, c in enumerate(core))
    if core[0] == '•':                       # 首字母大小写按本书最常见形态
        best = forms[pick].most_common(1)
        if best:
            out = best[0][0][0] + out[1:]
    return word[:lead] + out + (word[len(word) - trail:] if trail else ''), f'ocr:{pick}×{freq[pick]}'


def review():
    d = {}
    f = pc.RAW / 'gap_review.tsv'
    for ln in f.read_text(encoding='utf-8').splitlines() if f.exists() else []:
        if ln and ln[0].isdigit():
            x = ln.split('\t')
            d[int(x[0])] = x[1]
    return d


def norm(s):
    return re.sub(r'[^a-z]', '', s.lower().replace('ſ', 's'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    a = ap.parse_args()
    freq, forms, tri = build_corpus()
    lex = load_lex()
    sites = json.loads((pc.RAW / 'gap_sites.json').read_text(encoding='utf-8'))
    rv = review()
    ocr = ocr_reads()
    rows, tally = [], collections.Counter()
    for s in sites:
        ws = s['tcp'].split(' ')
        lw = norm(s['left'][-1]) if s['left'] else ''
        rw = norm(s['right'][0]) if s['right'] else ''
        out, evs, ok = [], [], True
        for k, w in enumerate(ws):
            l2 = lw if k == 0 else norm(ws[k - 1])
            r2 = rw if k == len(ws) - 1 else norm(ws[k + 1])
            fx, ev = judge(w, l2, r2, freq, forms, tri, lex)
            if fx is None and ev.startswith(('ambig', 'rare', 'skip:已知字母')) and s['gid'] in ocr:
                r = ocr_pick(w, ocr[s['gid']], freq, lex, forms)
                if r:
                    fx, ev = r
            if fx is None:
                ok = False
                tally[ev.split(':')[0]] += 1
                break
            out.append(fx)
            if ev != 'keep':
                evs.append(ev)
        if not ok:
            continue
        reading = ' '.join(out)
        img = rv.get(s['gid'])
        if img is None:
            agree = '未看图'
        else:
            iv = img[2:] if img.startswith('P:') else img
            agree = '一致' if norm(iv) == norm(reading) else f'不一致:看图作 {img}'
        tally['可判'] += 1
        tally[agree.split(':')[0]] += 1
        rows.append((s['gid'], reading, '; '.join(evs), agree, s['slug'], s['tcp']))
    print('  '.join(f'{k} {v}' for k, v in tally.most_common()), file=sys.stderr)
    for r in rows[::max(1, len(rows) // 20)]:
        print(f'  #{r[0]} {r[5]!r} → {r[1]!r}  [{r[2]}] {r[3]}', file=sys.stderr)
    bad = [r for r in rows if r[3].startswith('不一致')]
    print(f'不一致 {len(bad)}：', file=sys.stderr)
    for r in bad[:40]:
        print(f'  #{r[0]} {r[5]!r} 语料 {r[1]!r} / {r[3]}', file=sys.stderr)
    if a.write:
        rows.sort(key=lambda r: ({'一致': 0, '未看图': 1}.get(r[3], 2), r[0]))
        OUT.write_text('# gid\t语料读法\t证据\t与看图判读\tslug\t录入本原样\n' +
                       ''.join('\t'.join(map(str, r)) + '\n' for r in rows), encoding='utf-8')
        print(f'写入 {len(rows)} 行 → {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
