# 卡里尔约伯记 OCR 各部：抽章实读校勘记录（old-book-ocr §4.5）

收敛判据：连续 5 个随机抽章（本书以站上一「段」为单位，一段约 20 个印本页；一整章动辄 100–480 页）每页错误 < 1 处。
任何一段 ≥ 1，计数清零。每页图只读一次，错处一次记完。

改正落在 `manual_fixes.tsv`（`scripts/caryl_ocr_manual.py`），流程次序：
`caryl_ocr_witness.py` → `caryl_ocr_ctx.py` → `caryl_ocr_manual.py` → `caryl_ocr_sweep.py`（全书同类清理）→ 发布。

| 轮 | 日期 | 抽中 | 底本 | 页数 | 本段错处 | 每页 | 连续达标 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-25 | 第 9 部 31:7–8（印本 pp. 356–379） | Packer 纸本 300 ppi | 24 | 约 290（落表 234 条，一条常含数处） | ≈ 12 | 0 |
| 2 | 2026-11-25 | 第 9 部 31:9–12（印本 pp. 380–423） | Packer 纸本 300 ppi | 44 | 约 478（落表 370 条） | ≈ 11 | 0 |
| 3 | 2026-11-26 | 第 6 部 21:30–31（印本 pp. 805–821） | Packer 纸本 | 17 | 约 175（落表 137 条） | ≈ 10 | 0 |
| 4 | 2026-11-27 | 第 4 部 11:4–6（印本 pp. 19–54） | Packer 纸本 | 36 | 约 310（落表 251 条） | ≈ 8.6 | 0 |
| 5 | 2026-11-28 | 第 6 部 21:27–29（印本 pp. 783–805） | Packer 纸本 | 23 | 约 250（落表 199 条） | ≈ 11 | 0 |
| 6 | 2026-11-29 | 第 4 部 11:15–16（印本 pp. 116–136） | Packer 纸本 | 21 | 约 180（落表 145 条） | ≈ 8.6 | 0 |
| 7 | 2026-11-30 | 第 9 部 31:19–21（印本 pp. 474–495） | Packer 纸本 | 22 | 约 170（落表 134 条） | ≈ 7.7 | 0 |
| 8 | 2026-12-01 | 第 4 部 13:26–28（印本 pp. 524–542） | Packer 纸本 | 19 | 约 200（落表 153 条） | ≈ 10.5 | 0 |

## 第 1 轮发现的错误类别与全书清理

