# 加尔文《撒母耳记上讲章》（拉丁文）——底本与处理链

2026-11-11 用户令「做撒母耳记上拉丁文版」。

## 文本的来历（据《加尔文全集》第 29 卷编者导言，第 237–240 栏）

- 加尔文用法文讲撒母耳记上，书记员当场笔录；法文稿由照管外来穷人的执事会保存。
- **法文原稿已佚**：全集编者（Baum / Cunitz / Reuss）称各处手稿与公共图书馆都查不到踪迹。
- 现存的是 David Claudus（导言原图作 *Subscripsit David Claudus*）的拉丁文译本：
  *Ioannis Calvini homiliae in I. librum Samuelis. Ex Gallicis Latinae factae et nunc primum in lucem editae.*
  Genevae, excudebat Gabriel Cartier, 1604（fol.）。107 篇。1617 年 Vignon / Chouet 版只是换了书名页的同一批印张。
- 编者说 1604 年版印错甚多，部分径改、部分在页边注出推测（本站作篇末编者注）。
- 对照：撒母耳记下有 87 篇法文手稿存日内瓦图书馆（1562-05-23 至 1563-02-03 讲），没有拉丁译本；
  唯一整理本 *Supplementa Calviniana* 第 1 卷与 Kelly 英译（1992）都在版权期内，本站未做。

## 底本

| | 第 29 卷（CR 57） | 第 30 卷（CR 58） |
|---|---|---|
| 出版 | Brunsvigae: Schwetschke, 1885 | 1886 |
| 内容 | 导言 + 第 1–44 篇（1–12 章） | 第 45–107 篇（13–31 章） |
| PDF | `bf_433x_57.pdf`（40.6 MB） | `bf_433x_58.pdf`（45.7 MB） |
| 本书所用页 | PDF 第 131–382 页 | PDF 第 15–417 页 |

来源：日内瓦大学开放档案 <https://archive-ouverte.unige.ch/unige:650>（全集 59 卷全套 PDF），
下载地址形如 `https://access.archive-ouverte.unige.ch/access/metadata/<uuid>/download`；
第 57 卷 uuid `53282219-8d96-4fb0-bd3f-bd94e7aa5981`，第 58 卷 `23af2452-661a-448c-80c4-bf86ffb115c9`。
存 `src/co29.pdf`、`src/co30.pdf`（不入库）。300 dpi 黑白页图 + 一层带正体/斜体字体的 OCR 文字（本书主文本）。
1885–86 年出版，公有领域；PDF 首页的版权套话针对的是扫描件，不影响底本文字。

**扫描件缺陷**：第 30 卷 PDF 第 244–271 页是第 463–466 栏两页轮流重扫 14 遍，272–275、306–317 页也有重扫；
抽取按「页眉栏码倒退」与「正文开头相似度 > 0.8」去重（共跳过 38 页），去重后栏码逐页连续，**无缺页**。

其他证人（未用，备查）：IA `ioanniscalviniop30calv`（多伦多藏第 30 卷，有 ABBYY）、CCEL `opera30`（未校 OCR）、
IA `bub_gb_riKCSWlJrdoC`（1667 阿姆斯特丹版第二卷，异版，OCR 很差）。第 29 卷在 IA 上找不到。

## 处理链

1. `scripts/ocr_calvin_1sam_witness.py` → `witness_tess.jsonl`：tesseract `script/Latin --psm 6` 按栏重读，第二证人
   （`lat` 模型 c→e 误读成片，弃用）。栏界与抽取同一判据（`gutter`）。
2. `scripts/extract_calvin_1sam.py` → `units.json`：
   - 文字层按栏组行，剔栏眉（取栏码作锚点 `#cNNN`）、页脚、书帖签名；字号 9.0 的页底行为编者脚注。
   - 13.9 号「HOMILIA …」起新篇；「CAP. …」只在换章处印，沿全书记着当前章。
   - 篇首斜体段为所讲经文（`.cs-text`，节号 `.cs-vn`）；缩进起段。
   - 行末连字符先把下一行词头挪上来，再交 `scripts/repair_calvin_1sam.py` 判读，日志 `repair_log.tsv`。
3. `scripts/publish_calvin_sermons.py 1samuel` → `calvin/1samuel-sermons/`。

## 判读（repair_calvin_1sam.py）

词表：wooorm/dictionaries 拉丁文 hunspell（`dictionaries/la/index.{dic,aff}`），`unmunch` 展开约 1800 万词形，
存 `lexicon/forms.txt`（不入库）；与本书两份 OCR 相交的部分缓存为 `lexicon_hits.txt`（入库，没有 forms.txt 时用它）。

- 重音：印本拉丁文无重音，OCR 加的 é è à â 等去掉（去后须在词表里）；元音后的分音符（Israël、Isaï）保留。
- 证人按位置：两份逐栏对齐，一对一处主文本不在词表、证人在词表且相近 → 取证人。
- 两边都是真词只改白名单（ilia→illa、ilium→illum、tarnen→tamen 等典型误读）。
- 字形混淆规则生成候选，词表**唯一**命中才改。
- 其余照录，记 `residue`，待看图。
