# Vos, "Eschatology of the Psalter" — 底本与校勘

- 原刊：*The Princeton Theological Review* 18, no. 1 (January 1920), pp. 1–43。1920 年美国出版，美国境内公有领域。
- 底本：Ted Hildebrandt 录入本 PDF（biblicalelearning.org，`src/bel.pdf`），逐页逐行照原刊排。
  semperreformanda.com 网页本经比对系同一录入本的转抄（且少数词），未用。
- 证人：Internet Archive `princetontheolog1811arms`（PTS 藏本扫描）。原生 JP2 约 2031×3237，
  `src/jp2/`（未入 git，可按 `scripts/vos_psalter_crop.py` 文首说明重下）；词坐标 `src/ptr_djvu.xml`（未入 git）。
- 中译：2026-11-10 查霍志恒《保罗的末世论》《诗篇的末世论》中译未见。

## 链条
1. `scripts/vos_psalter_extract.py` → `extract.json`（正文段落、脚注、行末断字处理、1920 页码 ⟦pN⟧）
2. `scripts/publish_vos_psalter.py` 套 `corrections.tsv` → `vos/psalter/index.md`（重跑逐字节不变）

## 校勘
录入本与原刊扫描 OCR 逐词比对，出入处按锚词裁原生分辨率页图（`scripts/vos_psalter_crop.py`）逐条读定，
落入 `corrections.tsv`（每条注原刊页码与依据）。主要是：德文书名 und→and、变音符号丢失、
旧体数字 1/11 录成 I/II、呼格 O 录成 0、经文出处数字误录、漏注号 44、希伯来文（HebrewTh 字体）解码。
原书误植照原样保留（Schäpfung、Ausgewähte、Ausgewaählte、Qurterly、Acording 等，见表头）。
