# 巴罗夫《何西阿书讲解》抽章实读校勘记录

底本是 EEBO-TCP 人工双录入本（不是 OCR），对照杜克藏本实物扫描（第 2–4 卷同版；第 1 卷证人是 1643 初版、他版，只作旁证）。
随机抽一段（站上一页），逐页对影像读，错处落 `tcp_fixes.tsv`（词句）、`gap_review.tsv`（缺字），整类的在抽取层改判据。

| 轮 | 日期 | 抽中 | 印本页 | 页数 | 本段错处 | 每页 |
|---|---|---|---|---|---|---|
| 1 | 2026-11-26 | 第 3 卷 10:12 | pp. 442–487（456 后原书页码跳到 467） | 36 | 约 30（正文词句 11、斜体 5、缺字 6、旁注正斜整条颠倒 4 条） | ≈ 0.8 |

## 第 1 轮（10:12）

整类（抽取层 `extract_burroughs.py`）：
- **拉丁旁注正斜颠倒**：原书拉丁旁注底子是斜体、出处人名与英文连接词正体，录入本只给正体部分标 `<hi>`，抽出来恰好反了
  （本段 Hierom、Arias Mont.、Paratus sum、Ipsa gratiarum actio 四条；另在第 1、2、4 卷各抽一条看图核实：
  1643 初版 p.95 Cujus faciem、第 2 卷 p.376 Septuag./Calv.、第 4 卷 p.510 Pareus，印法相同）。
  格林希尔那条整条正斜互换规则接进来，但它的外文判据（英文虚词 < 15%）在本书把英文短旁注（Use to Ministers.、Fair Skins foul Souls…）也判成外文，
  改为：三字母以上小写词 ≥ 2 个、其中本书正文常用词（≥ 20 次）不到三分之一，且有拉丁虚词或多数词带拉丁词尾。全书 229 条旁注翻转（四卷 104／32／50／43）。
  旁注改动后缺字组原串有 66 组带上／去掉斜体号，判读表 1930 条仍全部对上落盘。

逐条（`tcp_fixes.tsv`）：Prophe→Prophet、God making→Gods making、Jesu→Jesus、Minister/Ministers 互误两处、they fruit→thy fruit、
take it is it is→as it is、Righteousnes→Righteousness、Graviora eras→cras、Well, [but what seed?] It is not every seed（录入本漏 3 词）；
斜体边界：「You will say,」原书正体、问句斜体（本段与 9:6 p.187 两处，全书只此两处这样标）、like a large field…（原书正体）、It is time.（原书斜体）；
terrarñ 后多出的缩写横（缺字判读后 TCP 的 cmbAbbrStroke 留成孤立附加符）。

缺字（`gap_review.tsv`）：希伯来旁注 לפי חסד（p.448）、יורה à ירה（p.478）；meâ、colli、dispairing、Obs.。p.453 希伯来字仍判不了（已有 `?`）。

全书同类查过、不改：
- 重复词（the the、in in、as as…）70 处：证人 OCR 同页也重复的 51 处；其余 19 处裁图看了 7 处，都是原书行末重排时多印一词（find in / in Matth.、must must、as as），原书误植照录。
- 英文旁注 p.467「Subjection is either passive…」原书底子斜体、人名正体，录入本反标；只此一条英文长注，未改。
- 旁注序号（p.477–478 页边的 1. 2. 3. 4.）录入本未录，不补。
- 段末 `▪`（录入者没认出的标点）本段 17 处未判，留着。
