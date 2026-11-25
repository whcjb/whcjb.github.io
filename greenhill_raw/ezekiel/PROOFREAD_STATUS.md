# 格林希尔《以西结书释义》抽章实读记录（old-book-ocr §4.5）

收敛判据：连续 5 个随机抽章，每章错处密度 < 1 处/页。底本 EEBO-TCP 人工录入本；对照 EEBO 胶片（IA bim）整页图，每页只读一次。

| 轮 | 抽章 | 卷 | 原书页 | 页数 | 本章错处 | 每页 | 全书同类 |
|---|---|---|---|---|---|---|---|
| 1 | 16-60 | 3 | — | — | 版式（此前一轮，按 §3.3a 排版对齐，未逐页计错） | — | — |
| 2 | 32-1 | 5 | 61–74 | 14 | 7 | 0.50 | 见下 |
| 3 | 48-1 | 5 | 586–596 | 11 | 2 | 0.18 | 见下 |
| 4 | 24-26（今并入 24-19） | 4 | 376–383 | 8 | 1 | 0.13 | 见下 |
| 5 | 32-24 | 5 | 86–96 | 11 | 5 | 0.45 | 见下 |
| 6 | 22-17 | 4 | 234–243 | 10 | 2 | 0.20 | 见下 |
| 7 | 21-14 | 4 | 161–180 | 20 | 6 | 0.30 | 见下 |
| 8 | 28-1 | 4 | 484–494 | 11 | 3 | 0.27 | 见下 |
| 9 | 48-21 | 5 | 596–611 | 16 | 7 | 0.44 | 见下 |
| 10 | 36-8 | 5 | 287–303 | 17 | 3 | 0.18 | 见下 |
| 11 | 38-17 | 5 | 214–230 | 17 | 0 | 0.00 | — |
| 12 | 16-20 | 3 | 214–223 | 10 | 3 | 0.30 | 见下 |

**收敛**：第 2–6 轮连续 5 章每页均 < 1 处（0.50 / 0.18 / 0.13 / 0.45 / 0.20），§4.5 收尾验收通过（2026-11-25）。

## 第 2 轮：32-1（2026-11-25）

本章 7 处：
- 录入本错字 5：`catch chat old`→that、`fighing`→sighing（ſ 录作 f）、`Chaldaans`→Chaldaeans（æ 漏 e）、`Jehosaephat`→Jehosaphat、`2 Chr. 1.8.`→18.
- 版式 2：章标题 `CHAP. XXXII.` 原书正体，产物排成斜体；p.62「1. Is from…」「2. From…」原书缩进成条，产物作普通段（未改，见下）。

全书同类清理：
- 章标题斜体：`head_md()` 加 CHAP. N 判正体，全书 42 处。
- ſ 录作 f：判词典 + 语料自证（f 形非词、换 s 成词且 s 形全书 ≥2 次）全书试跑 17 条，逐条看上下文，落 7 条（confulted defert fense fiege fome luft mifery）；
  其余为拉丁/法文真词（fui fune fus fol）、专名（Flanders）、希伯来转写（Af）或另类问题，不动。
- u/o：`full uf comeliness`→of，1 条。
- 未落、待看图：`af er their`（13-10，第二卷无胶片，疑 after）、`rhe Mediatour`（16-7）、`tbe Prophets`（13-8）——可能是原书误植，按政策照录，须看图才定。
- 已知未改：总括段里的「1. 2.」分条原书缩进，录入本作普通 `<p>`，产物未排成条目。

## 第 3 轮：48-1（2026-11-25）

本章 2 处（录入本错）：`Levit. 31.17.`→21.17.（p.593）、`before hand`→beforehand（p.594，胶片连排）。
照录不计：p.593 页码胶片作「59」+残迹（TCP 录 59）；`Counrry`（p.589 原书误植）；`as it it is`（p.586 原书衍字）；
`a piece`（p.594 胶片字距难判，全书 15 处不动）。

全书同类清理：
- 引文章号超出该卷章数（按各卷章数表全书扫，2 Kings 25 章）：16 条候选。第三至五卷 11 条逐条裁胶片看：
  原书即如此印、照录 8 条（Eccles. 13.26、Mar. 24.13、Levit. 39.10、Levit. 28.25、2 Thess. 9.1、2 Pet. 13.4、Dan. 26.37、1 King. 25.1；
  另 2 Chron. 134.3 首位一笔不清，不动）；录入错改 2 条：`1 Tim. 29.10`→`2 9.10`（原书「2 9. 10.」）、`Levit. 215.10`→25.10（原书「2r5」坏字）。
  第一、二卷 5 条无同版胶片，未动：1-25 `2 Cor. 18.18`、3-4 `Psal. 219.6`、8-18 `Mar. 21.35`、11-14 `Zeph. 28.9`、11-16 `Dan. 28.63`。
