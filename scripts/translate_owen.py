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

REVIEW_SYSTEM = ("你是资深改革宗神学译审, 精通清教神学与和合本圣经。"
                 "你的任务是校对约翰·欧文《希伯来书注释》的中文初译, 使其对得起原著。")

def review_one(en, draft, resume):
    """二遍审校: 拿英文原文 + 中文初译, 逐条修正, 只输出修正后的中文。"""
    if not draft.strip() or not re.search(r'[一-鿿]', draft):
        return draft
    key = tf.md5key('REVIEW2::' + en + '||' + draft)
    f = tf.CACHE_DIR / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 1:
        return f.read_text(encoding='utf-8')
    prompt = (
        "校对下面英文原文的中文初译。**只输出修正后的中文译文**, 不加任何说明。"
        "保持所有 HTML 标签、脚注标记[^N]、以及希腊/希伯来/叙利亚/拉丁原文不变。\n"
        "重点检查并修正:\n"
        "① 意义偏差、漏译、擅自增译——须忠实英文;\n"
        "② 幻觉——中文若出现英文原文中没有的专名或概念, 删除或改正;\n"
        "③ 口语或现代词(如「力度」「能量」「搞」「到位」)→ 庄重书面的清教神学文体;\n"
        "④ 连接词/虚词意义漂移(如 Particularly 误作「尤有进者」应作「尤其」);\n"
        "⑤ 术语: 经文、书卷、人名一律和合本; 不同英文词须用不同中文(power 权能/energy 感力/"
        "efficacy 功效); authority 位格治权→权柄、圣经权威性→权威;\n"
        "若初译已准确通顺, 原样返回。\n\n"
        f"【英文原文】\n{en}\n\n【中文初译】\n{draft}")
    out = re.sub(r'<<<[^>]*>>>', '', tf.call_claude(prompt)).strip()
    tf.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out

def split_page(text):
    """-> (fm_block, body_lines)  fm_block 含首尾 ---"""
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    if m:
        return m.group(1), m.group(2)
    return '', text

def translate_page(page_path, resume, publish, review=False, limit=0):
    src = ROOT / page_path
    text = src.read_text(encoding='utf-8')
    fm, body = split_page(text)
    lines = body.split('\n')

    # 收集可译单元。英文页已 linkify: 正文段带 id(<p id="sec-N">), 总纲(折叠 details)
    # 内含 <a …><b>N.</b> 文字</a>。
    # ⚠️ 纲要**整份一起翻译**(40 条互为上下文, 是一份连贯清单)再按编号拆回。实测:
    #    · 拆成单条孤立翻译 → 丢上下文塌成同义词(power/efficacy 都成"效力");
    #    · 拿整段正文当上下文翻短标题 → 模型照段落改写, 严重幻觉(Circumstances→"祭司职分…")。
    #    整份纲要一起翻是唯一零幻觉且能区分近义词的做法。
    from owen_outline import _split_outline
    NAV_ITEM = re.compile(r'(<a class="owen-outline-item" href="#sec-(\d+)"><b>\d+\.</b> )(.*?)(</a>)', re.S)
    units = []          # (line_idx, kind, text, meta)
    for i, l in enumerate(lines):
        s = l.strip()
        if s.startswith('# '):
            units.append((i, 'h1', s[2:], None))
        elif 'class="owen-outline"' in s and 'owen-outline-item' in s:
            full_en = ' '.join(f'{n}. {t}' for (_p, n, t, _s) in NAV_ITEM.findall(s))
            units.append((i, 'outline', full_en, None))
        else:
            mh = re.match(r'^<h2>(.*)</h2>$', s, re.S)
            mp = re.match(r'^(<p[^>]*>)(.*)(</p>)$', s, re.S)
            if mh:
                units.append((i, 'h2', mh.group(1), None))
            elif mp:
                units.append((i, 'p', mp.group(2), mp.group(1)))   # meta = 原开标签(含 id)
    print(f'{page_path}: {len(units)} 个可译单元', flush=True)

    texts = [u[2] for u in units]
    zh_list = tf.cached_translate(texts, resume)
    if review:                       # 二遍审校: 逐段比对英文, 修漂移/幻觉/口语/术语
        base = tf.SYSTEM
        tf.SYSTEM = REVIEW_SYSTEM
        out = []; pcount = 0
        for (i, kind, en, meta), zh in zip(units, zh_list):
            if kind == 'p':
                pcount += 1
            do = kind in ('h1', 'h2', 'outline') or (kind == 'p' and (limit <= 0 or pcount <= limit))
            out.append(review_one(en, zh, resume) if do else zh)
        n_rev = sum(1 for u in units if u[1] == 'p' and (limit <= 0 or True)) if limit <= 0 else min(limit, sum(1 for u in units if u[1]=='p'))
        print(f'  二遍审校: 前 {n_rev if limit>0 else "全部"} 段正文 + 标题/纲要', flush=True)
        zh_list = out
        tf.SYSTEM = base
    for (i, kind, _, meta), zh in zip(units, zh_list):
        zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
        if kind == 'h1':   lines[i] = f'# {zh}'
        elif kind == 'h2': lines[i] = f'<h2>{zh}</h2>'
        elif kind == 'p':  lines[i] = f'{meta}{zh}</p>'
        elif kind == 'outline':
            zh_items = dict(_split_outline(zh) or [])
            def _rep(m):
                n = int(m.group(2))
                return m.group(1) + zh_items.get(n, m.group(3)) + m.group(4)
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

