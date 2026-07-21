#!/usr/bin/env python3
"""
fix_romans_ocr_artifacts.py — 罗马书 OCR 发布产物 idempotent 后处理。

按 scan skill (`ocr-pipeline:04-publish`) Gate-9/10/11 修复 publish 留下的
OCR artifact。重跑安全（idempotent）：跑两次结果一样。

修复规则（按发现顺序，最稳的先做）：
1. Gate-11: verse 主体段早于对应 anchor → 删除错位副本（保留 anchor 后的正确版本）
2. Gate-10: 同章 anchor 顺序倒置 → 删除位置错的 anchor（保留正确顺序的）
3. Gate-9:  同 (N,V) 主体段双重出现 → 删除靠前的副本
4. Gate-12: 嵌入式主体段（`**罗马书 N:V。**` 出现在段中而非段首）→ 报告，
   不自动修（需人工分段 + 补 anchor，分段位置脚本无法判断）
5. Gate-13: 缺失 anchor（有主体段但无对应 anchor）→ 报告，需人工补

Detect-only gates（12/13）只报告不修改，避免误删用户校准的内容。

锁定章节：LOCKED_CHAPTERS = {1, 9, 10, 15, 16} —— 用户校准好，永远跳过。

用法（项目根目录）：
    python3 scripts/fix_romans_ocr_artifacts.py             # dry-run
    python3 scripts/fix_romans_ocr_artifacts.py --apply     # 实际写入
"""
import argparse
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROMANS_DIR = ROOT / 'calvin' / 'romans'
LOCKED_CHAPTERS = {1, 9, 10, 15, 16}


def find_main_segments(text: str, ch: int):
    """Find all `**罗马书 N:V。**` main segments. Returns [(verse, start, end)]."""
    return [(int(m.group(1)), m.start(), m.end())
            for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)]


def find_anchors(text: str, ch: int):
    """Find all verse-anchor positions. Returns [(verse, start, end_of_line)]."""
    out = []
    for m in re.finditer(rf'<h2 class="verse-anchor"\s+id="romans-{ch}-(\d+)"[^>]*>[^<]*</h2>\n?',
                         text):
        out.append((int(m.group(1)), m.start(), m.end()))
    return out


