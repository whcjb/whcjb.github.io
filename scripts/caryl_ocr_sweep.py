#!/usr/bin/env python3
"""卡里尔缺部 OCR：抽章实读后的全书同类清理（old-book-ocr §4.5 第 4 步）。排在 caryl_ocr_manual.py 之后（人工改正表是照上下文纠错之后的文字记的，清理若排在前面会先改掉原串的一部分，改正表就对不上）。

    /usr/bin/python3 scripts/caryl_ocr_sweep.py              # 试跑：每条规则命中数与样例
    /usr/bin/python3 scripts/caryl_ocr_sweep.py --apply      # 落到各部 fixed/；改动记 caryl_raw/job_ocr/sweep.tsv

规则来自 2026-11-25 抽读第 9 部 31:7–8 一段（25 页，记错 235 条，平均每页约 12 处）。每条都只在纯文本上匹配，
不跨标签（旁注、页码锚点、存疑标记、经文框标签都不碰）：

  split   词中断开：相邻两截拼起来是本书 ≥ 5 次的词，且至少一截不是词，或后一截是常见后缀
          （direct ly、end lesse、out ward、unjust ly、oc asion）
  job     Job 读坏：Tob/fob/Sob/Jub/Iob/Jeb（含所有格 s）→ Job；小写 job 前面不是 a/the/his 时 → Job
  way     冠词、物主代词、形容词之后的 may/nay/var/mav → way（「the may」「good may」）；不碰 that/this/which may（情态动词）
  modal   人称代词之后的 mill/mil → will，mould → would，mas/vas → was，vere/mere → were
  saith   faith 前是人名（Job、David、God、Christ、the Lord…）或后是人名、he、the Lord → saith（长 s 读成 f）
  of      独立的 ef → of；er → or（两边都是英文词）
  tis     'Tis 开引号读错：「"Tis」「“ Tis」「“Tis」→「'Tis」
  isa     书卷缩写读坏：I/a. → Isa.，P/al. → Psal.，Plal. → Psal.
  ——第 2 轮（第 9 部 31:9–12，44 页）补：ofx（ofit→of it）、Tis 撇号读丢、fin→sin、fh-→sh-、bis/bim→his/him、
          代词后 hill→will、mould not→would not、(I Cor.→(1 Cor.、(Ter.→(Jer.、(Hof.→(Hos.、(faith the text→(saith
  head    漏进正文的页眉（「Chap. 31. An Exposition upon the Booke of JOB. Vers. 7.」）删掉
"""
import argparse
import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import caryl_ocr_ctx as C  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
PARTS = ('p4', 'p6', 'p82', 'p9')
UNI = C.UNI
SUFFIX = {'ly', 'lesse', 'nesse', 'ward', 'wards', 'ing', 'ed', 'ment', 'ness', 'ful', 'full', 'ous'}
NAMES = r'(?:Job|David|God|Christ|Moses|Paul|Peter|Solomon|Isaiah|Jeremiah|Elihu|Eliphaz|Bildad|Zophar|the Lord|the Prophet|the Apostle|he|she|they|hee)'
DETS = r'(?:the|a|good|his|my|their|our|your|her|its|narrow|right|wrong|same|thy|thine|mine|old|new|plaine|straight|evill|crooked)'


