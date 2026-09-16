#!/usr/bin/env python3
"""把掉在经文框外面的经文后半截接回框里（中英两侧一起修）。

AGES PDF 的经文框常被 PyMuPDF 按行组切成两块（框内文字跨了两个 block）。
`structured_to_md.py` 旧版只把第一块收进 `<div class="scripture-box">`，
第二块就当成普通段落 emit 在 `</div>` 后面——页面上看到的是：经文框在句子
中间被切断，剩下的半句连同后面几节裸露在框外。诗篇 69:1-5 是典型：

    <div class="scripture-box" markdown="1">
    …我到了深水中，大水
    </div>

    水淹没了我。3. 我因呼求困乏…5. …我的罪愆不能隐瞒。

生成器（structured_to_md.py）已修；本脚本负责把既有产物补回来。中文那边
`publish_psalms_zh.py` 每次发布都会从只读的 zh_chapters 重新生成，raw 里是
坏的，所以发布脚本末尾会调本脚本补一遍。

要修哪些框由下面的 SPLIT_BOXES 表指定，不现场判——判据只在「还没修」的产物
上成立，修完信号就消失；先前用「英文版框是不是断的」当判据，结果重新发布一次
中文就把修好的页面又打回了原形。`--scan` 用启发式普查候选，供人工核过入表。

用法：
    python3 scripts/fix_split_scripture_box.py --book psalms-1 \
        --en calvin/psalms-1-en --zh calvin/psalms-1 [--apply]
    python3 scripts/fix_split_scripture_box.py --scan \
        --en calvin/psalms-1-en --zh calvin/psalms-1     # 普查候选，不改文件
"""
import re
import sys
from pathlib import Path

BOX_OPEN = re.compile(r'^<div class="scripture-box')
COMMENTARY_START = re.compile(r'^(\*\*|<|#|\[\^|-{3}|\{|\|)')
VERSE_ANCHOR = re.compile(r'(?:^|[\s；。，,;:])\d+\s*\.\s')
VERSE_NUM = re.compile(r'(?:^|[\s>*，。；：])(\d{1,3})\s*[.．]')

# 被切断的框清单：{书 → {篇号: {框序号, …}}}，序号 = 该章第几个 scripture-box（从 0 数）。
# 一次性普查的结果，逐条对过英文版与中文版的接缝。两卷的切断成因还不一样：
#   · psalms-1：structured 原文里经文段跨两个 BODY（提取阶段被 PyMuPDF 切开）
#   · psalms-2：框是另一个转换器（psalms2_scripture_boxes.py）按空行收的，
#     空行落在经文中间就切断，与 structured 的切点不是一回事
# 新开书卷先用 --scan 普查，人工核过再往表里加。
SPLIT_BOXES = {
    'psalms-1': {18: {9}, 19: {0}, 26: {2}, 31: {2, 4}, 33: {1, 5}, 38: {1},
                 40: {4}, 46: {1}, 49: {0}, 56: {0}, 69: {0}, 75: {0}, 78: {4}},
    'psalms-2': {80: {1}, 94: {0}, 97: {0}, 135: {4}, 146: {1}},
}

# 经文被切成两块时，译者偶尔把整节都译进了前一块，后一块又重译了一遍；直接合并
# 会出现重复句。这里按「英文版对应处只出现一次」的事实，列出续接段开头要删掉的
# 重复文字。key = (书, 篇号, 框序号)；只作用于中文侧，对不上就报警并原样合并。
# key = (目录名, 章文件名 stem, 框序号)；值是要从续接块开头删掉的字符串，
# 或 (删掉的字符串, 换成什么)。对不上就报警并原样合并。
JUNCTION_DEDUP = {
    ('psalms-1', '46', 1): '其中的水翻腾',            # 前块已译「其中的水虽砰訇翻腾」
    ('psalms-1', '49', 0): '无论贫贱富足，都当留心听。',   # 前块已译「无论上流下流…都当留心听」
    ('psalms-1', '69', 0): '水',                     # 前块末尾已是「大水」
    ('psalms-2', '135', 4): '口中也没有气息。 ',        # 前块已译「口中也没有气息」
    # 前块是加尔文的译法「保护你右手所栽的，并那枝子」，后块又照和合本把
    # 第 15 节整节重译了一遍；去掉重复的前半，留下续接的后半
    ('psalms-2', '80', 3): ('保护你右手所栽的和', '，'),
}


