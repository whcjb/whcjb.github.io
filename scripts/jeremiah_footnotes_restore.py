#!/usr/bin/env python3
"""把耶利米书英文版的脚注还原成标准结构：正文 [^fXN] + 章末 [^fXN]: 定义。

现状（AGES 提取遗留，与 psalms「末章吞附录」同类）：
  - 正文引用**在**：`<span style="color:#800000">fA128</span>`（卷一 590 处）
  - 附录定义被末章整个吞掉：jeremiah-1-en/24.md 613KB，正文只占前 171 行，
    之后 577KB 全是 602 条 `ftA1` 定义；jeremiah-2-en/52.md 同类
  - 正文码 fA128 ↔ 附录码 ftA128（差一个 t，见 memory: 正文码与附录码别查混）

本脚本做三件事（只动英文版；耶利米书中文一章未译、零缓存，改源无代价）：
  1. 末章切出附录，解析成 {code: 定义}
  2. 各章正文的 span 引用改写成标准脚注引用 [^fA128]
  3. 定义按「该章出现过的引用」分配，追加到对应章末

配不上的一律**原样保留**并打印，绝不臆造（正文有引用无定义 / 附录有定义无引用）。

用法:
    python3 scripts/jeremiah_footnotes_restore.py --vol 1 --dry-run
    python3 scripts/jeremiah_footnotes_restore.py --vol 1
"""
import argparse, re, sys
from collections import OrderedDict, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# 附录里的定义码**不一定带 t**：PDF p1242 那条就写作 fD52 而非 ftD52（AGES 的
# 码有格式变体，见 memory: AGES脚注码有大小写变体）。所以附录段内一律宽松匹配，
# 靠归一化配对，不靠字面相等。
DEF_SPAN = re.compile(r'<span style="color:#800000">\s*(f[tT]?[A-Za-z]?\d+[a-z]?)\s*</span>')
# 定位附录起点必须用**严格**的 ft 码：附录第一条一定是 ftA1（带 t）。若用上面的
# 宽松式，末章正文里的引用（fA…）会被当成第一条定义，正文被误切掉。
STRICT_DEF = re.compile(r'<span style="color:#800000">\s*f[tT][A-Za-z]?\d+[a-z]?\s*</span>')
REF_SPAN = re.compile(r'<span style="color:#800000">\s*(f(?![tT])[A-Za-z]?\d+[a-z]?)\s*</span>')
PAGE_RE = re.compile(r'<!--\s*PAGE\s+\d+\s*-->')

VOLS = {
    '1': ('calvin/jeremiah-1-en', 24, 1, 23),
    '2': ('calvin/jeremiah-2-en', 52, 24, 51),
}


NORM_RE = re.compile(r'^f[tT]?([A-Za-z]?)(\d+)([a-z]?)$')


def norm(code):
    """归一化脚注码，吸收 t 的有无与大小写差异：
    fA128 / ftA128 / FTA128 → ('A', 128, '')。配不上就返回原串。"""
    m = NORM_RE.match(code)
    return (m.group(1).upper(), int(m.group(2)), m.group(3).lower()) if m else code


def split_appendix(text):
    """末章文本 → (正文部分, 附录部分)。附录从第一条定义所在行起。"""
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        if STRICT_DEF.search(ln):
            return '\n'.join(lines[:i]).rstrip() + '\n', '\n'.join(lines[i:])
    return text, ''


def parse_defs(appendix):
    """附录 → OrderedDict{code: 定义正文（单行）}"""
    out = OrderedDict()
    hits = list(DEF_SPAN.finditer(appendix))
    for k, m in enumerate(hits):
        end = hits[k + 1].start() if k + 1 < len(hits) else len(appendix)
        body = appendix[m.end():end]
        body = PAGE_RE.sub(' ', body)                 # 分页标记不属于脚注内容
        body = re.sub(r'^\s*[.、,]\s*', '', body)      # 定义常以 "ftA1." 起，剥掉紧跟的点
        body = re.sub(r'\s*\n\s*', ' ', body).strip()  # 压成单行，续行不必缩进
        body = re.sub(r'\s{2,}', ' ', body)
        if body:
            out.setdefault(m.group(1), body)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', default='1', choices=['1', '2'])
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    d, last_ch, lo, hi = VOLS[args.vol]
    EN = ROOT / d

    tail = EN / f'{last_ch}.md'
    body_last, appendix = split_appendix(tail.read_text(encoding='utf-8'))
    if not appendix:
        sys.exit(f'{tail} 里找不到附录定义，可能已经处理过')
    defs = parse_defs(appendix)
    defs_ci = {norm(k): (k, v) for k, v in defs.items()}
    print(f'附录：{len(defs)} 条定义，切出后末章正文 {len(body_last):,} bytes '
          f'（原 {tail.stat().st_size:,}）')

    # 各章的引用
    per_ch = OrderedDict()
    for p in sorted(EN.glob('*.md'), key=lambda x: (not x.stem.isdigit(),
                                                    int(x.stem) if x.stem.isdigit() else 0)):
        txt = body_last if p.name == tail.name else p.read_text(encoding='utf-8')
        codes = [m.group(1) for m in REF_SPAN.finditer(txt)]
        if codes or p.name == tail.name:
            per_ch[p] = (txt, codes)

    used, missing_def, total_ref = set(), [], 0
    plans = []
    for p, (txt, codes) in per_ch.items():
        total_ref += len(codes)
        chapter_defs = OrderedDict()
        def repl(m):
            code = m.group(1)
            hit = defs_ci.get(norm(code))
            if not hit:
                missing_def.append((p.stem, code))
                return m.group(0)                      # 配不上 → 原样保留
            chapter_defs.setdefault(code, hit[1])
            used.add(hit[0])
            return f'[^{code}]'
        new = REF_SPAN.sub(repl, txt)
        if chapter_defs:
            block = '\n'.join(f'[^{c}]: {t}' for c, t in chapter_defs.items())
            new = new.rstrip() + '\n\n' + block + '\n'
        plans.append((p, new, len(chapter_defs)))

    orphan = [k for k in defs if k not in used]
    print(f'正文引用 {total_ref} 处；配上定义 {len(used)} 条')
    print(f'  正文有引用但附录无定义 {len(missing_def)} 处 → {missing_def[:6]}（原样保留）')
    print(f'  附录有定义但正文无引用 {len(orphan)} 条 → {orphan[:8]}（留在末章附录段）')

    if orphan:      # 无主定义不丢弃，保留在末章末尾，另加标题说明
        for i, (p, new, n) in enumerate(plans):
            if p.name == tail.name:
                block = '\n'.join(f'[^{c}]: {defs[c]}' for c in orphan)
                plans[i] = (p, new.rstrip() + '\n\n<!-- 以下脚注定义在本卷正文中'
                            '找不到对应引用，原样保留，勿删 -->\n' + block + '\n', n)

    if args.dry_run:
        print('\n[dry-run] 各章将写入：')
        for p, new, n in plans:
            print(f'  {p.name:12s} {len(new):>9,} bytes  追加定义 {n} 条')
        return
    for p, new, n in plans:
        p.write_text(new, encoding='utf-8')
        print(f'  ✓ {p.name:12s} {len(new):>9,} bytes  定义 {n} 条')


if __name__ == '__main__':
    main()