def rules():
    R = []
    # job
    R.append(('job', re.compile(r'\b(?:Tob|fob|Fob|Sob|Jub|Iob|Jeb|Ieb|lob|Iub)(\'?s?)\b'), lambda m: 'Job' + m.group(1)))
    R.append(('job', re.compile(r'(?<!\ba )(?<!\bthe )(?<!\bhis )\bjob(\'?s?)\b'), lambda m: 'Job' + m.group(1)))
    # way
    R.append(('way', re.compile(rf'\b({DETS}) (?:may|nay|var|mav)\b(?! be\b)'), lambda m: m.group(1) + ' way'))
    R.append(('way', re.compile(r'\b(out of (?:the|that|his|their|my) )(?:may|nay|man|var)\b'), lambda m: m.group(1) + 'way'))
    # modal
    R.append(('modal', re.compile(r'\b(I|we|wee|he|hee|they|ye|yee|you|thou|she|it|who|which) (mill|mil|mould|mas|vas|vere|mere)\b'),
              lambda m: m.group(1) + ' ' + {'mill': 'will', 'mil': 'will', 'mould': 'would', 'mas': 'was', 'vas': 'was',
                                            'vere': 'were', 'mere': 'were'}[m.group(2)]))
    # saith
    R.append(('saith', re.compile(rf'\b({NAMES}) faith\b'), lambda m: m.group(1) + ' saith'))
    R.append(('saith', re.compile(rf'([,;(] ?)faith (?={NAMES}\b)'), lambda m: m.group(1) + 'saith '))
    # of / or
    R.append(('of', re.compile(r'(?<=[a-z] )ef(?= [a-z])'), lambda m: 'of'))
    R.append(('of', re.compile(r'(?<=[a-z] )er(?= [a-z])'), lambda m: 'or'))
    # 'Tis
    R.append(('tis', re.compile(r'["“”]\s?Tis\b'), lambda m: "'Tis"))
    # 书卷缩写
    R.append(('isa', re.compile(r'\bI/a\.'), lambda m: 'Isa.'))
    R.append(('isa', re.compile(r'\bP[/l]al\.'), lambda m: 'Psal.'))
    # —— 第 2 轮（2026-11-25，第 9 部 31:9–12 实读 44 页）补的几类
    # of 与后词粘连：ofit、ofthe、ofthis…（书里没有这些词）
    R.append(('ofx', re.compile(r'\bof(it|the|this|that|a|an|his|her|their|them|him|God|my|our|your)\b'), lambda m: 'of ' + m.group(1)))
    # 'Tis 撇号读丢：句中独立的 Tis / tis（排在上面 tis 规则之后，引号形的已归一）
    R.append(('tis', re.compile(r'(?<![’\'‘"“\w])Tis\b'), lambda m: "'Tis"))
    R.append(('tis', re.compile(r"(?<=\s)['’‘] (?=tis\b)"), lambda m: '’'))
    R.append(('tis', re.compile(r'((?:[,;:(]|\b(?:and|but|so|when|thus|as|yet|because|that|for|or|know|here|therefore)) )tis\b', re.I),
              lambda m: m.group(1) + "’tis"))           # 「wait tis my change come」是 till，不碰
    # 长 s 读成 f：fin/finne/finner…（本书这几部讲不到鱼鳍）；fhall/fhould/fhew… → sh-
    R.append(('fin', re.compile(r'\bfin(|ne|s|nes|full|fully|fulnesse|fullnesse|ner|ners|ning|ned)\b'), lambda m: 'sin' + m.group(1)))
    R.append(('fh', re.compile(r'\bfh(?=[a-z])'), lambda m: 'sh'))
    # bis/bim → his/him（「a five-fold bis」那一处另说，不碰）
    R.append(('bis', re.compile(r'(?<!fold )\bbis\b'), lambda m: 'his'))
    R.append(('bis', re.compile(r'\bbim\b'), lambda m: 'him'))
    # 人称代词、God 之后的 hill → will；mould not/be/have → would（「dust and mould of the Earth」不动）
    R.append(('modal', re.compile(r'\b(I|he|hee|we|wee|they|ye|yee|you|thou|it|who|God) hill\b'), lambda m: m.group(1) + ' will'))
    R.append(('modal', re.compile(r'\bmould(?= (?:not|be|have)\b)'), lambda m: 'would'))
    # 书卷：(I Cor. → (1 Cor.；(Ter. → (Jer.；(Hof. → (Hos.
    R.append(('isa', re.compile(r'\(I (?=(?:Cor|Tim|Sam|King|Kings|Chron|Pet|Joh|Thes|Thess)\.)'), lambda m: '(1 '))
    R.append(('isa', re.compile(r'\(Ter\.'), lambda m: '(Jer.'))
    R.append(('isa', re.compile(r'\(Hof\.'), lambda m: '(Hos.'))
    # (faith the text / the Evangelist / one … → (saith
    R.append(('saith', re.compile(r'\(faith (?=the |one )'), lambda m: '(saith '))
    # 漏进正文的页眉
    R.append(('head', re.compile(r'\bCha[pn][.,-]?\s?\d{1,2}\.?\s+An Ex\w*\s+u\w*\s+\w+\s+Boo?[sk]\w*\s+\S{1,3}\s?\S{0,3}\s+V\w{2,5}[.,]?\s?\d{0,2}\.?'),
              lambda m: ''))
    return R


