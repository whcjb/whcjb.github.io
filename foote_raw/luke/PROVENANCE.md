# 福特《路加福音讲义》——底本与处理链

## 著者与著作

James Foote（詹姆斯·福特，A.M.），苏格兰阿伯丁 East Church 牧师，1843 年分裂后
随苏格兰自由教会（Free Church of Scotland）出走，任 Free East Church 牧师。
《路加福音讲义》（*Lectures on the Gospel according to Luke*）共 137 讲，由讲坛
讲章扩写而成，逐段讲完路加福音 1–24 章。初版三卷，爱丁堡 John Johnstone 出版；
第 1 卷序署 1838 年 8 月于阿伯丁。另有 Ogle & Murray 1858 年第 3 版（改为两卷本）。

体例：每讲先列讲题（`LECTURE n.`）与经文出处（`LUKE i. 1-4.`），接着小字排印
整段钦定本经文（悬挂缩进，节号内嵌），然后是讲解正文。页脚有脚注（`*` `†` `‡`
`§` 标号），正文间有小字诗行引文（赞美诗、拉丁诗句）。

## 底本

全部来自 Internet Archive，Google 扫描、牛津大学图书馆藏本，ABBYY FineReader XML 可下载。
HathiTrust / Google Books 未见其他全视图扫描本（2026-11-06 查）。

| IA 条目 | 卷 | 版次 | 讲次 | 扫描页 | djvu 非词率 | 用途 |
|---|---|---|---|---|---|---|
| `lecturesongospe03footgoog` | 1 | 第 2 版 | I–XL | 617 | 2.87% | **主底本** |
| `lecturesongospe02footgoog` | 2 | 第 2 版 | XLI–XC | 697 | 2.30% | **主底本** |
| `lecturesongospe00footgoog` | 3 | 第 2 版 | XCI–CXXXVII | 675 | 2.52% | **主底本** |
| `lecturesongospe01footgoog` | 1（两卷本） | 第 3 版 | I–LXVI | 819 | 3.71% | 第二证人 |

非词率按 `scripts/alexander_lexicon.py` 判词典、`_djvu.txt` 全文 ≥2 字母 token 计。

- 主底本统一用第 2 版：三卷齐全，版次一致。
- 第 3 版卷一覆盖 Lect. I–LXVI（第 2 版卷一全部 + 卷二前 26 讲），是这一段唯一的
  第二证人；**第 2 版卷二后 24 讲与卷三全卷只有一份扫描**，判读只能靠页面影像。
- 第 3 版与第 2 版之间可能有作者修订，第二证人判读时要按 skill §1 第 ② 层的
  「两版之间的改写会被误当误读」防备。
- **网上没有人工录入本**：BibleHub 有约 65 段（每段 300–400 词）摘录，属《圣经图解》
  一类汇编的节录，且与 A. L. R. Foote 混在同一作者页；Logos 有商业录入本（DRM，不可用）。
- 第 1 卷第 2 版序署 1838 年，书前有题献与序。

## 本地文件（不入库，按上表 id 可重下）

```
foote_raw/luke/src/<id>_abbyy.gz          ABBYY XML（主输入）
foote_raw/luke/src/<id>_djvu.txt          ABBYY 纯文本（仅作量非词率用）
foote_raw/luke/src/<id>_page_numbers.json IA 页码表（leaf → 印刷页码，书前若干页缺）
foote_raw/luke/pdf/vol{1,2,3}_ed{2,3}_<id>.pdf   页面影像（第 ③ 层）
```

## 处理链

```
python3 scripts/extract_foote.py          # ABBYY → work/lectures.json + work/md/NNN.md
```

### 抽取（`scripts/extract_foote.py`）版面判据，2026-11-06 实测

| 元素 | 判据 |
|---|---|
| 正文 | fs 9（三卷众数），段首 startIndent ≈ 78 |
| 讲题 | 单行、`L..T...` + 罗马数字，fs 10–12；少数排 9 号（Lect. I、XXII）时看后两行结构（单行经文出处 + 悬挂缩进经文段） |
| 经文出处 | 讲题后紧跟的短单行 |
| 经文段 | fs 8、悬挂缩进（startIndent < 0），讲题后到正文前 |
| 页眉 | 页首单行，`页码 LECTURE n.` / `LUKE i. 1-4. 页码`；读花的形另有宽松式 |
| 脚注 | 本页最后一个正文字号多行段之后的小字段 |
| 书帖签名 | `VOL. II. K`，剔除 |
| 卷末 | `END OF VOL` 起截断（其后为出版社书目广告） |

