#!/usr/bin/env python3
"""卡里尔缺部 OCR：pages.json（逐页版面）→ 分段正文 caryl_raw/job_ocr/p<部>/en/<slug>.md + order.json

    /usr/bin/python3 scripts/caryl_ocr_text.py 4            # 试跑：列各段、经文框行数、页码推定
    /usr/bin/python3 scripts/caryl_ocr_text.py 4 --apply

产出格式与 TCP 部分（caryl_raw/job/en_chapters/）一致，发布脚本可直接接：段首经文框 `.cy-text`（出处行作 `.cy-vlabel`）、
段内逐节小经文框 `.cy-vhead` 前挂 commentary-anchor、印本页码 `.cy-pb`、旁注 `.cy-margin`。**此处尚未纠错**，纠错在下游。

切分判据（第 4 部实测）：
- 段首出处行：`JOB Chap. 11. Verf. 1,2,3.`；第 6 部有的不印 Chap.（`JOB. 19 Vers. 20,21, 22.`），这时行首须像 JOB。
  节号须递增，乱序的按前后推（mono）；与下一段重叠的末节截掉。
  另两种写法：`OB. 19.7,8,9.`（没有 Vers，RE_SEC2）、`VERS. 11, 12, 13, 14,`（只有节号，章取页眉，RE_SEC3）。
  对开本（第 8 部底本）：每章起头单独一行 `CHAP. XXVIII.`（RE_CHAPLINE），其后印整章经文，按全章比对定经文框；
  分段用 `VERS. 25,26,27.`（可只有一个节号）。
  兜底：页眉章号进到下一章（连续两页）、本页与下一页都没有段首行，就在新章第一页开段（第 6 部 19:1–3 的段首行读坏了）。；首字 JOB 是花体，常读丢或读成 `OB`/`TOB`/`10B`/`02`/`102`，
  所以行首放宽到任意 0–4 个字母数字，另加两道闸：行短于 60 字符、章号等于本页页眉章号或其后一章（新章起头那页的页眉还是上一章；正文里的交叉引用在整行中间）。
- 经文框：出处行之后，与钦定本该段经文（出处所列各节 ±1）词重合 ≥ 0.6 的连续行。缩进判不了——经文行悬挂缩进、
  讲解首段花体首字母占两行，都和段落缩进混在一起。
- 逐节小经文框：行首 `Verse 7.`（Vers./Verf./Verfe 变体），接着的经文行同样按重合度续上。
- 分段：上一行是段尾短行（终点离栏右界 > 80px）或本行缩进 ≥ 35px 且上一行以句末标点收尾；上一行以断词号收尾的不分。
- 旁注：同侧相邻行并成一条，挂在与它起头同高的正文行之后（`.cy-margin`）。
- 断词：行末 `¬`（kraken 的断词号）去掉拼合；行末 `-` 保留连字符拼合（复合词）。
- 页码：页眉页码 OCR 常错，按「页码 − 叶序」的众数推定整部的偏移，逐页按叶序推算；推不出的页留空锚。
"""
import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
KJV = ROOT / 'foote_raw' / 'luke' / 'src' / 'kjv' / '19-JOBeng-kjv2006.usfm'
P = 'cy'
RE_SEC = re.compile(r'^\W{0,3}(?P<pre>(?:(?!C\w{0,2}a?p)[A-Za-z0-9]{1,4}\W{1,3}){0,2})\s*(?P<chap>C[A-Za-z]{0,2}a?p[A-Za-z]*[.,]?\s*)?(\d{1,2})\W+\s*V\w{0,4}[.,]?\s*(.*)$', re.I)
RE_SEC2 = re.compile(r'^\W{0,3}(?P<pre>(?:[A-Za-z0-9]{1,4}\W{1,3}){1,2}?)(\d{1,2})\s*[.,:]\s*(\d{1,2}(?:\s*[.,]\s*\d{1,2})+)\W*$')
RE_SEC3 = re.compile(r'^\W{0,2}VERS?\W{1,3}(\d{1,2}(?:\s*[.,]\s*\d{1,2})*)\W*$')
RE_CHAPLINE = re.compile(r'^\W{0,3}C[A-Z]{1,3}P\W{0,3}\s*([XVIL]{2,7})\W*$')   # 对开本每章起头单独一行「CHAP. XXVIII.」
RE_JOBISH = re.compile(r'^\W*(?:[IJT1l]?\s?[O0]\s?[BRE8]|10[B28]|1?0[23])\W*$', re.I)
RE_VH = re.compile(r'^\(?V(?:er|cr|e)[sf]\w{0,2}[.,]?\s*(\d{1,2}|[IlO1][\dIlO]?)\s*[.,]\s*(.*)$')
FIX_DIG = str.maketrans({'I': '1', 'l': '1', 'O': '0', 'o': '0'})


