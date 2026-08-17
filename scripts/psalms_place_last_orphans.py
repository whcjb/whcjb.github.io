#!/usr/bin/env python3
"""安置最后 7 条「未定位的注释」。

底本(含 PDF 上标层)确实没有这些标记，但正文里留下了足够的实证痕迹：

- ch102/ch105/ch114：**同一编号出现两次引用**，其中第二处的注释内容正是下一号。
  ch102 [^fd140] 一处在 “sparrow…house-top”(对 ftd140 平顶)、一处在 “signifies *a bat*”
  (对 ftd141 法文 Nicticorax)；ch105 同理；ch114 注释里的 “*Judah is called his holiness*”
  与 “*and Israel his dominion*” 对应 ftd360/ftd361。→ 第二处改成下一号。
- ch105 另有一处：文件内 [^fd232]: 的正文其实是 ftd233 的内容，键少了一号，一并改回，
  并补上真正的 ftd232。
- ch81：中译 [^fc406] 的定义正文就是 ftc407（Kennicott 论 *pot*），且引用正落在
  “his hands were freed from the pots” 处，编号少一号 → 改成 fc407。
- ch90/ch92：注释自陈所注的词（“*Early*, after the dark night of afflictions”；
  “*They shall still bring forth fruit in old age*”），正文中该词唯一 → 就近插入引用。

ch119 fe1（论 Lowth 的希伯来诗平行体三分法）正文里找不到它所说的 “This sentence”，
没有可依据的落点，不处理。

用法:
    python3 scripts/psalms_place_last_orphans.py --dry-run
    python3 scripts/psalms_place_last_orphans.py
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'calvin/psalms-2-en'
ZH = ROOT / 'calvin_raw/psalms-2/zh_chapters'
MARK = '<!-- unplaced-footnotes -->'

# 第 n 次出现的引用改号：(章, 旧号, 第几次(1起), 新号)
RENUM = [
    ('102', 'fd140', 2, 'fd141'),
    ('105', 'fd232', 2, 'fd233'),
    ('114', 'fd357', 2, 'fd360'),
    ('114', 'fd358', 2, 'fd361'),
    ('81',  'fc406', 1, 'fc407'),
]
# 定义键改号：(章, 旧键, 新键)
REKEY = [('105', 'fd232', 'fd233'), ('81', 'fc406', 'fc407')]
# 就近插入：(章, 英文锚, 中文锚, 新号)
INSERT = [
    ('90', '[^fc576] with thy goodness', '[^fc576]饱得你的慈爱', 'fc577'),
    ('92', 'They shall still bud forth in old age;',
           '他们年老的时候仍要结果子，要满了汁浆而常发青；', 'fc601'),
]
PLACED = {'81': ['fc407'], '90': ['fc577'], '92': ['fc601'], '102': ['fd141'],
          '105': ['fd233'], '114': ['fd360', 'fd361']}


def nth_sub(text, old, n, new):
    """把第 n 次出现的 old 换成 new。"""
    hits = [m.start() for m in re.finditer(re.escape(old), text)]
    if len(hits) < n:
        return None
    i = hits[n - 1]
    return text[:i] + new + text[i + len(old):]


def harvest_and_drop(text, codes):
    """从孤儿块取出中文定义并删除该条；块空则整块移除。返回 (新文本, {code: 定义})。"""
    m = re.search(r'(\n*' + re.escape(MARK) +
                  r'\n<div class="unplaced-footnotes".*?</div>\n?)', text, re.S)
    if not m:
        return text, {}
    got, kept = {}, []
    for line in m.group(1).split('\n'):
        mm = re.match(r'- \*\*([A-Za-z0-9]+)\*\*\s*(.*)$', line)
        if mm and 'f' + mm.group(1) in codes:
            got['f' + mm.group(1)] = mm.group(2).strip()
        else:
            kept.append(line)
    if not any(l.startswith('- **') for l in kept):
        return text[:m.start(1)].rstrip() + '\n' + text[m.end(1):], got
    return text[:m.start(1)] + '\n'.join(kept) + text[m.end(1):], got


def add_def(text, code, body):
    """在定义区按编号插入一条定义。"""
    blocks = [(m.group(1), m.group(0).strip()) for m in
              re.finditer(r'^\[\^([a-z]{1,3}\d+[A-Za-z]?)\]:.*?(?=\n\[\^|\n*\Z)',
                          text, re.S | re.M)]
    entry = f'[^{code}]: {body}'
    if not blocks:                      # 该章没有定义区（ch81 英文版就是如此）
        return text.rstrip() + '\n\n' + entry + '\n'
    merged = {c: b for c, b in blocks}
    merged[code] = entry
    order = sorted(merged, key=lambda c: (re.match(r'[a-z]+', c).group(0),
                                          int(re.sub(r'\D', '', c))))
    start = text.index(blocks[0][1])
    end = text.index(blocks[-1][1]) + len(blocks[-1][1])
    return text[:start] + '\n\n'.join(merged[c] for c in order) + text[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    en_defs = json.loads((ROOT / 'calvin_raw/psalms-2/footnote_defs.json')
                         .read_text(encoding='utf-8'))
    zh_path = ROOT / 'calvin_raw/psalms-2/zh_footnote_defs.json'
    zh_defs = json.loads(zh_path.read_text(encoding='utf-8'))

    chapters = sorted(PLACED)
    texts = {ch: {'en': (EN / f'{ch}.md').read_text(encoding='utf-8'),
                  'zh': (ZH / f'{ch}.md').read_text(encoding='utf-8')}
             for ch in chapters}

    for ch, old, n, new in RENUM:
        for side in ('en', 'zh'):
            r = nth_sub(texts[ch][side], f'[^{old}]', n, f'[^{new}]')
            if r is None:
                print(f'  ⚠ ch{ch} {side}: 找不到第 {n} 个 [^{old}]')
            else:
                texts[ch][side] = r
        print(f'ch{ch}: 第 {n} 处 [^{old}] → [^{new}]')

    for ch, old, new in REKEY:
        for side in ('en', 'zh'):
            texts[ch][side] = re.sub(r'^\[\^' + old + r'\]:', f'[^{new}]:',
                                     texts[ch][side], flags=re.M)
        print(f'ch{ch}: 定义键 {old} → {new}')

    for ch, en_anchor, zh_anchor, code in INSERT:
        for side, anchor in (('en', en_anchor), ('zh', zh_anchor)):
            t = texts[ch][side]
            if t.count(anchor) != 1:
                print(f'  ⚠ ch{ch} {side}: 锚点命中 {t.count(anchor)} 次，跳过')
                continue
            i = t.index(anchor) + len(anchor)
            texts[ch][side] = t[:i] + f'[^{code}]' + t[i:]
        print(f'ch{ch}: 插入 [^{code}]')

    # 定义落位 + 孤儿块清理
    for ch in chapters:
        codes = set(PLACED[ch])
        texts[ch]['zh'], zh_got = harvest_and_drop(texts[ch]['zh'], codes)
        texts[ch]['en'], _ = harvest_and_drop(texts[ch]['en'], codes)
        zh_defs.update(zh_got)
        for c in PLACED[ch]:
            key = 'ft' + c[1:]
            if key in en_defs and f'[^{c}]:' not in texts[ch]['en']:
                texts[ch]['en'] = add_def(texts[ch]['en'], c, en_defs[key])
        # ch105 需要补回真正的 fd232（原定义被误挂在 fd232 键下，已改成 fd233）
        if ch == '105' and '[^fd232]:' not in texts[ch]['en']:
            texts[ch]['en'] = add_def(texts[ch]['en'], 'fd232', en_defs['ftd232'])
        print(f'ch{ch}: 中文定义收割 {sorted(zh_got)}')

    if a.dry_run:
        print('\n（预演，未写入）')
        return
    for ch in chapters:
        pe, pz = EN / f'{ch}.md', ZH / f'{ch}.md'
        pe.chmod(0o644); pz.chmod(0o644)
        pe.write_text(texts[ch]['en'], encoding='utf-8')
        pz.write_text(texts[ch]['zh'], encoding='utf-8')
        pz.chmod(0o444)
    zh_path.write_text(json.dumps(zh_defs, ensure_ascii=False, indent=1),
                       encoding='utf-8')
    print(f'\n已写入 {len(chapters)} 章；zh_footnote_defs.json → {len(zh_defs)} 条')


if __name__ == '__main__':
    main()
