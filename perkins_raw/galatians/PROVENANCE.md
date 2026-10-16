# 帕金斯《加拉太书注释》——底本与处理链

## 著者与著作

William Perkins（威廉·珀金斯，1558–1602），剑桥基督学院院士，英国清教徒
神学的奠基人。本书是他在剑桥圣安德烈堂（Great St Andrew's）逐节讲解加拉太书
的讲稿，生前未及付印、只讲到第 5 章。1604 年由 Ralph Cudworth（拉尔夫·卡德沃思，
剑桥以马内利学院神学学士）整理出版，并**由 Cudworth 本人续写第 6 章**
（书中另有一张补编扉页 *The Supplement or Continuation of the Commentarie vpon
the sixt Chapter*，另有一篇献给 Sir Bassingbourne Gawdy 的献辞）。

所以全书著者分两段：第 1–5 章 Perkins，第 6 章与书末 *The Conclusion*
Cudworth。发布时页面上要分清，不能把第 6 章算到 Perkins 名下。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A09383**（人工双录入 TEI P5），github `textcreationpartnership/A09383` |
| 版次 | 剑桥 John Legat 1604 初版，STC 19680 / ESTC S114465 |
| 授权 | EEBO-TCP Phase I，CC0 1.0（公有领域） |
| TCP 来源页图 | ProQuest EEBO 缩微胶片 378 张对开图 |
| 影像证人 | Internet Archive `bim_early-english-books-1475-1640_a-commentarie-_perkins-william_1604`（同一版次，755 叶 = TCP 378 对开 ×2，单页 4025×5768） |
| 他版证人（未用） | IA `…_a-commentarie-on-the-fiv_perkins-william_1607`、`…_a-commentarie-or-exposit_perkins-william_1617`（重排版，可作缺字的第二影像证人） |

### 为什么不 OCR

TCP 是人工键入、逐页校对过的文本层（old-book-ocr §2.2「有可信文本层就不要
重 OCR」），斜体（`<hi>`）、旁注（`<note place="margin">`）、印本页码
（`<pb n>`）、版心行号（`<milestone n="5|10|…">`）全都带着。IA 那份扫描件
自带的 OCR 不能用：缩微胶片两侧的版框竖线把版面切碎，整页词序打乱
（leaf 0035 的头一行读成 `For there one ſo goſpeli. Paul ; word men,…`）。

### TCP 自己标出的缺口

| 类 | 记号 | 处数 | 去向 |
|---|---|---|---|
| 读不出的字母 | `•`（每字母一个） | 400 处 | 裁图判读 |
| 读不出的整词 | `〈◊〉` | 58 | 裁图判读 |
| 读不出的一截 | `〈…〉` | 41 | 裁图判读 |
| 希腊／希伯来活字（TCP 体例不录） | `〈Greek〉` | 98 | 裁图判读 + tesseract grc |
| 认不清的标点 | `▪` | 48 | 裁图判读 |
| 重复页 | — | 41 | 丢（是缩微胶片重拍，不是缺文） |

第 6 章（Cudworth 补编）一章就占了 415 处——胶片那一段的影像明显更差。

处理顺序：`gap_sites.json` 记下每处缺字所在的印本页、TCP 图号、版心行号
→ 下载该对开的两叶原图 → 本地 tesseract 取词坐标（只用来定位，不取字）
→ 按缺字两侧上下文对齐、裁出该行 → 人工判读 → 判读结果落 `manual_fixes.tsv`
（按「篇 + 第几处缺字 + 缺字原形」对位，原形对不上就报错不落）。

### 书末附录

印本书末有三份检索表（*Common Places handled in this Commentarie*、经文索引、
字母索引），全部按**印本页码**检索。网页按经文分页，印本页码只作为页内锚点
保留（`<span class="pk-pb" id="pN">`），检索表不单独发布。

### 勘误表

卷首有一张 *Faults escaped*（28 条）。按 §0.0 原样排在卷首，**不擅自改进正文**：
TCP 录的是印出来的字，勘误是原书自己的附件，两者都保留才是原样。

## 文件

| 文件 | 内容 |
|---|---|
| `src/A09383.xml` | TCP 原件（入库） |
| `en_chapters/*.md` | `scripts/extract_perkins.py` 产物 |
| `gap_sites.json` | 缺字清单（抽取时一并写出） |
| `pagemap.json` | 印本页 → IA leaf |
| `witness_1604/` | IA 原图与本地 OCR（不入库，可重新下载） |
