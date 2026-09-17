#!/usr/bin/env python3
"""清掉 AGES 页底脚注在切章时留下的重复红字残条。

AGES 的页底脚注在按页切章时会被归到邻章，于是同一条注在两处各出现一份：
一处已被正规化成 `[^f904]: …`（多半落在下一章文件里），另一处以红字
`ft904.` 原样留在上一章或附录页的正文中间——读者看到的就是正文里冒出一个
ft904（约拿书序里的 f1t 是同一类，只是那套码 AGES 压根没收注文）。

只删「该号在本书已有正规定义」的那一份重复。没有定义的孤儿条一律留着并报出
来：宁可页面上留个红字，也不能悄悄删掉全书唯一一份注文（[[feedback_no_fabrication]]
的反面——不编造，也不静默丢弃）。
"""
import re
from pathlib import Path

RESIDUE_RE = re.compile(
    r'^<span style="color:#800000">\s*[Ff][Tt]?(\d+[A-Za-z]?)\.?\s*</span>\s*\S.*$', re.M)
DEF_LABEL_RE = re.compile(r'^\[\^f(\d+[A-Za-z]?)\]:', re.M)


def drop_duplicate_footnote_residue(out_dir: Path, verbose: bool = True):
    """返回 (删除数, 保留的孤儿列表)。"""
    files = sorted(Path(out_dir).glob('*.md'))
    known = set()
    for f in files:
        known |= {m.group(1).lower()
                  for m in DEF_LABEL_RE.finditer(f.read_text(encoding='utf-8'))}
    dropped = 0
    orphans = []
    for f in files:
        t = f.read_text(encoding='utf-8')

        def rep(m):
            nonlocal dropped
            if m.group(1).lower() in known:
                dropped += 1
                return ''
            orphans.append((f.name, m.group(1)))
            return m.group(0)

        new = re.sub(r'\n{4,}', '\n\n\n', RESIDUE_RE.sub(rep, t))
        if new != t:
            f.write_text(new, encoding='utf-8')
    if verbose:
        name = Path(out_dir).name
        if dropped:
            print(f'  {name}: 删除重复脚注残条 {dropped} 处')
        if orphans:
            print(f'  {name}: 保留无定义的孤儿残条 {len(orphans)} 处 -> {orphans[:6]}')
    return dropped, orphans


if __name__ == '__main__':
    import sys
    for d in sys.argv[1:]:
        drop_duplicate_footnote_residue(Path(d))
