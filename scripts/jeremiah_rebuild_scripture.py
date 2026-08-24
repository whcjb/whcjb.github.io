#!/usr/bin/env python3
"""用重新提取的双语经文块，替换耶利米书分章 md 里散架的经文区。

背景：耶利米书 2026-06-02 提取时，双语列分界阈值 LATIN_X_MIN 用的是照 1cor
（拉丁列 x0=218）定的 200，而耶利米书拉丁列 x0=198 —— 差 2 个点，整列被判成
英文左栏，双语状态机从未激活。结果 scripture-box 里只剩英文首节，拉丁文和其余
英文节散落成独立 <p>（29 章 135 处，54 处还被排成 text-align:right）。
skill §11.0 明确记着这种形态「被用户打回过」。

已在 calvin_extract.py 的 VOLUMES 给两卷加 latin_x_min:190 并重新提取，新的
合并 md 里已是规范双语表格。本脚本只把**经文区**换过去，其余内容（注释正文、
已修好的 952 条脚注）一律不动。

⚠️ 删散落段必须用**内容比对**，不能靠样式猜：
   第一版按 `<p style="margin-left:2em;">` + 数字开头来判定，结果把注释里的
   缩进引文段也当成经文吃掉了（dry-run 显示 130+ 个脚注锚点凭空消失，那些
   引用本在注释里）。现改为：只有该段文字确实出现在新双语表格中（证明它就是
   经文、已被新表覆盖）才删，否则原样保留。

用法: python3 scripts/jeremiah_rebuild_scripture.py [--dry-run]
"""
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOLS = [('jeremiah-1', 'calvin/jeremiah-1-en'), ('jeremiah-2', 'calvin/jeremiah-2-en')]

NEW_BLOCK = re.compile(
    r'<h2 class="scripture-anchor"[^>]*data-ref="([^"]+)"[^>]*>.*?</h2>\s*\n+'
    r'<div class="scripture-box scripture-box--bilingual"[^>]*>.*?\n</div>', re.S)
OLD_BLOCK = re.compile(
    r'<h2 class="scripture-anchor"[^>]*data-ref="([^"]+)"[^>]*>.*?</h2>\s*\n+'
    r'<div class="scripture-box"[^>]*>.*?\n</div>', re.S)
PARA = re.compile(r'<p style="(?:margin-left:2em;|text-align:right;)"[^>]*>.*?</p>|'
                  r'<p style="(?:margin-left:2em;|text-align:right;)"[^>]*>(?:(?!\n\n).)*', re.S)
FN_REF = re.compile(r'\[\^(f[A-Za-z]?\d+[a-z]?)\]')


def plain(s):
    """剥标记、压空白，用于内容比对"""
    s = re.sub(r'\[\^[^\]]+\]', '', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'[*_`]', '', s)
    return re.sub(r'\s+', ' ', s).strip()


def covered_by(seg_text, table_text):
    """seg 的文字是否已被新表格覆盖：取若干长片段看是否都能在表里找到"""
    p = plain(seg_text)
    if len(p) < 40:
        return False
    probes = [p[i:i + 40] for i in range(0, min(len(p), 200), 40)]
    hit = sum(1 for x in probes if x and x in table_text)
    return hit >= max(1, len(probes) * 3 // 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    for raw_name, en_dir in VOLS:
        merged = (ROOT / f'calvin_raw/{raw_name}/calvin_{raw_name}.md').read_text(encoding='utf-8')
        new_blocks = {m.group(1): m.group(0) for m in NEW_BLOCK.finditer(merged)}
        print(f'== {raw_name}: 新双语块 {len(new_blocks)} 个')

        n_file = n_repl = n_stray = n_fn = n_keep = 0
        for p in sorted((ROOT / en_dir).glob('*.md'),
                        key=lambda x: (not x.stem.isdigit(),
                                       int(x.stem) if x.stem.isdigit() else 0)):
            t = p.read_text(encoding='utf-8')
            orig = t
            for m in list(OLD_BLOCK.finditer(t))[::-1]:      # 从后往前，位移不乱
                ref = m.group(1)
                new = new_blocks.get(ref)
                if not new:
                    continue
                table_plain = plain(new)
                start, end = m.start(), m.end()
                # 逐段检查其后的缩进/右对齐段：只有内容已被新表覆盖的才吃掉
                cur = end
                while True:
                    nxt = PARA.match(t, cur) or PARA.match(t, cur + 1) or PARA.match(t, cur + 2)
                    if not nxt:
                        break
                    seg = nxt.group(0)
                    if not covered_by(seg, table_plain):
                        break
                    # 该段里的脚注引用要带走并在新块中复位
                    for fm in FN_REF.finditer(seg):
                        ctx = plain(seg[max(0, fm.start() - 70):fm.start()])[-38:]
                        if ctx and ctx in table_plain:
                            n_fn += 1
                        else:
                            n_keep += 1
                    cur = nxt.end()
                    n_stray += 1
                t = t[:start] + new + t[cur:]
                n_repl += 1
            if t != orig:
                n_file += 1
                if not args.dry_run:
                    p.write_text(t, encoding='utf-8')
        print(f'   {n_file} 文件，替换经文块 {n_repl}，吃掉已覆盖的散落段 {n_stray}，'
              f'其中脚注可复位 {n_fn}，需人工确认 {n_keep}')


if __name__ == '__main__':
    main()
