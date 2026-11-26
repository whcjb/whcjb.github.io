# 巴罗夫《何西阿书讲解》抽章实读校勘记录

底本是 EEBO-TCP 人工双录入本（不是 OCR），对照杜克藏本实物扫描（第 2–4 卷同版；第 1 卷证人是 1643 初版、他版，只作旁证）。
随机抽一段（站上一页），逐页对影像读（每叶只读一次，读过的叶与结论记 `read_pages.tsv`，抽样自动跳过、再用到时照账本结论），错处落 `tcp_fixes.tsv`（词句）、`gap_review.tsv`（缺字），整类的在抽取层改判据。

| 轮 | 日期 | 抽中 | 印本页 | 页数 | 本段错处 | 每页 |
|---|---|---|---|---|---|---|
| 1 | 2026-11-26 | 第 3 卷 10:12 | pp. 442–487（456 后原书页码跳到 467） | 36 | 约 30（正文词句 11、斜体 5、缺字 6、旁注正斜整条颠倒 4 条） | ≈ 0.8 |
| 2 | 2026-11-26 | 第 2 卷 7:9–12 | pp. 677–684 | 8 | 2（词句 1、希伯来旁注 1）＋段首首字一类 | ≈ 0.25 |
| 3 | 2026-11-26 | 第 2 卷 5:15 | pp. 510–527 | 18 | 12（词句 3、漏页边标记 1、缺字 8——其中希伯来／希腊旁注 6）＋页边纯序号一类 | ≈ 0.7 |

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

## 第 2 轮（7:9–12）

- 逐条：p.682「as the Doves but」→「as the Dove; but」（tcp_fixes）；p.680 页边希伯来 פותה（gid 2073）。
  该旁注原先只剩〈Greek〉、按约定不出脚注，补字后出脚注。
- 整类（`burroughs_common.dropcaps`）：原书段首花饰首字后余字小型大写（THE word、GOD hath、THEY are），录入本没标 decorInit、
  旧规则只认两字母首词（IN、WE）和 WEe 式，三字母以上的全大写首词漏认；段首先有旁注的（`[^5] THE word`）也漏。规则放宽后全书补认 33 处，逐条看过都在经文框或标题后的段首。
- 查过不改：p.677「one one night」、p.679「Mini-/nisters」原书行末重印；页边序号（1. 2. 3.）录入本不录，照旧。
- 已知未做：全书只剩〈Greek〉的希伯来旁注（站上不出脚注）尚有若干，需逐条看图，未在本轮处理。

## 第 3 轮（5:15）

- 逐条（tcp_fixes）：p.510「I will not, not leave you; there it two」→「not, not, not … there is two」（来 13:5 五重否定，录入本漏一个 not）；
  p.511「desturbs He even and Earth」→「Heaven」；p.515 页边「Obs. 3.」录入本漏。
- 缺字（gap_review）：希腊／希伯来旁注 6 条照影像补（来 13:5 οὐ μή σε ἀνῶ…、יאשמו、ישחרנני שחר、ὀρθρίσουσι、צקון לחש、ζέοντες）；Damned.、consciance（原书拼法）。
- 整类（`extract_burroughs.prep`）：页边只印一个序号（2、3、4…）的，录入本记作空 `<milestone type="tcpmilestone" n="…"/>`，抽取时整类丢掉。
  段内的改排成页边纲目标记，全书恢复 521 处（四卷 145／221／125／0；p.678「2 3 4」、p.522「2」看图核过）。块级的（章节间）不动。
  新标记不计入分页词数（否则 9:2 段跨过阈值多切出 9-4 页、改动网址）；缺字组编号与判读表全部仍对上。
- 查过不改：页边「Answ. 2」「Answ. 3」类——原书多半只印数字（p.522、p.526），单位是录入者补的，但录入本里补的和原书印出的（Obs. 1–5 各条都印）写法完全相同，规则分不开，照录入本。
  原书误植照录：Sainss、Remakable（录入本已正作 Remarkable，不动）、Isa. 16.14（应作 26.14）、how much better it it。
