#!/usr/bin/env python3
"""诗篇中译发布后自检 (zero-token, 纯本地)。

用法:
    python3 scripts/qa_psalms_zh.py                # 全卷 psalms-1
    python3 scripts/qa_psalms_zh.py 53 54 55       # 指定章
    python3 scripts/qa_psalms_zh.py --book psalms-2

检查项 (对应 4cce04db4 那批人工发现的问题):
  [P] 对话式污染   —— Claude 的回复顶替了正文/经文引用行 (ch44 案例)
  [M] 残留标记     —— <<<END>>> / ``` / [BATCH] 等提示词碎片 (ch18 案例)
  [U] 漏译         —— 整段仍是英文 (无 CJK 且 ASCII 字母成句)
  [S] 结构错位     —— 与英文版逐块类型序列不一致 (ch7/8/9/18/51 案例:
                      英文 1 段被译成多段)
  [V] 经文节号     —— 经文框内 <strong>N.</strong> 序列与英文版不一致
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent

# --- [P] 对话式污染特征 --------------------------------------------------
# STRONG: 只要出现就报 (正常译文不可能出现)
POLLUTION_STRONG = [
    '我已就位', '没有收到', '需要翻译的英文', '请提供英文', '以下是译文',
    '翻译如下', '我无法翻译', '当前分支', '未提交的更改', 'Co-Authored-By',
    'Claude', 'assistant:',
]
# WEAK: 只在短块里报 —— 对话式回复通常很短, 正文段落很长, 避免误伤散文
POLLUTION_WEAK = ['抱歉', '好的，我', '明白了', '如需', '作为 AI', '仓库']
WEAK_MAX_LEN = 300
# --- [M] 提示词/流程残留标记 --------------------------------------------
MARKERS = ['<<<END>>>', '<<<', '>>>', '```', '[BATCH', 'CHUNK ', '---8<---']

CJK = re.compile(r'[一-鿿]')
FM = re.compile(r'\A---\n.*?\n---\n', re.S)


def blocks(text):
    """去掉 front matter, 按空行切块。"""
    text = FM.sub('', text)
    return [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]


def btype(b):
    """把块归类成结构类型 —— 只看骨架, 不看文字内容。"""
    if b.startswith('<h2 class="scripture-anchor"'):
        return 'anchor'
    if b.startswith('<div class="scripture-box"'):
        return 'box-open'
    if b.startswith('<p class="scripture-ref"'):
        return 'ref'
    if b == '</div>':
        return 'box-close'
    if b.startswith('<!-- PAGE'):
        return 'page'
    if b.startswith('<p style="text-align:center'):
        return 'center'
    if re.match(r'\[\^f?\w+\]:', b):
        return 'footnote-def'
    if b.startswith('<strong>') or re.match(r'^\*?\*?\d+\.', b):
        return 'verse-text'
    if b.startswith('<'):
        return 'html'
    return 'para'


def verse_nums(b):
    """英文版用 <strong>N.</strong>, 中文版在 markdown="1" 块里用 **N.** —— 两种都收。"""
    return (re.findall(r'<strong>(\d+)\.</strong>', b)
            + re.findall(r'\*\*(\d+)\.\*\*', b))


def check(zh_path, en_path):
    issues = []
    zt = zh_path.read_text(encoding='utf-8')
    zb = blocks(zt)

    for b in zb:
        for pat in POLLUTION_STRONG:
            if pat in b:
                issues.append(('P', f'疑似对话式污染 {pat!r}: {b[:90]}'))
        if len(b) <= WEAK_MAX_LEN:
            for pat in POLLUTION_WEAK:
                if pat in b:
                    issues.append(('P', f'短块含可疑措辞 {pat!r}: {b[:90]}'))
        for pat in MARKERS:
            if pat in b:
                issues.append(('M', f'残留标记 {pat!r}: {b[:90]}'))
        if btype(b) in ('para', 'verse-text') and not CJK.search(b):
            # 纯英文成句 (排除短的 HTML 碎片/数字)
            if len(re.findall(r'[A-Za-z]{3,}', b)) >= 8:
                issues.append(('U', f'疑似漏译(整段英文): {b[:90]}'))

    if en_path.exists():
        eb = blocks(en_path.read_text(encoding='utf-8'))
        zseq, eseq = [btype(b) for b in zb], [btype(b) for b in eb]
        if zseq != eseq:
            i = next((k for k in range(min(len(zseq), len(eseq)))
                      if zseq[k] != eseq[k]), min(len(zseq), len(eseq)))
            issues.append(('S', f'结构序列不一致 (zh {len(zseq)} 块 / en {len(eseq)} 块), '
                                f'首个分歧 #{i}: zh={zseq[i] if i < len(zseq) else "-"} '
                                f'en={eseq[i] if i < len(eseq) else "-"} | '
                                f'zh块: {(zb[i][:70] if i < len(zb) else "")!r}'))
        zv = [v for b in zb for v in verse_nums(b)]
        ev = [v for b in eb for v in verse_nums(b)]
        if zv != ev:
            issues.append(('V', f'经文节号序列不一致: zh={zv} en={ev}'))
    else:
        issues.append(('S', f'英文对照缺失: {en_path}'))
    return issues


def main():
    argv = sys.argv[1:]
    book = 'psalms-1'
    if '--book' in argv:
        i = argv.index('--book')
        book = argv[i + 1]
        del argv[i:i + 2]

    zh_dir = ROOT / 'calvin' / book
    en_dir = ROOT / 'calvin' / f'{book}-en'
    if argv:
        chapters = argv
    else:
        chapters = sorted((p.stem for p in zh_dir.glob('*.md') if p.stem.isdigit()),
                          key=int)

    bad = 0
    for ch in chapters:
        zh = zh_dir / f'{ch}.md'
        if not zh.exists():
            print(f'ch{ch}: 缺失 {zh}')
            bad += 1
            continue
        issues = check(zh, en_dir / f'{ch}.md')
        if issues:
            bad += 1
            print(f'\n=== {book} ch{ch}: {len(issues)} 处 ===')
            for kind, msg in issues:
                print(f'  [{kind}] {msg}')

    print(f'\n共查 {len(chapters)} 章, {bad} 章有问题, {len(chapters) - bad} 章干净。')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
