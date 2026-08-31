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

FRESH_REVIEW = False   # True 时二遍审校忽略旧审校缓存, 强制重审
REVIEW_CACHED_ONLY = False   # True 时审校只用已有缓存, 未命中用初译(不新调模型)
NOTE_ISSUES = False    # True 时边审校边总结, 审校器自报改动类别写入 NOTES_PATH
NOTES_PATH = ROOT / 'owen_raw/hebrews/review_notes.md'
REVIEW_SYSTEM = ("你是资深改革宗神学译审, 精通清教神学与和合本圣经。"
                 "你的任务是校对约翰·欧文《希伯来书注释》的中文初译, 使其对得起原著。")

def review_one(en, draft, resume):
    """二遍审校: 拿英文原文 + 中文初译, 逐条修正, 只输出修正后的中文。"""
    if not draft.strip() or not re.search(r'[一-鿿]', draft):
        return draft
    key = tf.md5key('REVIEW2::' + en + '||' + draft)
    f = tf.CACHE_DIR / f'{key}.txt'
    if resume and not FRESH_REVIEW and f.exists() and f.stat().st_size > 1:
        return f.read_text(encoding='utf-8')
    if REVIEW_CACHED_ONLY:        # 只用已有审校缓存, 未命中直接用初译(不新调模型)
        return draft
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
        "⑥ canonical 作表语/单用(如 called canonical)→「正典」或「正典书卷」, 勿作"
        "「正典的」拖泥带水; 作定语修饰名词才用「正典的」, 但「正典的书卷」宜作「正典书卷」;\n"
        "若初译已准确通顺, 原样返回。\n")
    if NOTE_ISSUES:
        prompt += ("先输出修正后的中文译文;然后另起一行输出「‖ISSUES‖」,其后用一行列出你本段所做"
                   "修改的问题类别(从: 意义偏差/漏译/增译/幻觉/口语现代词/连接词漂移/术语/撞词/"
                   "canonical表语/标点 中选,可多项,各附三五字例;若未作实质修改写「无」)。\n\n"
                   f"【英文原文】\n{en}\n\n【中文初译】\n{draft}")
    else:
        prompt += f"\n【英文原文】\n{en}\n\n【中文初译】\n{draft}"
    raw = re.sub(r'<<<[^>]*>>>', '', tf.call_claude(prompt)).strip()
    if NOTE_ISSUES and '‖ISSUES‖' in raw:
        out, _, issues = raw.partition('‖ISSUES‖')
        out = out.strip(); issues = issues.strip()
        if issues and issues != '无':
            with open(NOTES_PATH, 'a', encoding='utf-8') as nf:
                nf.write(f'- [{en[:36].strip()}…] {issues}\n')
    else:
        out = raw
    tf.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out

_APOSTLES = ['保罗','彼得','约翰','雅各','马太','马可','路加','安得烈','腓力','多马',
             '巴拿巴','提摩太','提多','司提反','西门','犹大']
_NAME_FIX = {'奥利根': '俄利根', '奥利金': '俄利根', '奥古斯汀': '奥古斯丁',
             '耶罗米': '耶柔米', '克里索斯托': '屈梭多模',
             # 「著」(作品) 被写成「着」(助词)。导论1 一段里就出了两处
             # (杂着卷一、最伟大着作)。只列这些固定词，避免误伤「为着/藉着/
             # 随着/接着」这类正当用法。
             '着作': '著作', '杂着': '杂著', '论着': '论著', '专着': '专著',
             '名着': '名著', '巨着': '巨著', '原着': '原著', '编着': '编著',
             '显着': '显著', '译着': '译著'}
def cleanup_terms(t):
    """确定性术语清理(免费, 不调模型): 改革宗/和合本不加「圣」于使徒名; 标准译名归一。"""
    for n in _APOSTLES:
        t = t.replace('圣' + n, n)
    for a, b in _NAME_FIX.items():
        t = t.replace(a, b)
    return t

