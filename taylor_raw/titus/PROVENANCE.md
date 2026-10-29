# 泰勒《提多书注释》——底本与处理链

## 著者与著作

Thomas Taylor（托马斯·泰勒，1576 年生于约克郡里士满—1632/33 年 1 月或 2 月卒于艾尔沃思；生卒取 DNB vol.55，
Charlotte Fell Smith 撰，并 1904 年 Errata p.272 对求学经历的更正；原文存 `dnb_taylor.txt`。TCP 编目作 1576-1632，
是旧历纪年）。

*A Commentarie vpon the Epistle of S. Paul written to Titus. Preached in Cambridge by Thomas Taylor, and now published
for the further vse of the Church of God. With three short tables in the end …*，[Cambridge]: Printed [by Cantrell Legge]
for L. Greene, 1612，四开本（STC 23825）。献辞落款 From my house at Watford. March 16. 1612。

版次：

| 版 | 出处 | 本站用途 |
|---|---|---|
| 1612 初版 | TCP A13535；IA 两份胶片（见下） | **底本** |
| 1619 第二版 | 扉页：*Reviewed by the Author, and enlarged with some notes, and besides the addition of many hundreths of places of Scripture, with an Alphabeticall table …* Printed by Cantrell Legge, Printer to the Vniversitie of Cambridge. 1619（IA 题作 1618） | 只作旁证 |
| 1658 | IA `bim_…_taylor-thomas-divine_1658` | 只作旁证 |

用户 2026-10-28 要「找人工录入版」：只有 1612 初版有 TCP 录入本，所以底本是初版，不是 1619 增订版。

## 是否有中译本

2026-10-28 查（中文检索）：未见中译。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A13535**，人工录入 TEI P5，github `textcreationpartnership/A13535`，`src/A13535.xml`（入库） |
| 授权 | EEBO-TCP Phase 1（2005-03），CC0 1.0 |
| 原书影像 bim | archive.org `bim_early-english-books-1475-1640_a-commentarie-upon-the-e_taylor-thomas_1612_0`（IA40310604-73）：EEBO 缩微胶片 Early English books 1475-1640, reel 1037:2 的灰度扫描，**与 TCP 同一卷胶片**。叶号 = 访问页号（783 叶全部可访问）；TCP 一张图 = 一个对开，左页叶 2f−3、右页叶 2f−2（实测 p.1 = facs 9 = 叶 16） |
| 第二份藏本 bim2 | archive.org `bim_early-english-books-1475-1640_a-commentarie-upon-the-e_taylor-thomas_1612`（IA40310712-34）：同一版的另一份藏本的胶片，bim 读不出时拿它看 |

## 结构（`scripts/extract_taylor.py`）

原书不分讲，按经文逐段讲：段前排出经文（`<q>` 以「Vers. N.」起头），段内逐语解说（`<q>` 以「]」收尾）。
一段一页，页名 `<章>-<首节>`，共 43 段；节段 = 本段首节到下一段首节 − 1。ch2 第 5 节、ch3 第 2 节的分页点在页边旁注
「vers. 5」/段内「vers. 2」处。卷首 title / dedication / to-the-reader / argument（「The occasion」「The parts」两节），
卷末三个索引表 doctrines / observations / questions 与 errata。

## 缺字

TCP 标出：读不出的字母 820、整词 44、一截 9、外文（希腊/希伯来文）158；另有认不清的标点 `▪`。
按词并组后 1,067 组（正文 631、旁注 436），`gap_sites.json`（`scripts/taylor_witness.py gaps`）。

判读流程与落盘口径同罗洛克（`rollock_raw/thessalonians/PROVENANCE.md`）：

1. 定位：TCP 图号 → bim 叶号，只在那几叶里找；本地 tesseract 重跑（`scripts/taylor_bim_ocr.py`），OCR 只作定位。
2. 看图判读：每组裁出所在行（`taylor_witness.py sheets`），记入 `gap_review.tsv`（gid / 读法 / 依据 / 备注）。
   读法：原书拼法照录；`∅` = 原书无字；`?` = 判不了；`P:xx` = 推断（列 `gap_pending_approval.tsv` 待用户同意，
   同意的进 `gap_approved.tsv`，发布为方括号推补）。
