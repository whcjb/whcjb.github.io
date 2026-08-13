#!/usr/bin/env python3
"""把 psalms-1 的脚注还原成标准的「正文 [^faN] + 章末 [^faN]: 定义」结构。

背景：AGES PDF 正文用 superscript span 标脚注（faN/fbN/fcN），定义集中在卷末
FOOTNOTES 附录（ftaN/ftbN/ftcN）。提取时 superscript span 被丢掉，附录又被
末章 ch78 整个吞进去，结果是正文 0 个引用、附录 1552 条无主定义。

本脚本只动英文版：
  A. 解析 footnotes.md → {code: 定义正文}
  B. 从 PDF 取每个 marker 及其前文上下文
  C. 按上下文把 [^faN] 插回英文章节，并把定义追加到该章末尾
不碰中文版——往正文插标记会改变段落文本，md5 缓存键全变，整卷要重翻。

用法:
    python3 scripts/psalms_footnotes_restore.py parse      # 阶段 A，输出统计
    python3 scripts/psalms_footnotes_restore.py markers    # 阶段 B
    python3 scripts/psalms_footnotes_restore.py apply [--dry-run]
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VOL = '2' if '--vol' in sys.argv and sys.argv[sys.argv.index('--vol') + 1] == '2' else '1'
EN = ROOT / f'calvin/psalms-{VOL}-en'
PDF = f'/Users/yanpeifa/Documents/论文/calvin/CAL_PSA{VOL}.pdf'
WORK = ROOT / f'calvin_raw/psalms-{VOL}'
CODE_SPAN = re.compile(r'<span style="color:#800000">(ft[a-z]\d+[A-Za-z]?)</span>')


def parse_appendix():
    """footnotes.md → {code: text}"""
    body = (EN / 'footnotes.md').read_text(encoding='utf-8').split('---\n', 2)[2]
    body = re.sub(r'<!-- PAGE \d+ -->', '', body)
    hits = list(CODE_SPAN.finditer(body))
    out = {}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(body)
        text = body[m.end():end]
        # 附录里的分节标题（<p class="title-block-h1|h2">PSALM N</p>）不属于脚注正文，
        # 遇到就截断；而跨页折行产生的 <p style="text-align:center"> 包裹要脱掉标签
        # 保留文字——那是同一条脚注被版式切开的下半截。
        # 除分节标题外，附录里穿插的经文锚点 h2 同样不属于脚注正文
        cut = re.search(r'<p class="title-block-h[12]"|<h2 class="scripture-anchor"', text)
        if cut:
            text = text[:cut.start()]
        text = re.sub(r'</?p\b[^>]*>', ' ', text)
        text = re.sub(r'\n\s*\n', ' ', text)          # 跨页断开的定义并回一段
        text = re.sub(r'\s+', ' ', text).strip()
        if text:
            out[m.group(1)] = text
    return out


def body_markers():
    """PDF → [{code, chapter_hint, context}]，context 为 marker 之前的正文片段"""
    import fitz
    doc = fitz.open(PDF)
    marks, buf, psalm = [], '', None
    for page in doc:
        for b in page.get_text('dict')['blocks']:
            if b['type']:
                continue
            for line in b['lines']:
                for s in line['spans']:
                    t = s['text']
                    if s['flags'] & 1:                 # superscript
                        # 上标 span 常把紧跟的标点一起吸进来（' fd43.'），
                        # 只匹配纯代码会漏掉 57 条；标点要还回正文缓冲。
                        m = re.fullmatch(r'\s*(f[a-z]\d+[A-Za-z]?)\s*([.,;:!?\'"]*)\s*', t)
                        if m:
                            marks.append({'code': m.group(1), 'psalm': psalm,
                                          'context': norm(buf)[-70:]})
                            if m.group(2):
                                buf = (buf + m.group(2))[-400:]
                            continue
                        a = re.fullmatch(r'\s*<(\d{6})>\s*', t)
                        if a:                          # AGES 经节锚点 → 判断当前诗篇
                            psalm = int(a.group(1)[2:5])
                            continue
                    buf = (buf + ' ' + t)[-400:]
    return marks


def norm(s):
    """归一化：去标记、统一引号、压空白 —— PDF 与发布 md 两侧用同一套"""
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\[\^[^\]]+\]', ' ', s)
    s = s.replace('*', ' ').replace('_', ' ')
    s = s.translate(str.maketrans('“”‘’—–', '""\'\'--'))
    return re.sub(r'[^A-Za-z0-9\'",.;:!?()-]+', '', s)


def projection(md_body):
    """归一化正文 + 偏移映射：norm_text[i] 对应 md_body[idx_map[i]]"""
    out, idx = [], []
    i, n = 0, len(md_body)
    while i < n:
        c = md_body[i]
        if c == '<':                                   # 跳过 HTML 标签 / 注释
            j = md_body.find('>', i)
            i = n if j < 0 else j + 1
            continue
        if c == '[' and md_body.startswith('[^', i):   # 跳过已有脚注标记
            j = md_body.find(']', i)
            i = n if j < 0 else j + 1
            continue
        if c in '*_':
            i += 1
            continue
        c = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-'}.get(c, c)
        # 全部去掉空白后再比对：PDF 侧 span 边界会凭空多出空格（"season ," vs
        # "season,"），保留空白会让大量上下文匹配不上。
        if re.match(r"[A-Za-z0-9'\",.;:!?()-]", c):
            out.append(c)
            idx.append(i)
        i += 1
    return ''.join(out), idx


def locate(ctx, chapters, whole=False):
    """在候选章节里找 ctx 的唯一出现；逐步缩短上下文提高召回。
    whole=True 时整串匹配、不缩窗（lemma 定位用，宁可漏不可错）。
    返回 (chapter_key, md_offset) 或 None。"""
    if whole:
        if len(ctx) < 12:
            return None
        hits = []
        for key, (norm_text, idx_map, _) in chapters.items():
            start = 0
            while True:
                p = norm_text.find(ctx, start)
                if p < 0:
                    break
                hits.append((key, idx_map[p + len(ctx) - 1] + 1))
                start = p + 1
                if len(hits) > 1:
                    return None
        return hits[0] if len(hits) == 1 else None
    variants = [ctx, re.sub(r'\d+', '', ctx)]      # 变体二：去掉混进来的页码数字
    for length in (60, 45, 32, 24):
      for v in variants:
        probe = v[-length:]
        if len(probe) < 16:
            continue
        hits = []
        for key, (norm_text, idx_map, _) in chapters.items():
            start = 0
            while True:
                p = norm_text.find(probe, start)
                if p < 0:
                    break
                hits.append((key, idx_map[p + len(probe) - 1] + 1))
                start = p + 1
                if len(hits) > 1:
                    break
            if len(hits) > 1:
                break
        if len(hits) == 1:
            return hits[0]
    return None


def lemma_of(text):
    """脚注定义开头重复的被注释词句。取不到就返回 None（宁可不落位）。"""
    t = re.sub(r'<[^>]+>', '', text).strip()
    m = re.match(r'[“"\'‘]?\s*\*([^*]{10,90}?)\*', t)      # 开头的斜体短语
    if m:
        return m.group(1).strip(' .,;:')
    m = re.match(r'[“"]([^”"]{14,90})[”"]', t)              # 开头的整句引语
    if m:
        return m.group(1).strip(' .,;:')
    return None


def apply(dry=True):
    defs = json.loads((WORK / 'footnote_defs.json').read_text(encoding='utf-8'))
    marks = json.loads((WORK / 'footnote_marks.json').read_text(encoding='utf-8'))

    # 第一轮：正文里还留着的死标记 span 直接转成脚注引用——位置是源头给的，
    # 不需要猜。ch72-78 等 9 章出自另一代流程，标记没被清掉。
    #
    # 必须在建 projection 之前做：ch17 这类章既有死标记、又有要靠上下文插入的
    # code，若先算偏移再做转换，`[^fa1]` 比原 span 短，后面所有偏移全部错位。
    LIVE = re.compile(r'<span style="color:#800000">(f[a-z]\d+[A-Za-z]?)</span>')
    chapters, converted, have = {}, {}, set()
    for p in sorted(EN.glob('*.md')):
        if p.stem == 'footnotes':
            continue
        text = p.read_text(encoding='utf-8')
        fm, body = re.match(r'(---\n.*?\n---\n)(.*)$', text, re.S).groups()
        found = [c for c in LIVE.findall(body) if 'ft' + c[1:] in defs]
        if found:
            # 只转换在附录里查得到定义的码。卷二有约 50 个死标记（fe49 等）
            # 附录里根本没有对应条目，转了就会变成没有定义的孤儿引用，
            # kramdown 会把 [^fe49] 原样吐在正文里。这类保持原状不动。
            keep = set(found)
            body = LIVE.sub(
                lambda m: f'[^{m.group(1)}]' if m.group(1) in keep else m.group(0), body)
            converted[p.stem] = found
            have.update(found)
        norm_text, idx_map = projection(body)
        chapters[p.stem] = (norm_text, idx_map, [fm, body])
    n_conv = sum(len(v) for v in converted.values())

    # 已经落位过的 code（重复运行时不要再插一遍）
    for key, (_, _, pair) in chapters.items():
        have.update(re.findall(r'\[\^([a-z]{1,3}\d+[A-Za-z]?)\]', pair[1]))

    # 第二轮：其余 code 靠 PDF 上下文定位插入
    placed, unmatched, nodef = [], [], []
    inserts = {}                                        # key -> [(offset, code, defkey)]
    for mk in marks:
        code = mk['code']
        defkey = 'ft' + code[1:]
        if code in have:                                # 已由第一轮精确落位
            continue
        if defkey not in defs:
            nodef.append(code)
            continue
        hit = locate(mk['context'], chapters)
        if not hit:
            unmatched.append(code)
            continue
        key, off = hit
        inserts.setdefault(key, []).append((off, code, defkey))
        placed.append(code)

    # 第三轮：PDF 里压根没有 marker 的条目，靠定义开头引用的经文短语（lemma）定位。
    # AGES 的脚注惯例是先重复被注释的词句再作注，如
    #   ftc601: “*They shall still bring forth fruit in old age*. Being thus planted…”
    # 该短语在正文中唯一出现时才插，插在短语之后。
    lemma_placed = []
    for code, text in defs.items():
        body_code = 'f' + code[2:]
        if body_code in have:
            continue
        lem = lemma_of(text)
        if not lem:
            continue
        hit = locate(norm(lem), chapters, whole=True)
        if not hit:
            continue
        key, off = hit
        inserts.setdefault(key, []).append((off, body_code, code))
        have.add(body_code)
        lemma_placed.append(body_code)

    print(f'死标记直接转换 {n_conv} 处（{len(converted)} 章）')
    print(f'按定义 lemma 定位 {len(lemma_placed)} 条')

    print(f'定位成功 {len(placed)} / {len(marks)}  '
          f'(上下文匹配失败 {len(unmatched)}, 附录无定义 {len(nodef)})')
    print('  分布:', {k: len(v) for k, v in sorted(inserts.items(), key=lambda x: len(x[1]), reverse=True)[:8]})
    if unmatched[:6]:
        print('  匹配失败示例:', unmatched[:6])
    if nodef[:6]:
        print('  无定义示例:', nodef[:6])
    if dry:
        return

    touched = set(inserts) | set(converted)
    used = set()
    for key in sorted(touched):
        fm, body = chapters[key][2]
        # 死标记转换已直接改在 body 上；上下文插入按偏移从后往前做。
        # 注意：偏移是基于转换前的 body 算的，所以只有"无死标记"的章会走到这里。
        for off, code, defkey in sorted(inserts.get(key, []), reverse=True):
            body = body[:off] + f'[^{code}]' + body[off:]
        codes = [c for _, c, _ in inserts.get(key, [])] + converted.get(key, [])
        already = set(re.findall(r'^\[\^([a-z]{1,3}\d+[A-Za-z]?)\]:', body, re.M))
        codes = sorted(set(codes) - already, key=lambda c: (c[:2], int(re.sub(r'\D', '', c) or 0)))
        if not codes:
            continue
        used.update(codes)
        tail = '\n\n' + '\n\n'.join(f'[^{c}]: {defs["ft" + c[1:]]}' for c in codes)
        (EN / f'{key}.md').write_text(fm + body.rstrip() + tail + '\n', encoding='utf-8')
    print(f'已写入 {len(touched)} 个章节文件，落位脚注 {len(used)} 条')

    # 附录页只保留没能落位的条目，避免与章末定义重复
    final_placed = set()
    for p in EN.glob('*.md'):
        if p.stem == 'footnotes':
            continue
        final_placed.update(re.findall(r'^\[\^([a-z]{1,3}\d+[A-Za-z]?)\]:',
                                       p.read_text(encoding='utf-8'), re.M))
    leftover = {k: v for k, v in defs.items() if 'f' + k[2:] not in final_placed}
    fn = EN / 'footnotes.md'
    head = fn.read_text(encoding='utf-8').split('---\n', 2)[1]
    note = ('\n<p><em>本页只保留未能定位到具体章节的脚注条目；其余 '
            f'{len(used)} 条已随文归入各章末尾。</em></p>\n\n')
    entries = '\n\n'.join(f'**{k}** {v}' for k, v in leftover.items())
    fn.write_text(f'---\n{head}---\n{note}{entries}\n', encoding='utf-8')
    print(f'附录页保留未落位条目 {len(leftover)} 条')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'parse'
    WORK.mkdir(parents=True, exist_ok=True)

    if cmd == 'parse':
        defs = parse_appendix()
        (WORK / 'footnote_defs.json').write_text(
            json.dumps(defs, ensure_ascii=False, indent=1), encoding='utf-8')
        lens = sorted(len(v) for v in defs.values())
        print(f'解析出 {len(defs)} 条定义')
        print(f'  长度中位数 {lens[len(lens)//2]}，最短 {lens[0]}，最长 {lens[-1]}')
        for k in list(defs)[:3]:
            print(f'  {k}: {defs[k][:90]}')

    elif cmd == 'markers':
        marks = body_markers()
        (WORK / 'footnote_marks.json').write_text(
            json.dumps(marks, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'PDF 中取到 {len(marks)} 个 marker')
        no_ctx = sum(1 for m in marks if len(m['context']) < 20)
        print(f'  上下文过短的: {no_ctx}')
        for m in marks[:3]:
            print(f"  {m['code']} (psalm {m['psalm']}): ...{m['context'][-60:]}")

    elif cmd == 'apply':
        apply(dry='--dry-run' in sys.argv)