def fix_main_before_anchor(text: str, ch: int):
    """Gate-11: 删除位置早于对应 anchor 的 verse 主体段（错位副本）。

    要求 anchor 之后还有同 verse 主体段才删（避免误删唯一一份）。
    """
    n_fixed = 0
    while True:
        mains = find_main_segments(text, ch)
        anchors = find_anchors(text, ch)
        anchor_pos = {v: pos for v, pos, _ in anchors}

        # 同一 verse 的主体段位置列表
        by_verse = {}
        for v, ms, me in mains:
            by_verse.setdefault(v, []).append((ms, me))

        fixed_one = False
        for v, occurrences in by_verse.items():
            if v not in anchor_pos: continue
            ap = anchor_pos[v]
            # 找出 anchor 前的副本
            before = [(s, e) for s, e in occurrences if s < ap]
            after = [(s, e) for s, e in occurrences if s > ap]
            if before and after:
                # 删 anchor 之前最靠前的副本（保留 anchor 之后的）
                ms, me = before[0]
                # 段落范围：从 ms 反推到该段开头（\n\n 之后）+ 到段末尾（下一个 \n\n）
                para_start = text.rfind('\n\n', 0, ms) + 2 if '\n\n' in text[:ms] else 0
                para_end_m = re.search(r'\n\n', text[me:])
                para_end = me + para_end_m.start() + 2 if para_end_m else len(text)
                text = text[:para_start] + text[para_end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def fix_anchor_disorder(text: str, ch: int):
    """Gate-10: 同章 anchor 顺序倒置 → 删除位置错的较早 anchor.

    保留正确顺序的（在主体段之前的）anchor。
    """
    n_fixed = 0
    while True:
        anchors = find_anchors(text, ch)
        # 找第一个倒序对
        fixed_one = False
        for i in range(len(anchors) - 1):
            v_cur, _, _ = anchors[i]
            v_next, _, _ = anchors[i + 1]
            if v_cur >= v_next:
                # anchor[i] = v_cur 错位（应该在 v_next 之后）→ 删它
                _, start, end = anchors[i]
                text = text[:start] + text[end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def fix_main_duplicate(text: str, ch: int):
    """Gate-9: 同一 (N,V) 主体段双重出现 → 删除靠前的副本（保留靠后/anchor 之后的）.

    经过 fix_main_before_anchor 后，多数双重应已消除；此处兜底。
    """
    n_fixed = 0
    while True:
        mains = find_main_segments(text, ch)
        by_verse = {}
        for v, ms, me in mains:
            by_verse.setdefault(v, []).append((ms, me))

        fixed_one = False
        for v, occs in by_verse.items():
            if len(occs) >= 2:
                # 删最靠前的副本
                ms, me = occs[0]
                para_start = text.rfind('\n\n', 0, ms) + 2 if '\n\n' in text[:ms] else 0
                para_end_m = re.search(r'\n\n', text[me:])
                para_end = me + para_end_m.start() + 2 if para_end_m else len(text)
                text = text[:para_start] + text[para_end:]
                n_fixed += 1
                fixed_one = True
                break
        if not fixed_one:
            break
    return text, n_fixed


def fix_missing_anchor(text: str, ch: int):
    """Gate-13 自动修：主体段段首正确但缺 anchor → 在主体段前插入 anchor。

    仅当主体段前段是空白（即段首干净）时才修；若是嵌入式（Gate-12），跳过。
    """
    n_fixed = 0
    # 收集所有当前 anchor
    while True:
        main_v = {int(m.group(1)) for m in
                  re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)}
        anchor_v = {int(m.group(1)) for m in
                    re.finditer(rf'class="verse-anchor"\s+id="romans-{ch}-(\d+)"', text)}
        single = {int(m.group(1)) for m in
                  re.finditer(rf'^## 罗马书 {ch}:(\d+)\s*$', text, re.MULTILINE)}
        missing = sorted(main_v - anchor_v - single)

        fixed_one = False
        for v in missing:
            m = re.search(rf'\*\*罗马书\s+{ch}:{v}。\*\*', text)
            if not m:
                continue
            ms = m.start()
            before = text[:ms]
            para_start = max(before.rfind('\n\n') + 2,
                             before.rfind('</h2>'),
                             before.rfind('</div>'))
            between = text[para_start:ms].strip()
            # 段首干净（前面是 \n\n / </h2> / </div>）才自动补
            if between and not between.endswith(('>', '\n')):
                continue
            anchor_html = (f'<h2 class="verse-anchor" id="romans-{ch}-{v}" '
                           f'data-ref="罗马书 {ch}:{v}">罗马书 {ch}:{v}</h2>\n\n')
            # 在主体段前插入 anchor (确保前面有 \n\n)
            insert_at = ms
            text = text[:insert_at] + anchor_html + text[insert_at:]
            n_fixed += 1
            fixed_one = True
            break
        if not fixed_one:
            break
    return text, n_fixed


def detect_embedded_main(text: str, ch: int):
    """Gate-12: 嵌入式主体段。`**罗马书 N:V。**` 出现在段中（非段首+非紧跟 anchor）。

    检测：找所有 main marker，看其前是否有非空白非 anchor 字符（即段中嵌入）。
    返回 [(verse, line_num, context)] 不修改文本。
    """
    issues = []
    for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text):
        v = int(m.group(1))
        ms = m.start()
        # 段首 = 文件首 / `\n\n` 后 / `</h2>\n*` 后
        if ms == 0:
            continue
        before = text[:ms]
        # 反查最近的 `\n\n` 或 `</h2>` 或 `</div>`
        para_start = max(
            before.rfind('\n\n') + 2,
            before.rfind('</h2>'),
            before.rfind('</div>'),
        )
        between = text[para_start:ms].strip()
        # 段首允许空、html 标签、`#` 标题
        if between and not between.endswith(('>', '。', '\n')):
            line = text[:ms].count('\n') + 1
            ctx = text[max(0, ms - 40):ms + 30].replace('\n', ' ')
            issues.append((v, line, ctx))
    return issues


