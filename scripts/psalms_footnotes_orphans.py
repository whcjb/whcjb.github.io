#!/usr/bin/env python3
"""安置那些在源头就丢了正文标记的脚注条目。

AGES 附录里有一批条目，正文和 PDF 里都找不到对应的 marker（卷一 141 条、
卷二 57 条），既不能靠上下文定位，也不能靠定义开头的 lemma 定位——它们注的词
在正文里根本不以同样措辞出现，有的还是法文注。

归属信号按可靠性排序：
  1. 附录自身的分节标记（`<p class="title-block-h2">PSALM N</p>`，卷一 72 个、
     卷二 101 个）——源头给的，覆盖 1552/1570 与 981/981；
  2. 前后编号同章（分节标记缺失时的兜底）。
注意分节标记在篇界处会偏一格：fa569 的 PDF marker 上下文（"the LXX… sons of
rams" = 诗篇 29:1 七十士译本 υἱοὶ κριῶν）明确落在 ch29，而附录分节说 ch28。
所以**有 PDF marker 的条目一律以实测位置为准**，分节标记只用于没有 marker 的条目。

不往正文里插引用标记——没有任何依据能确定插在哪个词后面，插了就是编造。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = '<!-- unplaced-footnotes -->'
NOTE_EN = ('The source edition groups these notes under this psalm, but their '
           'in-text reference marks were lost, so they cannot be attached to a '
           'specific word.')


def chapter_of_leftovers(vol):
    """→ (defs, {code: chapter}, [无法归章的 code])
    先用附录分节，取不到再退回前后编号推断。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from psalms_footnotes_sections import code_sections
    sections = code_sections(vol)
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
        if c in sections and (en / f'{sections[c]}.md').exists():
            mapping[c] = str(sections[c])          # 附录分节优先
        elif prev and prev == nxt:
            mapping[c] = prev                      # 兜底：前后同章
        else:
            unresolved.append(c)
    return defs, mapping, unresolved


def main(vol):
    defs, mapping, unresolved = chapter_of_leftovers(vol)
    en = ROOT / f'calvin/psalms-{vol}-en'

    by_chapter = {}
    for code, ch in mapping.items():
        by_chapter.setdefault(ch, []).append(code)

    # 先清掉所有旧区块：条目可能改归到别的章，只重写新章会留下过期残块
    for p_ in en.glob('*.md'):
        t = p_.read_text(encoding='utf-8')
        if MARK in t:
            p_.write_text(t[:t.index(MARK)].rstrip() + '\n', encoding='utf-8')

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