_PUNCT_SKIP = set(' \t"\'“”‘’')
def normalize_punct(t):
    """中文标点全角化(，；：（）), 保护章节号冒号(43:24)与拉丁/希腊/英文句内标点;
    「」→ 直双引号。sec-7 风格。"""
    def cjk(c): return bool(c) and '一' <= c <= '鿿'
    t = t.replace('「', '"').replace('」', '"')
    out = []
    for i, c in enumerate(t):
        p = t[i-1] if i > 0 else ''
        n = t[i+1] if i+1 < len(t) else ''
        # 判「是否处在中文语境」时要跳过引号：序7 出过
        #   …神里的奥秘","为要藉着教会…
        # 两段经文引文之间的逗号，左右紧邻的都是引号而非汉字，旧规则看不见它。
        def near(k, step):
            j = k
            while 0 <= j < len(t) and t[j] in _PUNCT_SKIP: j += step
            return cjk(t[j]) if 0 <= j < len(t) else False
        ctx = near(i - 1, -1) or near(i + 1, 1)
        if c == ',' and ctx: out.append('，'); continue
        if c == ';' and ctx:
            # 保护 HTML 实体结尾的分号(&quot; &#x27; &amp; 等), 勿全角化
            if re.search(r'&([a-zA-Z]+|#[0-9]+|#x[0-9a-fA-F]+)$', t[max(0, i-9):i]):
                out.append(c); continue
            out.append('；'); continue
        if c == ':' and ctx and not (p.isdigit() and n.isdigit()):
            out.append('：'); continue
        # ! ? 原先漏掉了，导论1 出过「我该去世了!&quot;」——半角叹号夹在中文里。
        # 句末常紧跟 &quot; 或右引号，所以前一个字符要跳过引号类再判中文。
        if c in '!?' and ctx:
            out.append('！' if c == '!' else '？'); continue
        out.append(c)
    t = ''.join(out)
    def paren(m):
        j = m.start() - 1
        while j >= 0 and t[j] in _PUNCT_SKIP: j -= 1
        before = t[j] if j >= 0 else ''
        if re.search(r'[一-鿿]', m.group(1)) or (before and ord(before) > 0x00FF):
            return '（' + m.group(1) + '）'
        return m.group(0)
    return re.sub(r'\(([^()]*)\)', paren, t)

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

    zh_body = cleanup_terms(normalize_punct('\n'.join(lines)))   # 标点全角化 + 术语清理, 自动

    # 英文页 front matter 取值
    def fmval(key):
        m = re.search(rf'^{key}:\s*(.+)$', fm, re.M)
        return m.group(1).strip().strip('"') if m else ''
    seq = re.search(r'/(\d+)/index\.md$', page_path)
    seqn = seq.group(1) if seq else Path(page_path).parent.name
    en_dir = '/' + str(Path(page_path).parent) + '/'      # /owen/hebrews/exercitations/N/
    zh_url = en_dir + 'zh/'
    zh_h1 = next((l[2:].strip() for l in lines if l.startswith('# ')), fmval('title'))

    # 章导航: 链到相邻中文页(仅当已翻译存在)
    exdir = src.parent.parent                       # .../exercitations
    base = en_dir.rstrip('/').rsplit('/', 1)[0] + '/'   # /owen/hebrews/exercitations/
    nav = []
    try:
        ni = int(seqn)
        if (exdir / f'{ni-1}/zh/index.md').exists():
            nav += [f'prev_url: "{base}{ni-1}/zh/"', f'prev_label: "导论 {ni-1}"']
        if (exdir / f'{ni+1}/zh/index.md').exists():
            nav += [f'next_url: "{base}{ni+1}/zh/"', f'next_label: "导论 {ni+1}"']
    except ValueError:
        pass
    nav_block = ('\n'.join(nav) + '\n') if nav else ''
    # 时间戳：已有中文页则沿用它自己的 date（重跑发布不改动历史时间，
    # 否则每次修个错别字全站时间都会跳）；新建才取当前时间。
    zh_existing = src.parent / 'zh' / 'index.md'
    zh_date = None
    if zh_existing.exists():
        m = re.search(r'^date:\s*(.+)$', zh_existing.read_text(encoding='utf-8'), re.M)
        if m:
            zh_date = m.group(1).strip()
    if not zh_date:
        from datetime import datetime
        zh_date = datetime.now().strftime('%Y-%m-%d %H:%M')
    # 中文页独立 front matter(prev/next 指相邻中文页; 加回英文链接)
    fm_zh = ('---\n'
             'layout: owen-chapter\n'
             f'book_id: {fmval("book_id") or "hebrews/exercitations"}\n'
             f'book_name: "{fmval("book_name") or "约翰欧文导论"}"\n'
             f'title: "导论 {seqn} · {zh_h1[:40]}"\n'
             # 中文页的 date 必须是**本次翻译完成的真实时间**，不能抄英文页。
             # 原先写 fmval("date")，于是全部中文页都顶着英文页的发布时间
             # （卷首八篇一律 2026-07-17 10:44），与实际翻译时间毫无关系，
             # 首页「最新内容」的排序也就全乱。
             # 已发布页面重跑时沿用它自己的 date（见上面 zh_existing），
             # 否则改个错别字重跑，全站中文页时间都会跳。
             f'date: {zh_date}\n'
             + nav_block
             + f'en_url: "{en_dir}"\n'
             '---\n')
    zh_page = fm_zh + zh_body

    # 1) 中文 raw(翻译产物, chmod 444 保留)
    # ⚠️ raw 必须按「章 / 导论 / 卷首」分目录：三类的编号各自从 1 起，
    # 全写进 zh_exercitations/{N}.md 会互相覆盖。实测第 1、2 章的 raw 已经
    # 把导论 1、2 的 raw 覆盖掉了（front matter 里 book_id 变成了 hebrews），
    # 卷首 1–8 更早就覆盖过导论 1–8。发布出去的中文页没事，丢的是 raw 备份。
    _sect = Path(page_path).parent.parent.name      # exercitations / prefaces / hebrews
    _sub = {'exercitations': 'zh_exercitations',
            'prefaces': 'zh_prefaces'}.get(_sect, 'zh_chapters')
    raw_dir = ROOT / 'owen_raw/hebrews' / _sub
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
        # 4) 回填上一篇中文页的 next(本页新出现, 让上一页能翻到本页)
        try:
            prev_zh = exdir / f'{int(seqn)-1}/zh/index.md'
            if prev_zh.exists():
                pt = prev_zh.read_text(encoding='utf-8')
                if 'next_url:' not in pt:
                    add = f'next_url: "{base}{seqn}/zh/"\nnext_label: "导论 {seqn}"\n'
                    pt = re.sub(r'\nen_url:', '\n' + add + 'en_url:', pt, count=1)
                    prev_zh.write_text(pt, encoding='utf-8')
                    print(f'✓ 回填上一篇 next → 导论{int(seqn)-1}/zh', flush=True)
        except ValueError:
            pass

