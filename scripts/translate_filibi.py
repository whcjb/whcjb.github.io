#!/usr/bin/env python3
"""
translate_filibi.py — 腓立比书英文注释 MD → 中文 MD

将 calvin_raw/phil/calvin_filibi.md 翻译成简体中文，
保留所有格式标记（HTML/Markdown/脚注/页码），只翻译英文内容，
拉丁文保留原文并附中文括注。

用法（从项目根目录）：
    python3 scripts/translate_filibi.py           # 全量翻译
    python3 scripts/translate_filibi.py --resume  # 断点续翻（跳过已有缓存）
    python3 scripts/translate_filibi.py --dry-run # 只解析，不翻译，统计各类型行数
"""
import sys, re, subprocess, hashlib
from pathlib import Path

SRC       = Path('calvin_raw/phil/calvin_filibi.md')
CACHE_DIR = Path('calvin_raw/phil/zh_cache')
OUT       = Path('calvin_raw/phil/calvin_filibi_zh.md')

BATCH = 5  # 每批翻译段数（每次调用 claude CLI）

SYSTEM = (
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
)


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def md5key(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


def call_claude(prompt: str, timeout: int = 300) -> str:
    r = subprocess.run(
        ['claude', '-p', SYSTEM],
        input=prompt, capture_output=True, text=True, timeout=600
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:400])
    return r.stdout.strip()


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

    # Footnote definition
    m = re.match(r'^\[\^(f(?:t)?\d+)\]: (.+)', line, re.DOTALL)
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

def main():
    resume  = '--resume'  in sys.argv
    dry_run = '--dry-run' in sys.argv

    if not SRC.exists():
        print(f'错误：找不到源文件 {SRC}')
        sys.exit(1)

    print(f'读取 {SRC} ...', flush=True)
    lines = SRC.read_text(encoding='utf-8').split('\n')

    print('分类行类型...', flush=True)
    segments = [classify(l) for l in lines]

    # 统计
    from collections import Counter
    cnt = Counter(k for k, _ in segments)
    print('各类型行数：', dict(cnt))

    if dry_run:
        return

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

    output = '\n'.join(out_lines)
    OUT.write_text(output, encoding='utf-8')
    print(f'\n✓ 写入 {OUT}  ({OUT.stat().st_size:,} bytes)')
    print(f'  段落翻译：{len(to_translate)} 段')
    hit = sum(1 for (i, t) in to_translate
              if (CACHE_DIR / f'{md5key(t)}.txt').exists())
    print(f'  缓存命中：{hit}，新翻译：{len(to_translate)-hit}')


if __name__ == '__main__':
    main()
