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
| 9 | 2026-11-26 | 第 9 部 30:16–17（印本 pp. 152–170） | Packer 纸本 | 19 | 约 295（落表 219 条；正文约 240） | ≈ 15.5（正文 12.6） | 0 |
| 10 | 2026-11-26 | 第 4 部 12:5–6（印本 pp. 186–205） | Packer 纸本 | 20 | 约 225（落表 151 条；正文约 146） | ≈ 11.2（正文 7.3） | 0 |
| 11 | 2026-11-26 | 第 6 部 21:4–6（印本 pp. 627–646） | Packer 纸本 | 20 | 约 245（落表约 180 条；正文约 208） | ≈ 12.2（正文 10.4） | 0 |
| 12 | 2026-11-26 | 第 4 部 14:1–2（印本 pp. 544–561） | Packer 纸本 | 18 | 约 270（落表约 160 条；正文约 226） | ≈ 14.9（正文 12.6） | 0 |
| 13 | 2026-11-26 | 第 6 部 20:15–17（印本 pp. 510–524） | Packer 纸本 | 15 | 约 180（落表 111 条；正文约 130） | ≈ 11.8（正文 8.7） | 0 |
| 14 | 2026-11-26 | 第 4 部 14:18–22（印本 pp. 650–671） | Packer 纸本 | 22 | 约 150（落表 120 条；正文约 120） | ≈ 6.8（正文 5.5） | 0 |
| 15 | 2026-11-26 | 第 9 部 30:4–7（印本 pp. 42–63） | Packer 纸本 | 22 | 约 190（落表 160 条；正文约 165） | ≈ 8.6（正文 7.5） | 0 |
| 16 | 2026-11-26 | 第 8 部对开本 28:1–11（第 401–428 栏） | 1676–77 对开本 | 14 叶 28 栏 | 约 560（落表 458 条；正文约 520） | 每栏 ≈ 20（每叶 ≈ 40） | 0 |
| 17 | 2026-11-26 | 第 9 部 31:34（印本 pp. 710–725） | Packer 纸本 | 16 | 约 140（落表 114 条；正文约 120） | ≈ 8.8（正文 7.5） | 0 |
| 18 | 2026-11-26 | 第 6 部 19:13–14（印本 pp. 232–253） | Packer 纸本 | 22 | 约 125（落表 106 条；正文约 115） | ≈ 5.7（正文 5.2） | 0 |
| 19 | 2026-11-26 | 第 4 部 12:17–18（印本 pp. 265–284） | Packer 纸本 | 20 | 约 230（落表 239 条；正文约 200） | ≈ 11.5（正文 10） | 0 |
| 20 | 2026-11-26 | 第 6 部 18:17–21（印本 pp. 114–136） | Packer 纸本 | 23 | 约 190（落表 169 条；正文约 160） | ≈ 8.3（正文 7） | 0 |
| 21 | 2026-11-26 | 第 6 部 21:11–13（印本 pp. 664–680） | Packer 纸本 | 17 | 约 150（落表 124 条；正文约 125） | ≈ 8.8（正文 7.4） | 0 |
| 22 | 2026-11-26 | 第 4 部 14:3–4（印本 pp. 562–578） | Packer 纸本 | 17 | 约 150（落表 128 条；正文约 130） | ≈ 8.8（正文 7.6） | 0 |
| 23 | 2026-11-27 | 第 9 部 30:15（印本 pp. 133–151） | Packer 纸本 | 19 | 约 175（落表 148 条；正文约 150） | ≈ 9.2（正文 7.9） | 0 |
| 24 | 2026-11-27 | 第 6 部 20:20–23（印本 pp. 541–563） | Packer 纸本 | 23 | 约 230（落表 177 条；正文约 185） | ≈ 10（正文 8） | 0 |
| 25 | 2026-11-27 | 第 6 部 21:16–18（印本 pp. 704–713、716–724） | Packer 纸本 | 19 | 约 165（落表 136 条；正文约 155） | ≈ 8.7（正文 8.2） | 0 |

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

## 第 9 轮发现的错误类别与全书清理（第 9 部 30:16–17，19 页）

