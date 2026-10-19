#!/usr/bin/env python3
"""以赛亚书希伯来活字乱码 → **闭集选词**换回马所拉文本原词。

9 月那遍 `isaiah_hebrew_ocr.py` 是开集读字：tesseract `heb` 读出什么就落什么，
置信度够才落，于是 3400 多处读不稳的一直以拉丁乱码留在正文里
（14:13 `isi'a-in`、`oitn» p5ii jVi o`），中译照抄（用户 2026-10-19 截图）。

但亚历山大讨论的希伯来词，绝大多数就是**本节经文里的词**（`הַר־מוֹעֵד`）。
这就把问题从「读出这块活字是什么字」换成「这块活字是本节经文里的哪个词」：

    候选 = WLC 本节 ±WINDOW 节的每个词（含去掉 ו/ב/כ/ל/מ/ה/ש 前缀词素的形式、
           带 maqaf 的相邻两词）
    读数 = tesseract heb 对裁图的读数（同 isaiah_hebrew_ocr 的裁图）
    选中 = 辅音骨架等长、至多差一个字母，且前后节里没有第二个同样近的词（见 choose）

**落盘的字全部来自 WLC**（Westminster Leningrad Codex，OSHB 4.20，公有领域，
alexander_raw/isaiah/ref/wlc_Isa.xml），**只落辅音（含 maqaf），不落元音点**：
原书时而带点（14:13 הַר־מוֹעֵד，且只点几处）、时而不带（16:12 יוכל），裁图里的点又
细又常被切掉，判不准「这处印没印点」。补上原书没印的点＝往原书里添东西；
不补只是少一点细节，字不会错。9 月 tesseract 落的那批本来也不带点，口径一致。tesseract 只负责「指」，不负责「写」：读数再糊，
写进正文的也是马所拉文本的正字。指不准（分数低、或前两名太接近）→ 不落。

引自经文之外的希伯来文（金希的注释原话、别卷经文、词根）不在闭集里，
这一步救不了，留给后面标〔希伯来文〕。

用法：
    python3 scripts/isaiah_hebrew_closedset.py --pages 342-370   # 试一章
    python3 scripts/isaiah_hebrew_closedset.py                   # 全书
输出 alexander_raw/isaiah/hebrew_closedset.tsv（与 hebrew_ocr.tsv 同列，
script 列写 heb-wlc，reading 列是 WLC 原词，conf 列是相似度×100），
由 isaiah_apply_hebrew.py 按位置落盘。
"""
import argparse
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from pathlib import Path

import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent))
import isaiah_hebrew_ocr as H                      # noqa: E402  裁图、切词、tesseract 都复用
from alexander_lexicon import build                # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WLC = ROOT / 'alexander_raw/isaiah/ref/wlc_Isa.xml'
PUB = ROOT / 'alexander/isaiah'
OUT = ROOT / 'alexander_raw/isaiah/hebrew_closedset.tsv'
OSIS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
ACC = re.compile(r'[֑-ֽ֯׀׃-׆]')   # 吟诵符、meteg、标点
PREFIX = set('ובכלמהש')
WINDOW = 3          # 本节前后各几节
# 节的定位：发布页里每节一个锚
ANCHOR = re.compile(r'id="isaiah-(\d+)-(\d+)"')


def bare(s):
    """WLC 写法 → 只留辅音与 maqaf（落盘用，见文件头）"""
    return re.sub(r'[^\u05D0-\u05EA\u05BE]', '', s)


def cons(s):
    return re.sub(r'[^א-ת]', '', s)