RULES = rules()
RE_SPLIT = re.compile(r'\b([A-Za-z]{1,10}) ([a-z]{1,7})\b')


def split_fix(m):
    a, b = m.group(1), m.group(2)
    w = (a + b).lower()
    if UNI.get(w, 0) < 5:
        return None
    if UNI.get(a.lower(), 0) >= 20 and UNI.get(b, 0) >= 20 and b not in SUFFIX:
        return None                          # 两截都是常见词（in deed、a way…）：不合
    if b in ('full', 'ful') and re.search(r'\b(?:a|an|the|his|her|my|thy|our|your|their)\s$', m.string[:m.start()], re.I) \
            and m.string[m.end():m.end() + 3] == ' of':
        return None                          # 「a mind full of Anguish」是名词＋形容词，不是 mindfull（「art mind ful of him」照合）
    if b in SUFFIX or not UNI.get(a.lower(), 0) or not UNI.get(b, 0):
        return a + b
    return None


def sweep_text(pt, log, where):
    """纯文本段落上跑规则；返回新文本。"""
    def sub_split(m):
        r = split_fix(m)
        if r:
            log.append(('split', where, m.group(0), r))
            return r
        return m.group(0)
    for _ in range(3):                       # 匹配会互相吃掉：「and resol ved」先被「and resol」占了，「resol ved」轮不到——迭代到不动点
        new = RE_SPLIT.sub(sub_split, pt)
        if new == pt:
            break
        pt = new
    for name, rx, fn in RULES:
        def rep(m, name=name, fn=fn):
            new = fn(m)
            if new != m.group(0):
                log.append((name, where, m.group(0), new))
            return new
        pt = rx.sub(rep, pt)
    return pt


RE_PB = re.compile(r'<span class="cy-pb"[^>]*></span>')


def is_sig(letters):
    """书帖签名（Ddd、Nnnn、Ccce、KKXK、SES、H h'hh）：2–5 个字母、大写起头、同一字母占六成以上、不是词。"""
    if len(letters) >= 3 and len(set(letters.lower())) == 1 and len(letters) <= 5:
        return True                          # 「t t t」：全小写也算
    if not (2 <= len(letters) <= 5) or not letters[0].isupper():
        return False
    if UNI.get(letters.lower(), 0):
        return False
    return letters.lower().count(letters[0].lower()) / len(letters) >= 0.6


