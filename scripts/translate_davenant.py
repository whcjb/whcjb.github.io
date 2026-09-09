#!/usr/bin/env python3
"""translate_davenant.py — 达文南特《歌罗西书注释》英文页 → 中文页。

复用 translate_filibi 的 call_claude / cached_translate / md5 缓存
（走 claude_usage.CLI_TRIM_FLAGS，不发工具定义/MCP/CLAUDE.md/skills/hooks，
实测 29,142 → 287 token/次）。

只翻正文：front matter 与结构标签原样保留，按空行切块逐块送翻，
块内的 `<span class="dv-lemma">` / `<span class="dv-enum">` / `<strong>`
等标签由模型原位保留（SYSTEM 第 2 条）。

三类不送模型、确定性生成：
  · `# CHAPTER I`                       → `# 第一章`
  · `<p class="dv-scripture-ref">…</p>` → `歌罗西书 1:1-2`
  · `dv-scripture` 块里被注释的经文      → 送翻时附上**简体和合本**原文作参照
    （zh_cuv.json 是繁体且字间带空格，用 opencc 转简并去空格）

缓存: davenant_raw/colossians/zh_cache/   （翻译产物，必须保留，重跑成本极高）
中文 raw: davenant_raw/colossians/zh_chapters/N.md
中文页: davenant/colossians/N/zh/index.md （章级 zh，与欧文一致；
        build_commentaries_index 靠 `<N>/zh/` 是目录来认）

用法（项目根目录）：
    python3 -u scripts/translate_davenant.py --chapter 1 --resume
    python3 -u scripts/translate_davenant.py --all --resume --publish
    python3 -u scripts/translate_davenant.py --chapter 1 --limit 6 --dry-run
"""
import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf                      # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'davenant_raw' / 'colossians'
PUB = ROOT / 'davenant' / 'colossians'
CACHE = RAW / 'zh_cache'
ZH_RAW = RAW / 'zh_chapters'

BOOK_NAME_ZH = '歌罗西书·达文南特注释'
CH_ZH = {1: '第一章', 2: '第二章', 3: '第三章', 4: '第四章'}
ROMAN_ZH = {'I': '第一章', 'II': '第二章', 'III': '第三章', 'IV': '第四章'}

SYSTEM = (
    "你是一位精通改革宗神学与十七世纪英国神学的中文译者，正在翻译约翰·达文南特"
    "(John Davenant, 1572-1641，索尔兹伯里主教、多特会议英国代表)"
    "《歌罗西书注释》(Allport 1831 年英译本)。\n"
    "将英文译成简体中文，忠实原文，保持达文南特经院式的缜密论证与庄重文体。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
    "2. 原位保留所有 HTML 标签与实体不变：<span class=\"dv-lemma\"> <span class=\"dv-enum\">"
    " <strong> <em> <sup> <a …> 以及 &#x27; &quot; &amp; &lt; &gt; 等；"
    "标签的位置、属性、闭合一律照原样，只翻标签之间的文字\n"
    "3. `dv-lemma` 里是本段所要注释的那一小节经文（以 `]` 收尾）。"
    "**这一小节必须译成中文**，用和合本对应处的措辞，并同样以 `]` 收尾；"
    "例：<span class=\"dv-lemma\">Paul.]</span> → <span class=\"dv-lemma\">保罗。]</span>；"
    "<span class=\"dv-lemma\">An Apostle.]</span> → <span class=\"dv-lemma\">作使徒的。]</span>\n"
    "3b. 脚注标记 `[^dv1]` `[^dv198]` 等原样保留，位置不动，不要翻译、不要增删\n"
    "3c. 正文里罗马数字的经卷章节（Luke vi. 13 / Matth. xxviii. / Actsii.）"
    "改写成和合本格式：路加福音 6:13 / 马太福音 28 章 / 使徒行传 2 章\n"
    "4. 拉丁文、希腊文、希伯来文一律保留原文，其后用圆括号附中文译义，"
    "如 λόγος(道)、in solidum(整体地)；整句拉丁引文保留原文，括注中文大意\n"
    "5. 圣经书卷名、人名、地名用和合本标准译名：Colossians→歌罗西书，Paul→保罗，"
    "Timotheus→提摩太，Epaphras→以巴弗，Colosse→歌罗西，Onesimus→阿尼西母，"
    "Apostle→使徒，Old/New Testament→旧约/新约\n"
    "6. 章节引用格式：歌罗西书 1:1，罗马书 3:23（书卷名 章:节）\n"
    "7. 神学术语保持学术性：justification→称义，sanctification→成圣，covenant→圣约，"
    "righteousness→义，merit→功德，efficacy→功效，grace→恩典，"
    "predestination→预定，reprobation→弃绝，Papists/Romanists→天主教徒，"
    "Socinians→苏西尼派，Pelagians→柏拉糾派，Schoolmen→经院学者\n"
    "8. 教父与学者姓名首次出现保留原文并括注中文音译，"
    "如 Chrysostom(屈梭多模)、Jerome(耶柔米)、Augustine(奥古斯丁)、Aquinas(阿奎那)\n"
    "9. 保留段首编号（如 1. 2. 10. 31.）与 Firstly/Secondly 之类次序词的层级不变"
)

