#!/usr/bin/env python3
"""
qa_mhenry.py — 马太亨利注释内容质检工具

用法：
    python3 scripts/qa_mhenry.py <book_id> [pdf_path] [chapter_pages...]

示例（撒迦利亚书）：
    python3 scripts/qa_mhenry.py zechariah \
        ~/Documents/论文/matthew_henry/马太亨利完整圣经注释-撒迦利亚书.pdf \
        1:3:6 2:7:10 3:11:14 4:15:18 5:19:21 6:22:25 7:26:29 \
        8:30:35 9:36:40 10:41:44 11:45:48 12:49:54 13:55:57 14:58:64

章节页码格式: <章号>:<起始页>:<结束页>  （1-indexed）
若不提供 pdf_path，仅做 HTML 结构检查，不对比 PDF 内容。

检测项目
─────────────────────────────────────────────────────────────
[A] 经文泄漏到 mh-unit-body
    症状：mh-unit-body 的开头直接是圣经节号（如「1 那日」「』6 必有」）
    而不是注释文字。

[B] 经文节号出现在 mh-verse 末尾之后（截断跨越 div 边界）
    即 mh-verse 末尾不是引号/句号/叹号，而是句子中途停止。

[C] mh-unit-body 中 mh-l1 块末尾截断
    末尾字符不是句号/叹号/问号/右括号，表示句子不完整。

[D] 跨页截断（需要 PDF）
    比对 md 文件最后一个 mh-l1 块末尾的文字，与 PDF 最后页末尾文字，
    若 md 文件末尾 == PDF 页面末尾（而非 PDF 下一页开头），
    则说明本章末尾与下一章 PDF 页面有内容溢出未被收录。

[E] HTML 标签不平衡
    统计 mh-unit / mh-unit-body / mh-verse / mh-l1 开关标签数量，
    若不平衡报警。

[F] mh-verse 中混入注释文字（非圣经）
    mh-verse 内出现典型注释特征词（如「注意：」「由此可见」「先知在此」）。

[G] mh-unit-body 开头被截断（孤立右括号 / 括号失衡）
    症状：注释体开头缺失（含 I. 引言 + 首个大纲点），只剩一段以经文引用
    右括号起头的残尾，如「书33：11）。」「翰福音11：50）；」「节）：」。
    根因：PDF 抽取/OCR 在页首·分栏边界漏掉注释开头，跨边界的经文引用
    「（书N：M）」只留下右括号。修复须对照中文 PDF 回填（勿翻译勿编造）。
"""

import re
import sys
import os

# ── ANSI colors ────────────────────────────────────────────────────────────────
RED    = "\033[31m"
YELLOW = "\033[33m"
GREEN  = "\033[32m"
CYAN   = "\033[36m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def warn(msg):  print(f"  {YELLOW}⚠ {msg}{RESET}")
def err(msg):   print(f"  {RED}✗ {msg}{RESET}")
def ok(msg):    print(f"  {GREEN}✓ {msg}{RESET}")
def info(msg):  print(f"  {CYAN}→ {msg}{RESET}")

# ── Helpers ────────────────────────────────────────────────────────────────────

VERSE_LEAK_RE = re.compile(
    r'<div class="mh-unit-body">\s*'          # start of mh-unit-body
    r'(?:<[^>]+>\s*)*'                          # optional tags
    r'(?:』|』|「|）)'                             # closing quote from verse
    r'?\s*\d+\s*[\u4e00-\u9fff]',              # digit + Chinese (verse number)
    re.DOTALL
)

VERSE_INLINE_COMMENTARY_RE = re.compile(
    r'<div class="mh-verse"[^>]*>.*?'
    r'(?:注意：|由此可见|先知在此|先知在这|前面说的是|记录在本章)',
    re.DOTALL
)

SENTENCE_END_CHARS = set('。！？」』）')

def check_tag_balance(text, tag):
    """Return (open_count, close_count) for a given class tag."""
    open_re  = re.compile(r'<div class="' + re.escape(tag) + r'"')
    close_re = re.compile(r'</div>')
    opens  = len(open_re.findall(text))
    # Approximate: count </div> that logically close mh-* tags
    # Just check open count is reasonable
    return opens

def last_mhl1_tail(text, n=60):
    """Return the last N chars of the last mh-l1 content."""
    blocks = re.findall(
        r'<div class="mh-l1">.*?</div>',
        text, re.DOTALL
    )
    if not blocks:
        return None
    last = blocks[-1]
    # Strip tags to get plain text
    plain = re.sub(r'<[^>]+>', '', last).strip()
    return plain[-n:] if len(plain) >= n else plain

