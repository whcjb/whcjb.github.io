#!/usr/bin/env python3
"""全卷普查：把正文里以**大写字面**残留的脚注标记还原成真引用。

根因只有一个：英文发布阶段识别正文标记的正则写死了小写 `f[a-e]\\d+`，而 AGES 源里
有相当一批标记是小型大写（FE204、FE291A…）。这些标记既没被转成 [^code]，也没被清掉，
就以字面文本留在正文中间；定义那头找不到引用，于是被堆进章末「未定位的注释」块。

—— 所以这从来不是「位置已佚」，而是「位置一直在、只是没被认出来」。

本脚本做全卷 sweep（此前只按孤儿块逐条修，漏了尚未翻译的章）：
1. 英文章节正文里的 `FXnnn` → `[^fxnnn]`，并从 footnote_defs.json 补上定义；
2. 中文 raw 若已翻译且同样残留该字面，一并替换；中文定义从孤儿块收割进
   zh_footnote_defs.json（未翻译的章跳过，等翻译后再跑一次即可）；
3. 两侧孤儿块删掉已落位的条目，块空则整块移除。

用法:
    python3 scripts/psalms_sweep_uppercase_marks.py --dry-run
    python3 scripts/psalms_sweep_uppercase_marks.py [--skip 140]
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK = '<!-- unplaced-footnotes -->'
LIT = re.compile(r'(?<![A-Za-z0-9])(F[A-F]\d+[A-Za-z]?)(?![A-Za-z0-9])')
DEF_BLOCK = re.compile(r'^\[\^([a-z]{1,3}\d+[A-Za-z]?)\]:.*?(?=\n\[\^|\n*\Z)', re.S | re.M)


def strip_regions(t):
    """返回去掉孤儿块与定义区后的正文，用于安全地找字面标记。"""
    t = re.sub(r'<div class="unplaced-footnotes".*?</div>', '', t, flags=re.S)
    return DEF_BLOCK.sub('', t)


def literals(t):
    return [m.group(1) for m in LIT.finditer(strip_regions(t))]


def replace_literals(t, codes):
    """只在正文区替换；孤儿块/定义区里的同名字符串不动。"""
    out, last = [], 0
    for m in re.finditer(r'<div class="unplaced-footnotes".*?</div>', t, re.S):
        out.append(_sub_body(t[last:m.start()], codes)); out.append(m.group(0))
        last = m.end()
    out.append(_sub_body(t[last:], codes))
    return ''.join(out)


def _sub_body(s, codes):
    def rep(m):
        c = m.group(1)
        if c.lower() not in codes:
            return m.group(0)
        return f'[^{c.lower()}]'
    # 定义区不动
    parts, last = [], 0
    for m in DEF_BLOCK.finditer(s):
        parts.append(LIT.sub(rep, s[last:m.start()])); parts.append(m.group(0))
        last = m.end()
    parts.append(LIT.sub(rep, s[last:]))
    out = ''.join(parts)
    # 标记前的多余空格（原文是上标）在中文里不留
    return re.sub(r'([　-〿＀-￯一-鿿])[ \t]+(\[\^f)', r'\1\2', out)


def harvest_and_drop(text, codes):
    m = re.search(r'(\n*' + re.escape(MARK) +
                  r'\n<div class="unplaced-footnotes".*?</div>\n?)', text, re.S)
    if not m:
        return text, {}
    got, kept = {}, []
    for line in m.group(1).split('\n'):
        mm = re.match(r'- \*\*([A-Za-z0-9]+)\*\*\s*(.*)$', line)
        if mm and 'f' + mm.group(1).lower() in codes:
            got['f' + mm.group(1).lower()] = mm.group(2).strip()
        else:
            kept.append(line)
    if not any(l.startswith('- **') for l in kept):
        return text[:m.start(1)].rstrip() + '\n' + text[m.end(1):], got
    return text[:m.start(1)] + '\n'.join(kept) + text[m.end(1):], got


def add_defs(text, new):
    if not new:
        return text
    blocks = [(m.group(1), m.group(0).strip()) for m in DEF_BLOCK.finditer(text)]
    merged = {c: b for c, b in blocks}
    for c, d in new.items():
        merged.setdefault(c, f'[^{c}]: {d}')
    order = sorted(merged, key=lambda c: (re.match(r'[a-z]+', c).group(0),
                                          int(re.sub(r'\D', '', c)), c))
    body = '\n\n'.join(merged[c] for c in order)
    if not blocks:
        return text.rstrip() + '\n\n' + body + '\n'
    start = text.index(blocks[0][1])
    end = text.index(blocks[-1][1]) + len(blocks[-1][1])
    return text[:start] + body + text[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--skip', nargs='*', default=[], help='跳过的章号(如正在翻译中)')
    a = ap.parse_args()

    en_dir = ROOT / 'calvin/psalms-2-en'
    zh_dir = ROOT / 'calvin_raw/psalms-2/zh_chapters'
    en_defs = json.loads((ROOT / 'calvin_raw/psalms-2/footnote_defs.json')
                         .read_text(encoding='utf-8'))
    zh_path = ROOT / 'calvin_raw/psalms-2/zh_footnote_defs.json'
    zh_defs = json.loads(zh_path.read_text(encoding='utf-8'))

    n_en = n_zh = 0
    for ep in sorted(en_dir.glob('*.md'),
                     key=lambda p: int(p.stem) if p.stem.isdigit() else 999):
        if not ep.stem.isdigit() or ep.stem in a.skip:
            continue
        et = ep.read_text(encoding='utf-8')
        codes = {c.lower() for c in literals(et)}
        if not codes:
            continue
        zp = zh_dir / f'{ep.stem}.md'
        zt = zp.read_text(encoding='utf-8') if zp.exists() else None
        zh_lit = {c.lower() for c in literals(zt)} & codes if zt else set()

        et2 = replace_literals(et, codes)
        et2, _ = harvest_and_drop(et2, codes)
        et2 = add_defs(et2, {c: en_defs['ft' + c[1:]] for c in codes
                             if 'ft' + c[1:] in en_defs})
        n_en += len(codes)
        line = f'ch{ep.stem}: 英文 {len(codes)} 条'

        if zt is not None:
            zt2 = replace_literals(zt, zh_lit)
            zt2, got = harvest_and_drop(zt2, codes)
            zh_defs.update(got)
            n_zh += len(zh_lit)
            line += f'；中文 {len(zh_lit)} 条，收割定义 {len(got)} 条'
            miss = codes - zh_lit
            if miss:
                line += f'（中文未见字面: {sorted(miss)}）'
        else:
            line += '；中文未翻译，跳过'
        print(line)

        if not a.dry_run:
            ep.chmod(0o644); ep.write_text(et2, encoding='utf-8')
            if zt is not None:
                zp.chmod(0o644); zp.write_text(zt2, encoding='utf-8'); zp.chmod(0o444)

    print(f'\n合计 英文 {n_en} 条 / 中文 {n_zh} 条'
          + ('（预演，未写入）' if a.dry_run else ''))
    if not a.dry_run:
        zh_path.write_text(json.dumps(zh_defs, ensure_ascii=False, indent=1),
                           encoding='utf-8')
        print(f'zh_footnote_defs.json → {len(zh_defs)} 条')


if __name__ == '__main__':
    main()