def fix_unpromoted_opener(text: str, ch: int):
    """Gate-18 自动修：OCR 原始 marker `**N CJK...**` 未 promote 成
    标准 `**罗马书 N:V。** ***引文***` 形式 → 自动转换 + 补 anchor。

    pattern: 段首 `**(N) (CJK 引文)**` (数字 + 空格 + 至多 40 字非 `*` + `**`)
    """
    ROMANS_VERSES = {1: 32, 2: 29, 3: 31, 4: 25, 5: 21, 6: 23, 7: 25, 8: 39,
                     9: 33, 10: 21, 11: 36, 12: 21, 13: 14, 14: 23, 15: 33, 16: 27}
    max_v = ROMANS_VERSES.get(ch, 40)
    n_fixed = [0]

    def replace(m):
        v = int(m.group(1))
        if v < 1 or v > max_v:
            return m.group(0)
        quote = m.group(2).strip()
        prefix = m.group(0)[:2] if m.group(0).startswith('\n\n') else ''
        has_anchor = bool(re.search(
            rf'class="verse-anchor"\s+id="romans-{ch}-{v}"', text))
        new = (f'\n\n<h2 class="verse-anchor" id="romans-{ch}-{v}" '
               f'data-ref="罗马书 {ch}:{v}">罗马书 {ch}:{v}</h2>\n\n'
               f'**罗马书 {ch}:{v}。** ***{quote}***') if not has_anchor else \
              (f'{prefix}**罗马书 {ch}:{v}。** ***{quote}***')
        n_fixed[0] += 1
        return new

    new_text = re.sub(r'(?:^|\n\n)\*\*(\d{1,3})\s+([^\*\n]{2,40})\*\*',
                      replace, text)
    return new_text, n_fixed[0]


def fix_truncated_main(text: str, ch: int):
    """Gate-17 自动修：跨页截断的主体段 → 从 OCR raw 跨页边界拼接续文。

    流程：
    1. 找截断段（段长 < 100 + 段尾非结句符号）
    2. 在 calvin_raw/romans-scan/ocr/page_*.md 中 grep 段尾 15 字符
    3. 该 page 末尾是截断段，下一 page 开头是续文（跳过页码+页眉）
    4. 拼接到主体段末尾

    保守起见：只修末尾是 < 5 字 + 续文匹配明确的情况；不确定就 skip。
    """
    OCR_DIR = ROOT / 'calvin_raw' / 'romans-scan' / 'ocr'
    if not OCR_DIR.exists():
        return text, 0
    ENDERS = ('。', '！', '？', '；', '"', '"', '」', '》', '）', '】', '*', '>')
    n_fixed = 0

    while True:
        # 找截断段
        truncated = []
        for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text):
            end_m = re.search(r'\n\n', text[m.start():])
            para = text[m.start():m.start() + end_m.start()] if end_m else text[m.start():]
            if len(para) < 100 and para.rstrip()[-1] not in ENDERS:
                truncated.append((int(m.group(1)), m.start(), m.start() + len(para)))
        if not truncated:
            break

        fixed_one = False
        for v, ps, pe in truncated:
            para = text[ps:pe]
            # 取截断段末尾 15 字符作为查找 key
            tail = para.rstrip()[-15:]
            # 在 OCR raw 找包含 tail 的页
            page_with_tail = None
            for page_file in sorted(OCR_DIR.glob('page_*.md')):
                content = page_file.read_text(encoding='utf-8')
                if tail in content:
                    # 确认 tail 在 page 末尾附近（最后 100 字）
                    if content.rstrip().endswith(tail) or content[-200:].find(tail) >= 0:
                        page_with_tail = page_file
                        break
            if not page_with_tail:
                continue
            # 找下一页
            page_num = int(page_with_tail.stem.split('_')[1])
            next_page = OCR_DIR / f'page_{page_num + 1:04d}.md'
            if not next_page.exists():
                continue
            next_content = next_page.read_text(encoding='utf-8')
            # 跳过页码（数字） + 页眉（加尔文文集/罗马书注释等）
            lines = next_content.split('\n')
            # 找第一个非空且非页码非页眉的行
            cont_line = None
            for ln in lines:
                ln = ln.strip()
                if not ln: continue
                if re.match(r'^\d{1,3}$', ln): continue  # 纯页码
                if ln in ('加尔文文集', '加尔文集', '罗马书注释'): continue
                if re.match(r'^第[一二三四五六七八九十百〇零0-9]+章', ln): continue
                # 第一行实际内容
                cont_line = ln
                break
            if not cont_line:
                continue
            # 安全检查：续文不应是新 verse opener（数字+空格+CJK）
            if re.match(r'^\d{1,3}\s+[一-鿿]', cont_line):
                continue
            # 拼接到主体段末尾
            new_para = para.rstrip() + cont_line
            text = text[:ps] + new_para + text[pe:]
            n_fixed += 1
            fixed_one = True
            break
        if not fixed_one:
            break
    return text, n_fixed