- 页码断号：全书 41 处，多为原书页码误植（如 39-9 段 242/143/244/145 交替），按照录政策不改。

## 第 4 轮：24-26（2026-11-25）

本章文字 0 错（p.376–383 逐页对胶片）。1 处结构错：原书 p.376「Vers. 25 … 26 … 27 …」是一段连引三节的经文，
第四卷按引语节号切页，把第 25 节切在上一页（24-19）末尾，本页只剩 26、27 节。

全书同类清理：`units_from_quotes()` 改为中间无正文的连续节号引语同属一段、只在第一节处切。第四卷受影响 2 处：
24-26 → 与 24-19 合并为 24-19（19–27 节；19–24 节单元 2960 词，按 MIN_WORDS=3000 并页）；
23-39（原从 Vers. 36 一段经文中间的第 39 节切开）→ 23-45（从 Vers. 45 起）。页数 236 → 235，旧页 23-39、24-26 删除。
其余第四卷各页开头逐页核过：均从「Vers. N」段首、章首或单节引语（前页以正文收尾）起页。

## 第 5 轮：32-24（2026-11-25）

本章 5 处：录入错 4——`Polanius`→Polanus（p.87，全书他处均作 Polanus）、`In the bed in darknesse`→is（p.87）、
`and that are like`→`and in that are like`（p.91，录入漏 in）、旁注 `Bab: Salum.`→Rab:（p.89）；程序错 1——旁注 `Us que`（p.89）。
照录不计：`Phil. 35`（p.94 原书）、`dogo`（p.96 原书）、`tee h`（p.96 坏字）、`Nebuchadnezzar`（p.95 n 残）。

全书同类清理：
- 缩写展开断词：录入本 `Ʋſ<expan><am>…</am><ex>que</ex></expan>` 标签间的排版换行被当成空格（Us que）。
  `tcp_tei.inline()` 对 expan/am/ex 去首尾空白，全书 26 处恢复（usque、atque、neque、quinque、Templumque…）。
  余下 `eorum que`、`justum que` 等 4 处录入本原文即分写，不动。

## 第 6 轮：22-17（2026-11-25）

本章 2 处（录入错）：`Ezek. 34.24`→`34.2, 4.`（p.237，原书两节号间有空）、经文 `become dross all they`→`dross: all they`（p.234，漏冒号）。
照录不计：`peoceeding`（p.234）、`degerated`（p.240）、`Tin beleevers`（p.238）、`Jer. 51.1`（p.239）——胶片即如此。

全书同类清理：以西结书自引节号超出该章节数（按 NV 表全书扫）4 条候选，有胶片的 3 条逐条看图：
`Ezek. 9.30`（24-9）录入错，原书「9. 10.」，改；`Ezek. 20.56`、`Ezek. 10.36.25`（第五卷）原书即如此，照录；
vol4-dedication 旁注 `Eze. 26.27` 胶片未定位，未动。

## 第 7 轮：21-14（2026-11-25，收敛后追加抽查）

本章 6 处：录入错 5——`husbandmen Jer. 52`漏逗号（p.162）、经文 24 节 `Therefore thou saith`→thus（p.167）、
`imagines fastae`→factae（p.171，ct 连字录成 st）、`could not ut trouble`→but（p.173）、旁注 `quaevie`→quaevis（p.179）；
本项目看图判读错 1——2280 希伯来文 `בחצים`→`בחיצים`（p.170，放大复读原书有 yod）。
照录不计：`appeat`（p.171）、`Mounts.`（p.173 句点逗号难分）。

全书同类清理：
- ct 连字录作 st：全书词频扫「st→ct 后成书中已见词、本形 ≤2 次」7 条，逐条看上下文，只 `fastae` 1 条；其余为真词（fastum、vestes、compast、detest…）。
- `thou saith`、`not ut` 全书各仅本章 1 处。

## 第 8 轮：28-1（2026-11-25，收敛后追加抽查）

