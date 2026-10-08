#!/usr/bin/env python3
"""约翰斯通《腓立比书讲疏》—— 两条 OCR 流合一的公共件。

字从 tesseract 来（ABBYY 8.0 的字准烂到 `tlie`/`l)y`/`ajjproved`），
斜体区间和段落边界从 ABBYY XML 来（tesseract 5.x 走 LSTM，字体属性一概不报）。
两边靠 difflib 在字符级对齐。

哨兵沿用 alexander_abbyy 那一套，不另起炉灶：
    IT_ON/IT_OFF  斜体开关
    HYPH          行末断词的接缝（**不直接删连字符**，复合词也断在这里）
    BREAK         行与行之间的接缝（ABBYY 偶尔把行末连字符整个吞掉）
"""
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alexander_abbyy as A

IT_ON, IT_OFF, HYPH, BREAK = A.IT_ON, A.IT_OFF, A.HYPH, A.BREAK

GREEK = re.compile(r'[Ͱ-Ͽἀ-῿]')


def is_running_head(line):
    """页眉行？'40 Lectures on Philippians. [CH. I.' / 'VER. 10.] ... 41'

    只在**多行段**里剔。单行段可能是讲题（`ADDRESS AND SALUTATION.`），
    同一套判据会把 30 篇讲题一并剔光 —— alexander 那边踩过这个坑。
    """
    t = line.strip()
    if not t or len(t) > 70:
        return False
    if 'lectures on philippians' in t.lower():
        return True
    if re.match(r"^\W*(ver[s]?\.|vers?\s)", t, re.I) and re.search(r'\d\s*$', t):
        return True
    if re.match(r'^\W*\d{1,3}\W*$', t):          # 孤零零一个页码
        return True
    return False


def join_ocr_lines(lines):
    """tesseract 的行 → 一条流，行末断词与行接缝都留哨兵。

    与 alexander_abbyy._join_lines 同判据：行尾连字符 + 下一行首字母小写 =
    断词（19 世纪排印里断词处一律小写续接），**但连字符不删**，留 HYPH 让
    cleanup 阶段拿全书复合词表定夺（well-watered 这类复合词也断在这里）。
    """
    buf = ''
    for raw in lines:
        t = raw.strip()
        if not t:
            continue
        if not buf:
            buf = t
            continue
        if buf.endswith('-') and t[:1].islower():
            buf = buf[:-1] + HYPH + t
        else:
            buf = buf + BREAK + t
    return buf


def strip_sentinels(text):
    """哨兵流 → (纯文本, 斜体标志表)"""
    plain, ital = [], []
    on = False
    for ch in text:
        if ch == IT_ON:
            on = True
        elif ch == IT_OFF:
            on = False
        elif ch == HYPH:
            # 行末断词的接缝**原样留着**，不要在这里变成 '-'。
            # 一变就跟 well-watered 这类本来带连字符的复合词再也分不开了；
            # 到底留不留连字符，要等全书拼完拿语料自证（resolve_hyphens）。
            plain.append(HYPH); ital.append(on)
        elif ch == BREAK:
            plain.append(' '); ital.append(on)
        else:
            plain.append(ch); ital.append(on)
    return ''.join(plain), ital


_NORM = str.maketrans({'‘': "'", '’': "'", '“': '"', '”': '"',
                       '—': '-', '–': '-', '‐': '-', ' ': ' ',
                       HYPH: '-'})      # 对齐时当连字符看，产物里仍是哨兵


def _norm(s):
    """对齐用的归一。只为让 diff 对得上，不回写产物。"""
    return s.translate(_NORM)


def _charmap(a, b):
    """a 的字符偏移 → b 的字符偏移（只含 difflib 认的匹配位）"""
    sm = difflib.SequenceMatcher(None, _norm(a), _norm(b), autojunk=False)
    m = {}
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            m[i + k] = j + k
    return m


def italic_runs(text):
    """哨兵流 → [(起, 止)] 斜体区间（按纯文本偏移）"""
    runs, on, start, pos = [], False, 0, 0
    for ch in text:
        if ch == IT_ON:
            if not on:
                on, start = True, pos
        elif ch == IT_OFF:
            if on:
                runs.append((start, pos)); on = False
        else:
            pos += 1
    if on:
        runs.append((start, pos))
    return runs


_WORD = re.compile(r"[A-Za-zͰ-Ͽἀ-῿'’\-" + HYPH + r"]+")


def _snap_to_words(text, ital):
    """斜体开关落在词中间 → 按词内多数票归一，整词进或整词出"""
    ital = list(ital)
    for m in _WORD.finditer(text):
        s, e = m.span()
        span = ital[s:e]
        if all(span) or not any(span):
            continue
        vote = sum(span) * 2 >= (e - s)
        for k in range(s, e):
            ital[k] = vote
    return ital


