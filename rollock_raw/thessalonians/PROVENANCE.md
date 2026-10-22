# 罗洛克《帖撒罗尼迦前后书讲章》——底本与处理链

## 著者与著作

Robert Rollock（罗伯特·罗洛克，约 1555–1599 年 2 月 8 日），爱丁堡大学首任校长、神学教授，
爱丁堡牧师（生平据 DNB vol. 49，T. F. Henderson 撰）。拉丁文 *Commentarius in utramque Epistolam ad
Thessalonicenses*（Edinburgh 1598）之外，他在爱丁堡讲台上逐节讲解这两卷书的英文讲章，身后由编者收集
听众笔录、对照拉丁文注释整理（见卷首 *To the Christian Reader*），1606 年印行：

*Lectures vpon the First and Second Epistles of Paul to the Thessalonians: preached by that faithfull
seruant of God M. Robert Rollock*，Edinburgh: Robert Charteris, 1606，[16], 246 [i.e. 346], [4], 173, [1] p.，
STC 21281 / ESTC S116171。帖后另有扉页与页码，帖前帖后的书帖记号连续。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A11010**（人工录入 TEI P5），github `textcreationpartnership/A11010`，`src/A11010.xml` |
| 授权 | EEBO-TCP Phase 1（2005-12），CC0 1.0（转录文本） |
| 录入 | 2005-07 Aptara 照 ProQuest 页图录入；2005-08 Judith Siefring 抽样校对 |
| TCP 来源页图 | ProQuest EEBO image set 16659，269 张 1-bit 黑白 TIFF（一张一个对开） |
| 原版影像 | `bim` = archive.org `bim_early-english-books-1475-1640_lectures-upon-the-first-_rollock-robert_1606`（同一卷胶片的 800 ppi 灰度扫描，537 叶，一叶一页） |

找过、用不了的：
- **Wodrow Society《Select Works of Robert Rollock》**（1844、1849 两卷，IA `selectworksofrob01roll` / `selectworksofrob02roll`）：
  不收这部讲章（卷一是《论有效的呼召》，卷二是讲章与受难史讲义），当不了重印本证人。
- IA 上 `robertirollocisc00roll`（1601 Herborn）与 bim 1598 版是**拉丁文注释**，另一部书，不作证人。
- **IA 自带的 bim hOCR**：漏词严重（一行常只认出一半），按上下文定位只定到 19%。改为本地重跑 OCR，见下。

## 结构

`scripts/extract_rollock.py`：一讲一页，页名 `<章>-<首节>`（帖前 27 讲、帖后 14 讲），卷首
`title` / `dedication` / `to-the-reader` / `argument`（帖后只有 `title` / `argument`）。讲前排出的经文
（`<epigraph>`）→ `.rl-text`，逐节一段；页边旁注 321 条 → `.rl-margin`；印本页码 → `.rl-pb`。
讲前经文标签录入有误的按讲内逐节经文改：帖后第 5 讲 `verſ. 34.` 实为 2:3–4（`BIBL_FIX`）。

发布（`scripts/publish_rollock_en.py`）：跨章的讲（帖前第 4 讲 1:9–2:2、第 13 讲 3:13–4:3）在两章的
目录页里都列出；每个经文框后按框里的节号挂 commentary-anchor。

## 缺字

TCP 标出的缺口：读不出的字母 715、整词 239、一截 144、外文 2；另有认不清的标点 269 处（`▪`）。
按词并组后 1,202 组（正文 1,122、旁注 80），`gap_sites.json`（`scripts/rollock_witness.py gaps`）。

### 判读流程

1. **定位**：每组缺字所在的 TCP 图号（`<pb facs>`）→ bim 叶号：一张 TCP 图是一个对开，左页 = 2f−3、
   右页 = 2f−2（实测 p.1 = facs 8 = 叶 14；帖后 p.173 = facs 269 = 叶 536）。只在这几叶里找。
2. **本地 OCR**（`scripts/rollock_bim_ocr.py`）：整页原图下载 → 缩一半（≈400 ppi）存档供裁图 →
   tesseract eng、psm 3、中值滤波 → 词与坐标。原图不留（磁盘紧）。OCR 读数**只用来定位**，不作证据。
