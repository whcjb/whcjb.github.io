# AGES 数字图书馆资源调研

> 调研日期：2026-09-29
> 问题：AGES 里除了加尔文的注释书，还有哪些书？
> 镜像：`https://media.sabda.org/`（印尼 SABDA 基金会放的 AGES 光盘镜像）
> 一手依据：`alkitab-10/AGES.PDF`（AGES 官方目录「Touch and Go Librarian」，MCL v5，18 页）＋ 逐层抓取的目录列表
> 存档：官方目录原件与原始目录树见 `scripts/` 之外的临时目录（本文已把其中内容整理进来）

---

## 一、结论

AGES（AGES Software，Master Christian Library）总共 400+ 种书，加尔文注释只是其中很小一块，而且**加尔文注释单独占一张盘**（The Comprehensive John Calvin Collection，355MB）——我们 `论文/calvin/` 里那 54 个 `CAL_*.pdf` 就出自这张，所以主盘的注释目录里只剩律法合参和希伯来书。

除加尔文外，AGES 里对本站真正有用的是三类：

1. **注释**：亚当·克拉克全本（8 册）、马太亨利简明、贺智四卷、**哈尔登罗马书**、达秘略解、文森特字义研究、JFB 四卷、司布真马太福音。
2. **改革宗神学与清教徒**：欧文 9 种 + 全集 6 卷、爱德华兹 5 种、本仁约翰 11 种、巴克斯特、弗拉维尔、伯罗斯、谢德、贺智《圣灵论》、平克、早期教会信条集。
3. **历史与工具**：**威斯敏斯特会议史**、艾德善圣经史 7 卷、教父全集（ANF 10 + NPNF 28）、吉本、约瑟夫、易斯顿辞典、Strong 词典。

推荐开工顺序：**哈尔登《罗马书释义》→ 贺智《以弗所书注释》→ 威斯敏斯特会议史 → 欧文那 9 种**。全部是 AGES 双语版式，和已跑通的 `hodge_romans_ages` 同一条流水线，基本零改造。

---

## 二、镜像结构：四张盘

| 路径 | 是什么 | 规模 |
|---|---|---|
| `alkitab-10/` | **MCL 主盘**，`LIBRARY/` 下 14 个分类 | 650MB |
| `alkitab-11/` | MCL v6，可列目录的只有 `LIBRARY3/`（114 个 PDF） | — |
| `alkitab-8/` | **宗教改革史图书馆 v2**（110 个 PDF） | 420MB |
| `alkitab-9/` | **司布真专盘**（Pilgrim Publications） | 350MB |
| （无镜像） | The Comprehensive John Calvin Collection | 355MB |

主盘分类：`BIBLES / BIBLSTDY / COLLECT / COMMENT / FATHERS / FICTION / HISTORY / INSPIRAT / LANGBIBL / MAPS / MINSHELP / QUO_ILLU / REFERENC / THEOLOGY`。

---

## 三、注释类 `alkitab-10/LIBRARY/COMMENT/`

