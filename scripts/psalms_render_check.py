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

用法：
    python3 scripts/psalms_render_check.py            # 全书
    python3 scripts/psalms_render_check.py 23 104     # 只查这几篇
"""
import html
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'alexander/psalms'
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


def main(only=None):
    files = sorted(SRC.glob('*.md'), key=lambda p: (p.stem != 'preface', p.stem))
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
        def words(s):
            s = s.replace('\u2019', "'").replace('\u2018', "'")
            return Counter(WORD.findall(TAG.sub(' ', s)))
        before = words(body)
        after = words(html.unescape(out))
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
    sys.exit(main(sys.argv[1:] or None))
