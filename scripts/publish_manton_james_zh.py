#!/usr/bin/env python3
"""manton_raw/james/zh_chapters/*.md → manton/james/<seg>/zh/（中文版发布）

英文版在 manton/james/<seg>/，中文版出到其下的 zh/ 子路径（欧文同款「章级 zh」），
不覆盖英文。build_commentaries_index.py 的 _lang_variants 会自动认出这种布局。

经节锚点与英文版同源：zh raw 里保留着 <!--VERSE N--> 标记，
这里复用英文发布脚本的 transform_body，锚点 id 与英文版**完全一致**
（james-<ch>-<v>），所以中英两侧的 verse-nav / verse-index 指向同一套编号。

用法：
    python3 scripts/publish_manton_james_zh.py            # 有哪些译完就发哪些
    python3 scripts/publish_manton_james_zh.py --section 1
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from publish_manton_james import transform_body, front_matter   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'manton_raw' / 'james' / 'zh_chapters'
OUT = ROOT / 'manton' / 'james'

BOOK_ID = 'james'
BOOK_NAME = '曼顿《雅各书注释》'
AUTHOR = '托马斯·曼顿'

# (raw 名, 路径段, 中文标题, 导航 label, 英文页 chapter 号或 None)
SECTIONS = [
    ('dedicatory',    'dedicatory',    '献辞',       '献辞',     None),
    ('advertisement', 'advertisement', '谨告读者',   '谨告读者', None),
    ('preface',       'preface',       '全书序论',   '序论',     None),
    ('1', '1', '第一章', '第一章', 1),
    ('2', '2', '第二章', '第二章', 2),
    ('3', '3', '第三章', '第三章', 3),
    ('4', '4', '第四章', '第四章', 4),
    ('5', '5', '第五章', '第五章', 5),
]


def transform(raw: str) -> str:
    """raw zh → 发布正文。skill 05 §1 的规范化动作。"""
    # 1. Claude 偶尔吐出的分段标记（含各种变体与行内残留）
    text = re.sub(r'<<<[^>]*?>>>', '', raw)
    # 2. abut-bold 合并（principles §0.4）
    text = text.replace('****', '')
    # 3. split italic quote（principles §0.5）
    QO = r'["“”\'‘’]'
    QD = r'["“”]'
    text = re.sub(rf'\*({QO})\*([^*]+?)\*([,.;:!?]*{QO})\*', r'*\1\2\3*', text)
    text = re.sub(rf'\*({QO})\*([^*]+?{QD})', r'*\1\2*', text)
    # 4. 模型偶尔把 front-matter 式的键名译成中文；本书 raw 无 front matter，
    #    真出现就是幻觉，直接剥掉这类孤立行
    text = re.sub(r'^(?:章|章节|上一节|下一节)[：:]\s*\d+\s*$', '', text, flags=re.M)
    return text.strip()


def publish_one(raw_name, seg, title, label, ch, seq_idx, now):
    src = RAW / f'{raw_name}.md'
    if not src.exists():
        return None
    body = transform(src.read_text(encoding='utf-8'))
    # 锚点与英文版同源：章节页用真实章号，前置三篇用 0（不产生经节锚点）
    body, n_anchor = transform_body(body, ch if ch else 0)

    prev = SECTIONS[seq_idx - 1] if seq_idx > 0 else None
    nxt = SECTIONS[seq_idx + 1] if seq_idx + 1 < len(SECTIONS) else None

    fm = front_matter(
        layout='manton-chapter', book_id=BOOK_ID, book_name=BOOK_NAME,
        author=AUTHOR, title=title, date=now, zh='true',
        en_url=f'/manton/james/{seg}/',
        chapter=ch if ch else None,
        prev_url=f'/manton/james/{prev[1]}/zh/' if prev else None,
        prev_label=prev[3] if prev else None,
        next_url=f'/manton/james/{nxt[1]}/zh/' if nxt else None,
        next_label=nxt[3] if nxt else None,
    )
    d = OUT / seg / 'zh'
    d.mkdir(parents=True, exist_ok=True)
    heading = f'# 雅各书 · {title}' if ch else f'# {title}'
    content = fm + '\n' + heading + '\n\n' + body + '\n'
    (d / 'index.md').write_text(content, encoding='utf-8')
    add_zh_url_to_en(seg)
    return seg, len(content), n_anchor


def add_zh_url_to_en(seg: str) -> None:
    """给对应英文页补 `zh_url:`，让它显示「中文版 ↔」切换。

    幂等：已有就不动。放在这里而不是英文发布脚本里，是因为只有中文页**真的
    发出来**之后那个链接才不是死链——英文版早于中译几周上线，提前写死会指向 404。
    """
    en = OUT / seg / 'index.md'
    if not en.exists():
        return
    t = en.read_text(encoding='utf-8')
    if re.search(r'^zh_url:', t, flags=re.M):
        return
    # 插在 front matter 的 date 行之后（date 必有，见 CLAUDE.md 约定）
    new = re.sub(r'^(date: .*)$', rf'\1\nzh_url: "/manton/james/{seg}/zh/"',
                 t, count=1, flags=re.M)
    if new != t:
        en.write_text(new, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section')
    a = ap.parse_args()
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    done = []
    for i, (raw_name, seg, title, label, ch) in enumerate(SECTIONS):
        if a.section and raw_name != a.section:
            continue
        r = publish_one(raw_name, seg, title, label, ch, i, now)
        if r:
            done.append(r)
            print(f'  ✓ {r[0]:14s} {r[1]:8,d} chars  anchors={r[2]}')
    if not done:
        print('  （尚无可发布的中文 raw）')
    return done


if __name__ == '__main__':
    main()