def _dedup(para, key):
    rule = JUNCTION_DEDUP.get(key)
    if not rule:
        return para, None
    strip, repl = rule if isinstance(rule, tuple) else (rule, '')
    if not para.startswith(strip):
        return para, f'去重串对不上：{para[:30]}'
    return repl + para[len(strip):].lstrip(), None


def _tail_plain(line: str) -> str:
    """剥掉尾部 HTML 闭标签与 `[^fN]` 脚注标记，得到用于判句末的纯文本。"""
    t = line.rstrip()
    prev = None
    while prev != t:
        prev = t
        t = re.sub(r'(?:</?[a-zA-Z][^>]*>)+$', '', t).rstrip()
        t = re.sub(r'\[\^[A-Za-z0-9]+\]$', '', t).rstrip()
    return t


def _is_sentence_end(line: str) -> bool:
    t = _tail_plain(line)
    return not t or t[-1] in '.?!:;"”’\')。！？；：」』…'


def _append_inside(line: str, text: str, glue: str) -> str:
    """把 text 接到 line 末尾；若 line 以块级闭合标签 `</p>` 收尾，接在它里面。

    只认 `</p>`：行内标签不能钻进去——john-en/18 的经文行以
    `<span style="color:#800000">F466</span>` 收尾，接进 span 里的话，后面
    整节经文都会变成红色脚注标记的一部分。"""
    m = re.search(r'(</p>)\s*$', line.rstrip())
    if m:
        return line.rstrip()[:m.start(1)].rstrip() + glue + text + m.group(1)
    return line.rstrip() + glue + text


def scan_boxes(lines):
    """产出 [(框序号, </div> 行号, 框内最后一行行号, 框外下一段行号), …]。"""
    res = []
    ordinal = -1
    in_box = False
    for i, line in enumerate(lines):
        s = line.strip()
        if BOX_OPEN.match(s):
            in_box = True
            ordinal += 1
        elif in_box and s == '</div>':
            in_box = False
            j = i - 1
            while j >= 0 and not lines[j].strip():
                j -= 1
            k = i + 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            res.append((ordinal, i, j, k if k < len(lines) else -1))
    return res


def merge(path: Path, ordinals, apply: bool, dedup_key=None):
    """把指定序号的框后面那一段并回框内。返回合并处数。"""
    if not ordinals or not path.exists():
        return 0
    lines = path.read_text(encoding='utf-8').split('\n')
    plan = []
    for ordinal, div_i, last_i, next_i in scan_boxes(lines):
        if ordinal not in ordinals or last_i < 0 or next_i < 0:
            continue
        if lines[last_i].lstrip().startswith('<p class="scripture-ref"'):
            continue
        para = lines[next_i].strip()
        if COMMENTARY_START.match(para):
            # 已经合并过（或该框根本没断）→ 幂等跳过，不报警
            continue
        para, warn = _dedup(para, (path.parent.name, path.stem, ordinal))
        if warn:
            print(f'  !! {path} 框 #{ordinal}: {warn}，原样合并')
        plan.append((last_i, next_i, para))
    if not plan:
        return 0
    drop = set()
    for last_i, next_i, para in plan:
        glue = '' if re.search(r'[一-鿿，。；：！？]$', _tail_plain(lines[last_i])) else ' '
        print(f'  {path}: …{_tail_plain(lines[last_i])[-30:]} ⟵ {para[:30]}…')
        lines[last_i] = _append_inside(lines[last_i], para, glue)
        drop.add(next_i)
    if apply:
        out = [l for n, l in enumerate(lines) if n not in drop]
        path.write_text(re.sub(r'\n{3,}', '\n\n', '\n'.join(out)), encoding='utf-8')
    return len(plan)


# ── 覆盖判据（--sweep）：框头写的节号范围 vs 框里实际有的节号 ────────
#
# 表驱动那套只适用于「句子被切在中间、节号一个不少」的形态。更常见的一种是
# 框里干脆少了后面几节（psalms-2 的框是按空行收的，空行落在第几节就断在第几
# 节；诗篇 108 甚至整整 13 节全在框外）。这种可以自证：框头 banner 上写着
# `100:1-3`，框里却一个节号都没有，而紧跟框外那段正好有——判据在「修好之后」
# 自动失效、在「重新发布又被打回原形」之后自动复现，所以可以每次发布都跑。
REF_RANGE = re.compile(r'class="verse-range">([^<]+)<')
VERSE_MARK = re.compile(r'(?<![\dA-Za-z])(\d{1,3})\s*[.．](?=\s|\*|$)')
# 注释段的形态：粗体节号 + 红色斜体经文短语（中英一致）
COMMENTARY_HEAD = re.compile(
    r'^(?:\*\*|<strong>)?\d{1,3}[.．]?(?:\*\*|</strong>)?\s*'
    r'(?:<span style="color:#800000"|\*<span|<em|\*[^*])')
