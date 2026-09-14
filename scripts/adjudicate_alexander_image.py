#!/usr/bin/env python3
"""亚历山大《诗篇注释》：按 1864 扫描件**页面影像**逐处判读残留 OCR 坏字。

为什么还要这一层：`repair_alexander_ocr.py` 的三道闸（字形规则／判词典／语料
自证）与 `adjudicate_alexander_ocr.py` 的第二证人（1850 三卷本）跑完，账上仍
剩 900 余处。它们过不去的原因是**证据不足**：两份 OCR 在同一处往往都读崩了，
拿一份崩的去改另一份崩的没有意义。PDF 的文本层是同一份 ABBYY OCR，也不算
第三方——**只有页面影像是**（feedback_page_image_is_final_authority）。

做法：按书页分组，把整页渲染成图，连同该页上待判的若干处（OCR 串 + 上下文）
一起交模型，只让它回答「影像上这一处印的是什么」。
  - **不让它重抄整页**：输出 token 翻倍，还会引入新的生成式错误。
  - **不把第二证人的读数给它看**：证人与影像必须各自独立出结果，
    两边一致才采信。给了就成了诱导，两个"证人"退化成一个。

采信要过三道（apply 阶段，见 --apply）：
  影像闸  模型必须给出明确读数，写 `?` 的一律不动
  判词闸  读数得是真词，或本书别处出现 ≥3 次（放行 Adhonai、Selah 这类专名
          与希伯来文音译），或是非拉丁字母（希腊文／希伯来文）
  互证闸  第二证人读数与影像读数一致 → 采信；
          证人无读数或不一致 → **再跑一遍独立的影像判读**，两遍一致才采信；
          仍不一致 → 记入待人工复核，不动正文

用法：
    python3 scripts/adjudicate_alexander_image.py --build          # 生成待判清单
    python3 scripts/adjudicate_alexander_image.py --pages 23,32,56 # 标定用
    python3 scripts/adjudicate_alexander_image.py --all            # 全书判读
    python3 scripts/adjudicate_alexander_image.py --all --pass2    # 第二遍
    python3 scripts/adjudicate_alexander_image.py --apply          # 过闸并落盘
"""
import argparse
import base64
import json
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import alexander_lexicon as L

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
PDF = Path.home() / 'Documents/论文/alexander/psalms_1864_kregel.pdf'
OFFSET = 3                       # pdf_index = 书页页码 + OFFSET（页眉标定，见 crop 脚本）
WITNESS_LOG = ROOT / 'logs/alexander_adjudicate.tsv'
SUSPECTS = ROOT / 'logs/alexander_image_suspects.json'
READINGS = ROOT / 'logs/alexander_image_readings.tsv'      # 第一遍
READINGS2 = ROOT / 'logs/alexander_image_readings2.tsv'    # 第二遍（互证）
APPLIED = ROOT / 'logs/alexander_image_applied.tsv'
PENDING = ROOT / 'logs/alexander_image_pending.tsv'

SYSTEM = (
    'You are a careful palaeographer proof-reading a 19th-century printed book '
    '(Alexander, "The Psalms Translated and Explained", 1864).\n'
    'You are given ONE page image and a numbered list of spots where the OCR '
    'text is suspected to be wrong. For each spot, report what the page IMAGE '
    'actually shows at that position.\n'
    'Rules:\n'
    '1. Output ONE line per numbered item, format exactly:  N|reading\n'
    '2. `reading` = exactly what is printed, in the original script. If it is '
    'Hebrew or Greek type, give the Hebrew/Greek characters.\n'
    '3. If you genuinely cannot make it out, or cannot locate the spot on this '
    'page, output  N|?  — never guess, never infer from context.\n'
    '4. Report ONLY the word/phrase at that spot, not the surrounding text.\n'
    '5. Do not add explanations, headers, or any other text.\n'
    '6. Preserve the original 19th-century spelling (shews, connexion, '
    'inclose) — do NOT modernise.'
)

TOK = re.compile(r"[A-Za-z][A-Za-z'’\-]*")
PAGE_RE = re.compile(r'<!-- PAGE (\d+) -->')


