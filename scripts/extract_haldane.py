#!/usr/bin/env python3
"""霍尔丹《罗马书释义》(Robert Haldane, Exposition of the Epistle to the Romans) 录入本 → units.json

底本：StudyLight「hal」(Text Courtesy of BibleSupport.com，public domain)，经互联网档案馆快照取原始 HTML
（scripts/fetch_haldane.sh → haldane_raw/romans/src/studylight/romans-<章>.html）。
录入本只有第 1–16 章逐节注释；原书（1874 第九版）的序言、导论、两篇专论、结语、附录不在其中。

每章页面：<h3><a data-entry="introduction|verse-N|verses-N-M">…</a></h3> 起一条，
条下 <p class="emphasis"> 是所讲经文（斜体），其余 <p> 是注释段落。注释区止于上下章导航栏。

清洗：HTML 实体解码；录入本混用 Windows-1252 的数字实体（&#151; &#146; …）→ 正确的破折号、引号；
只留 i / b / sup 三种行内标签（i → em）；空白归一；希腊文 NFC。
"""
import html
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'haldane_raw' / 'romans'
SRC = RAW / 'src' / 'studylight'

CP1252 = {'\x91': '‘', '\x92': '’', '\x93': '“', '\x94': '”', '\x96': '–', '\x97': '—', '\x85': '…', '\x95': '•'}
# data-entry 可能是空的（第 9 章章首概述 data-entry=""，标题文字也空）——按 introduction 处理
RE_ENTRY = re.compile(r'<h3[^>]*>\s*<a [^>]*data-entry="([^"]*)"[^>]*>([^<]*)</a>\s*</h3>', re.S)
END_MARK = '<div class="flexbox-row-nowrap jc-between'


RE_AGES = re.compile(r'<\d{2}[0-9A-F]{4,5}>')          # AGES 经文锚点编码 <19D601>，录入本从 AGES 转来时留下的

# 录入本从 AGES 转来时，有 9 个希腊词没换成 Unicode，留着 AGES 希腊字体的拉丁转写（> 尖音符、j 柔气号、J 粗气号），
# 有的还被插了空格（poi >hma）。全书只此 9 处（grep 「字母 >字母」除去 em> 等标签尾），逐条写死。
# 不还原的代价：英文页显示乱码；中译时模型把它还原成希腊字母，翻译闸在原文里找不到，判「原文没有的希腊词」，
# 整章不写出（第 14 章 14#45 poi >hma 连挡两夜）。
# dikaiw>atov 录入本漏了 μ（罗 5:18 δικαιώματος；1874 扫描本 OCR 同位作 dtxatuaros），未看图，照录入本原样还原，待用户定。
AGES_GREEK = {
    'Dikaiosu>nh': 'Δικαιοσύνη',
    'dikaiosu>nh': 'δικαιοσύνη',
    'cro >noi aijw >nioi': 'χρόνοι αἰώνιοι',
    'cwri>v no>mou': 'χωρίς νόμου',
    'di ’ eJno>v dikaiw>atov': 'δι’ ἑνός δικαιώατος',
    'poi >hma': 'ποίημα',
}


def clean_inline(s: str) -> str:
    s = RE_AGES.sub('', s)
    s = re.sub(r'<sup>\s*(\d+)\s*</sup>', r'⟦fn\1⟧', s)   # 脚注号先换成记号，免得被标签清洗吃掉
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'</?(?!(?:i|b|sup)\b)[a-zA-Z][^>]*>', '', s)          # 只留 i / b / sup
    s = re.sub(r'<(/?)(i|b|sup)\b[^>]*>', r'<\1\2>', s)
    s = html.unescape(s)
    s = ''.join(CP1252.get(c, c) for c in s)
    for k, v in AGES_GREEK.items():
        s = s.replace(k, v)
    s = unicodedata.normalize('NFC', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'<i>\s*</i>', '', s)
    s = re.sub(r'\s+</i>', '</i> ', s).replace('<i> ', ' <i>')
    s = re.sub(r'\s{2,}', ' ', s).replace('<i>', '<em>').replace('</i>', '</em>').strip()
    return re.sub(r'\s*⟦fn(\d+)⟧', r'[^f\1]', s)


def entries_of(ch: int):
    t = (SRC / f'romans-{ch}.html').read_text(encoding='utf-8', errors='ignore')
    t = ''.join(CP1252.get(c, c) for c in t)
    heads = list(RE_ENTRY.finditer(t))
    # 结束标记在页顶导航里也出现一次（在第一条之前）；取第一条之后的那个，否则每章末条被截空（实测 16 章全中）
    end = t.find(END_MARK, heads[0].start()) if heads else -1
    out = []
    for k, m in enumerate(heads):
        stop = heads[k + 1].start() if k + 1 < len(heads) else end
        block = t[m.end():stop]
        key = m.group(1) or 'introduction'
        # 脚注区：「<b>Footnote:</b><br /><b>45</b>: 文字 <br /><b>46</b>: …」，不在 <p> 里
        notes = {}
        for fb in re.findall(r'<b>\s*Footnotes?:\s*</b>(.*?)(?=<p[ >]|<h3|$)', block, re.S):
            for n, txt in re.findall(r'<b>\s*(\d+)\s*</b>\s*:(.*?)(?=<b>\s*\d+\s*</b>\s*:|$)', fb, re.S):
                notes[int(n)] = clean_inline(txt)
        # 脚注块拿掉后，按原顺序收段：<p>…</p> 是一段；<p> 外面游离的文字也算一段
        # （录入本有的段落没包 <p>，实测第 5 章「…has no foundation.’ ³³」整段在 <p> 外，漏了会丢正文和注号）
        rest = re.sub(r'<div>\s*<b>\s*Footnotes?:\s*</b>.*?</div>', '', block, flags=re.S)
        paras = []
        for piece in re.split(r'(<p[^>]*>.*?</p>)', rest, flags=re.S):
            mp = re.match(r'<p([^>]*)>(.*?)</p>$', piece, re.S)
            if mp:
                paras.append((mp.group(1), mp.group(2)))
            elif len(re.sub(r'<[^>]+>', ' ', piece).split()) >= 3:
                paras.append(('', piece))
        lemma, body = '', []
        for attrs, inner in paras:
            txt = clean_inline(inner)
            if not txt:
                continue
            if 'emphasis' in attrs and not lemma and not body:
                lemma = re.sub(r'^<em>(.*)</em>$', r'\1', txt)
            else:
                body.append(txt)
        mv = re.match(r'verses?-(\d+)(?:-(\d+))?$', key)
        e = {'key': key, 'label': html.unescape(m.group(2)).strip() or 'Introduction', 'lemma': lemma, 'paras': body,
             'notes': {str(k): v for k, v in sorted(notes.items())}}
        if mv:
            e['v1'] = int(mv.group(1))
            e['v2'] = int(mv.group(2) or mv.group(1))
        out.append(e)
    return out


def main():
    chapters = []
    for ch in range(1, 17):
        es = entries_of(ch)
        chapters.append({'ch': ch, 'entries': es})
        words = sum(len(re.sub(r'<[^>]+>', ' ', p).split()) for e in es for p in e['paras'] + [e['lemma']])
        print(f'第 {ch:2} 章：{len(es):3} 条，约 {words:6} 词')
    (RAW / 'units.json').write_text(json.dumps({'chapters': chapters}, ensure_ascii=False, indent=1), encoding='utf-8')
    print('→', (RAW / 'units.json').relative_to(ROOT))


if __name__ == '__main__':
    main()