| 文件码 | 作者 | 书名 | 本站状态 |
|---|---|---|---|
| `CAL_HAR1-3` | 加尔文 | 福音书合参 1–3 | 已做 |
| `CAL_HEBR` | 加尔文 | 希伯来书注释 | 已做 |
| `CLARKE_C/C1_GE_DE`…`C6BTH_RE` | 亚当·克拉克 | 全本圣经注释 8 册 | 未做 |
| `HEN_CMCN` | 马太亨利 | 简明全本注释 | 本站 mhenry 走的是全本，非简明本 |
| `HOD_ROMA` | 贺智 | 罗马书注释 | 英文版已上线 |
| `HOD_1COR` / `HOD_2COR` | 贺智 | 哥林多前／后书注释 | 本地已有 PDF，未做 |
| `HOD_EPHE` | 贺智 | **以弗所书注释** | 未做 ← 候选 |
| `HAL_ROMA` | 哈尔登（Robert Haldane） | **罗马书释义** | 未做 ← 首选 |
| `DAR_SYNT` / `DAR_SYOT` | 达秘 | 圣经略解 新约／旧约 | 未做 |
| `VIN_NT12` / `VIN_NT34` | 文森特 | 新约字义研究 1–4 卷 | 未做 |
| `SPU_MATT` | 司布真 | 马太福音注释 | 未做 |
| `BET_NTCO` | Joseph Agar Beet | 罗马书—腓利门注释 | 未做 |
| `WAT_LDPR` | 汤姆·沃森 | 主祷文 | 未做 |
| `DEN_DECH` | 邓尼（James Denney） | 基督之死 | 未做 |
| `DEI_NTLM` | 戴斯曼 | 新约与现代研究之光 | 导论性质，非注释 |
| `RAM_LT7C` | 兰赛 | 给七教会的信 | 带图版与小亚细亚地图 |
| `CAR_JONA` | B. Carradine | 约拿书 | 圣洁派 |
| `NAV_TOBI` | Nave | 简明主题圣经 | 工具书 |

另在 `alkitab-11/LIBRARY3/`：**JFB 注释四卷**（`JFB_OTV1-2`、`JFB_NTV1-2`）、克拉克全本另一套编号（`CLA_VOL1-8`）。
卫斯理《新旧约释义》在 `COLLECT/WESLEY_C/`（`WES_NTNO` / `WES_OTNO`）。

---

## 四、神学类 `THEOLOGY/`

| 文件码 | 作者 | 书名 |
|---|---|---|
| `AQU_INTR`＋`AQU_VOL1-6` | 阿奎那 | 神学大全（导论＋六卷） |
| `ARM_VOL1-3` | 阿民念 | 文集三卷（文件实际放在 `HISTORY/`） |
| `AUG_ENCH` | 奥古斯丁 | 信望爱手册 |
| `BAX_TSER` | 巴克斯特 | 圣徒永恒的安息 |
| `CAL_INST` | 加尔文 | 基督教要义（四卷合一） |
| `CAL_CHLF` / `CAL_PRAY` | 加尔文 | 基督徒的生活／论祷告 |
| `CHE_ORTH` / `CHE_HRTC` | 切斯特顿 | 正统／异端 |
| `DEN_DECH` | 邓尼 | 基督之死 |
| `FLA_MDGR` | 弗拉维尔 | 恩典之法 |
| `HOD_HOSP` | 贺智 | **圣灵论** |
| `LUT_95TH` `LUT_CATE` `LUT_SCAT` `LUT_SMAR` | 路德 | 95 条论纲／大要理／小要理／施马加登信条 |
| `MEL_AUCO` | 墨兰顿 | 奥格斯堡信条 |
| `PIN_INBI` `PIN_GOHE` `PIN_LASA` | 平克 | 圣经的默示／神之为神／律法与圣徒 |
| `SHD_ETPN` | 谢德 | 永刑的教义 |
| `SPU_PUCA` | 司布真 | 清教徒要理问答 |
| `ANO_THGR` | 佚名 | 德意志神学 |
| `VAR_CRDS` | — | **早期教会信条集** |
| `CLA_CLBB` | 亚当·克拉克 | Clavis Biblica（在 `REFERENC/`） |
| `WHI_HWST` | 安德鲁·怀特 | 科学与神学交战史（在 `REFERENC/`） |

---

## 五、历史 `HISTORY/`

- `HET_WSTM` — **《威斯敏斯特会议史》**（Hetherington）← 候选
- `EDE_HIS1-7` — 艾德善《圣经史》七卷（从洪水前世界到被掳）
- `GIB_VOL1-6` — 吉本《罗马帝国衰亡史》六卷
- `BNG_VOL1-4` — Nathan Bangs《美以美会史》（**不是 Bengel**）
- `I_P_TRCH` — Innes & Powell《基督的受审》
- `APOCRYP2` — 次经
- `JOSEPHUS/` — 约瑟夫著作（子目录，未展开）