# `<table` 必须在列表里：律法合参那几章框后面紧跟的是另一种版式的
# `<table class="scripture-table calvin-parallel">`，不加的话会把表格的开
# 标签当成一块经文收进框里。
BLOCK_STOP = ('<h', '<div', '</div', '<table', '<!--', '---', '[^', '{:', '|')
MAX_PULL = 3        # 一个框最多往回收几块，防跑飞


def _expand_range(rng: str) -> set:
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


def _marks(text: str) -> set:
    return set(VERSE_MARK.findall(re.sub(r'<[^>]+>', ' ', text)))


def _plain(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()


def _starts_with_verse_num(text: str) -> bool:
    """这一块是不是以节号开头（`**1.**` / `<strong>1.</strong>` / `1.`）。

    要先剥掉外层 `<p …>` 壳再判——psalms-2/100 的经文块是
    `<p style="margin-left:2em;">**1.** 普天下当向耶和华欢呼…`，不剥就判成
    「不是节号开头」，于是被当成上一句的续接，接出了「称谢诗**1.** 普天下…」。"""
    s = re.sub(r'^\s*<p[^>]*>\s*', '', text.lstrip())
    s = re.sub(r'^(?:<[^>]+>\s*)*', '', s)
    return bool(re.match(r'^(?:\*\*)?\s*\d{1,3}\s*[.．]', s))


def sweep_file(path: Path, apply: bool) -> int:
    """按 banner 节号覆盖把框外的经文收回框内。返回处理的框数。"""
    lines = path.read_text(encoding='utf-8').split('\n')
    changed = 0
    # 从后往前做，行号不会因删除而失效
    for ordinal, div_i, last_i, next_i in reversed(scan_boxes(lines)):
        if last_i < 0:
            continue
        start = div_i
        while start >= 0 and not BOX_OPEN.match(lines[start].strip()):
            start -= 1
        box = '\n'.join(lines[start:div_i])
        mref = REF_RANGE.search(box)
        if not mref:
            continue
        want = _expand_range(mref.group(1))
        if not want:
            continue
        pulled = []
        k = next_i
        while want - _marks(box + '\n' + '\n'.join(pulled)) and len(pulled) < MAX_PULL:
            if k < 0 or k >= len(lines):
                break
            blk = lines[k].strip()
            if not blk or blk.startswith(BLOCK_STOP) or COMMENTARY_HEAD.match(blk):
                break
            missing = want - _marks(box + '\n' + '\n'.join(pulled))
            # 这一块得确实是接下来那几节：含缺的节号，或是上一块没写完的句子
            cont = (any(re.search(rf'(?<!\d){v}(?!\d)', blk) for v in missing)
                    or (not _is_sentence_end(pulled[-1] if pulled else lines[last_i])
                        and not _starts_with_verse_num(blk)))
            if not cont:
                break
            pulled.append(lines[k])
            k += 1
            while k < len(lines) and not lines[k].strip():
                k += 1
        if not pulled:
            continue
        changed += 1
        print(f'  {path} 框 #{ordinal} [{mref.group(1)}]: 收回 {len(pulled)} 块 '
              f'→ …{_plain(pulled[-1])[-28:]}')
        if apply:
            # 先删后插：被收的块整块搬进 </div> 之前
            body = []
            for blk in pulled:
                prev = body[-1] if body else lines[last_i]
                # 上一块没写完句子、这一块又不是以节号起头 → 同一句被切开，
                # 接回上一块（连 <p> 壳一起去掉：那层壳是 PDF 版式的痕迹，
                # 留着会让半句话居中、另半句不居中，同一个框里两种排版）
                if not _is_sentence_end(prev) and not _starts_with_verse_num(blk):
                    # 同一句被切开 → 接回上一块里面（去掉这一块的 <p> 壳）
                    txt = re.sub(r'^<p[^>]*>', '', blk.strip())
                    txt = re.sub(r'</p>\s*$', '', txt)
                    txt, warn = _dedup(txt.strip(), (path.parent.name, path.stem, ordinal))
                    if warn:
                        print(f'  !! {path} 框 #{ordinal}: {warn}，原样合并')
                    glue = '' if re.search(r'[一-鿿，。；：！？]$',
                                           _tail_plain(prev)) else ' '
                    merged = _append_inside(prev, txt.strip(), glue)
                    if body:
                        body[-1] = merged
                    else:
                        lines[last_i] = merged
                    continue
                body.append(blk)
            drop = set(range(next_i, k))
            new = []
            for n, l in enumerate(lines):
                if n in drop:
                    continue
                new.append(l)
                if n == last_i and body:
                    for blk in body:
                        new += ['', blk]
            lines = new
    if changed and apply:
        # 只写回，不做全文空行归一化——文末脚注定义之间本来就隔着两个空行，
        # 顺手 collapse 会把整章的空行全改一遍，diff 里真正的修改就淹了
        path.write_text('\n'.join(lines), encoding='utf-8')
    return changed


# ── 普查（--scan）：只报告候选，入表要人工核 ─────────────────────────
def _is_verse_continuation(para: str) -> bool:
    if COMMENTARY_START.match(para):
        return False
    if re.match(r'^[a-z,;:)\]]', para):      # 英文续接
        return True
    return bool(VERSE_ANCHOR.search(para))   # 含节号 → 经文，不是注释


def scan_en(path: Path):
    """英文版：框内最后一行没写完句子，框外下一段又是经文续接。"""
    lines = path.read_text(encoding='utf-8').split('\n')
    hit = set()
    for ordinal, div_i, last_i, next_i in scan_boxes(lines):
        if last_i < 0 or next_i < 0:
            continue
        if lines[last_i].lstrip().startswith('<p class="scripture-ref"'):
            continue
        if _is_sentence_end(lines[last_i]):
            continue
        if _is_verse_continuation(lines[next_i].strip()):
            hit.add(ordinal)
    return hit


def _verses(text: str) -> set:
    return set(VERSE_NUM.findall(re.sub(r'<[^>]+>', ' ', text)))


def _box_text(lines, div_i):
    chunk = []
    j = div_i - 1
    while j >= 0 and '<div class="scripture-box' not in lines[j]:
        chunk.append(lines[j])
        j -= 1
    return '\n'.join(chunk)


def scan_zh(en_path: Path, zh_path: Path):
    """中文版：同序号的框里缺了英文框有的节号，而框外那段正好有。"""
    if not zh_path.exists():
        return set()
    en_lines = en_path.read_text(encoding='utf-8').split('\n')
    zh_lines = zh_path.read_text(encoding='utf-8').split('\n')
    en_box = {o: _verses(_box_text(en_lines, d)) for o, d, _, _ in scan_boxes(en_lines)}
    hit = set()
    for ordinal, div_i, last_i, next_i in scan_boxes(zh_lines):
        if next_i < 0 or ordinal not in en_box:
            continue
        missing = en_box[ordinal] - _verses(_box_text(zh_lines, div_i))
        para = zh_lines[next_i].strip()
        if not missing or COMMENTARY_START.match(para):
            continue
        if any(re.search(rf'(?<!\d){v}(?!\d)', para) for v in missing):
            hit.add(ordinal)
    return hit


def main() -> int:
    argv = sys.argv[1:]
    apply = '--apply' in argv
    scan = '--scan' in argv
    def opt(name):
        i = argv.index(name)
        return [a for a in argv[i + 1:] if not a.startswith('--')]
    if '--sweep' in argv:
        total = 0
        for d in opt('--sweep'):
            p = Path(d)
            files = sorted(p.glob('*.md')) if p.is_dir() else [p]
            for f in files:
                total += sweep_file(f, apply)
        print(f'[{"applied" if apply else "dry-run"}] {total} 个框')
        return 0
    en_dir = Path(opt('--en')[0])
    zh_dirs = [Path(p) for p in opt('--zh')]
    if scan:
        for en in sorted(en_dir.glob('*.md')):
            cand = scan_en(en) | set().union(
                *[scan_zh(en, d / en.name) for d in zh_dirs]) if zh_dirs else scan_en(en)
            if cand:
                print(f'{en.stem}: {sorted(cand)}')
        return 0
    book = opt('--book')[0]
    table = SPLIT_BOXES.get(book)
    if not table:
        print(f'SPLIT_BOXES 里没有 {book}，先用 --scan 普查', file=sys.stderr)
        return 1
    total = 0
    for chapter, ordinals in sorted(table.items()):
        name = f'{chapter}.md'
        total += merge(en_dir / name, ordinals, apply)
        for d in zh_dirs:
            total += merge(d / name, ordinals, apply,
                           dedup_key=(book, chapter))
    print(f'[{"applied" if apply else "dry-run"}] {total} 处')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