PLAN_GUIDE = (
    "\n\n【文体与术语指南——遵此约定, 但按上下文取舍, 非机械替换】\n"
    "1. 文风: 文白相济、庄重典雅的清教神学文体; 长句可照译, 不硬拆到走味; "
    "严禁口语/现代词(如「力度」「能量」「搞」「到位」)与网络语。\n"
    "2. 不同英文词必须译成不同中文(严禁撞词)。关键近义区分: "
    "power 权能 / energy 感力 / efficacy 功效 / virtue 德能。\n"
    "3. authority 双义: 位格被授予的治权(基督、君王, ἐξουσία)→权柄; "
    "圣经/正典/本书信本身的权威性(抽象属性)→权威。\n"
    "4. 神学术语依和合本 + 改革宗惯用: righteousness 义, justification 称义, "
    "covenant 约, priesthood 祭司的职任, mediator 中保, canonical 正典的, "
    "sanctification 成圣, repentance 悔改; 经文、书卷、人名一律和合本。\n"
    "5. 表外术语: 先按经文(和合本对应处)→标准神学译法→上下文取义; "
    "关键而拿不准者, 中文后括注英文, 如「德能(virtue)」。"
)

def load_glossary():
    """受控术语表 → 注入 system prompt 的对照行(优先和合本, 禁撞词)。"""
    import json
    g = json.load(open(ROOT / 'scripts/owen_glossary.json', encoding='utf-8'))
    lines = []
    for cat, terms in g.items():
        if cat.startswith('_'):
            continue
        for en, zh in terms.items():
            lines.append(f'  {en} → {zh}')
    return ('\n\n【受控术语表·必须严格遵守(优先和合本圣经用词; 不同英文词必须译成不同中文, '
            '严禁把 power/authority/efficacy 等不同词译成同一中文)】\n' + '\n'.join(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', required=True, help='已发布英文页相对路径')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--review', action='store_true', help='二遍审校(逐段比对英文修正)')
    ap.add_argument('--limit', type=int, default=0, help='仅审校前 N 段正文(0=全部)')
    args = ap.parse_args()

    tf.SYSTEM = SYSTEM + PLAN_GUIDE   # 方案指南(文风+近义防撞+双义+表外规则), 非死表
    tf.CACHE_DIR = ROOT / 'owen_raw/hebrews/zh_cache'
    tf.BATCH = 1
    translate_page(args.page, args.resume, args.publish, args.review, args.limit)

if __name__ == '__main__':
    main()