## 六、参考 `REFERENC/`

`EAS_DICT` 易斯顿圣经辞典 · `STR_GREK` Strong 希腊文词典 · `TOR_TNTT` 托雷主题汇编 · `HIT_DSPN` Hitchcock 圣经专名释义辞典 · `WTZ_CHRN` 圣经基督教年表 · `EDE_TMPL` 艾德善《圣殿》 · `EDE_SJSL` 艾德善《犹太社会生活素描》 · `SON_MAPS` SON Light 地图 · `RAM_WCBB` 兰赛《生于伯利恒？》 · `CAR_BICR` / `CAR_GIDE` Carradine

## 七、事工 `MINSHELP/`

`BAX_REPA` **巴克斯特《改革宗牧师》** · `COK_DUMI` Coke《传道人的职责》 · `DAR_MINR` 达秘《论事奉》

## 八、灵修 `INSPIRAT/`

`BUR_RJCC` **伯罗斯《稀世珍宝：基督徒的知足》** · `FLA_FNLF` 弗拉维尔《生命的泉源》讲道集 · `BOU_PRPR` / `BOU_NEPR` 邦兹《传道人与祷告》《祷告的必要》 · `CLV_ONLG` 伯尔纳《论爱神》 · `KEM_IMIC` 金碧士《效法基督》 · `BLA_PTPG` 劳伦斯弟兄《与神同在》 · `HLT_SCAL` 希尔顿《完全的阶梯》 · `DON_DEVO` 约翰·邓恩《沉思录》 · `SMI_CSHL` 汉娜·史密斯《基督徒得胜生活的秘诀》 · `TAY_AROB` 戴德生《一条蓝丝带》 · `FOX_MRTR` 福克斯《殉道史》 · `WHI_SERM` 怀特菲尔德讲道集 · `BRE_SOWS` Brengle · `ALP_UNIF` 利古里 · `JOW_CALV` Jowett《与他一同受苦》（文件码与书名对不上，存疑）

---

## 九、作者专集 `COLLECT/`

| 目录 | 数量 | 内容 |
|---|---|---|
| `OWEN_C` | 9 | **基督论**、神选民信仰的凭据、因信称义的教义、两要理问答、三位一体与基督的位格及补赎、为《三位一体》某些段落辩护、敬拜导论、**与神相交**、为《相交》某些段落辩护 |
| `EDWARDS` | 5 | 讲道集（含《落在忿怒之神手中的罪人》等）、宗教情操真伪辨、论经历的判别、神奇妙作为的叙事、立志文 |
| `BUNYAN` | 11 | 论敌基督、基督徒的品行、义人的心愿、合一与和睦的劝勉、圣洁生活、灵魂的伟大、归与的义、窄门、敬畏神、耶路撒冷的罪人得救、因恩得救 |
| `FINNEY` | 8 | 讲道集、系统神学、复兴讲座、向挂名信徒讲道等 |
| `LAW_C` | 10 | 威廉·劳《严肃的呼召》等 |
| `MOODY` | 7 | 慕迪 |
| `ANDERSON` | 7 | 罗伯特·安德森《将临的君王》《神的沉默》《希伯来书中的预表》等 |
| `WESLEY_C` | 17 | 《全集》14 卷 ＋ 新旧约释义 ＋《基督徒的完全》 |
| `LUTHER` | 3 | 善功论、罗马书序、桌边谈（更多在 `alkitab-8`） |
| `SPURGEON` | 9 | 讲道选 4 卷、《按着应许》《全然出于恩典》《信心的支票簿》《朝朝暮暮》《清教徒要理问答》《直等到他来》 |
| `BIOGRAPH` | 12 | 本仁、克拉克、芬尼、弗拉维尔、福克斯、慕迪、欧文、司布真、卫斯理传记；墨兰顿《路德传》 |
| `HOLINESS` | 26＋`CARRADIN/` | 圣洁派；含 `GDB_VOL1-7` Godbey 新约注释七卷 |

