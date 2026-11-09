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

### 两条字流按片段换（`scripts/foote_spans.py`，skill §3.2d 缩到片段级）

ABBYY 在长段里把一截读废（第 86 讲 p.637、第 128 讲 p.529/542、第 120 讲 p.418），整段非词率只有 5–13%，
按段判（`foote_streams.py`，命中 0）看不见。改按两锚之间的一截比：我们这截 ≥2 非词且占 ≥40%、tesseract 那截全真词、
词数比 0.6–1.6、各 ≤25 词。抽查后加闸：页眉混入（`… LUKE IV`）、我们本来对的词不许被换（It→I）、数字不许丢、
tesseract 给的词须是本书常见或钦定本词（theer）、不许吞词（penrerted 丢了）、字母相似度 ≥0.5、
单字母（脚注 † 读成 f）不收。换 131 截。链条位置：repair → spans → adjudicate → symbols。

游离符号那一步补斜体星号的位置也改过：开标记（前有空白）放空白后、闭标记紧贴前词；证人缝里有空白而新缝没有就补空格
（回退检查抓出 4 处 `himself,*or*` / `And'as` 之类，已归零）。

### 验收（片段换流之后）

| 项 | 结果 |
|---|---|
| 对第①层产物逐词回退 | 改动 5033 处，回退 0 |
| 整链重跑 / 再跑一遍 | 逐字节一致 / 零变化 |
| 渲染：表格 / 锚点 / 强调 | 0 / 1151 / 4307 对出 4303 |
| 正文待判 | 7275 → 6458（分账计入 tess 一致）→ **6312** |

### 第 ④ 层：希腊活字（评估后**不自动落盘**）

`scripts/foote_greek_scan.py` 全书 tesseract `eng+grc` 逐词 TSV（`tess_grc/`，45M，不入库，可重跑）；
`scripts/foote_greek.py` 拿英文词当锚、两锚之间 grc 全希腊且置信度 ≥75 才换。首轮 130 条几乎全错——grc 把英文短词
读成希腊字母（a→ἃ、As→ΑΒ、of→οὗ、is→ἐδ），正是 skill §2.5 的坑；收紧（我们这截须全是非词且含 ≥3 字母乱码、
grc 截 ≥4 个希腊字母）后剩 3 条，其中 `ἀσοσσιλλω` 是乱码、`᾿Αναπηρους` 丢重音。原生分辨率裁图看了两处
（第 115 讲 οἶνος ἀμπελινος、第 78 讲脚注 'Αναπηρους），重音气息看不准，按「不能猜」不落。
结论：grc 读这本书的带重音活字质量差（380 候选 220 低置信）。脚本作定位工具留着（约 91 页、三百来个希腊词已定位），
希腊引文待逐处看图手工转录——属批量看图，须用户同意。`greek_fixes.tsv` 留空，不接链条。

### 第 ③ 层：页面影像

实读第 107 讲 p.226 半页（无证人的后半部）：与产物逐字一致。按残字密度抽最密几页，发现读坏集中在长段一截 →
促成片段换流。其余残字没有逐个看图（memory：缺字判读别批量看图）。

### 分账（终）

| | 第①层后 | 第②层 ed3 后 | 证人两轮＋结构清理 | 片段换流后（终） |
|---|---|---|---|---|
| 已核实原样（两证人同位一致） | 0 | 376 | 1723 | 1722 |
| 外文与活字残渣 | 828 | 813 | 712 | 707 |
| 两字母碎片 | 1521 | 1522 | 1524 | 1504 |
| 脚注区 | 1723 | 1595 | 990 | 990 |
| **正文待判** | 11649 | 9183 | 6458 | **6312** |

正文待判 6312 里含大量判词典不认的真词（史书人名地名、拉丁词）——两证人都没读出同一词的才留在这档。

### 中译前清底本 · 第一批：两证人同读（2026-11-09，`manual_fixes.tsv`）

用户定「先清底本再译」。正文待判 6312 先分档（判词典口径同 `foote_ledger.py`）：

| 档 | 数 | 处理 |
|---|---|---|
| 破折号连写（`soul—they`，两侧都是真词） | 1520 | 统计口径误报，不动 |
| 首字母大写词（多为史书人名地名） | 943 | 待抽查 |
| 证人给出真词、被闸挡下 | 1492 | 本批只做其中「两证人同位读出同一真词」354 处 |
| 证人读崩 | 593 | 看图 |
| 无证人 | 1790 | 看图／字形规则 |

两证人同读的 583 条候选（按 token 计，含重复锚）再过两道闸：改前改后字形相似度 ≥0.6（挡锚撞车——证人把断词后半截对到下一个词上，
`de pendence→and`、`instrue- tion→it`）；token 前后不贴 `^ & \ - 数字` 等噪点（挡 `utt^ly→utterly^ly`）。过闸 168 条**逐条看过**，
再剔 24 条：吞后词（`thoushalt→thou`、`comethand→cometh`、`ofAbia→Abia`）、断词后半截在下一词（`Bethle hem`、`salvar tion`）、
序数丢数字（`llth→th`）、证人读错（诗 73:26 *faileth* 证人读 `fail`）；6 条句中大写改小写（`Jieartr→heart`、`Avith→with`）。
落 **144 条**，接在 `adjudicate_foote_ocr.py --apply` 两证人表之后（`MANUAL`）。