def fix_pagebreaks(md, log, where):
    """页码锚点前：剥掉漏进正文的书帖签名；锚点前是空行、上段没收尾、锚点后小写起头的，并回一段
    （「…He will E e e ⟂ watch dayly」「…the sent-U u u ⟂ forth-light」「…our bodyes afB bb ⟂ ter the resurrection」）。"""
    out, last = [], 0
    for m in RE_PB.finditer(md):
        seg = md[last:m.start()]
        k = len(seg)
        while k and seg[k - 1].isspace():
            k -= 1
        body, gap = seg[:k], seg[k:]
        if not body or (body.endswith('>') and not re.search(r'<span class="cy-ocr"[^>]*>[^<]*</span>$', body)):
            out.append(seg + m.group(0))
            last = m.end()
            continue
        glued = False
        # 末尾往回剥最多 4 个短 token（纯字母／数字，或 cy-ocr 包着的），找像签名的最短后缀
        toks, cut, bb = [], [], body
        while len(toks) < 4:
            mt = re.search(r'(\s?)(<span class="cy-ocr"[^>]*>([^<]{1,6})</span>|[A-Za-z’\'\d]{1,6})$', bb)
            if not mt:
                break
            toks.insert(0, mt.group(3) if mt.group(3) is not None else mt.group(2))
            cut.insert(0, mt.start())
            bb = bb[:mt.start()]
            if not mt.group(1):
                break
        for i in range(len(toks)):
            t0 = toks[i]
            pre = re.match(r'([a-z]+)([A-Z].*)$', t0)                       # 「afB bb」：签名粘在半个词后面
            letters = re.sub(r'[^A-Za-z]', '', (pre.group(2) if pre else t0) + ''.join(toks[i + 1:]))
            if is_sig(letters) and (i > 0 or pre or cut[0] == 0 or body[cut[0]].isspace() or not body[cut[0] - 1].isalpha()):
                start = cut[i]
                keep = ''
                if pre:                      # 留下前半截（连存疑标记一起去掉：签名剥掉后它就是半个正常词）
                    start = cut[i] + (1 if body[cut[i]].isspace() else 0)
                    keep = pre.group(1)
                    glued = True
                log.append(('sig', where, re.sub(r'<[^>]+>', '', body[start:]).strip(), keep))
                body = body[:start].rstrip(' ') + (' ' if keep and body[cut[i]].isspace() else '') + keep
                break
        after = md[m.end():m.end() + 1]
        if '\n\n' in gap and re.search(r'[a-z,;-]$', body) and re.match(r'[a-z]', after) and not body.rstrip().endswith('>'):
            log.append(('pbjoin', where, body[-20:] + '⏎⏎', after))
            gap = '' if glued or body.endswith('-') else ' '
        elif glued:
            gap = '' if '\n\n' not in gap else gap
        out.append(body + gap + m.group(0))
        last = m.end()
    out.append(md[last:])
    return ''.join(out)


def sweep_md(md, log, where):
    """只改标签之间的纯文本片段（不跨标签），旁注 span 整个跳过。"""
    for _ in range(3):                       # 长签名（「H h h h h」）一遍只剥得掉后几截：迭代到不动点
        new = fix_pagebreaks(md, log, where)
        if new == md:
            break
        md = new
    out, last = [], 0
    for m in re.finditer(r'<span class="cy-margin">.*?</span>|<[^>]+>|\{:[^}]*\}', md, re.S):
        out.append(sweep_text(md[last:m.start()], log, where))
        out.append(m.group(0))
        last = m.end()
    out.append(sweep_text(md[last:], log, where))
    return re.sub(r' {2,}', ' ', ''.join(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--show', default='')
    a = ap.parse_args()
    log, outs = [], {}
    for p in PARTS:
        for f in sorted((BASE / p / 'fixed').glob('*.md')):
            outs[f] = sweep_md(f.read_text(encoding='utf-8'), log, f'{p}/{f.stem}')
    c = collections.Counter(x[0] for x in log)
    print('全书同类清理：' + '，'.join(f'{k} {v}' for k, v in c.most_common()), file=sys.stderr)
    for k in c:
        xs = [x for x in log if x[0] == k]
        step = max(1, len(xs) // 12)
        print(f'  [{k}] ' + ' | '.join(f'{x[2]}→{x[3]}' for x in xs[::step][:12]), file=sys.stderr)
    if a.show:
        for x in log:
            if x[0] == a.show:
                print('\t'.join(x))
    if a.apply:
        for f, md in outs.items():
            f.write_text(md, encoding='utf-8')
        (BASE / 'sweep.tsv').write_text(''.join('\t'.join(x) + '\n' for x in log), encoding='utf-8')


if __name__ == '__main__':
    main()