讲题 OCR 变体（全部要认）：`LECTUEE` `LECTUSE` `LECTXJEE` `LEOTUEE` `LteCTURE`
`LECTUHEXCIL`（粘连）、罗马数字 C→O（`OXIII`）、尾 I→L（`XIIL` `XVUL`）、小写 `cm`。
讲次按顺序号定，读出的罗马数字只作核对。页码掉到另一行的页眉会剩下孤立的
`LECTURE XIII.`，形状与讲题全同，靠字号（9 vs 10–12）分开。讲题偶尔与经文出处
被 ABBYY 归成同一段（vol2 leaf 245），按行拆开。

### 抽取验收（2026-11-06）

| 项 | 数 |
|---|---|
| 讲数 | 40 + 50 + 47 = **137**，与原书一致 |
| 正文段 | 3386 |
| 脚注 | 446 |
| 「上段无句末标点 + 下段小写起头」 | 155 → **9**（剩余与脚注／诗行相邻，待处理） |
| 漏网页眉 | 6（读花形，待 repair） |
| 经文出处为空 | 5 讲（82、83、88、113、117：讲题后先排小标题，待查） |

### 第 ① 层（`python3 scripts/repair_alexander_ocr.py foote`，2026-11-06）

`en_chapters/` 由 `work/md/` 复制而来，repair 原地改写。全书试跑 824 种改法逐条看过：

- 放行：`h→b`（heen/hecause）、`li→h`（tlie/liave）、`im→un`（imto/imder）、
  `fi/fl→ff`（difierent/oflf）、`u→ll`（wiu/stiu）、`w→iv/to/vn`（ivith/toas/vnth）等成套连字误读。
- 原样保留（`FOOTE_KEEP`）：人名 Heli／Noe／Jair（规则会改成 heb／woe／fair），
  短罗马数字 ii/iv/ix（章号），以及 au/cau/fau/iu/ui/ths/tus 等 n・ll・iii 读法判不了的短词。
- 手工改（`FOOTE_MANUAL`）：dauy→daily、mauy→many、settung→setting、tliej→they、shajt→shalt
  （规则原会改成 dally／mally／settling／thief／shaft）。
- 词尾 `*` 是脚注标号（1097 个），换成哨兵 `\ue010`，不进规则；`Christ*s` → `Christ's`；
  词首 `*` 多为开引号读错，跳过留给后层。
- 一次调用迭代到不动点（`iterate`，`*cliap` 次轮才露出 `cliap`）。

| 验收 | 结果 |
|---|---|
| 原串全真词、改后出现非词 | 0 |
| 对 repair 输出再跑 repair | 零变化 |
| 非词率（≥2 字母 token） | 1.56% → **1.42%**（81.7 万词） |

剩余非词大头：希腊／拉丁引文、脚注出处缩写、两字母碎片（tooshort），留给第 ②③ 层。

### 第 ① 层第二轮（2026-11-06，按 skill 补过）

抽样正文待判前 80 高频，发现本扫描件特有的成套误读第一轮没收：`v→y`（haye/heayen/giye）、
`y→j`（thej/jou/maj）、`h→b`（tbe）、`ch→di`（whidi）、词首 `G` 读成 Gr/O/Q、`f` 读成 i。
作为本书附加规则挂上（`FOOTE_RULES` / `FOOTE_HEAD`，其他书不受影响）；钦定本路加全部词形并入判词典
（`foote_kjv_words`，人名地名不再被当残字）。1030 种改法逐条看过，另挡 17 种（逗号读成 y/j 的
`noty`/`andj`/`lordj`、断词碎片、候选不唯一）＋手工 2 条（gloiy→glory、heliering→believing）。

### 第 ② 层（`scripts/adjudicate_foote_ocr.py`，Lect. 1–66）

证人＝第 3 版卷一 ABBYY。照诗篇 look_up（前后六词窗口滑动三词锚＋另一侧确认）读出证人同位读数，
过闸才落。1058 种改法逐条看过后定的闸：

| 闸 | 挡什么 |
|---|---|
| 判词闸 | 读数必须是真词（不开「证人出现 ≥3 次」后门：第 3 版 OCR 也有 imderstood/oflf/IsraeV 成套错） |
| 证人读崩 | 从证人读数按字形规则走得到我们的串（Satuminus→Saturninus） |
| 一头丢字／截断／拆词 | ofAbia→Abia、Sth→th、Gosp→Gospel（下一 token 是 el 时会叠字） |
| 尾字噪点 | 去尾 ≥6 字母已成词、证人另读（generationl→feneration） |
| 字形闸 | 编辑距离占比 ≤1/3 或字形可达；另放行等长两处替换（coidd→could，69 条看过，8 条留看图） |
| 词尾 y/j | 是逗号读错：Christy → `Christ,` |
| 词尾 t/f | 是脚注标号 † 读错：Jesusf → `Jesus`＋脚注哨兵 |

