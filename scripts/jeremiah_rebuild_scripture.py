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

# ⚠️ 匹配体内绝不能跨到下一个块。最初写成 `.*?\n</div>`，以为非贪婪会停在本框
# 闭合处——实际单语框的闭合形式不同，它一路跨过好几个块才停（匹配 1:1-3 时吞掉
# 36,531 字符、5 个 h2、9 个经文框），中间的注释就被连带替换掉了。而且净增删
# 数字看不出来：那一版跑完显示净增 9k 行，照样把内容吞了。故用负向前瞻锁死边界。
_NO_CROSS = r'(?:(?!<h2 class="scripture-anchor")(?!<div class="scripture-box").)*?'
NEW_BLOCK = re.compile(
    r'<h2 class="scripture-anchor"[^>]*data-ref="([^"]+)"[^>]*>' + _NO_CROSS + r'</h2>\s*\n+'
    r'<div class="scripture-box scripture-box--bilingual"[^>]*>' + _NO_CROSS + r'\n</div>', re.S)
OLD_BLOCK = re.compile(
    r'<h2 class="scripture-anchor"[^>]*data-ref="([^"]+)"[^>]*>' + _NO_CROSS + r'</h2>\s*\n+'
    r'<div class="scripture-box"[^>]*>' + _NO_CROSS + r'\n</div>', re.S)
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
        # 有些双语块前面没有 <h2 scripture-anchor>（直接就是 div），上面按
        # h2+data-ref 配对的正则抓不到它们。补一份按块内 ages-code 索引的表，
        # 替换时用旧块自己的 h2 兜底。
        BARE = re.compile(r'<div class="scripture-box scripture-box--bilingual"[^>]*>'
                          + _NO_CROSS + r'\n</div>', re.S)
        new_by_code = {}
        for m in BARE.finditer(merged):
            cm = re.search(r'ages-code">&lt;(\d{6})&gt;', m.group(0))
            if cm:
                new_by_code.setdefault(cm.group(1), m.group(0))
        print(f'== {raw_name}: 新双语块 {len(new_blocks)} 个')

        n_file = n_repl = n_stray = n_fn = n_keep = n_bad = 0
        for p in sorted((ROOT / en_dir).glob('*.md'),
                        key=lambda x: (not x.stem.isdigit(),
                                       int(x.stem) if x.stem.isdigit() else 0)):
            t = p.read_text(encoding='utf-8')
            orig = t
            for m in list(OLD_BLOCK.finditer(t))[::-1]:      # 从后往前，位移不乱
                ref = m.group(1)
                new = new_blocks.get(ref)
                if not new:
                    # 退路：按旧块内的 ages-code 找那些「没有 h2」的新双语块，
                    # 并把旧块自己的 h2 接到前面，保住锚点与导航
                    cm = re.search(r'ages-code">&lt;(\d{6})&gt;', m.group(0))
                    bare = new_by_code.get(cm.group(1)) if cm else None
                    if not bare:
                        continue
                    h2m = re.match(r'(<h2 class="scripture-anchor".*?</h2>)\s*\n+',
                                   m.group(0), re.S)
                    new = (h2m.group(1) + '\n\n' + bare) if h2m else bare
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
                # 逐句抽查：替换前的注释句必须在替换后仍找得到，否则判为吞并、拒写。
                # 这一步是必须的——净增删数字看不出吞并（第一版跨块吞了内容，
                # 却仍显示净增 9k 行，就这样被提交上去了）。
                flat = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', t))
                cand = [l for l in orig.split('\n')
                        if len(l) > 150 and not l.startswith('<')
                        and not re.match(r'\s*\*?\*?\d+\.', l)]
                lost = [c for c in cand
                        if re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', c))[40:120].strip()
                        not in flat]
                if lost:
                    print(f'     !! {p.name}: {len(lost)}/{len(cand)} 段注释替换后找不到 → 拒写')
                    n_bad += 1
                    continue
                n_file += 1
                if not args.dry_run:
                    p.write_text(t, encoding='utf-8')
        print(f'   写入 {n_file} 文件，替换经文块 {n_repl}，散落段 {n_stray}，'
              f'脚注 {n_fn}/{n_keep}，因注释丢失拒写 {n_bad} 个')


if __name__ == '__main__':
    main()