# ── 待判清单 ──────────────────────────────────────────────────────────────

def _legit_compound(w, vocab):
    """连字复合词，两半都是真词 → 正经词（dwelling-place / burnt-offering）。"""
    if '-' not in w:
        return False
    parts = [p for p in w.split('-') if p]
    return len(parts) > 1 and all(L.is_word(p, vocab) or p.istitle() for p in parts)


def _mask_markup(raw: str) -> str:
    """把 HTML 标签/注释替换成等长空格：偏移不变，扫描时不会把 class 名当正文。"""
    def blank(m):
        return ' ' * (m.end() - m.start())
    return re.sub(r'<!--.*?-->|<[^<>]*>', blank, raw, flags=re.S)


# 「脏词整段」：一串不含空白的字符，里面至少有一个字母。
# **不能按 token 切**——`IJ^DDD` 是一个希伯来词、`beha\'iour` 是一个英文词，
# 切成两半分别判读，替换回去就成了半吊子（`beha\'viour`），标定时踩到过。
# 切分时把**词与词之间**的符号排除在外（斜体星号、破折号、括号、引号、逗号），
# 否则 `God.—*Men` 会被当成一个词送去判读（标定时 2522 处里一多半是这么来的）；
# 但词**内部**的 OCR 杂质（`^ \\ ' ~ / &lt;`）必须留在段里，那正是要判的东西。
SPAN = re.compile(r'[^\s*\u2014\u2013()\[\]{}"\u201c\u201d,;]+')
# 词首尾的排版符号不算词的一部分，剥掉再判
TRIM = '*_()[]{}.,;:!?"\u2018\u2019\u201c\u201d\u2014\u2013'
# 书里通行的缩写，判词典收不到，不是坏字
ABBREV = {'i.e', 'e.g', '&c', 'viz', 'cf', 'sc', 'ib', 'ibid', 'Ps', 'ver',
          'vs', 'ch', 'Heb', 'Gr', 'Lat', 'Sept', 'LXX', 'MS', 'MSS', 'Vulg',
          'sq', 'sqq', 'pp', 'vol', 'Chron', 'Deut', 'Exod', 'Isa', 'Jer',
          'Ezek', 'Hos', 'Zeph', 'Hab', 'Mic', 'Mal', 'Matt', 'Mat', 'Rom',
          'Cor', 'Gal', 'Eph', 'Phil', 'Col', 'Thess', 'Tim', 'Tit', 'Philem',
          'Jas', 'Pet', 'Rev', 'Sam', 'Kings', 'Neh', 'Prov', 'Eccl', 'Cant',
          'Lam', 'Dan', 'Obad', 'Jon', 'Nah', 'Hag', 'Zech', 'Num', 'Lev',
          'Gen', 'Josh', 'Judg', 'Esth'}


def _suspect(span, vocab):
    """这一段脏不脏。返回 (是否可疑, 剥掉首尾排版符号后的芯)。"""
    core = span.strip(TRIM)
    if not core or not re.search(r'[A-Za-z]', core):
        return False, core
    if core in ABBREV or core.rstrip('.') in ABBREV:
        return False, core
    if L.is_word(core, vocab) or _legit_compound(core, vocab):
        return False, core
    # 纯字母且是真词的变体（19 世纪拼法等）已由 is_word 放行；
    # 到这里说明要么含非字母杂质，要么不是真词
    return True, core