判读 1086 改（规则表 `witness_fixes.tsv`，每讲从后往前落、幂等）、371 两版一致、386 无证人、
其余被闸挡下。逐词回退判据 0。

### 分账（`python3 scripts/foote_ledger.py`）

| | 第①层后 | 第①层二轮 | 第②层后 |
|---|---|---|---|
| 已核实原样 | 0 | 0 | 376 |
| 外文与活字残渣 | 828 | 824 | 813 |
| 两字母碎片 | 1521 | 1520 | 1522 |
| 脚注区 | 1723 | 1718 | 1595 |
| **正文待判** | 11649 | 10444 | **9183** |

### 第二条非生成式字流：tesseract 重扫（`scripts/foote_tesseract.py`）

PDF 内嵌原图（约 500 dpi，不上采样）→ medianBlur(3) → tesseract 5.5 `eng --psm 4`，三卷 1989 页，
产物 `tess/v{1,2,3}/{leaf}.txt`（leaf 与 ABBYY 页序一致）。同一份扫描、换一个引擎（skill §3.2c），
**只当证人**，字不直接进产物。用途：Lect. 67–137 的第 ② 层判读（没有第二份印本）、全书游离符号取证。

### 第 ② 层第二轮：tesseract 证人（全书 137 讲）

同一套闸；改法 1166 种按风险筛出逐条看，另挡 43 种（`TESS_HOLD`：改成别的真词 hready→bread、
oftn→oven、fowlsf→fouls、zxiv→XXII、Grsece→Grace；碎片；证人也崩；候选不唯一）。2092 改、1780 两流一致。
两张证人表按序落（ed3 → tess），锚换算用两表合并的修正映射，再跑零变化。

### 结构清理（skill §3.1 / §3.2a / §3.2b / §4.4）

- 页眉：页码前夹噪点（`J 14 LECTURE VIII.`、`1 ] 8 LECTURE XCIX.`）与讲题读花（`LEC5TURE`、`LECrrURE`）另立判据；
  主页眉判据不开 re.I——脚注出处 `‡ Luke ii. 40, 52.` 与 recto 页眉同形，曾被误删一条，已回。
- 跨页续段：26 → 3（剩：拉丁诗行本就分行、`:—` 收尾、1 处待看图）。无字母碎段（页顶一颗 `*`）不删，挂到下一段开头。
- 游离符号（`scripts/foote_symbols.py`，白名单外字符＋转义星号逐个取证）：tesseract 同位给出正常标点才换、
  同位无墨才删；只准动标点空白（字母数字不变）、斜体标记（未转义 `*`）一个不许少（实测曾删掉斜体收尾致页面露星号）。
  引号统一归直引号（tesseract 引号方向不可靠）。落 1864 条，定位不唯一 2 条不落。白名单外字符 8441 → 约 6000（定位不到的 4356 处留待看图）。
- 词内斜体 `suf*fered*` 3 处去标记。

### 渲染验收（2026-11-06）

| 项 | 结果 |
|---|---|
| 误生表格 / 正文 `<ol>` | 0 / 0 |
| 经节锚点 | 1151（＝全书节数），重复 0 |
| 强调对数 vs 渲染 `<em>` | 4307 / 4304（差额在原书自带奇数星号的 14 段） |
| 页面字面星号 | 898 → 588（多为 `\*` 转义的 OCR 星号，定位不到证人） |
| 整链重跑（extract → … → symbols） | 逐字节一致 |

### 分账（第②层两轮＋结构清理后）

| | 第②层 ed3 后 | 现在 |
|---|---|---|
| 已核实原样 | 376 | 370 |
| 外文与活字残渣 | 813 | 741 |
| 两字母碎片 | 1522 | 1524 |
| 脚注区 | 1595 | 1497 |
| **正文待判** | 9183 | **7275** |

## 待做

1. ~~第 ① 层~~ ~~第 ② 层（ed3＋tess）~~ ~~结构清理~~ 已完成
2. 第 ② 层：Lect. I–LXVI 用第 3 版作第二证人按位置判读
3. 经文段：钦定本同位词校正（参照 `extract_alexander_acts.py` 的 `header_fix`）
4. ~~发布~~ 2026-11-06 英文版上线（只过第 ① 层，书首页注明为校勘中的工作本）：
   `python3 scripts/publish_foote_en.py --apply` → `foote/luke/lecture-1…137` + 章目录 `1…24`；
   版式 `_layouts/foote-{book,chapter}.html`（覃红 #d14457）；历代解经登记见 build_commentaries_index.py。
   各讲经文范围写死在 `VERSES`（印本出处 OCR 读花，按连续性定、四讲以经文段末节号核过）。
   渲染验收：误生表格 0、正文 `<ol>` 0、经节锚点 1151＝路加全书节数、重复 id 0。
