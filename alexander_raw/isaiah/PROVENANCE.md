# 亚历山大《以赛亚书注释》——底本与处理链

## 著作

Joseph Addison Alexander（1809–1860）的成名作，分两卷出版：

| 卷 | 书名 | 年份 | 范围 |
|---|---|---|---|
| 一 | *The Earlier Prophecies of Isaiah* | 1846 | 第 1–39 章 |
| 二 | *The Later Prophecies of Isaiah* | 1847 | 第 40–66 章 |

均由纽约与伦敦 Wiley and Putnam 印行。两卷各有自己的序与导论；卷二的导论
专门处理第 40–66 章的 *genuineness*（真伪）之争。

## 底本

| | |
|---|---|
| 卷一 | Internet Archive `propheciesisaiah01alexuoft`（744 扫描页） |
| 卷二 | Internet Archive `propheciesisaiah02alexuoft`（558 扫描页） |
| 藏本 | 多伦多 Knox College，Caven Library |
| 校对 PDF | `~/Documents/论文/alexander/propheciesisaiah0{1,2}alexuoft.pdf` |

**为什么是这一对**：同一部书在 IA 上有十来份不同馆藏的扫描件。逐份把
`_djvu.txt` 拿判词典量了一遍错词率，取各自最低的：

```
卷二  propheciesisaiah02alexuoft  2.83%   ← 选用
      laterprophecieso184700alex  2.88%
      laterprophecies00alexgoog   3.48%
      laterprophecieso02alex      4.06%
卷一  propheciesisaiah01alexuoft  4.22%   ← 选用（39 个章题一次全中）
      earlierprophecie00alexrich  4.23%
      earlierprophecie187600alex  4.30%
      earlierprophecie00alex      4.57%
其他  propheciesofisai01alex      5.33%（1865 Scribner 重排本，反而更差，弃用）
```

一并核过章首：卷一 uoft 的 39 个章首里只有第 1 章的小型大写被读崩
（`THE fteJ£n`），一处，人工改掉；其余各卷章首都干净。
Kregel 1992 年的单卷影印本（`commentaryonisai0000alex`）是借阅受限件，
且没有 ABBYY XML，用不了。

**不收录**：卷一 p731 起的出版社书目广告。

## 版面

```
卷一  p7 扉页 · p9–14 序 · p15–77 导论 · p79–730 正文（书页 1–652）
卷二  p7 扉页 · p9–10 序 · p11–46 导论 · p47–547 正文（书页 1–501）
```

页眉三种形态，判据各不相同（`scripts/extract_alexander_isaiah.py:is_runhead`）：

| 形态 | 判法 |
|---|---|
| `xxn INTRODUCTION.` / `I N T R O D U 0 T I O N.` / `P 11 E F A C E.` | 字母被逐个拆开还会漏字母，只能按关键词相似度判 |
| `2 ISAIAH, CHAP. I.`（卷一） | 带书名，**不要求页码**——OCR 常把页码整个吞掉 |
| `2 CHAPTER XL.`（卷二） | 与章题只差一个页码，**必须要求页码**，否则连章题一起删 |

## 处理链

与《诗篇注释》共用 `scripts/alexander_common.py`，只有页眉/章题/节号三处
正则不同：

```
propheciesisaiah0{1,2}alexuoft_abbyy.gz
        │  alexander_abbyy.parse_pages      斜体、断词接缝、段落属性
        ▼  pages_v{1,2}.pkl
        │  extract_alexander_isaiah.py      剥页眉 → 定章题 → 合段 → 清理
        ▼  en_chapters/{preface,introduction,later-preface,later-introduction,1..66}.md
        │  repair_alexander_ocr.py isaiah   字形规则 + 判词典 + 语料自证
        ▼  （就地修复；改动全量记在 logs/alexander_isaiah_ocr_repair.tsv）
        │  publish_alexander_en.py isaiah   front matter + 节号锚点 + index.html
        ▼  alexander/isaiah/*.md
```

## 三处与诗篇不同的地方

**节号是 `V. 7.`**，不是裸数字，而且只有一套编号（诗篇因希伯来文与英文
的题注计法不同，会出现 `7 (6).`）。发布时统一渲染成带锚点的数字，
与站内其他注释和 verse-nav 胶囊一致。

**章题是罗马数字**，`CHAPTER XIII.`。找章题不能用前缀匹配——XII 是 XIII 的
前缀，第 12 章会定位到第 13 章的标题上，往后 27 章全部找不到；也不能只认
整串相等——`CHAPTER XI.` 被读成 `CHAPTER XL`（`I.` 粘成 `L`），第 11 章
就是这么丢的。最后的判据是「整串相等，或**等长且只差一个字符**」。

**合并解题**。原书在第 2–4 章、13–14 章、15–16 章之前各有一段合并的解题
（`CHAPTERS II, III, IV.`），讲这一组预言的整体结构。它属于后面那一组的
第一章，不特别处理会被并到**上一章**的尾巴上。已归位到第 2、13、15 章开头。

## 断词与复合词

行末断词的连字符 OCR 时有时无。有连字符的在抽取阶段接好；没有的靠判词典
在修复阶段补（`rejoin_split_words`，只在两半至少有一半不是词时才拼，
`to be`、19 世纪本来就分写的 `any thing` 一律不动）。

反过来，`well-watered`、`burnt-offering`、`twenty-second` 这类**原书本来
就带连字符**的复合词也会正好断在连字符上，删掉连字符就错了。抽取时在接缝
处留标记，再拿全书**行内**出现过的复合词表来定夺
（`alexander_common.resolve_hyphens`）。这条是另一个会话在诗篇里查出 8 处
`wellwatered` 之后补的，两本书共用。

## 完整性核验

按章比对「切片后的源字符数」与「抽取产物字符数」（只数字母与数字，不受
空格、连字符、斜体标记影响）：66 章合计**相差 0 个字符**。

## OCR 修复的账目

```
规则修复 264 · w 形翻案 114 · 罗马数字 6 · 真词 6 · 存疑未动 9813 · 过短未动 1609
```

存疑未动占全书 63.6 万词的 1.7%，绝大多数是希伯来活字读崩后的两三字母
残渣（`ns` `bs` `Hn` `nx` `bx`）、拉丁引文与德国注释家的人名，本来就不该动。

## 还能做而未做的

- **第二证人判读**。诗篇那边用 1850 三卷本当第二证人，按位置锚定把
  「存疑未动」清掉了 862 处（`scripts/adjudicate_alexander_ocr.py`）。
  以赛亚书的条件更好——IA 上有**八份以上**不同馆藏的独立扫描件可当证人，
  多数表决比单证人更硬。这条没做。
- **中译**。全书无中译本，站内也未翻译。
- 经文索引（verse-index）。
