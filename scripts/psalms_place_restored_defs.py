#!/usr/bin/env python3
"""把刚还原了正文引用的脚注，从「未定位的注释」块搬回正式脚注定义。

配合 psalms_restore_lost_marks.py 使用：那一步在正文里补回了 [^code] 引用，
这一步负责让定义正式落位——

1. 中文定义此前只以列表项形式存在于孤儿块里，从块中收割后写进 zh_footnote_defs.json；
2. 英文定义从 footnote_defs.json（键为 ftX…）取出，按编号插进该章的定义区；
3. 中英两侧的孤儿块删掉这些条目，块空了就整块移除。

用法:
    python3 scripts/psalms_place_restored_defs.py --dry-run
    python3 scripts/psalms_place_restored_defs.py
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN_DIR = ROOT / 'calvin/psalms-2-en'
ZH_DIR = ROOT / 'calvin_raw/psalms-2/zh_chapters'
MARK = '<!-- unplaced-footnotes -->'

RESTORED = {
    '84': ['fc457'], '119': ['fd423'],
    '135': ['fe153', 'fe155', 'fe156', 'fe157', 'fe158', 'fe159',
            'fe160', 'fe161', 'fe162', 'fe167', 'fe168'],
    '127': ['fe98'],
    '136': ['fe169', 'fe172', 'fe173', 'fe174', 'fe175'],
}

DEF_RE = re.compile(r'^\[\^([a-z]{1,3}\d+[A-Za-z]?)\]:.*?(?=\n\[\^|\n*\Z)', re.S | re.M)


def num(code):
    return int(re.sub(r'\D', '', code))


def harvest_zh(text, codes):
    """从孤儿块里取出这些 code 的中文定义（块里的 key 去掉了首字母 f）。"""
    m = re.search(r'<div class="unplaced-footnotes".*?</div>', text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(0).split('\n'):
        mm = re.match(r'- \*\*([A-Za-z0-9]+)\*\*\s*(.*)$', line)
        if mm and 'f' + mm.group(1) in codes:
            out['f' + mm.group(1)] = mm.group(2).strip()
    return out


def drop_from_block(text, codes):
    """从孤儿块里删掉这些条目；块空了整块移除。"""
    m = re.search(r'(\n*' + re.escape(MARK) + r'\n<div class="unplaced-footnotes".*?</div>\n?)',
                  text, re.S)
    if not m:
        return text
    block = m.group(1)
    kept = [l for l in block.split('\n')
            if not (re.match(r'- \*\*([A-Za-z0-9]+)\*\*', l)
                    and 'f' + re.match(r'- \*\*([A-Za-z0-9]+)\*\*', l).group(1) in codes)]
    if not any(l.startswith('- **') for l in kept):
        return text[:m.start(1)].rstrip() + '\n' + text[m.end(1):]
    return text[:m.start(1)] + '\n'.join(kept) + text[m.end(1):]


def insert_en_defs(text, new_defs):
    """按编号把新定义插进该章的定义区。"""
    blocks = [(m.group(1), m.group(0).strip()) for m in DEF_RE.finditer(text)]
    if not blocks:
        return None
    start = text.index(blocks[0][1])
    end = text.index(blocks[-1][1]) + len(blocks[-1][1])
    merged = {c: b for c, b in blocks}
    for c, d in new_defs.items():
        merged[c] = f'[^{c}]: {d}'
    ordered = sorted(merged, key=lambda c: (re.match(r'[a-z]+', c).group(0), num(c)))
    return text[:start] + '\n\n'.join(merged[c] for c in ordered) + text[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    en_defs = json.loads((ROOT / 'calvin_raw/psalms-2/footnote_defs.json')
                         .read_text(encoding='utf-8'))
    zh_path = ROOT / 'calvin_raw/psalms-2/zh_footnote_defs.json'
    zh_defs = json.loads(zh_path.read_text(encoding='utf-8'))

    harvested = {}
    for ch, codes in RESTORED.items():
        ep, zp = EN_DIR / f'{ch}.md', ZH_DIR / f'{ch}.md'
        et, zt = ep.read_text(encoding='utf-8'), zp.read_text(encoding='utf-8')

        got = harvest_zh(zt, codes)
        missing = [c for c in codes if c not in got]
        if missing:
            print(f'ch{ch}: 中文定义未在孤儿块中找到 {missing}')
        harvested.update(got)

        new_en = {c: en_defs['ft' + c[1:]] for c in codes if 'ft' + c[1:] in en_defs}
        et2 = insert_en_defs(et, new_en)
        if et2 is None:
            print(f'ch{ch}: 英文章节无定义区，跳过'); continue
        et2 = drop_from_block(et2, codes)
        zt2 = drop_from_block(zt, codes)
        print(f'ch{ch}: 英文补定义 {len(new_en)} 条，收割中文 {len(got)} 条，孤儿块已剔除')
        if not a.dry_run:
            ep.chmod(0o644); zp.chmod(0o644)
            ep.write_text(et2, encoding='utf-8')
            zp.write_text(zt2, encoding='utf-8')
            zp.chmod(0o444)

    if not a.dry_run:
        zh_defs.update(harvested)
        zh_path.write_text(json.dumps(zh_defs, ensure_ascii=False, indent=1),
                           encoding='utf-8')
        print(f'\nzh_footnote_defs.json: +{len(harvested)} 条 → {len(zh_defs)} 条')
    else:
        print(f'\n预演：将新增中文定义 {len(harvested)} 条')


if __name__ == '__main__':
    main()
