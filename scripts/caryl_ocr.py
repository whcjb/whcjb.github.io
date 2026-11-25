#!/usr/bin/env python3
"""卡里尔《约伯记讲解》EEBO-TCP 未录的 4 部：按叶取图 → kraken OCR（ALTO，带行坐标）。

    /usr/bin/python3 scripts/caryl_ocr.py list 4               # 叶数
    /usr/bin/python3 scripts/caryl_ocr.py fetch 4 0-120        # 取图，已取的跳过（curl 12 路并发）
    /usr/bin/python3 scripts/caryl_ocr.py ocr 4 0-70           # kraken 8 路并行，已识别的跳过

单次命令控制在 10 分钟内，分段跑（fetch 约 120 叶、ocr 约 70 叶一段）。

## 底本与对照本（2026-11-24 实测；对照本只当第二证人，用 IA 自带 OCR 文本，不重跑）

各取同一章附近一页，kraken 识别后对 TCP 卡里尔词表（8 部 250 万词）算非词率（行末断词先拼合）：

| 部 | 底本 | 非词率 | 对照本 | 不用的 |
|---|---|---|---|---|
| 4（11–14 章） | Packer 藏本纸本 1670 印次，600 ppi | 3.7% | 1670 胶片（同一印次）6.3% | 1649 初版胶片 12.1% |
| 6（18–21 章） | Packer 藏本纸本，600 ppi | 3.4% | 1653 胶片甲 5.0% | 1653 胶片乙 6.3% |
| 8（27–29 章） | 1670 胶片，800 ppi | 3.9% | Packer 纸本 300 ppi 9.7% | |
| 9（30–31 章） | Packer 1669 四开纸本，300 ppi | 6.6% | 1676 对开合订本第二卷胶片（叶 325–530）5.7% | |

第 9 部：IA 的纸本对开本 `expositionwithpr0001jose` 只是第一卷（到 22 章前后），30–31 章只在第二卷胶片里；
两者质量相近，底本取四开本（与其余 11 部同属四开单行本），对开本另起排版、错处不重合，正好当对照本。
另一套 `joseph-caryl-job-NN`（130–140 ppi）分辨率太低，不用。

## 引擎（第 3 部有 TCP A35439 可对，Packer 第 III 册 3 叶，对上率 = 按词匹配数 / TCP 词数）

| 引擎 | p.38 | p.198 | p.398 |
|---|---|---|---|
| tesseract eng+enm，背景展平 41 + 中值 3，psm 4 | 0.407 | 0.880 | 0.792 |
| kraken + CATMuS-Print Large | **0.919** | **0.937** | — |

kraken 主要错型：斜体 h→b（wbich、beavens）、a/i、w→u/m、J→T/F；CATMuS 把长 ſ 直接出 s，合本站口径。
预处理（old-book-ocr §2.5）：缩到 ≈360–400 ppi，不上采样；灰度 → 除以 41px 闭运算背景。
中值滤波在 300 ppi 上实测变差（9.7% → 11.3%），不用。存灰度 JPEG q92。

取图用 curl：系统 Python 3.9 的 SSL 连 IA 数据节点会卡在握手（2026-11-24 卡死一次近两小时），curl 正常。
"""
import argparse
import json
import subprocess
import sys
import tempfile
import urllib.parse
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / 'caryl_raw' / 'job_ocr'
KRAKEN = Path.home() / '.venvs' / 'kraken' / 'bin' / 'kraken'
MODEL = Path.home() / '.venvs' / 'kraken-models' / 'catmus-print-large.mlmodel'
BIM = 'bim_early-english-books-1641-1700_an-exposition-'
# 部 → (IA item, jp2 zip 名, 缩放)
VOLS = {
    4: ('joseph-caryl-exposition-on-job-vol-iv', 'Joseph Caryl-Exposition On Job-Vol IV_jp2.zip', 0.6),
    6: ('joseph-caryl-exposition-on-job-vol-vi.', 'Joseph Caryl-Exposition On Job-Vol VI._jp2.zip', 0.6),
    8: (BIM + '_caryll-joseph_1670', BIM + '_caryll-joseph_1670_jp2.zip', 0.5),
    # 第 8 部的第二底本：胶片自第 160 叶起大段发暗透印，363/628 叶非词率 ≥ 15%（第 210 叶四种预处理都在 56–62%），
    # Packer 纸本（300 ppi）也全识别，按原书页码逐页择优（old-book-ocr §3.2d）
    81: ('joseph-caryl-exposition-on-job-vol-viii', 'Joseph Caryl-Exposition On Job-Vol VIII_jp2.zip', 1.0),
    # 第 8 部最终底本（2026-11-25 用户定）：1676–77 对开合订本第二卷胶片，第 27–29 章在叶 153–326。
    # 四开本两份择优后坏页仍 ≥ 15%；对开本这一段 28、29 章各测一叶 5.1%、4.5%，全段均匀。双栏，见 caryl_ocr_assemble 的双栏模式。
    # Digital Puritan 那份 PDF（Google 扫描，黑白二值）同页 9.8–19.3%，不用。
    82: (BIM.replace('an-exposition-', 'an-exposition-with-prac') + '_caryll-joseph_1676_2',
         BIM.replace('an-exposition-', 'an-exposition-with-prac') + '_caryll-joseph_1676_2_jp2.zip', 0.6),
    9: ('joseph-caryl-exposition-on-job-vol-ix', 'Joseph Caryl-Exposition On Job-Vol IX_jp2.zip', 1.0),
}


