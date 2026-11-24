#!/usr/bin/env python3
"""修跨页断句：一句话被 PAGE 分页标记拦腰截成两个段落。

缺陷形态（AGES PDF 提取阶段产生）：
    ...The fisheries of the Nile also are very productive, and a part:
    <!-- PAGE 14 -->
    of the wealth of Egypt: whilst the country is so well watered...
底本里这是跨页的**同一句话**（第 13 页末 → 第 14 页首），提取时按空行切段，
于是一句被拆成两段。中译照着拆，读者看到的就是「…一部分」断在那里、
下一段突兀地从「埃及的财富之利」起头。

检测（三个条件同时成立，实测 520 处抽样零误报）：
1. 段落结尾**没有**句末标点（. ! ? » ” " ’），且不是脚注定义/注释/标题行；
2. 紧随其后（允许空行）是 `<!-- PAGE N -->` 标记；
3. 标记之后的第一个非空段落以**小写字母**或中文/西文左引号起头。

修法：把两段合并回一段，PAGE 标记原样留在行内（HTML 注释不渲染，
且正文里本来就有行内 PAGE 标记的先例）。**不删除任何原文字符。**

英文合并后该段 md5 变化，中译需对相应章节 `--resume` 重跑：只有被合并的段落
会重新翻译，其余全部缓存命中。

用法:
    python3 scripts/fix_page_split_paragraphs.py --dry-run          # 全库普查
    python3 scripts/fix_page_split_paragraphs.py --dry-run calvin/isaiah-1-en
    python3 scripts/fix_page_split_paragraphs.py                    # 修全库
    python3 scripts/fix_page_split_paragraphs.py calvin/isaiah-1-en # 只修一卷
"""
import argparse
import glob
import os
import re
import sys

TAG = re.compile('<[^>]+>')
# 句末标点：中英都要收。原先只有 ASCII 一套，于是中文页里正常以「。」
# 收尾的段落一律被当成「没结句」，只靠下面的续段守卫兜着，很脆。
END_PUNCT = re.compile(r'[.!?»”"’。！？；」』】）]\s*$')
# 句中引语：逗号/顿号/分号/冒号 紧接右引号收尾
MID_QUOTE = re.compile(r'[,，、;；:：]\s*[»”"’]\s*$')
# 经文/章节出处缩写：其后的「N.」是出处，不是分条序号
_REF_ABBR = {'vers', 'ver', 'verse', 'verses', 'chap', 'chapter', 'cap', 'ch', 'psal', 'ps',
             'psalm', 'see', 'comp', 'cf', 'sect', 'part', 'lib', 'book', 'page', 'pag', 'p', 'v'}


