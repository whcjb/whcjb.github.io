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
MARK_RE = re.compile(r'<span style="color:#800000">(f[a-e]\d+[A-Za-z]?)</span>')
REF_RE = re.compile(r'\[\^(f[a-e]\d+[A-Za-z]?)\](?!:)')     # 锚点脚本插入的引用

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
            # 脚注正文的翻译用 opus——这是要读的内容，质量不能降；
            # 定位那种机械活才用 haiku（见 psalms_footnote_anchors.py）。
            ['claude', '-p', '--model', 'opus', '--strict-mcp-config',
             '--disallowedTools', '*', '--system-prompt', SYSTEM],
            input=text, capture_output=True, text=True)
        out = r.stdout.strip()
        if r.returncode == 0 and out and 'weekly limit' not in out:
            cached.write_text(out, encoding='utf-8')
            return out, False
        last = out or r.stderr.strip()
    raise RuntimeError(f'翻译失败: {last[:200]}')


BATCH = 5


def translate_chunk(codes, defs, cache_dir):
    """一次调用翻译 BATCH 条脚注定义 → {code: 中文}

    用 <<<N>>> 分隔并逐条写缓存；解析不出来的条目退回逐条翻译，
    所以批处理只影响速度，不影响可靠性。
    """
    out, pending = {}, []
    for c in codes:
        f = cache_dir / f'{md5key(defs["ft" + c[1:]])}.txt'
        if f.exists():
            out[c] = f.read_text(encoding='utf-8')
        else:
            pending.append(c)
    if not pending:
        return out

    parts = [f'<<<{i+1}>>>\n{defs["ft" + c[1:]]}' for i, c in enumerate(pending)]
    prompt = ('请按编号逐条翻译以下脚注，输出保持 <<<N>>> 编号格式：\n\n'
              + '\n\n'.join(parts))
    raw = call_raw(prompt)
    got = {}
    for m in re.finditer(r'<<<(\d+)>>>\s*\n(.*?)(?=<<<\d+>>>|\Z)', raw, re.S):
        i = int(m.group(1)) - 1
        if 0 <= i < len(pending) and m.group(2).strip():
            got[pending[i]] = m.group(2).strip()
    for c in pending:
        if c not in got:                       # 解析失败 → 逐条兜底
            got[c], _ = call_claude(defs['ft' + c[1:]], cache_dir)
    for c, zh in got.items():
        (cache_dir / f'{md5key(defs["ft" + c[1:]])}.txt').write_text(zh, encoding='utf-8')
        out[c] = zh
    return out


def call_raw(prompt, retries=3):
    for _ in range(retries):
        r = subprocess.run(
            ['claude', '-p', '--model', 'opus', '--strict-mcp-config',
             '--disallowedTools', '*', '--system-prompt', SYSTEM],
            input=prompt, capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip() and 'weekly limit' not in r.stdout:
            return r.stdout.strip()
    raise RuntimeError('批量翻译失败')


def codes_in_chapters(vol, chapters=None):
    """中译 raw 里还留着死标记的 code（位置正确，缺的只是中文定义）"""
    src = ROOT / f'calvin_raw/psalms-{vol}/zh_chapters'
    found = {}
    for p in sorted(src.glob('*.md'), key=lambda x: int(x.stem) if x.stem.isdigit() else 0):
        if not p.stem.isdigit() or (chapters and int(p.stem) not in chapters):
            continue
        t = p.read_text(encoding='utf-8')
        for c in MARK_RE.findall(t) + REF_RE.findall(t):
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

    # 逐条调用时每次固定开销约 5 秒（CLI 启动+认证+建会话），875 条光启动就 73 分钟；
    # 一次送 BATCH 条，启动开销摊薄到 1/BATCH，生成也在同一个流里更省。
    # 解析失败的条目自动退回逐条翻译，所以批处理不会降低可靠性。
    # 按字符预算分组，不按固定条数：脚注长度差 300 倍（最短 4 字符、最长 7848），
    # 固定条数要么长条撑爆输出、要么短条严重装不满。一批约 8000 字符英文，
    # 对应中文输出约 5k token，安全且充分利用单次调用。
    def chunks(codes):
        buf, size = [], 0
        for c in codes:
            n = len(defs['ft' + c[1:]])
            if buf and (size + n > 8000 or len(buf) >= 25):
                yield buf
                buf, size = [], 0
            buf.append(c); size += n
        if buf:
            yield buf

    done_n, failed = 0, []
    for chunk in chunks(todo):
        # 单批失败不该拖垮整轮: 其余批次照跑, 失败的下次 --resume 从缓存续
        try:
            for code, zh in translate_chunk(chunk, defs, cache_dir).items():
                done[code] = zh
        except RuntimeError as e:
            failed += chunk
            print(f'  !! 批次失败({e}), 跳过 {len(chunk)} 条: {chunk[:3]}…', flush=True)
            continue
        done_n += len(chunk)
        out_path.write_text(json.dumps(done, ensure_ascii=False, indent=1),
                            encoding='utf-8')
        print(f'  {done_n}/{len(todo)}', flush=True)
    print(f'完成，共 {len(done)} 条中文定义 → {out_path.relative_to(ROOT)}')
    if failed:
        print(f'⚠ {len(failed)} 条未译，下次运行会重试: {failed}')
        sys.exit(1)


if __name__ == '__main__':
    main()
