#!/usr/bin/env python3
"""经文框体检：一条命令把所有已知毛病查一遍，只报告不修改。

写这个脚本的由头：同一类毛病连着三轮没修干净，每次都是「只认得出一种写法」——
节号只认 `**5.**` 漏了裸 `5.`、只扫段落漏了表格单元格、括注门槛卡在 20 字漏了
短节。修完一处就以为这一类结了，结果用户又截图回来。

所以把判据集中到这里，按「页面上看得见的形态」查，不依赖某个修复脚本的内部规则。
改完任何一处产物，跑一次这个脚本；全零才算这一类真的清了。

    python3 scripts/audit_scripture_boxes.py [目录…]     # 默认全 calvin/
"""
import difflib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOX = re.compile(r'<div class="scripture-box[^"]*"[^>]*>.*?\n</div>', re.S)
REF = re.compile(r'class="verse-range">([^<]+)<')
ROW = re.compile(r'<tr><td class="scripture-en">(.*?)</td>'
                 r'<td class="scripture-la">(.*?)</td></tr>', re.S)
CELL = re.compile(r'<td class="scripture-(?:en|la)">(.*?)</td>', re.S)
PARA = re.compile(r'<p[^>]*>', re.S)
NUM = re.compile(r'^\s*(?:<strong>|\*\*)?(\d{1,3})[.．]')
VNUM = re.compile(r'(?<![\dA-Za-z])(\d{1,3})\s*[.．](?=\s|\*|$)')
PAREN = re.compile(r'（([^（）]{6,})）')
CJK = re.compile(r'[一-鿿]')
COMMENTARY = re.compile(r'(?:\*\*|<strong>)\d{1,3}[.．](?:\*\*|</strong>)?\s*'
                        r'<span style="color:#800000">\s*\*')
MD = re.compile(r'\*\*|(?<![*\w])\*[^*\n]+?\*(?![*\w])|\[\^')
SUB_NOTE = re.compile(r'[〔\[［][^〕\]］]*[〕\]］]')
META = re.compile(r'或作|或译|译作|可译|直译|字面|本义|字义|意即|原文|按字|希伯来|拉丁文|法文|英文|'
                  r'另有人|有些人|有人译|别人译|此译|亦作|即指|注：|参见|字母|拘泥|容后|见下文|'
                  r'当解作|解作|疏解|语助词|连接词|当读作|当译作|此句当|不定式|集合名词|此处作|推测|或可省略|我如此翻译|关系代词')


def plain(s: str) -> str:
    return re.sub(r'\*', '', re.sub(r'<[^>]+>', ' ', s))


