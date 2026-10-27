# 詹金《犹大书讲解》——底本与处理链

## 著者与著作

William Jenkyn（威廉·詹金，1613 年 12 月受洗—1685 年 1 月 19 日卒于新门监狱；生卒取 DNB vol.29，Alexander Gordon 撰，
TCP 编目同）。*An Exposition of the Epistle of Jude, together with many large and usefull Deductions*，两部分，四开本，
London: Tho. Maxey for Samuel Gellibrand：

| | 内容 | 出版 | Wing |
|---|---|---|---|
| 第一部分 | 第 1–8 节（XL 讲），印本页 1–640 | 1652（Thomason 藏本扉页改作 1653，手写 May 13） | J639 |
| 第二部分 | 第 8–25 节，印本页 1–686 | 1654 | — |

1658 年合为对开本一册重印；另有 1783 格拉斯哥本、1839/1840 伦敦 Sherman 编订本、1865 爱丁堡 Nichol 本。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A87554**（第一部分）、**A87557**（第二部分），人工录入 TEI P5，github `textcreationpartnership/` |
| 授权 | EEBO-TCP Phase 2（2011-12），CC0 1.0（转录文本） |
| 原书影像 | `bim52` = archive.org `bim_early-english-books-1641-1700_an-exposition-of-the-epi_jenkyn-william_1652`（第一部分，**与 TCP 同版**的缩微胶片灰度扫描） |
| | `bim56` = archive.org `bim_early-english-books-1641-1700_an-exposition-of-the-epi_jenkyn-william_1656`（IA 题作 First part，实为 **1656 年第二版**全书：前约 300 叶第一部分、其后第二部分；第二部分 1654 初版网上无扫描，只能拿这一版作旁证） |
| 重印本证人 | `r1865` = archive.org `expositionuponep00jenk`（Edinburgh: J. Nichol 1865，现代拼法；**删去了全部页边旁注**） |

查过未用：1839 Holdsworth 本（`anexpositionupo01shergoog`，与 1865 同一 Sherman 系统）。

## 是否有中译本

2026-10-27 查：未见正式中译（按 memory「有中译本的书一律不做」先查后开工）。

## 结构（`scripts/extract_jenkyn.py`）

一节一篇（犹大书只一章，发布页名 `1-<首节>`；14–15、17–19、22–23、24–25 合讲）；第 8 节两部分各讲一段，
第二部分那段为 `1-8-ii`。卷首 `title1` / `to-the-reader` / `errata1` / `advertisement`；第二部分 `title2` / `dedication`
排在 `1-8-ii` 前；书末 `errata2`。EXPLICATION / OBSERVATIONS 小标题 → `###`；旁注 → `.jk-margin`；
印本页码 → `.jk-pb`（第一部分 id `pN`、第二部分 `qN`）。`<add>`（Thomason 藏本的手写日期等）丢弃。
原书的星号参见记号写成 `&#42;`，不与斜体星号混。

发布（`scripts/publish_jenkyn_en.py`）：一节超过 120k 字符在段落之间切页（续页 `-k`），共 44 页。
经文锚点 `jude-1-<节>` 只挂第一次讲解（`1-8-ii` 不挂）。

## 缺字

TCP 标出缺字元素 1,641 个（外文 861、字母 685、标点 76、整词 18、一截 1），按词并组后 **1,557 处**
（`gap_sites.json`）。与 adams 不同：抽取时每个缺字元素前嵌编号 `N`，判读按编号精确落位，
不靠串比对（`jenkyn_common.py`，自检「落不下 0」）。

### 判读流程（2026-10-27）

1. **定位**（`jenkyn_witness.py match/relocate`）：TCP 上下文三词组投票，在 r1865 与对应胶片的 IA hOCR 词流里定位。
   正文几乎全部定位到；旁注因 1865 本删了、上下文又短，另走 `notes`/`renotes`：按 TCP 影像号推叶号，在前后几叶里按字符模糊对齐。
2. **预填**（`judge`）：同 adams 三道闸（真词闸、邻词闸、残字闸）。A/B 档 169 条；每 7 条抽 1 看图（25 条），
   24 条相合，1 条（#30 `it'`/its）判不了改 `?`，其余整档采信。认不清的标点不预填（1865 标点已现代化），一律看胶片。
3. **逐条看图**：正文英文 C 档、正文希腊/希伯来文全部看图（1865 现代铅字 + 胶片对照）；旁注只看胶片。
   记入 `gap_review.tsv`（读法用原书拼法；`P:` 推断；`?` 判不了；`∅` 原书无字；`⁀` 与邻词连写）。
   第二部分的读法来自 1656 第二版，依据栏注明「1656 第二版」。

### 结果

| | 读出（看图或 A/B） | 推断待同意 `P:` | 判不了 `?` | 未看 |
|---|---|---|---|---|
| 正文 883 | 829 | 21 | 33 | 0 |
| 旁注 674 | 351 | 20 | 44 | 259 |

页面上剩红色记号 410 个（组内多词则多个记号）。**推断 41 条列 `gap_pending_approval.tsv`，未经用户同意不落**
（memory feedback_no_guess_inference_needs_approval）；同意后把 gid 抄进 `gap_approved.tsv`，发布时以 ⟦⟧ 推补显示，
首页自动生成逐条说明表。

旁注未看的 259 条：胶片 IA OCR 对旁注识别差，定不到叶内位置，裁图常落到正文；逐叶页边整栏图试过（`margins`/`nblocks`），
单页歪斜、命中低。要续做，可本地 tesseract 重跑胶片页边（参照 rollock_bim_ocr.py）再定位。

### 已知要再核的

- #1360：原书作 `proficiendi`，TCP 录作 `presi icu••` 两词（presi 本身也错），改动跨出缺口，暂留 `?`。
- #1067：两版都作「ἐλέγχετε for ἐλεεῖτε」，录入本只标一处缺口，1654 初版是否同此无图可核（列在推断里）。
- 第二部分凡据 1656 第二版读出的，理论上可能与 1654 初版有异（第二版自称 Corrected）；网上无 1654 扫描，未能再核。

## 文件

| 文件 | 内容 |
|---|---|
| `src/A87554.xml` `src/A87557.xml` | TCP 原件（入库） |
| `gap_sites.json` | 缺字词组（gid、所含缺字元素编号 gns、上下文） |
| `witness_locs.json` | 各证人定位与预填 |
| `gap_decisions_witness.tsv` | 预填结果（给人看） |
| `gap_review.tsv` | 逐条看图判读（后写覆盖先写） |
| `gap_pending_approval.tsv` | 推断待同意清单 |
| `en_chapters/*.md` | 抽取产物（带缺字编号，未落判读） |
| `witness/` | 证人 hOCR、整页图、裁图、判读图（不入库，可重建） |

## 重跑

```
python3 scripts/extract_jenkyn.py --apply
python3 scripts/jenkyn_witness.py gaps
python3 scripts/jenkyn_witness.py build                 # 下 hOCR，建词流
python3 scripts/jenkyn_witness.py match && python3 scripts/jenkyn_witness.py relocate
python3 scripts/jenkyn_witness.py notes && python3 scripts/jenkyn_witness.py renotes
python3 scripts/jenkyn_witness.py judge
python3 scripts/jenkyn_common.py                         # 自检：落下组数、落不下、剩余记号
python3 scripts/publish_jenkyn_en.py --apply
python3 scripts/build_commentaries_index.py
```
