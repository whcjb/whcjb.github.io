#!/usr/bin/env python3
"""渲染层校验：正文对不等于页面对。

markdown 层面数星号是**数不清开闭的**——`*a* 正文 *b*` 里中间那段会被误算成
一个强调，星号总数是偶数，页面上却整段跑飞。只有过一遍 kramdown、看渲染出来的
`<em>`，才知道斜体到底落在哪。

五项（skill old-book-ocr §4.4），都很便宜：
  渲染丢词    逐篇过 kramdown，比对渲染前后的实词集合——野生 `<` 被当标签，
              会从那里一路吃到下一个 `>`，中间的字在页面上直接消失
  斜体跑飞    `<em>` 内容首尾带空白 = 归一化没到不动点
  斜体过长    单个 `<em>` 跨越几百字 = 少了一个闭合星号，整段被拖进斜体
  锚点总数    每轮比对，数字必须稳定
  重复锚点    同一 id 出现多次，页内跳转会跳错位置

诗篇与以赛亚共用。以赛亚原先没有这道闸。

用法：
    python3 scripts/alexander_render_check.py                 # 诗篇全书
    python3 scripts/alexander_render_check.py isaiah          # 以赛亚全书
    python3 scripts/alexander_render_check.py isaiah 42 66    # 只查这几章
"""
import html
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOOKS = {'psalms': ROOT / 'alexander/psalms', 'isaiah': ROOT / 'alexander/isaiah'}
WORD = re.compile(r"[A-Za-zæœÆŒ][A-Za-zæœÆŒ'’-]*")
TAG = re.compile(r'<[^<>]+>')
EM = re.compile(r'<em>(.*?)</em>', re.S)
LONG_EM = 400          # 一个 <em> 超过这么多字符，多半是少了一个闭合星号


def render(md):
    r = subprocess.run(['kramdown', '--input', 'GFM'], input=md,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:200])
    return r.stdout


def body_of(path):
    t = path.read_text(encoding='utf-8')
    return t.split('---', 2)[2] if t.startswith('---') else t


def main(book='psalms', only=None):
    src = BOOKS[book]
    files = sorted(src.glob('*.md'), key=lambda p: (p.stem != 'preface', p.stem))
    if only:
        files = [f for f in files if f.stem in only]
    bad = Counter()
    for f in files:
        body = body_of(f)
        try:
            out = render(body)
        except Exception as e:                       # noqa: BLE001
            print(f'  [{f.stem}] 渲染失败 {e}')
            bad['渲染失败'] += 1
            continue

        # ① 渲染丢词：比对渲染前后的实词集合
        # kramdown 会把直撇号转成弯的（`God's` → `God’s`），比对前先归一，
        # 否则全书 144 篇都报「丢词」，真正的丢词反而淹了
        # 两边都要先 unescape：正文里的 `&lt;` `&nbsp;` 在渲染后变成 `<`、空格，
        # 不先归一就会把实体名本身（lt、nbs）当成「渲染后丢掉的词」——
        # 以赛亚全书 33 篇都会这么误报，真正的丢词反而淹在里面
        # **先剥标签、再 unescape**，顺序不能反：正文里的 `&lt;` 还是转义态，
        # 剥标签时不会被当成标签开头；先 unescape 会把它变成真的 `<`，
        # TAG 从那里一路吃到下一个 `>`，两边同时吃掉同一段，
        # 真正的「野生 < 吞词」就被自己掩盖了（第 14 章 28 个词那次）。
        # 剥完标签再 unescape，实体名（lt、nbs）才不会被当成词。
        def words(s):
            s = html.unescape(TAG.sub(' ', s))
            s = s.replace('\u2019', "'").replace('\u2018', "'")
            return Counter(WORD.findall(s))
        before = words(body)
        after = words(out)
        lost = before - after
        if lost:
            bad['渲染丢词'] += 1
            print(f'  [{f.stem}] 渲染后少了 {sum(lost.values())} 个词：'
                  f'{list(lost)[:8]}')

        # ② 斜体跑飞：<em> 首尾带空白
        for m in EM.finditer(out):
            inner = html.unescape(m.group(1))
            if inner != inner.strip():
                bad['斜体首尾带空白'] += 1
                print(f'  [{f.stem}] <em> 首尾带空白 {inner[:48]!r}')
                break

        # ③ 斜体过长
        for m in EM.finditer(out):
            if len(m.group(1)) > LONG_EM:
                bad['斜体过长'] += 1
                print(f'  [{f.stem}] <em> 长 {len(m.group(1))} 字符 '
                      f'{TAG.sub("", m.group(1))[:56]!r}…')
                break

        # ③b 斜体没闭合：**未转义星号个数是奇数**。数星号分不清开闭，
        # 但奇偶是硬的——奇数一定有一个落单的，页面上要么多出一个字面 `*`，
        # 要么半段话莫名其妙变成斜体。`<em>` 过长只抓得到跑飞得很远的那种，
        # 落单星号离下一个星号不远时它一声不吭（以赛亚 13 段里它只报了 4 段）。
        for line in body.split('\n'):
            if line.strip() and not line.startswith('<!--') \
                    and len(re.findall(r'(?<!\\)\*', line)) % 2:
                bad['斜体没闭合'] += 1
                print(f'  [{f.stem}] 未转义星号是奇数：'
                      f'{TAG.sub("", line)[:60]!r}…')
                break

        # ④⑤ 锚点
        ids = re.findall(r'id="([^"]+)"', body)
        dup = [k for k, v in Counter(ids).items() if v > 1]
        if dup:
            bad['重复锚点'] += 1
            print(f'  [{f.stem}] 重复 id {dup[:4]}')
    n_anchor = sum(len(re.findall(r'id="', body_of(f))) for f in files)
    print(f'查了 {len(files)} 篇；锚点合计 {n_anchor}')
    print('渲染层校验：' + ('全部通过 ✓' if not bad else
                          '，'.join(f'{k} {v} 篇' for k, v in bad.items())))
    return 1 if bad else 0


if __name__ == '__main__':
    args = sys.argv[1:]
    bk = args.pop(0) if args and args[0] in BOOKS else 'psalms'
    sys.exit(main(bk, args or None))