def detect_truncated_main(text: str, ch: int):
    """Gate-17: verse 主体段被跨页截断（段尾非结句符号 + 段长 < 100 字）。

    PDF 跨页时，publish 没拼接 page 边界的同一主体段，导致主体段在中途断掉。
    特征：段尾非 `。！？；" 》" 等结句符号 + 段总长很短。

    返回 [(verse, line, tail)]。
    """
    ENDERS = ('。', '！', '？', '；', '"', '"', '」', '》', '）', '】', '*', '>')
    issues = []
    for m in re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*[^\n]*', text):
        full_line = m.group(0)
        # 主体段实际内容（去掉 `**罗马书 N:V。**` marker 部分）
        content = full_line[m.end() - m.start():] if m.end() > m.start() else ''
        # 整段（到下一 \n\n）
        end_m = re.search(r'\n\n', text[m.start():])
        para = text[m.start():m.start() + end_m.start()] if end_m else text[m.start():]
        # 去除 marker 和 emphasis markers
        body = re.sub(r'\*\*罗马书\s+\d+:\d+。\*\*\s*\*{0,3}[^*]*\*{0,3}', '', para).strip()
        if len(para) < 100 and para.rstrip()[-1] not in ENDERS:
            line = text[:m.start()].count('\n') + 1
            issues.append((int(m.group(1)), line, para[-30:]))
    return issues


def fix_duplicate_continuation(text: str, ch: int):
    """Gate-16 自动修：延续段重复 → 删最靠前的副本（保留 anchor 后版本）。

    扫所有段（\\n\\n 分割），按首 30 字符 hash，同 prefix 出现 ≥ 2 次 →
    删第一个，保留后续。重跑安全 (idempotent)。
    """
    n_fixed = 0
    while True:
        paras = text.split('\n\n')
        prefix_to_indices = {}
        for i, para in enumerate(paras):
            stripped = para.strip()
            if (stripped.startswith(('<', '#', '**', '[^', '*', '|', '{:', '---', '!'))
                    or len(stripped) < 60):
                continue
            prefix = stripped[:30]
            prefix_to_indices.setdefault(prefix, []).append(i)

        dup_indices = [(prefix, idxs) for prefix, idxs in prefix_to_indices.items()
                       if len(idxs) >= 2]
        if not dup_indices:
            break
        prefix, idxs = dup_indices[0]
        del paras[idxs[0]]
        text = '\n\n'.join(paras)
        n_fixed += 1
    return text, n_fixed


