# spurgeon-matthew 诊断笔记（Step 1）

日期 2026-09-30 · 源 `~/Documents/论文/spurgeon/spurgeon_matthew_ages.pdf`
下载自 https://media.sabda.org/alkitab-10/LIBRARY/COMMENT/SPU_MATT.PDF
（AGES Digital Library 镜像，1,277,720 字节；镜像限速，`--http1.1` + `-C -`
续传跑了 11 轮约 25 分钟）

**书名以扉页为准**（p1）：*The Gospel of the Kingdom — A Popular Exposition of
the Gospel according to Matthew*，作者署名 CHARLES HADDON SPURGEON。
封面另印 *A Popular Exposition to the Gospel according to Matthew*（AGES 自拟）。
p2–3 的 INTRODUCTORY NOTE 说明这是司布真临终前最后一部作品，
后半部「写于天国的边境上」。

## 起手清单

| 项 | 值 |
|---|---|
| 页数 | 511（410×626） |
| meta | title=Spurgeon - Commentary on Matthew, producer=Acrobat PDFWriter 2.0 for Macintosh, 1996/1997 |
| AGES 指纹 | 封面 "THE AGES DIGITAL LIBRARY / COMMENTARY" ✓ |
| `<NNNNNN>` 经节锚点 | 0 |
| x0 分布 | **单峰 x=26**（2130 行）。次峰 x=144 只有 9 行（0.4%），是分节头不是段首缩进 |
| 格式判定 | `ages_phil` 单列 |
| 字号谱 | 12.0 正文 / 10.0 页码 / 9.0 **小型大写的后半截**（T+HE）/ 16.0 分节头 |

## 与贺智那批的三处结构差异（都不能照抄）

1. **没有任何脚注**。文末无 FOOTNOTES/NOTES 区；9pt span 全是小型大写的后半截
   （AGES 把 `THE` 排成 size-12 `T` + size-9 `HE`），不是脚注号。
   → `inline_sup_footnotes` 必须**关**。开着会把版面里的数字标成 `[^fN]`，
   而全书没有任何 def 与之对应。

2. **正文不靠首行缩进分段**：全书顶格 x26，段落靠块间距分。
   → `para_indent` 必须 **0**。
   （诊断器原来会把 x=144 那 9 行噪声峰当段首，算出 para_indent=112 这种离谱值；
   已给次峰加「占正文行数 ≥1.5%」的门槛，贺智四本仍稳定给出 12。）

3. **分节头是 `CHAPTER 1:18-25`**（阿拉伯数字 + 经文范围，size 16 蓝 `#0000d4`），
   副标题另起一行（size 12 粗斜 绿 `#006411`，如 `THE BIRTH OF THE KING`）。
   贺智那套 `CHAPTER <罗马数字>` 在本书一次都不出现。

## 版式：经文与释经交织

这本是讲道体通俗释经，一节经文 + 一段讲解交替推进：

| 元素 | 字形 | 产物 |
|---|---|---|
| 经文节号 | size 12 粗体黑 `18.` | `**18.**` |
| 经文正文 | size 12 **粗斜体暗红** `#800000`（flags 22） | `<span style="color:#800000">***…***</span>` |
| 释经段落 | size 12 常规黑 | 普通段落 |
| 释经里的经文引语 | size 12 斜体暗红（flags 6，不加粗） | `<span style="color:#800000">*…*</span>` |

与贺智/加尔文不同：那两位的红色只是**引语标记**，这本的红色块**本身就是圣经经文**。

### 两个本书特有的提取坑（已按卷开关处理）

- **经文 span 被逐行切开**：PDF 一行一个 span，同一节经文成了
  `<sty X>…his</sty> <sty X>mother…</sty>`，转 md 后是
  `***…his** **mother…***`，星号配对全乱。
  → `merge_adjacent_styles`：相邻同属性 `<sty>` 之间只隔空白就合并。
- **两端对齐读出连空格**：`Now  the  birth  of  Jesus`，全书 23,725 处
  （贺智罗马书 0 处、以弗所书 9 处，可见是本书版式特有）。
  → `collapse_double_spaces`：只在标签之外折叠，不碰属性。

两个开关都默认关，已发布各卷的 raw 重跑后逐字节不变（以弗所书已实测）。

## 结构

| 页 | 内容 |
|---|---|
| p0 | 封面 |
| p1 | 扉页（书名 / 作者 / SAGE Software） |
| p2–p3 | INTRODUCTORY NOTE（苏珊娜·司布真署，未具名） |
| p4–p9 | TABLE OF CONTENTS（104 条） |
| p10–p508 | 正文，103 个分节，覆盖马太福音 1–28 章 |
| p509–p510 | PUBLISHERS NOTES / AGES 出版说明（丢） |

→ `skip_pages={0,1,4,5,6,7,8,9}`、`stop_page=509`

**原书自己就有的空缺**（目录与正文一致，不是我们漏抽）：
- 马太 5:13-16 无分节（5:1-12 之后直接跳到 5:17-20）
- 末节标作 `CHAPTER 28:11-15`，但正文一直讲到 28:20（16,17 与 18-20 两个经文块
  在同一节里，没有另起分节头）
- 全书最后一行是装饰符 `<> <> <> …`（dingbat 字体），不是标题

## 字形基线（Gate T 口径，skip_head=3 skip_tail=2）

| 特征 | spurgeon-matthew | 贺智以弗所（对照） |
|---|---|---|
| bold | **149,913** | 1,011 |
| italic | **205,742** | 38,165 |
| red (#800000) | **203,978** | 37,913 |
| greek | **0** | 2,571 |
| centered_blocks | **220** | 56 |

bold/italic/red 三项都比贺智高两个数量级，因为**经文正文本身是粗斜体暗红**，
占了全书近三分之一篇幅（TimesNewRomanPS-BoldItalicMT 142,095 字符）。
Gate T 比对时要留意：md 侧 `***…***` 不被 `\*\*([^*]+)\*\*` 命中，
这本书的 bold 口径需要单独确认，不能直接套贺智的读数。

## VOLUMES 条目（已写入 scripts/calvin_extract.py）

```python
'spurgeon-matthew': {
    'format': 'ages_phil',
    'inline_sup_footnotes': False,   # 本书没有脚注，9pt 是小型大写
    'para_indent': 0,                # 全书顶格，靠块间距分段
    'merge_adjacent_styles': True,   # 逐行切开的经文 span 合回一整段
    'collapse_double_spaces': True,  # 两端对齐读出的 `Now  the  birth`
    'skip_pages': {0, 1, 4, 5, 6, 7, 8, 9},   # 封面 / 扉页 / 目录 6 页
    'stop_page': 509,
    'pdf':  '/Users/yanpeifa/Documents/论文/spurgeon/spurgeon_matthew_ages.pdf',
    'out':  os.path.join(BASE, 'spurgeon_raw/matthew/spurgeon_matthew_structured.txt'),
},
```
