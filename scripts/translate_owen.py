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
from owen_outline import linkify as outline_linkify

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
    # 收集可译单元。英文页已 linkify: 段可能带 id(<p id="sec-N">), 总纲是
    # <nav class="owen-outline">…<a …><b>N.</b> 文字</a>…</nav>。均提取内文翻译后按结构套回。
    NAV_ITEM = re.compile(r'(<a class="owen-outline-item" href="#sec-\d+"><b>\d+\.</b> )(.*?)(</a>)', re.S)
    units = []          # (line_idx, kind, text, meta)
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('# '):
            units.append((i, 'h1', s[2:], None))
        elif s.startswith('<nav class="owen-outline"'):
            for k, m in enumerate(NAV_ITEM.finditer(s)):
                units.append((i, f'nav', m.group(2), k))   # 每个纲目条目
        else:
            mh = re.match(r'^<h2>(.*)</h2>$', s, re.S)
            mp = re.match(r'^(<p(?:\s+id="[^"]*")?>)(.*)(</p>)$', s, re.S)
            if mh:
                units.append((i, 'h2', mh.group(1), None))
            elif mp:
                units.append((i, 'p', mp.group(2), mp.group(1)))   # meta = 原开标签(含 id)
    print(f'{page_path}: {len(units)} 个可译单元', flush=True)

    texts = [u[2] for u in units]
    zh_list = tf.cached_translate(texts, resume)
    zmap = {}
    for (i, kind, _, meta), zh in zip(units, zh_list):
        zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
        if kind == 'h1':
            lines[i] = f'# {zh}'
        elif kind == 'h2':
            lines[i] = f'<h2>{zh}</h2>'
        elif kind == 'p':
            lines[i] = f'{meta}{zh}</p>'
        elif kind == 'nav':
            zmap.setdefault(i, {})[meta] = zh
    # 重建总纲 nav 行: 逐条替换链接文字, 保留 href/编号
    for i, itemmap in zmap.items():
        cnt = [0]
        def _rep(m):
            k = cnt[0]; cnt[0] += 1
            return m.group(1) + itemmap.get(k, m.group(2)) + m.group(3)
        lines[i] = NAV_ITEM.sub(_rep, lines[i])

    zh_body = '\n'.join(lines)

    # 英文页 front matter 取值
    def fmval(key):
        m = re.search(rf'^{key}:\s*(.+)$', fm, re.M)
        return m.group(1).strip().strip('"') if m else ''
    seq = re.search(r'/(\d+)/index\.md$', page_path)
    seqn = seq.group(1) if seq else Path(page_path).parent.name
    en_dir = '/' + str(Path(page_path).parent) + '/'      # /owen/hebrews/exercitations/N/
    zh_url = en_dir + 'zh/'
    zh_h1 = next((l[2:].strip() for l in lines if l.startswith('# ')), fmval('title'))

    # 中文页独立 front matter(不混英文 prev/next; 加回英文链接)
    fm_zh = ('---\n'
             'layout: owen-chapter\n'
             f'book_id: {fmval("book_id") or "hebrews/exercitations"}\n'
             f'book_name: "{fmval("book_name") or "约翰欧文导论"}"\n'
             f'title: "导论 {seqn} · {zh_h1[:40]}"\n'
             f'date: {fmval("date")}\n'
             f'en_url: "{en_dir}"\n'
             '---\n')
    zh_page = fm_zh + zh_body

    # 1) 中文 raw(翻译产物, chmod 444 保留)
    raw_dir = ROOT / 'owen_raw/hebrews/zh_exercitations'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_out = raw_dir / f'{seqn}.md'
    if raw_out.exists():
        raw_out.chmod(0o644)
    raw_out.write_text(zh_page, encoding='utf-8')
    raw_out.chmod(0o444)
    print(f'✓ 中文 raw → {raw_out}  (chmod 444)', flush=True)

    hit = sum(1 for t in texts if (tf.CACHE_DIR / f'{tf.md5key(t)}.txt').exists())
    print(f'  缓存命中 {hit} / {len(texts)}', flush=True)

    if publish:
        # 2) 中文页 → <en页>/zh/index.md (不覆盖英文)
        zh_out = src.parent / 'zh' / 'index.md'
        zh_out.parent.mkdir(parents=True, exist_ok=True)
        zh_out.write_text(zh_page, encoding='utf-8')
        print(f'✓ 中文页 → {zh_out}', flush=True)
        # 3) 英文页回填 zh_url(仅当尚无), 使其显示「中文版」切换
        en_txt = src.read_text(encoding='utf-8')
        if 'zh_url:' not in en_txt:
            en_txt = re.sub(r'\n---\n', f'\nzh_url: "{zh_url}"\n---\n', en_txt, count=1)
            src.write_text(en_txt, encoding='utf-8')
            print(f'✓ 英文页回填 zh_url → {page_path}', flush=True)

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
