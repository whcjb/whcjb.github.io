#!/usr/bin/env python3
"""古治《圣徒的祭：诗篇 116 篇注释》→ gouge/psalm116/（英文版），底本 1868 年 Nichol 重印本 OCR。

    python3 scripts/publish_gouge_psalm116.py

为什么不用 TCP：EEBO-TCP A01981 是一份错配的录入本——正文前半录的是 J. Gough 的剧本《The Strange Discovery》(1640)，
古治这本只录了后半（前 80 余页即第 1–39 小节缺失，此外 8 处各缺 2–4 页，书末也缺）。拼起来会有十来处 1632／1868 两种拼法来回切换，
所以整本用 1868 年 Nichol 本（IA davidsblessedman00smit，影像第 297–442 页；用户 2026-11-19 认可），TCP 覆盖的那六成拿来当第三证人。

清理（nichol1868_ocr.py + 本脚本）：
  ① ABBYY 段落 → ② tesseract 按位置对证 → ①' 符号形／字形规则 →
  ③ 真词互换（两条流都是真词但读法不同，如 tilings/things、laud/land）：TCP 在同一位置（左右各 3 词定位）与哪一边一致就取哪一边；
     TCP 未覆盖或两边都不一致的照 ABBYY 留着，记入 gouge_raw/psalm116/disagree_left.tsv。
  ④ 看图判读表 gouge_raw/psalm116/fixes.tsv（原串须全书唯一）。
结构：「Ver. N.」段起一节经文、一页；其前的总论（第 1–3 小节）一页；「Sec. N.」段首的斜体是小节标题，单成 h4。
编者／原书旁注（6 号字）收在各页末「Notes」。页边经节标记、页眉不收；合订本页码以 p.N 锚点标在页内。
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nichol1868_ocr as n          # noqa: E402
import publish_tcp_psalm as tp      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'gouge_raw' / 'psalm116'
TEI = '{http://www.tei-c.org/ns/1.0}'
P = 'gg'
BODY = (304, 442)
FRONT = [('dedication', 'The Epistle Dedicatory', '献辞', 299, 301),
         ('to-blackfriars', 'To my Beloved Parishioners of Blackfriars', '致黑衣修士区堂众', 302, 303)]
CFG = dict(tcp='—', author='gouge', book='psalm116', P=P, c0='#3d1d5a', c1='#592b82', psalm=116,
           short='Gouge on Psalm 116', hero='Psalm 116', year='1868',
           title_en="The Saints' Sacrifice: A Commentary on Psalm CXVI",
           tagline="William Gouge · The Saints' Sacrifice",
           edition='First published London 1632 · text of the Edinburgh reprint, James Nichol, 1868')


def sk(w):
    w = n.norm(w).replace('v', 'u').replace('j', 'i').replace('y', 'i')
    w = re.sub(r'(.)\1', r'\1', w)
    return w[:-1] if w.endswith('e') and len(w) > 3 else w


def tcp_index():
    """TCP 古治部分（跳过剧本的 act/scene/prologue）→ sk 词序列与 3-gram 索引。"""
    r = ET.parse(RAW / 'src' / 'A01981.xml').getroot()
    words = []
    for d in r.iter(TEI + 'div'):
        if d.get('type') == 'section':
            words += [sk(x) for x in n.WORD.findall(''.join(d.itertext()).replace('ſ', 's'))]
    idx = {}
    for i in range(len(words) - 2):
        idx.setdefault(tuple(words[i:i + 3]), []).append(i)
    return words, idx


def tcp_vote(left, right, words, idx):
    """左 3 词、右 3 词都在 TCP 里相邻出现（中间恰 1 词）→ 返回中间那个词（sk 形），否则 None。"""
    for i in idx.get(tuple(left), []):
        if tuple(words[i + 4:i + 7]) == tuple(right):
            return words[i + 3]
    return None


def clean(text, wit, tcp, left_log):
    led = []
    t, _ = n.repair(text, wit, led)
    t = n.glyph_repair(t, led)
    # ③ 真词互换：TCP 投票
    words, idx = tcp
    plain = t.replace(n.IT_ON, ' ').replace(n.IT_OFF, ' ')
    toks = list(n.WORD.finditer(plain))
    reps = {}
    for a, b, _ in n.disagree(t, wit):
        for k, m in enumerate(toks):
            if m.group() != a or k < 3 or k + 3 >= len(toks):
                continue
            left = [sk(x.group()) for x in toks[k - 3:k]]
            right = [sk(x.group()) for x in toks[k + 1:k + 4]]
            v = tcp_vote(left, right, words, idx)
            if v is not None and v == sk(b) and v != sk(a):
                reps[k] = b if not a[:1].isupper() else b[:1].upper() + b[1:]
            elif v is None or v != sk(a):
                left_log.append((a, b, ' '.join(x.group() for x in toks[max(0, k - 5):k + 6])))
            break
    if reps:
        out, last = [], 0
        for k in sorted(reps):
            m = toks[k]
            out.append(t[last:m.start()])
            out.append(reps[k])
            last = m.end()
        out.append(t[last:])
        t = ''.join(out)
    return t


def balance(t):
    """斜体哨兵配平：没开就关的关标记、到末尾没关的开标记，一律删。"""
    out, op = [], None
    for ch in t:
        if ch == n.IT_ON:
            if op is not None:
                continue
            op = len(out)
        elif ch == n.IT_OFF:
            if op is None:
                continue
            op = None
        out.append(ch)
    if op is not None:
        del out[op]
    return ''.join(out)


def heb(m):
    """(T13rT,)、(pn)、(p2{)：合订本在英文后括注希伯来原词，拉丁引擎读成乱码；判据：括号内不是真词／经节号／罗马数字。"""
    inner = m.group(1).replace(n.IT_ON, '').replace(n.IT_OFF, '').strip(' ,;')
    if not inner or re.fullmatch(r'[\divxlcIVXLC.,:;&\s-]+', inner) or re.fullmatch(r'[A-Za-z]+', inner) and n.is_word(inner):
        return m.group(0)
    toks = re.findall(r'[A-Za-z]+', inner)
    if toks and all(n.is_word(x) for x in toks) and not re.search(r'[\d{}\[\]^]', inner):
        return m.group(0)
    return f'(<span class="{P}-gap" title="Hebrew in the 1868 edition, not read by OCR（原书此处是希伯来文，OCR 读不出）">〈Hebrew〉</span>)'


def md(t):
    """哨兵层面处理斜体（分得清开／关）：合并相邻斜体段、删 OCR 文本里原有的 *（脚注号或噪点），最后才转 markdown。"""
    t = t.replace('*', '')
    t = re.sub(r'\s*■\s*', ' ', t)                                    # 污点：先删，免得斜体开头留空白
    t = re.sub(r'\\yi\[', 'will', t)                                  # 诗 85 斜体乱码（影像核：will）
    t = re.sub(r'(?<=[A-Za-z\]\[])\\+(?=\s|' + n.IT_OFF + r'|$)', '', t)   # 词尾孤立反斜杠（vrA\）会转义后面的星号
    t = re.sub(r'\(([^()]{1,12})\)', heb, t)                            # 括号里的希伯来文乱码 → 〈Hebrew〉（在斜体转换之前）
    t = balance(t)
    t = re.sub(n.IT_OFF + r'(\s*)' + n.IT_ON, r'\1', t)
    t = re.sub(n.IT_ON + r'(\s*)' + n.IT_OFF, r'\1', t)               # 空斜体段
    t = re.sub(n.IT_ON + r'(\s*)', r'\1' + n.IT_ON, t)                 # 开标记后的空白挪到外面
    t = re.sub(r'(\s*)' + n.IT_OFF, n.IT_OFF + r'\1', t)               # 关标记前的空白挪到外面
    t = t.replace(n.IT_ON, '*').replace(n.IT_OFF, '*')
    t = re.sub(r'\s*■\s*', ' ', t)
    t = re.sub(r'(?<=[A-Za-z.,;:\'’])[\^}]+(?=[\s,.;:\'’)*]|$)', '', t)     # 脚注号残渣：third^ branch、deliverances}
    t = re.sub(r'(?m)^(\d+)\. ', r'\1\\. ', t)          # 行首序号别被 kramdown 当列表
    t = t.replace('|', '')
    return re.sub(r' {2,}', ' ', t).strip()


def assemble(lo, hi, tcp, left_log):
    """lo–hi 页 → 段落流 [{'kind': body/note/head/verse, 'text', 'page'}]，跨栏跨页续段已并。"""
    pages = n.load()
    out = []
    for i in range(lo, hi + 1):
        pp = n.printed_page(i)
        first_on_page = True
        for bi, b in enumerate(pages[i]):
            if n.kind(b) != 'text':
                continue
            wit = n.tess(i, bi, b)
            for j, p in enumerate(b['pars']):
                t = clean(p['text'], wit, tcp, left_log)
                t = re.sub('^Ver\\. ' + n.IT_ON + r'li\. ', 'Ver. 14. ' + n.IT_ON, t)   # p.91 节号读进了斜体（影像核：14）
                plain = t.replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()
                if not plain:
                    continue
                if p['fs'] and p['fs'] < 6.5:
                    out.append(dict(kind='note', text=t, page=pp))
                    continue
                if p['fs'] >= 9:                                  # 卷首大字（书名等）
                    out.append(dict(kind='big', text=t, page=pp))
                    continue
                new = 'startIndent' in p['attrs'] or re.match(r'(Sec|Ver)[.,]', plain)
                anchor = f'<span class="{P}-pb" id="p{pp}" data-p="{pp}"></span>' if (first_on_page and pp) else ''
                first_on_page = False if anchor or not first_on_page else first_on_page
                prev = next((x for x in reversed(out) if x['kind'] == 'body'), None)
                if not new and j == 0 and prev is not None:       # 栏首／页首无首行缩进 → 上一段的续行
                    pt = prev['text']
                    if pt.rstrip(n.IT_OFF).endswith('-') and plain[:1].islower():
                        prev['text'] = pt.rstrip(n.IT_OFF)[:-1] + pt[len(pt.rstrip(n.IT_OFF)):] + anchor + t
                    else:
                        prev['text'] = pt + ' ' + anchor + t
                    continue
                out.append(dict(kind='body', text=anchor + t, page=pp))
    return out


BOUNDS = [(9, '1', '1–2'), (19, '3', '3'), (23, '4', '4'), (29, '5', '5'), (38, '6', '6'), (44, '7', '7'), (51, '8', '8'),
          (57, '9', '9'), (68, '10', '10–11'), (78, '12', '12–13'), (91, '14', '14'), (100, '15', '15'), (105, '16', '16'),
          (114, '17', '17'), (122, '18', '18'), (124, '19', '19')]
SEC = re.compile(r'^(Sec[.,]\s*[\dIlSGO.]+\.?\s*)' + n.IT_ON + r'(.*?)' + n.IT_OFF + r'\s*(.*)$', re.S)
VER = re.compile(r'^(?:<span[^>]*></span>)?(Ver[.,]\s*[\dILl]+[.,]?\s*)' + n.IT_ON + r'(.*?)' + n.IT_OFF + r'\s*(.*)$', re.S)


def render(stream):
    """段落流 → markdown；小节标题 h4、经文框、页末注。"""
    body, notes = [], []
    for x in stream:
        t = x['text']
        if x['kind'] == 'note':
            notes.append(md(t))
            continue
        if x['kind'] == 'big':
            body.append(f'<p class="{P}-quote">{md(t)}</p>')
            continue
        anchor = ''
        m0 = re.match(r'^(<span class="[^"]+-pb"[^>]*></span>)', t)
        if m0:
            anchor, t = m0.group(1), t[m0.end():]
        m = SEC.match(t)
        if m:
            num = re.sub(r'\D', '', m.group(1).replace('l', '1').replace('I', '1').replace('S', '5')
                         .replace('G', '6').replace('O', '0')) or '?'
            body.append(f'#### {anchor}<span class="{P}-sec">Sec. {num}.</span> {md(n.IT_ON + m.group(2) + n.IT_OFF)}')
            if m.group(3).strip():
                body.append(md(m.group(3)))
            continue
        m = VER.match(t)
        if m:
            body.append(f'<div class="{P}-text" markdown="1">\n\n{anchor}**{md(m.group(1)).strip()}** '
                        f'{md(n.IT_ON + m.group(2) + n.IT_OFF)}\n\n</div>')
            if m.group(3).strip():
                body.append(md(m.group(3)))
            continue
        body.append(anchor + md(t))
    out = '\n\n'.join(body)
    if notes:
        out += f'\n\n<div class="{P}-notes" markdown="1">\n\n<p class="{P}-notes-h">Notes</p>\n\n' + \
               '\n\n'.join(notes) + '\n\n</div>'
    return out


def apply_fixes(text):
    f = RAW / 'fixes.tsv'
    if not f.exists():
        return text
    for line in f.read_text(encoding='utf-8').splitlines():
        if not line or line.startswith('#'):
            continue
        old, new = line.split('\t')
        c = text.count(old)
        if c != 1:
            print(f'⚠️ 判读表条目命中 {c} 次：{old!r}')
            continue
        text = text.replace(old, new)
    return text


def main():
    tcp = tcp_index()
    left_log = []
    stream = assemble(BODY[0], BODY[1], tcp, left_log)
    # 按分界表切页（印本页码, OCR 读出的节号, 页标签）：古治第 2 节讲在第 1 节下、第 13 节讲在第 12 节下，第 10–11 节合讲；
    # 第 17 节开头先把 17–19 节一并引出，第 18、19 节在第 122、124 页才各自展开；第 11、16、19 节中途重引半节经文当小标题。
    # 表外的「Ver.」段一律只当小标题（经文框），不起新页。
    units, cur, verse, todo = [], [], 'intro', list(BOUNDS)
    for x in stream:
        plain = re.sub(r'<[^>]+>', '', x['text']).replace(n.IT_ON, '').replace(n.IT_OFF, '').strip()
        m = re.match(r'Ver[.,]\s*(\S+?)[.,\s]', plain) if x['kind'] == 'body' else None
        if m and todo and x['page'] == todo[0][0] and m.group(1).strip('.') == todo[0][1]:
            if cur:
                units.append((verse, cur))
            cur, verse = [], todo.pop(0)[2]
        cur.append(x)
    units.append((verse, cur))
    assert not todo, todo
    fronts = []
    for slug, en, zh, a, b in FRONT:
        fronts.append(dict(slug=slug, title=en, zh=zh, md=apply_fixes(render(assemble(a, b, tcp, left_log)))))
    U = []
    for verse, xs in units:
        pg = [x['page'] for x in xs if x['page']]
        U.append(dict(verse=verse, part=None, pages=(min(pg), max(pg)) if pg else None, contents=[],
                      md=apply_fixes(render(xs)), slug='introduction' if verse == 'intro' else f'v{verse.replace("–", "-")}',
                      name='Introduction' if verse == 'intro' else None))
    vs = [u['verse'] for u in U]
    print('经节页：', vs)
    (RAW / 'disagree_left.tsv').write_text('\n'.join('\t'.join(x) for x in left_log) + '\n', encoding='utf-8')
    tot = bad = 0
    for u in U:
        b, c = n.nonwords(re.sub(r'<[^>]+>', ' ', u['md']))
        tot += c
        bad += len(b)
    print(f'正文 {tot} 词，残余非词 {bad}（{bad / tot:.2%}）；未决的真词互换 {len(left_log)} 处')
    c = dict(CFG, about_en=ABOUT_EN, about_zh=ABOUT_ZH, omitted_en='', omitted_zh='', about_full=True)
    tp.write_layouts('gouge-psalm116', c, force='--layouts' in sys.argv)
    tp.publish('gouge-psalm116', c, fronts, U, [], {}, ROOT / 'gouge' / 'psalm116', '/gouge/psalm116/', RAW)


ABOUT_EN = ("Gouge, for forty-five years minister of St Anne's, Blackfriars, published this commentary on Psalm 116 in 1632 "
            "and dedicated it to Robert, Lord Rich, Earl of Warwick, and to his parishioners. The text given here is that of "
            "the Edinburgh reprint of 1868 (Nichol's Series of Commentaries), read by OCR from the Princeton copy "
            "(Internet Archive davidsblessedman00smit) and checked against a second, independent OCR, against the 1632 "
            "edition where its keyed transcription survives (EEBO-TCP A01981, which lacks about a third of the book), "
            "and against the page images. The opening sections on the whole psalm and each verse are one page; "
            "Gouge's 128 numbered sections are given as headings, and the notes at the foot of the 1868 pages are "
            "collected at the end of each page. The page numbers of the 1868 edition are marked in the text. Hebrew words, "
            "which OCR cannot read, are marked in red. OCR errors still remain, chiefly in the italic passages (verse "
            "texts and section headings); they are being corrected against the page images.")
ABOUT_ZH = ("古治在伦敦黑衣修士区圣安妮堂牧会四十五年，1632 年出版这部诗篇 116 篇注释，献给沃里克伯爵罗伯特·里奇勋爵及本堂会众。"
            "本站正文据 1868 年爱丁堡 Nichol《清教徒注释丛书》重印本，用普林斯顿藏本的扫描件（IA davidsblessedman00smit）OCR 识读，"
            "并与另一份独立 OCR、1632 年原版的录入本（EEBO-TCP A01981，缺全书约三分之一）及页面影像对照校过。"
            "开头论全篇的几节一页，每节经文一页；古治全书编号的 128 小节作小标题，1868 年版页脚的注收在各页之末；文中标出 1868 年版页码。"
            "希伯来文 OCR 读不出，以红字标出。目前仍有 OCR 错误，主要在斜体段落（经文与小节标题），正在对照页面影像逐页校正。")

if __name__ == '__main__':
    main()
