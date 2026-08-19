#!/usr/bin/env python3
"""把 AGES 老式字体抽成拉丁乱码的希伯来文还原成 Unicode 希伯来文。

背景：calvin 注释里 teal 色 span（`<span style="color:#008080">…</span>`、
structured.txt 里是 `<sty c="008080">…</sty>`）本该是希伯来原文，AGES 用的是
非 Unicode 老字体，导出后变成 `µ[m` 这类拉丁乱码。**不是 OCR 失败，是字体编码
没转换**（希腊文那套字体映射到真 Unicode，所以希腊文没坏）。

解码算法：整串**倒序**（视觉序 → 逻辑序），再逐字符映射。输出逻辑序，浏览器
靠 Unicode bidi 自动右到左显示，不需要加 dir 属性。

    µ[m  →  倒序 m [ µ  →  מ ע ם  →  מעם   (旁边音译 megnam，「从民中」)

含映射表外字符的 span 一律**跳过不猜**（占位符 XXX、带元音点的变体等）。

缓存 key 迁移
------------
英文源（calvin/<book>-en/N.md）同时是 translate_filibi 的翻译输入，缓存文件名
是段落原文的 md5。直接改源会让整卷缓存失效、重译一遍（一章约 $1.3）。所以本
脚本改英文源时，会把 zh_cache/<旧md5>.txt 一并改名为 <新md5>.txt，并对缓存内
容做同样解码——改完 `--resume` 仍然全部命中。

用法:
    python3 scripts/decode_ages_hebrew.py --book isaiah-1 --dry-run
    python3 scripts/decode_ages_hebrew.py --book isaiah-1
    python3 scripts/decode_ages_hebrew.py --paths calvin/micah  # 任意目录/文件
"""
import argparse, hashlib, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parent.parent

# 源字符 → 希伯来（映射在**倒序之后**逐字进行）
MAP = {
    'a': 'א', 'b': 'ב', 'g': 'ג', 'd': 'ד', 'h': 'ה', 'w': 'ו', 'z': 'ז',
    'j': 'ח', 'f': 'ט', 'y': 'י', 'k': 'כ', 'l': 'ל', 'm': 'מ', 'n': 'נ',
    's': 'ס', '[': 'ע', 'p': 'פ', 'x': 'צ', 'q': 'ק', 'r': 'ר', 'ç': 'ש',
    't': 'ת',
    # 词尾形
    'µ': 'ם', 'ˆ': 'ן', '˚': 'ך', '≈': 'ץ', 'ã': 'ף',
    # 连字符 maqaf
    'A': '־',
    # 大写位 = 带 dagesh 的变体形，归基字母。每个都由文中紧跟的音译独立核对过：
    #   Lm[→עמל gnamal / Yl[→עלי ale / Rwa→אור or / Dy→יד yad /
    #   H[wmç→שמועה shemugnah / La wnm[ yk→כי עמנו אל ki Immanu-el
    # 未见到实例的大写字母**不猜**，遇到再按音译核对后补。
    'T': 'ת', 'B': 'ב', '5': 'ך', 'L': 'ל', 'Y': 'י', 'R': 'ר', 'D': 'ד',
    'H': 'ה',
    ' ': ' ',
}
HEB_RE = re.compile(r'[֐-׿]')
SPAN_RE = re.compile(r'(<span style="color:#008080">)(.*?)(</span>)', re.S)
STY_RE  = re.compile(r'(<sty c="008080"[^>]*>)(.*?)(</sty>)', re.S)


def decode(garble: str):
    """乱码 → 希伯来；不可解码返回 None（调用方保持原样）。"""
    if not garble or HEB_RE.search(garble):
        return None                      # 空 / 已经是 Unicode 希伯来
    if any(c not in MAP for c in garble):
        return None                      # 含映射表外字符，按规矩跳过不猜
    return ''.join(MAP[c] for c in reversed(garble))


def convert_text(text: str):
    """返回 (新文本, 转换数, 跳过数)"""
    n = skipped = 0

    def repl(m):
        nonlocal n, skipped
        out = decode(m.group(2))
        if out is None:
            if not HEB_RE.search(m.group(2)) and m.group(2).strip():
                skipped += 1
            return m.group(0)
        n += 1
        return m.group(1) + out + m.group(3)

    text = SPAN_RE.sub(repl, text)
    text = STY_RE.sub(repl, text)
    return text, n, skipped


# ── 翻译缓存 key 迁移 ──────────────────────────────────────────────────
def md5key(t: str) -> str:
    return hashlib.md5(t.encode('utf-8')).hexdigest()[:16]


