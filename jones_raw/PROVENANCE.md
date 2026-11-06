# 琼斯《约翰二书、三书简释》——底本与处理链

## 著者与著作

William Jones（威廉·琼斯，1561–1636 年 12 月 12 日；DNB vol.30，W. A. J. Archbold 撰，原文存 `dnb_jones.txt`）。
剑桥克莱尔学堂出身，1584 年伊曼纽尔学院创立时为首批院士；1590 神学学士、1597 神学博士；1592 年起任萨福克郡
东伯格霍尔特教区牧师四十四年。DNB 另提醒勿与同名的怀特岛阿雷顿那位（fl. 1612–1631）相混。

*A Commentary upon the Epistles of Saint Paul to Philemon, and to the Hebrewes; together with a Compendious Explication
of the Second and Third Epistles of Saint Iohn*, London: R. B. for Robert Allot, 1635，对开本（STC 14739.5，ESTC S112377）。
另有题 1636 年的印本。DNB 写作「London, 1636, 8vo」，与 1635 年扉页和 TCP 编目不合，以扉页为准。

本站只取卷末的约翰二书（印本 pp. 661 起）、约翰三书两篇，**腓利门书、希伯来书不取**（希伯来书本站已有欧文）。

## 是否有中译本

2026-11-06 查（中英文检索）：未见中译。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A04619**，人工录入 TEI P5，github `textcreationpartnership/A04619`，`src/A04619.xml`（入库） |
| 授权 | EEBO-TCP Phase 1，2015-01-01 起公有领域 |
| 原书影像 | IA `bim_early-english-books-1475-1640_a-commentary-upon-the-ep_jones-william-b-d_1635`（757 叶）；另有 `…_1636`（719 叶，1636 年印本）可作第二证人。尚未取图 |

## 结构（`scripts/extract_jones.py`）

TCP 把约翰二书、三书各放一个 `<div type="exegesis">`，下分 `<div type="verse">`（题头「VERSE. 1.」）；约翰三书末段合讲
13、14 节（「VER. 13, 14.」）。一节一页，页名 `1-<首节>`；每卷另出章目录 `1.md`。
卷首三篇两卷共用、各收一份：书名页 `title`、献辞 `dedication`（只取献杰尔明爵士那篇——它专为约翰二书、三书与腓利门书而写；
献里奇勋爵那篇是献希伯来书的，不收）、致读者 `to-the-reader`；卷末勘误只取「In Epist. Iohan.」一节 `errata`。

原书节下不排经文，开讲以斜体引出所讲字句；只有约翰二书第 1 节用了方括号（`[THE ELDER]`），抽成 `.jw-lemma`。
页边旁注只有出处一种，无指引字母。

## 缺字（未判读）

TCP 标出（约翰二书 / 约翰三书正文，不含两卷共用的卷首卷末）：

| | 2john | 3john |
|---|---|---|
| 未录的希腊文 `〈Greek〉` | 38 | 42 |
| 读不出的字母、词 `•` `〈◊〉`，认不清的标点 `▪` | 15 | 17 |

卷首卷末另有：献辞 2 处、致读者 1 处、勘误 1 处希腊文。

**全部尚未判读**，正文标红上线。判读做法照阿特索尔（`attersoll_raw/philemon/PROVENANCE.md`）：先建 gap_sites.json，
按印本页定位 IA 胶片叶，本地 OCR 只作定位，看图判读记入 `<book>/gap_review.tsv`，推断 `P:` 列待用户同意。
希腊文要逐处看图转录，不得按上下文猜补。

## 重跑

```
python3 scripts/extract_jones.py --apply
python3 scripts/publish_jones_en.py --apply
python3 scripts/build_commentaries_index.py
```