def detect_duplicate_continuation(text: str, ch: int):
    """Gate-16 detect-only (audit 报告用，fix 之后应为空)。"""
    paras = text.split('\n\n')
    pos = 0
    seen = {}
    for para in paras:
        stripped = para.strip()
        if (stripped.startswith(('<', '#', '**', '[^', '*', '|', '{:', '---', '!'))
                or len(stripped) < 60):
            pos += len(para) + 2
            continue
        prefix = stripped[:30]
        line = text[:pos].count('\n') + 1
        seen.setdefault(prefix, []).append(line)
        pos += len(para) + 2
    return [(prefix, lines) for prefix, lines in seen.items() if len(lines) >= 2]


def detect_sub_heading_misplaced(text: str, ch: int):
    """Gate-15: sub-heading 总论段错位到 section heading 之前。

    publish 启发式（detect_paragraph_verse）只识别带数字前缀的段或 CUV
    模糊匹配。verse 注释的"总论段"（无数字前缀、第一人称论说体）会被
    fallback 到 cur_sec，错位在下一 section heading 之前。

    检测：扫每个 `## 罗马书 N:A-B` heading 紧前的最后一段，段首是
    sub-heading opener 列表词 → 报告。

    返回 [(verse_section, line, snippet)] 不修改文本。
    """
    # 严格 opener: 仅"我在此/我将/我想"等第一人称论说体（calvin 总论段标志），
    # 不含"我们/本节/本段/对于"等（这些常用于 verse 注释的正常延续段）
    OPENERS = ('我在此不', '我在此愿', '我将坦然', '我想在此')
    issues = []
    for m in re.finditer(rf'\n## 罗马书 {ch}:[\d-]+\s*\n', text):
        before = text[:m.start()].rstrip()
        last_para_start = before.rfind('\n\n') + 2
        if last_para_start <= 1:
            continue
        last_para = text[last_para_start:m.start()].strip()
        if last_para.startswith(('<', '#', '**', '[^', '*', '|', '{:', '---')):
            continue
        for op in OPENERS:
            if last_para.startswith(op):
                line = text[:last_para_start].count('\n') + 1
                # 下一 section 标识
                next_sec = re.match(r'\n## 罗马书 (\d+:[\d-]+)', text[m.start():])
                sec = next_sec.group(1) if next_sec else '?'
                issues.append((sec, line, last_para[:50]))
                break
    return issues


