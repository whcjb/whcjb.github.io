#!/usr/bin/env python3
"""batch_prefill.py —— 索引类「一条一块」的篇，打包批量翻译，逐条写进该书的翻译缓存。

佩特《马可福音》字母索引表 2,200 条、亚当斯《彼得后书》要目索引 573 条：原流程一条调一次模型，
两千多次调用既慢又贵，一句话的短块还最容易让模型自语。这里每 SIZE 条打包成一次调用（行首编号 [n]），
拆回后**每条照样过该书自己的 structural_diff**，合格的按该书的缓存键（KEY_NS + 遮盖后原文）写进缓存；
不合格的不写，留给随后照常跑的 translate_<书>.py --resume 单条重译。缓存键、闸子、组装、发布都不变。

CLI 调用走 translate_filibi.call_claude（--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt）。

用法：python3 -u scripts/batch_prefill.py --module translate_petter --section alphabetical-table [--size 40]
"""
import argparse
import importlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402

RE_LINE = re.compile(r'^\s*\[(\d+)\]\s?(.*)$')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--module', required=True)
    ap.add_argument('--section', required=True)
    ap.add_argument('--size', type=int, default=40)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max-batches', type=int, default=0, help='试跑：只跑前 N 批')
    a = ap.parse_args()
    M = importlib.import_module(a.module)
    tf.SYSTEM = M.SYSTEM
    texts = [M.mask(b)[0] for k, b in M.units_of(a.section) if k == 'text']
    todo = []
    for t in dict.fromkeys(texts):                       # 去重：同一条只译一次
        if '\n' in t:                                    # 多行块不打包（拆回对不上行），留给原流程
            continue
        if not (M.CACHE / f'{tf.md5key(M.KEY_NS + t)}.txt').exists():
            todo.append(t)
    batches = [todo[i:i + a.size] for i in range(0, len(todo), a.size)]
    print(f'[{a.module}:{a.section}] 共 {len(texts)} 段，待预填 {len(todo)} 条，分 {len(batches)} 批', flush=True)
    if a.max_batches:
        batches = batches[:a.max_batches]
    if a.dry_run:
        return
    ok = bad = 0
    M.CACHE.mkdir(parents=True, exist_ok=True)
    for bi, batch in enumerate(batches, 1):
        body = '\n'.join(f'[{i}] {t}' for i, t in enumerate(batch, 1))
        prompt = ("下面是一部十七世纪英文注释书书末索引的若干条目，每行以 [编号] 开头。逐行译成简体中文："
                  "**行数、编号与原文一一对应，一行对一行，不并行、不拆行、不漏行**；每行保留行首 [编号]；"
                  "页码数字照抄；`*` 斜体标记成对照留；⟦N⟧ 占位符原样保留；索引词条译成简洁的中文名词短语。"
                  "把全部译文放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n" + body)
        raw = tf.call_claude(prompt, timeout=900, label=f'{a.section}·batch{bi}')
        m = re.findall(r'<译文>(.*?)</译文>', raw, re.S)
        out = m[-1] if m else raw
        got = {}
        for ln in out.strip().split('\n'):
            mm = RE_LINE.match(ln)
            if mm:
                got[int(mm.group(1))] = mm.group(2).strip()
        for i, t in enumerate(batch, 1):
            zh = got.get(i, '')
            if hasattr(M, 'tidy'):
                zh = M.tidy(zh)
            if zh and not M.structural_diff(t, zh):
                (M.CACHE / f'{tf.md5key(M.KEY_NS + t)}.txt').write_text(zh, encoding='utf-8')
                ok += 1
            else:
                bad += 1
        print(f'  批 {bi}/{len(batches)}：累计合格 {ok}、留给单条重译 {bad}', flush=True)
    print(f'✓ 预填完成：合格 {ok}，不合格 {bad}（随后 translate --resume 会单条重译这些）', flush=True)


if __name__ == '__main__':
    main()
