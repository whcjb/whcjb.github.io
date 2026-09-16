#!/usr/bin/env python3
"""删掉拉丁文经文后面多余的中文括注（中译版上一行已经有同一节的中文了）。

加尔文注释的中译页，经文框里是「中文经文 + 拉丁文经文」两行。个别书卷的译者
在拉丁文那一行末尾又用括号把整节重译了一遍：

    **5.** 盗贼若来在你那里，或强盗夜间而来（你何竟被剪除），岂不偷窃直到够了呢？…
    **5.** An fures venerunt ad te? … Annon reliquissent racemos?（盗贼曾来到你那里吗？…）

同一节的中文出现两遍，框被撑得很长。删掉拉丁文后面那个括注即可——中文经文本来
就在上面。

判定（三条全中才删）：
  1. 该行是经文行（`**N.**` / `<strong>N.</strong>` 起头），不是脚注定义；
  2. 括注前面紧挨着的是拉丁文（前 24 个字符里有 ≥8 个拉丁字母、没有汉字）；
  3. 同一个框（或前后 8 行窗口）里能找到这一节的中文——`**N.**` 后面直接跟
     汉字。找不到就跳过并报警：那种地方括注是唯一的中文，删了读者就没中文
     经文可读了（阿摩司书 5:7 就是这种，单独处理）。

第 3 条很要紧：阿摩司书 1:10、以西结书 15:2-4 的中文是接在**上一行末尾**或
**下一行**的（译文把两节挤在一段里），只看「上一行开头」会误判成没有中文。

用法：
    python3 scripts/fix_latin_zh_gloss.py [--apply]
"""
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CJK = re.compile(r'[一-鿿]')
VERSE_LINE = re.compile(r'^\s*(?:<p[^>]*>)?\s*(?:\*\*|<strong>)(\d+)[.．]')
# 括注：整段中文，括号里不再嵌括号
PAREN = re.compile(r'（([^（）]{6,})）')
# 校注开头的常见说法——这类括注是对拉丁文用词的说明，不是整节重译，必须留着
# 经文重译里常嵌一个〔或作：…〕小注，判「是不是校注」之前要先摘掉
SUB_NOTE = re.compile(r'[〔\[［][^〕\]］]*[〕\]］]')
# 出现这些字样的括注是对拉丁文用词的说明，不是整节重译，必须留着
META = re.compile(r'或作|或译|译作|可译|直译|字面|本义|字义|意即|原文|按字|希伯来|拉丁文|法文|英文|'
                  r'另有人|有些人|有人译|别人译|此译|亦作|即指|注：|参见|字母|拘泥|容后|见下文')
# 括注与「附近那节中文」的字面相似度下限。整节重译即便用词与和合本差得远
# （俄巴底亚书 5 只有 0.23），也比「校注」「配错了节」高；实测 0.13 以下全是
# 配错节或校注，取 0.18 作闸。
MIN_SIM = 0.18
# 希伯来文（teal）/希腊文（蓝）行内 span
SCRIPT_SPAN = re.compile(r'color:#(?:008080|0000d4)')
WINDOW = 8


def _plain(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s)


def _cjk(s: str) -> str:
    return ''.join(CJK.findall(s))


def _zh_verse_text(lines, i, verse: str) -> str:
    """前后 WINDOW 行里，找「**N.** + 汉字」那一节的中文正文。"""
    pat = re.compile(r'(?:\*\*|<strong>)' + re.escape(verse) + r'[.．](?:\*\*|</strong>)?\s*'
                     r'(?:<[^>]+>\s*)*([一-鿿][^\n]{0,200})')
    for j in range(max(0, i - WINDOW), min(len(lines), i + WINDOW + 1)):
        seg = lines[j]
        if j == i:
            # 本行里同节的中文只可能出现在括注之外（比如「拉丁…（中文）：**N.** 中文」）
            seg = PAREN.sub('', seg)
        m = pat.search(seg)
        if m:
            return m.group(1)
    return ''