验收：整链 extract→…→symbols 重跑，人工表 144 条全落、定位失败 0；对改前产物逐词比对差异恰为这 144 处、回退 0；
再跑一遍零变化（证人表 033 `serrant` 1 条、符号表 26 条「已落过判不出」改前就有，是锚在 symbols 之后变形，非本批引起）；
渲染：表格 0 / 锚点 1151 / 重复 0 / 正文 `<ol>` 0。分账正文待判 6312 → **6175**。

### 第二批：单证人／两证人不一致／一证人读崩（2026-11-09）

候选＝至少一个证人同位给出真词的全部残字。自动分三类后逐条看：
- **单词替换** 393 条看过：剔 61（证人读错 `imaginings`→`imagining`、`Barjona`→`Bar`、`capecity`→`cape`；章序数丢数字
  `Idth`/`lOth`/`dth`；引注缺卷章号 `JohnTii`/`Mattxu`；拿不准 `natiflo`/`wiudi`），19 条按上下文与经文改读数
  （`farf`→`fan` 太 3:12、`fone`→`gone`、`sariog` 不收）、14 条转拆词、28 条转并词。
- **拆词**（粘连两词，证人只读出其一）118 条看过：剔 15；自动拆法改正 14（`shallJind`→`shall find`、`aUfilled`→`all filled`；
  复合词用连字符 `self-reproach`）；词尾 `i` 是逗号读错的 15 条只去 `i`；钦定本本就连写的 `menpleasers`/`marketplaces` 不拆。
- **并词**（断词两截）29＋28 条，进新表 `manual_spans.tsv`（逐字原串→改作，本讲须恰好一次）。

`manual_fixes.tsv` 增至 550 条、`manual_spans.tsv` 58 条。`adjudicate_foote_ocr.py`：加 `apply_spans`；「已落过」判断改按改作词序列、
锚按人工表与整串表换算后取后三词、撇号当空格——四表在已落盘产物上重跑全认作已落过（原先 033 `serrant` 那条老毛病一并消掉）。
061 `Woe untoyou^ Pharisees` 改走整串连逗号一起改（只拆词会让 symbols 那条锚变成两处、定位不唯一）。

验收：整链重跑逐字节一致；对第一批产物逐词比对 463 块、回退 0；再跑零变化；渲染 表格 0 / 锚点 1151 / 重复 0 / `<ol>` 0。
正文待判 6175 → **5736**。

### 第 ③ 层：整页转录当第三证人（2026-11-09）

用户定「脚本整页转录当证人」。`scripts/foote_transcribe.py` 把残字 ≥3 处的 838 页＋希腊引文页 58 页（页单
`transcribe_pages.json`，共 866，两页在 PDF 之外）的 PDF 内嵌原图（缩到 1300px 宽）各送一次，连版式标记
（`[HEAD]` 页眉、`*斜体*`、`[FN:*]` 注号、`[SIG:]` 书帖、`[?]` 读不出）整页转录，存 `vlm/v{卷}/{leaf}.txt`。
864 页、**$41.95**（`logs/foote_transcribe.tsv`）。转录**只当证人，文字不进产物**。

`scripts/foote_vlm_adjudicate.py`：每页三条字流（我们 / tesseract / 转录）按位置逐词对齐（印刷页号经
`src/*_page_numbers.json` 对到 leaf）。**tesseract 与转录同位读出同一个词、且与我们不同**才成候选：
- `agree3` 我们不是真词（407）；`realword3` 我们是真词、两家一致改成另一个形近真词（826）——判词典看不见的
  真词错字，`he→be` 105、`hut→but` 33、`hy→by` 21、`bom→born` 20、`hare→have` 19、`thai→that`、`haying→having`、
  `hook→book`、`hear→bear`、`feet→fact`、`lore→love`、`Tillage→village`……
- 不收：两家读出同一个非词（`nbt`）、`realword3_far`（字形差太远 105）、只有转录有读法（`vlm_only` 189）、
  转录与我们都是真词而 tesseract 同我们（`keep` 216）——转录读错的就挡在这里。

守卫（候选 1241 → 规则 1164，逐组看过；挡下的记 `logs/foote_vlm.tsv` 的 skip 列）：
- 词前／词后紧粘的残渣算进原串（`«uid`→`and`、`6ase`→`case`、`mean«`→`means`、`U9`→`us`），残渣若是标点／开引号，
  要两家同位都有才保留，否则整条不落（`punct_disagree`/`lead_disagree`）；残渣前还粘着字母的是残片（`frag_left`）；
  残渣连着下一个词的（`God^s`）不落（`junk_join`）。`(`、`[` 当残渣：`(o`→`to`、`[Wanting`→`planting`。