# ── 简体和合本（供经文块参照）────────────────────────────────────────────────
_CUV = None


def cuv_verse(chapter: int, verse: int) -> str:
    """→ 简体和合本 歌罗西书 chapter:verse；取不到返回 ''。"""
    global _CUV
    if _CUV is None:
        try:
            from opencc import OpenCC
            cc = OpenCC('t2s')
        except Exception:                                   # noqa: BLE001
            cc = None
        books = json.load((ROOT / 'scripts/zh_cuv.json').open(encoding='utf-8-sig'))
        col = next((b for b in books if b.get('name') == 'Colossians'), None)
        _CUV = {}
        if col:
            for ci, ch in enumerate(col['chapters'], 1):
                for vi, v in enumerate(ch, 1):
                    t = v.replace(' ', '')                  # 这份数据字间带空格
                    _CUV[(ci, vi)] = cc.convert(t) if cc else t
    return _CUV.get((chapter, verse), '')


def zh_ref(en_ref: str):
    """`Colossians 1:9,10,11` → (`歌罗西书 1:9-11`, 章, [节…])"""
    m = re.match(r'\s*Colossians\s+(\d+):([\d,\s]+)', en_ref)
    if not m:
        return en_ref, None, []
    ch = int(m.group(1))
    vs = [int(x) for x in re.findall(r'\d+', m.group(2))]
    if len(vs) > 1 and vs == list(range(vs[0], vs[-1] + 1)):
        span = f'{vs[0]}-{vs[-1]}'                          # 连号合并
    else:
        span = ','.join(str(v) for v in vs)
    return f'歌罗西书 {ch}:{span}', ch, vs


# ── 分块 ──────────────────────────────────────────────────────────────────────

def split_page(text):
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    return (m.group(1), m.group(2)) if m else ('', text)


STRUCT_ONLY = re.compile(r'^(?:</?div[^>]*>|---|\s*)$')
# 经文块的实际排版（publish_davenant_en.py 产出）：
#     <div class="dv-scripture" markdown="1">
#     <p class="dv-scripture-ref">Colossians 1:1,2</p>
#                                                    ← 空行
#     <strong>1.</strong> Paul, an Apostle …
#     </div>
# 所以 div 开标签和 ref 落在**同一块**，经文句在下一块且尾带 </div>。
REFDIV_RE = re.compile(
    r'^(<div class="dv-scripture"[^>]*>\s*\n)'
    r'<p class="dv-scripture-ref">([^<]*)</p>\s*$', re.S)