def check_md_file(md_path, pdf_doc=None, pdf_start=None, pdf_end=None):
    """Run all checks on a single .md file."""
    chap = os.path.basename(md_path).replace('.md', '')
    print(f"\n{BOLD}── Chapter {chap} ({md_path.split('/')[-1]}) ──{RESET}")

    with open(md_path, encoding='utf-8') as f:
        text = f.read()

    issues = 0

    # [A] verse leak into mh-unit-body
    leaks = re.findall(
        r'(<div class="mh-unit-body">\s*(?:[\s\S]{0,80}?)(?:』|）|」)?\s*\d+\s)',
        text
    )
    # Refined: look for mh-unit-body where content starts with quote+digit or just digit
    body_starts = re.findall(
        r'<div class="mh-unit-body">\s*\n\s*\n([\S ]{0,120})',
        text
    )
    for start in body_starts:
        stripped = re.sub(r'<[^>]+>', '', start).strip()
        # Verse leak: starts with closing quote + digit, or digit directly
        if re.match(r'^[』」）]?\s*\d+\s*[\u4e00-\u9fff]', stripped):
            err(f"[A] 经文泄漏到 mh-unit-body 开头: 「{stripped[:50]}…」")
            issues += 1

    # [B] mh-verse ends mid-sentence
    verse_blocks = re.findall(
        r'<div class="mh-verse"[^>]*>([\s\S]*?)</div>',
        text
    )
    for vb in verse_blocks:
        plain = re.sub(r'<[^>]+>', '', vb).strip()
        if not plain:
            continue
        last_char = plain[-1]
        if last_char not in SENTENCE_END_CHARS:
            # Allow it if it ends with a Chinese character (might be OK for some)
            # But flag if it ends with a common mid-sentence character
            if last_char in '，、；：':
                err(f"[B] mh-verse 末尾似乎截断（末尾字符：「{last_char}」）: …{plain[-40:]}")
                issues += 1
            elif re.search(r'[\u4e00-\u9fff]$', plain):
                # Ends with Chinese char but not sentence-end punctuation
                # Check if it looks like a word break (no closing bracket/quote)
                if not re.search(r'[」』）]$', plain):
                    warn(f"[B] mh-verse 末尾可能截断: …{plain[-50:]}")
                    issues += 1

    # [C] last mh-l1 ends abruptly
    tail = last_mhl1_tail(text, n=80)
    if tail:
        last_char = tail.strip()[-1] if tail.strip() else ''
        if last_char not in SENTENCE_END_CHARS and last_char not in '）」』':
            err(f"[C] 最后一个 mh-l1 末尾疑似截断: …「{tail.strip()[-60:]}」")
            issues += 1
        else:
            ok(f"[C] 最后 mh-l1 末尾正常: …「{tail.strip()[-40:]}」")

    # [F] mh-verse contains commentary text
    commentary_markers = ['注意：', '由此可见', '先知在此', '前面说的是', '记录在本章']
    for vb in verse_blocks:
        plain = re.sub(r'<[^>]+>', '', vb).strip()
        for marker in commentary_markers:
            if marker in plain:
                err(f"[F] mh-verse 中混入注释文字（含「{marker}」）: …{plain[plain.index(marker)-10:plain.index(marker)+30]}…")
                issues += 1
                break

    # [G] mh-unit-body 开头被截断（孤立右括号）
    #     读每个 mh-unit-body 起始正文, 若从头到尾先遇到 ） 而其前无 （（括号失衡），
    #     说明开头连同经文引用的 （ 一起被 PDF 抽取/OCR 漏掉（跨页·分栏边界），
    #     只留下右括号。典型残尾: 「书33：11）。」「翰福音11：50）；」「节）：」。参见 skill §4.6。
    for m in re.finditer(r'<div class="mh-unit-body">([\s\S]{0,300})', text):
        seg = re.sub(r'<[^>]+>', '', m.group(1))
        io = seg.find('（'); ic = seg.find('）')
        if ic != -1 and (io == -1 or ic < io):
            snip = re.sub(r'\s+', '', seg)[:40]
            err(f"[G] mh-unit-body 开头疑似截断（孤立右括号）: 「{snip}…」")
            issues += 1

    # [E] tag balance (simple check)
    n_unit      = text.count('<div class="mh-unit">')
    n_verse     = text.count('<div class="mh-verse">')
    n_body      = text.count('<div class="mh-unit-body">')
    if n_unit != n_verse or n_unit != n_body:
        warn(f"[E] 标签数量不匹配：mh-unit={n_unit} mh-verse={n_verse} mh-unit-body={n_body}")
        issues += 1

    # [D] PDF cross-page truncation check
    if pdf_doc and pdf_start and pdf_end:
        try:
            import fitz
            # Get last page text
            last_page_text = pdf_doc[pdf_end - 1].get_text()  # 0-indexed
            # Get last 200 chars of last PDF page (excluding header/footer)
            lines = [l.strip() for l in last_page_text.split('\n')
                     if l.strip() and not re.match(r'^(马太亨利|第\d+页|第.+章)$', l.strip())]
            if lines:
                pdf_last_sentence = lines[-1][-80:]

                # Get last 200 chars of md text (excluding HTML tags)
                md_plain = re.sub(r'<[^>]+>', '', text)
                md_plain = re.sub(r'\s+', ' ', md_plain).strip()
                md_tail = md_plain[-200:]

                # Check if the PDF's last line appears in the md file
                # (it should, unless truncated)
                key = pdf_last_sentence[-30:] if len(pdf_last_sentence) >= 30 else pdf_last_sentence
                if key and key not in text:
                    # Check next page for overflow
                    if pdf_end < len(pdf_doc):
                        next_page = pdf_doc[pdf_end].get_text()
                        next_lines = [l.strip() for l in next_page.split('\n')
                                      if l.strip() and not re.match(r'^(马太亨利|第\d+页|第.+章)$', l.strip())]
                        if next_lines:
                            next_first = next_lines[0][:60]
                            warn(f"[D] 跨页溢出？PDF末页末句: 「{key}」未在md中找到")
                            info(f"    下一页开头: 「{next_first}」")
                            issues += 1
        except Exception as e:
            warn(f"[D] PDF检查失败: {e}")

    if issues == 0:
        ok("所有检查通过")
    else:
        print(f"  {RED}发现 {issues} 个问题{RESET}")

    return issues


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    book_id = args[0]
    site_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    book_dir  = os.path.join(site_root, 'mhenry', book_id)

    if not os.path.isdir(book_dir):
        print(f"{RED}书卷目录不存在: {book_dir}{RESET}")
        sys.exit(1)

    # Parse optional pdf + chapter pages
    pdf_path = None
    chapter_pages = {}  # {ch_num: (start_page, end_page)}  1-indexed
    pdf_doc = None

    for arg in args[1:]:
        if os.path.exists(arg) or arg.endswith('.pdf'):
            pdf_path = os.path.expanduser(arg)
        elif ':' in arg:
            parts = arg.split(':')
            ch = int(parts[0])
            start = int(parts[1])
            end = int(parts[2]) if len(parts) > 2 else int(parts[1])
            chapter_pages[ch] = (start, end)

    if pdf_path:
        try:
            import fitz
            pdf_doc = fitz.open(pdf_path)
            print(f"{GREEN}PDF 已加载: {pdf_path} ({len(pdf_doc)} 页){RESET}")
        except ImportError:
            print(f"{YELLOW}未安装 PyMuPDF（fitz），跳过 PDF 检查。安装：pip install pymupdf{RESET}")
        except Exception as e:
            print(f"{YELLOW}PDF 加载失败: {e}{RESET}")

    # Collect chapter files
    md_files = sorted(
        [f for f in os.listdir(book_dir) if f.endswith('.md') and f != 'preface.md'
         and re.match(r'^\d+\.md$', f)],
        key=lambda x: int(x.replace('.md', ''))
    )

    total_issues = 0
    print(f"\n{BOLD}{CYAN}═══ 马太亨利注释质检：{book_id} ═══{RESET}")

    for md_file in md_files:
        ch = int(md_file.replace('.md', ''))
        md_path = os.path.join(book_dir, md_file)
        pages = chapter_pages.get(ch)
        pdf_start = pages[0] if pages else None
        pdf_end   = pages[1] if pages else None
        issues = check_md_file(md_path, pdf_doc, pdf_start, pdf_end)
        total_issues += issues

    # Also check preface
    preface_path = os.path.join(book_dir, 'preface.md')
    if os.path.exists(preface_path):
        print(f"\n{BOLD}── Preface ──{RESET}")
        with open(preface_path, encoding='utf-8') as f:
            ptext = f.read()
        # Simple check: not empty
        if len(ptext) < 200:
            warn("前言内容过短，请核查")
        else:
            ok("前言内容长度正常")

    print(f"\n{BOLD}{'═'*50}{RESET}")
    if total_issues == 0:
        print(f"{GREEN}{BOLD}✓ 全部检查通过，共 {len(md_files)} 章{RESET}")
    else:
        print(f"{RED}{BOLD}✗ 共发现 {total_issues} 个问题，请逐一修复{RESET}")

    return total_issues


if __name__ == '__main__':
    sys.exit(main())
