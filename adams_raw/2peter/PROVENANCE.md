# 亚当斯《彼得后书注释》——底本与处理链

## 著者与著作

Thomas Adams（托马斯·亚当斯，约 1583–1652，11 月 26 日下葬；生卒取 Baker, DLB 151, 1995）。
*A Commentary or, Exposition vpon the Diuine Second Epistle Generall, written by the Blessed Apostle
St. Peter*，London: Richard Badger [and Felix Kyngston] for Iacob Bloome, 1633，两卷对开本
（[8], 764, [2], 801–1634, [28] p.），STC 108 / ESTC S106782。献给 Sir Henry Marten。
DNB 与 Wikipedia 作 1638，是误记；扉页、STC、TCP 均作 1633。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A00665**（人工录入 TEI P5），github `textcreationpartnership/A00665` |
| 授权 | EEBO-TCP Phase 2（2013-12），CC0 1.0（转录文本） |
| TCP 来源页图 | ProQuest EEBO image set 7151，大英图书馆藏本缩微胶片（Early English books 1475–1640, reel 905:07） |
| 原版影像 | `bim` = archive.org `bim_early-english-books-1475-1640_a-commentary-upon-the-se_adams-thomas_1632`（同一卷胶片的灰度扫描，7440 宽） |
| 重印本证人 | `r1862` = archive.org `expositionuponse00adam`（Edinburgh: J. Nichol 1862，James Sherman 修订）；`r1848` = `anexpositionupo00shergoog`（London: Bohn 1848，同一修订本） |

找过、用不了的：EarlyPrint 的 A00665（按字母模式自动补了约 3,500 处，不标来源、未对照影像；未补的仍有 8,000 余处，
不作证据）；Logos/Faithlife（Sherman 修订本的电子版，付费不可下载）；Google Books、HathiTrust、Digital Bodleian、
Folger、BSB 均未见 1633 原书的数字化本。已知实物藏本：Salisbury Cathedral、Toronto CRRS、Lancaster University
（Burnley Grammar School 旧藏）、大英图书馆。

## 结构

`scripts/extract_adams.py`：一节一篇（`<章>-<首节>`；1:20–21 合讲在 `1-20`），卷首 `title1` / `dedication`，
卷二扉页 `title2`（排在 2:11 前），书末 `index` / `errata`。卷二开头的「The Summe of the Verse」conclusion
接在 `2-10` 后。旁注 6,552 条 → `.ad-margin`；印本页码 → `.ad-pb`（卷二从 801 起，连号）。
`<milestone>` 是原书分条的排版记号，丢弃。

发布（`scripts/publish_adams_en.py`）：一节的讲解超过 120k 字符时在段落之间切页（优先在原书小标题前），
续页页名 `<章>-<首节>-<k>`，标题带 `(part k of n)`，经文锚点只挂第一页。全书 93 页。

## 缺字

TCP 标出的缺口：读不出的字母 13,436 个、整词 1,947、一截 64、外文（希腊／希伯来）199、认不清的标点若干；
按词并组后 11,059 处（`gap_sites.json`，`scripts/adams_witness.py gaps`）。

### 判读流程（2026-10-21）

1. **定位**：TCP 上下文三词组投票，在 1862 与 bim 两份 hOCR 词流里定位（r1862 定位 10,270，bim 7,353）；
   再按前后已定位缺字之间的窗口补定位。
2. **预填**（`judge`）：1862 同位读出的词，挑本书语料里的 1633 拼法；过三道闸——真词闸（1862 OCR 乱码不采）、
   邻词闸（缺口前后各一词与 1862 同位一致，否则视为 Sherman 改写／把拉丁译成英文）、残字闸（合 TCP 残存字母）。
   过闸的为 A/B 档 6,518 条。
3. **抽样看图**：A/B 档每 20 抽 1，329 条看图，2 条需改（已修进规则：her/here 词尾 e、拉丁被译成英文）。
   其余 A/B 整档采信（用户 2026-10-21 定）。
4. **逐条看图**：B?/C/X 档 4,541 条全部出判读图（1862 裁图 + bim 裁图），记入 `gap_review.tsv`。
5. **推断复核**：上一步标 P:（推断）与 ?（判不了）的 1,652 条，对照 1633 原图宽裁（整行宽、上下各两行、
   原分辨率近景）复核，记入 `gap_recheck.tsv`。复核到 330 条时统计：约 45% 在原图读出、约 48% 落在胶片装订缝
   黑边里读不出、约 7% 定位错。用户决定不再寻找其他 1633 实物扫描（网上没有），改按下一步处理。
6. **重印本补定**：仍是推断的 1,308 条里，1862 同位读出同一词（只差古今拼法）的 502 条，按证人读数落
   （`gap_promote_r1862.tsv`，用户 2026-10-21 同意）。1848 本只再定位到 13 条（同一修订本，改写处一样读不出）。

### 落盘口径（`scripts/adams_common.py`）

- 证人读出：直接替换缺字词，拼法照 1633（本书语料常用写法）。
- 推补（仍是 P: 的 806 条）：正文写 `⟦…⟧`，发布为 `.ad-conj` 方括号另色，title 写明「编者推补，非原书原文」。
  用户 2026-10-21 同意先以推补发布；将来若取得 1633 实物照片，按清单替换。
- 判不了（?）与两份证人都没定位到的（262 条，其中 161 条是页边经文出处）：记号留在页面上标红（`.ad-gap`），
  发布时剩 548 个记号。
- `∅`：原图该处并无缺词（TCP 误标，如 #1202），删记号。
- 落点对齐：抽取产物里的缺字词组按文档顺序与 `gap_sites.json` 同串比对（窗口内找）；对不上的 6 组不落、报出。

## 照原样

- TCP 自身的拼写与录入（如 1-1 的 `withou plentifull`，非缺字）不改。
- 1633 原书的排印异常照录（如 `Hevven`、`faderis`、`Forulesse`）。

## 文件

| 文件 | 内容 |
|---|---|
| `src/A00665.xml` | TCP 原件（入库） |
| `gap_sites.json` | 缺字清单（gid） |
| `witness_locs.json` | 各证人定位与预填（auto / tier） |
| `gap_decisions_witness.tsv` | 预填结果（给人看） |
| `review_plan.json` | 抽样／逐条看图的条目表 |
| `gap_review.tsv` | 逐条看图判读 |
| `gap_recheck.tsv` | 推断条目对照原图复核 |
| `gap_promote_r1862.tsv` | 1862 同位读出、升为证人读数的 502 条 |
| `en_chapters/*.md` | 抽取产物（未落判读） |
| `witness/` | 证人 hOCR、词流、裁图、判读图（不入库，可重建） |

## 重跑

```
python3 scripts/adams_witness.py gaps
python3 scripts/adams_witness.py build --keys r1862,bim     # 下载 hOCR，建词流
python3 scripts/adams_witness.py match && python3 scripts/adams_witness.py judge
python3 scripts/extract_adams.py --apply
python3 scripts/adams_common.py                           # 自检：对齐与落盘统计
python3 scripts/publish_adams_en.py --apply
python3 scripts/build_commentaries_index.py
```
