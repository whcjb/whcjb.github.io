# 霍尔《提摩太后书第三、四章注释》——底本与处理链

## 著者与著作

Thomas Hall（托马斯·霍尔，1610–1665；DNB vol.24，Alexander Gordon 撰，原文存 `dnb_hall.txt`）。
*A Practical and Polemical Commentary, or, Exposition upon the Third and Fourth Chapters of the Latter Epistle of
Saint Paul to Timothy …* London: E. Tyler for John Starkey, 1658，对开本（Wing H436，ESTC R14473）。

## 是否有中译本

2026-10-28 中文检索两轮：未见。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A45335**，人工录入 TEI P5，github `textcreationpartnership/A45335`，`src/A45335.xml`（入库） |
| 授权 | EEBO-TCP，CC0 1.0 |
| 原书影像 bim | archive.org `bim_early-english-books-1641-1700_a-practical-and-polemica_hall-thomas_1658`（IA40313709-79），与 TCP 同一卷胶片。叶号 = 访问页号（513 叶）；TCP 一张图 = 一个对开，左页叶 2f−1、右页叶 2f（实测 p.1 = facs 10 右页 = 叶 20）。原生 5127×8026（800 ppi） |

只此一份扫描，没有第二证人。

## 结构（`scripts/extract_hall.py`）

TEI 的 div 已按原书分好：part = 章（3、4），subpart = 一段经文（「VERSE 2.」起头），其下 section/subsection 是
逐语小标题 → h3/h4。一段经文一页，页名 `<章>-<首节>`，共 41 段；第三章第 8 节后插的加尔文《驳放纵派》第七章
单独一页 `3-8-calvin`。卷首 title / epistle-to-reader（卡拉米）/ dedication（伍斯特）/ to-the-reader（作者）/
to-the-reader-2（John Ley）/ books / errata，卷末 postscript / questions / texts / subject-index（**不能叫 index**，
会盖掉书首页）/ starkey。TEI→markdown 的行内与块级共用 `scripts/tcp_tei.py`，发布共用 `scripts/tcp_publish.py`。

## 缺字

按词并组 1,611 组（正文 530、旁注 1,081），`gap_sites.json`。判读口径同泰勒（`taylor_raw/titus/PROVENANCE.md`）：
只有看图读出的落盘；`P:` 推断列待同意；`?` 判不了标红。读法里**不要加星号**（斜体由原串首尾保留；加了会和录入本的
斜体分组错位，2026-10-28 一次弄坏 8 篇的星号奇偶）。

定位：`scripts/hall_bim_ocr.py`（本地 tesseract，IA 1/4 缩图）→ `hall_witness.py build/match`。旁注的本地 OCR
定位常偏到正文，看图改用原分辨率裁片：`scripts/tcp_native.py hall crops`（从 `*_jp2.zip` 按 HTTP Range 只取一叶，
`scripts/ia_rangezip.py`；IA 的 page/nN.jpg 现场转码一页 40 秒，太慢），旁注一律裁左右两条整页边。

### 进度（2026-10-28 首次上线）

| | 组数 |
|---|---|
| 已判 | 446（落盘 275，推断 164 待同意，判不了 7） |
| 未判 | 约 1,165（旁注为主），页面标红 |

## 重跑

```
python3 scripts/extract_hall.py --apply
python3 scripts/hall_witness.py gaps
python3 scripts/hall_bim_ocr.py && python3 scripts/hall_witness.py build && python3 scripts/hall_witness.py match
python3 scripts/hall_witness.py sheets --gids 0-99 --name m        # 正文：本地缩图
python3 scripts/tcp_native.py hall crops --gids 0-1610 && python3 scripts/tcp_native.py hall sheets --gids … --name o
python3 scripts/publish_hall_en.py --apply
python3 scripts/build_commentaries_index.py
```