- 多出的词尾是标点读错（`deaths to`→`death, to`、`himP`→`him?`、`tiSy`→`us,`）：两家须同位有同一标点。
- 我们这串比改作长 3 字母以上且只是首尾含它（`Avulhe`→`he` 会丢 And、`thefooliih`→`the`）：不落（`merge_suspect`）。
- 证人那边是 `1st` 的 `st`（前面紧挨数字）：不落（`v_frag`，章序数另案）。
- 证人的弯撇号一律按本书直撇号比（`God’s`≠分歧）；补的引号用直引号；残渣前已有引号就不再补。
- 诗行省音 `Against`→`'gainst`（088，转录与 tesseract 都读出撇号）。
- 锚取整讲前三词；本讲同词同锚有几处时往前加长到唯一（118 `ye shall not he so` 两处只有一处有证人）。

落盘：`vlm_fixes.tsv`（讲次、锚、原串、改作），`adjudicate_foote_ocr.py --apply --vlm` 在 `foote_symbols.py --apply`
**之后**落（锚取自 symbols 之后的文本）。`apply` 支持原串带残渣、锚多于三词；「已落过」换算锚时连本表一起算、
改作后紧跟收引号（`me'`）照认。

验收：1164 条一次落完、再跑全认作已落过；对落盘前逐词比对 1129 块、回退判据命中 0、新出小写非词 1（`by-tmd^by` 原样残）；
整链从 extract 重跑逐字节一致；渲染 表格 0 / 锚点 1151 / 重复 0 / 正文 `<ol>` 0。
正文待判（`foote_ledger.py`，只数非词）5736 → **5439**；真词错字另修 800 余处（判词典本来看不见）。

章节序数（字流把 `1st` 拆成 `st`，按词对不上）另查：转录与 tesseract 同位一致的 9 处走 `manual_spans.tsv`
（`2dd`→`23d`、`dd`→`3d`×3、`lOth`→`10th`、`Idth`→`13th`、`14jth`→`14th`、`d5th`→`35th`、`Ist`→`1st`）。

「已落过」换算锚改为每个锚词「换／不换」两种都试：修正表按词全讲统一换算会误伤锚里本来对的同形词
（021 `as he waz` 被换成 `as be was`）。② 层各表在终态上重跑全认作已落过；symbols 排在 ③ 之前，终态上重跑不作数。

**看图落盘（用户 2026-11-09：「需要有图片证明才能落盘」）**：上面的推断清单逐条裁 PDF 内嵌原图（原生分辨率，不放大）
定位到行读定，14 处全部有图为证，进 `manual_spans.tsv`：097 `shall he accomplished`→`be`、118 第二处 `not he so`→`be`、
002 `dd chapter of the Acts`→**`3d`**（原先按经文推的 2d 是错的——推断不看图会改错）、002 `e2d`→`62d`、019 `L4th`→`14th`、
054 `*BSd* and d4th`→`33d and 34th`、079 `Epictetos … I5th`→`Epictetus … 15th`、080 `I8th`→`18th`、103 `Idth`→`13th`、
107 `I7th`→`17th`、115 `Sd`→`3d`、119 `I7th`→`17th`、133 `5dd`→`53d`、012 `and.5th`→`and 5th`。
前一轮两证人一致的 9 处序数也补看了图，全部相符。

未落、待看：`vlm_only` 189、`keep` 中 tesseract 读残的、守卫挡下 69 条、同锚而无证人的两处
（097 p.92 `Son of man shall he accomplished`、118 p.391 第二处 `ye shall not he so`）、单证人序数 11 处——已看图落盘，见上。

## 待做

1. ~~第 ① 层~~ ~~第 ② 层（ed3＋tess）~~ ~~结构清理~~ ~~片段换流~~ 已完成；第 ④ 层评估后不落（见上）
2. 希腊引文逐处看图转录（约 91 页）——须用户同意
3. 剩余正文待判按「证人有话说／对不上／无证据」细分后，疑难处看图（第 ③ 层整页转录已做，见上；`vlm_only` 待看图）
2. 第 ② 层：Lect. I–LXVI 用第 3 版作第二证人按位置判读
3. 经文段：钦定本同位词校正（参照 `extract_alexander_acts.py` 的 `header_fix`）
4. ~~发布~~ 2026-11-06 英文版上线（只过第 ① 层，书首页注明为校勘中的工作本）：
   `python3 scripts/publish_foote_en.py --apply` → `foote/luke/lecture-1…137` + 章目录 `1…24`；
   版式 `_layouts/foote-{book,chapter}.html`（覃红 #d14457）；历代解经登记见 build_commentaries_index.py。
   各讲经文范围写死在 `VERSES`（印本出处 OCR 读花，按连续性定、四讲以经文段末节号核过）。
   渲染验收：误生表格 0、正文 `<ol>` 0、经节锚点 1151＝路加全书节数、重复 id 0。