3. **看图判读**：每组裁出所在行，记入 `gap_review.tsv`（gid / 读法 / 依据 / 备注）。
   读法：原书拼法照录；`∅` = 原书此处无字；`?` = 判不了；`P:xx` = 推断（列清单待用户同意，同意的进
   `gap_approved.tsv`，发布为 ⟦…⟧ 方括号推补）。

### 落盘口径（`scripts/rollock_common.py`）

缺字组按抽取产物的文档顺序编号；落盘时逐组核对原串与 `gap_sites.json` 一致才落，抽取改动导致编号漂移
会被拦下。TCP 录入错（非缺字）记 `tcp_fixes.tsv`，原串须全书唯一。

### 进度（2026-10-22 判读完毕）

- 1,202 组全部看过原版影像：读出 1,036、原书无字 2（∅）、判不了 163（?）、推断 1（P:，待用户同意：gid 201 `rejoising for`）。
  读出的已落盘；判不了的以红色记号留在页面上。
- **判不了的 163 组都是胶片本身的毛病，不是没去看**：
  - 重影 90：p.341–342、帖后 p.26、p.95、p.98 等几页拍了两次、两次影像错位叠印，字叠字；
  - 透印 33：p.116、p.234、p.312–325 等页背面字透过来，与正面笔画混在一起；
  - 污渍 23：p.65–66 页底一大块胶片污渍；
  - 其他 17：标点看不清、手写批注潦草、希腊文小字（gid 13，形似 εὖ πράττειν）。
  这几类只有换一份藏本的影像才有可能读出；网上只有这一份胶片扫描。
- **藏本上的手写批注**：这份藏本页边有前人读者的手写批注（ob. / R. / v. p.147 / 1. Thess. 4.17 等，书末署 "Read thro 1st September 1838"）。
  TCP 录入员把其中一部分当作页边旁注录进去了，判读时照原图读出的手写字照录，备注里注明「手写」。
- 定位：IA 自带 hOCR 漏词太多，改本地 tesseract 全书 537 叶重跑（`rollock_bim_ocr.py`）；`rollock_witness.py match`
  先按字符级编辑距离（edlib，免受 OCR 粘词影响）在 TCP 图号对应的几叶里找，找不到的按词流插值估位、按印本页码对叶，
  整页出判读图（`rollock_pagesheets.py`），重影/透印页另出原分辨率三段放大图（`--zoom 3`）。
- TCP 录入错 14 条进 `tcp_fixes.tsv`（看图时顺带发现；最大一处 p.112 漏录一整句并错置）。
- 两卷扉页照原书影像手排（`manual_pages/`），花边与印刷商徽记（Justitia / Religio 木刻）裁自胶片，存 `img/rollock/`。

### 第二轮：判不了的 163 组按 800 ppi 原图重看（2026-10-22）

- 先找第二份影像：EEBO（Michigan / Oxford）与 archive.org 是同一卷胶片（Huntington 图书馆藏本）；Google Books、
  Wodrow 选集均无全书影像。图像处理（找叠印的来源页、背面镜像相减）试过，叠印上来的字对不上任何相邻页，减不掉。
- 改用 IA 原始 800 ppi 页图（前面判读用的是半尺寸），重影/透印页按条带（`rollock_bands.py`）、零散的按原分辨率裁图
  （`rollock_fullcrop.py`）逐条看。结果：163 组里**又读出 98 组**；**44 组字形看得出大概但不够清楚**，写成推断，
  列在 `gap_pending_approval.tsv` 待用户逐条同意；**21 组仍读不出**（p.66 页底整块黑污渍 9、墨点盖字 2、
  手写批注潦草 2、重影太重 6、页码数字 2）。
- 看图时又发现 TCP 录入错 2 条进 `tcp_fixes.tsv`：帖后 1:8 引文 TCP 漏录 *knovv **not** God* 的 not（意思相反）；
  帖前 5:24 讲 `so hes no appoynted` 实为 `so hes he appoynted`。
