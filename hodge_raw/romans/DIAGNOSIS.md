# hodge-romans 诊断笔记（Step 1）

日期 2026-09-03 · 源 `~/Documents/论文/hodge/hodge_romans_ages.pdf`
下载自 https://media.sabda.org/alkitab-11/LIBRARY3/HOD_ROMA.PDF
（AGES Digital Library 镜像，与 1cor/2cor 同一批，1cor 是 alkitab-11/LIBRARY3、
2cor 是 alkitab-10/LIBRARY/COMMENT，都在 media.sabda.org）

## 起手清单

| 项 | 值 |
|---|---|
| 页数 | 720（410×626） |
| meta | title=Hodge - Commentary On Romans, producer=Acrobat PDFWriter 2.0 for Macintosh, 1996/1998 |
| AGES 指纹 | 封面 "THE AGES DIGITAL LIBRARY" ✓；页尺寸 ✓；producer ✓ |
| `<NNNNNN>` 经节锚点 | **0** —— 但 1cor/2cor 也是 0，贺智这三本都没有。锚点是 Calvin-AGES 的特征，不能拿来当贺智的判据 |
| x0 分布 | **单峰 x=26**（7955 行），段首 x=44（1052 行）→ 单列，`para_indent=12`，与 1cor/2cor 实测一致 |
| x0≈198 的 201 行 | 是**页码**（y=25，页顶居中），不是第二列。单列确认，无双语 scripture 区 |
| 格式判定 | `ages_phil` 单列（同 1cor/2cor/john/acts） |

## 与 1cor/2cor 的差异（必须改配置的地方）

1. **文末脚注区标题是 `NOTES` 不是 `FOOTNOTES`**（p704）。
   skill §7 的 `detect_fn_start_page` 只认 `^FOOTNOTES$`，在本书返回 None。
   正文结束于 p703（以 `———————————` 收尾），NOTES 区 p704–717，
   条目形态：独立一行 `N.` + 随后正文（与 1cor/2cor 同）。
2. **希腊文体量大 8 倍**：Koine-Medium 4314 词（1cor 872 / 2cor 2118）。
   抽取出来是 AGES 转写码，非 Unicode：`kai< ajne>zhsen`、`qeou~`、`Pri>skillan`。
   README 记的「希腊转换吃掉 `<sty>` 标记 131 处」这个坑在本书风险成倍放大，
   Gate X 必须过。
3. **居中块 214 个**（1cor 58 / 2cor 37）：每章开头有全大写的 `CONTENTS` 提要块，
   导论还有 5 个居中小节标题。
4. 希伯来文 Gideon-Medium 仅 48 字符（1cor/2cor 也少），量小。

## 结构

| 页 | 内容 |
|---|---|
| p0 | 封面 |
| p1 | HYPERTEXT TABLE OF CONTENTS |
| p2 | 书名页（原文误印 "SAGE Software"） |
| p3–4 | PREFACE |
| p5–18 | INTRODUCTION（5 节：1.The Apostle Paul / 2.Origin and Condition of the Church at Rome / 3.Time and Place of its Composition / 4.Authenticity of the Epistle / 5.Analysis of the Epistle） |
| p19–703 | CHAPTER I–XVI（罗马数字，p19 那个是 `CHAPTER I` 无点，其余带点） |
| p704–717 | NOTES（文末集中脚注） |
| p718–719 | AGES 出版说明（丢） |

→ `skip_pages=3`、`skip_tail=2`

各章起始页：I=19 II=70 III=105 IV=161 V=203 VI=294 VII=328 VIII=381
IX=455 X=516 XI=547 XII=594 XIII=627 XIV=644 XV=667 XVI=691

## 字形基线（Gate T 的比对基准，skip_head=3 skip_tail=2）

| 特征 | romans | 1cor | 2cor |
|---|---|---|---|
| bold | **1359** | 1804 | 1321 |
| italic | **81062** | 80326 | 63389 |
| red (#800000) | **76439** | 80316 | 62457 |
| greek (Koine 词数) | **4314** | 872 | 2118 |
| centered_blocks | **214** | 58 | 37 |

行内脚注号：size 9.0 TimesNewRomanPSMT 裸数字 → `inline_sup_footnotes: True`
字号谱：12.0 正文 / 16.0 H2 / 20.0 H1 / 10.0 页码 / 9.0 脚注号
