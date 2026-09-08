# 达文南特《歌罗西书注释》— Step 01 诊断

底本：**John Davenant, *An Exposition of the Epistle of St. Paul to the Colossians*,
translated by Josiah Allport, London: Hamilton, Adams & Co.; Birmingham: Beilby,
Knott and Beilby, 1831, 2 vols.**（普林斯顿神学院藏本，Internet Archive
`expositionofepis01dave` / `expositionofepis02dave`，标记 `NOT_IN_COPYRIGHT`）

拉丁原著 `Expositio epistolae D. Pauli ad Colossenses`（1627 剑桥初版，另有
1630/1639/1646 重印；archive.org `expositioepistol00dave` 为 1630 版）**不作底本，
仅作对照**：17 世纪对开本的长 ſ、连字与缩写符号，tesseract 拉丁 OCR 错误率过高，
且没有第二语种可交叉校验。Allport 本是英语改革宗引用达文南特的标准本。

## 1. 起手 5 条 checklist

- [x] PDF 路径已知：`davenant_raw/colossians/expositionofepis0{1,2}dave.pdf`（39M / 37M）
- [x] 格式分类：**扫描件 + OCR 层**，不是 AGES 电子排版，也不是 CCEL
- [ ] 已有 volume entry：**无**，尚未进 `calvin_extract.py` 的 `VOLUMES`
      （本卷不走 `extract_ages_phil`，见 §4）
- [x] 目标产物：`davenant/colossians-en/`（英文）+ `davenant/colossians/`（中译）
- [x] 字形基线：**取不到**，见 §3——这是本卷与既有各卷最大的不同

## 2. 实测数据

| 项 | vol 1 | vol 2 |
|---|---|---|
| 扫描页数 | 648 | 622 |
| 页面尺寸 | 逐页不同（如 266×452） | 逐页不同（如 326×564） |
| 自带文本层 | IA 的 tesseract 层，字体一律 `GlyphLessFont` | 同 |
| 前 60 页文本量 | 136,133 字符（近空页 10） | 125,086（近空页 10） |
| 含 `Ver. N` 页眉的页 | 218 | 119 |

### 结构边界（0-based 扫描页号）

**vol 1**
```
p0–83    扫描封面 / 书名页 / 献辞 / Allport《Life of Bishop Davenant》
p84      CORRIGENDA ET EMENDATA
p86      正文起：AN EXPOSITION OF THE EPISTLE OF ST. PAUL TO THE COLOSSIANS. CHAP. I.
p422     CHAP. II
~p631    歌罗西书 2:23 末（末页眉 Ver. 23）
p632     ADDENDA TO VOL. I
p636+    空白 / 扫描尾页
```

**vol 2**
```
p14      CHAP. III
p223     CHAP. IV
~p318    注释正文结束（末页眉 Ver. 18）
p320     半题页：A DISSERTATION ON THE DEATH OF CHRIST, AS TO ITS EXTENT
         AND SPECIAL BENEFITS: CONTAINING A SHORT HISTORY OF PELAGIANISM…
p322     「KIND READER」序（Allport）
p326     该论文正文起 CHAP. I，至 CHAPTER VII（p522）+ 附录
```

→ **歌罗西书注释正文 ≈ 851 页**（vol1 p86–631 = 546 + vol2 p14–318 = 305）。
vol2 后半的《论基督之死》是**另一部独立著作**（达文南特论基督之死范围的名篇，
假设普救论的经典文献），约 300 页，**不并入本卷**，日后另立。

## 3. ⚠️ 字形信息不可恢复（本卷的核心制约）

IA 自带层是 `GlyphLessFont` 隐形文本，**没有任何字体/字号/斜体信息**。
重新 OCR 也拿不到：tesseract 5.5.2 加 `-c hocr_font_info=1` 在样本页
（vol1 p88，453 词）识别出的 `<em>` 斜体数为 **0**。

而本书的斜体承担三种实义（见 vol1 p120 页样，已核原图）：

1. **被注释的词句（lemma）**：`*And from the Lord Jesus Christ*.]` —— 斜体 + `]`
2. **圣经引语**：`*How much more shall your Father who is in heaven give good
   things to them that ask him?*` 后接出处 `Matth. vii. 11.`