def build():
    vocab = L.build()
    wit = {}
    if WITNESS_LOG.exists():
        for i, line in enumerate(WITNESS_LOG.open(encoding='utf-8')):
            if i == 0:
                continue
            f = line.rstrip('\n').split('\t')
            if len(f) >= 4:
                wit[(f[0], f[1])] = f[2]

    items, seen = [], set()
    for sec in ['preface'] + [str(i) for i in range(1, 151)]:
        p = SRC / f'{sec}.md'
        if not p.exists():
            continue
        raw = p.read_text(encoding='utf-8')
        marks = [(m.start(), int(m.group(1))) for m in PAGE_RE.finditer(raw)]
        if not marks:
            continue
        masked = _mask_markup(raw)
        for m in SPAN.finditer(masked):
            span = m.group(0)
            bad, core = _suspect(span, vocab)
            if not bad:
                continue
            if m.start() < marks[0][0]:          # front matter
                continue
            page = next((pg for pos, pg in reversed(marks) if pos < m.start()), None)
            ctx = re.sub(r'\s+', ' ', raw[max(0, m.start() - 55):m.end() + 55])
            key = (page, core, ctx[:40])
            if key in seen:
                continue
            seen.add(key)
            items.append(dict(sec=sec, tok=core, span=span, page=page, ctx=ctx,
                              wit=wit.get((sec, core), '')))
    SUSPECTS.parent.mkdir(parents=True, exist_ok=True)
    SUSPECTS.write_text(json.dumps(items, ensure_ascii=False, indent=1),
                        encoding='utf-8')
    pages = sorted({i['page'] for i in items if i['page']})
    print(f'待判 {len(items)} 处，{len(pages)} 书页（{pages[0]}–{pages[-1]}）→ {SUSPECTS}')
    return items


def load():
    if not SUSPECTS.exists():
        return build()
    return json.loads(SUSPECTS.read_text(encoding='utf-8'))


# ── 判读 ──────────────────────────────────────────────────────────────────

def render(page_no, dpi=220):
    import fitz
    idx = page_no + OFFSET
    d = fitz.open(PDF)
    if not (0 <= idx < d.page_count):
        d.close()
        return None
    png = d[idx].get_pixmap(dpi=dpi).tobytes('png')
    d.close()
    return png


def ask(png, items, label=''):
    lines = [f'{n}. OCR has «{it["tok"]}» in: …{it["ctx"]}…'
             for n, it in enumerate(items, 1)]
    text = ('This page image is page ' + str(items[0]['page']) +
            ' of the book. For each numbered spot below, report what the IMAGE '
            'actually shows in place of the OCR string «…»:\n\n' + '\n'.join(lines))
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64',
                                     'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': text},
    ]}}
    cmd = ['claude', '-p', '--safe-mode', '--strict-mcp-config',
           '--disallowedTools', '*',
           '--input-format', 'stream-json', '--output-format', 'stream-json',
           '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n',
                       capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f'CLI rc={r.returncode} {r.stderr[:200]}')
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(f'CLI error: {str(o.get("result"))[:200]}')
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('未拿到 result 事件')


def parse(res, items):
    out = {}
    for line in res.splitlines():
        m = re.match(r'\s*(\d+)\s*[|｜]\s*(.+?)\s*$', line)
        if not m:
            continue
        n = int(m.group(1))
        if 1 <= n <= len(items):
            out[n - 1] = m.group(2).strip().strip('«»「」"')
    return out


