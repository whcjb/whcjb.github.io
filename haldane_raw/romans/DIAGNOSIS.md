# haldane-romans 诊断笔记（AGES）

日期 2026-11-18 · 源 `~/Documents/论文/haldane/haldane_romans_ages.pdf`
下载自 https://media.sabda.org/alkitab-10/LIBRARY/COMMENT/HAL_ROMA.PDF（同件另见 alkitab-11/V6F-Z/）

| 项 | 值 |
|---|---|
| 页数 | 908（410×626），Acrobat PDFWriter 3.0.1，1998 |
| 结构 | p0 封面 · p1 TOC · p2 书名页 · **p3–4 FOREWORD（AGES 版加的现代推荐序，不收）** · p5 PREFACE · p12 INTRODUCTION · p23 EXPOSITION / CHAPTER 1 … CHAPTER 16 · p883 CONCLUSION（末印 THE END.）· p893 FOOTNOTES（ft1–ft64）· p906–907 AGES 出版说明 |
| 版面 | 单列，正文 x=26；前半本段首缩进 x=44/48，后半本不缩进 |
| 分段 | **靠段间空白**：段内行距 14–16pt，段间 22–24pt。每页首行都在 y≈55，跨页无从判断 |
| 字色 | 红斜体 #800000 = 经文（20,587 词）；蓝 #0000d4 = 大标题（24pt）与希腊文（Koine 体，47 处）；绿 #006411 = PART N. 与 THE END.；藏青粗体 #000080 = 分点（1st / 2nd / 1.，66 处）|
| 小型大写 | 段首大字母 16pt + 余字 9pt（T+HIS）；正文 12pt 中 9pt 大写（S+AUL）|
| 脚注号 | 9pt 红色升高的 `fN`；文末 `ftN.` 条目 |
| 经文锚点 | 页边 `<NNNNNN>`（6pt 红），常把一行劈成两截 |

## 为什么不用 calvin_extract.py `ages_phil`

试跑 `haldane-romans` 配置：以锚点 `<NNNNNN>` 起首的续行被判成 `[FOOTNOTE]`（1,296 处），段落碎掉；
又不宜为一本书改通用提取器（skill §11.5：重跑会伤已发布各卷）。故单写 `scripts/extract_haldane_ages.py`，
规则照 AGES skill。`calvin_extract.py` 里的配置留作记录。

## 与 StudyLight 录入本（units_studylight.json）比对

- 词多重集：全书 37.5 万词，每章差十几至几十词——录入本有几十处斜体边界吞空格的粘连词（fori / forthe），
  AGES 不粘；AGES 希腊文是转写码（已转 Unicode 并以录入本的拼写定送气 / 重音）。录入本的字 AGES 全有。
- 节头：录入本的全部条目 AGES 都有；AGES 另多出几十个录入本并掉的节头。
- **分段：录入本大量多分了段**。抽查 8 处录入本分段、AGES 不分的地方，1874 第九版扫描本（`src/scan/`，
  段间有空行）全是同一段内句子接排；只有 2 处是 AGES 漏分。故页内只认 AGES 段距，跨页以 1874 扫描本的段首为证。
- 脚注：AGES 64 条全；录入本缺正文的 7 条（22 23 34 38 56 57 58）与缺注号的 4 处（1 2 24 26）AGES 都有。

## AGES 自身的错，编者改正

- 8:5 印作 `Ver. 6.`（紧接真 Ver. 6.）→ 改 5（录入本亦作 5）。
- 5:18 δικαιώματος 漏 μ（录入本同漏，2026-11 经用户同意补）。
- 若干希腊词转写码转不对（J 粗气、w|= iota 下标、混拉丁字母）——见 extract_haldane_ages.py `GREEK_FIX`。
- 节号变体：`Ver. 27 —`（只 `Ver. 2` 粗体）、`Ver. 31:`。
- 3:27、6:6、11:30、13:12 经文与注释排成一段，按注释照例重提经文首句处断开。

## 未收

两篇专论（论外邦世界 / 论守安息日）与附录：后来版本才有（1874 第九版 pp. 653–702、713–730），AGES 版没有。
