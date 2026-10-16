# 雷登《彼得前书实用注释》——底本与处理链

## 著者与著作

Robert Leighton（罗伯特·雷登，1611–1684），纽巴特尔牧师、爱丁堡大学校长，后任邓布兰主教、
格拉斯哥大主教（DNB vol. 33）。本书是纽巴特尔时期讲解彼得前书的手稿，生前未刊，身后分两卷出版。

## 底本

| 卷 | TCP | 版次 | 内容 |
|---|---|---|---|
| 卷一 | A47642（Phase 1，2004） | York: J. White, 1693，Wing L1028A / ESTC R216658 | 书名页、致敬虔的读者、第 1–2 章、勘误 |
| 卷二 | A47643（Phase 1，2004） | London: B.G. for Sam. Keble, 1694 | 准印、书名页、致基督徒读者、书商广告（不收）、勘误、第 3–5 章 |

授权：EEBO-TCP Phase 1 自 2015 年起整体公开；A47643 的 TEI 头仍是旧授权文字，A47642 已写 CC0。

### 归一与照原样

长 ſ → s；u/v、i/j（Iesus、Vnto）照原样；原书排印错照录（pnt、aud、jonrneys、fourd 等）。

### 原书版式（抽取器据此处理）

- 卷一经文标签在 `<head>`（`Verses. 8, 9.`），卷二在 `<bibl>`；div@n（卷一）给节号。
- 未单列的节：1:19 在 1:18 单元讲解里引了，2:8 在 2:7 单元里引了 → 锚点挂过去；
  2:19–20 原书没讲，不挂。3:21 原书列了两次，锚点只给头一次。
- 两卷页码各自从 1 起：锚点 id 带卷号 `p1-12` / `p2-12`。

## 缺字

TCP 缺字词 1,095 个（字母 884、整词 70、一截 12、希腊文 99、标点若干）。

### 证人

| 键 | IA item | 用途 |
|---|---|---|
| orig | `comment00leig`（1693 卷一）、`pract00leig`（1694 卷二），普林斯顿神学院藏本 | **同一版**实物扫描，判读最终依据 |
| r1864 | `1864practicalcom01/02leiguoft`（Philadelphia: Presbyterian Board） | 重排本，OCR 干净，只用来定位 |

IA 页图接口 `page/n{N}` 的 N 只数对外显示的叶，hOCR 的页序号是全部扫描叶，**要按 `_scandata.xml` 的
addToAccessFormats 换算**——第一版判读图没换算，整批裁到别页，已重出。

### 结果

- 逐张看图复核：1,054 处判出落盘（`gap_review_witness.tsv`，证据 `img orig <item> n<leaf>`）。
- 卷一勘误表在原书第 501 叶，其中 5 处缺字直接从影像读出。
- **用户规定（2026-10-16）：不能猜，推断必须经过同意。** 语料推断不直接落盘；剩余 41 处列于
  `gap_pending_approval.tsv`（建议 + 依据），同意的移入 `gap_review_approved.tsv` 再落盘，
  页面上以方括号另色标出。

## 重跑

```
python3 scripts/extract_leighton.py --apply
python3 scripts/leighton_gapfill.py --apply     # 只导出看图复核 + 经同意的条目
python3 scripts/leighton_common.py              # 自检
python3 scripts/publish_leighton_en.py --apply
python3 scripts/build_commentaries_index.py
```
