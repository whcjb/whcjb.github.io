#!/usr/bin/env python3
"""中文页里夹着未译英文词的块：找出来、把对应的缓存条目移出去，等重跑重译。

判据与 translate_davenant.check_block 里的那条一样（两侧紧贴汉字的小写拉丁词，
罗马数字除外）。缓存条目**移进 zh_cache_rejected/**，不删——翻译产物按约定
绝不无备份删除；重跑时缓存未命中就会重译，新译文过同一道闸。

用法: python3 scripts/davenant_zh_leakscan.py [章号…]   默认 1 2 3 4
"""
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'davenant_raw' / 'colossians' / 'zh_cache'
REJECT = ROOT / 'davenant_raw' / 'colossians' / 'zh_cache_rejected'
LEAK_RE = re.compile(r'[一-鿿]\s*([a-z]{3,})\s*[一-鿿]')
ROMAN_ONLY = re.compile(r'^[ivxlcdm]+$')


def leaked(text):
    return [w for w in LEAK_RE.findall(re.sub(r'<[^>]+>', ' ', text))
            if not ROMAN_ONLY.match(w)]


def main(chapters):
    REJECT.mkdir(exist_ok=True)
    for n in chapters:
        page = ROOT / 'davenant' / 'colossians' / str(n) / 'zh' / 'index.md'
        if not page.exists():
            continue
        words = leaked(page.read_text(encoding='utf-8'))
        print(f'ch{n}: ' + ('干净' if not words else
                            f'{len(words)} 处 —— ' + ' '.join(dict.fromkeys(words))))
    # 缓存整目录扫一遍（条目按英文块的 md5 存，与章无关）
    moved = 0
    for f in sorted(CACHE.glob('*.txt')):
        if leaked(f.read_text(encoding='utf-8')):
            shutil.move(str(f), REJECT / f.name)
            moved += 1
    print(f'缓存里夹英文词的条目：移出 {moved} 条 → zh_cache_rejected/；'
          f'重跑对应章节即会重译（重译后过 check_block 的同一道闸）')
    return 0


if __name__ == '__main__':
    sys.exit(main([int(x) for x in sys.argv[1:]] or [1, 2, 3, 4]))