## 十、教父 `FATHERS/`

三个子目录，即全套 **ANF 10 卷 ＋ NPNF 第一辑 14 卷（奥古斯丁 8 + 屈梭多模 6）＋ 第二辑 14 卷**。
文件码规律：`ECF_0_NN`＝ANF，`ECF_1_NN`＝NPNF 一辑，`ECF_2_NN`＝NPNF 二辑。

## 十一、其余

- `BIBLES/` — KJV、ASV、达秘译本、Young 直译、Weymouth 新约（各分新旧约）
- `LANGBIBL/` — 西班牙文 Reina-Valera 1909、耶柔米武加大译本
- `BIBLSTDY/` — `DER_DNOT` Derickson 神学笔记、`BIB_ST15` 查经课程 1–5
- `QUO_ILLU/` — 讲道例证与引语集、伊索寓言
- `FICTION/` — 本仁《天路历程》《圣战》、麦克唐纳
- `MAPS/` — 经典圣经地图（唯一没列完的一类）

## 十二、另外两张盘

**`alkitab-8` 宗教改革史 v2**（110 个 PDF）：路德《全集》6 卷、讲道 8 卷、《加拉太书注释》、《登山宝训》、书信集、95 条；梅尔·多比涅《宗教改革史》8 卷；诺克斯（`KNX_*`）；丁道尔（`TYN_DRTR`）；拉提默（`LAT_SRRE`）；Hefele 会议史 5 卷；ANF 前 10 卷；约瑟夫；Strong 的 7 卷本。

**`alkitab-9` 司布真专盘**：Pilgrim Publications 的司布真讲道全集，首页是 `HOMEPAGE.HTM`。

---

## 十三、抓取经验（下次要用得上）

1. **服务器极慢且不稳**：列大目录常 90s 超时，下载速度低到 ~160 B/s。`--http1.1` 比默认 HTTP/2 稳；配 `-C -` 续传 + 多次重试才能把大文件拉全。并发超过 2–3 反而全体饿死。
2. **目录列表时有时无**：`alkitab-8/LIBRARY/` 之类大目录要重试十几次才回一次完整 HTML；`alkitab-9/LIBRARY/`、`alkitab-11/LIBRARY/` 始终列不出。
3. **不下整本也能认书名**：`curl -r -3000` 取 PDF 尾部 3KB，里面有 `/Title` `/Author` `/Subject` 的 Info 字典。头部 `-r 0-6000` 只能拿到书签（章节名），认不出书名。
4. **最省事的路子是先抓官方目录**：`alkitab-10/AGES.PDF`（约 400KB）就是全库带书名的索引，18 页，`pdfplumber` 直接出文本。早抓它可以省掉大半探测。
5. AGES 文件码是「三字母作者 + 四字母书名缩写」，但有例外（`WHI_HWST` 是 White 不是 Whiston，`BNG` 是 Bangs 不是 Bengel），**不要凭码猜书名**，以官方目录为准。

---

## 补充（2026-11-18）

- **完整逐本书目**另见 `docs/SABDA_AGES_书目.md`：alkitab-7 至 11 共 1,135 个 PDF，按文件名去重 772 本，按作者排列，附下载路径。
- **更正**：上文「二、镜像结构」说加尔文专盘（The Comprehensive John Calvin Collection）无镜像——其实有：**`alkitab-7/` 就是加尔文专盘**，`alkitab-7/LIBRARY/CALVIN/` 下 96 个 PDF（`CAL_*` 注释等），另有 `alkitab-7/CALVIN.PDF`、`alkitab-7/MOVIE/MOVIE.PDF`（The Life of John Calvin）。
- 司布真《大卫的宝库》（Treasury of David）不在任何一张盘里；`alkitab-9/LIBRARY/SPU_S&T1–7` 是月刊《剑与镘》（The Sword and the Trowel）合集，不是它。


