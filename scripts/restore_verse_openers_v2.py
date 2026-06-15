#!/usr/bin/env python3
"""V2 安全恢复 — 修复 publish 把 verse-opener 跨页删掉、孤儿 continuation
留在 published 的损坏。严格按 .claude/commands/ocr-pipeline/04-publish.md
Step 1-7 + 三层保险 实现。

默认 dry-run 输出报告；加 --apply 才真改文件。

用法:
  python3 scripts/restore_verse_openers_v2.py              # dry-run
  python3 scripts/restore_verse_openers_v2.py --apply      # 应用
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
OCR_RAW = ROOT / 'calvin_raw' / 'romans-scan' / 'calvin_romans_zh.md'
BOOK_DIR = ROOT / 'calvin' / 'romans'
BOOK_NAME = '罗马书'

# Step 1c: 常见词头白名单 — 段首 2 字符若在此白名单内，不算"孤儿单字头"
COMMON_HEAD_CHARS = {
    '你', '我', '他', '她', '它', '们', '上', '保', '基', '虽', '然', '因', '所',
    '那', '这', '第', '其', '若', '当', '从', '为', '按', '与', '在', '就', '要',
    '如', '虽', '本', '又', '只', '但', '可', '不', '已', '将', '以', '是', '有',
    '没', '会', '能', '让', '使', '凡', '一', '二', '三', '现', '今', '于', '却',
    '何', '由', '比', '至', '便', '即', '若', '何', '虽', '即', '故', '兹', '此',
    '我们', '他们', '她们', '我自', '我的', '你的', '你们', '基督', '上帝', '保罗',
    '虽然', '然而', '因为', '所以', '虽是', '因此', '当然', '当我', '当他', '当那',
}

# 段首 2 字符若构成常见词，跳过（不视为孤儿）
def is_common_head(s: str) -> bool:
    """段首 2 字符判定是否常见词头。"""
    if len(s) < 2:
        return True
    return s[0] in COMMON_HEAD_CHARS or s[:2] in COMMON_HEAD_CHARS

# 结句符
SENT_END = '.。！？；;:!?"”\')）'

def is_sent_end(s: str) -> bool:
    s = s.rstrip()
    if not s:
        return True
    return s[-1] in SENT_END

# Step 1b: 段内含 HTML 块就跳过
HTML_BLOCK_PAT = re.compile(
    r'<(?:div\s+class="scripture-box|p\s+class="scripture-ref|table|thead|tbody|h2)'
)

def is_html_block(p: str) -> bool:
    return bool(HTML_BLOCK_PAT.search(p))

# Step 3: verse-opener 格式
OPENER_RE = re.compile(r'^(\d{1,2})\s+([一-鿿].{0,500})$', re.M)
COMMENTARY_KWS = ('保罗', '我们', '在此', '这里', '本节', '基督', '上帝')

def is_verse_opener(text: str) -> tuple[bool, int, str, str]:
    """判定一段是否 verse-opener 格式。返回 (ok, verse_num, verse_phrase, commentary)。"""
    m = re.match(r'^(\d{1,2})\s+([一-鿿].*)$', text.strip(), re.S)
    if not m:
        return False, 0, '', ''
    n = int(m.group(1))
    if n < 1 or n > 36:
        return False, 0, '', ''
    body = m.group(2)
    # 段末非结句符
    if is_sent_end(body):
        return False, 0, '', ''
    # 段长 30-500
    if not (30 <= len(body) <= 500):
        return False, 0, '', ''
    # 含 commentary 关键词或 ……
    if not ('……' in body or '…' in body or any(kw in body for kw in COMMENTARY_KWS)):
        return False, 0, '', ''
    # 拆 verse phrase / commentary
    if '……' in body:
        vp, comm = body.split('……', 1)
    elif '…' in body:
        vp, comm = body.split('…', 1)
    else:
        # 没省略号但有 commentary 关键词 — 取关键词前作为 phrase
        for kw in COMMENTARY_KWS:
            idx = body.find(kw)
            if idx > 5:
                vp, comm = body[:idx], body[idx:]
                break
        else:
            vp, comm = '', body
    return True, n, vp.strip(), comm.strip()

# Step 2: OCR raw 解析跨页对
def find_crosspage_pairs(raw: str) -> list[tuple[str, str, int]]:
    """返回 [(prev_para, next_para, raw_position), ...] 跨页前后段对。"""
    pairs = []
    PAGE_RE = re.compile(r'<!-- PAGE \d+ -->')
    for m in PAGE_RE.finditer(raw):
        # 取注释前段
        before = raw[:m.start()].rstrip()
        if not before: continue
        # 段边界 = 最后一个 \n\n
        i = before.rfind('\n\n')
        prev_para = before[i+2:] if i >= 0 else before
        # 取注释后段
        after = raw[m.end():].lstrip()
        # 跳过可能的连续 PAGE 注释
        while after.startswith('<!--'):
            j = after.find('-->')
            if j < 0: break
            after = after[j+3:].lstrip()
        # 段边界 = 第一个 \n\n
        j = after.find('\n\n')
        next_para = after[:j] if j >= 0 else after
        if prev_para and next_para:
            pairs.append((prev_para.strip(), next_para.strip(), m.start()))
    return pairs


def split_into_paragraphs(text: str) -> list[tuple[int, str]]:
    """段落分割，返回 [(起始行号, 段内容), ...]。"""
    out = []
    lines = text.split('\n')
    cur_lines = []
    cur_start = 0
    for i, line in enumerate(lines):
        if line == '':
            if cur_lines:
                out.append((cur_start, '\n'.join(cur_lines)))
                cur_lines = []
            continue
        if not cur_lines:
            cur_start = i + 1  # 1-indexed
        cur_lines.append(line)
    if cur_lines:
        out.append((cur_start, '\n'.join(cur_lines)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='真改文件; 默认只 dry-run')
    ap.add_argument('--max-per-file', type=int, default=50, help='单文件最多插入数 (Step 7-3)')
    args = ap.parse_args()

    raw = OCR_RAW.read_text()

    # Step 2: 跨页对
    pairs = find_crosspage_pairs(raw)
    print(f'OCR raw 跨页对总数: {len(pairs)}')

    # 候选: 跨页前段是 verse-opener 的
    opener_pairs = []
    for prev, nxt, pos in pairs:
        ok, n, vp, comm = is_verse_opener(prev)
        if ok:
            opener_pairs.append((prev, nxt, n, vp, comm, pos))
    print(f'其中跨页前段是 verse-opener 的: {len(opener_pairs)}')

    # 读 published 文件
    files = {}
    for ch in range(1, 17):
        p = BOOK_DIR / f'{ch}.md'
        if p.exists():
            files[ch] = p.read_text()

    # 索引: 跨页后段前 12 字符 → 在哪个文件出现
    # 全局唯一性检查
    all_text = '\n\n===CHAPTER-SEP===\n\n'.join(
        [f'CH{ch}:{txt}' for ch, txt in files.items()])

    # Step 1 + Step 4: 对每个 opener-pair 找候选孤儿段
    plan = []  # 计划修改的列表
    skipped = []  # (原因, 信息)

    for prev, nxt, n, vp, comm, pos in opener_pairs:
        if len(nxt) < 12:
            skipped.append(('next-too-short', f'N={n} {prev[:30]}'))
            continue
        fp12 = nxt[:12]
        # Step 4-1: 双向唯一性 — fp12 在所有 published 文件中只出现 1 次
        count_total = all_text.count(fp12)
        if count_total != 1:
            skipped.append(('not-unique', f'N={n} fp={fp12!r} count={count_total}'))
            continue

        # 找在哪个文件、哪一段
        found_ch = None
        found_para_idx = -1
        for ch, txt in files.items():
            idx = txt.find(fp12)
            if idx < 0: continue
            found_ch = ch
            # 找段边界
            ps = txt.rfind('\n\n', 0, idx)
            if ps < 0: ps = 0
            else: ps += 2
            pe = txt.find('\n\n', idx)
            if pe < 0: pe = len(txt)
            para = txt[ps:pe]
            # Step 1b: HTML 块跳过
            if is_html_block(para):
                skipped.append(('inside-html', f'N={n} {fp12!r}'))
                found_ch = None
                break
            # Step 4-2: 往前 200 字符不含 </div>
            ctx_before = txt[max(0, ps-200):ps]
            if '</div>' in ctx_before:
                skipped.append(('near-divend', f'N={n} {fp12!r}'))
                found_ch = None
                break
            # 已有 **罗马书 N:V。** 节标的段跳过 (不需要补)
            if re.match(r'^\*\*罗马书 \d{1,2}:\d{1,2}。\*\*', para):
                skipped.append(('already-has-marker', f'N={n} {para[:30]}'))
                found_ch = None
                break
            # Case B 跳过: published 段开头若就是 OCR prev 段开头 (verse-opener
            # 没被删，只是没 promote 加粗) → 不要重复补
            ocr_prev_head = prev.split('\n', 1)[0].strip()[:10]
            if para[:10] == ocr_prev_head:
                skipped.append(('case-b-unpromoted', f'N={n} {para[:30]}'))
                found_ch = None
                break
            # 章节 sanity (Step 4 加强): OCR prev 或当前 published 段
            # 提到其他书卷的关键词 → 章节归位错误，不补
            other_book_kws = [
                '以弗所', '弗所', '腓立比', '歌罗西', '加拉太', '帖撒罗尼迦',
                '提摩太', '约翰一', '约翰二', '约翰三', '彼得前', '彼得后',
            ]
            combined_text = prev + para[:200]
            hits = [kw for kw in other_book_kws if kw in combined_text]
            if hits:
                skipped.append(('chapter-mismatch', f'N={n} mentions {hits}'))
                found_ch = None
                break
            # OCR prev 末尾若是"（<书卷简写>"形式 (跨页打断的圣经引用，
            # 不是 verse-opener)，如"(西" "(弗" "(腓" "(林前" "(林后" "(帖前"
            prev_tail = prev.rstrip()[-3:]
            if re.search(r'[（(](?:西|弗|腓|林前|林后|帖前|帖后|提前|提后|多|门|来|约一|约二|约三|彼前|彼后|犹|启)$',
                         prev_tail + prev.rstrip()[-6:]):
                skipped.append(('mid-citation', f'N={n} prev ends with ref'))
                found_ch = None
                break
            # orphan 段开头若是 "数字:数字)" 形式 (圣经引用闭合括号)
            if re.match(r'^\d{1,3}:\d{1,3}[)）]', para):
                skipped.append(('mid-citation-2', f'N={n} para starts as ref-close'))
                found_ch = None
                break
            # Step 1c: 段首词头白名单跳过 (不算孤儿)
            head2 = para[:2]
            if is_common_head(head2):
                skipped.append(('common-head', f'N={n} head={head2!r}'))
                found_ch = None
                break
            # Step 1d (修正): 上一段末尾**必须**是结句符 — 这才说明中间
            # 有 verse-opener 被删除。如果前段非结句符，那是 publish 把
            # 跨页合并了或前段也被截断，不是我们的目标。
            if ps > 2:
                prev_para_text = txt[:ps-2]
                pps = prev_para_text.rfind('\n\n')
                prev_para_text = prev_para_text[pps+2:] if pps >= 0 else prev_para_text
                # 跳过 markdown 标题、HTML 块、scripture 引用等"伪段"
                pt_stripped = prev_para_text.strip()
                if (pt_stripped.startswith('#') or pt_stripped.startswith('<') or
                    pt_stripped.startswith('**罗马书')):
                    pass  # 这些前段算"边界"，candidate 段大概率是 verse-opener 被删后的孤儿
                elif not is_sent_end(prev_para_text):
                    skipped.append(('prev-not-sent-end', f'N={n} {fp12!r}'))
                    found_ch = None
                    break
            # Step 5: 构造新段
            marker = f'**{BOOK_NAME} {ch}:{n}。**'
            new_opener = f'{marker} '
            if vp:
                new_opener += f'***{vp}*** '
            new_opener += comm
            # 拼孤儿段 (前段被截词 + 孤儿单字 自然合并)
            new_full = new_opener + para
            plan.append({
                'ch': ch, 'n': n,
                'file': str(BOOK_DIR / f'{ch}.md'),
                'para_start': ps,
                'para_end': pe,
                'old_para_head': para[:60],
                'ocr_prev': prev[:80],
                'new_para_head': new_full[:120],
                'new_full': new_full,
            })
            found_para_idx = ps
            break

    print(f'\n通过所有 strict 检查的候选: {len(plan)}')
    print(f'跳过总数: {len(skipped)}')

    # 跳过原因汇总
    from collections import Counter
    reasons = Counter(s[0] for s in skipped)
    print('跳过原因:')
    for r, c in reasons.most_common():
        print(f'  {r}: {c}')

    # 单文件 < max-per-file 检查 (Step 7-3)
    by_file = Counter(p['ch'] for p in plan)
    over = [(ch, c) for ch, c in by_file.items() if c > args.max_per_file]
    if over:
        print(f'\n!! 单文件超阈值 {args.max_per_file}，abort:')
        for ch, c in over:
            print(f'  romans/{ch}.md: {c} 处')
        sys.exit(1)

    # Dry-run 报告
    print(f'\n=== Dry-run 报告 (前 {min(20, len(plan))} 处) ===')
    for i, p in enumerate(plan[:20]):
        print(f'\n[{i+1}] romans/{p["ch"]}.md  para@offset={p["para_start"]}')
        print(f'  OCR 前段: {p["ocr_prev"]}')
        print(f'  原孤儿段: {p["old_para_head"]}')
        print(f'  新段头部: {p["new_para_head"]}')

    if len(plan) > 20:
        print(f'\n... 还有 {len(plan) - 20} 处')

    print(f'\n按文件分布:')
    for ch, c in sorted(by_file.items()):
        print(f'  romans/{ch}.md: {c} 处')

    if not args.apply:
        print('\n=== Dry-run 完毕。--apply 才会真改 ===')
        return

    # Step 7-1: git stash
    print('\n=== Apply 模式 ===')
    print('1. git stash 当前未提交改动...')
    r = subprocess.run(['git', 'stash', 'push', '-m', 'restore_verse_openers_v2 backup'],
                       capture_output=True, text=True, cwd=ROOT)
    stashed = 'No local changes' not in r.stdout
    print(f'   stashed: {stashed}')

    # 应用 — 按 file + para_start 倒序
    by_file_items = {}
    for p in plan:
        by_file_items.setdefault(p['ch'], []).append(p)
    n_applied = 0
    for ch, items in by_file_items.items():
        items.sort(key=lambda x: -x['para_start'])
        txt = files[ch]
        for item in items:
            ps, pe = item['para_start'], item['para_end']
            txt = txt[:ps] + item['new_full'] + txt[pe:]
            n_applied += 1
        (BOOK_DIR / f'{ch}.md').write_text(txt)
        print(f'  romans/{ch}.md: {len(items)} 处已应用')

    print(f'\n2. 共应用 {n_applied} 处')

    # Step 7-2: jekyll build
    print('3. jekyll build 验证...')
    r = subprocess.run(['bundle', 'exec', 'jekyll', 'build'],
                       capture_output=True, text=True, cwd=ROOT, timeout=180)
    has_error = '[31m' in r.stdout or 'Error' in r.stderr.split('\n')[0]
    if has_error:
        print('   !! build error — 回滚')
        subprocess.run(['git', 'checkout', '--', 'calvin/romans/'], cwd=ROOT)
        if stashed:
            subprocess.run(['git', 'stash', 'pop'], cwd=ROOT)
        sys.exit(1)
    print('   build OK')

    if stashed:
        print('4. 恢复之前 stash 的改动...')
        r = subprocess.run(['git', 'stash', 'pop'], capture_output=True, text=True, cwd=ROOT)
        print(f'   stash pop: {r.returncode == 0}')

    print('\n=== 完成。请人工抽样审核后再 commit ===')


if __name__ == '__main__':
    main()
