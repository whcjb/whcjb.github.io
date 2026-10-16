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

### 第 ② 层：1841 年他版证人（2026-10-16 补做）

| | |
|---|---|
| 证人 | *An Exposition of the Gospel … According to John. Reprinted from the Edition of 1657*，London: T. Ward & Co.，439 页 |
| 来源 | Google Books `PXRjAAAAcAAJ`（大英图书馆藏本，2015 年数字化，公版全文） |
| 取法 | PDF 下载被人机验证拦；改走阅读器的签名页图接口（`jscmd=click3` → `src`），438/439 页取到（缺 PA3 卷首） |

1841 本是**重排、拼写现代化**的翻印（beleevers → believers、经文出处改罗马数字章号、
偶有改写如 `regrate [reflection]`），所以只当证人不当底本：

1. 两套 tesseract（原图 psm4 / 2× Otsu psm6）各出词流，两侧上下文三词组投票定位；
2. 每处裁出 1841 页图那几行，**逐条看图判读**（`scripts/hutcheson_review.py` 落
   `gap_review_1841.tsv`）。judge 的自动读数只当预填值，不直接落盘；
3. 拼写落 **1657 的写法**：1841 读数只负责在本书语料的候选里挑一个
   （`Men's` → `Mens`、`improve` → `emprove` 的那一类以本书频次为准）；
4. 1841 本在该处改写、读不出 1657 原词的，判 `?` 不补（如 `regrate`、`•an` 处 1841 作
   `cometh`）。

结果：541 处待判里 490 处定位到，人工复核 458 条、判出 391 条；连同语料自证的 265 条，
`manual_fixes.tsv` 共 656 条。**剩余 158 个缺字记号**：未定位 51、锚点覆盖低 38、
看过判不了 67（多为 1841 改写处）及非字母缺口。

### 找过但用不了的

- IA 的 EEBO 影像集未收此书；IA 1971 Sovereign Grace / 1972 Banner of Truth 重印本借阅限制，
  全文与书内检索 403。

## 文件

| 文件 | 内容 |
|---|---|
| `src/A45241.xml` | TCP 原件（入库） |
| `en_chapters/*.md` | `scripts/extract_hutcheson.py` 产物 |
| `gap_sites.json` | 缺字清单（抽取时写出） |
| `gap_decisions.tsv` | 每处缺字词的判读记录（`?` = 不判）与证据 |
| `manual_fixes.tsv` | 语料自证 + 1841 复核导出的按位落盘表，`hutcheson_common.py` 自检 |
| `gap_review_1841.tsv` | 1841 他版逐条看图复核（`?` = 看过判不了） |
| `witness_locs.json` / `gap_decisions_witness.tsv` | 定位结果 / 自动读数（预填值） |
| `witness_1841/` | 页图、OCR、判读图（不入库，`hutcheson_witness.py fetch/ocr` 重建） |
| `en_meta.json` | 每页发布时刻（重跑不改已有值） |
| `pages.json` / `pages_en.json` | 印本页码表 / 发布页表 |

## 重跑

```
python3 scripts/extract_hutcheson.py --apply
python3 scripts/hutcheson_witness.py fetch && … ocr && … build && … match && … judge   # 他版证人（只有重做判读时才需要）
python3 scripts/hutcheson_gapfill.py --apply      # 语料自证 + 并入 gap_review_1841.tsv
python3 scripts/hutcheson_common.py          # 自检：每条都要落得下
python3 scripts/publish_hutcheson_en.py --apply
python3 scripts/build_commentaries_index.py
```
