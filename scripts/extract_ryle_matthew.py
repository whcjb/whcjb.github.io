#!/usr/bin/env python3
"""莱尔《马太福音释经默想》英文底本抽取：e-Sword 模块（RTF）→ ryle_raw/matthew/esword_sections.json

    python3 scripts/extract_ryle_matthew.py

底本来源与改动类型见 ryle_raw/matthew/PROVENANCE.md。这一步只做格式转换，不改字：
  斜体 \\i…\\i0         → *…*
  首词小型大写 T\\fs16 HESE → ⟪THESE⟫
  出处 \\ul Gen_12:3\\ulnone → ⟨Gen_12:3⟩（e-Sword 格式，回改成 1857 写法在 collate 一步）
  [Footnote: …]          → ⟦fn⟧，脚注正文另存 notes
加粗（\\b）在模块里只是包在标点和空格上的录入残留，丢弃。
模块在 1:1 一条里先放「(Note, Mr. Ryle's Preface follows these comments.)」这句模块编者说明，
再在注释正文后接 ===== 分隔的序言：说明句丢弃，序言单独抽出。
"""
import json
import re
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'ryle_raw' / 'matthew'
SRC = RAW / 'src' / 'esword' / 'Ryle.cmtx'
OUT = RAW / 'esword_sections.json'

TOKEN = re.compile(r"\\'([0-9a-fA-F]{2})|\\([a-z]+)(-?\d+)? ?|\\([^a-z\r\n])|([{}])|(\r?\n)|([^\\{}\r\n]+)")
HEADER_GROUPS = re.compile(r'\{\\fonttbl.*?\}\}\s*|\{\\colortbl[^}]*\}\s*|\{\\\*\\generator[^}]*\}\s*', re.S)
REF = re.compile(r'\b([1-3]?[A-Z][a-z]{1,2})_(\d+):(\d+(?:[-–,]\s?\d+)*)')


def runs(rtf):
    """RTF → [(text, italic, ul, fs)]，段落边界用 ('\\n\\n', …)。"""
    rtf = HEADER_GROUPS.sub('', rtf)
    out = []
    it = ul = False
    fs = 24
    for m in TOKEN.finditer(rtf):
        hexc, word, num, sym, brace, nl, text = m.groups()
        if text is not None:
            out.append((text, it, ul, fs))
        elif hexc is not None:
            out.append((bytes([int(hexc, 16)]).decode('cp1252'), it, ul, fs))
        elif word is not None:
            if word == 'par':
                out.append(('\n\n', False, False, 24))
            elif word == 'i':
                it = num != '0'
            elif word == 'ul':
                ul = True
            elif word == 'ulnone':
                ul = False
            elif word == 'fs':
                fs = int(num)
            elif word == 'emdash':
                out.append(('—', it, ul, fs))
            elif word == 'endash':
                out.append(('–', it, ul, fs))
            elif word in ('lquote', 'rquote'):
                out.append(("'", it, ul, fs))
            elif word in ('ldblquote', 'rdblquote'):
                out.append(('"', it, ul, fs))
            elif word == 'line':
                out.append((' ', it, ul, fs))
            # 其余（pard/f/cf/b/sb/sa/qj/tab/rtf1…）都是版式，丢弃
        elif sym is not None:
            if sym in '\\{}':
                out.append((sym, it, ul, fs))
            elif sym == '~':
                out.append((' ', it, ul, fs))
    return out


def smallcaps(rs):
    """首字母正常字号 + 紧跟 fs16 的大写串 → 一个小型大写词 ⟪…⟫。"""
    out = []
    i = 0
    while i < len(rs):
        t, it, ul, fs = rs[i]
        if (i + 1 < len(rs) and rs[i + 1][3] == 16 and fs != 16 and re.fullmatch(r'[A-Z]', t[-1:] or '')
                and re.match(r'[A-Z]+', rs[i + 1][0])):
            nxt = rs[i + 1][0]
            m = re.match(r'[A-Z]+', nxt)
            pre = t[:-1]
            if pre:
                out.append((pre, it, ul, fs))
            out.append(('⟪' + t[-1] + m.group(0) + '⟫', it, ul, 24))
            rest = nxt[m.end():]
            if rest:
                out.append((rest, it, ul, 24))
            i += 2
            continue
        out.append((t, it, ul, fs))
        i += 1
    return out