def dirs(part):
    d = BASE / f'p{part}'
    (d / 'img').mkdir(parents=True, exist_ok=True)
    (d / 'alto').mkdir(parents=True, exist_ok=True)
    return d


def curl(url, out=None, tries=4):
    for _ in range(tries):
        r = subprocess.run(['curl', '-sL', '-m', '300', '-f'] + (['-o', str(out)] if out else []) + [url],
                           capture_output=True)
        if r.returncode == 0:
            return r.stdout
    raise RuntimeError(f'curl 失败：{url}')


def nleaves(part):
    """一个条目里放几册时（Packer 藏本）元数据没有 imagecount，按该册 _page_numbers.json 的条数算。"""
    item, z, _ = VOLS[part]
    pn = z[:-len('_jp2.zip')] + '_page_numbers.json'
    q = urllib.parse.quote
    return len(json.loads(curl(f'https://archive.org/download/{q(item)}/{q(pn)}'))['pages'])


def member_url(part, leaf):
    item, z, _ = VOLS[part]
    b = z[:-len('_jp2.zip')]
    q = urllib.parse.quote
    return f'https://archive.org/download/{q(item)}/{q(z)}/{q(b + "_jp2")}/{q(f"{b}_{leaf:04d}.jp2")}'


def fetch_one(part, leaf):
    import cv2
    import numpy as np
    from PIL import Image
    Image.MAX_IMAGE_PIXELS = None
    out = dirs(part) / 'img' / f'{leaf:04d}.jpg'
    if out.exists():
        return 0
    with tempfile.NamedTemporaryFile(suffix='.jp2') as tf:
        curl(member_url(part, leaf), tf.name)
        im = np.array(Image.open(tf.name).convert('L'))
    sc = VOLS[part][2]
    if sc != 1.0:
        im = cv2.resize(im, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    bg = cv2.morphologyEx(im, cv2.MORPH_CLOSE, np.ones((41, 41), np.uint8))
    fl = cv2.divide(im, bg, scale=255)
    tmp = out.with_suffix('.tmp.jpg')
    cv2.imwrite(str(tmp), fl, [cv2.IMWRITE_JPEG_QUALITY, 92])
    tmp.rename(out)
    return 1


def _one(part, x):
    try:
        return fetch_one(part, x)
    except Exception as e:      # noqa: BLE001
        return (x, str(e)[:80])


def parse_range(s, n):
    if not s:
        return list(range(n))
    a, _, b = s.partition('-')
    return list(range(int(a), min(n - 1, int(b or a)) + 1))


def cmd_fetch(part, rng, workers=8):
    ls = parse_range(rng, nleaves(part))
    with ProcessPoolExecutor(workers) as ex:   # jp2 解码吃 CPU，线程用不满 8 核（实测 82%），改进程；单叶大的（对开本 ~10MB）并发太高会被 IA 限流，用 --workers 3
        res = list(ex.map(_one, [part] * len(ls), ls))
    n = sum(r for r in res if isinstance(r, int))
    bad = [r for r in res if not isinstance(r, int)]
    print(f'第 {part} 部：新取 {n} 叶（{ls[0]}–{ls[-1]}，共 {len(ls)}）；失败 {len(bad)} {bad[:3]}', file=sys.stderr)


def cmd_ocr(part, rng, shards):
    d = dirs(part)
    imgs = sorted((d / 'img').glob('[0-9][0-9][0-9][0-9].jpg'))
    if rng:
        a, _, b = rng.partition('-')
        imgs = [p for p in imgs if int(a) <= int(p.stem) <= int(b or a)]
    todo = [p for p in imgs if not (d / 'alto' / f'{p.stem}.xml').exists()]
    if not todo:
        print('无待识别叶', file=sys.stderr)
        return
    procs = []
    for g in (todo[k::shards] for k in range(shards)):
        if not g:
            continue
        args = [str(KRAKEN), '-a']
        for p in g:
            args += ['-i', str(p), str(d / 'alto' / f'{p.stem}.xml')]
        args += ['segment', '-bl', 'ocr', '-m', str(MODEL)]
        procs.append(subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True,
                                      env={'OMP_NUM_THREADS': str(max(1, 8 // shards)),
                                           'PATH': '/usr/bin:/bin:/opt/homebrew/bin'}))
    bad = 0
    for pr in procs:
        _, err = pr.communicate()
        if pr.returncode:
            bad += 1
            print(err[-2000:], file=sys.stderr)
    done = sum(1 for p in todo if (d / 'alto' / f'{p.stem}.xml').exists())
    print(f'第 {part} 部：识别 {done}/{len(todo)} 叶，失败进程 {bad}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['fetch', 'ocr', 'list'])
    ap.add_argument('part', type=int, choices=sorted(VOLS))
    ap.add_argument('range', nargs='?')
    ap.add_argument('--shards', type=int, default=8)
    ap.add_argument('--workers', type=int, default=8)
    a = ap.parse_args()
    if a.cmd == 'fetch':
        cmd_fetch(a.part, a.range, a.workers)
    elif a.cmd == 'ocr':
        cmd_ocr(a.part, a.range, a.shards)
    else:
        print(f'第 {a.part} 部：{nleaves(a.part)} 叶')


if __name__ == '__main__':
    main()
