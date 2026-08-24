#!/usr/bin/env python3
"""补回卷二三处丢失的脚注引用（fG11 / fG14 / fH116）。

背景：PDF 里这三个标记落在**拉丁文经文段**（加尔文自己的拉丁译文）中，而英文
版提取时 scripture-box 只保留了英文经文、丢掉了拉丁半边，标记随之丢失，定义
成了无主脚注堆在卷末（jeremiah_footnotes_restore.py 只能把它们留在末章）。

不能照 PDF 字面位置还原（英文 md 里没有拉丁段），所以映射到**同一句经文的英译
位置**——每条都用定义自身的内容交叉印证过：
  fG11  定义「Why should he kill (or smite) thy life?」→ 英译 "wherefore should
        he slay thee"（PDF 拉丁 quare percutiet to in anima）→ ch40
  fG14  定义「It is not redundant, for it is the idiom of the language」，注的是
        拉丁 illuc 是否冗余（PDF "sed abundat"）→ 英译该节句首 → ch41
  fH116 定义「The best rendering of this verse is by Venema…」→ 英译 "Zedekiah
        rebelled against the king of Babylon."（PDF rebellavit Sedechias…）→ ch52

ftE187 不在此列：PDF 里只有附录定义、正文无引用，保持无主，不臆造。

锚点必须在目标章唯一命中，否则跳过并报警。用法:
    python3 scripts/jeremiah_fix_lost_refs.py [--dry-run]
"""
import argparse, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN = ROOT / 'calvin/jeremiah-2-en'
TAIL = EN / '52.md'

# (码, 目标章, 锚点正则——引用插在 group(1) 之后)
# fH116 那句在 ch52 出现两次（经文块 + 注释），PDF 里它紧跟 v3 末尾、v4 之前，
# 故用「后面接 4.」收窄，避免插错地方。
FIXES = [
    ('fG11',  '40.md', r'(wherefore should he slay thee)'),
    ('fG14',  '41.md', r'(Now the pit wherein Ishmael had cast all the dead bodies)'),
    ('fH116', '52.md', r'(Zedekiah rebelled against the king of Babylon\.)(?=\s*<?s?t?r?o?n?g?>?\s*4\.)'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    tail = TAIL.read_text(encoding='utf-8')
    moved = []
    for code, ch, anchor in FIXES:
        p = EN / ch
        t = p.read_text(encoding='utf-8')
        if f'[^{code}]' in t and f'[^{code}]:' not in t.split('\n[^')[0]:
            pass
        hits = list(re.finditer(anchor, t))
        if len(hits) != 1:
            print(f'  !! {code} → {ch}: 锚点命中 {len(hits)} 次，跳过（不臆造位置）')
            continue
        # 取定义（当前堆在末章，键名可能带 t）
        m = re.search(rf'^\[\^f?t?{code[1:]}\]: (.*)$', tail, re.M)
        if not m:
            m = re.search(rf'^\[\^ft{code[1:]}\]: (.*)$', tail, re.M)
        if not m:
            print(f'  !! {code}: 末章找不到定义，跳过')
            continue
        body = m.group(1)
        new = re.sub(anchor, lambda m: m.group(1) + f'[^{code}]', t, count=1)
        if ch == '52.md':
            # 定义已在本章，只删旧的无主键、按新码重写
            new = re.sub(rf'^\[\^ft{code[1:]}\]: .*$', f'[^{code}]: {body}', new, flags=re.M)
        else:
            new = new.rstrip() + f'\n[^{code}]: {body}\n'
        if not args.dry_run:
            p.write_text(new, encoding='utf-8')
        moved.append((code, ch))
        print(f'  ✓ {code} → {ch}  引用插在「…{hits[0].group(1)[-34:]}」之后'
              + ('（定义同章，改键）' if ch == '52.md' else '（定义移入本章）'))

    # 末章删掉已搬走的定义
    if moved and not args.dry_run:
        tail_new = TAIL.read_text(encoding='utf-8')
        for code, ch in moved:
            if ch != '52.md':
                tail_new = re.sub(rf'^\[\^ft{code[1:]}\]: .*\n?', '', tail_new, flags=re.M)
        TAIL.write_text(tail_new, encoding='utf-8')
    print(f'\n{"[dry-run] " if args.dry_run else ""}处理 {len(moved)} 条；'
          'ftE187 按 PDF 保持无主（正文确无引用）')


if __name__ == '__main__':
    main()
