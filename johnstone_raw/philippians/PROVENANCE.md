# 约翰斯通《腓立比书讲疏》——底本与处理链

## 著者与著作

Robert Johnstone（罗伯特·约翰斯通，LL.B.），苏格兰联合长老会（United
Presbyterian Church）神学院教授，爱丁堡。《腓立比书讲疏：释经与实践，附修订
译文及希腊文经文注释》1875 年由爱丁堡 William Oliphant 初版，1904 年再版，
1977 年 Klock & Klock 重印一次后绝版。

体例是「讲章 + 希腊文注」：正文逐段讲解（释经在前、应用在后），每讲末尾附
一段 `NOTES` 讨论希腊文异文与词义，页脚另有小字脚注。**斜体与希腊文是这本
书的体例骨架**，丢了任何一样这本书就残了。

## 底本

| | |
|---|---|
| 主底本 | Internet Archive `lecturesexegeti00john` |
| 版次 | 1875 年 Oliphant 初版（多伦多大学 Robarts 图书馆藏本） |
| 扫描页数 | 516（`imagecount`） |
| 原图分辨率 | 1995 × 3342 px/页（约 400 dpi，足够重 OCR） |
| 页码偏移 | 印刷页 p.40 = IIIF leaf 56，**偏移 +16**（需逐段复核，前后衬页可能变） |
| 第二证人 | **没有**。全网只此一份扫描 |

### 为什么不用现成的文本

- **IA 自带的 `_djvu.txt` 不能用**：OCR 引擎是 ABBYY FineReader **8.0**（2007），
  `grep '[Ͱ-Ͽἀ-῿]'` 结果为 **0** —— 希腊文一个字符都没有，而这本书的副标题
  正是「附希腊文经文注释」。另有 `tlie/tlic/liis` 33 处、`pniycrlcss`、
  `ngonized`、`ajipeal`、`welfiire`、`imist`、`^^-ill`，`^ \ |` 噪声 1255 处。
- **AGES 没有这本**：官方目录 `alkitab-10/AGES.PDF`（18 页）全文 grep
  `Johnstone` = 0、`Philipp` = 0。腓立比书在 AGES 里只被
  `BET_NTCO`（Joseph Agar Beet《罗马书—腓利门注释》）顺带覆盖。
- **Google Books / HathiTrust / Online Books Page** 均无全视图数字版；
  Logos 有商业数字版，DRM，取不出文本。
- **biblehub 上的 "R. Johnstone, LL.B." 条目不是这本书**，是《圣经图解》
  (Biblical Illustrator) 的摘要提纲 —— 腓 2:5–11「The Great Example」全文只有
  2413 字符，而原书这一讲是十几页。

## 处理链：三条流合一

单独哪一条流都不够，必须合：

```
                         ①  ABBYY XML（IA 自带）
lecturesexegeti00john_abbyy.gz
        │   斜体 italic="true" + par.startIndent 段落结构 + 脚注块
        │   —— 字准极差，**只取版面与斜体，不取字**
        │   scripts/alexander_abbyy.py（通用，直接复用）
        ▼
                         ②  tesseract eng+grc（本地重跑）
lecturesexegeti00john_jp2.zip → scripts/johnstone_ocr.py
        │   字准好一个数量级，**但斜体为零**
        │   实测 p.40：整页 36 行只有 1 个错字（veigious ← religious）
        ▼
                         ③  tesseract grc-only（同图再跑一遍）
        │   只为希腊文。eng+grc 会把词首希腊词当拉丁字母读
        │     eng+grc : yivseds τραπεζίται δόκιμοι
        │     grc-only: γίνεσθε  τραπεζίται δόκιμοι   ← 对的
        │   英文部分在这一遍里是乱码，**只抽希腊游程回填**
        ▼
   scripts/extract_johnstone.py
        字从 ②，希腊文从 ③，斜体区间与段落边界从 ①，difflib 字符级对齐
        ▼
johnstone_raw/philippians/en_chapters/*.md
        ▼
   三道闸清残字（字形规则 / 判词典 / 语料自证）
        ⚠️ 第二证人判读这条线走不通 —— 全网只有一份扫描件。
           真词错字只能靠影像精读 + 语料自证兜。
```

## 实测对照（印刷页 p.40 脚注）

旧（IA 自带 ABBYY 8.0）：

```
>  Accordin{^  to  a  precept  ascribed  l)y  early  writers  to  our  Lord,  yUivix
rfa.xx^lra.1  ioxi/Aoi^  '  Be  yc  ajjproved  money-changers.'
```

新（本地 tesseract 5.5，eng+grc ＋ grc-only 回填）：

```
1 According to a precept ascribed by early writers to our Lord, γίνεσθε
τραπεζίται δόκιμοι, ‘Be ye approved money-changers.’
```
