#!/usr/bin/env python3
"""框头写着 1-11 节，框里只有 1-4 节，其余几节掉在框外——把它们收回框内。

与 `fix_split_scripture_box.py --sweep` 是同一类毛病，但那一版扫不到这一种：
框外那几节前面往往隔着一个 `<!-- PAGE 37 -->` 页界注释，sweep 碰上块级标记就
停了；而且它最多只往回收 3 块，这里动辄七八块（约珥书 2:1-11 就有 13 块）。

这里按「框头节号范围是否被覆盖」驱动：一直往后收，直到缺的节号都齐了为止。
每一块都要是经文，判据是含有缺的那些节号；遇到下面这些一律停手：
  · `<h2 class="scripture-anchor">`（下一段经文的锚点）
  · 另一个 `<div>` / `<table>`（另一种版式的块，不属于这个框）
  · `[^fN]:` 脚注定义、`{:` kramdown 属性行
  · 注释段（粗体节号 + 红色斜体经文短语）
页界注释 `<!-- PAGE N -->` 不算阻断，跟着一起收进框里（它本来就不渲染）。

用法：
    python3 scripts/fix_box_verse_spill.py [--apply]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
REF = re.compile(r'class="verse-range">([^<]+)<')
VNUM = re.compile(r'(?<![\dA-Za-z])(\d{1,3})\s*[.．](?=\s|\*|$)')
PAGE = re.compile(r'^<!-- PAGE \d+ -->$')
PAGE_LEAD = re.compile(r'^(?:<!-- PAGE \d+ -->\s*\n)+')
STOP = ('<h', '<div', '</div', '<table', '[^', '{:', '|', '---')
COMMENTARY = re.compile(r'^(?:<p[^>]*>)?\s*(?:\*\*|<strong>)\d{1,3}[.．](?:\*\*|</strong>)?\s*'
                        r'<span style="color:#800000">\s*\*')
MAX_BLOCKS = 40


def plain(s: str) -> str:
    """剥掉标签与 markdown 强调符再找节号。

    节号有两种写法：`**6.**` 与 `**6**.`（点在粗体外面）。不去掉 `*`，第二种
    会变成 `6**.`，节号正则认不出来——约珥书英文版就因此在第 6 节停住。"""
    return re.sub(r'\*', '', re.sub(r'<[^>]+>', ' ', s))


def expand(rng: str) -> set:
    rng = rng.split(':')[-1].strip()
    out = set()
    for part in re.split(r'[,，]', rng):
        part = part.strip().replace('—', '-').replace('–', '-')
        m = re.fullmatch(r'(\d+)\s*-\s*(\d+)', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b >= a and b - a < 200:
                out |= {str(x) for x in range(a, b + 1)}
        elif part.isdigit():
            out.add(part)
    return out


def blocks_after(text: str, pos: int):
    """框之后按空行切块，产出 (块文本, 起, 止)。"""
    i = pos
    while i < len(text):
        while i < len(text) and text[i] == '\n':
            i += 1
        j = text.find('\n\n', i)
        if j < 0:
            j = len(text)
        blk = text[i:j]
        if blk.strip():
            yield blk.strip(), i, j
        i = j


def fix_file(path: Path, apply: bool):
    text = path.read_text(encoding='utf-8')
    hits = []
    while True:
        moved = False
        for m in BOX.finditer(text):
            mr = REF.search(m.group(0))
            if not mr:
                continue
            want = expand(mr.group(1))
            if not want:
                continue
            missing = want - set(VNUM.findall(plain(m.group(0))))
            if not missing:
                continue
            take, end = [], m.end()
            for blk, s, e in blocks_after(text, m.end()):
                if len(take) >= MAX_BLOCKS:
                    break
                if PAGE.match(blk):
                    take.append(blk)
                    end = e
                    continue
                # 页界注释常与下一段挤在同一块里（中间没有空行），判断前先剥掉，
                # 否则「注释段」这条认不出来，会把注释整段收进经文框
                body_only = PAGE_LEAD.sub('', blk)
                if body_only.startswith(STOP) or COMMENTARY.match(body_only):
                    break
                got = set(VNUM.findall(plain(body_only)))
                # 「含有还缺的节号」这条太紧：第 6 节的拉丁文自成一块、块里只有
                # 「6.」，而 6 已经随上一块（第 5 节拉丁文末尾带着第 6 节中文）
                # 补齐了，于是在这里就停住，后面第 7-11 节全丢在框外（约珥书 2
                # 踩过）。改判「这一块的节号都落在框头范围内」。
                if not got or not got <= want:
                    break
                take.append(blk)
                end = e
                missing -= got
            take = [b for b in take if not PAGE.match(b)] and take or []
            # 末尾若只剩页界注释，去掉（别把它挪进框里当结尾）
            while take and PAGE.match(take[-1]):
                take.pop()
            if not take:
                continue
            body = '\n\n'.join(take)
            new_box = m.group(0)[:-len('</div>')].rstrip('\n') + '\n\n' + body + '\n\n</div>'
            # 重新定位被搬走那一段的结束位置
            cut = text.find(take[-1], m.end()) + len(take[-1])
            text = text[:m.start()] + new_box + text[cut:]
            hits.append((mr.group(1), len(take)))
            moved = True
            break
        if not moved:
            break
    if hits:
        for rng, n in hits:
            print(f'  {path} [{rng}]: 收回 {n} 块')
        if apply:
            path.write_text(text, encoding='utf-8')
    return len(hits)


def main() -> int:
    apply = '--apply' in sys.argv
    total = sum(fix_file(p, apply) for p in sorted(ROOT.glob('calvin/*/*.md')))
    print(f'[{"applied" if apply else "dry-run"}] {total} 个框')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
