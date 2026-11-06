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

## 待做

1. ~~第 ① 层~~ 已完成
2. 第 ② 层：Lect. I–LXVI 用第 3 版作第二证人按位置判读
3. 经文段：钦定本同位词校正（参照 `extract_alexander_acts.py` 的 `header_fix`）
4. 发布：`foote/luke/` 独立目录与样式、经文弹层、章节 date 取真实时刻