def blocks_of(body: str):
    """→ [(kind, text, …)]；kind ∈ pass / h1 / refdiv / scripture / body

    refdiv 的第 3 项是英文经文引用，scripture 的第 3 项是它所属的引用、
    第 4 项是块尾要还原的 </div>。
    """
    out = []
    pending_ref = None                      # 上一块是 refdiv 时，带下来给经文句
    for b in re.split(r'\n\s*\n', body):
        s = b.strip()
        if not s:
            out.append(('pass', b)); continue
        m = REFDIV_RE.match(s)
        if m:
            pending_ref = m.group(2).strip()
            out.append(('refdiv', b, pending_ref)); continue
        if s.startswith('# '):
            out.append(('h1', b)); pending_ref = None; continue
        if s.startswith('<p class="dv-scripture-ref">'):
            pending_ref = re.sub(r'<[^>]+>', '', s).strip()
            out.append(('refdiv', b, pending_ref)); continue
        if not re.search(r'[A-Za-z]{3}', s) or STRUCT_ONLY.match(s):
            out.append(('pass', b)); continue
        if pending_ref is not None:
            tail = ''
            core = s
            if core.endswith('</div>'):
                core = core[:-len('</div>')].rstrip()
                tail = '\n</div>'
            out.append(('scripture', core, pending_ref, tail))
            pending_ref = None
            continue
        out.append(('body', b))
    return out


def prompt_of(item):
    """送模型的文本。scripture 块附上简体和合本参照，参照进 md5 key，缓存才稳定。"""
    if item[0] != 'scripture':
        return item[1]
    _zh, ch, vs = zh_ref(item[2])
    ref = '\n'.join(f'{v}. {cuv_verse(ch, v)}' for v in vs if cuv_verse(ch, v))
    if not ref:
        return item[1]
    return (item[1] + '\n\n【和合本参照，经文句照抄和合本用词，不要自行翻译；'
            '英文只引了半句就只取和合本对应的半句】\n' + ref)


# ── 批量翻译（换掉 translate_filibi 里写死的书名标签）────────────────────────

# 模型偶尔把脚注定义的半角冒号译成全角（`[^dv14]：`）。kramdown 只认半角，
# 全角的那条定义整条不渲染，正文里的 `[^dv14]` 就以字面量印出来
# （中文第一章实测 3 条）。落盘前统一收回半角。
FULLWIDTH_FNDEF = re.compile(r'^(\[\^\w+\])：', re.M)


def normalize_fn_colon(text):
    return FULLWIDTH_FNDEF.sub(r'\1:', text)


def translate_batch(texts):
    parts = [f'<<<{i+1}>>>\n{t}' for i, t in enumerate(texts)]
    prompt = ('请按编号顺序翻译以下各段（达文南特《歌罗西书注释》），'
              '保持 <<<N>>> 格式输出：\n\n' + '\n\n'.join(parts))
    raw = tf.call_claude(prompt)
    res = [None] * len(texts)
    for m in re.finditer(r'<<<(\d+)>>>\s*\n(.*?)(?=<<<\d+>>>|\Z)', raw, re.S):
        i = int(m.group(1)) - 1
        if 0 <= i < len(texts):
            res[i] = m.group(2).strip()
    for i, t in enumerate(res):
        if t is None:
            try:
                res[i] = tf.call_claude(texts[i], timeout=180)
            except Exception:                               # noqa: BLE001
                res[i] = texts[i]
    return res


# ── 主流程 ────────────────────────────────────────────────────────────────────

def fmval(fm, key):
    m = re.search(rf'^{key}:\s*(.+)$', fm, re.M)
    return m.group(1).strip().strip('"') if m else ''


