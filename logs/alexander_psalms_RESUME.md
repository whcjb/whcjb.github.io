# 亚历山大《诗篇注释》——续跑说明（2026-09-15 暂停点）

## 一、当前状态

### 中译
- **已发布 11 篇**：著者序 + 诗篇 1–10，落在 `alexander/psalms/zh/`
- 余 140 篇未译
- 流程：`scripts/translate_alexander_psalms.py --range N-M --resume`
  → 自动 `publish_alexander_psalms_zh.py` + commit + push
- 页面 date 取 `alexander_raw/psalms/zh_meta.json` 里**该篇实际译完的时刻**

### 英文底本 OCR 清理（本轮主线，已基本收尾）
全书扫出 1456 处待判 / 480 书页，经四道判读，**已落盘约 900 处**：

| 依据 | 处数 |
|---|---|
| 第二证人（1850 三卷本）互证 | 101 |
| 整页影像两遍互证 | 616 |
| 整页影像第三遍（dpi 320）破局 | 21 |
| 希伯来相邻词序对调 | 7 |
| 裁图两遍互证（收残） | 139 |
| 判词闸拦下但读数无误，逐条看影像手工放行 | 11 |
| 诗篇 24 `^&lt` 同串四见，按位置手工落定 | 4 |
| 本人逐张读影像手工落定 | 12 |

复扫：残留可疑 span 1456 → 约 560，其中**约 530 是判词典收不到的正经专名**
（Adhonai、Habakkuk、Al-tashheth、burnt-offering 之类），本来就没错。

## 二、还没做完的（下次从这里接）

### A. 8 处裁图两遍不一致，需要我亲自读影像
裁图在 `<scratchpad>/crop/c0NN.png`（若 scratchpad 已清，用下面的重裁脚本）。
编号与上下文见 `<scratchpad>/crop_meta.json`；两遍读数见
`logs/alexander_crop_round1.tsv` / `round2.tsv`。

| # | 篇 | OCR 残串 | 一遍 | 二遍 |
|---|---|---|---|---|
| 72 | 49 | `xx\ii` | `xxvii.` | `xxvii` |
| 89 | 58 | `jc„` | `θυμός` | `θυμός,` |
| 94 | 66 | `/-itw«` | `praise` | `pruise` |
| 101 | 69 | `i^yuh'^` | `שִׁלּוּמִים` | `שִׁלוּמִים` |
| 112 | 74 | `n|^n` | `חַיַת` | `חַיַּת` |
| 128 | 96 | `phrase/rom` | `phrase from` | `phrase *from*` |
| 141 | 110 | `prateritum` | `præte-ritum` | `præteritum` |
| 142 | 115 | `they/eel` | `they feel` | `and feel` |

多数分歧只在标点或希伯来元音点上（本卷体例是**不带元音点的辅音形式**，
全书 129 个希伯来词里 127 个无点，落盘一律去点）。

重裁命令（scratchpad 清空后用）：
```python
import fitz, json
from pathlib import Path
doc = fitz.open(Path.home()/'Documents/论文/alexander/psalms_1864_kregel.pdf')
# pdf_index = 书页页码 + 3（页眉标定）；锚点用上下文里的短语，要求唯一命中
```
完整逻辑见 `scripts/adjudicate_alexander_image.py` 与本文件同目录的
`alexander_image_suspects.json`。

### B. 全书复扫剩下的约 560 处
绝大多数是判词典收不到的正经专名。若要继续收，先把 `ANNOTATE`／
`alexander_raw/lexicon_extra.txt` 补上这些专名，让复扫数字降到真正的残留。

### C. 诗篇 1–10 的希伯来文
这 10 篇是本轮最早处理的，当时按**无点**形式落的盘，与后来全书一致——
不必回头改。

## 三、不要踩的坑
- **修正必须落脚本，不能只改已发布正文**：重跑 `publish_alexander_en.py`
  会把 `alexander/psalms/*.md` 冲回未修复状态。诗篇 1–10 那 48 条已写进
  `scripts/adjudicate_alexander_ocr.py` 的 `MANUAL_TEXT`；
  本轮全书这批记在 `logs/alexander_image_applied.tsv` 与
  `logs/alexander_crop_applied.tsv`，**尚未写进 MANUAL_TEXT**，要补。
- **希伯来相邻词会倒序**：ABBYY 按视觉左右切词，希伯来文右起横书。
- **上下文快照是修复前取的**：同一轮里邻近坏字先被改掉，快照前文就失效，
  定位要退回「按相似度择位」。
- **改英文后中译会自动重译**：缓存键就是英文段落本身，
  `translate_alexander_psalms.py --resume` 只会重跑受影响的段。
  诗篇 1–10 已经这样重跑过一轮；**本轮全书改动涉及的篇里，
  1–10 若再被改到，需要再跑一次 --resume**。

## 四、下次开工第一步
```bash
cd /Users/yanpeifa/Documents/whcjb.github.io
git log --oneline -8                     # 看清上次停在哪
python3 scripts/adjudicate_alexander_image.py --apply --dry-run   # 看剩余闸门分布
```
