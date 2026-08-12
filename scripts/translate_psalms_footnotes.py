#!/usr/bin/env python3
"""把诗篇脚注定义从英文译成中文，供中译版还原真脚注。

英文版的脚注已经还原（见 psalms_footnotes_restore.py）；中译版正文里还留着
fa/fb/fc 死标记，位置是对的，缺的只是中文定义。本脚本按 code 逐条翻译并缓存，
产出 calvin_raw/psalms-N/zh_footnote_defs.json。

缓存按定义原文的 md5，和 translate_filibi.py 同一套路：改章重跑不会重复付费。

用法:
    python3 scripts/translate_psalms_footnotes.py --vol 1                # 译中文正文里已有标记的全部 code
    python3 scripts/translate_psalms_footnotes.py --vol 1 --chapters 17 18
    python3 scripts/translate_psalms_footnotes.py --vol 1 --limit 5      # 先试几条
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MARK_RE = re.compile(r'<span style="color:#800000">(f[a-e]\d+[a-z]?)</span>')

SYSTEM = (
    "你是一位精通加尔文神学的中文译者，正在翻译加尔文《诗篇注释》的**脚注**。\n"
    "这些脚注多为编者按语：校勘异文、引用其他译本或注释家（Horsley、Ainsworth、"
    "Dr Gill、Street、Hammond 等）、给出希伯来文/希腊文/拉丁文/法文原文的说明。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明、不重复原文、不要前言\n"
    "2. 保留所有 HTML 标签与结构不变，尤其 <span class=\"...\"> 与 "
    "<span style=\"color:#...\">…</span>（里面是希伯来文/希腊文原文，**原样保留不翻译**）\n"
    "3. 保留 Markdown 标记不变：**bold** *italic*\n"
    "4. 拉丁文/法文/希腊文/希伯来文保留原文，其后括号附中文译义；"
    "标注语种的缩写照译：— *Fr.* → — *法文本*，— *Lat.* → — *拉丁文本*，"
    "*marg.* → *边注*，*Sept.* / *LXX* → *七十士译本*\n"
    "5. 被注释的经文短语（脚注开头常见的 *斜体短语*）照简体和合本译，并保持斜体\n"
    "6. 人名按通行中译：Horsley→霍斯利，Ainsworth→安斯沃思，Gill→纪尔，"
    "Street→斯特里特，Hammond→哈蒙德，Calvin→加尔文，Kennicott→肯尼科特；"
    "圣经书卷名与章节引用用和合本格式（如 以赛亚书 6:9）\n"
    "7. 保持学术注释的语体，简练，不加评论"
)


def md5key(t):
    return hashlib.md5(t.encode('utf-8')).hexdigest()[:16]


def call_claude(text, cache_dir, retries=3):
    key = md5key(text)
    cached = cache_dir / f'{key}.txt'
    if cached.exists():
        return cached.read_text(encoding='utf-8'), True
    last = ''
    for _ in range(retries):
        # 见 translate_filibi.CLI_TRIM_FLAGS：去掉工具/MCP/默认 agent 提示词，
        # 每次调用前缀 22,014 → 444 token。prompt 走 stdin（--disallowedTools
        # 是可变参数，位置参数会被它吞掉）。
        r = subprocess.run(
            ['claude', '-p', '--strict-mcp-config', '--disallowedTools', '*',
             '--system-prompt', SYSTEM],
            input=text, capture_output=True, text=True)
        out = r.stdout.strip()
        if r.returncode == 0 and out and 'weekly limit' not in out:
            cached.write_text(out, encoding='utf-8')
            return out, False
        last = out or r.stderr.strip()
    raise RuntimeError(f'翻译失败: {last[:200]}')


def codes_in_chapters(vol, chapters=None):
    """中译 raw 里还留着死标记的 code（位置正确，缺的只是中文定义）"""
    src = ROOT / f'calvin_raw/psalms-{vol}/zh_chapters'
    found = {}
    for p in sorted(src.glob('*.md'), key=lambda x: int(x.stem) if x.stem.isdigit() else 0):
        if not p.stem.isdigit() or (chapters and int(p.stem) not in chapters):
            continue
        for c in MARK_RE.findall(p.read_text(encoding='utf-8')):
            found.setdefault(c, p.stem)
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vol', default='1')
    ap.add_argument('--chapters', nargs='*', type=int)
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()

    work = ROOT / f'calvin_raw/psalms-{args.vol}'
    cache_dir = work / 'zh_footnote_cache'
    cache_dir.mkdir(exist_ok=True)
    defs = json.loads((work / 'footnote_defs.json').read_text(encoding='utf-8'))
    out_path = work / 'zh_footnote_defs.json'
    done = json.loads(out_path.read_text(encoding='utf-8')) if out_path.exists() else {}

    todo = [c for c in codes_in_chapters(args.vol, set(args.chapters or []))
            if c not in done and 'ft' + c[1:] in defs]
    if args.limit:
        todo = todo[:args.limit]
    print(f'待译 {len(todo)} 条（已有 {len(done)} 条）')

    hits = 0
    for i, code in enumerate(todo, 1):
        en = defs['ft' + code[1:]]
        zh, cached = call_claude(en, cache_dir)
        hits += cached
        done[code] = zh
        out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                            encoding='utf-8')
        if i % 10 == 0 or i == len(todo):
            print(f'  {i}/{len(todo)}（缓存命中 {hits}）', flush=True)
    print(f'完成，共 {len(done)} 条中文定义 → {out_path.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
