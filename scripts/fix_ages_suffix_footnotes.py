#!/usr/bin/env python3
"""修 AGES 字母后缀脚注（FtNNNA）——引用被希腊转写吃坏、定义被上一条吞掉。

AGES 版把同一编号的第二条脚注写成 `Ft305A`。旧流水线两头都栽了：

  引用侧：`format_inline` 先把正文里的 `f305A` 转成 `[^f305A]`，随后
          `convert_ages_greek` 看见 `A]` —— 这正是 AGES 编码里「带重音的
          大写 Alpha」—— 转成了 `Ά`。页面上留下一串红色字面量 `[^f305Ά`，
          全库 218 处（1cor 第 7-9 章最密）。
  定义侧：`FN_DEF_RE` 与文末脚注区的规则都只认 `FtNNN`，`Ft305A` 那一行
          认不出是新定义，被当成上一条的续行整条吞掉——1cor 有 53 条挤进了
          `[^f404]` 里，正文引用全成孤儿。

生成器（structured_to_md.py）三处已修：定义正则认尾字母、引用尾字母转小写
（定义那边会 lower()）、希腊转写前把 `[^…]` 藏起来。本脚本修既有产物：

  1. 把被吞的定义从宿主定义里拆出来，各自成条 `[^f305a]: …`；
  2. 正文引用 `[^f305Ά` → `[^f305a]`（Ά→a、Β→b）；
  3. 英文版若还有引用没定义，从 structured 原文里取（中文那边取不到——
     这些条目当初就没进英文章节文件，也就从没被翻译过），转成与页面其余
     脚注一致的形态后补上；
  4. 中文版实在无定义的引用退回红色死标记 `<span …>f358a</span>`，与全库
     其它「有标记无定义」的脚注一个样子，不留 `[^f358a]` 这种渲染不出来的
     字面量。这些条目待补译，脚本会把清单打出来。

用法：
    python3 scripts/fix_ages_suffix_footnotes.py [--apply]
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    'structured_to_md', ROOT / 'scripts/structured_to_md.py')
_s2md = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_s2md)

# 页面上冒充 `]` 的希腊字母 → 原来的后缀字母
GREEK_SUFFIX = {'Ά': 'a', 'Β': 'b'}
BAD_REF = re.compile(r'\[\^([A-Za-z]{0,3}\d+)([' + ''.join(GREEK_SUFFIX) + r'])')
SWALLOWED = re.compile(r'\s*<span style="color:#800000">\s*([Ff][Tt]?\d+[A-Za-z])\s*</span>\s*')
DEF_LINE = re.compile(r'^\[\^([A-Za-z]{0,3}\d+[A-Za-z]?)\]:')

# 已发布目录名 → calvin_raw 下的 structured 目录名（对不上的按同名找）
RAW_DIR = {'1corinthians': '1cor', '2corinthians': '2cor'}


def norm(code: str) -> str:
    return re.sub(r'^ft', 'f', code.lower())


def structured_defs(book: str) -> dict:
    """从 structured 原文里取字母后缀脚注的定义正文（英文用）。"""
    raw = RAW_DIR.get(book, book)
    path = ROOT / f'calvin_raw/{raw}/calvin_{raw}_structured.txt'
    if not path.exists():
        return {}
    out = {}
    pat = re.compile(r'^\[(?:BODY|FOOTNOTE)\]\s*(?:<sty\s[^>]*>)?\s*'
                     r'([Ff][Tt]?\d+[A-Za-z])\s*(?:</sty>)?\s*(.+)$')
    for line in path.read_text(encoding='utf-8').split('\n'):
        m = pat.match(line)
        if m:
            body = _s2md.apply_verse_styling(_s2md.format_inline(m.group(2)), red=False)
            body = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', body).strip()
            out[norm(m.group(1))] = body
    return out


def split_swallowed(lines):
    """把宿主定义里夹带的 `<span>FtNNNA</span> 正文…` 拆成独立定义条目。"""
    out, found = [], {}
    for line in lines:
        if not DEF_LINE.match(line) or not SWALLOWED.search(line):
            out.append(line)
            continue
        parts = SWALLOWED.split(line)
        out.append(parts[0].rstrip())          # 宿主定义自己的正文
        for code, body in zip(parts[1::2], parts[2::2]):
            key = norm(code)
            body = body.strip()
            found[key] = body
            out.append('')
            out.append(f'[^{key}]: {body}')
    return out, found


NEEDS_MD = re.compile(
    r'<(?:span|p)\b(?![^>]*markdown=)[^>]*>(?:(?!</(?:span|p)>).)*'
    r'\[\^[A-Za-z]{0,3}\d+[A-Za-z]\]', re.S)


def needs_fix(text: str) -> bool:
    return bool(BAD_REF.search(text) or SWALLOWED.search(text) or NEEDS_MD.search(text))


def fix_file(path: Path, en_defs: dict, apply: bool):
    original = path.read_text(encoding='utf-8')
    text = original
    if not needs_fix(text):
        return 0, []
    lines = text.split('\n')
    lines, recovered = split_swallowed(lines)
    text = '\n'.join(lines)
    # 引用还原
    text = BAD_REF.sub(lambda m: f'[^{norm(m.group(1))}{GREEK_SUFFIX[m.group(2)]}]', text)
    have = {norm(c) for c in DEF_LINE.findall(text)} | {
        norm(m.group(1)) for m in re.finditer(r'^\[\^([A-Za-z]{0,3}\d+[A-Za-z]?)\]:', text, re.M)}
    refs = [norm(c) for c in re.findall(r'\[\^([A-Za-z]{0,3}\d+[A-Za-z]?)\](?!:)', text)]
    missing = [c for c in dict.fromkeys(refs) if c not in have and re.search(r'[A-Za-z]$', c)]
    added, orphan = [], []
    for code in missing:
        if en_defs.get(code):
            text = text.rstrip('\n') + f'\n\n[^{code}]: {en_defs[code]}\n'
            added.append(code)
        else:
            orphan.append(code)
    # 中文侧无定义的引用 → 退回红色死标记（页面上是个小小的红字，不是字面量）
    for code in orphan:
        text = re.sub(r'\[\^' + re.escape(code) + r'\](?!:)',
                      f'<span style="color:#800000">{code}</span>', text)

    # 中译把引用裹在红色 <span> 里，span 不带 markdown="span" 的话 kramdown
    # 整块跳过，页面上露出字面的 [^f305a]（见 reference_kramdown_markdown_attr）
    def _md_span(m):
        tag, inner = m.group(1), m.group(2)
        if 'markdown=' in tag or '[^' not in inner:
            return m.group(0)
        return tag[:-1] + ' markdown="span">' + inner + '</span>'
    text = re.sub(r'(<span\b[^>]*>)((?:(?!</span>).)*)</span>', _md_span, text, flags=re.S)

    def _md_p(m):
        tag, inner = m.group(1), m.group(2)
        if 'markdown=' in tag or '[^' not in inner:
            return m.group(0)
        return tag[:-1] + ' markdown="1">' + inner + '</p>'
    text = re.sub(r'(<p\b[^>]*>)((?:(?!</p>).)*)</p>', _md_p, text, flags=re.S)
    n = len(recovered) + len(added)
    if text != original:
        print(f'  {path}: 拆出 {len(recovered)} 条、补 {len(added)} 条'
              + (f'、无定义退回死标记 {len(orphan)} 条' if orphan else ''))
    if text == original:          # 只是命中了正文里的死标记，没什么可改
        return 0, orphan
    if apply:
        mode = path.stat().st_mode & 0o777
        if not mode & 0o200:        # zh_chapters 平时是只读的
            path.chmod(0o644)
            path.write_text(text, encoding='utf-8')
            path.chmod(mode)
        else:
            path.write_text(text, encoding='utf-8')
    return n, orphan


def main() -> int:
    apply = '--apply' in sys.argv
    targets = sorted(list(ROOT.glob('calvin/*/*.md'))
                     + list(ROOT.glob('calvin_raw/*/zh_chapters/*.md')))
    cache = {}
    total, all_orphan = 0, {}
    for p in targets:
        if not needs_fix(p.read_text(encoding='utf-8')):
            continue
        is_en = p.parent.name.endswith('-en')
        book = p.parent.name[:-3] if is_en else p.parent.name
        if is_en:
            if book not in cache:
                cache[book] = structured_defs(book)
            defs = cache[book]
        else:
            defs = {}          # 中文定义只能来自译文，structured 是英文的
        n, orphan = fix_file(p, defs, apply)
        total += n
        if orphan:
            all_orphan[str(p.relative_to(ROOT))] = orphan
    print(f'[{"applied" if apply else "dry-run"}] 共处理 {total} 条定义')
    if all_orphan:
        print('待补译（中文无定义，已退回死标记）:')
        for k, v in all_orphan.items():
            print(f'  {k}: {len(v)} 条 {v[:6]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
