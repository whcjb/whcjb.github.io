#!/usr/bin/env python3
"""
translate_owen.py — 约翰·欧文《希伯来书注释》英文页 → 中文页。

复用 translate_filibi 的 call_claude / cached_translate / md5 缓存机制,
但**只翻译正文**: front matter、eyebrow div 原样保留;
`# 标题` / `<h2>...</h2>` / `<p>...</p>` 提取内文翻译后按原标签套回。

缓存: owen_raw/hebrews/zh_cache/  (md5 → 译文, 必须保留, 重跑成本极高)
中文 raw: owen_raw/hebrews/zh_exercitations/N.md  (翻译产物, chmod 444)

用法(项目根目录):
    python3 -u scripts/translate_owen.py --page owen/hebrews/exercitations/1/index.md [--resume] [--publish]
--publish: 直接把中文写回该已发布页(否则只写 raw)。
"""
import sys, re, argparse
from pathlib import Path
import translate_filibi as tf   # 同目录, 复用其 CLI/缓存

ROOT = Path(__file__).resolve().parent.parent

SYSTEM = (
    "你是一位精通清教神学与改革宗传统的中文译者,正在翻译约翰·欧文(John Owen, 1616-1683)"
    "《希伯来书注释》的导论(Exercitations)与序言。\n"
    "将英文译成简体中文,忠实原文,保持欧文缜密、庄重的神学文体。\n"
    "严格规则:\n"
    "1. 只输出译文,不加任何说明,不重复原文,不要前言或解释\n"
    "2. 保留所有 HTML 标签与实体不变:<i> <b> <sup> 以及 &#x27; &quot; &amp; &lt; &gt; 等\n"
    "3. 希腊文/希伯来文/叙利亚文/拉丁文一律保留原文,其后用圆括号附中文译义,"
    "如 λόγος(道)、Sola Scriptura(唯独圣经);整句拉丁引文保留原文,括注中文大意\n"
    "4. 圣经书卷名、人名用和合本标准译名:Hebrews→希伯来书,Paul→保罗,Moses→摩西,"
    "Melchisedec→麦基洗德,Messiah→弥赛亚,apostle→使徒,Old/New Testament→旧约/新约\n"
    "5. 章节引用格式:希伯来书 1:1,罗马书 3:23(书卷名 章:节)\n"
    "6. 神学术语保持学术性:canonical→正典的,priesthood→祭司职分,sacrifice→献祭,"
    "covenant→圣约,justification→称义,righteousness→义,dissertation→专论\n"
    "7. 教父/学者姓名首次出现保留原文并括注中文音译,如 Chrysostom(屈梭多模)\n"
    "8. 保留段首编号(如 1. 2. 10. 31.)不变"
)

def split_page(text):
    """-> (fm_block, body_lines)  fm_block 含首尾 ---"""
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    if m:
        return m.group(1), m.group(2)
    return '', text

def translate_page(page_path, resume, publish):
    src = ROOT / page_path
    text = src.read_text(encoding='utf-8')
    fm, body = split_page(text)
    lines = body.split('\n')

    # 收集可译单元: (line_idx, kind, inner)
    units = []
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('# '):
            units.append((i, 'h1', s[2:]))
        else:
            mh = re.match(r'^<h2>(.*)</h2>$', s)
            mp = re.match(r'^<p>(.*)</p>$', s)
            if mh:
                units.append((i, 'h2', mh.group(1)))
            elif mp:
                units.append((i, 'p', mp.group(1)))
    print(f'{page_path}: {len(units)} 个可译单元', flush=True)

    texts = [u[2] for u in units]
    zh_list = tf.cached_translate(texts, resume)

    for (i, kind, _), zh in zip(units, zh_list):
        zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()   # 剥 Claude 分批标记 artifact
        if kind == 'h1':
            lines[i] = f'# {zh}'
        elif kind == 'h2':
            lines[i] = f'<h2>{zh}</h2>'
        else:
            lines[i] = f'<p>{zh}</p>'

    zh_body = '\n'.join(lines)

    # 写中文 raw(翻译产物, 保留)
    seq = re.search(r'/(\d+)/index\.md$', page_path)
    raw_dir = ROOT / 'owen_raw/hebrews/zh_exercitations'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_out = raw_dir / (f'{seq.group(1)}.md' if seq else (Path(page_path).parent.name + '.md'))
    if raw_out.exists():
        raw_out.chmod(0o644)
    raw_out.write_text(fm + zh_body, encoding='utf-8')
    raw_out.chmod(0o444)
    print(f'✓ 中文 raw → {raw_out}  (chmod 444)', flush=True)

    hit = sum(1 for t in texts if (tf.CACHE_DIR / f'{tf.md5key(t)}.txt').exists())
    print(f'  缓存命中 {hit} / {len(texts)}', flush=True)

    if publish:
        src.write_text(fm + zh_body, encoding='utf-8')
        print(f'✓ 已发布中文到 {page_path}', flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', required=True, help='已发布英文页相对路径')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    args = ap.parse_args()

    tf.SYSTEM = SYSTEM
    tf.CACHE_DIR = ROOT / 'owen_raw/hebrews/zh_cache'
    tf.BATCH = 1
    translate_page(args.page, args.resume, args.publish)

if __name__ == '__main__':
    main()