def kjv():
    vs, ch = {}, 0
    for ln in KJV.read_text(encoding='utf-8').splitlines():
        m = re.match(r'\\c (\d+)', ln)
        if m:
            ch = int(m.group(1))
        m = re.match(r'\\v (\d+) (.*)', ln)
        if m:
            t = re.sub(r'\\\+?w ([^|]*)\|[^\\]*\\\+?w\*', r'\1', m.group(2))
            t = re.sub(r'\\\+?\w+\*?', '', t)
            vs[(ch, int(m.group(1)))] = t
    return vs


def toks(s):
    return [w.lower() for w in re.findall(r'[A-Za-z]{3,}', s)]


def overlap(line, vocab):
    w = toks(line)
    if not w:
        return 0.0
    return sum(1 for x in w if x in vocab) / len(w)


def verse_nums(s):
    s = s.translate(FIX_DIG)
    ns = [int(x) for x in re.findall(r'\d{1,2}', s)]
    return ns


COLS_NUMBERED = {82}   # 对开本按栏编号：一叶两栏两个号（第 331、332 栏）
CHAPS = {4: (11, 14), 6: (18, 21), 8: (27, 29), 82: (27, 29), 9: (30, 31)}


class Builder:
    def __init__(self, part):
        self.part = part
        self.chs = CHAPS[part]
        self.d = BASE / f'p{part}'
        self.pages = json.loads((self.d / 'pages.json').read_text(encoding='utf-8'))
        self.K = kjv()

    def vocab(self, ch, vs):
        v = set()
        for n in range(min(vs) - 1, max(vs) + 2):
            v |= set(toks(self.K.get((ch, n), '')))
        return v

    def page_numbers(self, leaves):
        """逐页定页码：读数与相邻读数互证（页码差 = 叶序差）才采信，其余按两侧可信页插补（同 caryl_ocr_merge8）。
        原用全部一个偏移（众数），局部缺叶多叶处会整段错一页（第 4 部印本第 181 页标成 182）。"""
        import caryl_ocr_merge8 as m8
        sub = {lf: self.pages[lf] for lf in leaves}
        return m8.assign_pages(sub, step=2 if self.part in COLS_NUMBERED else 1)

    def page_numbers_mode(self, leaves):
        diffs = collections.Counter()
        for i, lf in enumerate(leaves):
            pn = self.pages[lf].get('pageno')
            if pn and re.fullmatch(r'\d{1,4}', pn):
                diffs[int(pn) - i] += 1
        if not diffs:
            return {}
        off, n = diffs.most_common(1)[0]
        return {lf: i + off for i, lf in enumerate(leaves) if i + off > 0}

    def chapter_of(self, lf):
        h = self.pages[lf].get('head') or ''
        m = re.search(r'C[A-Za-z]{0,2}ap[A-Za-z]*[.,]?\s*(\d{1,2})', h)
        if m:
            return int(m.group(1))
        m = re.search(r'C[A-Za-z]{0,2}A?P[A-Za-z]*[.,]?\s*([XVIL]{2,7})\b', h, re.I)   # 对开本页眉：CHAP. XXIX.
        return roman(m.group(1).upper()) if m else None

    def next_chapter(self, leaves, lf):
        i = leaves.index(lf)
        return self.chapter_of(leaves[i + 1]) if i + 1 < len(leaves) else None

    def has_heading(self, leaves, lf):
        """本页或下一页有段首行（真段首在，就不兜底）。"""
        i = leaves.index(lf)
        for x in leaves[i:i + 2]:
            for b in self.pages[x]['body']:
                t = b['t']
                if len(t) < 60 and (RE_SEC.match(t) or RE_SEC2.match(t) or RE_SEC3.match(t)):
                    return True
        return False

    def build(self):
        leaves = sorted(k for k, v in self.pages.items() if v['kind'] == 'text')
        def is_head(lf, t):
            if len(t) >= 60:
                return False
            m = RE_SEC.match(t)
            if m:
                return self.chs[0] <= int(m.group(3)) <= self.chs[1]
            mc = RE_CHAPLINE.match(t)
            if mc:
                return self.chs[0] <= roman(mc.group(1)) <= self.chs[1]
            return bool(RE_SEC3.match(t)) and self.chapter_of(lf) is not None and \
                self.chs[0] <= self.chapter_of(lf) <= self.chs[1]
        start = next((i for i, lf in enumerate(leaves)
                      if any(is_head(lf, b['t']) for b in self.pages[lf]['body'])), None)
        if start is None:
            raise SystemExit('找不到第一个段首出处行')
        body_leaves = leaves[start:]
        pno = self.page_numbers(body_leaves)
        sections, front = [], []
        cur = None
        para = []                 # 当前段落的行
        out = []                  # 当前段的块：('p', text) / ('text', md) / ('vhead', text) / ('raw', html)
        mode = None               # None / 'epi' / 'vh'
        epi_vocab, epi_lines, vh_vocab = set(), [], set()
        pending_pb = []

        def flush_para():
            nonlocal para
            if para:
                out.append(('p', join_lines(para)))
                para = []

        def close_epi():
            nonlocal mode, epi_lines
            if mode == 'epi':
                lab, lines = epi_lines[0], epi_lines[1:]
                md = f'{lab}\n{{: .{P}-vlabel}}' + ''.join('\n\n' + join_lines(x) for x in group_verses(lines))
                out.append(('text', md))
            elif mode == 'vh':
                out.append(('vhead', join_lines(epi_lines)))
            mode, epi_lines = None, []

        def close_section():
            flush_para()
            close_epi()
            if cur:
                cur['blocks'] = list(out)
                sections.append(cur)
            out.clear()

        prev = None
        for lf in body_leaves:
            pg = self.pages[lf]
            n = pno.get(lf)
            if n and self.part in COLS_NUMBERED:
                pb = (f'<span class="{P}-pb" id="p{n}" data-p="{n}–{n + 1}" data-leaf="{int(lf)}" '
                      f'title="Columns {n}–{n + 1} of the 1676–77 folio begin here (对开本第 {n}–{n + 1} 栏起)"></span>')
            else:
                pb = (f'<span class="{P}-pb" id="p{n}" data-p="{n}" data-leaf="{int(lf)}" '
                      f'title="Page {n} of the printed part begins here (原书第 {n} 页起)"></span>') if n else \
                 f'<span class="{P}-pb" data-leaf="{int(lf)}"></span>'
            pending_pb.append(pb)
            x1 = pg['x1']
            notes = group_margin(pg['margin'])
            for b in pg['body']:
                t = b['t'].strip()
                if not t:
                    continue
                if pending_pb:
                    t = ''.join(pending_pb) + t
                    pending_pb = []
                plain = re.sub(r'<[^>]+>', '', t)
                m = RE_SEC.match(plain) if len(plain) < 60 else None
                if m and re.fullmatch(r'[a-z]{2,}\W*', (m.group('pre') or '').strip()):
                    m = None                    # 「at Chap. 27. vers. 11…」：行首是英文小写词，是正文里的交叉引用
                if m and not m.group('chap') and not RE_JOBISH.match(m.group('pre') or ''):
                    m = None                    # 没有 Chap. 的（第 6 部「JOB. 19 Vers. 20」）行首必须像 JOB，挡掉「Verf. 19.」
                hc0 = self.chapter_of(lf)
                if hc0 is not None and not (self.chs[0] <= hc0 <= self.chs[1]):
                    hc0 = None                         # 页眉章号本身读坏了（第 8 部「Chip. 129.」），不拿它当闸
                if m and hc0 is not None and int(m.group(3)) - hc0 not in (0, 1) and \
                        self.chs[0] <= int(m.group(3)) <= self.chs[1]:
                    m = None                    # 章号与本页页眉不合：正文里的交叉引用
                hit = None
                whole = False
                mc = RE_CHAPLINE.match(plain)
                if m:
                    hit = (int(m.group(3)), m.group(4))
                elif mc and self.chs[0] <= roman(mc.group(1)) <= self.chs[1]:
                    if cur and cur['ch'] == roman(mc.group(1)):
                        prev = b                       # 与当前章相同：页眉残片落进正文（第 212 叶「CRAP. XXVIII.」夹在句中），删
                        continue
                    hit = (roman(mc.group(1)), '1')    # 新章起头：其后印整章经文
                    whole = True
                else:
                    m2 = RE_SEC2.match(plain) if len(plain) < 40 else None
                    m3 = RE_SEC3.match(plain) if len(plain) < 40 else None
                    if m2 and RE_JOBISH.match(m2.group('pre')) and self.chapter_of(lf) in (None, int(m2.group(2)), int(m2.group(2)) - 1):
                        hit = (int(m2.group(2)), m2.group(3))          # 「OB. 19.7,8,9.」：没有 Vers 字样
                    elif m3 and (self.chapter_of(lf) or cur):
                        hc3 = self.chapter_of(lf)
                        if not hc3 or not (self.chs[0] <= hc3 <= self.chs[1]):
                            hc3 = cur['ch'] if cur else None           # 页眉章号读坏（对开本「CHAP. XXV.I.」）：取当前段的章
                        if hc3:
                            hit = (hc3, m3.group(1))                   # 「VERS. 11, 12, 13, 14,」：只有节号，章取页眉
                # 兜底：页眉章号进到下一章、却还没见到该章段首 → 在这一页开新段（该章首段的段首行读坏了）
                hch = self.chapter_of(lf)
                if (not hit and cur and hch == cur['ch'] + 1 and not cur.get('synthetic_next') and b is pg['body'][0]
                        and self.next_chapter(body_leaves, lf) == hch and not self.has_heading(body_leaves, lf)):
                    hit = (hch, '1')
                    cur['synthetic_next'] = True
                    synthetic = True
                else:
                    synthetic = False
                if hit and not (self.chs[0] <= hit[0] <= self.chs[1]):
                    hc = self.chapter_of(lf)
                    if m and m.group('chap') and hc and self.chs[0] <= hc <= self.chs[1]:
                        hit = (hc, hit[1])             # 章号读错（「Chap. 49.」）而页眉章号可信：取页眉
                    else:
                        hit = None                     # 章号不在本部范围（第 8 部「Ctap. 17.」）
                if hit:
                    vs = mono(verse_nums(hit[1]))
                    ch = hit[0]
                    hch = self.chapter_of(lf)
                    if hch and hch != ch and ch not in range(1, 43):
                        ch = hch
                    if not vs:
                        vs = [1]
                    close_section()
                    cur = dict(part=self.part, ch=ch, vs=vs, ref=plain, leaf=lf)
                    if synthetic:                      # 段首行读坏了：这一行是正文，照常进段落
                        cur['ref'] = f'[Chap. {ch}]'
                        mode, epi_lines = None, []
                        para.append(t)
                        prev = b
                        continue
                    mode, epi_lines = 'epi', [t]
                    epi_vocab = self.vocab(ch, list(range(1, 43)) if whole else vs)
                    prev = b
                    continue
                if cur is None:
                    front.append(plain)
                    prev = b
                    continue
                vh = RE_VH.match(plain)
                if vh and len(vh.group(2)) > 3:
                    v = verse_nums(vh.group(1))
                    if v and 1 <= v[0] <= 42:
                        flush_para()
                        close_epi()
                        out.append(('raw', f'<div class="commentary-anchor" id="job-{cur["ch"]}-{v[0]}"></div>'))
                        mode, epi_lines = 'vh', [t]
                        vh_vocab = self.vocab(cur['ch'], [v[0]])
                        prev = b
                        continue
                if mode == 'epi':
                    # 经文上一行以断词号收尾：下一行（半个词起头）一律归经文框——否则「ters that passe away」这类残句漏到讲解段首
                    cont = bool(re.search(r'[¬-]$', re.sub(r'<[^>]+>', '', epi_lines[-1]).strip()))
                    if cont or overlap(plain, epi_vocab) >= 0.6 or (len(toks(plain)) <= 3 and overlap(plain, epi_vocab) > 0):
                        epi_lines.append(t)
                        prev = b
                        continue
                    close_epi()
                elif mode == 'vh':
                    if overlap(plain, vh_vocab) >= 0.6 and not (prev and prev['end'] < x1 - 80):
                        epi_lines.append(t)
                        prev = b
                        continue
                    close_epi()
                new_para = False
                if prev is not None and para and not re.search(r'[¬-]$', re.sub(r'<[^>]+>$', '', para[-1])):
                    if prev.get('short'):
                        new_para = True
                    elif b['indent'] and re.search(r'[.:;?!)]\W*$', para[-1]):
                        new_para = True
                if new_para:
                    flush_para()
                para.append(t)
                prev = b
                # 旁注挂在与它起头同高（或其后最近）的正文行之后
                while notes and notes[0][0] <= b['y'] + 40:
                    para[-1] += f' <span class="{P}-margin">{notes.pop(0)[1]}</span>'
            if notes and para:
                para[-1] += ''.join(f' <span class="{P}-margin">{n[1]}</span>' for n in notes)
        close_section()
        return front, sections, pno


