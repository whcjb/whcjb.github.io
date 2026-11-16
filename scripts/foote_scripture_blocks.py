#!/usr/bin/env python3
"""福特讲解中「整段只有一处钦定本经文引文」的段落（如 `" *Glory to God in the highest…*"`）→ 认出路加福音第几节，换和合本。

2026-11-16 中译批次第 6、8 讲两次被拦：这类段落送模型后，它要比对钦定本与和合本措辞（2:14 good will towards men），
就把推敲写进输出（Rule: quote 和合本 wording…）。经文本来就该照抄和合本，不需要模型：
按钦定本逐节比对（只比字母，忽略标点、斜体、引号），整段正好等于某一节或连续几节的前缀/全文时，由程序填和合本。
对不上的（意译、节选、他书经文）仍送模型。
"""
import difflib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
USFM = ROOT / 'foote_raw' / 'luke' / 'src' / '72-LUKeng-kjv2006.usfm'
_KJV = None
_CUV = None
# 整段一处引文：开引号、斜体星号的各种先后（`" *X*"` `" *X"*` `"*X*"` `"*X"*`），段内不再有别的文字
RE_WHOLE = re.compile(r'^"\s?\*([^*"]+?)[.,;:!?]?(?:\*"|"\*)$')


def kjv():
    global _KJV
    if _KJV is None:
        _KJV, c = {}, 0
        for line in USFM.read_text(encoding='utf-8').splitlines():
            m = re.match(r'\\c (\d+)', line)
            if m:
                c = int(m.group(1))
            for vm in re.finditer(r'\\v (\d+) (.*?)(?=\\v \d+ |$)', line):
                t = re.sub(r'\|strong="[^"]*"', '', vm.group(2))     # \w 词|strong="G…"\w* 与 \+w 各种写法
                t = re.sub(r'\\\+?[a-z]+\d*\*?', '', t).replace('¶', '')
                _KJV[(c, int(vm.group(1)))] = re.sub(r'\s+', ' ', t).strip()
    return _KJV


def cuv(c, v):
    global _CUV
    if _CUV is None:
        _CUV = json.loads((ROOT / 'assets' / 'cuv.json').read_text(encoding='utf-8'))['42']
    return _CUV.get(str(c), {}).get(str(v), '')


def norm(s):
    return re.sub(r'[^a-z]', '', s.lower())


def match(block, verses):
    """block 整段是 verses 范围内连续若干节 → 返回和合本译文（带斜体与弯引号）；否则 None。"""
    m = RE_WHOLE.match(block.strip())
    if not m:
        return None
    q = norm(m.group(1))
    if len(q) < 12:
        return None
    K = kjv()
    # 福特拼法与 KJV2006 小异（towards/toward、until/till、showing/shewing），按字母串相似度 ≥ 0.9 认
    best = (0.0, None)
    for i in range(len(verses)):
        acc = ''
        for j in range(i, len(verses)):
            acc += norm(K.get(verses[j], ''))
            r = difflib.SequenceMatcher(None, acc, q, autojunk=False).ratio()
            if r > best[0]:
                best = (r, verses[i:j + 1])
            if len(acc) > len(q) * 1.2:
                break
    if best[0] < 0.9:
        return None
    zh = ''.join(cuv(a, b) for a, b in best[1] if cuv(a, b).strip())
    zh = re.sub(r'（有古卷[^）]*）', '', zh)                 # 和合本异文小注，嵌进讲解正文不要
    # 和合本自带的引号：2:14 整节成对、6:46 只有开引号（收引号在 49 节）——外面已有一层，首尾的去掉
    if zh.startswith('“') and (zh.endswith('”') or zh.count('“') > zh.count('”')):
        zh = zh[1:]
    if zh.endswith('”') and zh.count('”') > zh.count('“'):
        zh = zh[:-1]
    return f'“*{zh}*”' if zh else None
