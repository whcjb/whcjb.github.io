# hodge-ephesians 诊断笔记（Step 1）

日期 2026-09-30 · 源 `~/Documents/论文/hodge/hodge_ephesians_ages.pdf`
下载自 https://media.sabda.org/alkitab-10/LIBRARY/COMMENT/HOD_EPHE.PDF
（AGES Digital Library 镜像；与 1cor / 2cor / romans 同一批，见
`docs/ages-library-survey.md`。镜像限速 ~300 B/s，755KB 拉了约 25 分钟，
必须 `--http1.1` + `-C -` 续传重试，默认 HTTP/2 会反复断在半路）

本次诊断由 `scripts/diagnose_ages_pdf.py` 生成（原始输出 `diagnose_raw.txt`），
该脚本先在 romans / 1cor / 2cor 三本已发布的书上回归过，四项配置（skip_pages、
stop_page、para_indent、字形基线）与既有 VOLUMES 条目逐一对上才用来诊断本书。

## 起手清单

| 项 | 值 |
|---|---|
| 页数 | 278（410×626） |
| meta | title=Hodge - Commentary on Ephesians, producer=Acrobat PDFWriter 2.0 for Macintosh, 1996/1997 |
| AGES 指纹 | 封面 "THE AGES DIGITAL LIBRARY / COMMENTARY / AN EXPOSITION OF EPHESIANS by Charles Hodge" ✓ |
| `<NNNNNN>` 经节锚点 | **0**（贺智四本都是 0，这是 Calvin-AGES 的特征，不能当贺智判据） |
| x0 分布 | **单峰 x=26**（2462 行），段首 x=44（180 行）→ 单列；x0≈198/200 那 80 行是页顶页码，不是第二列 |
| 格式判定 | `ages_phil` 单列，与 1cor / 2cor / romans 同 |
| 行内脚注号 | size 9.0 裸数字 → `inline_sup_footnotes: True` |
| 字号谱 | 12.0 正文 / 10.0 页码 / 9.0 脚注号 / 8.0 / 20.0 H1 / 16.0 H2 |

## 与 1cor / 2cor / romans 的差异（必须改配置的地方）

1. **`skip_pages` 是 `{0, 1}` 不是 `{0, 1, 2}`。**
   那三本的 p2 是纯书名页，本书的 p2 是**书名 ＋ INTRODUCTION 正文同页**
   （`An Exposition of EPHESIANS / by Charles Hodge / INTRODUCTION /
   I THE CITY OF EPHESUS / The city of Ephesus, under the Romans…`）。
   照抄 `{0,1,2}` 会把导论第一页整页丢掉。

2. **第六章的章头在源里印成 `CHAPTER Vl`**（小写字母 L 冒充罗马数字 I），
   p240。这是 AGES 数字化的错字，不是我们读错——PDF 里就是这样。
   只认 `[IVXLC]+` 的正则会漏掉整章，全书变 5 章。
   诊断器已放宽到 `[IVXLClO]+` 并单独告警；**发布阶段的章头正则必须同样处理**。

3. **文末脚注区标题是 `NOTES` 不是 `FOOTNOTES`**（p270），与 romans 同、
   与 skill §7 的 `detect_fn_start_page` 默认正则不同。

4. 希腊文 2571 词，介于 2cor（2118）与 romans（4314）之间；无希伯来文
   （Gideon 字符数 0，前三本也都很少）。

## 结构

| 页 | 内容 |
|---|---|
| p0 | 封面 |
| p1 | HYPERTEXT TABLE OF CONTENTS |
| p2–p17 | INTRODUCTION（八节：I THE CITY OF EPHESUS … VIII COMMENTARIES） |
| p18–p269 | CHAPTER I–VI |
| p270–p275 | NOTES（文末集中脚注） |
| p276–p277 | PUBLISHERS NOTES / AGES 出版说明（丢） |

→ `skip_pages={0,1}`、`stop_page=276`

各章起始页：I=18　II=67　III=108　IV=136　V=192　VI=240（源里写作 `Vl`）

章内还有 `SECTION N` 分节（如 p169 `SECTION II / VERSES 17-32 — CHAPTER V 1-2`）——
注意这种行里也出现 "CHAPTER V" 字样，但它是节头不是章头，行锚定正则（`^…$`）
能正确排除，别改成非锚定匹配。

## 字形基线（Gate T 比对基准，skip_head=3 skip_tail=2）

| 特征 | ephesians | romans | 1cor | 2cor |
|---|---|---|---|---|
| bold | **1011** | 1359 | 1804 | 1321 |
| italic | **38165** | 81062 | 80326 | 63389 |
| red (#800000) | **37913** | 76439 | 80316 | 62457 |
| greek (Koine 词数) | **2571** | 4314 | 872 | 2118 |
| centered_blocks | **56** | 214 | 58 | 37 |

全书另计：blue #0000d4 19103 字符（标签蓝，与希腊文 Koine 同色，判标签必须
排除 Koine 字体）、green #006411 193 字符。

## VOLUMES 条目（已写入 scripts/calvin_extract.py）

```python
'hodge-ephesians': {
    'format': 'ages_phil',
    'inline_sup_footnotes': True,
    'para_indent': 12,          # 正文 x26 / 段首 x44（实测缩进 18，阈值取 12）
    'skip_pages': {0, 1},       # 封面 / HYPERTEXT TOC；p2 是导论正文，不能跳
    'stop_page': 276,           # p276-277 是 AGES 出版说明
    'pdf':  '/Users/yanpeifa/Documents/论文/hodge/hodge_ephesians_ages.pdf',
    'out':  os.path.join(BASE, 'hodge_raw/ephesians/hodge_ephesians_structured.txt'),
},
```
