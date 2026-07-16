#!/usr/bin/env python3
"""
owen_flag.py — 免费(零 token)可疑句标记器。
扫描已发布中文页, 用结构性规律捞出"高风险不通顺句", 供人重点校对——
不改写、不调模型, 只把嫌疑句挑出来, 把人工从"逐句读"降到"只看这几句"。

用法: python3 scripts/owen_flag.py owen/hebrews/exercitations/1/zh/index.md
"""
import re, sys

DUP_CONN = ['足以', '不仅', '一方面', '既能', '虽然', '尽管', '不但', '与其']

def sentences(body):
    # 去 HTML 标签; 按句末标点切句(保留位置感)
    text = re.sub(r'<[^>]+>', '', body)
    text = text.replace('&quot;', '"').replace('&#x27;', "'").replace('&amp;', '&')
    return [s.strip() for s in re.split(r'(?<=[。！？])', text) if s.strip()]

def flags(s):
    fl = []
    for c in DUP_CONN:
        if s.count(c) >= 2:
            fl.append(f'「{c}」重复×{s.count(c)}')
    if s.count('——') >= 2:
        fl.append('多个——(嵌套插入)')
    # 长句单独不算问题(欧文本就长句); 仅"超长 + 有——插入"才提示句式重组风险
    if len(s) > 180 and '——' in s:
        fl.append(f'超长且含——({len(s)}字)')
    # 相邻重复词(4字内的 2-3 字串在 20 字内再现 = 口吃/断裂)
    for m in re.finditer(r'([一-鿿]{2,3})', s):
        w = m.group(1)
        nxt = s[m.end():m.end()+22]
        if w in nxt and w not in ('我们', '他们', '基督', '圣经', '因为', '所以', '这卷', '本书'):
            fl.append(f'近距重复「{w}」'); break
    return fl

def main():
    p = sys.argv[1]
    body = open(p, encoding='utf-8').read().split('\n---\n', 1)[-1]
    hits = 0
    for s in sentences(body):
        fl = flags(s)
        if fl:
            hits += 1
            print(f'[{", ".join(fl)}]')
            print(f'  {s[:110]}{"…" if len(s)>110 else ""}\n')
    total = len(sentences(body))
    print(f'—— 共 {total} 句, 标记 {hits} 句可疑 ({hits*100//max(total,1)}%) 供人工重点看')

if __name__ == '__main__':
    main()
