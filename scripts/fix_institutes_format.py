#!/usr/bin/env python3
"""
修复 reading/calvin/institutes/ 下所有章节的格式。
每次新增章节后运行，确保格式统一：

- 分组标签：去掉错误外层括号  （text，n–m） → text（n—m）
- 分组标签与节标题混合行 → 拆分为两行
- 第三卷：章标题加 ##，节标题加 ###，脚注提取到末尾

用法：
    python3 scripts/fix_institutes_format.py
"""
import re, sys
from pathlib import Path

SITE_DIR  = Path(__file__).parent.parent
INST_DIR  = SITE_DIR / "reading/calvin/institutes"

CIRCLED     = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚"
CIRCLED_SET = set(CIRCLED)

# ── 分组标签修复 ──────────────────────────────────────────────────────────────

# 情况1: （text，n–m） N. title → text（n—m）\n\n### N. title（混合行）
PAT_MIXED = re.compile(r'^（(.+)[，,](\d+[–—\-]+\d+)）\s+(\d+[\.．].+)$')
# 情况2: （text，n–m）单独成行 → text（n—m）
PAT_SOLO  = re.compile(r'^（(.+)[，,](\d+[–—\-]+\d+)）$')

def fix_group_label_line(line: str) -> list[str]:
    s = line.strip()
    m = PAT_MIXED.match(s)
    if m:
        return [f'{m.group(1)}（{m.group(2)}）', '', f'### {m.group(3).strip()}']
    m = PAT_SOLO.match(s)
    if m:
        return [f'{m.group(1)}（{m.group(2)}）']
    return [line]

def needs_group_fix(line: str) -> bool:
    s = line.strip()
    return s.startswith('（') and bool(re.search(r'[，,]\d+[–—\-]\d+）', s))

def fix_group_labels(text: str) -> str:
    out = []
    for line in text.split('\n'):
        if needs_group_fix(line.strip()):
            out.extend(fix_group_label_line(line))
        else:
            out.append(line)
    return '\n'.join(out)

# ── 第三卷专项修复 ────────────────────────────────────────────────────────────

def process_vol3(text: str) -> str:
    """章标题加 ##，节标题加 ###，内嵌脚注移至末尾"""
    lines = text.split('\n')

    # 分离 front matter
    if lines[0].strip() == '---':
        end = lines.index('---', 1)
        fm         = lines[:end+1]
        body_lines = lines[end+1:]
    else:
        fm         = []
        body_lines = lines

    main: list[str] = []
    fns:  dict[str, list[str]] = {}
    current_fn: str | None = None

    def flush_fn():
        nonlocal current_fn
        if current_fn:
            t = ' '.join(fns.get(current_fn, [])).strip()
            if t:
                fns[current_fn] = [t]
        current_fn = None

    for line in body_lines:
        stripped = line.strip()

        # 章标题
        if re.match(r'^第[一二三四五六七八九十百]+章[\s\u3000]', stripped) and not stripped.startswith('##'):
            flush_fn()
            main.append(f'## {stripped}')
            continue

        # 分组标签（先于节标题检测）
        if needs_group_fix(stripped):
            flush_fn()
            main.extend(fix_group_label_line(stripped))
            continue

        # 节标题
        if re.match(r'^\d+[\.．]\s+\S', stripped) and not stripped.startswith('###'):
            flush_fn()
            main.append(f'### {stripped}')
            continue

        # 脚注段落
        if stripped and stripped[0] in CIRCLED_SET:
            flush_fn()
            current_fn = stripped[0]
            rest = stripped[1:].strip()
            fns[current_fn] = [rest] if rest else []
            continue

        # 脚注续行
        if current_fn is not None:
            if not stripped:
                flush_fn()
                main.append('')
            else:
                cn = sum(1 for c in stripped if '\u4e00' <= c <= '\u9fff') / max(len(stripped), 1)
                if cn > 0.6 and len(stripped) > 30 and stripped[0] not in CIRCLED_SET:
                    flush_fn()
                    main.append(line)
                else:
                    fns.setdefault(current_fn, []).append(stripped)
            continue

        flush_fn()
        main.append(line)

    flush_fn()

    # 组装脚注 HTML
    fn_html = []
    for m in CIRCLED:
        if m in fns:
            t = ' '.join(fns[m]).strip()
            if t:
                fn_html.append(f'<div class="inst-fn">{m} {t}</div>')

    body = '\n'.join(main).rstrip()
    if fn_html:
        body += '\n\n' + '\n'.join(fn_html)

    return '\n'.join(fm) + ('\n' if fm else '') + body + '\n'


# ── 主处理 ────────────────────────────────────────────────────────────────────

def main():
    changed = []
    all_md  = sorted(list(INST_DIR.glob('*.md')) +
                     list(INST_DIR.glob('*/index.md')))

    for path in all_md:
        original = path.read_text(encoding='utf-8')
        name = path.stem if path.stem != 'index' else path.parent.name
        m    = re.match(r'^(\d+)-', name)
        vol  = int(m.group(1)) if m else 0

        if vol == 3:
            fixed = process_vol3(original)
            fixed = fix_group_labels(fixed)   # 再跑一遍分组标签修复
        elif vol in (1, 2, 4):
            fixed = fix_group_labels(original)
        else:
            continue

        if fixed != original:
            path.write_text(fixed, encoding='utf-8')
            changed.append(str(path.relative_to(INST_DIR)))

    if changed:
        print(f'修复 {len(changed)} 个文件：')
        for f in changed:
            print(f'  {f}')
    else:
        print('所有文件格式已符合规范，无需修复。')


if __name__ == '__main__':
    main()
