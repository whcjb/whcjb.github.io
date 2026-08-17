#!/usr/bin/env python3
"""修正 new-translation.md 里 ff 系列脚注「引用与定义错位一号」。

诊断（每一步都有实证，不是推断）：
- 底本的印刷标记编号 64–156 共 92 个，附录条目 ftf64–ftf155 也是 92 条；
- 低号段吻合：[^ff78] 在 “my ears hast thou made fit” ↔ ftf78「Lat. aptasti」；
- 高号段整体差一：[^ff92] 在 “He ruleth over the world” ↔ ftf91「Dominatur seculo」，
  [^ff100] 在 “to the locusts” ↔ ftf99「法文作 to the grasshopper」，
  [^ff130] 在 “the wickedness” ↔ ftf129「法文作 sin」；
- 断点在印刷标记 91（诗篇 66:6 “Through the river”）：**附录漏收了这一条**，
  于是其后附录编号一路比印刷标记少 1。
- 五个分卷标题各有一条注（ftf64/79/95/109/122 = 第一至第五卷范围说明），
  它们的标记分别是 FF64 / <sup>79</sup> / <sup>96</sup> / <sup>110</sup> / <sup>123</sup>，
  加上文末 <sup>156</sup>，都因只匹配小写 f[a-e]\\d+ 的正则而没被识别成引用。

按位置对应后 92 条定义恰好一一落位、无冲突：
    印刷 64 → ftf64        印刷 65–90  → ftf65–ftf90
    印刷 91 → （底本缺）    印刷 92–155 → ftf91–ftf154
    印刷 156 → ftf155
即：引用号 92–155 各减 1，91 处的引用删除（保留它只会显示别人的注），
6 个未识别标记补成引用。

用法:
    python3 scripts/fix_new_translation_ff_offset.py --dry-run
    python3 scripts/fix_new_translation_ff_offset.py
"""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / 'calvin/psalms-2-en/new-translation.md'

# 未被识别的 6 个标记 → 其正确的定义号
BARE = [
    ('<p style="text-align:center; font-size:22px; font-weight:bold; margin:18px 0 12px;"'
     ' markdown="1"><span style="color:#800000">FF64</span></p>\n\n', '', None),  # 见下方特判
    ('PART SECOND.<sup>79</sup>', 'PART SECOND.[^ff79]', 79),
    ('PART THIRD<sup>96</sup>', 'PART THIRD[^ff95]', 95),
    ('PART FOURTH.<sup>110</sup>', 'PART FOURTH.[^ff109]', 109),
    ('PART FIFTH.<sup>123</sup>', 'PART FIFTH.[^ff122]', 122),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    ed = json.loads((ROOT / 'calvin_raw/psalms-2/footnote_defs.json')
                    .read_text(encoding='utf-8'))
    t = PAGE.read_text(encoding='utf-8')
    body, sep, _tail = t.partition('\n[^ff')
    if not sep:
        raise SystemExit('找不到定义区')

    # 1) 删掉 91 处的引用：底本漏收该条，留着只会显示 ftf91（别处的注）
    n_del = len(re.findall(r'\s*\[\^ff91\](?!:)', body))
    body = re.sub(r'\s*\[\^ff91\](?!:)', '', body, count=1)

    # 2) 引用号 92–155 各减 1（升序处理会连锁覆盖，先换占位符）
    def shift(m):
        n = int(m.group(1))
        return f'[[SH{n - 1}]]' if 92 <= n <= 155 else m.group(0)
    body = re.sub(r'\[\^ff(\d+)\](?!:)', shift, body)
    n_shift = len(re.findall(r'\[\[SH\d+\]\]', body))
    body = re.sub(r'\[\[SH(\d+)\]\]', r'[^ff\1]', body)

    # 3) 补上 6 个未识别的标记
    n_bare = 0
    for old, new, _code in BARE[1:]:
        if old in body:
            body = body.replace(old, new, 1); n_bare += 1
        else:
            print(f'  ⚠ 未找到标记: {old[:40]}')
    # FF64 单独处理：它印在 “PART FIRST.” 之前，统一挪到标题之后
    m = re.search(r'<p[^>]*markdown="1"><span style="color:#800000">FF64</span></p>\s*', body)
    if m:
        body = body[:m.start()] + body[m.end():]
        body = body.replace('PART FIRST.', 'PART FIRST.[^ff64]', 1); n_bare += 1
    else:
        print('  ⚠ 未找到 FF64')
    # 文末 <sup>156</sup> → [^ff155]
    if '<sup>156</sup>' in body:
        body = body.replace('<sup>156</sup>', '[^ff155]', 1); n_bare += 1

    # 4) 定义区按落位后的引用重建
    used = sorted({int(x) for x in re.findall(r'\[\^ff(\d+)\](?!:)', body)})
    defs = '\n\n'.join(f'[^ff{n}]: {ed["ftf" + str(n)]}' for n in used
                       if f'ftf{n}' in ed)
    missing = [n for n in used if f'ftf{n}' not in ed]

    print(f'删除无定义引用 {n_del} 处；引用号下移 {n_shift} 个；补回标记 {n_bare} 个')
    print(f'落位定义 {len(used)} 条（{used[0]}–{used[-1]}）'
          + (f'；缺定义 {missing}' if missing else '；无缺失'))
    gaps = [n for n in range(used[0], used[-1] + 1) if n not in used]
    print('号段空缺:', gaps or '无')

    if not a.dry_run:
        PAGE.write_text(body.rstrip() + '\n\n' + defs + '\n', encoding='utf-8')
        print('已写入', PAGE.name)


if __name__ == '__main__':
    main()