本段错处约 295（落表 219 条）：正文约 240（每页约 12.6），旁注约 55——这一段旁注密，希伯来文、拉丁文、希腊文旁注 15 条几乎全读坏，逐条照影像补。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 英文词里冒出组合附加符（thé、à、oùr、wherés、quiçkly、Slèepe、fighóings）：去掉后是本书常见词、带符号的拼法本书没有才去 | ~10 | 643 |
| 私用区字符 U+E8BF（拉丁文缩写 q;，「Animam;」）→ q; | 2 | 114（多在旁注） |
| 词与 ’tis 粘连：and’tis、when’tis、but’tis → and ’tis | 6 | 132 |
| 长 s 读成 f：himfelf(e)、themfelves | 2 | 50 |
| 小写 tob → Job | 1 | 40 |
| 斜体 M 读成 A：Ay bones／Ay heart／Afy dayes → My | 4 | 16 |
| 主语后 nas → was | 2 | 5 |
| tabe → take | 2 | 18 |

结构类（未成规则，逐条改）：
- 逐节小标题第二行（「sinews take no rest.」）落成正文段、旁注插在中间；本段在人工表里并回标题。
- 页面透印的反字（下一页「Affliction」「Note」反面透过来）被读成乱码插进正文（p.161 两处）；页末接字「First,」读成「Firé,」漏进正文（p.154）。
- 跨页断词 pier-/ceth、afflicti-/on、Solo-/mon 拼不上，挪到前一页拼合。

已知未修：原书 powre／poure 两种拼法都用（TCP 卡里尔语料 powre 系 180 次、poure 系 116 次），本段影像全是 powr-，OCR 读成 pour- 的约 20 处已逐条改，全书无法按规则改。

原书照录：O momother（行末 mo- 与下行 mother 重排）、he (being God)。

## 第 10 轮发现的错误类别与全书清理（第 4 部 12:5–6，20 页）

本段错处约 225（落表 151 条）：正文约 146（每页约 7.3，九轮来最低），旁注约 79——希伯来／拉丁旁注 19 条几乎条条读坏，逐条照影像补（旁注占了本段三分之一）。
p.205 下半页是下一段 12:7 的开头，同一张图一并核了（落表 8 条）。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 序数词数字读成字母：IIth／Sth／2oth／I2th → 11th／5th／20th／12th | 3 | 20 |
| 经卷引文章号 5 读成 S：(Joh. S. 35.) → (Joh. 5. 35.) | 1 | 7 |
| 代词后 hall → shall（长 s 读丢） | 2 | 17 |
| 介词后 tle → the | 1 | 12 |
| 旁注 mibi → mihi（旁注不进文字规则，单独全文改） | 2 | 14 |
| uhen → when、the seet → feet、wi ll → will | 3 | 4 |

