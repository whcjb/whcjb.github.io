#!/usr/bin/env python3
"""判词典：判断一个 token 是不是「真词」。OCR 修复全靠它当守门人。

只在 token **不是**真词时才允许改动——这条约束是整个修复流程唯一的安全网，
没有它就会把 shews/connexion 这类 19 世纪拼法「改正」成现代拼法，属于篡改
底本（feedback_pdf_verify_before_change）。
"""
import re
from pathlib import Path

WEB2 = ['/usr/share/dict/web2', '/usr/share/dict/web2a', '/usr/share/dict/words']
EXTRA = Path(__file__).resolve().parent.parent / 'alexander_raw/psalms/lexicon_extra.txt'

ROMAN = re.compile(r'^[ivxlcdm]+$', re.I)


def _inflect(w):
    out = {w + 's', w + "'s", w + "s'", w + 'ly', w + 'ness', w + 'less'}
    if w.endswith(('s', 'x', 'z', 'ch', 'sh')):
        out.add(w + 'es')
    if w.endswith('e'):
        out |= {w[:-1] + 'ing', w + 'd', w[:-1] + 'es', w + 'st', w[:-1] + 'er'}
    elif w.endswith('y') and len(w) > 2 and w[-2] not in 'aeiou':
        # imply → implying（-y 动词加 -ing 不换 i，之前漏了这条，
        # 结果 implying/supplying/qualifying 全被当成错字）
        out |= {w[:-1] + 'ies', w[:-1] + 'ied', w[:-1] + 'ier', w[:-1] + 'iest',
                w[:-1] + 'ily', w[:-1] + 'iness', w + 'ing'}
    else:
        out |= {w + 'ed', w + 'ing', w + 'er', w + 'est'}
        # 单音节短元音结尾要双写辅音：refer→referred, commit→committed
        if len(w) > 2 and w[-1] not in 'aeiouwxy' and w[-2] in 'aeiou' and w[-3] not in 'aeiou':
            out |= {w + w[-1] + 'ed', w + w[-1] + 'ing', w + w[-1] + 'er', w + w[-1] + 'est'}
    return out


def build():
    base = set()
    for p in WEB2:
        try:
            base |= {l.strip().lower() for l in open(p, encoding='utf-8', errors='ignore') if l.strip()}
        except FileNotFoundError:
            pass
    lex = set(base)
    for w in base:
        if len(w) >= 3:
            lex |= _inflect(w)
    if EXTRA.exists():
        for line in open(EXTRA, encoding='utf-8'):
            for w in line.split('#')[0].split():
                w = w.lower()
                lex.add(w)
                if len(w) >= 3:
                    lex |= _inflect(w)
    return lex


ARCHAIC = re.compile(r'^(.*?)(eth|est)$')


def is_word(tok, lex):
    t = tok.strip("'’.,;:!?()[]").lower()
    if not t:
        return True
    if ROMAN.match(t):
        return True
    if t in lex:
        return True
    # 古体动词变位：lieth / knowest / doeth —— 词典只收词头，这里按词干判
    m = ARCHAIC.match(t)
    if m and len(m.group(1)) >= 3:
        stem = m.group(1)
        if stem in lex or stem + 'e' in lex or (stem.endswith('i') and stem[:-1] + 'y' in lex):
            return True
    return False
