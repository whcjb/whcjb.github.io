#!/usr/bin/env python3
"""合参书注释头：纯节号 **N.** → 完整「书卷 章:节。」引用。

skill 规则(05-publish-zh §合参注释头): 合参(harmony)书每节注释头必须写全书卷+章+节,
不能只写节号。书卷+章由上下文推断——最近的 绿色h2章标题 / 「前往」指引 / 已有全引用头 /
经文框 thead 英文引用, 四者取最近者。

- 只改 `**N.** <span style="color:#800000">` 形式的纯节号头 → `书卷 章:N。 <span...>`(纯文本, 非粗体, 与既有全引用头一致)
- 幂等: 已是全引用的头不匹配, 重跑安全。
- 若某头无任何上下文可定位 → 保留原样 + 打印警告(不臆造)。

用法: python3 scripts/add_verse_refs_harmony.py calvin/harmony-law-2/23.md [更多文件...]
      python3 scripts/add_verse_refs_harmony.py --all-law    # 全 law-1/2/3/4
"""
import re, sys, glob

BOOKS = r'创世记|出埃及记|利未记|民数记|申命记'
GREEN = re.compile(r'<span style="color:#006411">(' + BOOKS + r')\s*(\d+)\s*</span>')
GOTO  = re.compile(r'前往\s*(' + BOOKS + r')\s*(\d+)')
FULL  = re.compile(r'^(' + BOOKS + r')\s*(\d+):(\d+)[。.]\s*<span style="color:#800000">')
EN2CN = {'GENESIS':'创世记','EXODUS':'出埃及记','LEVITICUS':'利未记','NUMBERS':'民数记','DEUTERONOMY':'申命记'}
THEAD = re.compile(r'<th[^>]*>.*?\b(GENESIS|EXODUS|LEVITICUS|NUMBERS|DEUTERONOMY)\s+(\d+):', re.I)
BARE  = re.compile(r'^\*\*(\d+)\.\*\* (<span style="color:#800000">)')
# 已有的【纯文本】全引用头(旧版转出的 或 原译文里的): "书卷 章:节。 <span maroon>" —— 需加粗
PLAINFULL = re.compile(r'^(' + BOOKS + r') (\d+):(\d+)[。.] (<span style="color:#800000">)')
# 已加粗的全引用头(幂等识别, 不重复处理但更新上下文): "**书卷 章:节。**"
BOLDFULL = re.compile(r'^\*\*(' + BOOKS + r') (\d+):(\d+)[。.]\*\* <span style="color:#800000">')


def transform(text):
    """合参注释头 → 加粗完整引用 **书卷 章:节。**(与对观福音合参一致, 使布局JS识别为可点击verse锚)。"""
    book = chap = None
    out = []; changed = 0; warned = 0
    for ln in text.split('\n'):
        for rx in (GREEN, GOTO, FULL, BOLDFULL):
            m = rx.search(ln)
            if m: book, chap = m.group(1), m.group(2)
        t = THEAD.search(ln)
        if t: book, chap = EN2CN[t.group(1).upper()], t.group(2)
        b = BARE.match(ln)
        if b:
            if book and chap:
                out.append(f'**{book} {chap}:{b.group(1)}。** {b.group(2)}' + ln[b.end():])
                changed += 1; continue
            warned += 1
        pf = PLAINFULL.match(ln)
        if pf:
            book, chap = pf.group(1), pf.group(2)
            out.append(f'**{pf.group(1)} {pf.group(2)}:{pf.group(3)}。** {pf.group(4)}' + ln[pf.end():])
            changed += 1; continue
        out.append(ln)
    return '\n'.join(out), changed, warned


def run(files):
    tot = tw = 0
    for f in files:
        s = open(f, encoding='utf-8').read()
        s2, n, w = transform(s)
        if n:
            open(f, 'w', encoding='utf-8').write(s2)
        print(f"  {f.split('/',1)[1] if '/' in f else f}: {n} 头转换" + (f"  ⚠{w}无上下文" if w else ""))
        tot += n; tw += w
    print(f"合计: {tot} 个注释头转全引用" + (f", ⚠{tw} 个无上下文(已保留)" if tw else ", 0 警告"))


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--all-law']:
        files = sorted(glob.glob("calvin/harmony-law-[1-4]/[0-9]*.md"))
    else:
        files = args
    if not files:
        print("usage: add_verse_refs_harmony.py <file...> | --all-law"); sys.exit(1)
    run(files)
