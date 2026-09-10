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

规则阶段（`repair_alexander_ocr.py isaiah`）：

```
规则 264 · w 形翻案 114 · 罗马数字 6 · 真词 6 · 存疑未动 9803 · 过短未动 1609
```

## 多证人判读

规则阶段剩下的「存疑未动」不是规则不够，是**证据不够**。以赛亚书在这一点上
条件特别好：同一部 1846/47 年版，IA 上有多家馆藏各自扫的独立副本，OCR 错法
互不相关，可以**多数表决**——比诗篇只有一个 1850 三卷本硬得多。

`scripts/adjudicate_alexander_isaiah.py`（工具函数复用诗篇那份
`adjudicate_alexander_ocr.py`）拿卷一 4 份、卷二 5 份证人，按前后各三词的
位置锚读出证人在同一位置印的是什么，至少两份一致才采信。落案：

```
非词改正 540 · 真词改正 105 · 人工核定 40 · 已核实原样 5003
证据不足 2209 · 无证据 3146 · 真词分歧待看 405
```

（真词那一路换严锚之后数字有升有降：证据不足变多是因为门槛提高，
真词分歧待看变少是因为页眉清干净后锚更容易对上。）

**真词改正**是这一轮最要紧的收获：`lime`→`time`、`lake`→`take`、
`bouse`→`house`、`Jiffy`→`fifty`、`Icings`→`kings`、`faying`→`saying`、
`smiling`→`smiting`（赛 66:3）、`leaching`→`teaching`（赛 48:17）——
这些错完之后**仍是合法英文词**，判词典与语料自证都看不见，只有拿另一份
原文按位置比对才查得出来。

判读器**只在证据压倒时才动真词**：全体证人一致、至少三份、且证人读数在
本书里比我们这串常见 20 倍以上。`mere`/`more`、`his`/`this` 这种两边都常用
的对子分不清是错字还是异文，一律留在「待看」里不动。

## 跨页吞词

判读器是逐 token 比对，看不见「少了一个词」。另做了一遍跨页审计：凡段落在
翻页处断开且句子没说完的，拿证人补出中间夹着什么。全书 54 处里 53 处夹的
只是证人自己的页眉（说明我们没丢东西），**只有一处真丢了词**——第 8 章
"the only case which has been ⟨cited⟩ to establish"，四份证人一致，已补回。

同一轮还发现 ABBYY 会给跨页续段误加 startIndent，把一句话劈成两段
（以赛亚书 76 处、诗篇 11 处）。已在 `alexander_common.merge` 里用内容信号
压过几何信号：上一段以小写字母或逗号收尾就是没说完，不另起段。

## 影像逐页排查

多证人也救不了两类：几份证人在同一处都读崩的，以及**证人自己也印着页眉**
的地方。这两类只能翻页面影像。`scripts/crop_alexander_isaiah.py` 按书页
渲染 PDF；**优先用 `--find "一句话"`**——正文里的 `<!-- PAGE n -->` 标的是
段落起始页，长段跨两三页，按它翻常翻错；`--find` 直接拿那句话去 PDF 文本层
搜（文本层与 en_chapters 同出一份 ABBYY OCR，同一串字一模一样）。

翻影像翻出来的，都不是自动化能发现的：

| 现象 | 页面上是 | 我们原来是 |
|---|---|---|
| 页码掉进正文 | `…explanation of` ⏎ `406` ⏎ `the phrase…` | `…explanation of 406 the phrase…` |
| 页码把断词撑开 | `circum-` ⏎ `26` ⏎ `locution` | `circum- 26 locution` |
| 页眉混进段落 | `…can` ⏎ `8 CHAPTER XL.` ⏎ `be fully…` | `…can g CHAPTERXL. be fully…` |
| 德文变音符 | `Rosenmüller` | `Rosenmiiller` |
| 断词漏连字符 | `Ven-ice` / `wea-pons` | `Ven ice` / `wea pons` |

**还翻出一处自动判读改错的**：第 34 章「the gratuitous **assertion** that」，
四份证人一致给出 assumption，照办就把原文改错了。原因是锚撞车——书里别处
有「by the gratuitous assumption that」，`look_up` 只校验右侧一个词，四词
上下文对常见句式不够。真词那一路因此改用两侧各三词的严锚
（`look_up_strict`），改动数从 116 降到 105，那一处也自动放过了。

**教训：多证人一致也可能是错的。** 动真词之前，能翻影像就翻。

## 撇号：可能是空格，也可能是字形误读

`explanations'of` 这类是**空格被读成撇号**，不修的话判读器只认得出前半那个
token，照证人补全会把后半整个吞掉（本书 4 处）。修在 repair 阶段
（`split_apostrophe_gap`）。

但同一个形状也可能是**字形误读**：诗篇那份 1864 扫描件里 `r` 常被读成 `i'`，
`fi'om`=from、`gi'eat`=great，而 `fi`/`om`/`gi`/`eat` 碰巧全在韦氏词表里，
「两半都是词」这条判据会把它们拆成 `fi om`——比原来坏得多（诗篇 48 处里
43 处是这一类，另一个会话查出来的）。

所以函数里串了两道判据：**字形规则表能给出解**、或**撇号直接删掉就成词**
（`off'ering`=offering），都判为误读，不拆。

以赛亚书这边不吃这一类——本书的 `i'` 全是希伯来活字残渣（`hi'n`、`rrni'ti`、
`s'li'a`）与真正的所有格（`Kimchi's`、`Jarchi's`），两半不同时是英文词。
但**这条规则的安全性依赖于书卷的错误谱，换一本书必须重新量**。
加上判据后本书 24 处拆、11 处挡。

被挡下的 11 处里，5 处是希伯来残渣（该挡），6 处是前半只有两字母的真空格
（`of'the`、`it'as`）——它们不必损失：repair 阶段只能靠「两半都是词」判断，
为安全用长度兜底；判读阶段有**位置证据**，证人在同一位置读出的就是前半截
（`of'the` 的读数是 `of`，而 `ni'aa` 的读数不会是 `ni`），残渣自动落不进来。
判读器因此加了 `splitq` 一路（做法来自诗篇线），把这 6 处连同 `of'Jehovah's`
一起捡了回来。

**推论，值得单独记住**：凡是排在 token 阶段**之前**的文本级规则，下结论前
都该先问一句「字形规则表对这个串有没有解」。`split_apostrophe_gap` 跑在
token 阶段之前，本卷 RULES 里虽有 `("i'", 'r')`，规则还没来得及修就已经被
拆坏了——把 token 阶段的判断力提前借到 PRE 阶段，顺序问题一并解决。

## 复现顺序

判读是落在**已发布产物**上的，所以重跑 publish 之后必须补跑判读：

```
python3 scripts/extract_alexander_isaiah.py
python3 scripts/repair_alexander_ocr.py isaiah
python3 scripts/publish_alexander_en.py isaiah
python3 scripts/adjudicate_alexander_isaiah.py --apply   # 跑到不再有改动为止
```

判读器是幂等的，改到收敛要三四轮（改掉一个词会让邻近位置的锚重新对上）。

## 还能做而未做的

- **中译**。全书无中译本，站内也未翻译。
- 经文索引（verse-index）。
- 「真词分歧待看」还剩 610 条，多是两版异文与撇号残渣，值得再人工过一遍。