| 类别 | 本段 | 处理 | 全书命中 |
|---|---|---|---|
| 单字 a/A/I/O 被划进旁注 | ~15 | 拼接层：贴着栏界、离相邻正文词 < 70px 的单字母词归正文 | 各部旁注少 ~300 行 |
| 单字符杂点旁注（u、(、—） | ~5 | 拼接层：删 | — |
| 行末断词后挂旁注，断词拼不上（Pro¬ ［u］ phet） | 2 | 切段层：先拼词、旁注挪到词后 | — |
| 行末连字符拼合时保留（wan-dering、mo-rall） | ~6 | 切段层：去连字符后是词表里的词就去掉 | — |
| 词中断开（direct ly、end lesse、unjust ly） | ~15 | sweep `split` | 225 |
| Job 读坏（Tob、fob、Sob、Jub、小写 job） | ~15 | sweep `job` | 749 |
| 'Tis 开引号读错（"Tis、“ Tis） | ~6 | sweep `tis` | 220 |
| 代词后 mill/mould/mas/vere/mere | ~12 | sweep `modal` | 190 |
| ef/er（of/or） | ~4 | sweep `of` | 102 |
| faith（saith，长 s 读成 f） | ~6 | sweep `saith` | 81 |
| 冠词／物主代词后 may/nay/var（way） | ~15 | sweep `way`（不碰 one/every/any/that/this may——情态动词） | 61 |
| 书卷缩写 I/a.、P/al.、Plal. | ~5 | sweep `isa` | 13 |
| 漏进正文的页眉 | 1 | sweep `head` + 人工表 | — |

未成类、只能逐条改的：斜体段落里的形近字（sowe→some、wish→wist、shed→sued、heart→beast…）、跨页断词（grow-/ing）、
标点与括号。斜体多的页明显更差（p.377 一页 28 处、p.378 23 处）。

另记：
- 原书误植照录：p.371「is sn eternall」（原书 sn）、「Communative Justice」（OCR 给成了正确拼法 Commutative，改回原书）。
- 接字判断：p.362 末行「sin;」确是接字（下一页以 sin; 起），删得对。
- 上下文推定存疑词会给出现代拼法或错词（clogge→dogge、erquirie→enquiry），这类都保留存疑虚线；p.360 的 clogge 已在人工表改回。

## 补录：此前抽查的单页（2026-11-25）

上线前后各部抽查读过的单页，当时只记了错处、没落表；按「已读的图不再重读」补进 `manual_fixes.tsv`（共 57 条），
叶号记进 `read_pages.tsv`，抽样脚本 `scripts/caryl_ocr_sample.py` 自动跳过这些叶。这几页不是随机抽章，不计入收敛判据。

| 部 | 叶 | 段 | 落表条数 | 备注 |
|---|---|---|---|---|
| 4 | 187 | 12-1 | 1 | trow→know（真词误读） |
| 4 | 383 | 13-5 | 6 | |
| 6 | 92 | 18-11 | 4 | 原书误植 Champer 照录 |
| 6 | 776 | 21-23 | 5 | |
| 8 | 171 | 27-7 | 29（约 60 处） | 对开本两栏 331–332；墨渍处「Dream, or the Interpretation」可辨认，已补 |
| 9 | 572 | 31-26 | 12 | |

对开本第 8 部这一叶两栏约 60 处错，即每栏约 30 处，远高于四开本各部，页首加重提示的判断不变。

## 第 2 轮发现的错误类别与全书清理（第 9 部 31:9–12，44 页）

结构类（切段层 `caryl_ocr_text.py` 改判据，全书重切）：

| 类别 | 本段 | 处理 | 全书 |
|---|---|---|---|
| 段首经文框截断：第一行后就关框，其余经文落进讲解（「…or if」） | 1 | 上行无句末标点时收悬挂缩进的小写续行；不缩进的新一节重合 ≥ 0.4 即收 | 20 余段经文框补全 |
| 出处行读坏：OB／IOB／10B／02／JOR／JOE／108 → JOB；Verf → Vers | 1 | 出处行归一 | 全部段首 |
| 段首花体字母下半截读成第二行行首碎字（「I and imprecation」「proLsperitie」「Zfury」） | 1 | 讲解首段第二行：比首行靠左的单字母剥掉；粘在词前的按词表剥（对开本不碰） | 59 |
| 逐节小标题以断词号收尾、续行落成正文（「let other¬ / bow downe upon her.」） | 1 | 续行小写起头就并进小标题 | 20 余处 |

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 'Tis 撇号读丢（句中独立的 Tis／tis；「wait tis」是 till 不碰） | ~6 | 620（含旧规则） |
| 长 s 读成 f：fhall→shall、fin/finne/finfull→sin… | ~8 | fh 233、fin 122 |
| of 与后词粘连：ofit、ofthe、ofa… | ~8 | 193 |
| bis/bim → his/him（「a five-fold bis」不碰） | ~5 | 133 |
| 书卷：(I Cor.→(1 Cor.、(Ter.→(Jer.、(Hof.→(Hos. | ~4 | 96 |
| 代词后 hill → will、mould not → would not | ~3 | 34 |
| (faith the text → (saith | 1 | 4 |
| 页底书帖签名漏进正文（D dd、E e e、Ggg→SES、H h h、afB bb） | 5 | 102 |
| 页缝把一句话劈成两段（签名或空行横在句中） | 4 | 74 |

清理规则自身的误伤也在这一轮修了：拆词合并把「a mind full of Anguish」并成 mindfull（冠词后、接 of 时不并）；
「and resol ved」被前一对匹配吃掉（拆词改为迭代到不动点）。

人工表（`caryl_ocr_manual.py`）补两条：原串、改成里可写 `\n`（并回劈开的段落）；「改成的串已在」只在原串已不在或原串包含于改成串时才判已落盘
（「base and H h h」→「base and 」那种前缀情形、或改成的串碰巧和段首经文框里一句相同，都曾被误判成已落盘）。

切段层改动后证人／上下文层少推定了 11 处（ihall、vauey、juast…），按上一版链条的读法落了人工表。

原书误植照录（本段）：bleed（shedding bleed）、concupisciple、glace（glace of thine eye）、fanlt、watied、uot、notorius、Cannanites、aud、mnsicallnesse、wardrope；
原书拼法 deceave／deceaves／deceavers 照录（OCR 给成了 deceive）。

未成类、只能逐条改的：斜体段里的形近字（wise→wife、mill→will、mas→was、ie→is）、旁注拉丁文与希伯来／希腊文（逐条照影像补，共 20 余条旁注）、括号与标点。

## 第 3 轮发现的错误类别与全书清理（第 6 部 21:30–31，17 页）

版面类（拼接层 `caryl_ocr_assemble.py`）：

| 类别 | 处理 | 全书 |
|---|---|---|
| 第 6 部第 732 叶以后一批页（多为偶数叶）版心窄约 90px，按全部固定栏宽推出的右界落在真行尾外，±60px 的实测校正一条也收不到；整页满行被判成短行，每行自成一段，旁注词混进正文 | ±60 内收不到点时，改取行首／行尾残差最密的一簇做校正 | 第 6 部 29 页病页 → 0；其他各部只变了对开本 2 叶（拉丁旁注归位） |

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 w 读成 m：主语后 mas/mere/mill/mould → was/were/will/would；the mord → word；the/a/no mise → wise；mbo/Nho/H'ho → who（「Every mas」是 man、「my mise」是 wife，都挡掉） | ~8 | 106 |
| 长 s 读坏的 shall：sall/spall/spalt/sual | 4 | 55 |
| 句首斜体 Y 读成 T：Te have/are/shall… → Ye | 2 | 23 |
| 书卷缩写：(Per.→(Jer.、(Isa-→(Isa. | 2 | 11（另 (Plal. 已有规则） |
| 整段乱码（书末花饰、横线、单成一段的签名，如「AMENENE MMA」「========T===」） | — | 35 |
| 段首噪点「- 」：markdown 排成项目列表 | 1 | 2（页面 `<ul>` 4 → 0） |
| 书帖签名里 l 读成 1/I（「LI11I 2」=Lllll 2）、长签名超过 4 截（「M m m m m」） | 2 | 签名判据补全 |

撤回：第 2 轮的 ofx 规则（ofit→of it）。p.813 影像证实原书「repayment ofit」「withthe」本就连排，照录；前两轮人工表里单纯把 ofit 拆开的条目一并改回照录。
清理规则误伤修了一处：way 规则把「yea to their yea, and nay to their nay」的 nay 改成了 way，已挡住。

切栏修正后第 6 部 21-19、21-23、21-27、21-32 几段证人／上下文层少推定了 8 处（Enomlidge、Vho、morms…），按上一版读法落人工表。

原书误植／拼法照录（本段）：punishmeut、destructiou、voluptuons、aud、therns、be hath、flatteri's、withthe、ofit。

## 第 4 轮发现的错误类别与全书清理（第 4 部 11:4–6，36 页）

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 代词 I：粘连 Iam/Ihave/Iwill…、撇号噪点 I'have/l'am、l 读成 I（「l will」「yea l judge」） | ~10 | 316 |
| 长 s 读成 f：fo/fay/fome/fuch → so/say/some/such | ~3 | 103 |
| of 读成 ot（后接限定词） | 2 | 34 |
| 书卷数字与卷名粘连：1Cor. → 1 Cor.（图上原书有空格） | 2 | ~45 |
| 页边阴影读成的「«」「»」 | ~6 | 53 |
| 页顶页眉残片：锚点后「Vers. 〔节号被划进旁注〕」、对开本「An 〔页码〕 Exposition upon the Book of」 | 2 | 4 |
| 正文小词被划进旁注（「God [is] invincible」）：人工表跨不了标签，在清理脚本里按看图结果逐条放回（MARGIN_BODY） | 1 | 1 |

试过但没落的：按二元组频率把旁注里的单个小词全书放回正文（打分能挑出 16 处，但图上没逐条核，未上）；
段首「(」噪点（页边阴影）——与原书真开括号形态一样，只能逐条改。

清理规则误伤修了一处：拆词合并把「a wry thought」并成 awry（冠词／代词后不再合并）。

原书误植照录（本段）：trne、doctriue、ns（Let ns）、uuderstandings、thiugs、douhle、whics、beeause、succestfull、spoak、fulfulling、aud、revealed us（漏 to）；
本页 p.25 页眉误印 Vers. 16、页码 131。

## 第 5 轮发现的错误类别与全书清理（第 6 部 21:27–29，23 页）

版面类：
- 拼接层：p.799 旁注栏紧贴正文，46 条旁注里大半被划进正文（正文行尾挂着拉丁词）。真行尾只有 5 行没粘旁注，凑不够最密簇的 6 点；门槛降到 5。全书只改了这一叶。
- 切段层：逐节小标题以「…the Prince? and」收尾、下一行小写续行时落成正文。上行没收尾、重合 ≥ 0.5、小标题不超过两行时并入。全书并回 24 处（多在对开本与第 4 部）。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 W 读成 W'／u'／n'／N'／Iv'（W'hat、n'hen、Iv'here） | ~6 | 77 |
| 斜体 J 读成 f：femes/facob/ferusalem/feremie/foseph | ~4 | 28 |
| sob → Job（并入 job 规则，排在 saith 之前） | ~4 | 116 |
| 句中 Te → Ye | 2 | 28（含旧规则） |
| (Job. N.N) 实为约翰福音：拿后文与 KJV 约伯记、约翰福音同节比，约翰明显更合才改 | 1 | 5 |
| 被划进旁注的正文小词（God [or] (as、draw [it] out、if [all] that…），看图逐条放回 | 4 | 4 |

原书误植照录（本段）：saith or him、gives he reason、a m an、pass e、kaown、adventnre、Aud、wrongfuly、aginst、divices、indeeed、disconrses、wickednsse、euquired。
p.800「may give a ▇ resolution」原书墨渍，读不出，未补。

## 第 6 轮发现的错误类别与全书清理（第 4 部 11:15–16，21 页）

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 Y 读成 T：Tea → Yea、Tou → You | 3 | Tea 26、Tou 9 |
| 句首 l → I | 1 | 3（另 pronI 旧规则） |
| Ged → God | 2 | 43 |
| osten → often（长 s 读成 f 的另一形） | 2 | 83 |
| chap./vers. I0. → 10. | 2 | 2 |
| 旁注插在正文词中间（「ret [旁注] neweth」）：并词、旁注后挪（MARGIN_SPLIT，看图逐条） | 1 | 1 |

版式：p.117 原书大括号表（First/Second/Third — an Honourable/a Setled/a Comfortable — estate）OCR 拆成碎行，按文意排成一句。
「ofit」并非处处连排：p.132「or as much / of it」原书分行，OCR 拼成 ofit，逐条改回。

原书误植照录（本段）：Secondy、fillthinesse、Pnblican、onec、Will yea、melled、soild、graee、nnsetlednes、destraction、delivrance。
p.128「cannot ▇ remain」墨渍，按文意补 but。

## 2026-11-29 全书同类错误复查

逐类在全书现有文本里数残留，发现清理规则有三处够不着：
1. **存疑标记切断匹配**：清理按标签切段，被 cy-ocr 包着的词把句子切开（「punispment</span> ef the」「(<span>Plal</span>. 139」），
   跨标记的规则全部失效。改为段内透过存疑标记匹配，改动碰到的标记一并去掉。全书多清出数百处（split +130、of +38、pronI +60 等）。
2. **规则写窄**：Te/Tou 只认部分后接词（「(Exod.19.6.) Te shall」漏）→ 后接小写词即改；W'h 只认 what/when 等几个词 → 泛化（wherefore、whether、while；I'hope／I'hid 拆成 I＋词）；
   代词 I 粘后词（Irejoyced、Igave）、anto → unto。
3. **页内段落劈开**：段尾以字母收尾、下段小写起头、上段不短于 50 字符时并段（不收「Observe,」后的论点句）。全书 76 处。

另查出 5 处段首出处行漏认（JOB 读成 B／DB／110 B，或「JOB19」粘连），5 段讲解被并进上一段：
第 6 部 19:29；第 9 部 30:16–17、31:29–30、31:35–37、31:38–40。切段层补认后各成一段，站上多 5 页（共 366 页）。
「B 31. Verf. 27, 30.」节号读坏，规则：节号不连续且落进上一段范围时，从上一段末节接着算（连续的重叠如 19:15–19 不动）。
重切后证人层在这几段少推定的词按上一版读法补表。

复查后残留（不再成类）：W'h 混读坏 7 处（u'hois、'heremithall、n'hercfore 等，词身另有错字）、Tea/Tou 3 处（「Tou saith」等不是 You）、
mith／mhich 等 3 处、页内劈段 76 处（上段是小标题、经文框或旁注行，规则不碰）。

## 第 7 轮发现的错误类别与全书清理（第 9 部 31:19–21，22 页）

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 th 读坏：ihe/ibe/tbe/rhe → the、ibat/tbat → that、rhen → when | ~4 | 135 |
| 斜体 w 读成 m：I sam → I saw、for mant → want；物主词后 omne/onne/omn → owne | ~6 | sam 7、owne 50 余 |
| 长 s：on every fide → side | 1 | 1 |
| 代词 I 读成 l（句中，后接常见动词） | 1 | 24 |
| (sal. → (Psal. | 1 | 1 |

原书误植／拼法照录：le thankfull、Naboath、wardropes。

## 第 8 轮发现的问题与全书处理（第 4 部 13:26–28，19 页）

结构类（本轮主要收获）：
- **页码锚点读错成串**：这一段锚点标 324、334，原书是 524、534——页码读数「5」读成「3」，连着几页都错，彼此差值又对得上，原判据挡不住。
  `assign_pages` 先剔离群：读数换算成偏移（页码 − 叶号×栏数），与全部中位数差 > 20（对开本 > 1）的不用。
  全书改正：第 4 部 43 叶、第 6 部 12 叶、第 8 部 5 叶（看图核过：202=393、203=395）、第 9 部 2 叶。
- **扫描乱序与漏页**（看图核过）：第 4 部第 172、173 叶互换（印本 166/165），漏扫 164、167；第 9 部第 307/308、309/310 两对互换，漏扫 302、307。
  切段层按原书页序重排（LEAF_SWAP、PAGE_SET），漏页处插「此页扫描件缺」说明（PAGE_GAP），以前句子被错页接上的地方现在断在缺页处。
- **版面**：第 4 部第 545 叶旁注紧贴正文（真行尾只有 4 行）；切栏回退判据再放宽一档（±15px、4 点）。同时让第 4 部 237、275、281、317、355、600 等叶行末被划进旁注的小词（of、the、and、un¬…）回到正文。
- **小标题**：「Verse28.」号码被 \w{0,2} 吞掉首位成 13:8（与 13:5 段锚点重复）——修正；顺带排除「Vessel, filled」误判、补认「Vess.5.」。
  标题末尾一两个词的短续行（「is moth-eaten.」）并入标题。

文字类：「T hat」「T hou」「T he」→ That/Thou/The（大写 T 后多空格）、unde standing → understanding。

版面修正后证人层在那几叶少推定了 7 个词（speak、justice、doing、with、such、translates、gird），按上一版读法补表。