def find_splits(lines):
    """→ [(段尾行号, 续段行号)]"""
    out = []
    for i, l in enumerate(lines):
        s = TAG.sub('', l).strip()
        if not s or s.startswith(('[^', '<!--', '#')) or len(s) < 30:
            continue
        # 引号内逗号不算句末：英式/美式标点把逗号收在引号里，于是
        # `“The name of God,” or “of Christ,”` 这种**句中**引语以 `”` 收尾，
        # 被 END_PUNCT 当成结句放过（1corinthians/6.md 那处跨页断句就这么漏的，
        # 2026-09-03；这已是本 Gate 的第三个洞，前两个见上面注释）。
        # 段尾是光秃的分条序号（`…or object. 3.` / `For, 1.`）：序号后的那句被分页截走了，
        # 不是句末。达拉谟启示录 6 处靠中译「第三，」才露出来（2026-11-24）。
        # 前面须是一个真词收句/收分句（object. / them. / For,），引证缩写（vers. / Chap. /
        # Psal.）后的数字是经文出处、不算；`Chap. 19. 2.` 这种章号后再跟序号的单列。
        # 罗马数字（`Ps. xxxv. 4.`）、书卷缩写（`Isa.`，首字母大写的短词）也都是出处。
        m = re.search(r'\b([A-Za-z]{2,})[.,;:]\s\d{1,2}\.$', s)
        w = m.group(1) if m else ''
        bare_num = bool(m and w.lower() not in _REF_ABBR
                        and not re.fullmatch(r'[ivxlcdm]+', w, re.I)
                        and (w.islower() or w in ('For', 'Answer'))) or \
            bool(re.search(r'\b(?:Chap|Chapter)\.?\s\d+\.\s\d{1,2}\.$', s))
        if ((END_PUNCT.search(s) and not MID_QUOTE.search(s)) or s.endswith(']')) and not bare_num:
            continue
        k, page = i + 1, False
        while k < len(lines):
            x = lines[k].strip()
            if not x:
                k += 1; continue
            if x.startswith('<!-- PAGE'):
                page = True; k += 1; continue
            break
        if not page or k >= len(lines):
            continue
        nxt = TAG.sub('', lines[k]).strip()
        if not nxt:
            continue
        # 续段守卫。原先只认「小写起首」，于是续段是**专有名词**时漏检：
        # hodge/1corinthians/preface.md 那句 `…went into a certain man's
        # house, named` / `Justus, one who worshipped God…` 被截成两段，
        # 而 Gate 5g 报 0（2026-09-03 用户看出来的）。补第二条规则：
        # 上一段末字是字母或逗号顿号一类**明确的句中字符**（连缩写点都没有），
        # 那它必然是被截断的，不管续段首字大小写。
        # 仍排除续段本身是标题/居中块/脚注定义/列表项的情形——那些是真的新段。
        looks_cont = nxt[0].islower() or nxt[0] in '（(’”'
        raw_nxt = lines[k].strip()
        # 断词连字符：`un-` + `Churching`。只认紧贴字母、续段是正文的；`It follows,-` / `proceed -`
        # 这种破折号后面跟的是经文标题，不算。
        hyphen = bool(re.search(r'[A-Za-z]-$', s)) and not re.search(r'[,\s]-$', s) and raw_nxt[:1].isalpha()
        mid_sentence = bool(re.search(r'[A-Za-z0-9一-鿿,，、;；:：]$', s)) or bare_num or hyphen
        nxt_is_new_block = bool(re.match(r'^(#|\*\*|\[\^|[-*+]\s|\d+\\?\.\s)', nxt))  # `2\. ` 是转义过的分条序号
        # 续段是分条序号，但上一段停在字母、逗号、连字符上（`Hence Observe,` / `of whom
        # they were verse` → `4\. …`）：那是句中插进来的序号，仍是同一句。冒号收尾的
        # 「如下：」+ 列表不算，照旧当新段。
        if nxt_is_new_block and re.match(r'^\d+\\\.\s', raw_nxt) and re.search(r'[a-z],?$', s):
            nxt_is_new_block = False
        if (looks_cont or mid_sentence) and not nxt_is_new_block:
            out.append((i, k))
    return out


def fix_file(path, dry):
    lines = open(path, encoding='utf-8').read().split('\n')
    spans = find_splits(lines)
    if not spans or dry:
        return spans
    for i, k in sorted(spans, reverse=True):        # 从后往前改, 行号不失效
        mid = [x.strip() for x in lines[i + 1:k] if x.strip()]   # 中间的 PAGE 标记
        sep = '' if lines[i].rstrip().endswith('-') else ' '   # `un-` + `Churching` 接回不留空格
        lines[i] = lines[i].rstrip() + sep + ' '.join(mid) + sep + lines[k].lstrip()
        del lines[i + 1:k + 1]
    os.chmod(path, 0o644)
    open(path, 'w', encoding='utf-8').write('\n'.join(lines))
    return spans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dirs', nargs='*', help='默认扫 calvin/*-en')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    dirs = a.dirs or sorted(glob.glob('calvin/*-en'))

    total, chapters = 0, []
    for d in dirs:
        n = 0
        for f in sorted(glob.glob(os.path.join(d, '*.md'))):
            spans = fix_file(f, a.dry_run)
            if spans:
                n += len(spans)
                chapters.append((os.path.basename(d), os.path.basename(f)[:-3], len(spans)))
        if n:
            print(f'  {os.path.basename(d)}: {n} 处')
            total += n
    print(f'\n{"发现" if a.dry_run else "已合并"} {total} 处，涉及 {len(chapters)} 个章节文件')
    if chapters:
        print('需要 --resume 重跑中译的章节：')
        by_book = {}
        for b, ch, n in chapters:
            by_book.setdefault(b[:-3], []).append(ch)
        for b, chs in sorted(by_book.items()):
            print(f'  {b}: {" ".join(sorted(chs, key=lambda c: (not c.isdigit(), int(c) if c.isdigit() else c)))}')
    return 0 if total == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
