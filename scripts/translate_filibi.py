#!/usr/bin/env python3
"""
translate_filibi.py — Calvin 注释 MD → 中文 MD（支持多书卷）

保留所有格式标记（HTML/Markdown/脚注/页码），只翻译英文内容，
拉丁文保留原文并附中文括注。

用法（从项目根目录）：
    python3 scripts/translate_filibi.py                              # 默认 phil 全量翻译
    python3 scripts/translate_filibi.py --book phil --resume         # 断点续翻
    python3 scripts/translate_filibi.py --book harmony1 --chapter 1  # harmony1 第 1 章
    python3 scripts/translate_filibi.py --book BOOK --dry-run        # 只统计行类型

支持的 --book 配置见下方 BOOKS 字典。harmony1 多文件模式按 --chapter
指定章号；phil 等单文件模式忽略 --chapter。
"""
import sys, re, subprocess, hashlib, argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

BATCH = 1  # 每批翻译段数（每次调用 claude CLI）

# ── 各书卷配置 ────────────────────────────────────────────────────────────────
# 每项要么是 (src_path, cache_dir, out_path, system) 单文件配置，
# 要么是按章号生成路径的回调（dict 含 src_fn / cache_dir / out_fn / system）。
BOOKS = {
    'phil': {
        'mode':   'single',
        'src':    ROOT / 'calvin_raw/phil/calvin_filibi.md',
        'cache':  ROOT / 'calvin_raw/phil/zh_cache',
        'out':    ROOT / 'calvin_raw/phil/calvin_filibi_zh.md',
        'system': (
            "你是一位精通加尔文神学的中文译者，专门翻译16世纪加尔文的圣经注释。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明、不重复原文\n"
            "2. 保留所有脚注引用标记不变：[^f1] [^ft35] 等\n"
            "3. 保留所有行内 HTML 标签不变：<span style=\"color:#800000\">*...*</span>\n"
            "4. 拉丁文/法文/希腊文保留原文，括号后附中文，如 fides（信心）\n"
            "5. 圣经书卷名和人名使用和合本标准译名：\n"
            "   PHILIPPIANS→腓立比书，COLOSSIANS→歌罗西书，GALATIANS→加拉太书\n"
            "   CORINTHIANS→哥林多书，THESSALONIANS→帖撒罗尼迦书，EPHESIANS→以弗所书\n"
            "   ROMANS→罗马书，TIMOTHY→提摩太书，HEBREWS→希伯来书\n"
            "   Paul→保罗，Timothy→提摩太，Philippi→腓立比，Epaphroditus→以巴弗提\n"
            "6. 章节引用格式保持：腓立比书 1:1，歌罗西书 2:6\n"
            "7. 脚注中的法文引文格式：保留原法文 —\"中文译文\"（保留破折号和引号格式）"
        ),
    },
    'harmony1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-1-en',          # 目录，按 {ch}.md 取
        'cache':  ROOT / 'calvin_raw/matthew1/zh_cache',
        'out':    ROOT / 'calvin_raw/matthew1/zh_chapters', # 目录，按 {ch}.md 输出
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《福音书和谐》（共观福音注释）卷一。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^123] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> 等\n"
            "5. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   πεπληροφορημένα（充分确信）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "6. 圣经书卷/人名用和合本标准译名：\n"
            "   Luke→路加福音，Matthew→马太福音，Mark→马可福音，John→约翰福音\n"
            "   Acts→使徒行传，Romans→罗马书，Corinthians→哥林多书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书\n"
            "   Hebrews→希伯来书，Peter→彼得，James→雅各书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Malachi→玛拉基书\n"
            "   Zechariah→撒迦利亚书，Daniel→但以理书，Micah→弥迦书\n"
            "   Zacharias→撒迦利亚（路加福音中施洗约翰之父），Elisabeth→以利沙伯\n"
            "   Mary→马利亚，Joseph→约瑟，Jesus→耶稣，Christ→基督，John the Baptist→施洗约翰\n"
            "   Gabriel→加百列，David→大卫，Abraham→亚伯拉罕，Sarah→撒拉，Joshua→约书亚\n"
            "   Paul→保罗，Luke→路加，Theophilus→提阿非罗\n"
            "7. 章节引用格式：路加福音 1:1，马太福音 2:23（书卷名 章:节）\n"
            "8. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "9. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "   sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "   regeneration→重生，election→拣选，predestination→预定，\n"
            "   sovereignty→主权，providence→护理，redemption→救赎"
        ),
    },
}

