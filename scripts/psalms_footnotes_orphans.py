#!/usr/bin/env python3
"""安置那些在源头就丢了正文标记的脚注条目。

AGES 附录里有一批条目，正文和 PDF 里都找不到对应的 marker（卷一 141 条、
卷二 57 条），既不能靠上下文定位，也不能靠定义开头的 lemma 定位——它们注的词
在正文里根本不以同样措辞出现，有的还是法文注。

唯一还站得住的信号：编码按文档顺序分配。若某条的前一号和后一号都落在同一章，
它必然也属于该章。据此归章（卷一 116 条、卷二 35 条），放进该章末尾一个明确
标注的区块；跨章边界、两侧不一致的仍留在附录页。

不往正文里插引用标记——没有任何依据能确定插在哪个词后面，插了就是编造。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = '<!-- unplaced-footnotes -->'
NOTE_EN = ('These notes belong to this chapter (their numbering falls between '
           'footnotes anchored here), but the in-text reference marks were lost '
           'in the source edition, so they cannot be attached to a specific word.')


def chapter_of_leftovers(vol):
    """→ ({code: chapter}, [无法归章的 code])，只认前后同章的情形"""
    defs = json.loads((ROOT / f'calvin_raw/psalms-{vol}/footnote_defs.json')
                      .read_text(encoding='utf-8'))
    en = ROOT / f'calvin/psalms-{vol}-en'
    where = {}
    for p in en.glob('*.md'):
        if p.stem == 'footnotes':
            continue
        for c in re.findall(r'^\[\^([a-z]{1,3}\d+[a-z]?)\]:',
                            p.read_text(encoding='utf-8'), re.M):
            where['ft' + c[1:]] = p.stem

    def key(c):
        m = re.match(r'(ft[a-z])(\d+)', c)
        return (m.group(1), int(m.group(2))) if m else (c, 0)

    ordered = sorted(defs, key=key)
    pos = {c: i for i, c in enumerate(ordered)}
    mapping, unresolved = {}, []
    for c in (k for k in defs if k not in where):
        i, prefix = pos[c], key(c)[0]
        prev = next((where[ordered[j]] for j in range(i - 1, -1, -1)
                     if ordered[j] in where and key(ordered[j])[0] == prefix), None)
        nxt = next((where[ordered[j]] for j in range(i + 1, len(ordered))
                    if ordered[j] in where and key(ordered[j])[0] == prefix), None)
        (mapping.setdefault(c, prev) if prev and prev == nxt else unresolved.append(c))
    return defs, mapping, unresolved


def main(vol):
    defs, mapping, unresolved = chapter_of_leftovers(vol)
    en = ROOT / f'calvin/psalms-{vol}-en'

    by_chapter = {}
    for code, ch in mapping.items():
        by_chapter.setdefault(ch, []).append(code)

    for ch, codes in sorted(by_chapter.items()):
        p = en / f'{ch}.md'
        text = p.read_text(encoding='utf-8')
        if MARK in text:                      # 幂等：重复运行先去掉旧区块
            text = text[:text.index(MARK)].rstrip() + '\n'
        codes.sort(key=lambda c: int(re.sub(r'\D', '', c)))
        # div 必须带 markdown="1"，否则条目里的 *斜体* / <span> 会原样显示成星号
        items = '\n'.join(f'- **{c[2:]}** {defs[c]}' for c in codes)
        block = (f'\n\n{MARK}\n<div class="unplaced-footnotes" markdown="1">\n'
                 f'#### Unanchored notes\n\n{NOTE_EN}\n{{: .uf-note}}\n\n'
                 f'{items}\n</div>\n')
        p.write_text(text.rstrip() + block, encoding='utf-8')

    # 附录页只留真正归不了章的
    fn = en / 'footnotes.md'
    head = fn.read_text(encoding='utf-8').split('---\n', 1)[1].split('---\n', 1)[0]
    note = (f'\n<p><em>本页收录源版本中引用标记丢失、且前后编号跨章因而无法归属到'
            f'具体章节的脚注条目，共 {len(unresolved)} 条。能归章的已随文放在对应章末尾。</em></p>\n\n')
    body = '\n\n'.join(f'**{c[2:]}** {defs[c]}'
                       for c in sorted(unresolved, key=lambda c: (c[:3], int(re.sub(r'\D', '', c)))))
    fn.write_text(f'---\n{head}---\n{note}{body}\n', encoding='utf-8')

    print(f'卷{vol}: 归章 {len(mapping)} 条（{len(by_chapter)} 章），'
          f'附录留 {len(unresolved)} 条')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else '1')
