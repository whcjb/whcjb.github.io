#!/usr/bin/env python3
"""把 [^faN] 脚注引用插进**现有中译**，不重译任何正文。

背景：英文版脚注已还原，但多数中译章翻译时英文源里还没有标记，所以中文没有
脚注。曾经试过重跑整章翻译——那会让段落文本变化、缓存失效、整段重译，等于拿
新译文覆盖旧译文，已回滚。

本脚本只做一件事：**定位**。对每个含脚注的英文段，把它和对应的中文段一起给
haiku，让它回一个「锚点」——中文段里的一小段原文，标记应插在其后。然后：

  1. 校验锚点在该中文段中**唯一出现**，否则丢弃不插；
  2. 由脚本自己做字符串拼接插入，模型的输出永远不会进入正文。

所以正文一个字都不会变——插错顶多是标记位置不对，不会污染译文。
模型分工：定位用 haiku（机械活，且有确定性校验兜底），
脚注正文的翻译仍用 opus（见 translate_psalms_footnotes.py）。

用法:
    python3 scripts/psalms_footnote_anchors.py --vol 1 --chapters 21 22   # 指定章
    python3 scripts/psalms_footnote_anchors.py --vol 1 --dry-run          # 只报告
    python3 scripts/psalms_footnote_anchors.py --vol 1                    # 全部待处理章
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REF_RE = re.compile(r'\[\^([a-z]{1,3}\d+[A-Za-z]?)\](?!:)')


def has_def(vol, code):
    """附录里查不到定义的 code 不要定位。

    英文 ch45 有个历史遗留的孤儿引用 [^f004]（附录无此条），若照样定位，
    模型会把它插进 AGES 经文编码里——实测把 <19F004> 插成了 <19[^f004]>。
    """
    global _DEFS
    if _DEFS is None:
        _DEFS = json.loads((ROOT / f'calvin_raw/psalms-{vol}/footnote_defs.json')
                           .read_text(encoding='utf-8'))
    return 'ft' + code[1:] in _DEFS


_DEFS = None
CTX_CHARS = 150          # 每个标记取多少英文前文作为定位线索

SYSTEM = (
    "你的任务是**定位**，不是翻译。\n"
    "给你一段英文原文的片段（每个片段末尾有一个脚注标记 [^code]）和这段英文对应的"
    "中文译文。请判断：在中文译文里，每个脚注标记应该插在哪个位置。\n"
    "输入分若干条，每条形如 `#段号 [code] …英文上下文`，随后给出对应的中文段。\n"
    "输出格式：每行一条，`段号<TAB>code<TAB>锚点`。锚点是**从该段中文里原样复制**的"
    "一小段文字（6 到 14 个字），标记应插在这段文字的**正后方**。\n"
    "硬性要求：\n"
    "1. 锚点必须与中文译文逐字相同，不得改写、不得加标点、不得用同义词\n"
    "2. 锚点要在该段中文里只出现一次；若某处短语重复，就往前多取几个字使其唯一\n"
    "3. 通常插在被注释的那个词或那句话之后（多为句末标点之前或之后）\n"
    "4. 只输出这些行，不要任何解释、不要复述译文\n"
    "5. 定位不了就不要输出该条"
)


def call(prompt, model='haiku', retries=2):
    for _ in range(retries):
        r = subprocess.run(
            ['claude', '-p', '--model', model, '--safe-mode',
             '--strict-mcp-config', '--disallowedTools', '*',
             '--system-prompt', SYSTEM],
            input=prompt, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    return ''


def split_paras(text):
    return [x.strip() for x in re.split(r'\n\s*\n', text) if x.strip()]


def para_spans(text):
    """→ [(start, end, para_text)]，保留在原文中的偏移。
    绝不能用 split + join 重建正文——那会把原有换行结构压平（实测一章
    100 行变 61 行）。插入必须按偏移在原文上做。"""
    spans = []
    for m in re.finditer(r'[^\n]+(?:\n(?!\s*\n)[^\n]*)*', text):
        if m.group(0).strip():
            spans.append((m.start(), m.end(), m.group(0)))
    return spans


def en_body(vol, n):
    b = (ROOT / f'calvin/psalms-{vol}-en/{n}.md').read_text(encoding='utf-8').split('---\n', 2)[2]
    b = b.split('<!-- unplaced-footnotes -->')[0]
    return [p for p in split_paras(b) if not re.match(r'^\[\^[a-z0-9]+\]:', p)]


def plain(s):
    """去标签取纯文本，用于给模型看英文上下文"""
    s = re.sub(r'<[^>]+>', '', s)
    return re.sub(r'\s+', ' ', s).strip()


vol_g = '1'


def anchors_for_chapter(items):
    """items = [(idx, en_para, zh_para)] → {idx: [(code, anchor)]}

    整章一次调用。跨段串味不用担心：锚点必须在**它自己那一段**里唯一出现，
    校验不过就丢弃，模型分不清段落只会导致漏插，不会插错段。
    """
    blocks = []
    for idx, e, z in items:
        hints = []
        for m in REF_RE.finditer(e):
            if not has_def(vol_g, m.group(1)):
                continue
            before = plain(e[:m.start()])[-CTX_CHARS:]
            hints.append(f'  [{m.group(1)}] …{before}')
        blocks.append(f'#{idx} 英文上下文：\n' + '\n'.join(hints)
                      + f'\n#{idx} 中文段：\n{z}')
    out = call('\n\n'.join(blocks))
    res = {}
    for line in out.splitlines():
        parts = re.split(r'\t+|\s{2,}', line.strip(), maxsplit=2)
        if len(parts) != 3:
            continue
        try:
            idx = int(parts[0].strip().lstrip('#'))
        except ValueError:
            continue
        code = parts[1].strip().strip('[]^ ')
        anchor = parts[2].strip()
        if re.fullmatch(r'[a-z]{1,3}\d+[A-Za-z]?', code) and anchor:
            res.setdefault(idx, []).append((code, anchor))
    return res


def insert(zh_para, pairs):
    """按锚点插入 [^code]；只接受唯一匹配。→ (新段, 成功列表, 失败列表)"""
    ok, fail = [], []
    for code, anchor in pairs:
        if f'[^{code}]' in zh_para:
            continue
        cnt = zh_para.count(anchor)
        if cnt != 1:
            fail.append((code, f'锚点出现 {cnt} 次'))
            continue
        i = zh_para.index(anchor) + len(anchor)
        zh_para = zh_para[:i] + f'[^{code}]' + zh_para[i:]
        ok.append(code)
    return zh_para, ok, fail


def process_chapter(vol, n, dry, loose=False):
    zh_path = ROOT / f'calvin_raw/psalms-{vol}/zh_chapters/{n}.md'
    raw = zh_path.read_text(encoding='utf-8')
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', raw, re.S)
    fm, body = m.groups()
    spans = para_spans(body)
    en_paras = en_body(vol, n)
    if len(en_paras) != len(spans):
        if not loose:
            return None, f'段数不对齐 en={len(en_paras)} zh={len(spans)}'
        # 宽松模式：不按段配对，把整章中文当一个作用域找锚点。
        # 校验不变——锚点必须在整章里唯一出现，否则不插。
        need = [c for c in dict.fromkeys(
                    x for e in en_paras for x in REF_RE.findall(e))
                if f'[^{c}]' not in body and has_def(vol_g, c)]
        if not need:
            return ([], []), None
        hints = []
        for e in en_paras:
            for m in REF_RE.finditer(e):
                if m.group(1) in need:
                    hints.append(f'  [{m.group(1)}] …{plain(e[:m.start()])[-CTX_CHARS:]}')
        out = call('#0 英文上下文：\n' + '\n'.join(hints) + f'\n#0 中文段：\n{body}')
        pairs = []
        for line in out.splitlines():
            parts = re.split(r'\t+|\s{2,}', line.strip(), maxsplit=2)
            if len(parts) == 3 and re.fullmatch(r'[a-z]{1,3}\d+[A-Za-z]?', parts[1].strip().strip('[]^ ')):
                pairs.append((parts[1].strip().strip('[]^ '), parts[2].strip()))
        new_body, ok, fail = insert(body, pairs)
        if not dry and ok:
            zh_path.chmod(0o644)
            zh_path.write_text(fm + new_body, encoding='utf-8')
            zh_path.chmod(0o444)
        return (ok, fail), None

    items = [(i, e, z) for i, ((start, end, z), e) in enumerate(zip(spans, en_paras))
             if REF_RE.search(e) and not REF_RE.search(z)]
    if not items:
        return ([], []), None
    got = anchors_for_chapter(items)

    total_ok, total_fail, edits = [], [], []
    for i, e, z in items:
        start, end, _ = spans[i]
        new_z, ok, fail = insert(z, got.get(i, []))
        wanted = set(REF_RE.findall(e))
        missed = wanted - set(ok) - {c for c, _ in fail}
        total_fail += [(c, '模型未给锚点') for c in missed] + fail
        if ok:
            edits.append((start, end, new_z))
            total_ok += ok
    if not dry and edits:
        for start, end, new_z in sorted(edits, reverse=True):   # 从后往前插，偏移不失效
            body = body[:start] + new_z + body[end:]
        zh_path.chmod(0o644)
        zh_path.write_text(fm + body, encoding='utf-8')
        zh_path.chmod(0o444)
    return (total_ok, total_fail), None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', default='1')
    ap.add_argument('--chapters', nargs='*', type=int)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--loose', action='store_true', help='段数对不齐时在整章范围内找锚点')
    args = ap.parse_args()
    global vol_g
    vol_g = args.vol

    src = ROOT / f'calvin_raw/psalms-{args.vol}/zh_chapters'
    todo = []
    for p in sorted(src.glob('*.md'), key=lambda x: int(x.stem)):
        n = int(p.stem)
        if args.chapters and n not in args.chapters:
            continue
        en = (ROOT / f'calvin/psalms-{args.vol}-en/{n}.md').read_text(encoding='utf-8')
        zh = p.read_text(encoding='utf-8')
        need = set(REF_RE.findall(en.split('<!-- unplaced-footnotes -->')[0])) - set(REF_RE.findall(zh))
        if need:
            todo.append((n, len(need)))
    print(f'待处理 {len(todo)} 章，缺 {sum(c for _, c in todo)} 条引用')

    all_ok = all_fail = 0
    for n, cnt in todo:
        res, err = process_chapter(args.vol, n, args.dry_run, args.loose)
        if err:
            print(f'  ch{n}: 跳过（{err}）')
            continue
        ok, fail = res
        all_ok += len(ok); all_fail += len(fail)
        print(f'  ch{n}: 插入 {len(ok)}/{cnt}，未定位 {len(fail)}', flush=True)
    print(f'合计插入 {all_ok} 条，未定位 {all_fail} 条')


if __name__ == '__main__':
    main()
