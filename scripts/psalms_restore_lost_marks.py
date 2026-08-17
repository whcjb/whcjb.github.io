#!/usr/bin/env python3
"""把「未定位的注释」里标记仍在正文中的脚注还原成真引用。

来由：英文发布阶段识别正文脚注标记的正则只写了小写 `f[a-e]\\d+`，而 AGES 源里有一批
标记是小型大写（FE153、FD423…）。这些标记既没被转成 `[^code]`，也没被清掉，而是以
**字面文本**留在正文里；定义那头找不到引用，就被归进章末的「未定位的注释」块。

所以这不是「位置已佚」，是「位置一直在，只是没认出来」。psalms-2 共 29 条孤儿，
其中 18 条的字面标记在英文章节与中文 raw 里各出现且仅出现一次 —— 原地替换即可，
不需要任何推断。

余下 11 条（fc407 ff110 fc577 fc601 fd141 fd233 ff123 fd360 fd361 fe1 fe98）
正文里确实找不到标记，需对照 PDF 才能定位，本脚本不处理。

用法:
    python3 scripts/psalms_restore_lost_marks.py --dry-run
    python3 scripts/psalms_restore_lost_marks.py
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EN_DIR = ROOT / 'calvin/psalms-2-en'
ZH_DIR = ROOT / 'calvin_raw/psalms-2/zh_chapters'

# ch84 的两个 span 在中译里被合并、且多出一个字面 fc456, 结构要单独处理, 不走通用替换
TARGETS = [
    ('119', 'fd423'),
    ('135', 'fe153'), ('135', 'fe155'), ('135', 'fe156'), ('135', 'fe157'),
    ('135', 'fe158'), ('135', 'fe159'), ('135', 'fe160'), ('135', 'fe161'),
    ('135', 'fe162'), ('135', 'fe167'), ('135', 'fe168'),
    ('136', 'fe169'), ('136', 'fe172'), ('136', 'fe173'), ('136', 'fe174'),
    ('136', 'fe175'),
]


def mark_re(code):
    # 前面排除 ^ 是为了不碰已经是 [^code] 的引用
    return re.compile(r'(?<![A-Za-z0-9^])' + code + r'(?![A-Za-z0-9])', re.I)


def replace_one(text, code):
    """把唯一一处字面标记换成 [^code]；返回 (新文本, 上下文) 或 (None, 原因)。"""
    pat = mark_re(code)
    hits = list(pat.finditer(text))
    if len(hits) != 1:
        return None, f'字面标记出现 {len(hits)} 次'
    m = hits[0]
    lo, hi = m.start(), m.end()
    ctx = re.sub(r'\s+', ' ', re.sub('<[^>]+>', '', text[max(0, lo - 55):hi + 25]))
    # 标记前常有多余空格（原文是上标），中文正文不留空格
    pre = text[:lo]
    if pre.rstrip() != pre and re.search(r'[　-〿＀-￯一-鿿]$', pre.rstrip()):
        pre = pre.rstrip()
    return pre + f'[^{code}]' + text[hi:], ctx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    ok = fail = 0
    for ch, code in TARGETS:
        ep, zp = EN_DIR / f'{ch}.md', ZH_DIR / f'{ch}.md'
        et, zt = ep.read_text(encoding='utf-8'), zp.read_text(encoding='utf-8')
        new_e, ce = replace_one(et, code)
        new_z, cz = replace_one(zt, code)
        if new_e is None or new_z is None:
            print(f'ch{ch} {code}: 跳过 — EN {ce if new_e is None else "ok"} / '
                  f'ZH {cz if new_z is None else "ok"}')
            fail += 1
            continue
        print(f'ch{ch} {code}')
        print(f'   EN …{ce}')
        print(f'   ZH …{cz}')
        if not a.dry_run:
            ep.chmod(0o644); zp.chmod(0o644)
            ep.write_text(new_e, encoding='utf-8')
            zp.write_text(new_z, encoding='utf-8')
            zp.chmod(0o444)
        ok += 1
    print(f'\n{"预演" if a.dry_run else "已还原"} {ok} 条 / 跳过 {fail} 条')


if __name__ == '__main__':
    main()