def _drop_greek(text, ital):
    """希腊文不打斜体。

    19 世纪排的希腊文用 Porson 体，字形本身是斜的（见 p.40 脚注的
    γίνεσθε τραπεζῖται δόκιμοι），ABBYY 照形判成 italic="true"。那是**字体**
    不是**强调**，跟着搬进 markdown 会把整本书的希腊文都包进 `*…*`。
    """
    ital = list(ital)
    for m in _WORD.finditer(text):
        s, e = m.span()
        if GREEK.search(text[s:e]):
            for k in range(s, e):
                ital[k] = False
    return ital


def _tidy_runs(text, ital):
    """收边：把区间修到词界上，清掉没内容的区间，合并只隔着空白的相邻区间。

    `*veigious *`（尾吞空格）、`* *`、`*, *`（整段只有标点）、
    `*the day* *of Christ,*`（跨行被切成两段）—— 都是对齐抖出来的毛边，
    不收会直接写进 markdown。
    """
    ital = list(ital)
    n = len(ital)

    i = 0                                   # 相邻区间之间只隔空白 → 合一
    while i < n:
        if ital[i]:
            j = i
            while j < n and ital[j]:
                j += 1
            k = j
            while k < n and text[k].isspace():
                k += 1
            if k < n and k > j and ital[k]:
                for t in range(j, k):
                    ital[t] = True
                continue
            i = j
        else:
            i += 1

    i = 0                                   # 掐头去尾的空白；没字就整段清掉
    while i < n:
        if not ital[i]:
            i += 1
            continue
        j = i
        while j < n and ital[j]:
            j += 1
        if not any(c.isalnum() for c in text[i:j]):
            for t in range(i, j):
                ital[t] = False
        else:
            for t in range(i, j):
                if text[t].isspace():
                    ital[t] = False
                else:
                    break
            for t in range(j - 1, i - 1, -1):
                if text[t].isspace():
                    ital[t] = False
                else:
                    break
        i = j
    return ital


def _par_italic(abbyy_par, ocr_chunk, dropped):
    """单段：ABBYY 的斜体区间 → OCR 字流的斜体标志表。

    **按「区间」搬，不按「每个字」搬**：逐字搬时 difflib 会在对不齐的地方把
    斜体开关卡进词中间，凭空造出 ABBYY 根本没有的斜体。

    **而且必须按段对齐，不能整页对齐**：整页对齐时脚注里的希腊文乱码
    （`yUivix`）会跟正文的错字（`veigious`）配上对，把斜体搬到几百字之外的
    地方去。实测踩过。

    **区间端点从外侧卡，不从内侧找**：斜体词恰恰是 tesseract 最容易读错的
    地方（p.40 的 *religious* 被读成 `veigious`），从内侧找锚点必然落空，
    一落空就把真斜体整个丢掉。而斜体两边的词 tesseract 读得对 —— 用
    `called ` 和 ` truth` 把中间那段夹出来，稳得多。内侧锚点只当退路。
    """
    a_plain, _ = strip_sentinels(abbyy_par)
    b_plain, _ = strip_sentinels(ocr_chunk)
    amap = _charmap(a_plain, b_plain)

    def scan(x, stop, step):
        for t in range(x, stop, step):
            if t in amap:
                return amap[t]
        return None

    ital = [False] * len(b_plain)
    for s, e in italic_runs(abbyy_par):
        lo = scan(s - 1, max(s - 40, -1), -1)
        hi = scan(e, min(e + 40, len(a_plain)), 1)
        js = 0 if lo is None else lo + 1
        je = (len(b_plain) if hi is None else hi) - 1
        if lo is None and hi is None:
            js = je = None
        if js is None or je < js or (je - js + 1) > 2 * (e - s) + 8:
            js = scan(s, min(s + 12, len(a_plain)), 1)
            je = scan(e - 1, max(e - 13, -1), -1)
        if js is None or je is None or je < js:
            dropped.append(a_plain[s:e])
            continue
        for k in range(js, je + 1):
            ital[k] = True

    ital = _snap_to_words(b_plain, ital)
    ital = _drop_greek(b_plain, ital)
    ital = _tidy_runs(b_plain, ital)
    return b_plain, ital


