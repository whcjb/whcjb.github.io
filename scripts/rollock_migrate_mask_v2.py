#!/usr/bin/env python3
"""把罗洛克中译缓存从旧占位符编号（v1：空标签对开、闭各一号）换算成新编号（v2：空标签对合一号）。

translate_rollock 的缓存键 = md5(KEY_NS + 遮盖后的原文)，缓存里存的也是遮盖后的译文。
mask 改了以后，凡含空标签对的段，键和编号都变了；不迁移的话下次 --resume 会把这些段重译一遍。

做法：旧缓存 → 用旧 tags 还原成完整译文 → 用新 mask 重新遮盖 → 过一遍结构闸里的占位符比对 → 写到新键。
- 旧缓存文件一个不删（翻译产物不可删）；新键已存在的不覆盖。
- 换算后占位符对不上的段只报告、不写。

用法：python3 scripts/rollock_migrate_mask_v2.py [--apply]   （不加 --apply 只统计）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_rollock as T          # noqa: E402
import translate_filibi as tf          # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()
    stat = dict(same=0, moved=0, exists=0, nocache=0, bad=0)
    for book in ('1thessalonians', '2thessalonians'):
        T.BOOK, T.SRC = book, T.ROOT / 'rollock' / book
        for slug in T.all_slugs():
            for kind, b in T.units_of(slug):
                if kind != 'text':
                    continue
                m1, tags1 = T.mask(b, T.RE_ANY_V1)
                m2, tags2 = T.mask(b)
                if m1 == m2:
                    stat['same'] += 1
                    continue
                f1 = T.CACHE / f'{tf.md5key(T.KEY_NS + m1)}.txt'
                f2 = T.CACHE / f'{tf.md5key(T.KEY_NS + m2)}.txt'
                if f2.exists():
                    stat['exists'] += 1
                    continue
                if not f1.exists():
                    stat['nocache'] += 1
                    continue
                full = T.unmask(f1.read_text(encoding='utf-8'), tags1)
                zh2, _ = T.mask(full)
                pe, pz = T.RE_PH.findall(m2), T.RE_PH.findall(zh2)
                if pe != pz or T.unmask(zh2, tags2) != full:
                    stat['bad'] += 1
                    print(f'  ✗ {book}/{slug}: 换算后占位符 {pe} → {pz}')
                    continue
                stat['moved'] += 1
                if a.apply:
                    f2.write_text(zh2, encoding='utf-8')
    print(('已写入' if a.apply else '试算（未写）'), stat)


if __name__ == '__main__':
    main()