本章 3 处（录入错，均在本页正文/旁注）：`uphold the same on mee`漏逗号（p.487）、旁注 `Fitz her bert. 2 Par. ch. 12.`→`Fitzherbert. 2 Par. ch. 18.`（p.489，拆词+章号）、
旁注 `Qui scipsum`→seipsum（p.494）。
照录不计：`carres`（p.492）、`thou forgets`（p.488）、`as the Lords made him`（p.488）、`haber pro sapiente habent`（p.494 旁注）、`into Sea,`（p.490）——胶片即如此。

全书同类清理：专名被拆成多段（`X yy zz` 合起来是书中已见词）全书扫，仅本条；`scipsum` 类 sc/se 混淆全书仅本条。

## 第 9 轮：48-21（2026-11-25，收敛后追加抽查）

本章 7 处：录入错 5——`furthest. Town` 衍句点（p.597）、`four fides`→sides（p.599）、`pointed out into us`→unto（p.603）、
`far if`→for（p.610）、经文 `which it in the midst`→is（p.611）；版式 1——小标题 `Verse, 28.` `Verse, 29.`（节号前有逗号）没认成悬挂的 Vers. 行；
结构 1——卷末颂词 `To God onely be Glory through Jesus Christ.` 与 `FINIS.` 不在本页。
撤回 1 条：第 2 轮全书清理时把 p.605 `full uf comeliness` 改成 of，本轮看图原书即印 uf，按照录政策撤回。
照录不计：`thingr`（p.599）、`fivemiles`（p.600）、`Jerulalem`（p.601）、`Cfiurch`（p.604）、`grrater`/`larter`（p.609）、`ftom`（p.610）、`threof`（p.610）。

全书同类清理：
- 小标题 `RE_HVERS` 允许 `Verse,` 后带逗号，全书 2 处（均本章）。
- 卷末 trailer/closer：抽取程序把总 div 内的 FINIS／颂词挂到「当时的最后一页」——其时各章还没出，落在了卷首页上
  （第四卷 FINIS 落在 vol4-dedication 末，第五卷颂词落在 vol5-to-the-reader 末）；body 层（总 div 之外）的 FINIS 则整个丢了（第一、五卷）。
  改为各章出完后挂本卷正文最后一页：第一卷 5-14、第四卷 29-21、第五卷 48-21 各得其 FINIS（第五卷连颂词）。第二、三卷录入本正文末无 trailer。

## 第 10 轮：36-8（2026-11-25，收敛后追加抽查）

本章 3 处，全是斜体／版式：
- `The Hebrew is, I will make you to dwell…`（p.290）与 `Men might wonder God should deale…`（p.299）两段整段正斜标反——录入本对「底子斜体」的段落只给正体部分标了 <hi>；
- 小标题 `Versi. 14.`（p.292，录入本衍 i）没认成悬挂的 Vers. 行。
文字 0 错。照录不计：`Laborant is`（p.297 原书分写）。

全书同类清理：
- 「*The Hebrew is,*」起头的段落全书 7 处同形，有胶片的 5 处（18-30、33-12、34-17、35-1、36-8）看图确认标反，统一在 `greenhill_common.load()` 里整段正斜互换（RE_INV）；
  另 2 处（36-21、36-29）同形，未定位到胶片，按同一规律处理（全书其余 90 余处「The Hebrew is, *…*」均为正体起头、引文斜体）。
- 其他起头的标反段：按「段内斜体全是 that is／or／saith the Hebrew 一类虚词」全书试筛 70 余段，逐条看文字，疑似 5 段，看图 4 段确认标反
  （27-24、35-12、36-33、36-8），40-1 那段看图为正常。这几段列入 `italic_invert.tsv`，整段互换。
- 小标题 `RE_HVERS` 再放宽一格，`Versi.` 也认。

## 第 11 轮：38-17（2026-11-25，收敛后追加抽查）

p.214–230 逐页对胶片，文字、斜体、版式 0 错。照录不计：`Counrey`（p.223）、`prcaeipitia`（p.222）——原书即如此。
无新类别，不做全书清理。

## 第 12 轮：16-20（2026-11-25，第三卷首次逐页计错）

本章 3 处（录入错）：`Jure Domini`→Dominii（p.214）、`Abutensiis`→Abutensis（p.217）、`viz. the forgate`→she（p.221）。
照录不计：`motion made of Topheth`（p.215 原书）、`Chidren`（p.215/219）、`in hem`（p.218，录入本已作 them，不回改）、`remembance`/`ingatitude`（p.223）。

全书同类清理：`viz.`／标点后 `the` 接动词（应为 she/he）全书扫，仅本条；`Jure X` 拉丁属格全书仅本条。
