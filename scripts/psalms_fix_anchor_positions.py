#!/usr/bin/env python3
"""把落错位置的脚注标记搬回英文版对应的那句话后面（诗篇中译）。

`psalms_footnote_anchors.py` 是让 haiku 在中文段里挑锚点、脚本再做插入，
校验只保证「锚点在段内唯一」，不保证「锚点是对的」。模型偶尔把一段里的几个
标记全丢到段末，症状是页面上出现挤在一起的上标（如 `fc67fc66`——编号还是
倒的，因为是倒着插的）。

全卷扫「相邻且编号递减」的标记对，共 9 处；连同诗篇 69:1-5 里位置明显不对的
fc65，逐条按英文版的位置重新落点。下表里每条都核对过脚注正文内容：

  code → 中文锚点（标记插在这段文字正后方），锚点必须在该章正文中唯一出现。

只动标记位置，一个字的译文都不改。可重复执行：标记已在目标位置就跳过。

用法：
    python3 scripts/psalms_fix_anchor_positions.py            # 报告
    python3 scripts/psalms_fix_anchor_positions.py --apply
之后必须重跑 publish_psalms_zh.py 才会反映到 calvin/psalms-*/。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (卷, 篇号, code, 锚点)
FIXES = [
    # 18:26-27 fa380「向着」← With the pure；fa381「谦卑/受苦」← save the afflicted
    (1, 18, 'fa380', '**26.** 清洁的人'),
    (1, 18, 'fa381', '困苦的百姓，你必拯救'),
    # 38:7 fb51「炙热如焚」← my reins are filled with burning
    (1, 38, 'fb51', '我满腰是火'),
    # 38:21 fb58 ← be not far from me
    (1, 38, 'fb58', '不要远离我'),
    # 47 fb184「遍及全世界」/ fb185 ← the faithful through the whole world
    (1, 47, 'fb184', '普天下信徒'),
    (1, 47, 'fb185', '普天下信徒'),
    # 55:14 fb306 / fb308「我们使我们的密谈甘甜」← our most secret thoughts
    (1, 55, 'fb306', '以为甘甜'),
    (1, 55, 'fb308', '以为甘甜'),
    # 55:19 fb312「必回答他们」← and afflict them；fb313「从亘古」← who sitteth from ancient time
    (1, 55, 'fb313', '那从太古常存的神'),
    (1, 55, 'fb312', '必听见而苦待他们'),
    # 58:4 fb349「虺=phethen」← the deaf adder；fb351「蛇可被咒术所迷」← received opinion
    (1, 58, 'fb349', '他们好像塞耳的聋虺'),
    (1, 58, 'fb351', '流行而普遍的谬见'),
    # 68:9-10 fc17「照你的意愿与厚赐」← a liberal rain；fc18「你的会众」← Thy congregation；
    #         fc19「必倾降，沛然大雨」← 注释头那句，不在经文框里
    (1, 68, 'fc17', '9.神啊，你降下大雨'),
    (1, 68, 'fc18', '你的会众'),
    (1, 68, 'fc19', '*神啊，你降下大雨；你产业以色列疲'),
    # 69:2-4 fc65「或作：水势与水流」← and the flood of the water；
    #        fc66「或作：得了坚固」← are increased；fc67「za=那时」← then I restored it
    (1, 69, 'fc65', '我到了深水中，大水'),
    (1, 69, 'fc66', '要把我剪除'),
    (1, 69, 'fc67', '我没有抢夺的'),
]


def process(vol, chapter, items, apply):
    p = ROOT / f'calvin_raw/psalms-{vol}/zh_chapters/{chapter}.md'
    body = p.read_text(encoding='utf-8')
    changed = []
    for code, anchor in items:
        ref = f'[^{code}]'
        # 锚点后面可能已经跟着别的标记（两条脚注挂同一句），要插在它们之后，
        # 否则同一锚点的第二条会插到第一条前面，又成了倒序。
        at = re.compile(re.escape(anchor) + r'((?:\[\^[A-Za-z0-9]+\])*)')
        hits = at.findall(body)
        if len(hits) != 1:
            print(f'  !! 诗篇 {chapter} {code}: 锚点「{anchor}」出现 {len(hits)} 次，跳过')
            continue
        if ref in hits[0]:                  # 已经在目标位置 → 幂等跳过
            continue
        n_ref = len(re.findall(re.escape(ref) + r'(?!:)', body))
        if n_ref != 1:
            print(f'  !! 诗篇 {chapter} {code}: 正文引用出现 {n_ref} 次，跳过')
            continue
        body = re.sub(re.escape(ref) + r'(?!:)', '', body, count=1)
        m = at.search(body)
        body = body[:m.end()] + ref + body[m.end():]
        changed.append(code)
    if not changed:
        return 0
    print(f'  诗篇 {chapter}: {", ".join(changed)} → 重新落点')
    if apply:
        p.chmod(0o644)                      # zh_chapters 平时是只读的
        p.write_text(body, encoding='utf-8')
        p.chmod(0o444)
    return len(changed)


def main() -> int:
    apply = '--apply' in sys.argv
    groups = {}
    for vol, ch, code, anchor in FIXES:
        groups.setdefault((vol, ch), []).append((code, anchor))
    total = 0
    for (vol, ch), items in sorted(groups.items()):
        total += process(vol, ch, items, apply)
    print(f'[{"applied" if apply else "dry-run"}] {total} 个标记')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