PLAN_GUIDE = (
    "\n\n【翻译要求·遵此约定但按上下文取舍】\n"
    "★优先级(冲突时一律按此让步): ①意思正确 ②中文读者读得懂 ③文风沉稳。"
    "为求典雅而让读者读不懂, 是错译不是好译; 宁可用平实的说法, 也不用现代人分辨不出的古词。\n"
    "文风: 文白相济、庄重, 长句照译不走味; 忌真现代/口语词(力度/能量/搞/到位), "
    "但勿为文雅改动本已正确的词(瘸腿勿改跛足, 撩动/扶持保留)。\n"
    "忠实清晰: 不增不删不臆测; 清晰优先勿过压到歧义; designed/ordained→本当、ought→当, "
    "勿臆加原文没有的「欲/使」; 悬空「它们/其」改回名词。\n"
    "句式重组(关键): 英文长句与相关结构(so far…as to、not only…but、although…yet、such…as)"
    "按**中文语序自然重组**, 勿照搬英文从句嵌套与插入语位置; 相关连词用一套中文对应句式"
    "(so far…as to→「…到…地步, 足以使…」), **不重复连词**(勿「足以…却足以」)、不用「——」硬切主谓; "
    "让步/原因插入语(though…because…)移入括号或另起分句, 勿夹在主句中间断裂。\n"
    "术语(经文/书卷/人名一律和合本; 不同英文词必用不同中文): power权能/energy感力/efficacy功效/"
    "virtue德能; authority 位格治权→权柄、圣经权威性→权威; canonical 表语→正典/正典书卷、定语→正典的; "
    "priesthood祭司的职任、mediator中保、covenant约、righteousness义、justification称义、"
    "sanctification成圣、repentance悔改。表外词: 经文→和合本、神学→改革宗惯用、拿不准括注英文。\n"
    "勿增译(最高频): 希腊/拉丁引文只留原文+必要简短括注, 勿擅加重复整句中译。\n"
    "勿幻觉: 不加原文没有的概念(holy penmen≠圣灵默示)。勿漏: 保留所有[^N]与原文标点。\n"
    "古语词须现代可辨: 文白相济不等于用现代读者分不出的古词。反例 page/leaf→「一页/一叶」, "
    "英文是「页/张(正反两面)」之别, 中文「页」「叶」同音近义, 读者只看见同义反复; "
    "leaf 译「一张纸」。该词的语义区别若在中文里落不到实处, 就换清晰说法, 勿为存古牺牲达意。\n"
    "专名: 教派/异端/学派/人物用学界通用译名(诺洼天派/亚流派/俄利根、保罗非圣保罗), "
    "**首次出现括注原文**(如 诺洼天派(Novatians)、亚流派(Arians)), 后续不再重复括注。"
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
    ap.add_argument('--fresh-review', action='store_true', help='强制重审(忽略旧审校缓存)')
    ap.add_argument('--review-cached-only', action='store_true', help='审校只用已有缓存, 未命中用初译')
    ap.add_argument('--notes', action='store_true', help='边审校边总结改动类别, 写入 review_notes.md')
    args = ap.parse_args()

    tf.SYSTEM = SYSTEM + PLAN_GUIDE   # 方案指南(文风+近义防撞+双义+表外规则), 非死表
    tf.CACHE_DIR = ROOT / 'owen_raw/hebrews/zh_cache'
    tf.BATCH = 1
    global FRESH_REVIEW, REVIEW_CACHED_ONLY, NOTE_ISSUES
    FRESH_REVIEW = args.fresh_review
    REVIEW_CACHED_ONLY = args.review_cached_only
    NOTE_ISSUES = args.notes
    translate_page(args.page, args.resume, args.publish, args.review, args.limit)

if __name__ == '__main__':
    try:
        main()
    except tf.SessionLimitError as e:
        # 退出码 42 = 撞会话额度，与 translate_filibi 一致。
        # 早先这里没有捕获，撞墙时是 traceback + rc=1，批处理脚本分不出
        # 「额度用尽（等一等就能继续）」和「真故障（要人看）」——看守脚本
        # 就无从判断该不该自动续跑。
        print(f'\n!! 会话额度用尽，停止翻译：{e}', flush=True)
        print('   已翻段落都在 zh_cache 里，额度恢复后 --resume 直接续。', flush=True)
        sys.exit(42)
