# 卡里尔约伯记 OCR 各部：抽章实读校勘记录（old-book-ocr §4.5）

收敛判据：连续 5 个随机抽章（本书以站上一「段」为单位，一段约 20 个印本页；一整章动辄 100–480 页）每页错误 < 1 处。
任何一段 ≥ 1，计数清零。每页图只读一次，错处一次记完。

改正落在 `manual_fixes.tsv`（`scripts/caryl_ocr_manual.py`），流程次序：
`caryl_ocr_witness.py` → `caryl_ocr_ctx.py` → `caryl_ocr_manual.py` → `caryl_ocr_sweep.py`（全书同类清理）→ 发布。

| 轮 | 日期 | 抽中 | 底本 | 页数 | 本段错处 | 每页 | 连续达标 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-25 | 第 9 部 31:7–8（印本 pp. 356–379） | Packer 纸本 300 ppi | 24 | 约 290（落表 234 条，一条常含数处） | ≈ 12 | 0 |
| 2 | 2026-11-25 | 第 9 部 31:9–12（印本 pp. 380–423） | Packer 纸本 300 ppi | 44 | 约 478（落表 370 条） | ≈ 11 | 0 |

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