def group_margin(ms):
    """同侧、上下相距不到 1.6 行高的旁注行并成一条（旁注是窄栏，一条注占好几行）；行末断词号拼合。"""
    out = []
    for m in sorted(ms, key=lambda m: m['y']):
        if out and out[-1][2] == m['side'] and m['y'] - out[-1][3] < 110:
            out[-1][1] = join_lines([out[-1][1], m['t']])
            out[-1][3] = m['y']
        else:
            out.append([m['y'], m['t'], m['side'], m['y']])
    return [(y, t) for y, t, _, _ in out]


def roman(r):
    v = {'I': 1, 'V': 5, 'X': 10, 'L': 50}
    n = [v.get(c, 0) for c in r]
    return sum(-a if i + 1 < len(n) and n[i + 1] > a else a for i, a in enumerate(n))


def mono(vs):
    """出处行节号须递增：乱序的按前后推（「10, 17」→ 10, 11；「19, 26, 21」→ 19, 20, 21）。"""
    out = []
    for i, v in enumerate(vs):
        if out and v <= out[-1]:
            v = out[-1] + 1
        elif out and i + 1 < len(vs) and v > vs[i + 1] and vs[i + 1] > out[-1]:
            v = out[-1] + 1
        out.append(v)
    return out


def join_lines(lines):
    s = ''
    for ln in lines:
        ln = ln.strip()
        if not s:
            s = ln
        elif s.endswith('¬'):
            s = s[:-1] + ln
        elif re.search(r'[A-Za-z]-$', s):
            s = s + ln
        else:
            s = s + ' ' + ln
    return s