3. **拉丁词句与强调**：`De Pauli laudibus`、`viz. *God.*`

其中 1 **可由结构恢复**——lemma 一律以 `]` 收尾，这是全书统一的排版约定，
是机器可判的锚点，且正好用作经节/短语级 anchor（相当于其他卷的
`commentary-anchor`）。2、3 只能靠内容推断，按 principles §0.3 属于
「拿内容猜字形」，**不做**。

**结论（发布策略，除用户另行指定）**：
- lemma 走结构恢复，渲染为主题色粗体 + 锚点
- 圣经引语与拉丁词句**不加斜体/红色**，保持平文
- 因此本卷**不适用 Gate T**（字形普查）——源侧根本数不出 bold/italic/red。
  忠于底本的检查改为 Gate X 一条：正文字符流与「IA 自带层 + 重新 OCR」
  两路交叉比对。

## 4. OCR 方案

`scripts/ocr_davenant.py`：PyMuPDF 渲 400 dpi 灰度 → tesseract `-l eng+lat --psm 6`。
单页约 1.9 s，6 workers；8 核机器上两卷**不并发**（vol1 跑完再排 vol2）。

- **语言包不要加 `grc`**：实测会把小型大写页眉 `Ver. 3.` 读成希腊字母 `Ρεν, 8.`。
  本书希腊词零散（如 `ἀποστέλλειν` 被 eng+lat 读成 `azocrenciv`），
  留待单独一遍按行区域重跑 `grc`，或标注保留。
- 与 IA 自带层的质量对比（英文词典非词率，样本 4 页）：

  | 页 | IA 层 | 重新 OCR |
  |---|---|---|
  | 88 | 21.8% | 21.6% |
  | 120 | 14.8% | **12.5%** |
  | 200 | 15.9% | **14.6%** |
  | 300 | 18.6% | 18.6% |

  字准提升有限（两路都是 tesseract），但重新 OCR 修掉了 IA 层的三个硬伤：
  词间双空格、小型大写塌成小写（`EPISTLE TO THE COLOSSIANS` → `to the colossians`）、
  以及 `saints` → `sai?its` 这类错字。**非词率高主要是词典问题**——
  `viz.`/`Matth.`/拉丁词/专名/行末连字都被算成错词；已核原图，
  印刷本身是清晰的 19 世纪铅印，不是模糊扫描。

## 5. Step 02 结果（scripts/extract_davenant.py）

按几何 + 行距做结构化，产物 `davenant_colossians_structured.txt`（1.87 MB / 3983 行）：

| 标签 | 数量 |
|---|---|
| `[BODY]` | 3256 |
| `[LEMMA]` | 303 |
| `[FN]` | 245 |
| `[SECTION]` | 88 |
| `[SCRIPTURE]` | 84（与 KJV 对不上、按正文留存的 5） |
| `[H1]` | 4（歌罗西书 4 章齐） |
| `[TITLE]` | 3（卷首书名块） |

三个判据都是实测校准、不硬编码，且各自踩过坑（代码里都写了反例）：

1. **脚注区按行距分，不按字号。** tesseract 的 `x_size` 逐行噪声太大——
   同页正文能从 37 跳到 46（vol2 是 48–58）。按字号做全局阈值两卷都翻车：
   vol1 阈值被正文簇内部的局部峰带到 40.5，vol2 把 p14 一整页普通正文
   （48–51）判成脚注（「89 页有脚注」全是假阳性）。改用「注区上方那道
   ≥1.5 倍行距的分隔空隙 + 其后紧跟脚注符 + 区内行距确实偏小」，三个信号
   互为守卫。参考行距取**页顶**前 8 行——p88 整页大半是脚注，全页中位数
   已落在脚注一侧。
2. **参考行距/缩进阈值按卷校准。** 两卷页面物理尺寸不同（266×452 vs
   326×564 pt）而渲图是固定 400 dpi，vol2 的像素尺度是 vol1 的 1.27 倍。
3. **经文块边界靠 KJV 对齐**，不靠启发式；对齐相似度顺带成为 Gate S。