3. TCP 录入错（非缺字）记 `tcp_fixes.tsv`，原串须全书唯一。
4. bim 上读不出的（书脊切字、墨团、页边小字）：`scripts/taylor_bim2.py` 在第二份藏本 bim2 的 IA hOCR 里按上下文定位，
   裁出同一行看；依据栏记 `img2`。

### 结果（2026-10-28 判读完毕）

| | 组数 |
|---|---|
| 看图读出（bim 或 bim2）并已落盘 | 966 |
| 推断 `P:`，列 `gap_pending_approval.tsv` 待用户同意，**未落** | 72 |
| 判不了 `?`（页面标红） | 29 |

- 推断 72 条的成因：墨团/污点盖住一两个字母（约 40 条，字形其余部分清楚）、页边希腊文小字重音与词尾看不全（约 20 条）、
  跨页估位没裁到原字（3 条）。按规矩一律不落，等用户逐条同意后抄进 `gap_approved.tsv`，发布为方括号推补。
- 判不了 29 条：两份胶片上都没能定位到的页边旁注 16 条，另有数字模糊、页边被墨渍整块盖住等。
- 原书误植照录（heatts、treee、lettes、haibourles、γεον/γεοφυτον——后者书末勘误改作 νεον/νεοφυτον）。
- TCP 录入错 3 条进 `tcp_fixes.tsv`：`A chilli,`→`Achilli,`；旁注 `χάρις, nor χάρισμα`→`non`；`Pides`→`Fides`。
- 自检：判读落下 966 组、原串不合 0、斜体星号奇偶未变；连跑两次发布零差异。

## 重跑

```
python3 scripts/extract_taylor.py --apply
python3 scripts/taylor_witness.py gaps
python3 scripts/taylor_bim_ocr.py          # witness/need_leaves.json 里的叶
python3 scripts/taylor_witness.py build && python3 scripts/taylor_witness.py match
python3 scripts/taylor_witness.py sheets --gids 0-99 --name a
python3 scripts/publish_taylor_en.py --apply
python3 scripts/build_commentaries_index.py
```

## 历代解经入口

提多书卡片入口用泰勒（用户 2026-10-28 指定）：`build_commentaries_index.py` 的 `LEAD_AUTHOR`。
费尔贝恩《教牧书信》的提多书部分保留，在费尔贝恩生平页「本站收录」与对照抽屉里照常可进。

## 2026-10-29 按 old-book-ocr skill 复查

- **§5.6 扉页手排**：`manual_pages/title.html`，照底本（bim，叶 0）原图逐行排：双线框、希腊文题辞、字号/字距/斜体/小型大写、横线；
  印刷商徽记（百合花，IN DOMINO CONFIDO）从底本原生分辨率胶片裁出 `img/taylor/device.jpg`。
  **两份藏本是同一版的两种发行本**：底本（TCP 所据）落款「Printed for L. GREENE. 1612.」，第二份（bim2）落款
  「Printed by CANTRELL LEGGE, Printer to the Vniversitie of CAMBRIDGE. 1612.」，其余排版相同。扉页按底本落款排；
  底本中部有大片水渍，水渍处的版式对照 bim2。题辞希腊文按原图补上重音（录入本作无重音的 Αρχην απαντων και τελοσ ποιει θεον）。
- **题头手排**：献辞、致读者、卷末三表中的两表（doctrines / observations）与问题表的题头，抽取压成一行 `##`，
  照原图逐行居中改排，放 `manual_heads/<slug>.html`，`publish_taylor_en.py` 的 `load_page()` 换入。
- **§4.4 渲染层**：无误生 `<table>`/`<ol>`/`<blockquote>`、无字面星号、无空强调或首尾带空白的 `<em>`、无重复 id。
- **§3.1 跨页断段**：「段尾无句末标点 + 下段小写起头」0 处（TCP 按原书分段）。
- **§3.2b 白名单**：游离字符只有原书缩写横（ē ō ū ā 等）与 5 处上圆点 `·`（TCP 照原书录入，保留）。
- **§4.1–4.3**：重跑抽取与库中产物逐字节一致；发布连跑两次零差异；判读 1,038 组全部命中，`tcp_fixes.tsv` 三条均在产物中生效。
- 用户问过 1:1「spread it selfe.」：原图第 4 页清楚印作 ſpread it ſelfe.，录入本无误。
