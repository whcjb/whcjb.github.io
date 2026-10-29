# 阿特索尔《腓利门书注释》——底本与处理链

## 著者与著作

William Attersoll（威廉·阿特索尔，生年不详—1640 年 5 月 30 日葬于萨塞克斯郡伊斯菲尔德；DNB vol.2，
A. B. Grosart 撰，原文存 `dnb_attersoll.txt`）。剑桥克莱尔学堂文学学士 1582、彼得学院文学硕士 1586；
1600 年起任伊斯菲尔德堂区牧师至去世。

*A Commentarie vpon the Epistle of Saint Paule to Philemon …*，London: William Iaggard, 1612，四开本（STC 890）。
献辞献给 Sir Thomas Pelham, Baronet。

| 版 | 出处 | 本站用途 |
|---|---|---|
| 1612 初版 | TCP A22481；IA 胶片 `bim_…_attersoll-william_1612`（IA40310712-04） | **底本** |
| 1633 第二版（corrected and enlarged，STC 891） | IA `bim_…_william-attersoll_1633`；无 TCP 录入本 | 只作旁证 |

## 是否有中译本

2026-10-29 查（中文检索）：未见中译。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A22481**，人工录入 TEI P5，github `textcreationpartnership/A22481`，`src/A22481.xml`（入库） |
| 授权 | EEBO-TCP Phase 2（2014-11），CC0 1.0 |
| 原书影像 bim | 与 TCP 同一卷胶片（Early English books 1475-1640, 1265:10）的灰度扫描，579 叶全部可访问；叶号 ≈ 印本页 + 21（IA page_numbers.json 有两三叶的偏差，定位时前后各放宽几叶） |
| 1633 旁证 | IA 自带 djvu.xml 词坐标定位；半宽图 4378 宽，坐标按原图 8756 宽 |

## 结构（`scripts/extract_attersoll.py`）

TCP 已按经文分 15 段（`<div type="verse(s)" n="1-2">`），一段一页，页名 `1-<首节>`；另出章目录 `1.md`。
卷首：title / dedication / to-the-reader / doctrines（全书教义总览）/ preface；卷末：contents-table（内容索引，
**不叫 index**，免与书首页撞路径）/ errata。页边旁注分两种：runSum（要点）→ `.at-sum`，带字母 n 的出处 → `data-n`。
单段篇幅大（1:4–5 一页约 28 万字符），照原书分段，不另拆。

## 缺字

TCP 标出：读不出的字母 134、整词 1、外文 5；认不清的标点 `▪` 16。按词并组 155 组（正文 134、旁注 21）。

判读流程同泰勒（`taylor_raw/titus/PROVENANCE.md`）：
1. 定位：印本页 → bim 叶（前后各放宽），本地 tesseract（eng，psm 3，中值滤波）重跑只作定位；
   1633 版用 djvu.xml 词坐标，得分低的按前后组的叶号收窄。
2. 看图判读，记入 `gap_review.tsv`（gid / 读法 / 依据 / 备注）。依据：`img` = 1612 胶片看图；`e1633` = 1633 版同位读出（看图）。
   1612 原图读不出、1633 同句清楚的，作 `img+e1633` 或 `e1633` 落盘（两版同一句的文字差异另记在备注里，1612 拼法优先）。
3. 推断 `P:` 列 `gap_pending_approval.tsv`，**未落**，等用户同意后抄进 `gap_approved.tsv`。

### 结果（2026-10-29）

| | 组数 |
|---|---|
| 看图读出（1612 或 1633）并已落盘 | 131 |
| 推断 `P:`，待用户同意，**未落** | 12 |
| 判不了 `?`（页面标红） | 12 |

- 判不了的多在书末内容索引的页码数字：1612 印残，1633 版索引末叶霉损读不出。
- 原书误植照录：mede（= made，1:15–16，p.292）；勘误表已列的 cooperation、Churles 等按原印照录（勘误页另有）。
- 第 5 组（1:1–2，p.15）：1612 原印 the 错排在 faithfull 之后，旧藏者划去并手改到 that 之后；1633 本句作 that the faithfull afflicted。
  按原印位置补 the，列为推断。

## 重跑

```
python3 scripts/extract_attersoll.py --apply
python3 scripts/attersoll_witness.py gaps
python3 scripts/attersoll_witness.py crops        # 取叶 + 本地 OCR + 裁图（witness/，不入库）
python3 scripts/publish_attersoll_en.py --apply
python3 scripts/build_commentaries_index.py
```

## 2026-10-29 按 old-book-ocr skill 复查

- **§5.6 扉页手排**：`manual_pages/title.html`，照底本（bim 叶 0）原图逐行排：双线框、各区横线、两组大括号排法
  （œconomicall / Politicall / Ecclesiasticall；As { Of …十一条）、小型大写人名、斜体。录入本作 oeconomicall，原图是 œ 连字，照原图。
  扉页无印刷商徽记。
- **题头手排**：献辞、致读者、教义总览、序论（An Exposition of the Epistle…）、书末内容索引的题头照原图逐行排，放
  `manual_heads/<slug>.html`；各题头上方的木刻花饰从原书胶片裁出放 `img/attersoll/headpiece-*.jpg`（献辞、致读者、
  索引各一种，教义总览与序论共用同一块）。勘误页题头只一行，不另排。
- **致读者整篇斜体**：原图（叶 10–17）此篇正文排斜体、人名与引语排正体，TCP 的 `<hi>` 标的是「换字体」，抽出的 `*…*`
  其实是正体段。发布时整篇包进 `.at-itbody` 由样式反转（`publish_attersoll_en.py` 的 `ITALIC_BODY`），不改抽取产物。
  其余各篇原图正文为正体，与录入本一致。
- **§3.1 跨页断段**：「段尾无句末标点 + 下段小写起头」只有扉页 1 处（大括号排法），已由手排取代；正文 0 处。
- **§3.2b 白名单**：游离字符只有原书字形——缩写横（103）、呼格 ô（22）、quàm 的 à、扉页 ¶，以及缺字记号；无噪点。
- **§4.1–4.3**：重跑抽取与库中产物逐字节一致；`gaps` 重跑一致；发布连跑两次零差异；判读 131 组全部命中、原串不合 0。
- **§4.4 渲染层**：正文区无误生 `<table>`/`<ol>`/`<blockquote>`、无字面星号、无空强调或首尾带空白的 `<em>`、无重复 id；
  逐页比对渲染前后实词，丢词 0。桌面宽度截图看过扉页与各题头页。
- 胶片叶 538–551 是卷首（扉页至致读者）的重拍，可作卷首的第二影像。