def expand(rng: str) -> set:
    rng = rng.split(':')[-1].strip()
    out = set()
    for part in re.split(r'[,，]', rng):
        part = part.strip().replace('—', '-').replace('–', '-')
        m = re.fullmatch(r'(\d+)\s*-\s*(\d+)', part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if b >= a and b - a < 200:
                out |= {str(x) for x in range(a, b + 1)}
        elif part.isdigit():
            out.add(part)
    return out


C_SPILL = '框头节号没被框内覆盖（经文就在框外）'
C_PARALLEL = '框后另起一张 parallel 表（版式不同，内容在）'
C_MIXED = '框内既有表格又有段落（排版不一致）'
C_COMMENT = '注释段落混进框里'
C_GLOSS = '拉丁文后面跟着整节中文括注'
C_ROWNUM = '双语表左右两列节号对不上'
C_MD = '单元格里残留 markdown 记号'
C_BLOCK = '单元格里混进块级标签'
CHECKS = [C_SPILL, C_MIXED, C_COMMENT, C_GLOSS, C_ROWNUM, C_MD, C_BLOCK]
INFO = [C_PARALLEL]      # 版式不同但内容在，只报告不计入


def audit(paths):
    found = {k: [] for k in CHECKS + INFO}
    for p in paths:
        text = p.read_text(encoding='utf-8')
        if 'scripture-box' not in text:
            continue
        zh = not p.parent.name.endswith('-en')
        for m in BOX.finditer(text):
            box = m.group(0)
            ref = REF.search(box)
            body = box.split('</table>', 1)[-1] if '</table>' in box else box
            rng = ref.group(1) if ref else '?'

            if ref:
                want = expand(ref.group(1))
                got = set(VNUM.findall(plain(box)))
                miss = sorted(want - got, key=int)
                if want and miss:
                    # 只看框后**第一块**：往后扫一大片会把注释里引用的节号也算进来
                    # （诗篇 26/68/138 的注释头「8. 耶和华啊，我喜爱……」就被误报过）
                    nxt = ''
                    for blk in text[m.end():m.end() + 4000].split('\n\n'):
                        b = blk.strip()
                        if not b or b.startswith('<!--') or 'commentary-anchor' in b[:60]:
                            continue
                        nxt = b
                        break
                    hit = [v for v in miss
                           if re.search(rf'(?<![\dA-Za-z]){v}[.．]', plain(nxt))]
                    if hit and nxt.startswith('<table'):
                        found[C_PARALLEL].append(f'{p} [{rng}] 缺 {miss[:6]}')
                    elif hit and not COMMENTARY.search(nxt) and '……' not in nxt[:80]:
                        found[C_SPILL].append(f'{p} [{rng}] 缺 {miss[:6]}')

            # 隐藏的脚注桩 `<p class="scripture-fnref-stub" style="display:none">`
            # 不算版式不一致（它压根不渲染）
            visible = re.sub(r'<p class="scripture-fnref-stub".*?</p>', '', body, flags=re.S)
            if '<table' in box and PARA.search(visible):
                found[C_MIXED].append(f'{p} [{rng}]')

            if COMMENTARY.search(box):
                found[C_COMMENT].append(f'{p} [{rng}]')

            # 拉丁文后的中文括注——段落与单元格一起查。判「是不是重复」不靠词表，
            # 靠「框里本来就有这一节的中文，且与括注字面相似」：校注天然不相似。
            zh_all = ''.join(CJK.findall(re.sub(r'（[^（）]*）', '', plain(box))))
            for chunk in [box] if '<td' not in box else CELL.findall(box):
                for pm in PAREN.finditer(chunk):
                    core = SUB_NOTE.sub('', re.sub(r'<[^>]+>', '', pm.group(1)))
                    if len(CJK.findall(core)) < 8:
                        continue
                    before = re.sub(r'<[^>]+>', '', chunk[:pm.start()])
                    if len(re.findall(r'[A-Za-z]', before[-40:])) < 10:
                        continue
                    if CJK.search(before[-25:]):
                        continue
                    # 「或译/原文作」这类括注是校注——哪怕它同时把整节重译了一遍，
                    # 也连着校注一起留（见 fix_latin_zh_gloss.py 的同名判据）
                    if META.search(core):
                        continue
                    hay = ''.join(CJK.findall(core))
                    sim = max((difflib.SequenceMatcher(None, zh_all[i:i + 3 * len(hay)], hay).ratio()
                               for i in range(0, max(1, len(zh_all)), max(1, len(hay) // 2))),
                              default=0)
                    if sim < 0.3:
                        continue
                    found[C_GLOSS].append(f'{p} [{rng}] {core[:24]}… (sim {sim:.2f})')

            for a, b in ROW.findall(box):
                na, nb = NUM.match(plain(a).strip()), NUM.match(plain(b).strip())
                if na and nb and na.group(1) != nb.group(1):
                    found[C_ROWNUM].append(f'{p} [{rng}] {na.group(1)}≠{nb.group(1)}')

            for cell in CELL.findall(box):
                if MD.search(cell):
                    found[C_MD].append(f'{p} [{rng}]')
                if 'commentary-anchor' in cell or '</p>' in cell or '<div' in cell:
                    found[C_BLOCK].append(f'{p} [{rng}]')
    return found


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    dirs = [Path(a) for a in args] or [ROOT / 'calvin']
    paths = []
    for d in dirs:
        paths += sorted(d.glob('*/*.md') if d.name in ('calvin',) else d.glob('*.md'))
    found = audit(paths)
    bad = 0
    for k in CHECKS + INFO:
        v = found[k]
        print(f'{"✔" if not v else ("ℹ" if k in INFO else "✗")} {k}: {len(v)}')
        for x in v[:5]:
            print(f'    {x}')
        if len(v) > 5:
            print(f'    …另有 {len(v) - 5} 处')
        if k in CHECKS:
            bad += len(v)
    print(f'\n共 {bad} 处' + ('（全清）' if not bad else ''))
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