def restore_dropcap(abbyy_plain, chunk, log=None):
    """首字下沉的那个大写字母，tesseract 读不出来，ABBYY 读得到。

    每篇讲章正文第一段都是下沉首字。tesseract 的两种败法都见过：
        THE Epistle begins…   → `HE Epistle begins…`        （整个吞掉）
        WITH the free discur… → `Ἶ | Ww" H the free discur…`（糊成一团乱码）
    字虽然从 tesseract 取，这一处必须从 ABBYY 补。

    判据：拿两边开头 60 个字做最长公共块，公共块之前 ABBYY 那一小截
    （≤6 个字、全大写）就是被吞掉的下沉首字，用它换掉 OCR 那一截。
    公共块短于 14 个字就不动 —— 对不牢的时候宁可留着错字。
    """
    a, b = abbyy_plain.lstrip(), chunk.lstrip()
    if len(a) < 30 or len(b) < 30:
        return chunk
    ha, hb = _norm(a[:60]), _norm(b[:60])
    m = difflib.SequenceMatcher(None, ha, hb, autojunk=False) \
        .find_longest_match(0, len(ha), 0, len(hb))
    if m.size < 14 or m.a > 6 or m.b > 14 or (m.a == 0 and m.b == 0):
        return chunk
    pre = a[:m.a]
    if pre and not all(c.isupper() or c.isspace() for c in pre):
        return chunk
    if log is not None:
        log.append((b[:m.b], pre))
    pad = chunk[:len(chunk) - len(b)]
    return pad + pre + b[m.b:]


def transfer_page(pars, ocr_text, dropped=None, dropcaps=None):
    """一页：ABBYY 的段落结构与斜体 → OCR 的字流，出 markdown。

    两步走 —— 先整页粗对一次只为切出段落边界，再**按段细对**搬斜体。
    """
    if dropped is None:
        dropped = []
    if dropcaps is None:
        dropcaps = []
    ab_plains = [strip_sentinels(p)[0] for p in pars]
    ab_all = ''.join(ab_plains)
    ocr_plain, _ = strip_sentinels(ocr_text)
    amap = _charmap(ab_all, ocr_plain)

    cuts, off = [], 0
    for t in ab_plains:
        pos = None
        for x in range(off, min(off + 80, len(ab_all))):
            if x in amap:
                pos = amap[x]
                break
        cuts.append(0 if pos is None else pos)
        off += len(t)
    cuts[0] = 0
    for i in range(1, len(cuts)):           # 单调化，交叉就并进上一段
        cuts[i] = max(cuts[i], cuts[i - 1])

    out = []
    for i, par in enumerate(pars):
        lo = cuts[i]
        hi = cuts[i + 1] if i + 1 < len(cuts) else len(ocr_plain)
        chunk = ocr_plain[lo:hi]
        if not chunk.strip():
            continue
        # 每一段都试。下沉首字不只在页内第一段 —— 讲章开篇那一页，前面还排着
        # 罗马数字、讲题、经文题记三段，限定「页内第一段」会让 30 篇全部漏掉
        # （实测只有导论一篇补上了）。判据本身够紧：ABBYY 那一小截必须 ≤6 个字
        # 且全大写，公共块还得 ≥14 个字，正常段落两边开头一致时根本不触发。
        chunk = restore_dropcap(ab_plains[i], chunk, dropcaps)
        text, ital = _par_italic(par, chunk, dropped)
        out.append(_emit(text, ital))
    return '\n\n'.join(out)


def _emit(text, ital):
    buf, on = [], False
    for k, ch in enumerate(text):
        if ital[k] and not on:
            buf.append('*'); on = True
        elif not ital[k] and on:
            buf.append('*'); on = False
        buf.append(ch)
    if on:
        buf.append('*')
    return ''.join(buf).strip()


RE_SEAM = re.compile(r'([A-Za-z]+)' + HYPH + r'([A-Za-z]+)')
RE_INLINE = re.compile(r'\b([A-Za-z]{2,})-([a-z]{2,})\b')


def learn_compounds(texts):
    """全书的**行内**连字符 → 复合词表。

    `self-sacrificing` / `fellow-men` / `to-day` / `yoke-fellow` 这些，原书本来
    就带连字符；正好断在连字符上时不能把它吃掉。凭据只能是同一部书别处行内
    怎么写 —— 不查词典，不凭直觉（feedback_measure_before_applying_rule）。
    """
    seen = set()
    for t in texts:
        for m in RE_INLINE.finditer(t):
            seen.add((m.group(1).lower(), m.group(2).lower()))
    return seen


def resolve_hyphens(text, compounds, log=None):
    """接缝哨兵 → 连字符或直接拼上。"""
    def repl(m):
        a, b = m.group(1), m.group(2)
        keep = (a.lower(), b.lower()) in compounds
        if log is not None:
            log.append((a + '-' + b, a + ('-' if keep else '') + b, keep))
        return a + ('-' if keep else '') + b
    return RE_SEAM.sub(repl, text).replace(HYPH, '')