def to_md(rs):
    """runs → 段落列表（markdown 斜体、⟨出处⟩）。"""
    # 合并同属性相邻 run（只看斜体与下划线）
    merged = []
    for t, it, ul, _ in rs:
        if t == '\n\n':
            merged.append(['\n\n', False, False])
            continue
        if merged and merged[-1][0] != '\n\n' and merged[-1][1] == it and merged[-1][2] == ul:
            merged[-1][0] += t
        else:
            merged.append([t, it, ul])
    s = []
    for t, it, ul in merged:
        if t == '\n\n':
            s.append('\n\n')
            continue
        if ul:
            t = REF.sub(lambda m: f'⟨{m.group(0)}⟩', t)
        if it and t.strip():
            lead = t[:len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            s.append(f'{lead}*{t.strip()}*{trail}')
        else:
            s.append(t)
    text = ''.join(s)
    text = re.sub(r'\*\s*\*', '', text)                 # 空斜体
    text = re.sub(r'\*([^*\n]+)\*\*([^*\n]+)\*', r'*\1\2*', text)  # 相邻斜体并一
    paras = [re.sub(r'[ \t]+', ' ', p).strip() for p in text.split('\n\n')]
    return [p for p in paras if p]


FN = re.compile(r'[\[(]Footnote:\s*(.*?)[\])]', re.S)   # 13:24 一条是圆括号写法


def split_notes(paras):
    """行内 [Footnote: …] → ⟦fn⟧。跨段的长注（25:1、26:36、27:1、27:45、28:11）从开头那段一直收到
    以 ] 收尾的那段，注内分段用空行保留。"""
    notes, out = [], []
    i = 0
    while i < len(paras):
        p = paras[i]
        k = p.find('[Footnote:')
        if k >= 0 and ']' not in p[k:]:
            body = [p[k + len('[Footnote:'):].strip()]
            i += 1
            while ']' not in paras[i]:
                body.append(paras[i])
                i += 1
            last = paras[i]
            j = last.index(']')
            body.append(last[:j].rstrip())
            notes.append('\n\n'.join(body))
            # 注在段中收尾（27:1）：] 之后的正文接回起注的那段
            out.append((p[:k].rstrip() + '⟦fn⟧ ' + last[j + 1:].strip()).strip())
            i += 1
            continue

        def take(m):
            notes.append(m.group(1).strip())
            return '⟦fn⟧'
        out.append(FN.sub(take, p))
        i += 1
    return out, notes


def main():
    db = sqlite3.connect(SRC)
    rows = db.execute('select ChapterBegin, VerseBegin, ChapterEnd, VerseEnd, Comments from Verses '
                      'where Book=40 order by ChapterBegin, VerseBegin').fetchall()
    sections, preface = [], None
    for c1, v1, c2, v2, rtf in rows:
        paras = to_md(smallcaps(runs(rtf)))
        if c1 == 1 and v1 == 1:
            assert paras[0].startswith('*(Note'), paras[0][:80]
            paras = paras[1:]
            k = next(i for i, p in enumerate(paras) if p.startswith('====='))
            body, pre = paras[:k], [p for p in paras[k + 1:] if not p.startswith('=====')]
            assert pre[0].startswith('Preface'), pre[0]
            preface = pre[1:]
            paras = body
        paras, notes = split_notes(paras)
        sections.append(dict(ch=c1, v1=v1, ch2=c2, v2=v2, paras=paras, notes=notes))
    OUT.write_text(json.dumps(dict(preface=preface, sections=sections), ensure_ascii=False, indent=1),
                   encoding='utf-8')
    nw = sum(len(' '.join(s['paras']).split()) for s in sections)
    print(f'{len(sections)} 段，{nw} 词，脚注 {sum(len(s["notes"]) for s in sections)}，序言 {len(preface)} 段 → {OUT}')


if __name__ == '__main__':
    main()
