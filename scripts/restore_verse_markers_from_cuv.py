#!/usr/bin/env python3
"""通过 CUV 短语 fuzzy match 恢复 OCR/publish 丢失的 verse-marker 前缀。

症状：OCR 偶尔产出 `**phrase。** 注释...` 段落但缺 `**书名 N:V。**` 前缀。
渲染在网页上就没有 verse 索引锚点，且 relocate 找不到该段属于哪个 verse，
留在错的 section 里，从胶囊跳不进去。

算法：每个 `**phrase。**` 开头段落，把 phrase 去标点 / 英文括号注 / 省略号
后在该章节 CUV 各 verse 文本里子串匹配，最早匹配的 verse 即为 verse-num。
匹配失败则保留原样（属 Calvin 自创小标题，不该加 marker）。

跑完后必须 sweep `relocate_misplaced_verse_commentary.py +
sort_intra_section_verses.py + dedupe_same_verse_markers.py`，因为恢复的
marker 极可能跨当前 section / 跟同 verse 段重复。

用法：
    python3 scripts/restore_verse_markers_from_cuv.py --book-cn 约翰福音 \
            --cuv-abbrev jo --dir calvin/john
"""
import argparse, json, re
from pathlib import Path
try:
    from opencc import OpenCC
    convert = OpenCC('t2s').convert
except Exception:
    convert = lambda s: s


def _normalize(s):
    # 先做繁→简转换（部分段落 OCR / Claude 翻译产物残留繁体）
    s = convert(s)
    s = re.sub(r'[ 。，！？、；：":“”‘’（）\(\)（）!？]', '', s)
    s = re.sub(r'[a-zA-Z\d]+', '', s)
    # Calvin 译本 vs CUV 字符 / 词汇差异，归一化以便 substring 匹配
    s = s.replace('上帝', '神')
    s = s.replace('著', '着')   # OpenCC t2s 偶尔留 著 (CUV 寫著)
    s = s.replace('她', '他')   # Calvin 用 她, CUV 用 他
    s = s.replace('基督', '耶稣')  # Calvin 注释 header 偶用 基督, CUV 用 耶稣
    return s


def _longest_common_substring(a, b):
    """O(len(a)*len(b)) DP; returns longest substring length."""
    if not a or not b:
        return 0
    la, lb = len(a), len(b)
    prev = [0] * (lb + 1)
    best = 0
    for i in range(1, la + 1):
        cur = [0] * (lb + 1)
        ai = a[i - 1]
        for j in range(1, lb + 1):
            if ai == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best = cur[j]
        prev = cur
    return best