def group_verses(lines):
    """经文框里一节一行：kraken 的行是原书排版行，这里按悬挂缩进不可靠，整框并成一段即可。"""
    return [lines] if lines else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('part', type=int)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    B = Builder(a.part)
    front, secs, pno = B.build()
    print(f'第 {a.part} 部：卷首 {len(front)} 行；段 {len(secs)}；推定页码 {min(pno.values()) if pno else "-"}–'
          f'{max(pno.values()) if pno else "-"}', file=sys.stderr)
    for s in secs:
        epi = sum(1 for b in s['blocks'] if b[0] == 'text')
        vh = sum(1 for b in s['blocks'] if b[0] == 'vhead')
        words = sum(len(b[1].split()) for b in s['blocks'] if b[0] in ('p', 'text', 'vhead'))
        print(f'  {s["ch"]}:{s["vs"]}  叶 {s["leaf"]}  经文框 {epi}  逐节 {vh}  词 {words}  | {s["ref"][:50]}', file=sys.stderr)
    if a.apply:
        out = B.d / 'en'
        out.mkdir(exist_ok=True)
        for f in out.glob('*.md'):
            f.unlink()
        order = []
        for k, s in enumerate(secs):
            nx = secs[k + 1] if k + 1 < len(secs) else None
            if nx and nx['ch'] == s['ch'] and max(s['vs']) >= min(nx['vs']) > min(s['vs']):
                s['vs'] = [v for v in s['vs'] if v < min(nx['vs'])]
            slug = f'{s["ch"]}-{min(s["vs"])}'
            k = 2
            while any(o['slug'] == slug for o in order):
                slug = f'{s["ch"]}-{min(s["vs"])}-{k}'
                k += 1
            md = []
            for kind, txt in s['blocks']:
                if kind == 'p':
                    md.append(txt)
                elif kind == 'text':
                    md.append(f'<div class="{P}-text" markdown="1">\n\n{txt}\n\n</div>')
                elif kind == 'vhead':
                    md.append(f'<p class="{P}-vhead" markdown="1">{txt}</p>')
                else:
                    md.append(txt)
            (out / f'{slug}.md').write_text('\n\n'.join(md).strip() + '\n', encoding='utf-8')
            order.append(dict(slug=slug, part=a.part, ch=s['ch'], v1=min(s['vs']), v2=max(s['vs']), ref=s['ref'],
                              leaf=s['leaf']))
        (B.d / 'order.json').write_text(json.dumps(dict(sections=order, front=front), ensure_ascii=False, indent=1) + '\n',
                                        encoding='utf-8')
        print(f'写入 {len(order)} 段 → {out}', file=sys.stderr)


if __name__ == '__main__':
    main()
