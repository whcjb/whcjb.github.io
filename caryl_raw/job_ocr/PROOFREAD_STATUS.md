# 卡里尔约伯记 OCR 各部：抽章实读校勘记录（old-book-ocr §4.5）

收敛判据：连续 5 个随机抽章（本书以站上一「段」为单位，一段约 20 个印本页；一整章动辄 100–480 页）每页错误 < 1 处。
任何一段 ≥ 1，计数清零。每页图只读一次，错处一次记完。

改正落在 `manual_fixes.tsv`（`scripts/caryl_ocr_manual.py`），流程次序：
`caryl_ocr_witness.py` → `caryl_ocr_ctx.py` → `caryl_ocr_manual.py` → `caryl_ocr_sweep.py`（全书同类清理）→ 发布。

| 轮 | 日期 | 抽中 | 底本 | 页数 | 本段错处 | 每页 | 连续达标 |
|---|---|---|---|---|---|---|---|
| 1 | 2026-11-25 | 第 9 部 31:7–8（印本 pp. 356–379） | Packer 纸本 300 ppi | 24 | 约 290（落表 234 条，一条常含数处） | ≈ 12 | 0 |

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