def find_verse(verse_text, ch, phrase):
    if ch not in verse_text:
        return None
    chunks = [c for c in re.split(r'[…\.]{1,}', phrase) if c.strip()]
    chunks_n = [_normalize(c) for c in chunks]
    chunks_n = [c for c in chunks_n if len(c) >= 2]
    if chunks_n:
        # 一阶段：exact substring（所有长 chunk 都在同一 verse）
        matches = [v for v, txt in verse_text[ch].items()
                   if all(c in _normalize(txt) for c in chunks_n)]
        if matches:
            return min(matches)
    # 二阶段：longest-common-substring 兜底 (≥4 字符)；
    # 适用于省略号短词（"他……来"）或词序差异（"他对腓力说" vs "就对腓力说"）
    full = _normalize(re.sub(r'[…\.]+', '', phrase))
    if len(full) < 4:
        return None
    best_v, best_len = None, 0
    for v, txt in verse_text[ch].items():
        norm_txt = _normalize(txt)
        lcs = _longest_common_substring(full, norm_txt)
        # 阈值与 phrase 长度成比例: ≥4 字符 + ≥phrase 60%
        min_len = max(4, len(full) * 6 // 10)
        if lcs >= min_len and lcs > best_len:
            best_len = lcs
            best_v = v
    return best_v


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book-cn', required=True)
    ap.add_argument('--cuv-abbrev', required=True, help='CUV bibles json abbrev (jo / mt / ...)')
    ap.add_argument('--dir', required=True)
    ap.add_argument('--cuv-json', default='scripts/zh_cuv.json')
    args = ap.parse_args()

    cuv = json.loads(Path(args.cuv_json).read_text(encoding='utf-8-sig'))
    book = next((b for b in cuv if b['abbrev'] == args.cuv_abbrev), None)
    if not book:
        raise SystemExit(f'CUV abbrev {args.cuv_abbrev!r} not found')

    verse_text = {}
    for ch_i, verses in enumerate(book['chapters'], 1):
        verse_text[ch_i] = {}
        for v_i, t in enumerate(verses, 1):
            verse_text[ch_i][v_i] = re.sub(r'\s', '', convert(t))

    book_cn = args.book_cn
    # 仅过滤完整书名引用（"路加福音"），不过滤裸人名（"约翰" / "马太"）——因为
    # "约翰" 是 v.6 经文里 John the Baptist 的人名，phrase "名叫约翰" 必须能匹配。
    book_token_re = re.compile(
        r'(马太福音|马可福音|路加福音|约翰福音|罗马书|哥林多前书|哥林多后书|'
        r'加拉太书|以弗所书|腓立比书|歌罗西书|帖撒罗尼迦|提摩太|提多书|腓利门书|'
        r'希伯来书|雅各书|彼得前书|彼得后书|约翰一书|约翰二书|约翰三书|犹大书|启示录)'
    )
    # Plain bare-CJK phrase + ?/。/. + space/CJK commentary (Pass 3 用):
    # 形如 `你是以利亚吗？他们为什么提以利亚...` — OCR ❷❶ 圈号被剥后无任何 markup
    # phrase 内允许中文省略号 `……` 或 ASCII `....` (Calvin 简写省略, 如
    # `你是……西门。` `耶稣……下迦百农去。`); terminator 必须是 `。/?/!/？/！`
    # 不允许单 `.` 作 terminator 以防把省略号中的 `.` 误切
    # 段首允许全角括号 `（...）` 开头 (如 `（因为）上帝爱世人。`)
    bare_marker_re = re.compile(
        r'^([（(]?[一-鿿][一-鿿…\.（）()]{1,30}?[一-鿿]）?)([？！。?!])\s*([一-鿿].{20,})$'
    )

    # 允许多种 `**phrase**` 形态:
    #   `**phrase。** rest`            ← 标准形式 (period 在 ** 内)
    #   `** phrase **`                 ← OCR 偶尔在 `**` 内外加空格
    #   `**phrase**。rest`             ← period 在 ** 外 (OCR 漏吃 period, 如 `**太初有道**。`)
    #   `**phrase。**rest`             ← 无空格紧贴 (如 `**有一个人。**现`)
    bold_marker_re = re.compile(r'^\*\*\s*([一-鿿][^*\n]{1,60}?)\s*\*\*([。.,，！？]?)\s*(.*)$')
    # section header
    sec_re = re.compile(rf'^## {re.escape(args.book_cn)} (\d+):\d+(?:-\d+)?')
    # italic-only phrase 段开头：`*phrase。* rest`
    italic_marker_re = re.compile(r'^\*\s*([一-鿿][^*\n]{2,60}?)。?\s*\*\s+(.*)$')

    total = 0
    for f in sorted(Path(args.dir).glob('*.md')):
        if not f.stem.isdigit():
            continue
        ch = int(f.stem)
        text = f.read_text(encoding='utf-8')
        lines = text.split('\n')
        fixed = 0

        # Pass 1: bold `**phrase。**` 加 verse-marker
        for i, ln in enumerate(lines):
            m = bold_marker_re.match(ln)
            if not m:
                continue
            phrase = m.group(1).rstrip('。.')
            # m.group(2) 是 outside period (可能为空); m.group(3) 是剩余 commentary
            outside_punct = m.group(2) or ''
            rest = m.group(3).lstrip()
            if book_token_re.search(phrase):
                continue
            # 跳过已经是 marker 的 (**N:V。** 形式)
            if re.match(r'^[一-鿿]+\s+\d+:\d+$', phrase):
                continue
            v = find_verse(verse_text, ch, phrase)
            if not v:
                continue
            new = f'**{book_cn} {ch}:{v}。** *{phrase}。* {rest}'.rstrip()
            if new != ln:
                lines[i] = new
                fixed += 1
                print(f'  {f.name}:L{i+1} → {ch}:{v} *{phrase[:24]}*  [bold]')

        # Pass 3: plain bare-CJK phrase + ?/。/. + commentary → 加 marker
        # context-aware: 优先选 phrase 命中且在当前 section range 内的 verse
        # (避免 Calvin 短句简写歧义引出错误高/低 verse)
        sections_in_ch = []
        for li, l in enumerate(lines):
            ms = re.match(rf'^## {re.escape(book_cn)} {ch}:(\d+)(?:-(\d+))?', l)
            if ms:
                sections_in_ch.append((li, int(ms.group(1)),
                                      int(ms.group(2)) if ms.group(2) else int(ms.group(1))))

        def section_for_line(li):
            for k, (sln, lo, hi) in enumerate(sections_in_ch):
                nxt = sections_in_ch[k+1][0] if k+1 < len(sections_in_ch) else len(lines)
                if sln < li < nxt: return (lo, hi)
            return None

        for i, ln in enumerate(lines):
            m = bare_marker_re.match(ln)
            if not m: continue
            phrase = m.group(1)
            punct = m.group(2)
            rest = m.group(3)
            COMMON_OPENERS = {'首先', '其次', '然后', '所以', '但是', '因此', '另外', '同样',
                              '此外', '总之', '换言之', '一方面', '反之', '现在', '当然',
                              '虽然', '不过', '然而'}
            if phrase in COMMON_OPENERS: continue
            if book_token_re.search(phrase): continue
            p_norm = _normalize(phrase)
            if len(p_norm) < 4: continue
            # 阶段 1: exact substring
            cands = [v for v, txt in verse_text[ch].items() if p_norm in _normalize(txt)]
            # 阶段 2: LCS 兜底 (Calvin 简写省字, 如 "许多人信了他的名" vs CUV
            # "许多人...就信了他的名" 中间有夹字, substring 不命中但 LCS 高)
            if not cands and len(p_norm) >= 6:
                min_lcs = max(6, len(p_norm) * 7 // 10)
                cands = [v for v, txt in verse_text[ch].items()
                         if _longest_common_substring(p_norm, _normalize(txt)) >= min_lcs]
            if not cands: continue
            # context-aware: 优先 section range 内的 verse
            sec = section_for_line(i)
            if sec:
                in_sec = [v for v in cands if sec[0] <= v <= sec[1]]
                if in_sec:
                    v = min(in_sec)
                elif len(cands) == 1:
                    # 候选只 1 个 (unambiguous), 加 marker 让 relocate 移到正确 section
                    v = cands[0]
                else:
                    # 多个候选都不在 section: 跳过 (避免误标)
                    continue
            else:
                v = min(cands)
            new = f'**{book_cn} {ch}:{v}。** *{phrase}{punct}* {rest}'
            if new != ln:
                lines[i] = new
                fixed += 1
                print(f'  {f.name}:L{i+1} → {ch}:{v} *{phrase[:24]}*  [bare]')

        # Pass 2: section 起始 italic 续段 `*phrase。* commentary` → 加 marker
        # 只处理 section 起首第一个 *phrase* 段（之前没有任何 bold marker / 内容段）
        # 因为 section 中间的 italic 续段属于上一个 marker 的同 verse 续段, 不该改
        for k, ln_idx in enumerate([i for i, l in enumerate(lines) if sec_re.match(l)]):
            sec_start = ln_idx
            # 找 section 起首第一个非 boilerplate 段
            j = sec_start + 1
            while j < len(lines):
                l = lines[j]
                if not l.strip() or l.startswith('<') or l.strip() == '</div>':
                    j += 1; continue
                # bold marker → OK, no need to restore italic
                if bold_marker_re.match(l):
                    break
                # italic phrase → 尝试 restore
                im = italic_marker_re.match(l)
                if im:
                    phrase = im.group(1).rstrip('。.')
                    rest = im.group(2)
                    if not book_token_re.search(phrase):
                        v = find_verse(verse_text, ch, phrase)
                        if v:
                            new = f'**{book_cn} {ch}:{v}。** *{phrase}。* {rest}'.rstrip()
                            if new != l:
                                lines[j] = new
                                fixed += 1
                                print(f'  {f.name}:L{j+1} → {ch}:{v} *{phrase[:24]}*  [italic-leading]')
                break

        if fixed:
            f.write_text('\n'.join(lines), encoding='utf-8')
            total += fixed
    print(f'\nTotal restored: {total}')


if __name__ == '__main__':
    main()