def load_wlc():
    """(章, 节) → [(显示形式, 辅音骨架)]，含去前缀形式与 maqaf 连写两词"""
    V = {}
    for v in ET.parse(WLC).iter(OSIS + 'verse'):
        _, c, n = v.get('osisID').split('.')
        words = []
        for w in v.iter(OSIS + 'w'):
            parts = ACC.sub('', ''.join(w.itertext())).split('/')
            words.append(parts)
        forms = []
        for k, parts in enumerate(words):
            full = ''.join(parts)
            forms.append(full)
            # 只剥前缀：被剥掉的每个词素都是单个辅音的 ו ב כ ל מ ה ש
            for i in range(1, len(parts)):
                if all(len(cons(p)) == 1 and cons(p) in PREFIX for p in parts[:i]):
                    forms.append(''.join(parts[i:]))
            if k + 1 < len(words):                      # 相邻两词连写（הַר־מוֹעֵד）
                nxt = ''.join(words[k + 1])
                for f in [full] + [''.join(parts[i:]) for i in range(1, len(parts))
                                   if all(len(cons(p)) == 1 and cons(p) in PREFIX
                                          for p in parts[:i])]:
                    forms.append(f + '־' + nxt)
        V[(int(c), int(n))] = [(f, cons(f)) for f in dict.fromkeys(forms) if len(cons(f)) >= 2]
    return V


def flat_chapter(ch):
    """发布页 → (纯文本, [(位置, 节)])：剥标签，记下每个节锚落在纯文本的哪里"""
    t = (PUB / f'{ch}.md').read_text(encoding='utf-8')
    t = t.split('\n---\n', 1)[1] if t.startswith('---') else t
    out, marks, i = [], [], 0
    for m in re.finditer(r'<[^>]+>|[^<]+', t):
        s = m.group(0)
        if s.startswith('<'):
            a = ANCHOR.search(s)
            if a:
                marks.append((sum(len(x) for x in out), int(a.group(2))))
            continue
        out.append(s)
    return re.sub(r'\s+', ' ', ''.join(out)), marks


_FLAT = {}


def locate(job):
    """在发布页里找到这处乱码 → (章, 节)；找不到 → None"""
    for ch in job['chapters']:
        if ch not in _FLAT:
            _FLAT[ch] = flat_chapter(ch)
        text, marks = _FLAT[ch]
        # 前文锚取后 3 个词：乱码本身可能已被 repair 改过一两个字符
        tail = ' '.join(job.get('ctx', job['before']).split()[-3:])
        if len(tail) < 8:
            continue
        hits = [m.start() for m in re.finditer(re.escape(tail), text)]
        if len(hits) != 1:
            continue
        pos = hits[0]
        v = max([vv for p, vv in marks if p <= pos], default=None)
        if v:
            return ch, v
    return None