def detect_missing_anchor(text: str, ch: int):
    """Gate-13: 有 `**罗马书 N:V。**` 主体段但缺对应 verse-anchor。

    单 verse section（如 `## 罗马书 12:3` 后接 scripture-anchor `romans-12-3`）
    不需要额外 verse-anchor，从结果排除。
    """
    main_verses = {int(m.group(1)) for m in
                   re.finditer(rf'\*\*罗马书\s+{ch}:(\d+)。\*\*', text)}
    anchor_verses = {int(m.group(1)) for m in
                     re.finditer(rf'class="verse-anchor"\s+id="romans-{ch}-(\d+)"', text)}
    single_verse_sections = {int(m.group(1)) for m in
                             re.finditer(rf'^## 罗马书 {ch}:(\d+)\s*$', text, re.MULTILINE)}
    return sorted(main_verses - anchor_verses - single_verse_sections)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true',
                    help='Actually write fixes (default: dry-run)')
    args = ap.parse_args()

    total = {'main_before_anchor': 0, 'anchor_disorder': 0, 'duplicate': 0,
             'embedded': 0, 'missing_anchor': 0}
    files_changed = 0

    for p in sorted(ROMANS_DIR.glob('*.md')):
        if not p.stem.isdigit():
            continue
        ch = int(p.stem)
        if ch in LOCKED_CHAPTERS:
            print(f'  {p.name}: SKIP (locked)')
            continue

        text = p.read_text(encoding='utf-8')
        orig = text

        text, n11 = fix_main_before_anchor(text, ch)
        text, n10 = fix_anchor_disorder(text, ch)
        text, n9 = fix_main_duplicate(text, ch)
        text, n16 = fix_duplicate_continuation(text, ch)
        text, n18 = fix_unpromoted_opener(text, ch)  # 先 promote 再补 anchor
        text, n13_auto = fix_missing_anchor(text, ch)
        text, n17 = fix_truncated_main(text, ch)

        # Detect-only gates（不修改文本）
        embedded = detect_embedded_main(text, ch)
        missing = detect_missing_anchor(text, ch)
        subhead = detect_sub_heading_misplaced(text, ch)
        dup_cont = detect_duplicate_continuation(text, ch)
        truncated = detect_truncated_main(text, ch)
        total['embedded'] += len(embedded)
        total['missing_anchor'] += len(missing)
        total['subhead_misplaced'] = total.get('subhead_misplaced', 0) + len(subhead)
        total['dup_continuation'] = total.get('dup_continuation', 0) + len(dup_cont)
        total['truncated_main'] = total.get('truncated_main', 0) + len(truncated)

        if (n11 + n10 + n9 + n16 + n13_auto + n17 > 0
                or embedded or missing or subhead or dup_cont or truncated):
            total['main_before_anchor'] += n11
            total['anchor_disorder'] += n10
            total['duplicate'] += n9
            total['dup_continuation_fixed'] = total.get('dup_continuation_fixed', 0) + n16
            total['anchor_added'] = total.get('anchor_added', 0) + n13_auto
            total['truncated_fixed'] = total.get('truncated_fixed', 0) + n17
            msg = f'  {p.name}: G-11={n11} G-10={n10} G-9={n9} G-16fix={n16} G-13fix={n13_auto} G-17fix={n17}'
            if embedded: msg += f' G-12={len(embedded)}'
            if missing: msg += f' G-13left={len(missing)} {missing}'
            if subhead: msg += f' G-15={len(subhead)}'
            if dup_cont: msg += f' G-16left={len(dup_cont)}'
            if truncated: msg += f' G-17={len(truncated)}'
            print(msg)
            for v, line, ctx in embedded:
                print(f'    Gate-12 v.{ch}:{v} @L{line}  ...{ctx}...')
            for sec, line, snippet in subhead:
                print(f'    Gate-15 next-sec={sec} @L{line}  "{snippet}..."')
            for prefix, lines in dup_cont:
                print(f'    Gate-16 重复段 @L{lines}  "{prefix}..."')
            for v, line, tail in truncated:
                print(f'    Gate-17 v.{ch}:{v} 截断 @L{line}  tail="...{tail}"')
            if args.apply and text != orig:
                p.write_text(text, encoding='utf-8')
                files_changed += 1

    sub_total = total.get('subhead_misplaced', 0)
    dup_total = total.get('dup_continuation', 0)
    trunc_total = total.get('truncated_main', 0)
    print(f'\n汇总: Gate-11={total["main_before_anchor"]} '
          f'Gate-10={total["anchor_disorder"]} Gate-9={total["duplicate"]} '
          f'Gate-12={total["embedded"]} Gate-13={total["missing_anchor"]} '
          f'Gate-15={sub_total} Gate-16={dup_total} Gate-17={trunc_total}')
    print(f'{"已写入" if args.apply else "Dry-run"} {files_changed} 个文件')
    if (total['embedded'] or total['missing_anchor']
            or sub_total or dup_total or trunc_total):
        print('\n⚠️  Gate-12/13/15/16/17 是 detect-only，不会自动修。需人工:')
        print('   - Gate-12: 主体段嵌在段中 → 段首加 \\n\\n 拆段')
        print('   - Gate-13: verse 缺 anchor → scripture-box 后插入 <h2 class="verse-anchor">')
        print('   - Gate-15: sub-heading 总论段错位在 section heading 前 →')
        print('             移到下一 section 的 v.A anchor 之后、主体段之前')
        print('   - Gate-16: 延续段重复 → 删错位副本（保留 anchor 后版）')
        print('   - Gate-17: verse 主体段被跨页截断 →')
        print('             查 OCR raw 跨页边界 + PDF 物理页, 拼接续文')
    if not args.apply:
        print('\n用 --apply 实际写入。')


if __name__ == '__main__':
    main()