人工表补：`MARGIN_BODY` 可带第 5 列（放回正文时改成的词）——p.193「(It is a」的 a 连同括号被划进旁注读成「al」。

未成类、逐条改的：经卷引文漏点（Psal.306、Psal. 7318、Revel.187——三四位数字不能按规则拆）、斜体段里的形近字（fret/seet→feet、affections→afflictions、That→What）、
跨页断词 oppo-/sers、mo-/narchy；小标题「Are secure.」被并进上段末尾。

原书照录：evedence、reaason、页码 194 误印 195。

## 第 11 轮发现的错误类别与全书清理（第 6 部 21:4–6，20 页）

本段错处约 245（落表约 180 条）：正文约 208（每页约 10.4），旁注约 36（希伯来／拉丁旁注 9 条照影像补）。
中途（读完 p.627 后）停下深查人工录入本：TCP 全目录与网上各家都没有缺的 4 部（见 PROVENANCE.md），回来续读。

结构类：
- **页末接字没剔掉**，与下页首词重复（「complaining. Having ⟨p.630⟩ Having given」）：拼接层判接字要「短、靠右、在末行」，
  接字与书帖签名同行、或签名夹在中间时漏判。清理层补：「词 ⟨页码锚点⟩ 同一个词」去掉前一个，被劈的段一并并回；排在剔签名之后。全书 43 处。
- 旁注栏划走的正文行首词（p.644「ye would」的 ye）：`MARGIN_BODY` 支持空改成（旁注删、正文由人工表补）。

文字类（新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 W 读成 m'：m'hat／m'hy → what／why | 1 | 3 |
| 斜体 w 读成 m：for me have／are／shall、why me doe → we | 1 | 8 |
| 句点后缺空格：turns.'Tis → turns. 'Tis | 1 | 8 |
| fles → flesh | 1 | 4 |

撤回一半：第 9 轮的私用区字符规则（U+E8BF → q;）只在词尾改；正文里单独一个的是别的字读坏（p.640「no \ue8bf as?」原书 Gods），全书由 114 降到 79。
顺带修正：第 9 轮写进 `caryl_ocr_sweep.py` 的一行中文注释被转成了 \u 转义，改回中文。

原书照录：teke（take）、industrions、discouragemenns、hroughont、gloring、himselefe、staitner、murmurrings、judgedhim（连排）。

## 第 12 轮发现的问题与全书处理（第 4 部 14:1–2，18 页）

本段错处约 270：正文约 226（每页约 12.6），旁注约 42。p.554 大面积透印，下半页几乎每行都混进反字乱码；p.561 下半页属下一段 14:3，同图一并核。

结构类（本轮主要收获）：
- **切栏失败：一批页版心比全部栏宽宽约 85px**（扫描缩放不同）。p.550 一页十来个行末词被成串划进旁注（「hastens [out life. but] of our hands」）。
  原 `column_bounds` 在两侧宽度与全部栏宽差 > 30px 时，只信一侧、另一侧按固定栏宽推，砍掉了真行尾。改为：两侧都 ≥ 15 内点、两缘平行、
  宽度在全部栏宽 ±12% 内，就信两侧各自的拟合（旁注外缘拟合出的宽度要多 300px 以上，进不来）。
  全书：第 4 部 159 叶重判，旁注 6012 → 5662 行（约 350 个正文词放回原位）；连带分段判对了（旧判法把行中当段首，如叶 216、218）。
  第 6 部 160 叶栏界微调，正文只变 6 叶；第 9 部 5 叶。剩余疑似病页 26 → 3（第 4 部叶 225、278、284）。
  试过在清理层把「一页 ≥ 4 条单个常见词的旁注」直接拆回正文——第 4 部 13:1 放回的位置错一行（「Look not [the] upon」），撤回，改在拼接层按坐标治。
- **页眉漏进正文**的其余写法（不带 Chap. 或 Vers.、Bookof/Bock/Booke、书名读成 JOn/JeR/JOE）：清理规则放宽，全书 18 处。

人工表：`caryl_ocr_manual.py` 支持改成写 `@正文`（拆旁注标签放回正文）；本轮拼接层修好后 p.550 不再需要，条目已删。

原书照录：sorrs、ordinany、determed、calamitses、Simpathy。
已知未修：14:3 段首旁注希伯来字与「Terminus diminuens.」本在正文旁、OCR 读进了正文行，人工表跨不了旁注标签，暂删正文里的这两处残片（旁注本身保留）。

## 第 13 轮发现的问题与全书处理（第 6 部 20:15–17，15 页）

本段错处约 180：正文约 130（每页约 8.7），旁注约 47（拉丁旁注 11 条照影像补）。

结构类：
- **段首经文框空了**：出处行后第一行斜体读得太烂（「He hath smallomed domne riches. andhe spall vouit」词重合 0.38），整框经文漏成讲解段落。
  `caryl_ocr_text.py` 第一行改用形近匹配（difflib ≥ 0.7）算重合，≥ 0.6 即收；讲解首段（0.17–0.33）进不来。全书只有两段如此（第 6 部 19:10、20:15），都已补全，别段输出不变。
- 小标题行末的词被划进旁注（p.521「brookes [ef]」）：`MARGIN_BODY` 删旁注、人工表补标题。

文字类（新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 句点后缺空格：the sword.It is → the sword. It is（后接常见句首词） | 2 | 约 50 |
| 经文出处右括号后缺空格：(Exod. 12.40.)It came → (Exod. 12.40.) It came | 2 | 约 34 |
| the mood → the wood（斜体 w 读成 m） | 1 | 3 |

原书照录：remporals、senecdochcially、convayance、sometim estaketh、fowler。

## 第 14 轮发现的问题与全书处理（第 4 部 14:18–22，22 页）

本段错处约 150（落表 120 条）：正文约 120（每页约 5.5，十四轮来最低），旁注 18 条（希伯来／拉丁旁注照影像补，7 条整条重录）。
本段是第 4 部最后一段：扫描件止于印本 p.671（叶 677），14:22 讲解半句断在「comprehends all sorts」。

结构类：
- **扫描件在本部结束前就断了**，页面半句收尾而没有任何说明。`caryl_ocr_text.py`：全部最后一段以非句末标点收尾时，插一行
  「[The scanned copy ends here…] 扫描件到此为止，以下各页缺。」全书 3 处：第 4 部 14:18、第 9 部 31:38、对开本 29:24。
- **缺页说明被纠错层当正文**：证人层把说明里的英文词（pages、scans）套上存疑标记。`caryl_ocr_fix.RE_PROTECT` 加 `cy-gap`，与旁注一样不进纠错。
- 旁注首字漏进正文（「grow germi-out」「themselves, Va-and」「lives in A」）：人工表逐条删、旁注补回首字。
- 引语逐行带“的段落被劈成两段（p.651「change come. / Let me be removed」）：人工表并回。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 w 读成 v：that ve have、need ve hope → we；「lo ve」「ha ve」是词被拆开，并回；「O ve」→ O ye；前词是残片（Ih ve、shal ve）不碰 | 1 | 约 150 |
| 句首斜体 M 读成 A：Ay ＋任何词 → My（第 9 轮只认 bones/heart 等，全书看过余下 30 余处都是 My） | 1 | 约 50 |
| 长 s 读成 f：fignif- → signif-（旁注拉丁 fignificat 一并，全文改） | 2 | 48 |
| 斜体 W 读坏：M'hen／NVe／IVho → When／We／Who（去掉后是本书常见词才改） | 2 | 16 |
| 序数词 zoth → 20th | 1 | 16 |
| out ward(ly) → outward(ly) | 1 | 31 |
| thoy：后接动词 → they，后接名词／own → thy（其余不碰） | 1 | 9 |
| 物主词后 orn／oun → own；Obierve／Oblerve → Observe；(l conceive → (I；, be shall → , he shall；Tte → The | 各 1–2 | 共约 15 |

撤回／不改：本段影像里 `wean the stones`（小标题）、`Propheet`、`Athiest`、`he wasketh`、`because that with waxeth`（=which）原书如此，照录；`Asick`、`betterto` 原书连排照录。
另记：重跑第 8 部（p82）切段层与 TCP 抽取（extract_caryl.py）时，现行脚本的输出与已提交版本有零星出入（经文框界、virum que→virumque），与本轮无关，未夹带。

## 第 15 轮发现的问题与全书处理（第 9 部 30:4–7，22 页）

本段错处约 190（落表 160 条）：正文约 165（每页约 7.5），旁注 11 条（希伯来／拉丁／希腊旁注几乎条条读坏，整条照影像重录）。
本段斜体引文多（经文、Broughton 译文、小标题），斜体段里的形近字仍是大头（me→we、ue→we、R'ho→Who、witb→with）。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 斜体 w 读成 m：that／and／when／which… me have／shall／should／may → we（「let me」「towards me」不在前词表里，不碰） | 2 | 约 60 |
| 斜体 h 读成 b：witb／hatb／Tbou → with／hath／Thou | 3 | 约 17 |
| 斜体 W 读成 R'：R'ho／R'herefore／R'hatsoever → Who／Wherefore…（去掉后是本书常见词才改） | 1 | 8 |
| Aud → And | 1 | 13 |
| hill I → will I；Thou halt → Thou shalt | 2 | 6 |
| Ibe：情态词后 → I be，句首 → The | 1 | 4 |
| malloms／mallons → mallows | 6 | 6（本段全部） |
| the sth verse → 5th；asthe → as the；Terusalem；(fer. → (Jer. | 各 1 | 共约 10 |

结构类：引文被页内劈段（p.62「&c.— ⏎ should have fed them」，劈段处还丢了 I）、段首经文框首行 R'ho 读坏，逐条改。

不改：ofits（p.813 影像证实原书连排，第 3 轮已定照录）；Scriprure、Rabshaketh、reretirement、Monchury、Propheet 原书如此，照录。

## 第 16 轮发现的问题与全书处理（第 8 部对开本 28:1–11，14 叶 28 栏）

先误抽了 p8（四开本第 8 部，站上 27–29 章用的是对开本 p82，p8 没上线）：读了 p.163 一页后发现，结果未落表，叶号记进 ledger 免得再抽；
p8 重跑产生的改动全部撤回。随后改从上线的四部（p4/p6/p82/p9）里抽，抽中 p82 28:1–11——对开本第一次整段实读。

本段错处约 560（落表 458 条）：正文约 520，每栏约 20、每叶约 40，远高于四开本各部；旁注 25 条整条照影像重录，10 条碎片删除。
黑体（black-letter）逐节小标题几乎行行读坏（De setteth、ano、Ebe、epe、bath、babe、net），本段逐条改。

结构类（`caryl_ocr_text.py`，只动对开本）：

| 类别 | 处理 | 全书 |
|---|---|---|
| 左右两侧旁注按高度混排，`group_margin` 只看上一行同侧，左右交错时一条也并不上：一条拉丁旁注碎成 40 多条 | 两侧分开并，再按起头高度排 | p82 旁注 810 条（466 条不到 18 字）→ 432 条（133 条） |
| 章首通栏整章经文，每行右半被版心右界切进右旁注 | 第二栏起头之上、同高只有一行正文的右旁注接回行尾（章题行不接） | 3 章章首 |
| 中缝行号「80」被切进旁注，右栏末行同高时整行跟着进了旁注（「(8o l bread at the Table…」） | 页底这类旁注：只有行号的删，带正文的剥掉行号作右栏末行接回 | 约 50 叶 |
| 胶片水印「UMI」作旁注 | 删 | 59 |

`caryl_ocr_manual.py`：`@正文`（旁注词放回正文）在段内不唯一时，原串可写「前文⟦旁注词」按紧挨的正文定位（本段两处 `is`）。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 正体长 s 读成 f、两层都没判的非词：faw／fecond／fuffice／impoffible → saw／second…（本书 0 次、改后 ≥ 30 次才改；fuit 拉丁、fon 黑体多是 for、fouls 也作 fowls、Ifa＝If a，不碰） | 约 10 | 约 70 |
| 斜体 is 读成带附加符号的单个 u：There ù a vein → is | 4 | 17 |
| 黑体 and 读成 ano／anu／ann、The 读成 Ebe、eye 读成 epe | 约 8 | 66 |

未处理、记下：对开本黑体逐节小标题大面积读坏（每段十几行），单词规则只补得了 and/The/eye；要么逐段看图，要么拿钦定本经文对齐重建，另议。
英文词里夹希腊字母（Eærιb、τhεm）p82 约 90 处，须看图，未动。
原书照录：There a is vein（p.408）、the desire of God is a most wicked desire（p.413）、Tubal-Caen、synechochically、by the the labour。

## 第 17 轮发现的问题与全书处理（第 9 部 31:34，16 页）

本段错处约 140（落表 114 条）：正文约 120（每页约 7.5），旁注 11 条（希伯来／拉丁）照影像整条重录。
页末提示词与书帖签名读成一段（「Wec 22242」）、跨页的 can｜not 读成 canset，逐条改。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| If eare → I feare | 3 | 4 |
| 斜体 J 读成 T／f 的人名：fonathan／Tosbua／fohn／fordan／fudah → Jonathan／Joshua／John／Jordan／Judah | 3 | 约 10 |
| 人称后的 sam／san → saw（I san the Lord、Pilate sam that） | 2 | 3 |
| 句末断词号残留：him¬. → him. | 2 | 10 |
| 页底提示词＋签名单成一段（Wec 22242、Verse S8882）：并入整段乱码删除 | 1 | 2 |
| lut → but（逗号或 nothing 之后）；agairst → against | 2 | 3 |

不改：ofit／toit／doit／init 全书约 200 处，第 3 轮影像证实部分原书连排，仍只按影像逐条改（本段 p.712 一处是分开印的，已改）。
原书照录：weakues（p.717）、even his evermore、by the the labour、raile（p.712）。

## 第 18 轮发现的问题与全书处理（第 6 部 19:13–14，22 页）

本段错处约 125（落表 106 条）：正文约 115（每页约 5.2，十八轮来最低），旁注 7 条（希伯来／拉丁／希腊）照影像重录。
跨页断词三处（Oni｜sephorus、bur｜den'd、can｜not 类）只改本页那半截；页底签名「Kk」读成 XK、透印读成旁注 DEE，删。
序数词里 I／1 读法不定（Ioth 本段两处是 19th，1oth 两处是 16th），不能立规则，逐条改。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 序数词拆开：13 th verse → 13th；13thi → 13th | 2 | 约 10 |
| 经文出处 ( Per. 15. 21.) → ( Jer.（斜体 J 读成 P） | 1 | 4 |
| Æegypt → Ægypt；Cbserve → Observe；spould → should；sucha → such a | 各 1 | 约 10 |

本轮工具修正：落表前的检查脚本此前查到失配也返回成功，有 3 条坏条目连同改好的版本一起进了表，全链重跑报出后删除；检查脚本已改为失配即失败。
原书照录：ngelected（p.243）、indishonour、poverte（p.246）、faithsulnesse（p.252）、afflictionr（p.244）、strome、did ot cause（p.243）。

## 第 19 轮发现的问题与全书处理（第 4 部 12:17–18，20 页）

本段错处约 230（落表 239 条，含旁注词放回正文的条目）：正文每页约 10，比上两轮反弹；旁注 16 条（希伯来／希腊／拉丁）照影像整条重录。
本段扫描偏淡、行尾常被切进旁注栏：p.272、p.278 各有 6–7 个行末词（the／is／to／in／so／by／of）被当成旁注，
用人工表的 `@正文`（「前文⟦词」定位）放回原处，再逐条把词挪到影像里的位置。全书仍有约 55 条这样的单词旁注（多在 p4 12-15、12-7 与对开本），留待抽到时逐页处理。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 大写 Rings → Kings（K 读成 R；1 Rings 17、the Rings gate、reproved Rings） | 2 | 7 |
| vise → wise（斜体 w 读成 v；「a prudent vise」＝wife、拉丁 vise tatione、in any vise 不碰） | 4 | 约 15 |
| sucb → such | 1 | 2 |

不改：whichis／mhichis 等连写约 27 处，与 ofit 同一处理（部分原书连排），只按影像逐条改。
原书照录：Jer.19.11（实为 Isa.19，原书误注）、thatGod、fouls of the Heaven、Generalissimo、Rehoboham。

## 第 20 轮发现的问题与全书处理（第 6 部 18:17–21，23 页）

本段错处约 190（落表 169 条）：正文每页约 7，旁注 22 条（希伯来／拉丁）照影像整条重录。
页首续行 4th) 读成 1)、跨页段落劈开，逐条改。

撤回（误伤）：`way` 规则把「the same may we to Bildad」（p.114，情态动词 may）改成了 way。规则加了排除：same 之后的 may／mav 不改。全书 2 处恢复。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| bave → have（斜体 h 读成 b；语料里有一次 bave，第 1 层没碰） | 1 | 25 |
| left 读成 lest：he／God／all／hath／not／nothing … lest him／them／us → left | 0 | 10 |
| lest me bring／judge／mar → lest we | 0 | 3 |
| spall → shall；bnom → know | 2 | 少量（多在存疑标记里，改了推定字） |

原书照录：Hester、Geneallogies、unappliable、Pharoab、contentfully、consanguitie、resurrction、the Isles shall be astonished（本段斜体经文照印本）。

## 第 21 轮发现的问题与全书处理（第 6 部 21:11–13，17 页）

本段错处约 150（落表 124 条，其中 10 条是把 OCR 给成正确拼法的原书误植改回）：正文每页约 7.4，旁注 13 条（希伯来／拉丁）照影像整条重录。
行末 is 被切进旁注 3 处（p.675 两处、p.678），用 `@正文` 放回；页底签名「RIrr2」、跨页小标题并段，逐条改。
p.680 下半页属 21-14 段，同一张图读过，6 处一并落表（段首经文框 There forè／me desire、wve desire na the trn ledge）。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 撇号噪点插进 Th：T'hey／T’hat／T’he → They／That／The（p82「T'hah」不碰） | 2 | 8 |
| momen → women（斜体 w 读成 m；「momen any」＝momentany、「the momen grass」不碰） | 1 | 9 |
| 词尾 !! → ll（natura!!／special!!／a!!） | 1 | 3 |
| inus → in us | 1 | 6 |
| hour hand(s)／selves → your（斜体 y 读成 h） | 1 | 3 |
| 代词后 bad not／been → had（「so bad not to have」不碰） | 1 | 4 |
| Ie is／hath／notes… → It（Ie are／walk／shall see 多是 We，不立规则） | 1 | 约 16 |

工具修正：
- 清理脚本一遍到不了不动点：整链重跑后再试跑，仍有签名「A a a a 2」、we mill 等 7 处要第二遍才清。改为每段迭代到不动点（至多 5 遍）。
- 人工表两对跨页断词条目（p4 12-5 mo-/narchy、p9 30-16 afflicti-/on）次序不稳：先补前半时纯文本里整词已经拼成，被判「已落盘」跳过，
  接着删后半，新链上会出「spiritual momust」「afflictior」。上线版是旧链产物所以没坏；两对都改成先删后半、再补前半，p9 那处顺带补回 affliction 后的空格。

原书误植照录（本段）：attecedent、exponnd、unlawfnll、conntenance、counteuance、houle、rhis、coporally、rlations、spendiug、heen；
he had is family、troublons、Ezek. 39 38（实为 36:38）照印本；thns（And thus Job）、soand（vhead 的 sound）两处 OCR 已给正确拼法，未改回。

## 第 22 轮发现的问题与全书处理（第 4 部 14:3–4，17 页）

本段错处约 150（落表 128 条，其中 6 条把 OCR 给成的正确拼法改回原书误植）：正文每页约 7.6，旁注 16 条（希伯来／拉丁）照影像重录。
本段偶数页左栏旁注切栏失败：旁注的词头被拼进正文行首，成了「Aposcri-sole」「especicu-cially」「appe-up」「su-the」「corrupti-the」这类
「旁注碎片-正文词」，一条拉丁旁注碎成两三截（p.566、567、578），逐条照影像删碎片、把旁注并成一条。
p.575 页底三行拉丁脚注续接旁注，「Clarum sa-」一截被切进旁注，放回。
全书「碎片-常见词」形状约 44 处（多在 p4 11-7、12-1、14-15），形状不足以判定哪半截是旁注，留待抽到时照影像处理。

人工表次序：把三截旁注并成一条时，要先删后两截、再改第一截（先改第一截，后两截的文字就在第一截里重复出现，判「不唯一」）。

结构类（`caryl_ocr_sweep.py`）：

| 类别 | 本段 | 全书 |
|---|---|---|
| 页码锚点后只剩页眉左角「Chap.14.」单成一段：删掉，下一段小写起头的并回同一句 | 2 | 15（p4 14-5／14-7／14-13、p6 19-4／19-7／20-27） |

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| 分句首（逗号／分号／冒号后）或 if／when 后的 me ＋ 情态词 → we（25 处逐条看过） | 2 | 约 30 |
| 英文词后的 vas ＋ 小写词 → was（拉丁 vas 前接希腊字母，不碰） | 1 | 27 |
| flest → flesh | 2 | 11 |
| Pob → Job | 1 | 3 |

原书误植照录（本段）：apon、afer、conscienee、spinging、uuclean、impossile；另 wbrds、poisnous、canno、mor、brethen、therereby、ourparents 本来就照印本，未动。

## 第 23 轮发现的问题与全书处理（第 9 部 30:15，19 页）

本段错处约 175（落表 148 条）：正文每页约 7.9，旁注 8 条（希伯来／拉丁）照影像重录。
新毛病是**证人层把印本拼法改成现代拼法**：第 9 部的对照本是现代拼法的版次，底本词只要是词表外的当时拼法（immortalitie、mortalitie、
possibilitie、worthlesnesse），按位置对上就被「改正」成 immortality／worthlessness；底本有 OCR 错时（flacke、Aimselfe、jatherlesse），
改出来的也是现代词尾（flock、Himself、fatherless）。p.143 一页就有 6 处 -itie → -ity。

结构类（`caryl_ocr_witness.py`）：

| 处理 | 全书 |
|---|---|
| 底本只是对照词的当时拼法（-ie／-ies／-nesse／-lesse 词尾，y／i 互换）→ 判 archaic，不改、不标存疑 | 65（p9 55、p6 9、p82 1） |
| 底本有错、按对照词改时，保留底本的当时词尾：-ie、-nesse、-lesse，以及词尾 e（对照词加 e 在 TCP 卡里尔语料里 ≥ 5 次才加：flocke、foole、looke、himselfe） | 约 115（p9 108、p6／p82／p4 各几处） |

判当时拼法时只做 y→i 折叠，不折叠双字母（试过折叠，把 loke 当成 looke 的变体放过了，第一次整链重跑时被人工表失配查出来）。
证人层改动后人工表 8 条原串失配（上游改出的词尾变了：Knowledg→Knowledge、usury→usurie、near→neare…），已按新的上游文字改原串。

文字类（`caryl_ocr_sweep.py` 新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| me／he are → we are（「reproached me are」「to me are」不碰；11 处逐条看过） | 1 | 11 |
| should／must／shall… me not ＋ 动词 → we not；think me can、the less me go | 2 | 5 |
| Ie are／walk／may／can／shall see → We（「Ie shall goe ill」是 It，不碰） | 1 | 6 |
| Ther ＋ 小写词 → They；Ther's → There's | 2 | 6 |
| 词中 ! 是 l（Second!y、swa!low、especia!ly、most high!y）；what! have → what I have；which!sin → which sin | 2 | 14 |
| oppressor／cord mas → was；any mas in → any man in | 1 | 4 |
| Ris the → 'Tis the | — | 1 |

原书误植照录（本段）：dee（God dee set）、rected（证人层给成了 erected）、be be（shall be be as the morning）。
本段几处 of it 印本字距看得出分开（p.140、144、149、151），只在本段按影像改；全书 ofit 仍照第 3 轮的判断不动。

## 第 24 轮发现的问题与全书处理（第 6 部 20:20–23，23 页）

本段错处约 230（落表 177 条）：正文每页约 8，旁注 25 条（拉丁／希伯来／希腊）照影像重录，本段旁注几乎条条读坏。
其余成片的：长 s 与 f 混读（sulnesse、surther、lest＝left）、斜体 w 读成 m／n（mrath、mealthy、n'hen）、页底书帖签名漏进正文（Aaaa、Bbbb2、Cccc）、
p.549 两行次序错乱（「his Secondly, Others expound … family.」）、p.550 旁注首行漏、旁注里的 a 落进正文。

结构类（`caryl_ocr_sweep.py` 的页缝处理）：

| 类别 | 全书 |
|---|---|
| 页序数字紧贴存疑标记（`<span class="cy-ocr">Hhhh</span>2`），签名剥离认不出 → 先补空格 | 6（Hhhh 2、XXXX 2、Cecc 2、qqq 2、CCCCc 2） |
| 签名＋接字被拼进末行行中（「are Thus A a a a a justly punished」）→ 人工表 1 条（p6 21-19） | 1 |

文字类（新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| be／is／nothing／meat／are lest → left（「say nothing lest they」是连词，不碰；22 处逐条看过） | 7 | 20 |
| surther → further | — | 8 |
| sully → fully（「To sully the spoyling」另看，不碰） | — | 5 |
| shal!／til! → shall／till | 1 | 3 |
| Nhen／n'hen → When／when；hom farre／great → how | 3 | 3 |
| (Ia. → (Isa.；satis fled → satisfied；days so all be → shall be | 3 | 4 |

原书误植照录（本段）：canuot、Nothiug、hononred、participiation、amay、spitits、diffeeence、mnst、drunkenenesse、sinfnlly；
原书拼法 sorow、claping、conveniant 照录。

## 第 25 轮发现的问题与全书处理（第 6 部 21:16–18，19 叶）

本段错处约 165（落表 136 条）：正文每页约 8.2，旁注 7 条照影像重录。

**页码错位（切段层 `caryl_ocr_text.py`）**：叶 717–722 的页码读坏（708 读成「708」，709 读成「702」，710 没读出，711 读成「71」…），
逐页定页码的插补把叶 717–719 判成无号（成品里只有叶锚、没有页码），叶 720–722 又错成 713–715，与真页 711–713 差 2。
看图定：叶 717–722 = pp. 708–713，叶 723 = p. 716；p.713 页底接字 Most、p.716 以「every one hath his lot」起，中间 pp. 714–715 扫描件缺，
补 `PAGE_SET`／`PAGE_GAP`（第 6 部），页上插「此页扫描件缺」说明。全书其余无页码叶锚 17 个，都是卷首献辞、序言等本不编页的叶。

文字类（新规则）：

| 类别 | 本段 | 全书命中 |
|---|---|---|
| Hom ost／Hom oft／hom est → How oft；how／too ost → oft | 8 | 4 |
| mrath(of／be／bringeth) → wrath (of…)；michedl → wicked | 2 | 5 |
| stubble／mountaines／mee before the mind → wind | 2 | 3 |
| 节首小标题 Vers N. 漏点 → Vers. N. | 2 | 4 |
| 「a Winde of Hype.bole」→ kinde of Hyperbole（p6 19-1，人工表） | — | 1 |

原书误植照录（本段）：nse、assirmes、al、distibute、eligantly、aud（两处）、notwithstandiug、bnt、wnide、becanse。

