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
  未改）。9:43 一讲题作「43, 44, unto ver. 49.」，节段取 43–49。2026-11-05 对照原版影像（叶 490、545）：原书即如此印，是原书印错，录入无误。
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

## 判读进度（2026-11-04）

- 影像证人：IA `bim_…_petter-george_1661`（与 TCP 同卷胶片）；第二份独立影像网上未找到（IA / Google Books / HathiTrust / Open Library / reformedbooksonline 均无）。
- 看图判读 gid 0–774（`gap_review.tsv`）：看图逐张判读太耗额度，774 以后停。原生 800 ppi 比服务端半宽图清楚得多（#633 appeard），若再看图应取原生分辨率。
- 本地语料自证 + 本地 OCR 裁定（`scripts/petter_gapfill.py` → `gap_corpus.tsv`，零模型额度）：682 组可判（lex 唯一候选 / ctx 三元搭配 / ocr 多候选中与本地 OCR 读数吻合者）；
  与看图读法对照 226 组一致、1 组不一致（#646 even/ever，OCR 档误判）。**全部待用户同意**，同意的抄进 gap_approved.tsv。
- 余 899 组：字母级多候选或已知字母过少、希腊文 121、缺整词/成段 114、缺标点 46。
- 第二轮看图（2026-11-05，只做希腊文 + 缺整词）：第一轮未看过的 65 组 + 第一轮「判不了」8 组，共 73 组，**取 IA 原生分辨率整页**
  （不经服务端缩图）裁图。定位：插值估位/行重定位多落错，改为按左右上下文词在本地 OCR 词序列里模糊对齐，仍找不到的按关键词搜叶号。
  看图读出 46（希腊文 37 + 英文 9，已落盘）、P: 推断 20（墨淡/褪色，待同意不落）、仍判不了 5（#4 #15 #157 #383 #1573 页角撕损）、
  未定位 1（#530）、#280 维持原判。20 条推断用户 2026-11-05 整批同意 → `gap_approved.tsv`，正文以 [方括号] 另色标出，书首页逐条列「编者推补逐条说明」「仍读不出的」两表（从判读表生成）。#775 录入本记作希腊文，原图其实是英文（from doing）。本书希腊字体 ρ 形近 ε（πυρία、θηρίῳ、τραπεζῖται）。
- 第三轮看图（2026-11-05，用户令「都要看图解决」）：余下 1380 组全部按左右邻词在本地 OCR 词序列里重新对齐、只裁缺字那一行
  （原生分辨率，整页用完即删），每张判读图约 10 条并列出第一轮读法/语料读法作对照。读出 223 组落盘；P: 推断 962 组
  （字母未着墨/墨淡，字形与候选相合）待同意；仍定位不到约 190 组（对齐落错行、旧估位也不准），记在判读表外待补。
  看图纠正语料读法若干：#780 our（非 out）、#803 小写 see、#1079 content（非 consent）、#901/#1221 Joh.（非 Job）。
  原书误植照录：temptarions、teachihg、prophefied、tbat、publibk、gifrs、scaree、he（=be）。
- 第三轮推断 991 条 + 第二轮 20 条用户同意发布；未定位组改全书 OCR 检索（12 读出、31 推断，同意发布）。
- 第四轮（2026-11-05，锚词定位）：本地 OCR 的 `words` **不是阅读顺序**，按序拼串检索在后半书（页面弧度大、OCR 碎）失效。
  改为：以已读组建 facs→叶号校准表插值，±4 叶内取缺字前后 ±30 词在 OCR 里的命中词纵坐标做线性拟合定行，裁整页宽约 10 行横条看图。
  122 组对准 110：读出 21 落盘、推断 88（用户同意发布）、判不了 1（#1369，后改 P:taxeth 待同意：本书 taxeth 3 次含「our Saviour also taxeth them in this Reproof」）。
  仍定位不到 12 组：#792 902 976 1002 1005 1028 1044 1049 1081 1117 1449 1458。
- 推补在正文改用无衬线字体 + 方括号 + 另色 + 虚下划线（用户 2026-11-05 要求），首页说明写明。
- 按 old-book-ocr 验收（2026-11-05）：发布两次零差异（幂等，stderr 可见）；对会话前基线 3186da542 逐词比对 1455 处改动全部落在缺字组内、组外 0；
  判读 1561 条全部落地（原串核对）；渲染层（kramdown GFM 逐页）表格 0、有序列表 0、`<em>` 首尾空白 0、字面星号 0、重复 id 0、渲染丢词 0；
  跨页断段只剩 6 处「As／And + 分条 1.」（原书即分段）；白名单字符体检捞出 8:34c 讲题 `follow me.=` 多出等号（第 568 叶原图无）→ `tcp_fixes.tsv`。
- 扉页照第 2 叶原图手排（`manual_pages/title.html`，§5.6）：分行、字号、斜体、框线、题辞两段；æ 照原图；手写藏书署名 Andr. Thomson 不录。