def translatable_texts(raw: str):
    """复刻 translate_filibi.translate_file 的取段逻辑，返回待翻文本列表。"""
    import translate_filibi as tf
    lines = raw.split('\n')
    segments, in_fm, fm_closed = [], False, False
    for idx, l in enumerate(lines):
        if not fm_closed and l.strip() == '---':
            if not in_fm and idx == 0:
                in_fm = True
            elif in_fm:
                in_fm, fm_closed = False, True
            segments.append(('pass', l)); continue
        if in_fm:
            segments.append(('pass', l)); continue
        segments.append(tf.classify(l))

    out = []
    for kind, data in segments:
        if kind in ('h1', 'h2', 'body', 'bq'):
            out.append(data)
        elif kind == 'fn':
            out.append(data[1])
        elif kind == 'md_table_header':
            out.append(data[0])
        elif kind == 'md_table_row':
            if data[0].strip():
                out.append(data[0])
        elif kind == 'html_td_row':
            if data[1].strip():
                out.append(data[1])
        elif kind == 'html_th':
            out.append(data[1])
    return out


def migrate_cache(old_raw: str, new_raw: str, cache_dir: Path, dry: bool):
    """英文源改动后，把 zh_cache/<旧md5>.txt 改名成 <新md5>.txt（内容也解码）。"""
    if not cache_dir.is_dir():
        return 0, 0
    olds, news = translatable_texts(old_raw), translatable_texts(new_raw)
    if len(olds) != len(news):
        print(f'    !! 取段数不一致（{len(olds)} vs {len(news)}），跳过缓存迁移')
        return 0, 0
    moved = missing = 0
    for o, nw in zip(olds, news):
        if o == nw:
            continue
        src, dst = cache_dir / f'{md5key(o)}.txt', cache_dir / f'{md5key(nw)}.txt'
        if not src.exists():
            if not dst.exists():
                missing += 1
            continue
        if not dry:
            zh = src.read_text(encoding='utf-8')
            zh_new, _, _ = convert_text(zh)      # 中文缓存里同一个 span 也解码
            dst.write_text(zh_new, encoding='utf-8')
            src.unlink()
        moved += 1
    return moved, missing


# ── 文件处理 ──────────────────────────────────────────────────────────
def process(path: Path, dry: bool, cache_dir=None):
    raw = path.read_text(encoding='utf-8')
    new, n, skipped = convert_text(raw)
    if n == 0:
        return 0, skipped, 0, 0
    moved = missing = 0
    if cache_dir is not None:
        moved, missing = migrate_cache(raw, new, cache_dir, dry)
    if not dry:
        mode = path.stat().st_mode & 0o777
        if not mode & 0o200:                 # raw 章节是 444 只读
            os.chmod(path, 0o644)
        path.write_text(new, encoding='utf-8')
        if not mode & 0o200:
            os.chmod(path, mode)
    return n, skipped, moved, missing


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', help='translate_filibi 的 book key，如 isaiah-1')
    ap.add_argument('--paths', nargs='*', default=[], help='额外的文件/目录')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    targets = []          # [(path, cache_dir_or_None)]
    if args.book:
        import translate_filibi as tf
        cfg = tf.BOOKS[args.book]
        cache = Path(cfg['cache'])
        src, out = Path(cfg['src']), Path(cfg['out'])
        # 英文源：改了要迁缓存
        for p in sorted(src.rglob('*.md') if src.is_dir() else [src]):
            targets.append((p, cache))
        # 中译 raw + 合并 md + structured：不参与 md5 key
        for p in sorted(out.rglob('*.md') if out.is_dir() else [out]):
            targets.append((p, None))
        rawdir = out.parent
        for p in sorted(rawdir.glob('*.md')) + sorted(rawdir.glob('*_structured.txt')):
            targets.append((p, None))
        pub = ROOT / 'calvin' / args.book
        if pub.is_dir():
            for p in sorted(pub.rglob('*.md')):
                targets.append((p, None))
    for s in args.paths:
        p = ROOT / s
        for q in (sorted(p.rglob('*.md')) if p.is_dir() else [p]):
            targets.append((q, None))

    tot = tot_skip = tot_moved = tot_missing = 0
    touched = 0
    for p, cache in targets:
        n, skipped, moved, missing = process(p, args.dry_run, cache)
        tot += n; tot_skip += skipped; tot_moved += moved; tot_missing += missing
        if n:
            touched += 1
            rel = p.relative_to(ROOT)
            extra = f'  缓存迁移 {moved}' if moved else ''
            extra += f'  缓存缺失 {missing}' if missing else ''
            print(f'  {rel}: {n} 处{extra}')
    tag = '[dry-run] ' if args.dry_run else ''
    print(f'\n{tag}解码 {tot} 处 / {touched} 文件；'
          f'跳过（映射表外字符）{tot_skip}；缓存改名 {tot_moved}，未命中 {tot_missing}')


if __name__ == '__main__':
    main()