### Gate（本卷专用，见 §3 为何不适用 Gate T）

    Gate W 零丢失   产物 319,772 词 / 应有 319,753 词
                    缺 79 · 多 98（0.03%），全部是行末连字在段落边界上的
                    并/不并差异，非内容丢失
    Gate S 经文     84 条经文块，9 条相似度 < 0.8 —— 逐条看过，都是达文南特
                    在释经前**再次短引**该节（`When Christ who is our life
                    shall appear, then`），不是提取错误；每节组的首个经文块
                    相似度中位数 0.99

## 6. Step 03 发布（scripts/publish_davenant_en.py）

输出 `davenant/colossians/{1,2,3,4}.md` + `index.html`，layout 两个新建：
`davenant-chapter.html` / `davenant-book.html`（每本书独立样式，不复用别家）。

- **主题色橄榄绿 `#556b2f`**（深端 `#3f5122`）：与既有六色的 CIELAB ΔE
  最小 29.0（最近的是欧文绿）。同批算过的 `#12525c`(16.6) /
  `#2f6b6b`(12.2) / `#3d5a3d`(11.9) 都离欧文绿太近，弃用。
- **发布路径用 `davenant/colossians/` 而非 `colossians-en/`**：本作者
  原生语种是英文（`PRIMARY_LANG['davenant'] = 'en'`），与贺智/欧文/曼顿
  一致，中译日后进 `zh/` 子路径。用 `-en` 后缀会被
  `build_commentaries_index.py` 的 `SKIP(-en$)` 跳过，「历代解经」里出不来
  （实测「约翰·达文南特 0 卷」）。
- **脚注按页配对**：本书脚注符是每页重置的 `*` / `†` / `‡`，不是全书连号。
  `†` `‡` 在 OCR 里常被读成 `+` `f` `t` `J` `I`，后三个会粘在词尾
  （`Thomasf`）无法可靠切出，所以只配 `*` 与 `+` 两种：207 条注中
  **174 条**做了行内引用，其余仍输出定义、只是没有行内链接。
- **经文块里的节号必须转成 HTML 粗体**：不转的话行首 `1. Paul, an Apostle…`
  会被 kramdown 当有序列表，整段经文渲染成 `<ol><li>`（实测）。

各章：ch1 1334 段 / 110 注，ch2 744 / 24，ch3 928 / 28，ch4 530 / 12；
经文块 27 + 20 + 21 + 16 = 84（= 结构化里的 SCRIPTURE 数），节号锚点 96。

## 7. 待办与未决

- [x] 行末连字合并（跨页也合）
- [x] 页眉剥离（两种版式，共剥 737 页）
- [x] 页脚脚注区分离（184 页 / 245 条）
- [ ] 仍有 29 行脚注残留在 `[BODY]`（0.9%）：这些页注区上方既无分隔空隙、
      行距也与正文无异，三条守卫都不触发。待逐页对图人工点掉
- [ ] `[SCRIPTURE]` 有 5 处与 KJV 对不上、按正文留着，待人工核对
- [ ] OCR 粘字：`Ishall` / `Itis` / `fulin` 一类（缺空格），需词典辅助切分
- [ ] 经文块里偶有页码渗入（歌 1:2 的 `which are at 5 Colosse`）。既然
      经文已与 KJV 对齐，可据此定点剔除孤立数字，尚未做
- [ ] 希腊词按行区域重跑 `grc`
- [ ] Allport 自己的译者注与附录**必须与达文南特正文分开标注**为「英译者注（Allport）」
- [ ] 《论基督之死》另立为独立卷，不并入歌罗西书注释

## 8. Step 03 格式校核：抽样对照扫描原书

**做法**：从 850 页正文里抽 9 页渲染成图逐段对读（vol1 p120/p130/p195/p200/
p300/p422/p520/p600，vol2 p14/p100/p150/p223/p318），再把每一类问题写成
全书量表跑一遍。抽样的目的不是找 OCR 错字，是看**版面还原**离原书有多远。

### 结论：结构层面对得上，此前的差距集中在五类机械性错误

段落起讫、lemma 位置、节组标题、经文块位置、脚注归属，抽样页与原书**逐段吻合**。
差距全部出在版面碎片和几何阈值上，已定位并修掉：

