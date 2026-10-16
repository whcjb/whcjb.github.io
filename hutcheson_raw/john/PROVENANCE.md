# 赫奇森《约翰福音注释》——底本与处理链

## 著者与著作

George Hutcheson（乔治·赫奇森，1615–1674，生卒年取 TCP 编目），苏格兰盟约派，
扉页署 *Minister of the Gospel at Edenburgh*。本书逐节讲解约翰福音，每段先排出
经文，再分「Doctrine / Learn 1. 2. 3.」条列教训，是他小先知书释义之后的第二部
同体例著作。卷首有伦敦长老会牧师 Edmund Calamy 的序（*Christian Reader*）、
作者致 Wemyss 与 Buccleuch 两位伯爵夫人的献辞、作者致读者；书末有作者自拟的
勘误表。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A45241**（人工录入 TEI P5），github `textcreationpartnership/A45241` |
| 版次 | London: Ralph Smith, 1657 初版，Wing H3826 / ESTC R11373；[8], 418, [1] p. |
| 授权 | EEBO-TCP Phase 2（2011-12），CC0 1.0（转录文本；不含页面影像） |
| TCP 来源页图 | ProQuest EEBO 缩微胶片 image set 48148（Cambridge University Library 藏本），221 张对开图 |
| 影像证人 | **无**——见下「缺字」 |

### 为什么不 OCR

TCP 是人工键入、校对过的文本层（old-book-ocr §2.2「有可信文本层就不要重
OCR」）。斜体（`<hi>`）、印本页码（`<pb n>`）、每段讲解前的经文（`<epigraph>`）、
花饰首字都带着。

### 归一与照原样

| 项 | 处理 | 理由 |
|---|---|---|
| 长 ſ | → s | 字形不是拼写（同一字母的词中形）。Perkins 那份 TCP 本来就没有 ſ，本书是第一次碰到 |
| `<g ref="char:V">Ʋ</g>` | → U | 同上，`HƲTCHESON` / `ƲPON` 的 U 字模 |
| 行末断词 | 拼合 | TCP `char:EOLhyphen` |
| u/v、i/j、`doth`、`then`(=than)、`beleeve`、`Sonne`、苏格兰词 `tryst` `dittay` `aggreage` `exerce` | **照原样** | 拼写即原文 |
| 印错的字（`brightnsse`、`chriſt` 小写） | 照原样 | 无影像无从核对；作者勘误表已承认 `lesser escapes in words` |
| 书末书商广告（Books Printed for Ralph Smith） | 不收 | 不是本书内容 |

### 原书自己的版式特点（抽取器据此处理）

- **一段讲解前可连列几节经文**（`q > p > bibl`），每节一个节号。551 个讲解单元、
  21 章 879 节，节号逐章核对与和合本节数完全一致。
- **一节拆两半分讲时两半都印节号**：8:6、8:41、19:16、21:7。照印本显示；锚点只给
  前一半，否则 verse-nav 跳到重复 id。
- **13:4 后半不带号**续列在下一单元开头（`— and laid aside his garments…`）。照排，
  不出锚点。
- **7:5 的经文原书漏排**，讲解里有 `From verse 5. Learn`。依据：书末勘误表自己说
  `mistakes in printing the verses of the Text Ex. gr. ch. 7. v 2, 3, 4. with which
  the fifth verse should also be printed`。照印本不补，勘误表原样在书末。
- 作者勘误表（*Courteous Reader…*）与 Perkins 同理**不擅自改进正文**，原样作为
  书末一页。

## 缺字

TCP 标出的缺口 838 处：读不出的字母 946 个（`•`）、整词 35（`〈◊〉`）、一截 4
（`〈…〉`）、希腊文 3（`〈Greek〉`，都在卷首 Calamy 序）、认不清的标点 21（`▪`）。
14 页缩微胶片重拍页（`reason="duplicate"`）丢。

### 找过的影像，都用不了

- IA 的 EEBO 影像集（`bim_early-english-books-1641-1700_*`）收了赫奇森 1654/1657
  的小先知书、1659 的论战小册、1691 的讲章集，**唯独没有这部约翰福音**。
- IA `expositionofgosp0000geor`（1971 Sovereign Grace 重印）、
  `gospelofjohn0000hutc`（1972 Banner of Truth）：都是借阅限制本，PDF、djvu.txt、
  书内检索（`fulltext/inside.php`）一律 403。
- Google Books：检索 API 当日配额用尽；网上提到的 1657 年扫描本未能核实。

所以 Perkins 那条「同版影像裁图判读」（第 ③ 层）与「他版按位置判读」（第 ② 层）
都走不通，**只做第 ① 层语料自证**，判不了的记号留在页面上（`.hc-gap` 标红）。

### 语料自证的守卫（scripts/hutcheson_gapfill.py）

只碰「词里缺几个字母」。缺整词／一截／希腊文／标点、含数字的（经文出处
`1•.10`）、已知字母少于 3 个的（`b•t`）一律不碰。满足以下之一才补：

1. **lex**：逐位填，在「全书语料 ∪ 系统词典 web2」并集里只有一个词对得上，且该词
   在本书出现 ≥3 次。并上词典是为挡 `lu•k → lurk`（书里只有 lurk，英语里 luck
   一样填得进）。
2. **ctx**：多个候选，但全书同样「左邻 + 候选 + 右邻」搭配里只有一个候选出现过、
   且 ≥2 次（`may be •educed to foure heads` → reduced，不是 seduced）。

结果（2026-10-16）：806 个缺字词里 lex 224、ctx 41 落盘，共 265 条；
ambig 217 / rare 34 / none 21 / 不碰 269 留着。265 条落盘前全部列出逐条看过，
ctx 档逐条带上下文核对。

### 将来能补的

拿到 1657 年版页面影像（EEBO 机构订阅、Cambridge UL 藏本、或 Google Books 全文
扫描）后，按 Perkins 的 gapcrop 流程逐处判读，判读结果追加进 `manual_fixes.tsv`
（`hutcheson_gapfill.py --apply` 会重写自动部分，手工判读要另存一份并在导出时合并）。

## 文件

| 文件 | 内容 |
|---|---|
| `src/A45241.xml` | TCP 原件（入库） |
| `en_chapters/*.md` | `scripts/extract_hutcheson.py` 产物 |
| `gap_sites.json` | 缺字清单（抽取时写出） |
| `gap_decisions.tsv` | 每处缺字词的判读记录（`?` = 不判）与证据 |
| `manual_fixes.tsv` | 由判读记录导出的按位落盘表，`hutcheson_common.py` 自检 |
| `en_meta.json` | 每页发布时刻（重跑不改已有值） |
| `pages.json` / `pages_en.json` | 印本页码表 / 发布页表 |

## 重跑

```
python3 scripts/extract_hutcheson.py --apply
python3 scripts/hutcheson_gapfill.py --apply
python3 scripts/hutcheson_common.py          # 自检：每条都要落得下
python3 scripts/publish_hutcheson_en.py --apply
python3 scripts/build_commentaries_index.py
```
