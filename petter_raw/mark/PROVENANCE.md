# 佩特《马可福音注释》——底本与处理链

## 著者与著作

George Petter（乔治·佩特，?–1654）。无 DNB 条目。生平据本书卷首其弟约翰·佩特（J. Petter，序末署
「From my Study at Heaver, in the County of Kent. Septemb. 3. 1661」）的《致敬虔读者序》，与 Venn《剑桥校友录》
（venn.lib.cam.ac.uk，2026-11-04 查：PTR602G 1602 年复活节以 sizar 入三一学院，1605 奖学生，1605/6 BA，1609 MA，
「Probably of Brede, Sussex, clerk. Probably the author of a commentary on St Mark in two folio volumes. Will (P.C.C.) 1654」；
PTR615J John Petter「Perhaps R. of Hever, Kent, 1632-62, ejected」）。序言：生于肯特郡桑德赫斯特堂区；约十六岁入三一学院，
导师 Simon Aldrich；约二十四岁任布雷德（Bread/Brede）牧职，44 年；卒于第 68 年。

*A Learned, Pious, and Practical Commentary upon the Gospel according to St. Mark.* London: J. Streater, sold by
George Sawbridge, 1661，两卷对开本（Wing P1888，ESTC R220413）。原是 1618 年 6 月 7 日起在布雷德的逐主日讲章，
每讲经文旁页边记讲道日期（录入本所存 425 讲中 414 讲有日期，1618-06-07 至 1630-07 前后；1–3 月的日期按旧历纪年）。

## 是否有中译本

2026-11-04 网页检索：未见。未逐一查微读书／恩道／三联／橡树书目。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A54583**（Phase 2，2011-12），人工录入 TEI P5，github `textcreationpartnership/A54583`，`src/A54583.xml`（入库；sha256 2fe81211…72b00dd） |
| 授权 | EEBO-TCP，CC0 1.0 |
| 录入所据 | EEBO image set 36283（Early English books 1641-1700; 2052:17），大英图书馆藏本缩微胶片，461 帧 |
| **残缺** | TCP 题注「Imperfect; lacks all after p.884」「Catchword on p.884: Chap.」：只有第 1–11 章，**第 12–16 章整个没有**。原书索引所引页码到 1600 余页 |
| 原书影像 | 未找（2026-11-04）。缺字判读与后五章都要靠另一部完整藏本的影像 |

AGES 数字图书馆：未见收录（产品目录与 sabda 镜像按命名习惯试探均无）。

## 结构（`scripts/extract_petter.py`）

TEI：front = title_page / preface / index（字母主题索引）；body 一个大 div，书题后 `<div type="chapter">` × 11；
章下每个 `<div type="verse|verses" n="…">` 一讲：`<epigraph>`（`<bibl>Mark 1. 4.</bibl>` + `<q>` 经文，经文里夹
`<note place="margin">` 讲道日期）→ 讲解。同一节常连讲几讲，n 相同。

- 一讲一页，页名 `<章>-<首节>`，同首节第 2、3…讲加 b、c…（共 425 讲）；节段取 n，`36, &c.` 到同章下一讲首节 − 1。
- 卷首三篇：`title`、`preface`、`alphabetical-table`（**不叫 index**，免得盖掉书首页，见 memory feedback_slug_index_collision）。
- 页边纲目标记 `<label type="milestone"><seg type="milestoneunit">Obſerv. </seg>1</label>`（5778 处）→ `<span class="pt-mark">`。
  录入本里正文往往又写一遍（`*Observ.* 1. …`），照录不去重。
- 讲题与经文不合两处（`N_FIX`）：7:33–34 题作「Mark 7. 33, 24.」；8:31 题作「Mark 7. 31.」（n 已是 31，只是 bibl 不合，
  未改）。9:43 一讲题作「43, 44, unto ver. 49.」，节段取 43–49。未看影像，不定是印错还是录错。
- 章题（CHAP. II. …）并进本章第一讲；章末 trailer（Finis … Capitis）挂本章最后一讲末尾。
- 第十一章末 `<gap reason="missing" extent="1+ pages">` → 发布时换成一行「录入本到此为止」说明（`publish_petter_en.py`）。
- 三处 `<gap reason="duplicate">`（重拍的页）丢弃。`1+ letters` 一处记作 〈…〉。
- 字母索引的页码 ≤ 884 的，发布时链到该页所在那一讲的 `#pN` 锚点。

## 缺字

抽取统计：字母级 1523、整词 60、成段 54、外文未录（〈Greek〉）121、缺页 1。相邻合并成组后 1581 组
（`petter_witness.py gaps` → `gap_sites.json`；正文 1571、旁注 10）。**全部未判读**，页面标红。
判读表格式同迪克森（`petter_common.py` 文首）：`gap_review.tsv` 看图读出、`gap_approved.tsv` 用户同意的推断。

## 处理链

```
python3 scripts/extract_petter.py --apply
python3 scripts/petter_witness.py gaps
python3 scripts/publish_petter_en.py --apply
python3 scripts/build_commentaries_index.py
```