# 运行时由 main() 注入下面三个全局变量
SRC = CACHE_DIR = OUT = SYSTEM = None


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def md5key(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def call_claude(prompt: str, timeout: int = 300, max_retries: int = 3) -> str:
    """调用 claude CLI；遇到失败重试 max_retries 次（指数退避 5/15/30s）。"""
    import time
    last_err = ''
    for attempt in range(max_retries):
        if attempt:
            wait = 5 * (3 ** (attempt - 1))
            print(f'    [retry {attempt}] {last_err[:120]} | wait {wait}s', flush=True)
            time.sleep(wait)
        try:
            r = subprocess.run(
                ['claude', '-p', SYSTEM],
                input=prompt, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired as e:
            last_err = f'TimeoutExpired({timeout}s)'
            continue
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        last_err = (f'rc={r.returncode} stderr={r.stderr[:200]!r} '
                    f'stdout={r.stdout[:120]!r}')
    raise RuntimeError(f'claude CLI failed after {max_retries} retries: {last_err}')


def translate_batch(texts: list) -> list:
    """
    一次 claude CLI 调用翻译多段文本。
    用 <<<N>>> 分隔符标记每段，解析响应时按编号提取。
    """
    parts = [f'<<<{i+1}>>>\n{t}' for i, t in enumerate(texts)]
    prompt = '请按编号顺序翻译以下各段（加尔文腓立比书注释），保持 <<<N>>> 格式输出：\n\n' + '\n\n'.join(parts)

    raw = call_claude(prompt)

    # 解析 <<<N>>> 格式响应
    result = [None] * len(texts)
    for m in re.finditer(r'<<<(\d+)>>>\s*\n(.*?)(?=<<<\d+>>>|\Z)', raw, re.DOTALL):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(texts):
            result[idx] = m.group(2).strip()

    # fallback：解析失败的逐条翻译
    for i, t in enumerate(result):
        if t is None:
            try:
                result[i] = call_claude(texts[i], timeout=120)
            except Exception:
                result[i] = texts[i]  # 保留原文

    return result


def cached_translate(texts: list, resume: bool) -> list:
    """批量翻译，已有缓存的直接读取。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results = [None] * len(texts)
    pending_idx = []

    for i, t in enumerate(texts):
        f = CACHE_DIR / f'{md5key(t)}.txt'
        if resume and f.exists() and f.stat().st_size > 2:
            results[i] = f.read_text(encoding='utf-8')
        else:
            pending_idx.append(i)

    # 分批翻译未命中缓存的
    for batch_start in range(0, len(pending_idx), BATCH):
        batch_pos = pending_idx[batch_start:batch_start + BATCH]
        batch_texts = [texts[i] for i in batch_pos]
        print(f'  翻译第 {batch_start+1}–{batch_start+len(batch_pos)} 段（共 {len(pending_idx)} 段未缓存）...', flush=True)
        zh_list = translate_batch(batch_texts)
        for i, zh in zip(batch_pos, zh_list):
            results[i] = zh
            f = CACHE_DIR / f'{md5key(texts[i])}.txt'
            f.write_text(zh, encoding='utf-8')

    return results


# ── 行分类 ────────────────────────────────────────────────────────────────────

def classify(line: str):
    """
    返回 (kind, data)：
      'pass'            → data = line（原样输出）
      'h1'              → data = heading text
      'h2'              → data = heading text
      'bq'              → data = blockquote content
      'fn'              → data = (key, footnote_text)
      'md_table_header' → data = (bold_ref_text, full_line)  # | **PHIL 1:1** | |
      'md_table_sep'    → data = line  # |---|---|
      'md_table_row'    → data = (left_en, right_lat, full_line)
      'body'            → data = paragraph text
    """
    # 空行 / 页码 / 水平线 / HTML结构标签
    stripped = line.strip()
    if not stripped:
        return ('pass', line)
    if re.match(r'^<!-- PAGE \d+ -->', line):
        return ('pass', line)
    if stripped == '---':
        return ('pass', line)
    if re.match(r'^</?(?:table|tbody|thead|tr)[\s>]', line) and '<td>' not in line:
        return ('pass', line)

    # H1 / H2
    m = re.match(r'^(#{1,2}) (.+)', line)
    if m:
        prefix = m.group(1)
        return ('h1' if prefix == '#' else 'h2', m.group(2))

    # Blockquote
    m = re.match(r'^> (.+)', line)
    if m:
        return ('bq', m.group(1))

    # Footnote definition  ([^17]: ...  or  [^f17]: ...  or  [^ft17]: ...)
    m = re.match(r'^\[\^(f?t?\d+)\]: (.+)', line, re.DOTALL)
    if m:
        return ('fn', (m.group(1), m.group(2)))

    # Markdown table separator  |---|---|
    if re.match(r'^\|[-| :]+\|$', stripped):
        return ('md_table_sep', line)

    # Markdown table row  | cell1 | cell2 |
    if stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 3:
        # 去掉首尾 |，再按 | 分割，保留空单元格
        cells = [c.strip() for c in stripped[1:-1].split('|')]
        if len(cells) >= 2:
            left, right = cells[0], cells[1]
            # 表格标题行：左列是粗体引用（如 **PHILIPPIANS 1:1-6**），右列为空
            if re.match(r'^\*\*.+\*\*$', left) and right == '':
                inner = left[2:-2]  # 去掉 **
                return ('md_table_header', (inner, line))
            # 内容行
            return ('md_table_row', (left, right, line))
        return ('pass', line)

    # HTML table row with two td columns
    if line.startswith('<tr><td>'):
        sep = line.find('</td><td>')
        if sep != -1 and line.endswith('</td></tr>'):
            left  = line[8:sep]
            right = line[sep+9:-10]
            return ('html_td_row', (left, right))

    # HTML table header th
    if '<th' in line and '<td>' not in line:
        m_th = re.search(r'(<th[^>]*>)([^<]+)(</th>)', line)
        if m_th:
            return ('html_th', (m_th.group(1), m_th.group(2), m_th.group(3), line))

    # 普通段落
    return ('body', line)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def translate_file(src_path: Path, out_path: Path, resume: bool, dry_run: bool):
    if not src_path.exists():
        print(f'错误：找不到源文件 {src_path}')
        return False

    print(f'读取 {src_path}', flush=True)
    lines = src_path.read_text(encoding='utf-8').split('\n')

    print('分类行类型...', flush=True)
    segments = [classify(l) for l in lines]

    # 统计
    from collections import Counter
    cnt = Counter(k for k, _ in segments)
    print('各类型行数：', dict(cnt))

    if dry_run:
        return True

    # 收集需要翻译的文本（按 seg index）
    # kind → text to translate
    to_translate = []  # [(seg_index, text_to_translate)]

    for i, (kind, data) in enumerate(segments):
        if kind in ('h1', 'h2', 'body', 'bq'):
            to_translate.append((i, data))
        elif kind == 'fn':
            to_translate.append((i, data[1]))
        elif kind == 'md_table_header':
            to_translate.append((i, data[0]))  # 翻译引用文字（如 PHILIPPIANS 1:1-6）
        elif kind == 'md_table_row':
            if data[0].strip():
                to_translate.append((i, data[0]))  # 翻译左列（英文）
        elif kind == 'html_td_row':
            if data[0].strip():
                to_translate.append((i, data[0]))
        elif kind == 'html_th':
            to_translate.append((i, data[1]))

    print(f'\n共 {len(to_translate)} 段需要翻译，缓存目录: {CACHE_DIR}', flush=True)

    # 批量翻译
    texts = [t for _, t in to_translate]
    zh_list = cached_translate(texts, resume)

    # 建立 seg_index → 中文 的映射
    translations = {seg_i: zh for (seg_i, _), zh in zip(to_translate, zh_list)}

    # 重建输出行
    print('\n重建 MD...', flush=True)
    out_lines = []
    for i, (kind, data) in enumerate(segments):
        zh = translations.get(i, '')

        if kind == 'pass':
            out_lines.append(data)
        elif kind == 'h1':
            out_lines.append(f'# {zh}')
        elif kind == 'h2':
            out_lines.append(f'## {zh}')
        elif kind == 'bq':
            out_lines.append(f'> {zh}')
        elif kind == 'fn':
            key = data[0]
            out_lines.append(f'[^{key}]: {zh}')
        elif kind == 'body':
            out_lines.append(zh if zh else data)
        elif kind == 'md_table_header':
            # | **PHILIPPIANS 1:1-6** | |  →  | **腓立比书 1:1-6** | |
            out_lines.append(f'| **{zh}** | |')
        elif kind == 'md_table_sep':
            out_lines.append(data)
        elif kind == 'md_table_row':
            left_en, right_lat, _ = data
            zh_left = zh if zh else left_en
            out_lines.append(f'| {zh_left} | {right_lat} |')
        elif kind == 'html_td_row':
            left_en, right = data
            zh_left = zh if zh else left_en
            out_lines.append(f'<tr><td>{zh_left}</td><td>{right}</td></tr>')
        elif kind == 'html_th':
            prefix, text_en, suffix, original = data
            out_lines.append(original.replace(text_en, zh, 1) if zh else original)
        else:
            out_lines.append(data if isinstance(data, str) else str(data))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = '\n'.join(out_lines)
    out_path.write_text(output, encoding='utf-8')
    print(f'\n✓ 写入 {out_path}  ({out_path.stat().st_size:,} bytes)')
    print(f'  段落翻译：{len(to_translate)} 段')
    hit = sum(1 for (i, t) in to_translate
              if (CACHE_DIR / f'{md5key(t)}.txt').exists())
    print(f'  缓存命中：{hit}，新翻译：{len(to_translate)-hit}')
    return True


def main():
    global SRC, CACHE_DIR, OUT, SYSTEM

    ap = argparse.ArgumentParser(description='Calvin MD → 中文 MD 翻译')
    ap.add_argument('--book', default='phil', choices=list(BOOKS.keys()),
                    help='选择书卷预设配置（默认 phil）')
    ap.add_argument('--chapter', type=str, default=None,
                    help='多章模式下指定章号（或 all），单文件模式忽略')
    ap.add_argument('--resume',  action='store_true', help='断点续翻')
    ap.add_argument('--dry-run', action='store_true', help='只统计行类型不翻译')
    args = ap.parse_args()

    cfg = BOOKS[args.book]
    CACHE_DIR = cfg['cache']
    SYSTEM    = cfg['system']

    if cfg['mode'] == 'single':
        SRC = cfg['src']
        OUT = cfg['out']
        translate_file(SRC, OUT, args.resume, args.dry_run)
    elif cfg['mode'] == 'multi_chapter':
        if not args.chapter:
            print(f'书卷 {args.book} 是多章模式，请用 --chapter N (或 all)')
            sys.exit(1)
        src_dir = cfg['src']
        out_dir = cfg['out']
        if args.chapter == 'all':
            chapters = sorted(int(p.stem) for p in src_dir.glob('*.md') if p.stem.isdigit())
        else:
            chapters = [int(args.chapter)]
        for ch in chapters:
            src = src_dir / f'{ch}.md'
            out = out_dir / f'{ch}.md'
            print(f'\n=== 第 {ch} 章 ===')
            translate_file(src, out, args.resume, args.dry_run)


if __name__ == '__main__':
    main()