def fix_file(path: Path, apply: bool):
    lines = path.read_text(encoding='utf-8').split('\n')
    changed, skipped = [], []
    for i, line in enumerate(lines):
        if '<td' in line or line.lstrip().startswith('[^'):
            continue
        m = VERSE_LINE.match(line)
        if not m:
            continue
        new = line
        for pm in list(PAREN.finditer(line)):
            # 一行里可能塞着好几节（`**3.** 拉丁（中文）4. 拉丁（中文）`），
            # 括注归属于它前面最近的那个节号，不是整行开头那个
            before_all = _plain(line[:pm.start()])
            nums = re.findall(r'(?:^|[\s>）)])(\d{1,3})[.．]', before_all)
            verse = nums[-1] if nums else m.group(1)
            inner = pm.group(1)
            if len(CJK.findall(inner)) < 6:
                continue
            # 括注里可能嵌着〔或作：…〕这种小注（经文重译里很常见），先摘掉
            core = SUB_NOTE.sub('', _plain(inner))
            if len(CJK.findall(core)) < 20 or META.search(core):
                continue      # 「或作/译作/字面/原文」这类是校注，不是整节重译，留着
            # 括注里夹着希伯来文/希腊文，或方括号小注占了近一半篇幅的，不是单纯
            # 的重译，而是带着一整套考据（约珥书 1:10 那条里有 יבש/בוש 的辨析）。
            # 这些内容别处没有，删了就没了——留着。
            if SCRIPT_SPAN.search(inner):
                continue
            notes = sum(len(x) for x in SUB_NOTE.findall(_plain(inner)))
            if notes > 0.4 * len(_plain(inner)):
                continue
            # 括注之前、回溯到上一个节号为止的那一段，必须是拉丁文经文
            cut = max(before_all.rfind(f'{verse}.'), 0)
            seg = before_all[cut:]
            if len(re.findall(r'[A-Za-z]', seg)) < 30 or len(CJK.findall(seg)) > 2:
                continue
            zh = _zh_verse_text(lines, i, verse)
            if not zh:
                skipped.append((verse, inner[:24]))
                continue
            sim = difflib.SequenceMatcher(None, _cjk(zh), _cjk(core)).ratio()
            if sim < MIN_SIM:
                skipped.append((verse, f'与中文经文只有 {sim:.2f} 相似度：{inner[:20]}'))
                continue
            new = new.replace(pm.group(0), '', 1)
        if new != line:
            new = re.sub(r'[ \t]{2,}', ' ', new).rstrip()
            changed.append((line, new))
            lines[i] = new
    if changed:
        print(f'  {path}: 删 {len(changed)} 处括注')
        for old, _ in changed:
            print(f'      {_plain(old)[:40]}… ⟶ 去掉 {PAREN.findall(old)[0][:26]}…')
    for v, s in skipped:
        print(f'  !! {path}: 第 {v} 节附近找不到中文经文，保留括注「{s}…」')
    if changed and apply:
        mode = path.stat().st_mode & 0o777
        if not mode & 0o200:
            path.chmod(0o644)
            path.write_text('\n'.join(lines), encoding='utf-8')
            path.chmod(mode)
        else:
            path.write_text('\n'.join(lines), encoding='utf-8')
    return len(changed)


# 阿摩司书 5:7 是个例外：那一格里英文经文压根没译，译者把整节中文塞进了拉丁文
# 后面的括注。删括注会让这一节连中文都没有，所以按本书通例（`N. 中文 N. 拉丁`）
# 重排——英文那半截换成括注里的中文。
SPECIAL = [(
    'amos', '5',
    '<strong>7.</strong> Ye who turn judgment to wormwood, and leave off righteousness in '
    'the earth. <strong>7.</strong> Qui convertunt in absynthium judicium, et justitiam in '
    'terra dimittunt.（他们使公平变为苦艾，将公义丢弃于地。）',
    '<strong>7.</strong> 他们使公平变为苦艾，将公义丢弃于地。<strong>7.</strong> Qui '
    'convertunt in absynthium judicium, et justitiam in terra dimittunt.',
)]


def apply_special(apply: bool) -> int:
    n = 0
    for book, chapter, old, new in SPECIAL:
        for path in (ROOT / f'calvin/{book}/{chapter}.md',
                     ROOT / f'calvin_raw/{book}/zh_chapters/{chapter}.md'):
            if not path.exists():
                continue
            text = path.read_text(encoding='utf-8')
            if old not in text:
                continue
            print(f'  {path}: 第 7 节按本书通例重排（英文未译那半截换成中文）')
            n += 1
            if apply:
                mode = path.stat().st_mode & 0o777
                if not mode & 0o200:
                    path.chmod(0o644)
                    path.write_text(text.replace(old, new), encoding='utf-8')
                    path.chmod(mode)
                else:
                    path.write_text(text.replace(old, new), encoding='utf-8')
    return n


def main() -> int:
    apply = '--apply' in sys.argv
    targets = [p for p in sorted(list(ROOT.glob('calvin/*/*.md'))
                                 + list(ROOT.glob('calvin_raw/*/zh_chapters/*.md')))
               if not p.parent.name.endswith('-en')]
    total = sum(fix_file(p, apply) for p in targets)
    total += apply_special(apply)
    print(f'[{"applied" if apply else "dry-run"}] {total} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