def lev(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def choose(reading, ch, v, V):
    """**只认几乎一模一样的**：辅音骨架等长、至多差 1 个字母（≤3 个字母的必须全同），
    且本节前后再没有第二个同样够近的词。

    第一版按相似度 ≥0.75 + 领先 0.15 挑，试跑第 14 章就看出两个坑：
    亚历山大常引去掉词尾的形式（אַלְמְנוֹת），经文里是 אַלְמְנוֹתָיו，按相似度挑会把
    带词尾的经文形式写进去——等于改了原书；希腊文乱码被 heb 模型硬读成
    「500008 ל6ון 006」，也凑得上 לְבָנוֹן。宁可少落，不能写错。
    """
    # 只数字母：元音点也在 \u0590 段，算进去会把带点的读数（עָבְדָה）误判成「夹杂」
    rh = [c for c in reading if '\u05D0' <= c <= '\u05EA' or (c.isascii() and c.isalnum())]
    rc = cons(reading)
    # 读数里非希伯来的字母数字超过两成 → 模型在硬凑（多半是希腊文或英文），不选
    if len(rc) < 2 or (len(rh) - len(rc)) > 0.2 * len(rh):
        return None
    tol = 0 if len(rc) <= 3 else 1
    near = {}
    for vv in range(v - WINDOW, v + WINDOW + 1):
        for f, c in V.get((ch, vv), []):
            if len(c) == len(rc):
                d = lev(rc, c)
                if d <= tol:
                    near.setdefault(c, (d, f))
    if not near:
        return dict(form='', sim=0, margin=0, ok=False)
    best = min(near.items(), key=lambda kv: kv[1][0])
    rivals = [c for c, (d, _) in near.items() if c != best[0] and d <= best[1][0]]
    return dict(form=best[1][1], sim=1 - best[1][0] / len(rc), margin=0 if rivals else 1,
                ok=not rivals)


# 差一个字母时只认 tesseract 在本书上**实测过**的形近混淆（读数字母 → 实为）：
# 全书第一遍 252 处差一字母里出现 ≥4 次的，加上公认的形近对。其余的差异可能是
# 原书真印了另一个字母（异文讨论），不落。
CONFUSE = {('ר', 'י'), ('ג', 'ו'), ('ט', 'ש'), ('ל', 'י'), ('צ', 'ע'), ('י', 'ו'), ('ר', 'ד'),
           ('ד', 'י'), ('ח', 'ה'), ('ז', 'ו')}
for a, b in [('ה', 'ת'), ('ה', 'ח'), ('ב', 'כ'), ('כ', 'פ'), ('ס', 'ם'), ('ד', 'ר'), ('ו', 'י'), ('ן', 'ו')]:
    CONFUSE |= {(a, b), (b, a)}
# 异文 / 别读 / 标音讨论的上下文：作者引的恰恰是**与马所拉文本不同**的读法
# （7:11「Symmachus seem to have read שְׁאֹלָה」），连辅音全同也可能元音不同——一律不落。
VARIANT = re.compile(r'\b(?:read|reads|reading|readings|MSS?|Sept|Septuagint|Vulg|Vulgate|Keri|Kethib|Kri|'
                     r'Chald|Chaldee|Syr|Syriac|Targum|Aq|Aquila|Sym|Symm|Symmachus|Theod|Theodotion|point|'
                     r'points|pointed|pointing|punctuat\w*|vowels?|vocali\w+|instead|conjectur\w*|emend\w*|'
                     r'variant|Masor\w*|Masoretic|text|changes?|changed|substitut\w*)\b', re.I)


def safe(before, after, tesseract, form):
    """闭集选中之后的闸。只落辅音，所以辅音全同的条目即使在异文讨论里也照落——
    落下的就是原书印的那几个字母；差一个字母的才可能是原书真印了别的字母，
    这类在异文上下文里不落，其余也只认实测形近混淆。"""
    a, b = cons(tesseract), cons(form)
    if a == b:
        return True
    if VARIANT.search(before + ' ' + after):
        return False
    diff = [(p, q) for p, q in zip(a, b) if p != q]
    fin = str.maketrans('ךםןףץ', 'כמנפצ')
    return len(diff) == 1 and (diff[0] in CONFUSE or
                              (diff[0][0].translate(fin), diff[0][1].translate(fin)) in CONFUSE
                              or diff[0][0].translate(fin) == diff[0][1].translate(fin))


def run(page_range, chapters):
    lex = build()
    V = load_wlc()
    jobs = []
    for vol in ('v1', 'v2'):
        doc = fitz.open(H.PDF[vol])
        idx = 0
        for _, el in ET.iterparse(H.XML[vol], events=('end',)):
            if el.tag != H.NS + 'page':
                continue
            idx += 1
            if not (page_range[vol][0] <= idx <= page_range[vol][1]):
                el.clear()
                continue
            pw, ph = int(el.get('width')), int(el.get('height'))
            page = doc[idx - 1]
            sx, sy = page.rect.width / pw, page.rect.height / ph
            prev_hyphen = False
            prev_tail = ''
            for line in el.iter(H.NS + 'line'):
                toks = H.line_tokens(line)
                # 行末断词的两个半截不是活字残渣（`uni-` ⏎ `form`、`pecu-` ⏎ `liar`）
                skip = set()
                line_hyphen = bool(toks) and toks[-1][0].rstrip('\'"').endswith('-')
                if line_hyphen:
                    skip.add(len(toks) - 1)
                if prev_hyphen and toks:
                    skip.add(0)
                prev_hyphen = line_hyphen
                runbuf = []
                for k, (txt, box) in enumerate(toks + [(None, None)]):
                    if txt is not None and runbuf and not any(c.isalnum() for c in txt):
                        runbuf.append((txt, box))
                        continue
                    if (txt is not None and k not in skip and H.looks_residue(txt, lex)
                            and len(runbuf) < 4):
                        runbuf.append((txt, box))
                        continue
                    if runbuf:
                        j = H.crop(runbuf, toks, page, sx, sy, vol, idx)
                        if j:
                            j['chapters'] = chapters
                            # 定位到节时才接上一行末尾（行首的乱码在本行没有前文）；
                            # 落盘的锚 before 仍只取同一行——原书正文与脚注交错，
                            # 「上一行」可能是另一栏，接进锚里正文就找不到了（第一遍 392 条落空）
                            j['ctx'] = (prev_tail + ' ' + j['before']).strip()
                            jobs.append(j)
                        runbuf = []
                prev_tail = ' '.join(t for t, _ in toks[-4:])
            el.clear()
        doc.close()

    def work(j):
        heb, ch_ = H.ocr(j['png'], 'heb')
        Path(j['png']).unlink(missing_ok=True)
        loc = locate(j)
        pick = choose(heb, *loc, V) if loc and len(H.HEBREW.findall(heb)) >= 2 else None
        return j, heb, ch_, loc, pick

    with ThreadPoolExecutor(8) as pool:
        res = list(pool.map(work, jobs))
    rows, stat = [], {'候选': len(res), '读出希伯来字母': 0, '定位到节': 0, '选中': 0}
    for j, heb, conf, loc, pick in res:
        if len(H.HEBREW.findall(heb)) >= 2:
            stat['读出希伯来字母'] += 1
        if loc:
            stat['定位到节'] += 1
        if pick and pick['ok'] and not safe(j['before'], j['after'], heb, pick['form']):
            stat['闸下'] = stat.get('闸下', 0) + 1
            continue
        if pick and pick['ok']:
            stat['选中'] += 1
            rows.append((j['vol'], j['scan_page'], j['before'], j['garbage'], j['after'],
                         # conf 写 95：闭集选中本身就是证据；isaiah_apply_hebrew 的门槛是 80
                         'heb-wlc', bare(pick['form']), 95,
                         f'{loc[0]}:{loc[1]}', heb, round(pick['margin'] * 100)))
    return rows, stat, res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', help='v1 扫描页范围，如 342-370（试跑用）')
    ap.add_argument('--refilter', action='store_true', help='不重跑 OCR，只拿现有 TSV 重过 safe() 闸')
    ap.add_argument('--chapters', default='', help='限定在哪几章里定位，逗号分隔；默认全书')
    a = ap.parse_args()
    if a.refilter:
        import csv
        rows = list(csv.reader(open(OUT, encoding='utf-8'), delimiter='\t', quoting=csv.QUOTE_NONE))
        keep = [rows[0]] + [r for r in rows[1:] if safe(r[2], r[4], r[9], r[6])]
        with open(OUT, 'w', encoding='utf-8') as f:
            f.write(''.join('\t'.join(r) + '\n' for r in keep))
        print(f'重过闸：{len(rows) - 1} → {len(keep) - 1}')
        return
    if a.pages:
        lo, hi = map(int, a.pages.split('-'))
        pr = {'v1': (lo, hi), 'v2': (0, -1)}
    else:
        pr = {'v1': H.BODY['v1'], 'v2': H.BODY['v2']}
    chapters = [int(x) for x in a.chapters.split(',') if x] or list(range(1, 67))
    rows, stat, res = run(pr, chapters)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('vol\tscan_page\tbefore\tgarbage\tafter\tscript\treading\tconf\tverse\ttesseract\tmargin\n')
        for r in rows:
            f.write('\t'.join(str(x) for x in r) + '\n')
    print(stat, '→', OUT)


if __name__ == '__main__':
    main()
