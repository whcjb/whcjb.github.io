#!/usr/bin/env python3
"""达拉谟《启示录注释》英译中。

复用 translate_filibi 的 CLI 调用与 md5 缓存。CLI 一律带 CLI_TRIM_FLAGS
——不发工具定义、MCP、CLAUDE.md、skills、hooks，实测 29,142 → 287 token/次。

与前三条线（贺智／司布真）的不同，都出在这本书的年代与体裁上：

1. **十七世纪苏格兰英语**。拼写、句法都是 1658 年的（`spirituall` `accesse`
   `dayes` `sheweth` `doth` `hath`），长句套长句，一句能跨半页。译文按现代
   中文书面语重组语序，但不得因为难读就删减从句。
2. **讲道体，不是注疏体**。原书是讲章整理稿，有对会众的直接呼告，也有
   「第一…第二…第三」的条分缕析。两种语气都要保住。
3. **离题论述（Digressions）自成文体**。全书 37 篇，专论教会治理、圣礼、
   良心、逼迫等题，是神学论文而非解经，用词要更严谨。
4. 达拉谟是坚定的**无千禧年／历史主义**解经者，把启示录读作教会史的预言。
   涉及罗马教廷、敌基督的判语是他的本意，照译，不作缓和。

产物：
  中文页  spurgeon 同构 → durham/revelation/zh/<N>.md
  中文raw durham_raw/revelation/zh/<N>.md（chmod 444）
  缓存    durham_raw/zh_cache/

用法:
    python3 scripts/translate_durham.py --sections preface,1 --publish
    python3 scripts/translate_durham.py --all --resume --publish
"""
import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import translate_filibi as tf                     # noqa: E402
from normalize_zh_quotes import normalize_text    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BOOK = 'revelation'

SYSTEM = (
    "你是改革宗神学文献的专业译者，正在翻译詹姆斯·达拉谟（James Durham, "
    "1622-1658，苏格兰盟约派，格拉斯哥牧师）的《启示录注释》（1658）。"
    "只输出译文，不要任何说明。\n"
    "\n"
    "★优先级（冲突时一律按此让步）：①意思正确 ②中文读者读得懂 ③文风沉稳。"
    "为求典雅而让读者读不懂，是错译不是好译。\n"
    "\n"
    "【原文年代】这是十七世纪苏格兰英语：拼写是当时的（spirituall / accesse / "
    "dayes / sheweth / doth / hath），长句套长句，一句可跨半页。译文按现代中文"
    "书面语重组语序，该拆句就拆；但**不得因为难读就删减从句或合并论点**。\n"
    "\n"
    "【体裁】原书是讲章整理稿：既有对会众的直接呼告（弟兄啊、你看），也有"
    "「第一…第二…第三…」的条分缕析。两种语气都要保住，不要一律抹平成论文腔。"
    "另有三十余篇「离题论述」（标题以 ### 起首，如 Concerning Church-government），"
    "那是神学专论而非解经，用词更严谨些。\n"
    "\n"
    "【立场】达拉谟是无千禧年／历史主义解经者，把启示录读作教会史的预言，"
    "对罗马教廷与敌基督的判语是他的本意，照译，不作缓和，也不加按语。\n"
    "\n"
    "【必须原样保留、不得翻译或改写的部分】\n"
    "1. 所有 HTML 标签与属性。\n"
    "2. markdown 标记：`#`/`##`/`###` 标题层级、**加粗**、*斜体*，"
    "星号与井号的个数一个都不能变。\n"
    "3. 页界注释 <!-- PAGE 51 -->、锚点 <div class=\"commentary-anchor\" ...>。\n"
    "4. 讲次标题里的经文范围原样保留：`## LECTURE V (11:15–19)` 译作"
    "`## 第五讲（11:15–19）`，罗马数字转中文序数，括号里的章节号不动。\n"
    "5. `# CHAP. 7` 译作 `# 启示录第 7 章`。\n"
    "\n"
    "【其他约定】\n"
    "· 经文引用照和合本用词；书卷章节号要译（Rev. 3:5 → 启示录 3:5），"
    "数字本身不动。\n"
    "· 神学术语按改革宗惯用译法（称义／成圣／中保／恩典／圣礼／良心）。\n"
    "· 引文后的 &c. 一律译成省略号……，不要译成「等」「等等」「云云」。\n"
    "· 近现代学者、释经家的音译人名，首次出现时括注英文原名；"
    "路德、加尔文这类定译不注。\n"
    "· 引号一律用弯引号“”（嵌套时内层用‘’），不要用直角引号「」。\n"
)


def split_page(text: str):
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    return (m.group(1), m.group(2)) if m else ('', text)


def translatable(line: str) -> bool:
    s = line.strip()
    if not s or s.startswith('<!--'):
        return False
    if re.fullmatch(r'-{3,}|<p[^>]*>|</p>', s):
        return False
    if re.fullmatch(r'<div class="commentary-anchor" id="[^"]+"></div>', s):
        return False
    if not re.search(r'[A-Za-z]{3}', s):
        return False
    return True



# ── 超长段按句子切片送译 ──────────────────────────────────────────────
# 达拉谟十七世纪的长句本来就绵密，Gate 5g 又把 1,348 处跨页断句合并了回去，
# 于是段落特别大：全书 2,861 段里 >300 词 733 个、>800 词 80 个、最大 3,520 词。
# 整段送译一次要模型吐出上千词，慢且有截断风险（序言第一段 1,701 词跑了五分钟
# 还没回）。这里只在**送译这一层**切片，译完按原顺序拼回同一段——产物里仍是
# 一段，版面与 fix_page_split_paragraphs 的成果都不受影响。
# 附带好处：缓存粒度变细，--resume 续得更准，不会因一个巨段失败就整段重来。
SLICE_MAX_WORDS = 350
_ABBR = re.compile(r'\b(?:viz|chap|ver|vers|cap|q|ans|answ|obj|Mr|St|i\.e|e\.g)\.$', re.I)


