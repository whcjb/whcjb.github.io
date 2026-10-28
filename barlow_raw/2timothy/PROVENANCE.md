# 巴洛《提摩太后书第一章讲解》——底本与处理链

## 著者与著作

John Barlow（约翰·巴洛，1580/81 生，卒年不详；Wood, *Athenae Oxonienses* vol.1 p.495，原文存 `wood_barlow.txt`）。
*An Exposition of the Second Epistle of the Apostle Paul to Timothy, the First Chapter …* London: I. D[awson] for
Iohn Bellamie, 1625（刻版扉页 1624），四开本（STC 1434，ESTC S100861）。1632 年对开本增讲第二章（IA
`bim_early-english-books-1475-1640_an-exposition-of-the-fis_barlow-john_1633`，无 TCP 录入本，暂未处理）。

## 是否有中译本

2026-10-28 中文检索两轮：未见。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A04220**，人工录入 TEI P5，github `textcreationpartnership/A04220`，`src/A04220.xml`（入库） |
| 原书影像 bim | archive.org `bim_early-english-books-1475-1640_an-exposition-of-the-sec_barlow-john_1625`（IA40310606-35），483 叶 |

**录入本缺页**：TCP 所据胶片漏拍 16 个对开（`<gap reason="missing" extent="2 pages">`，约 32 页，落在第 3、4、6、
9–12 节）。bim 上这些页都在（实测 p.89 之后叶 117/118 = p.90/91），待据影像补录到 `supplied/N.md`；
发布时没补的位置显示一行红字说明。bim 比 TCP 多出这些页，叶号偏移逐图不同：`witness/offsets.json`
（按每图文字三词组与 OCR 比对得出，只修孤立离群点）。

## 结构（`scripts/extract_barlow.py`）

body 是一个 tract：全章导论（`introduction`）+ 18 个 verse div，一节一页 `1-<节>`。每节分「The Logicall
resolution」「The Theologicall exposition」，原书是页边旁注，照录。卷首 title / dedication（普利茅斯市长）/
to-the-reader / contents（按节的要目表）；书末「Laus Deo. Amen.」挂第 18 节末。

## 缺字

461 组（正文 421、旁注 40）。胶片发灰、黑边、透印重，本地 OCR 先切黑边、放大 1.5 倍、自适应二值化
（`scripts/barlow_bim_ocr.py`），仍只有约 95 组能精确定位，其余按上下文插值估位；判读改按页看
（`scripts/tcp_pages.py`）。

### 进度（2026-10-28 首次上线）

已判 7 组；其余与 16 处缺页待做。
