# 坎德利什《约翰一书讲解》——底本与处理链

## 著者与著作

Robert Smith Candlish（罗伯特·坎德利什，1806 生于爱丁堡—1873 年 10 月 19 日卒；生卒取 DNB vol.8，W. G. Blaikie 撰，
原文存 `src/dnb/`）。*The First Epistle of John, Expounded in a Series of Lectures*，46 讲。据第一版序（脚注）：
1860 年 10 月开讲，至 1864 年 1 月讲完；第一版序写于 1866 年（文中「last year (1865)」）；第二版序署 1869 年。
IA 上普林斯顿神学院藏第二版两卷（firstepistleofjo01cand / 02cand）印本年份 1870，Edinburgh: A. and C. Black；
另有 1877 第三版单卷本（firstepistlejoh01candgoog）。

## 是否有中译本

2026-10-27 查：未见正式中译（ccbiblestudy 约翰一书书目只收英文本）。

## 底本：用户指定「人工录入版」，不用扫描件

2026-10-27 用户明令「不要用扫描件」「就用人工录入的那版」。所以本书**不走 OCR／影像判读**，正文据：

| | 来源 | 用途 |
|---|---|---|
| 底本 | **Monergism Books 电子本**（2020，PDF；ePub/mobi 被 Cloudflare 挡）<br>`https://www.monergism.com/thethreshold/sdg/candlish/The%20First%20Epistle%20of%20John%20Expou%20-%20Robert%20Candlish.pdf` | 全部正文 |
| 第二证人 | **ccbiblestudy.org 的 e-Sword 本**（两卷 .doc，BibleSupport.com 制作，自称出自 William A. Anderson 2008 年 Libronix 本，扉页作 1877 第三版）<br>`https://ccbiblestudy.org/New%20Testament/62%201John/62-1John-E/` 620175 / 620176 | 脚注正文、段落起点、Monergism 漏文与错字的旁证 |

`src/` 不入库（Monergism 文末声明保留其电子版权利；两份都可按上面地址重下）。

### 两份录入本的性质（对齐实测，`scripts/align_candlish.py`）

**不是同一份录入本**（我起初以为是，逐词对齐后推翻）：
- Monergism 更近原书：保留 `ver.`、`Holy Ghost`、`stedfastly`、`fulness`、`Eccles.`/`Isa.` 之类缩写；
  但经文引用已改作现代格式（`John 15:11`，原书 `John xv. 11`）、标点有改动（原书 `;—"` 多作 `:`）、**斜体全无**、
  **作者脚注正文全丢**（只剩 28 个 `*` 与 1 个 `†`）。
- e-Sword 本改得更多：Holy Ghost→Holy Spirit、经卷缩写展开、fulness→fullness；并有该模块转换的系统性损坏——
  与经卷缩写同形的词被展开成经卷名加「 ,」（is→`Isaiah ,`、Son→`Song of Solomon ,`、he→`Hebrews ,`、
  man→`Prayer of Manasseh ,`、Re-→`Revelation -`）、经文出处包 HYPERLINK 域或整个被吃掉成 `()`、数字与前词粘连
  （`October1860 ,`）；第 2 卷开头与第 XXX、XXXVI 讲前有整讲重复；脚注那部分是 OCR 文字（cither / tome / lam）。

### 处理

1. `scripts/extract_candlish.py`：PDF → `units.json`。一块一段；讲题 Georgia-Bold 21.2pt，部分标题 25pt，题记经文 x0≈92。
   跨页：上页末块末行排满（x1 ≥ 515）即与下页首块相接，接缝留 `\n⁣` 记号。末页「-----」之后是 Monergism 版权声明，不收。
2. 跨页接缝（378 处）：接缝后的文字是 e-Sword 本某段的开头 → 分段（7 处），否则接上。另有 4 处 e-Sword 本分段而
   Monergism 排在同一行中间的，照 Monergism 不分。
3. `manual_fixes.tsv`（7 条）：只收「e-Sword 本同位读出、Monergism 读成非词或漏文」的——
   childen / atleast / apssing / seryant、trumpetcall / forthflowing 两处连字符，
   以及第 XXIX 讲 Monergism 在两个 in 之间跳行漏掉的 46 个词。每条须恰好命中一次。
4. 脚注（`scripts/candlish_notes.py` 定位 → `candlish_build_notes.py` 机械清理 → `notes.json` 定稿）：
   按 `*` 前的文字在 e-Sword 本里找对应的括注或「1]」段。清理只做导出损坏的还原（经卷名误展开、粘连、
   残下的「 ,」、`Lcke`→`Lücke`、`ver24`→`ver. 24`）；被吃掉的经文出处标 ⟦lost⟧，页面显示灰色「…」。
   第 XV 讲的长附注「Note referred to at page 186」作脚注排。第 XVI 讲 `abide in the Father and the Son."*`
   两份录入本都没有正文，留号注明缺文。
5. `scripts/publish_candlish_en.py`：一讲一页 `lecture-N`（不用裸数字，扫描器把 `<N>.md` 当章页）；
   `1`–`5` 章目录页；`contents`（作者的分析目录，序言里特别请读者留意）；`preface-2` / `preface-1`。
   经文锚点 `1john-<章>-<节>` 只挂第一次讲到该节的那一讲（全书 105 节齐）。
   破折号后紧贴字母的直引号写死为开引号（kramdown 智能引号把 `;—"But` 判成收引号，123 处）。

### 待同意（`notes_pending.tsv`，未经同意不落）

两份共有的错字 3 处、目录 `5:26`、e-Sword 脚注的 OCR 错字 6 处、被吃掉的经文出处 4 处、缺文脚注 1 条。

## 验收

- 渲染：表格 0、正文 `<ol>` 0、字面 `[^` 0、脚注引用 29 = 脚注 29、锚点 105 无重复、渲染前后实词无丢失、
  引号方向（`”` 后紧跟字母 / `“` 后紧跟空白）0。
- 重跑：`extract → publish --apply` 两次产物逐字节不变。