def run(pages, out_path, dpi=220, retry_next_page=False):
    items = load()
    if retry_next_page:
        # 第一遍写 `?` 的，多半是**段落跨页**：`<!-- PAGE n -->` 标的是段首那页，
        # 而这处字在 n+1 页上（p160 的 `sowZ` 就是这样）。改问下一页。
        first = {}
        if READINGS.exists():
            for line in READINGS.open(encoding='utf-8'):
                f = line.rstrip('\n').split('\t')
                if len(f) >= 5:
                    first[(f[0], f[1], f[2][:40])] = f[3]
        items = [dict(it, page=(it['page'] or 0) + 1) for it in items
                 if first.get((it['sec'], it['tok'], it['ctx'][:40])) == '?']
        print(f'第一遍未判读 {len(items)} 处，改问下一页')
    bypage = defaultdict(list)
    for it in items:
        if it['page']:
            bypage[it['page']].append(it)
    done = set()
    if out_path.exists():
        for line in out_path.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            if len(f) >= 4:
                done.add((f[0], f[1], f[2][:40]))
    todo = [p for p in pages if p in bypage]
    total = 0.0
    fails = 0
    with out_path.open('a', encoding='utf-8') as fh:
        for k, pg in enumerate(todo, 1):
            group = [it for it in bypage[pg]
                     if (it['sec'], it['tok'], it['ctx'][:40]) not in done]
            if not group:
                continue
            try:
                png = render(pg, dpi)
                if png is None:
                    print(f'  p{pg} 越界', flush=True)
                    continue
                res, cost = ask(png, group, label=f'p{pg}')
            except Exception as e:                       # noqa: BLE001
                print(f'  p{pg} 失败：{e}', flush=True)
                fails += 1
                # 连续失败多半是会话额度用尽——再跑下去只是空烧，
                # 已判读的都在 TSV 里，重跑会自动跳过（reference_cli_session_limit）
                if fails >= 5:
                    print('✗ 连续 5 页失败，判定为额度/环境问题，中止。'
                          '已判读的已落盘，重跑本命令会从断点续上。', flush=True)
                    sys.exit(42)
                time.sleep(5)
                continue
            fails = 0
            total += cost
            got = parse(res, group)
            for i, it in enumerate(group):
                fh.write(f'{it["sec"]}\t{it["tok"]}\t{it["ctx"]}\t'
                         f'{got.get(i, "?")}\t{pg}\n')
            fh.flush()
            print(f'[{k}/{len(todo)}] p{pg} {len(group)} 处 '
                  f'${total:.2f}', flush=True)
    print(f'完成，累计 ${total:.2f} → {out_path}')


# ── 过闸落盘 ──────────────────────────────────────────────────────────────

def norm(s):
    return re.sub(r'[^0-9a-zA-Zα-ωΑ-Ωἀ-ῼ֐-׿]', '', s or '').lower()


def apply_gates(dry=True):
    vocab = L.build()
    corpus = Counter()
    for p in SRC.glob('*.md'):
        corpus.update(TOK.findall(p.read_text(encoding='utf-8')))

    def read_tsv(p):
        d = {}
        if not p.exists():
            return d
        for line in p.open(encoding='utf-8'):
            f = line.rstrip('\n').split('\t')
            if len(f) >= 5:
                d[(f[0], f[1], f[2][:40])] = f[3]
        return d

    r1, r2 = read_tsv(READINGS), read_tsv(READINGS2)
    items = load()
    ok, pending = [], []
    for it in items:
        k = (it['sec'], it['tok'], it['ctx'][:40])
        img = r1.get(k, '')
        if not img or img == '?' or norm(img) == norm(it['tok']):
            continue                                  # 影像闸：无读数 / 与原串同形
        # 判词闸：读数里**每一个**拉丁词都得是真词或书中常见。
        # 不能只在「整条读数是单个词」时查——模型有时给出多词读数
        # （`7more` → `more than the time,`），那样就整条绕过了这道闸。
        words = re.findall(r"[A-Za-z][A-Za-z'’\-]*", img)
        bad = [w for w in words
               if not (L.is_word(w, vocab) or corpus[w] >= 3 or w in ABBREV)]
        if bad:
            pending.append((it, img, r2.get(k, ''), f'判词闸：{bad[:3]} 不是真词'))
            continue
        # 读数长度失控（模型把整句抄回来了）也不采信
        if len(img) > max(40, len(it['tok']) * 4):
            pending.append((it, img, r2.get(k, ''), '判词闸：读数过长，疑似整句回抄'))
            continue
        # 互证闸
        wit = it.get('wit') or ''
        second = r2.get(k, '')
        if wit and norm(wit) == norm(img):
            ok.append((it, img, 'witness'))
        elif second and second != '?' and norm(second) == norm(img):
            ok.append((it, img, 'pass2'))
        else:
            pending.append((it, img, second, '互证闸：证人/二遍不一致'))
    print(f'过闸 {len(ok)} 处，待人工复核 {len(pending)} 处')
    if dry:
        for it, img, src in ok[:15]:
            print(f'  [{it["sec"]}] {it["tok"]!r} → {img!r}  ({src})')
        return ok, pending

    ok = _fix_hebrew_order(ok)
    from collections import defaultdict as dd
    per = dd(list)
    for it, img, src in ok:
        per[it['sec']].append((it, img, src))
    n = 0
    with APPLIED.open('a', encoding='utf-8') as fh:
        for sec, lst in per.items():
            p = SRC / f'{sec}.md'
            t = p.read_text(encoding='utf-8')
            for it, img, src in lst:
                # 用上下文定位，避免同名 token 改错位置
                ctx = it['ctx']
                head = ctx.split(it['tok'])[0][-25:]
                old = head + it['tok']
                if t.count(old) != 1:
                    fh.write(f'{sec}\t{it["tok"]}\t{img}\tSKIP-定位不唯一\n')
                    continue
                t = t.replace(old, head + img, 1)
                fh.write(f'{sec}\t{it["tok"]}\t{img}\t{src}\n')
                n += 1
            p.write_text(t, encoding='utf-8')
    with PENDING.open('w', encoding='utf-8') as fh:
        fh.write('# 影像判读未过闸，需人工复核\n篇\tOCR串\t影像读数\t二遍\t原因\t上下文\n')
        for it, img, second, why in pending:
            fh.write(f'{it["sec"]}\t{it["tok"]}\t{img}\t{second}\t{why}\t{it["ctx"]}\n')
    print(f'已落盘 {n} 处 → {APPLIED}；待复核清单 → {PENDING}')
    return ok, pending



