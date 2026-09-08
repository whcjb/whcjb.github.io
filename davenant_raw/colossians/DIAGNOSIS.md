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

## 5. 待办与未决

- [ ] 行末连字（`de-/rived`、`merito-/riously`）合并
- [ ] 页眉剥离：`*Ver. N.*  EPISTLE TO THE COLOSSIANS.  <页码>`（偶页/奇页版式一致）
- [ ] 页脚脚注区分离：标记为 `*`、`†`（OCR 常读成 `+`）、`‡`（常读成 `f`）
- [ ] 希腊词按行区域重跑 `grc`
- [ ] Allport 自己的译者注与附录**必须与达文南特正文分开标注**为「英译者注（Allport）」
- [ ] 《论基督之死》另立为独立卷，不并入歌罗西书注释