| 类别 | 修前 | 修后 | 病灶 |
|---|---|---|---|
| 页眉整行拼进正文 | 77 处 | 0 | 页眉正则去卡 `Ver. N.`，OCR 读成 `Vers`/`Verne`/`Ven`/`Ver. M.` 全漏；改认中间那句全大写书名 |
| 页脚签名拼进正文 | 14 处 | 0 | `VOL. I. Mm`/`Vel. 1. NR` 这类 JUNK_RE 认不全；改用 `is_foot()` 只对末两行判 |
| 段落被腰斩 | 90 处 | 46 | 扫描件歪斜，x0 一页内漂 32px > 缩进阈值 24；基线由「整页众数」改成「最近 5 行续行中位数」 |
| lemma 漏检 | 47 处 | 0 | `]` 被 OCR 读成 `\|` 或 `)`；放开变体 + 三道守卫挡假阳（lemma 共 327 条） |
| 经文块被腰斩 | 11 处 | 0 | SECTION 分支单段硬切，相似度 0.60 也过 0.55 门槛；改为一律走贪心增长 |

另外修掉的：

- **卷号缺失导致脚注串卷**：两卷扫描页号区间重叠（vol1 86-631、vol2 14-317），
  页码标记只写 `<!--pN-->`，3/4 章会去抢 1/2 章的注（144 条落在共用桶，
  实测 6 条真配串了）。标记改为 `<!--v1p93-->`，配对 key 带卷号。
- **vol2 尾页 off-by-one**：p318 是《论基督之死》的半标题页，4 章末尾因此
  多出 `FINIS. A DISSERTATION DEATH OF CHRIST`。范围改 14-317。
- **注被整条丢掉**：kramdown 只渲染被引用到的定义，没配上行内引用的注等于
  没出——207 条只出了 174 条。现在没配上的挂在该页最后一段段尾，
  277 条全部出（160 条原位、117 条段尾兜底）。
- **跨页长注的续页**：Allport 的传记体长注常连着三四页，续页顶上没有脚注符，
  三条守卫全不触发，整段注文拼进正文（29 页）。补了两条几何兜底
  （无符时门槛更硬：空隙 ≥1.5 倍行距 + 注区行距 <0.88 倍；单行短注看字号）。
  识别到的脚注页 184 → 239，注 245 → 335 条，仍漏 1 页。
- **经文块里的断词**：经文是悬挂缩进，每行都判成段首，行末连字没走 dehyph，
  留下 `spiri- tual` / `be- ginning`（19 处）。段间改用 dehyph 拼接。

零丢失核对（Gate W）：产物 319,035 词 / 应有 319,055 词，缺 89 多 69，
差额全是连字合并处两侧记法不同（`re`+`vealed` vs `revealed`），非丢字。

### 仍在的差距（本步不动，性质是 OCR 而非版面）

- **斜体不还原**：原书的圣经引语、拉丁词句一律斜体，抽样页上一次能占十来行
  （如 vol1 p120 引 Ephes. i. 3,4 那一段）。按 §3 的判断这属于「拿内容猜字形」，
  维持平文。lemma 是唯一还原的一种（有 `]` 这个机器可判的锚点）。
- **OCR 错字**：`Ishall`（缺空格）、`Pau/`、`Sau!`、`thé`、`1l.`、
  引用误读（`Ephes. i. 3, 4` → `Ephes. 1. 2, 4`）、段首编号误读
  （vol1 p600 的 `2.` 读成 `9.`，于是 1/9/3/4）。这些要另起一轮词典 + 引用
  校核，不在版面这一步。
- **117 条脚注只精确到页**：正文里那个符号被 OCR 吃了或粘进了词里
  （`Thomasf`），无法定位到句中，挂在该页末段段尾。
- **经文块 3 处与 KJV 相似度 <0.8**：核图确认**是原书如此**——达文南特
  只印半节加 `&c.`（歌 1:9-11 印到 “spiritual understanding; &c.” 为止），
  或用自己的译法（歌 4:2 的 “or, apply with all earnestness”）。不是缺字。