HEB = re.compile(r'[\u0590-\u05ff]')


def _fix_hebrew_order(ok):
    """相邻两处都读成希伯来文时，**交换替换值**。

    ABBYY 按视觉左右切词，希伯来文是右起横书，所以 `Dy^T HD^` 这一串里
    视觉上靠左的 `Dy^T` 其实是逻辑上**后面**那个词（רַגְלַיִם），
    `HD^` 才是前面的 נְכֵה。原样落回去，读者看到的词序是反的
    （reference_ages_hebrew_font 记过同一个坑）。
    判据：同一篇、上下文里两处紧挨着（中间只有空白），且两处读数都是希伯来文。
    """
    bysec = defaultdict(list)
    for i, (it, img, src) in enumerate(ok):
        bysec[it['sec']].append(i)
    out = list(ok)
    for sec, idxs in bysec.items():
        raw = (SRC / f'{sec}.md').read_text(encoding='utf-8')
        pos = {}
        for i in idxs:
            j = raw.find(ok[i][0]['tok'])
            if j >= 0:
                pos[i] = j
        for a_i in idxs:
            for b_i in idxs:
                if a_i >= b_i or a_i not in pos or b_i not in pos:
                    continue
                ta, tb = ok[a_i][0]['tok'], ok[b_i][0]['tok']
                ja, jb = pos[a_i], pos[b_i]
                if not (ja < jb and raw[ja + len(ta):jb].strip() == ''):
                    continue
                if HEB.search(ok[a_i][1]) and HEB.search(ok[b_i][1]):
                    out[a_i] = (ok[a_i][0], ok[b_i][1], ok[a_i][2] + '+heb-swap')
                    out[b_i] = (ok[b_i][0], ok[a_i][1], ok[b_i][2] + '+heb-swap')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--pages', help='如 23,32,56 或 100-120')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--pass2', action='store_true', help='跑第二遍（互证用）')
    ap.add_argument('--next-page', action='store_true',
                    help='只重跑第一遍判成 ? 的，改问下一页（段落跨页）')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--dpi', type=int, default=220)
    a = ap.parse_args()

    if a.build:
        build()
        return
    if a.apply:
        apply_gates(dry=a.dry_run)
        return
    items = load()
    allpages = sorted({(i['page'] or 0) + (1 if a.next_page else 0)
                      for i in items if i['page']})
    if a.all:
        pages = allpages
    elif a.pages:
        pages = []
        for part in a.pages.split(','):
            if '-' in part:
                lo, hi = map(int, part.split('-'))
                pages += [p for p in allpages if lo <= p <= hi]
            else:
                pages.append(int(part))
    else:
        ap.error('要 --pages 或 --all')
    run(pages, READINGS2 if a.pass2 else READINGS, a.dpi,
        retry_next_page=a.next_page)


if __name__ == '__main__':
    main()