def slice_long(text: str, limit: int = SLICE_MAX_WORDS):
    """→ 若干片。切点取句末标点后的空白，避开缩写。不超限就原样返回一片。"""
    if len(text.split()) <= limit:
        return [text]
    parts, cur = [], ''
    for chunk in re.split(r'(?<=[.!?;:])\s+', text):
        cand = (cur + ' ' + chunk).strip() if cur else chunk
        if cur and len(cand.split()) > limit and not _ABBR.search(cur):
            parts.append(cur)
            cur = chunk
        else:
            cur = cand
    if cur:
        parts.append(cur)
    return parts


def translate_section(sec: str, resume: bool, publish: bool):
    src = ROOT / 'durham' / BOOK / f'{sec}.md'
    if not src.exists():
        print(f'  {src} 不存在，跳过', flush=True)
        return
    fm, body = split_page(src.read_text(encoding='utf-8'))
    lines = body.split('\n')
    idxs = [i for i, l in enumerate(lines) if translatable(l)]
    print(f'{BOOK}/{sec}: {len(idxs)} 个可译单元', flush=True)

    # 切片：记下每段切成了几片，译完按 owner 拼回
    pieces, owner = [], []
    for i in idxs:
        sl = slice_long(lines[i])
        pieces += sl
        owner += [i] * len(sl)
    n_split = len(pieces) - len(idxs)
    if n_split:
        print(f'  超长段切片：{len(idxs)} 段 → {len(pieces)} 片', flush=True)

    zh_pieces = tf.cached_translate(pieces, resume)
    merged = {}
    for i, zh in zip(owner, zh_pieces):
        zh = re.sub(r'<<<[^>]*>>>', '', zh).strip()
        merged[i] = (merged[i] + ' ' + zh).strip() if i in merged else zh
    out = list(lines)
    for i, zh in merged.items():
        out[i] = zh

    def fv(k, default=''):
        m = re.search(rf'^{k}:\s*(.+)$', fm, re.M)
        return m.group(1).strip().strip('"') if m else default

    zh_dir = ROOT / 'durham' / BOOK / 'zh'
    zh_out = zh_dir / f'{sec}.md'
    date = ''
    if zh_out.exists():
        m = re.search(r'^date:\s*(.+)$', zh_out.read_text(encoding='utf-8'), re.M)
        date = m.group(1).strip() if m else ''
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M')

    def zh_label(lb):
        m = re.match(r'Revelation (\d+)', lb)
        if m:
            return f'启示录 第 {m.group(1)} 章'
        return '致读者' if lb == 'To the Reader' else lb

    nav = ''
    for k, label in (('prev_section', 'prev_label'), ('next_section', 'next_label')):
        v = fv(k)
        if v:
            nav += f'{k}: {v}\n{label}: "{zh_label(fv(label))}"\n'

    zh_fm = ('---\n'
             'layout: durham-chapter\n'
             f'book_id: {BOOK}\n'
             'book_name: "达拉谟《启示录注释》"\n'
             f'title: "{zh_label(fv("title"))}"\n'
             f'date: {date}\n'
             + nav
             + f'en_url: "/durham/{BOOK}/{sec}/"\n'
             'zh: true\n'
             '---\n')
    page = zh_fm + '\n'.join(out)
    page, n_q, n_h, warn = normalize_text(page)
    if warn:
        print(f'  ⚠ 标点归一跳过：{warn}', flush=True)
    elif n_q or n_h:
        print(f'  标点归一：引号 {n_q} 对 · 半角 {n_h} 处', flush=True)

    raw_dir = ROOT / 'durham_raw' / BOOK / 'zh'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f'{sec}.md'
    if raw.exists():
        raw.chmod(0o644)
    raw.write_text(page, encoding='utf-8')
    raw.chmod(0o444)
    hit = sum(1 for p in pieces
              if (tf.CACHE_DIR / f'{tf.md5key(p)}.txt').exists())
    print(f'  缓存命中 {hit} / {len(pieces)} 片', flush=True)

    if publish:
        zh_dir.mkdir(parents=True, exist_ok=True)
        zh_out.write_text(page, encoding='utf-8')
        print(f'✓ 中文页 → {zh_out}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sections')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    a = ap.parse_args()

    tf.SYSTEM = SYSTEM
    tf.CACHE_DIR = ROOT / 'durham_raw' / 'zh_cache'
    tf.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tf.BATCH = 1

    if a.all:
        secs = ['preface'] + [p.stem for p in sorted(
            (ROOT / 'durham' / BOOK).glob('[0-9]*.md'), key=lambda x: int(x.stem))]
    else:
        secs = [s.strip() for s in (a.sections or '').split(',') if s.strip()]
    if not secs:
        print('需要 --sections 或 --all', file=sys.stderr)
        return 1
    for s in secs:
        translate_section(s, a.resume, a.publish)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except tf.SessionLimitError as e:
        print(f'\n!! 会话额度用尽，停止：{e}', flush=True)
        print('   已翻段落都在 zh_cache 里，恢复后 --resume 直接续。', flush=True)
        sys.exit(42)
