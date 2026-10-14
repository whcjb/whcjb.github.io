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


LEX_OK = None          # extract_johnstone 填：判一个词是不是真词


def _words(t):
    return re.findall(r"[A-Za-z]{2,}", re.sub(r'[Ͱ-Ͽἀ-῿]+', ' ', t))


def _nonword(t, lo=8):
    w = _words(t)
    if len(w) < lo or LEX_OK is None:
        return None
    return sum(1 for x in w if not LEX_OK(x.lower())) / len(w)


FUNC_WORDS = set(
    'the a an and or but of to in on at by as if is it he we they that this '
    'not for with from into all his her its our your my be been was were '
    'had has have will would shall should may might can could do did'.split())


def _fill_gaps(ab_text, chunk, log):
    """ABBYY 有、我们这边**整个漏掉**的词，补回去。

    tesseract 偶尔会吞词：`a bereaved ⟨heart,⟩ even amid the deepest`、
    `with profoundest thankful-⟨ness.⟩`（用户截图）。整段换流看不见它——
    漏词的那一段 tesseract 反而比 ABBYY 更干净（0.013 vs 0.075）。

    三道闸，少一道就会把 OCR 错字当成「缺词」补成重复：
    ① 缺口两侧必须是**完全对齐**的长块（各 ≥3 个词）——词只是拼错时，
       两侧不会同时对齐（`ποΐ` ← `not`、`411.` ← `all.'` 都是这么滤掉的）；
    ② 缺的每个词要么 ≥4 个字母、要么是常见虚词——`lo`/`ver`/`J` 这类是
       ABBYY 自己的碎片，不是真缺词；
    ③ 一次最多补 6 个词。
    """
    wa = [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', ab_text)]
    wc = [(m.group(0), m.start(), m.end()) for m in re.finditer(r'\S+', chunk)]
    na = [re.sub(r'[^A-Za-z]', '', x[0]).lower() for x in wa]
    nc = [re.sub(r'[^A-Za-z]', '', x[0]).lower() for x in wc]
    if len(na) < 20 or LEX_OK is None:
        return chunk
    ops = difflib.SequenceMatcher(None, na, nc, autojunk=False).get_opcodes()
    ins = []
    for k, (tag, i1, i2, j1, j2) in enumerate(ops):
        if tag != 'delete' or not (1 <= i2 - i1 <= 6):
            continue
        prev = ops[k - 1] if k else None
        nxt = ops[k + 1] if k + 1 < len(ops) else None
        if not prev or prev[0] != 'equal' or prev[2] - prev[1] < 3:
            continue
        if not nxt or nxt[0] != 'equal' or nxt[2] - nxt[1] < 3:
            continue
        seg = na[i1:i2]
        if not all(w and LEX_OK(w) and (len(w) >= 4 or w in FUNC_WORDS)
                   for w in seg):
            continue
        ins.append((wc[j1][1], ab_text[wa[i1][1]:wa[i2 - 1][2]], 0))

    # 词被**截断**：我们这边停在连字符上（`thankful-`），ABBYY 给出整词
    # （`thankfulness.`）。这是「替换」不是「缺失」，上面那条判据看不见。
    # 只认一对一、且我们这半截是对方的前缀——补的永远是词尾那几个字母。
    # 词被**截断**：我们这边停在连字符上（`thankful-`），ABBYY 给出整词
    # （`thankfulness.`）。这是「替换」不是「缺失」，上面那条判据看不见。
    # 截断处前后常常还夹着别的错字（`profoundcst` ← `profoundest`），所以
    # 在整个替换块里找配对，而不是要求一对一。
    # 只认「我们这半截是对方的前缀」——补的永远是词尾那几个字母。
    for tag, i1, i2, j1, j2 in ops:
        if tag != 'replace' or i2 - i1 > 3 or j2 - j1 > 4:
            continue
        for jj in range(j1, j2):
            ours = wc[jj][0].rstrip('*\\ ')
            if not ours.endswith('-') or len(ours) < 4:
                continue
            stem = re.sub(r'[^A-Za-z]', '', ours).lower()
            hit = [ii for ii in range(i1, i2)
                   if na[ii].startswith(stem) and len(na[ii]) > len(stem)
                   and LEX_OK(na[ii])]
            if len(hit) != 1:
                continue
            # **后半截还在的，是断词不是截断**：补全会写出
            # `appearance ance`、`immediate diate` 这样的重复（实测 13 处）。
            # 直接看紧邻的下一个词是不是正好是缺的那几个字母。
            rest = na[hit[0]][len(stem):]
            if jj + 1 < len(wc) and nc[jj + 1].startswith(rest[:3]):
                continue
            end = jj + 1
            if end < j2 and not re.search(r'[A-Za-z]', wc[end][0]):
                end += 1
            ins.append((wc[jj][1], re.sub(r'[ \t]{2,}', ' ', wa[hit[0]][0]),
                        wc[end - 1][2] - wc[jj][1]))
            break

    if not ins:
        return chunk
    ins.sort()
    out, last = [], 0
    for at, text, skip in ins:
        if at < last:
            continue
        out.append(chunk[last:at] + re.sub(r'[ \t]{2,}', ' ', text)
                   + ('' if skip else ' '))
        last = at + skip
        log.append(('⟨截断⟩' if skip else '⟨缺⟩', text.strip()[:60]))
    return ''.join(out) + chunk[last:]


def _better_stream(ab_text, chunk, log):
    """两条字流里挑读得对的那一条——**按段**挑，不按页。

    正文的字一向取 tesseract，版面与斜体取 ABBYY。可扫描件有局部受损时，
    一条流会在某几段上整段读废，另一条却好好的：
        tesseract  `. or ων μος the Coane pe sar to them a very gloomy one.`
        ABBYY      `tension of Christianity among the Gentiles, could not but
                    appear to them a very gloomy one.`
    （leaf 215，用户截图）。**页级判据看不见它**——整页的非词率被正常段落
    拉平了，全书只报出 1 页，且不含这一页。

    判据：两边都 ≥8 个词，且 tesseract 的非词率比 ABBYY 高 20 个百分点
    以上。两条都是非生成式引擎，换的是「读得对的那一份」，不是猜。
    """
    ra = _nonword(ab_text)
    if ra is None or ra > 0.1:
        return _fill_gaps(ab_text, chunk, log)
    ro = _nonword(chunk, 4)
    if ro is None:
        return chunk
    # 两条路都要 ABBYY 这一侧干净（非词率 ≤10%）：
    #   ① 非词率高出 20 个百分点；
    #   ② **词数骤降**——tesseract 把整段读没了，剩下的几个字连 8 个词
    #      都凑不齐，光看非词率的最小词数闸就把它挡在外面（leaf 215 实测：
    #      `. er κοὐ» 4 Sr or ων μος the Coane` 只有 5 个拉丁词）。
    drop = len(_words(chunk)) < len(_words(ab_text)) * 0.6
    # ③ **真词错字**非词率看不见：`pe sar` ← `appear`，两个都在词表里，
    #    两边的非词率都是 0。可两条字流在同一段上本该说同一句话，差得太
    #    多就说明有一条读错了。只在「ABBYY 这侧干净、而 tesseract 并不
    #    更干净」时才按 ABBYY 走——tesseract 更干净的那些段不碰
    #    （诗那一段就是 tesseract 对、ABBYY 糊）。
    wo, wa = [w.lower() for w in _words(chunk)], [w.lower() for w in _words(ab_text)]
    far = (ro >= ra and len(wa) >= 8
           and difflib.SequenceMatcher(None, wo, wa, autojunk=False).ratio() < 0.8)
    if not (ro > ra + 0.2 or (drop and ro > 0.3) or far):
        return _fill_gaps(ab_text, chunk, log)
    log.append((chunk.strip()[:60], ab_text.strip()[:60]))
    # ABBYY 的行内多空格要压掉，直撇号要转成弯引号——不然搬过来的那段
    # 在满页弯引号里一眼就看得出来。
    t = re.sub(r'[ \t]{2,}', ' ', ab_text)
    t = re.sub(r"(?<=[A-Za-z,.;:!?])'", '’', t)
    t = re.sub(r"'(?=[A-Za-z‘])", '‘', t)
    return t


def transfer_page(pars, ocr_text, dropped=None, dropcaps=None, verse=None,
                  swapped=None):
    """一页：ABBYY 的段落结构与斜体 → OCR 的字流，出 markdown。

    两步走 —— 先整页粗对一次只为切出段落边界，再**按段细对**搬斜体。
    """
    if dropped is None:
        dropped = []
    if dropcaps is None:
        dropcaps = []
    if swapped is None:
        swapped = []
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
        # 这一段 tesseract 是不是读废了：废了就改用 ABBYY 的字。
        chunk = _better_stream(ab_plains[i], chunk, swapped)
        # 每一段都试。下沉首字不只在页内第一段 —— 讲章开篇那一页，前面还排着
        # 罗马数字、讲题、经文题记三段，限定「页内第一段」会让 30 篇全部漏掉
        # （实测只有导论一篇补上了）。判据本身够紧：ABBYY 那一小截必须 ≤6 个字
        # 且全大写，公共块还得 ≥14 个字，正常段落两边开头一致时根本不触发。
        chunk = restore_dropcap(ab_plains[i], chunk, dropcaps)
        text, ital = _par_italic(par, chunk, dropped)
        md = _emit(text, ital)
        v = verse[i] if verse and i < len(verse) else None
        if v:
            md = _as_verse(md, v)
            # 同一节诗被 ABBYY 拆成的续段，并回上一段诗块（见 verse_pars）
            if (getattr(v, 'cont', False) and out
                    and out[-1].startswith('<span class="jh-verse">')
                    and out[-1].endswith('</span>')
                    and md.startswith('<span class="jh-verse">')):
                out[-1] = out[-1][:-len('</span>')] + '<br>' + md[len('<span class="jh-verse">'):]
                continue
        out.append(md)
    return '\n\n'.join(out)


def _as_verse(md, lines):
    """一段诗拆回一行一句，包成 `.jh-verse`。

    哪一段是诗由 ABBYY 的行坐标定（见 extract_johnstone.verse_pars），
    这里只管**切点**：按原书各行的字数比例摊，落点就近找空格。不拿
    ABBYY 的行文字去匹配——它那份 OCR 更糊（`Animula vagula` 读成
    `Animiila vagiila`），匹配不上就整块丢了。

    切点可能落在斜体区中间，那会留下落单的星号。所以每切一刀就数一次
    未转义星号，奇数就补上闭合、下一行开头补回开启。
    """
    if len(lines) == 1 and len(md) >= 8:
        return '<span class="jh-verse">' + md + '</span>'
    total = sum(len(x) for x in lines)
    if total < 20 or len(lines) < 2 or len(md) < 20:
        return md
    cuts, acc = [], 0
    for x in lines[:-1]:
        acc += len(x)
        k = int(round(len(md) * acc / total))
        # 按字数比例摊的切点会差一两个词（`bear in / mind How` ← 印面
        # `bear in mind / How`）。在比例点附近的空格里挑「前一个词跟 ABBYY
        # 这一行末词最像」的那个；ABBYY 的字糊，用相似度不用相等。
        words = [w for w in x.split() if re.search(r'[A-Za-z]', w)]
        tail = re.sub(r'[^a-z]', '', words[-1].lower()) if words else ''
        best, bs = md.rfind(' ', 0, min(k + 1, len(md))), -1.0
        if len(tail) >= 2:
            for mm in re.finditer(' ', md):
                j = mm.start()
                if abs(j - k) > max(12, len(x) // 3):
                    continue
                w = md[:j].split()[-1] if md[:j].split() else ''
                w = re.sub(r'[^a-z]', '', w.lower())
                sc = difflib.SequenceMatcher(None, w, tail).ratio() - abs(j - k) / 400
                if sc > bs:
                    best, bs = j, sc
            if bs < 0.6:
                best = md.rfind(' ', 0, min(k + 1, len(md)))
            else:
                # 行末孤立的标点（`control ;`、`three, —`）跟着本行走
                while True:
                    m2 = re.match(r' ([^\sA-Za-z0-9*]+)(?= |$)', md[best:])
                    if not m2 or best + m2.end() >= len(md):
                        break
                    best += m2.end()
        k = best
        if k > 0 and (not cuts or k > cuts[-1] + 4):
            cuts.append(k)
    if not cuts:
        return md
    parts, prev = [], 0
    for k in cuts:
        parts.append(md[prev:k].strip())
        prev = k + 1
    parts.append(md[prev:].strip())
    parts = [x for x in parts if x]
    if len(parts) < 2:
        return md
    fixed, open_it = [], False
    for x in parts:
        if open_it:
            x = '*' + x
        n = len(re.findall(r'(?<!\\)\*', x))
        open_it = n % 2 == 1
        if open_it:
            x += '*'
        fixed.append(x)
    return '<span class="jh-verse">' + '<br>'.join(fixed) + '</span>'


def tighten_italics(par):
    """斜体标记贴着空格时，把标记往里收。

    markdown 的强调**开标记后面不许跟空白、闭标记前面不许有空白**，否则
    那一只星号成了字面星号，而配对的另一只反倒去开一段新的强调：
        源文  `In ‘* all things ’*—ecclesiastical procedure…`
        页面  `In ‘* all things ’—ecclesiastical…`（后面整段都成了斜体）
    星号奇偶闸看不见它——数目是对的，位置不对（用户截图）。

    标记位置本来就是从 ABBYY 的斜体区间搬过来的，边界差一个空格很正常；
    把空格挪到标记外面，意思不变。开闭按出现次序配对，只动贴着空白的那些。
    """
    # 相邻的两只星号是**空强调**，渲染出来什么都不是，只会把中间的字
    # 挤掉。全书 3 处，都落在页缝上（`extraordinary com-` ⟂ `**anion`），
    # 是页顶噪点被当成了斜体标记。成对删掉，奇偶不受影响。
    par = re.sub(r'(?<!\\)\*(?<!\\)\*', '', par)
    pos = [m.start() for m in re.finditer(r'(?<!\\)\*', par)]
    if len(pos) < 2:
        return par
    cuts = []
    for k in range(0, len(pos) - 1, 2):
        a, b = pos[k], pos[k + 1]
        na = a
        while na + 1 < b and par[na + 1].isspace():
            na += 1
        nb = b
        while nb - 1 > na and par[nb - 1].isspace():
            nb -= 1
        if nb <= na + 1:          # 区间里只剩空白，整对放弃
            continue
        if na != a or nb != b:
            cuts.append((a, na, nb, b))
    if not cuts:
        return par
    out, last = [], 0
    for a, na, nb, b in cuts:
        out.append(par[last:a] + par[a + 1:na + 1] + '*' + par[na + 1:nb]
                   + '*' + par[nb:b])
        last = b + 1
    return ''.join(out) + par[last:]


def _emit(text, ital):
    """斜体标志表 → markdown。

    **正文里原有的星号必须转义。** 原书拿 `*` 当脚注符，扫描噪点也会吐出
    星号；它们跟我们加的斜体标记混在一起，kramdown 按奇偶配对，一个落单
    就把后面整段的标记全部错位、原样打印出来。
    判据只有一条「星号个数必须成对」看得见这类（feedback_fix_table_makes_errors）。
    """
    buf, on = [], False
    for k, ch in enumerate(text):
        if ch == '*':
            if ital[k] and not on:
                buf.append('*'); on = True
            elif not ital[k] and on:
                buf.append('*'); on = False
            buf.append('\\*')
            continue
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