---

## 补充（2026-11-24）：格林希尔《以西结书释义》——AGES 没有，EEBO-TCP 有全本人工录入

**AGES 查无此书。** 把 `media.sabda.org/alkitab-1` 至 `alkitab-13` 递归爬了一遍（共 4,448 个文件），没有 `GRE_*` 文件码，也没有任何 Greenhill 的书；以西结书注释只有加尔文的 `alkitab-7/LIBRARY/CALVIN/CAL_EZEK.PDF`。

顺带把之前没调研过的几张盘看了一下，**都和本站无关**：

| 盘 | 内容 |
|---|---|
| `alkitab-1` | 神学教育信息化讲义（Blackboard 教程、网课论文、链接页） |
| `alkitab-2` | 释经学／宗教学 PDF 129 本 ＋ Religion-Online.org 书 193 本（多为现代自由派） |
| `alkitab-3`、`alkitab-4` | 海波斯、马克斯韦尔等领导力讲座（wma／rm 音频 ＋ 讲义） |
| `alkitab-5` | 列不出目录 |
| `alkitab-6` | 另一套光盘软件（Online Bible 等），`wh2-ref` 里有克拉克注释的 PDF |
| `alkitab-12` | 只有 `ccel/` 的几个索引页，没有正文 |
| `alkitab-13` | 有声圣经 mp3（以斯帖记—启示录） |

**人工录入本在 EEBO-TCP**：五卷 1645–1662 年初版全部做了双人录入，**CC0 公有领域**，GitHub `textcreationpartnership/<ID>` 可以直接取 XML，已经存到 `greenhill_raw/ezekiel/src/`：

| TCP 编号 | 章 | 初版 | Wing | 词数 | illegible 缺口 | foreign 缺口 |
|---|---|---|---|---|---|---|
| `A85666` | 1–5 | 1645 | G1851 | 21.3 万 | 205 | 204 |
| `A85667` | 6–13 | 1649 | — | 22.2 万 | 636 | 349 |
| `A42015` | 14–19 | 1651 | G1855 | 24.0 万 | 266 | 612 |
| `A85668` | 20–29 | 1658 | — | 22.8 万 | 367 | 389 |
| `A42016` | 30–48 | 1662 | — | 26.5 万 | 425 | 179 |

合计约 117 万词，48 章齐全。

说明：
- `<gap reason="foreign">` 是 TCP 不录的**希腊文和希伯来文**，要用页面影像或 1864 年 Nichol 版补。
- `<gap reason="illegible">` 是底片看不清的字，**绝大多数只缺 1–2 个字母**，约每 600 词一处，可以从上下文或 Nichol 版补回。
- 正文里另有 `•`／`〈◊〉` 缺字符号约 2,100 处，也算在要补的范围里。
- 拼写是 17 世纪原貌（长 s `ſ`、u/v 互用等），发布前要规范化。
- 各卷 `<div type>` 不统一：`part`／`textual_commentary`／`observations`／`exposition` 混用，切章节时要按卷分别处理。
- 现代排印本：1839 年 Holdsworth 版、1864 年 Nichol 版（James Sherman 编），HathiTrust 上只有页面影像，没有人工录入本；Banner of Truth 1994 年重印本有版权。

## 补充（2026-11-26）：巴罗夫《何西阿书讲解》——AGES 没有，EEBO-TCP 有四卷人工录入

AGES 主盘只收了巴罗夫的《知足的珍贵》（`BUR_RJCC`，见上文第七节），没有何西阿书。人工录入本在 EEBO-TCP，四卷（第 1–13 章）全有，CC0，
已存 `burroughs_raw/hosea/src/`：A30572（1–3 章，1652 第二版）、A77979（4–7 章，1650）、A30574（8–10 章，1650）、A30575（11–13 章，1651）。
巴罗夫讲到 13:11 去世，13:12 以后不在这四卷里。中文译本未见（2026-11-26 网上查过）。
