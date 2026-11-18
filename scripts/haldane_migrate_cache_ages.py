#!/usr/bin/env python3
"""霍尔丹改 AGES 底本后的中文缓存迁移：旧译文按段拼成新段，不重译。

    python3 scripts/haldane_migrate_cache_ages.py [--rev <旧版 commit>]

2026-11-18 霍尔丹底本由 StudyLight 录入本改为 AGES（extract_haldane_ages.py），版式照 AGES。录入本把 AGES 的一段
拆成了几段（1874 第九版扫描本证实是录入本多分），新段落的文字 = 录入本连续几段相接。缓存键取段落原文，新段对不上
旧键，照常会整段重译。本脚本：
  1. 从 git 旧版（--rev，默认改版前的 HEAD~）取英文页 haldane/romans/<章>.md 与 translate_haldane.py，用旧的
     blocks() 还原每个旧段落的遮盖原文与缓存译文；
  2. 新版每个待译段落：只比字母（去空格、标点、标签——录入本的粘连词 fori / forthe 也就对上了），找章内连续几个
     旧段落相接与之全等；且各旧段的标签（⟦N⟧ 所代表的）依次相接 == 新段标签；
  3. 把这几段旧译文依次相接，占位符编号顺延，过 T.structural_diff（新原文 vs 拼出的译文）才写入新键；旧文件不删。
对不上的段落留给 translate_haldane.py --resume 正常翻译。
"""
import argparse
import importlib.util
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import translate_filibi as tf          # noqa: E402
import translate_alexander_acts as T   # noqa: E402


def git_show(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def letters(s):
    s = re.sub(r'⟦\d+⟧|<[^>]+>|\[\^f\d+\]:?', '', s)
    return re.sub(r'[^a-zα-ωά-ώἀ-ῼ]', '', s.lower())


def payload(b):
    m = re.match(r'^(\[\^f\d+\]:) (.*)$', b, re.S)
    return (m.group(1) + ' ', m.group(2)) if m else ('', b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rev', default='HEAD')
    a = ap.parse_args()
    tmp = Path(tempfile.mkdtemp())
    (tmp / 'romans').mkdir()
    for c in range(1, 17):
        (tmp / 'romans' / f'{c}.md').write_text(git_show(a.rev, f'haldane/romans/{c}.md'), encoding='utf-8')
    (tmp / 'old_translate.py').write_text(git_show(a.rev, 'scripts/translate_haldane.py'), encoding='utf-8')
    old = load(tmp / 'old_translate.py', 'old_translate_haldane')
    old.SRC = tmp / 'romans'
    old.ROOT = ROOT
    new = load(ROOT / 'scripts' / 'translate_haldane.py', 'new_translate_haldane')
    cache, ns = new.CACHE, new.KEY_NS
    made = tried = 0
    for c in range(1, 17):
        olds = []                                   # (letters, tags, zh 遮盖译文)
        for b in [x[1] for x in old.blocks(c) if x[0] == 'text']:
            pre, body = payload(b)
            masked, tags = T.mask(body)
            f = cache / f'{tf.md5key(ns + masked)}.txt'
            olds.append((letters(masked), tags, f.read_text(encoding='utf-8') if f.exists() else None, bool(pre)))
        first = {}
        for i, o in enumerate(olds):
            first.setdefault(o[0][:40], []).append(i)
        for k, b, gid, kinds in new.blocks(c):
            if k != 'text':
                continue
            pre, body = payload(b)
            masked, tags = T.mask(body)
            key = tf.md5key(ns + masked)
            if (cache / f'{key}.txt').exists():
                continue
            tried += 1
            target = letters(masked)
            hit = None
            for i in first.get(target[:40], []):
                acc, j = '', i
                while j < len(olds) and len(acc) < len(target):
                    acc += olds[j][0]; j += 1
                if acc == target and all(o[2] is not None for o in olds[i:j]) \
                        and sum((o[1] for o in olds[i:j]), []) == tags:
                    hit = (i, j); break
            if not hit:
                continue
            parts, off = [], 0
            for o in olds[hit[0]:hit[1]]:
                parts.append(re.sub(r'⟦(\d+)⟧', lambda m: f'⟦{int(m.group(1)) + off}⟧', o[2]))
                off += len(o[1])
            zh = ''.join(p.strip() for p in parts)
            if T.structural_diff(masked, zh):
                continue
            (cache / f'{key}.txt').write_text(zh, encoding='utf-8')
            made += 1
        print(f'[{c}] 累计拼出 {made} / 尝试 {tried}', flush=True)
    print(f'完成：新缓存 {made} 段（共 {tried} 段待译）')


if __name__ == '__main__':
    main()
