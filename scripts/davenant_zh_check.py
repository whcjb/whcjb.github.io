#!/usr/bin/env python3
"""拿 check_block 把**已落缓存**的译文再过一遍，不合格的移出缓存等重译。

translate_davenant 的 revise() 只在翻译当轮跑这道闸；闸子后来加严了
（比如「夹着未译的英文词」），早先译好的块不会自动复查。这个脚本按章重放
同一道闸：读英文页 → 切块 → 查缓存 → check_block，不合格的条目移进
zh_cache_rejected/（不删），重跑该章时缓存未命中就会重译。

用法: python3 scripts/davenant_zh_check.py [章号…]     默认 1 2 3 4
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import translate_davenant as T                                  # noqa: E402
import translate_filibi as tf                                   # noqa: E402

REJECT = ROOT / 'davenant_raw' / 'colossians' / 'zh_cache_rejected'


def main(chapters):
    REJECT.mkdir(exist_ok=True)
    total = 0
    for n in chapters:
        src = T.PUB / f'{n}.md'
        if not src.exists():
            continue
        _fm, body = T.split_page(src.read_text(encoding='utf-8'))
        items = T.blocks_of(body)
        bad = 0
        for it in items:
            if it[0] not in ('body', 'scripture'):
                continue
            text = T.prompt_of(it)
            f = T.CACHE / f'{tf.md5key(text)}.txt'
            if not f.exists():
                continue
            why = T.check_block(text, f.read_text(encoding='utf-8'))
            if why:
                print(f'  ch{n} {f.name}: {why}')
                shutil.move(str(f), REJECT / f.name)
                bad += 1
        print(f'ch{n}: 缓存里不合格 {bad} 条')
        total += bad
    print(f'共移出 {total} 条 → zh_cache_rejected/；重跑对应章节即重译')
    return 0


if __name__ == '__main__':
    sys.exit(main([int(x) for x in sys.argv[1:]] or [1, 2, 3, 4]))
