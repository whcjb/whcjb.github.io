#!/usr/bin/env python3
"""qa_davenant_zh_ratio.py —— 中译「长度比」闸：找**译到一半就断掉**的块。

起因：`[^dv40]`（Justin 传 + Bede 传，英文 3,344 字符）的中译只有 423 字符——
从 Justin 结尾处整段截断，Bede 半篇一个字没有。产物、渲染层、既有的两道译后闸
（`davenant_zh_check` / `davenant_zh_leakscan`）**全都看不出来**：标签数对得上、
没有夹英文、块也不空。只有拿它对应的英文比长度才看得见。
后来这道闸又抓出 `[^dv22]`（2,048 → 68 字符）。

### 怎么对齐

⚠️ **不能按块下标对齐**。中文页把三行章题并成一行、锚点与小标题的分块也不完全
一致，按下标比会整页错位（第一版实测：`EN: But here a doubt arises` 对上
`ZH: <div class="dv-anchor">`，报出 97 条全是假的）。改成两种**天然同一**的锚：

  · **脚注**：按 `[^dvN]` 的 id 精确配对，一一对应，不受分块影响
  · **节**：按 `<div class="dv-anchor" id="colossians-N-M">` 切段，id 两边相同

### 阈值

中译一般在 0.30–0.55（汉字信息密度高），实测全书脚注中位数 0.39、节中位数 0.33。
低于 0.22 报警。英文短于 150 字符的不比——标题与 `Corollaries.` 这类块比值抖动
没有意义。

⚠️ 这是**看趋势**的闸：拉丁引诗整块照抄时比值会很高，经文块引和合本时会偏低，
都不是错。报出来的要人工看一眼。

用法：
    python3 scripts/qa_davenant_zh_ratio.py
    python3 scripts/qa_davenant_zh_ratio.py --min-ratio 0.25
"""
import argparse
import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'davenant' / 'colossians'
MIN_RATIO = 0.22
MIN_LEN = 150
# ⚠️ 锚点是 `<div class="dv-anchor" id="…"></div>`，但产物里 `</div>` 另起一行，
# 正则写成一整串会一条也匹配不上（第一版实测「节」比了 0 项还不报错）。
ANCHOR = re.compile(r'<div class="dv-anchor" id="([^"]+)">')


def dense(s):
    """剥掉标签、脚注引用、页码 span 之后的字符数。"""
    s = re.sub(r'<span class="dv-fn-page">.*?</span>', ' ', s)
    s = re.sub(r'<[^>]+>|\[\^[a-z0-9]+\]|&[a-z#0-9]+;', ' ', s)
    return len(re.sub(r'\s+', '', s))


def notes(path):
    t = path.read_text(encoding='utf-8')
    return {m.group(1): dense(m.group(2))
            for m in re.finditer(r'^\[\^(dv\d+)\]:(.*)$', t, re.M)}


def sections(path):
    """按 dv-anchor 的 id 切段 → {id: 该节的实词字符数}。脚注区不算。"""
    t = path.read_text(encoding='utf-8')
    # ⚠️ 只剥**开头的 front matter**。产物里脚注区之前还有一条 `---` 分隔线，
    # 按 `split('---')[-1]` 取最后一段会只剩脚注区，锚点一个也找不到
    # （第一版实测「节」比了 0 项，却不报错）。
    t = re.sub(r'\A---\n.*?\n---\n', '', t, flags=re.S)
    t = re.sub(r'^\[\^dv\d+\]:.*$', '', t, flags=re.M)
    parts = ANCHOR.split(t)
    out = {}
    for i in range(1, len(parts) - 1, 2):
        out[parts[i]] = dense(parts[i + 1])
    return out


def compare(name, en, zh, lo, min_len):
    rs, bad = [], []
    for k, e in en.items():
        if k not in zh or e < min_len:
            continue
        r = zh[k] / e
        rs.append(r)
        if r < lo:
            bad.append((k, e, zh[k], r))
    mid = statistics.median(rs) if rs else 0
    print(f'  {name}：比了 {len(rs)} 项，中位数 {mid:.2f}，低于 {lo} 的 {len(bad)} 项')
    for k, e, z, r in sorted(bad, key=lambda x: x[3]):
        print(f'    ⚠️ {k}  英文 {e} / 中文 {z} = {r:.2f}')
    return len(bad)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--min-ratio', type=float, default=MIN_RATIO)
    ap.add_argument('--min-len', type=int, default=MIN_LEN)
    a = ap.parse_args()
    bad = 0
    for n in (1, 2, 3, 4):
        en, zh = PUB / f'{n}.md', PUB / str(n) / 'zh' / 'index.md'
        if not (en.exists() and zh.exists()):
            continue
        print(f'ch{n}')
        bad += compare('脚注', notes(en), notes(zh), a.min_ratio, a.min_len)
        bad += compare('节  ', sections(en), sections(zh), a.min_ratio, a.min_len)
    print(f'Gate R 中译长度比：可疑 {bad} 项')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