def translate_chapter(n: int, resume: bool, publish: bool, limit: int, dry: bool):
    src = PUB / f'{n}.md'
    fm, body = split_page(src.read_text(encoding='utf-8'))
    items = blocks_of(body)

    send = [i for i, it in enumerate(items) if it[0] in ('body', 'scripture')]
    if limit:
        send = send[:limit]
    texts = [prompt_of(items[i]) for i in send]
    hit = sum(1 for t in texts if (CACHE / f'{tf.md5key(t)}.txt').exists())
    print(f'ch{n}: 块 {len(items)}  需译 {len(send)}  缓存命中 {hit}'
          f'  英文 {sum(len(t) for t in texts):,} 字符', flush=True)
    if dry:
        for i in send[:6]:
            print(f'  [{items[i][0]}] {items[i][1][:90]}…')
        return

    zh_list = tf.cached_translate(texts, resume)
    zh = {i: z for i, z in zip(send, zh_list)}

    out = []
    for i, it in enumerate(items):
        kind = it[0]
        if kind == 'h1':
            m = re.match(r'#\s*CHAPTER\s+([IVX]+)', it[1].strip())
            out.append(f'# {ROMAN_ZH.get(m.group(1), CH_ZH.get(n, ""))}' if m else it[1])
        elif kind == 'refdiv':
            head = it[1][:it[1].index('<p class="dv-scripture-ref">')]
            out.append(head + f'<p class="dv-scripture-ref">{zh_ref(it[2])[0]}</p>')
        elif i in zh:
            t = re.sub(r'<<<[^>]*>>>', '', zh[i]).strip()
            if kind == 'scripture':
                t += it[3]                      # 还原块尾的 </div>
            out.append(t)
        else:
            out.append(it[1])
    zh_body = '\n\n'.join(out)

    ZH_RAW.mkdir(parents=True, exist_ok=True)
    zh_page_dir = PUB / str(n) / 'zh'
    existing = zh_page_dir / 'index.md'
    date = None
    if existing.exists():
        m = re.search(r'^date:\s*(.+)$', existing.read_text(encoding='utf-8'), re.M)
        date = m.group(1).strip() if m else None
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M')

    nav = []
    if (PUB / str(n - 1) / 'zh' / 'index.md').exists():
        nav += [f'prev_url: "/davenant/colossians/{n-1}/zh/"',
                f'prev_label: "{CH_ZH.get(n-1, "")}"']
    if (PUB / str(n + 1) / 'zh' / 'index.md').exists():
        nav += [f'next_url: "/davenant/colossians/{n+1}/zh/"',
                f'next_label: "{CH_ZH.get(n+1, "")}"']

    fm_zh = ('---\n'
             'layout: davenant-chapter\n'
             'book_id: colossians\n'
             f'book_name: "{BOOK_NAME_ZH}"\n'
             f'chapter: {n}\n'
             f'title: "{CH_ZH.get(n, "")}"\n'
             f'date: {date}\n'
             'zh: true\n'
             + (('\n'.join(nav) + '\n') if nav else '')
             + f'en_url: "/davenant/colossians/{n}/"\n'
             '---\n')
    page = normalize_fn_colon(fm_zh + zh_body)

    raw_out = ZH_RAW / f'{n}.md'
    if raw_out.exists():
        raw_out.chmod(0o644)
    raw_out.write_text(page, encoding='utf-8')
    raw_out.chmod(0o444)
    print(f'✓ 中文 raw → {raw_out}  (chmod 444)', flush=True)

    if publish:
        zh_page_dir.mkdir(parents=True, exist_ok=True)
        existing.write_text(page, encoding='utf-8')
        print(f'✓ 中文页 → {existing}', flush=True)
        t = src.read_text(encoding='utf-8')
        if 'zh_url:' not in t:
            t = t.replace('---\n\n# CHAPTER',
                          f'zh_url: "/davenant/colossians/{n}/zh/"\n---\n\n# CHAPTER', 1)
            src.write_text(t, encoding='utf-8')
            print(f'✓ 英文页回填 zh_url → {src}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--chapter', type=int)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    if not (a.chapter or a.all):
        sys.exit('要 --chapter N 或 --all')

    tf.SYSTEM = SYSTEM + tf.SCRIPTURE_RULE
    tf.CACHE_DIR = CACHE
    tf.translate_batch = translate_batch        # cached_translate 走模块级查找

    for n in ([a.chapter] if a.chapter else [1, 2, 3, 4]):
        try:
            translate_chapter(n, a.resume, a.publish, a.limit, a.dry_run)
        except tf.SessionLimitError as e:
            print(f'✗ ch{n} 会话额度用尽，已翻部分留在缓存：{e}', flush=True)
            sys.exit(42)


if __name__ == '__main__':
    main()
