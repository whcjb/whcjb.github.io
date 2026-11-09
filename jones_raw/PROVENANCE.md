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
| 原书影像 | IA `bim_early-english-books-1475-1640_a-commentary-upon-the-ep_jones-william-b-d_1635`（757 叶，与 TCP 同一册，判读即用它）；另有 `…_1636`（719 叶，1636 年印本）作第二证人，2026-11-09 用来复核判不定的各组（见下） |

## 结构（`scripts/extract_jones.py`）

TCP 把约翰二书、三书各放一个 `<div type="exegesis">`，下分 `<div type="verse">`（题头「VERSE. 1.」）；约翰三书末段合讲
13、14 节（「VER. 13, 14.」）。一节一页，页名 `1-<首节>`；每卷另出章目录 `1.md`。
卷首三篇两卷共用、各收一份：书名页 `title`、献辞 `dedication`（只取献杰尔明爵士那篇——它专为约翰二书、三书与腓利门书而写；
献里奇勋爵那篇是献希伯来书的，不收）、致读者 `to-the-reader`；卷末勘误只取「In Epist. Iohan.」一节 `errata`。

原书节下不排经文，开讲以斜体引出所讲字句；只有约翰二书第 1 节用了方括号（`[THE ELDER]`），抽成 `.jw-lemma`。
页边旁注只有出处一种，无指引字母。

## 缺字判读（2026-11-06，按 old-book-ocr skill 第③层：看同一册胶片影像）

TCP 标出的缺字按词并组：2john 58 组、3john 64 组（卷首献辞、致读者与卷末勘误 5 组两卷共用，只判一次，3john 抄自 2john）。
大头是录入者不录的希腊文（`reason="foreign"`），其余是读不出的字母与认不清的标点。

| | 2john | 3john |
|---|---|---|
| 看图读出，已落盘 | 48 + 2（1636 本） | 54 + 1（1636 本） |
| 推断 `P:`，待用户同意，**未落**（正文标红，首页逐条列「拟补」） | 7 | 8 |
| 读不出 `?`（标红） | 1 | 1 |

做法：
1. `jones_witness.py gaps` 建 gap_sites.json；`crops` 取 IA 原生分辨率整页图（≈5300×8000），本地 tesseract 只作定位；
   `tight` 按定位点裁紧图，**不缩放**拼判读页——缩放后希腊小字认不清（实测）。
2. 紧图偏了（希腊文跨行、在下一行行首、旁注、定位落到同页别处）用 `jones_fix_crop.py` 补裁（wrap/up/margin/page）。
   旁注栏在版心之内（单页左栏或右栏），不在页边。
3. 希腊文照印本转录：ȣ（ου）、ος、στ、ττ、καί 等连字拆成标准字母；重音照所见；印本不标下写 ι 的不补；
   字母认不准的一律 `P:`，在备注写图上所见与拟补依据。原书误植照录（第 044 组 ἐνεργέτης，卷末勘误已更正为 εὐεργέτης）。

两处录入本把夹在希腊文中间的拉丁／英文一起漏了：2john 第 013 组「οὓς, *Scil.* ἀνθρώπους」、3john 第 007 组
「εὐοδοῦσθαι of εὖ & ὁδός」，按图补全。3john 第 035 组「E•periculis」图上 E 与 periculis 之间只有空格，录入本误标缺字。

### 第二证人：1636 印本复核（2026-11-09）

用户令「用 1636 本对照，不要猜」。`scripts/jones_witness1636.py` 取 IA 1636 本原生分辨率叶（≈5200×7800，叶号 ≈ 印本页 + 5～7），
对 1635 上判为 `P:` / `?` 的 20 组逐一裁图看：

- **1636 读清、已落**（依据 `img1636`）：2john 056 `books;`（1635 墨渍分不清逗号分号）、055 旁注 *Laert.*；3john 062 `nostrils`。
- **两本字形一致、确认是印本本身的写法**，剩下的是「照录误植还是改正」的编辑决定，仍留 `P:` 待同意：
  致读者 δαπάναθεν（拟 δαπανηθέν）、2john 013 ἀθρώπους（拟补 ν）、046 μὴ Συμπέσῃ τὸ βαλαντιὸν（拟 βαλανεῖον）、
  3john 022 Gat.（拟 Gal.）、027 ἀυαγγελίου（拟 εὐ-）、033 Ἀ’πλαμβάνειν、051 ὁμηροπάτης、052 Ἰωάννου πάτης。
- **1636 帮不上**：2john 016 do·h、040 t·act、3john 031 the r——两本同一处一样的断字／空缺；2john 052 旁注 14 紧贴栏线；
  053 行末 χαίρ+一字认不准；031 ἀθετεῖν 已确认，其后「τι」形似 π 仍分不清；3john 040 ὁ ϖροτέȣθν 末两字母、045 仍认不准。

判读表备注逐条写了 1636 叶号与所见。witness1636/ 不入库。

## 扉页

照 1635 原图（叶 0，有剑桥大学图书馆馆藏章——与 TCP 底本同一册）逐行手排：`manual_pages/title.html`，两卷共用；
蓟花印刷商徽记裁自原图 `img/jones/device.jpg`。原图作 D<sup>r</sup>.、minusvæ（录入本作 D.、minusve），照原图。
馆藏章不是印刷内容，不排。

## 重跑

```
python3 scripts/extract_jones.py --apply
python3 scripts/jones_witness.py gaps             # 改了抽取后必须重建，gid 对不上的判读不落
python3 scripts/publish_jones_en.py --apply
# 判读用（witness/ 不入库）：jones_witness.py crops / tight；jones_fix_crop.py OUT.jpg 2john-014:wrap …
python3 scripts/build_commentaries_index.py
```
