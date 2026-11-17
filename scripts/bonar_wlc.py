#!/usr/bin/env python3
"""WLC（openscriptures/morphhb）词表：辅音骨架 → {带点形式: 出现次数}，供核对博纳尔书中的希伯来文。

去掉经文的重音符号（U+0591–05AF）、meteg、rafe；按 maqaf 与语素分隔符「/」拆词；保留元音、dagesh、shin/sin 点。
"""
import collections
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'bonar_raw' / 'psalms' / 'src' / 'wlc'
CACHE = ROOT / 'bonar_raw' / 'psalms' / 'work' / 'wlc_index.json'

DROP = set(chr(c) for c in range(0x0591, 0x05B0)) | {'ֽ', 'ֿ', '׀', '׃', 'ׄ', 'ׅ', '׆'}


def clean(w):
    w = unicodedata.normalize('NFD', w)
    w = ''.join(c for c in w if c not in DROP)
    return unicodedata.normalize('NFC', w)


def skel(w):
    return ''.join(c for c in unicodedata.normalize('NFD', w) if 'א' <= c <= 'ת')


def index():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding='utf-8'))
    idx = collections.defaultdict(collections.Counter)
    ps = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    for f in sorted(SRC.glob('*.xml')):
        x = f.read_text(encoding='utf-8')
        for vm in re.finditer(r'<verse osisID="([^"]+)">(.*?)</verse>', x, re.S):
            vid, body = vm.groups()
            for wm in re.finditer(r'<w [^>]*>([^<]*)</w>', body):
                whole = wm.group(1).replace('/', '')
                for part in [whole] + wm.group(1).split('/'):
                    w = clean(part)
                    if skel(w):
                        idx[skel(w)][w] += 1
                        if vid.startswith('Ps.'):
                            ps[vid.split('.')[1]][skel(w)][w] += 1
    data = dict(all={k: dict(v) for k, v in idx.items()},
                ps={c: {k: dict(v) for k, v in d.items()} for c, d in ps.items()})
    CACHE.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    return data
