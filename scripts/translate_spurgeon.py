#!/usr/bin/env python3
"""司布真《天国的福音——马太福音通俗释经》英译中。

复用 translate_filibi 的 CLI 调用与 md5 缓存（`tf.cached_translate`）。
CLI 一律带 CLI_TRIM_FLAGS —— 不发工具定义、MCP、CLAUDE.md、skills、hooks，
实测 29,142 → 287 token/次，见 scripts/claude_usage.py。

与贺智那条线（translate_hodge.py）的两点不同，都出在这本书的体裁上：

1. **红色粗斜体 span 里是圣经经文本身**，不是引语标记。贺智的红字是他引用
   经文中的片语，司布真这本是「先印一整节经文、再讲」，所以那一段必须按
   和合本译，不能自由发挥。
2. **是讲道，不是学术释经**。司布真面对的是会众，句子短、比喻多、直呼「弟兄」。
   译文要保住这股口气，不能译成贺智那种论证体。

产物：
  中文页  spurgeon/matthew/zh/<N>.md      （URL /spurgeon/matthew/zh/<N>/）
  中文raw spurgeon_raw/matthew/zh/<N>.md  （chmod 444）
  缓存    spurgeon_raw/zh_cache/          （md5 键，入 git，重跑全命中零 token）

用法:
    python3 scripts/translate_spurgeon.py --sections preface,1,2 --publish
    python3 scripts/translate_spurgeon.py --all --resume --publish
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

BOOK_CN = {'matthew': '马太福音'}
BOOK_EN = {'matthew': 'Matthew'}

SYSTEM = (
    "你是改革宗神学文献的专业译者，正在翻译司布真（C. H. Spurgeon, 1834-1892，"
    "伦敦大都会会幕牧师）的《天国的福音——马太福音通俗释经》。只输出译文，"
    "不要任何说明。\n"
    "\n"
    "★优先级（冲突时一律按此让步）：①意思正确 ②中文读者读得懂 ③文风。"
    "为求典雅而让读者读不懂，是错译不是好译。\n"
    "\n"
    "【这本书的体裁】这是讲道，不是学术注释。司布真面对的是会众：句子短，"
    "比喻多，常直接呼告（弟兄啊、你看）。译文要保住这股恳切亲切的口气，"
    "不要译成学究式的论证体，也不要用现代口语词（力度／搞／到位／的话）。"
    "庄重的现代书面语，略带文言色彩即可。\n"
    "\n"
    "【必须原样保留、不得翻译或改写的部分】\n"
    "1. 所有 HTML 标签与属性，如 <p ...>、<span style=\"color:#800000\">、"
    "</span>、markdown=\"1\"。\n"
    "2. markdown 标记：**加粗**、*斜体*、***粗斜体***。星号的个数与位置"
    "一个都不能变。\n"
    "3. 页界注释 <!-- PAGE 51 -->、隐藏锚点 <h2 class=\"scripture-anchor\" ...>。\n"
    "4. 行首的经文节号如 **18.**、**11, 12.**、**4-6.** 原样保留。\n"
    "\n"
    "【经文与释经要分开对待】\n"
    "· <span style=\"color:#800000\">***…***</span> 这种**粗斜体红色**整段，"
    "是马太福音的经文正文（英文底本是钦定本）。必须按和合本的用词与语感译，"
    "人名地名一律照和合本，不得自由改写。\n"
    "· 红色但**不加粗**的 *斜体* 片段，是司布真在讲解中回引经文的短语，"
    "同样照和合本用词，仍留在原 span 内。\n"
    "· 其余黑色正文是他的讲解，按上面的体裁要求译。\n"
    "\n"
    "【其他约定】\n"
    "· 书卷章节号要译（Matthew 3:5 → 马太福音 3:5），数字本身不动。\n"
    "· 神学术语按改革宗惯用译法；教会用语以和合本为准（称义／成圣／中保／"
    "恩典／信心／良心／圣礼）。\n"
    "· 引文后的 &c. 一律译成省略号……，不要译成「等」「等等」「云云」。\n"
    "· 近现代学者、释经家的音译人名，首次出现时括注英文原名；"
    "路德、加尔文这类定译不注。\n"
    "· 引号一律用弯引号“”（嵌套时内层用‘’），不要用直角引号「」。\n"
)


def split_page(text: str):
    m = re.match(r'^(---\n.*?\n---\n)(.*)$', text, re.S)
    return (m.group(1), m.group(2)) if m else ('', text)


def translatable(line: str) -> bool:
    """哪些行需要送翻。"""
    s = line.strip()
    if not s or s.startswith('<!--'):
        return False
    if re.fullmatch(r'-{3,}|<p[^>]*>|</p>', s):
        return False
    # 隐藏的分节锚点 h2 是纯结构（id/data-ref 下游要用），送翻会被改写
    if s.startswith('<h2 class="scripture-anchor"'):
        return False
    if re.fullmatch(r'<div class="commentary-anchor" id="[^"]+"></div>', s):
        return False
    if not re.search(r'[A-Za-z]{3}', s):
        return False
    return True


def translate_section(book: str, sec: str, resume: bool, publish: bool):
    src = ROOT / 'spurgeon' / book / f'{sec}.md'
    if not src.exists():
        print(f'  {src} 不存在，跳过', flush=True)
        return
    fm, body = split_page(src.read_text(encoding='utf-8'))
    lines = body.split('\n')
    idxs = [i for i, l in enumerate(lines) if translatable(l)]
    print(f'{book}/{sec}: {len(idxs)} 个可译单元', flush=True)

    zh_lines = tf.cached_translate([lines[i] for i in idxs], resume)
    out = list(lines)
    for i, zh in zip(idxs, zh_lines):
        out[i] = re.sub(r'<<<[^>]*>>>', '', zh).strip()

    def fv(k, default=''):
        m = re.search(rf'^{k}:\s*(.+)$', fm, re.M)
        return m.group(1).strip().strip('"') if m else default

    zh_dir = ROOT / 'spurgeon' / book / 'zh'
    zh_out = zh_dir / f'{sec}.md'
    # 时间戳用**本次翻译完成的真实时间**；已发布页重跑沿用原值
    date = ''
    if zh_out.exists():
        m = re.search(r'^date:\s*(.+)$', zh_out.read_text(encoding='utf-8'), re.M)
        date = m.group(1).strip() if m else ''
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M')

    title = fv('title')
    m = re.match(r'Matthew (\d+)', title)
    zh_title = f'马太福音 第 {m.group(1)} 章' if m else ('卷首题记' if sec == 'preface' else title)

    nav = ''
    for k, label in (('prev_section', 'prev_label'), ('next_section', 'next_label')):
        v = fv(k)
        if v:
            lb = fv(label)
            mm = re.match(r'Matthew (\d+)', lb)
            zh_lb = f'第 {mm.group(1)} 章' if mm else ('卷首题记' if lb == 'Introductory Note' else lb)
            nav += f'{k}: {v}\n{label}: "{zh_lb}"\n'

    zh_fm = ('---\n'
             'layout: spurgeon-chapter\n'
             f'book_id: {book}\n'
             f'book_name: "司布真《天国的福音——{BOOK_CN.get(book, book)}通俗释经》"\n'
             f'title: "{zh_title}"\n'
             f'date: {date}\n'
             + nav
             + f'en_url: "/spurgeon/{book}/{sec}/"\n'
             'zh: true\n'
             '---\n')
    page = zh_fm + '\n'.join(out)
    # 标点归一就在这里做，不要留到事后手动跑：--resume 重跑会把缓存里的
    # 直角引号与半角标点再写回来（以弗所书实测重跑一次回来 22 对）。
    page, n_q, n_h, warn = normalize_text(page)
    if warn:
        print(f'  ⚠ 标点归一跳过：{warn}', flush=True)
    elif n_q or n_h:
        print(f'  标点归一：引号 {n_q} 对 · 半角 {n_h} 处', flush=True)

    raw_dir = ROOT / 'spurgeon_raw' / book / 'zh'
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw = raw_dir / f'{sec}.md'
    if raw.exists():
        raw.chmod(0o644)
    raw.write_text(page, encoding='utf-8')
    raw.chmod(0o444)
    hit = sum(1 for i in idxs
              if (tf.CACHE_DIR / f'{tf.md5key(lines[i])}.txt').exists())
    print(f'  缓存命中 {hit} / {len(idxs)}', flush=True)

    if publish:
        zh_dir.mkdir(parents=True, exist_ok=True)
        zh_out.write_text(page, encoding='utf-8')
        print(f'✓ 中文页 → {zh_out}', flush=True)
        t = src.read_text(encoding='utf-8')
        if 'zh_url:' not in t:
            t = t.replace('\ndate:', f'\nzh_url: "/spurgeon/{book}/zh/{sec}/"\ndate:', 1)
            src.write_text(t, encoding='utf-8')
            print('✓ 英文页回填 zh_url', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', default='matthew')
    ap.add_argument('--sections', help='逗号分隔，如 preface,1,2')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true')
    ap.add_argument('--publish', action='store_true')
    a = ap.parse_args()

    tf.SYSTEM = SYSTEM
    tf.CACHE_DIR = ROOT / 'spurgeon_raw' / 'zh_cache'
    tf.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tf.BATCH = 1

    if a.all:
        secs = ['preface'] + [p.stem for p in sorted(
            (ROOT / 'spurgeon' / a.book).glob('[0-9]*.md'), key=lambda x: int(x.stem))]
    else:
        secs = [s.strip() for s in (a.sections or '').split(',') if s.strip()]
    if not secs:
        print('需要 --sections 或 --all', file=sys.stderr)
        return 1
    for s in secs:
        translate_section(a.book, s, a.resume, a.publish)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except tf.SessionLimitError as e:
        print(f'\n!! 会话额度用尽，停止：{e}', flush=True)
        print('   已翻段落都在 zh_cache 里，恢复后 --resume 直接续。', flush=True)
        sys.exit(42)
