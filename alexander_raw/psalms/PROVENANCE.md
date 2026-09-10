# 亚历山大《诗篇注释》——底本与处理链

## 著者与著作

Joseph Addison Alexander（1809–1860），普林斯顿神学院首任教授 Archibald
Alexander 的第三子。1826 年以第一名毕业于新泽西学院，1834 年入神学院任
Charles Hodge 的助手，1840 年接任霍智的东方与圣经文学讲席，1851 年转圣经与
教会史，1859 年转新约文学，次年病逝。

《诗篇注释》1850 年初版，三卷。他在序言里自述，此书本是从翻译 Hengstenberg
《诗篇注释》起意的，动手后发现删改不如另写，遂成独立著作。

## 底本

| | |
|---|---|
| 主底本 | Internet Archive `commentaryonpsal00alex` |
| 版次 | 1864 年 Scribner 单卷修订版（Kregel 1991 影印重排） |
| 页数 | 590（扫描页序号） |
| 正文范围 | p22–p577 |
| 著者序 | p14–p21 |
| 第二证人 | `psalmstranslated01alex` / `02alex` / `03alex`（1850 年 Presbyterian Board 三卷本，第六版），抽取产物在 `chapters_raw/` |
| 校对用 PDF | `~/Documents/论文/alexander/psalms_1864_kregel.pdf`（同一 item 的 PDF 只有 584 页，与 XML 的 590 页**本身就错位**，别拿页序号互相套）|

**为什么用 1864 单卷本而不是 1850 三卷本**：同一部书，1864 版扫描字号大、
ABBYY 误识率低一个数量级；篇题已是阿拉伯数字 `Psalm 1`，不必跟罗马数字的
OCR 变体缠斗；且 150 篇在一卷里，不必处理跨卷拼接。1850 三卷本留作第二证人。

**不收录的部分**：p12–13 是 Kregel 1991 年新写的 FOREWORD，版权在世；
p578 起是出版社书目广告。两者都不在公有领域文本之内，一律不取。

## 处理链

```
commentaryonpsal00alex_abbyy.gz          IA 的 ABBYY FineReader XML
        │
        │  scripts/alexander_abbyy.py     page/block/par/line/formatting 解析
        │                                 —— **斜体从这里来**
        ▼
   pages1864.pkl
        │
        │  scripts/extract_alexander_psalms.py
        │    · 剥页眉页脚（'570 Psalm 149:1 - 6' 及其 OCR 变体）
        │    · 按 par 的 startIndent 判新段 / 续段，合并跨页断段
        │    · 斜体哨兵 → markdown `*…*`，修边界空白与相邻段合并
        ▼
alexander_raw/psalms/en_chapters/{preface,1..150}.md
        │
        │  scripts/repair_alexander_ocr.py  字形规则 + 判词典 + 语料自证
        ▼
   （同目录，就地修复；改动全量记在 logs/alexander_ocr_repair.tsv）
        │
        │  scripts/publish_alexander_en.py  front matter + 节号锚点 + index.html
        ▼
alexander/psalms/{preface,1..150}.md
```

`en_chapters.bak/` 是 extract 之后、repair 之前的快照，调修复规则时用来回到
干净起点。它不进库（重跑 extract 约 30 秒即可再生），但**本地别删**——
repair 是就地改写，没有它每调一次规则都要重跑整条链。

## 为什么斜体是这本书的命根子

Alexander 的体例是**夹译夹注**：他自己对希伯来文的译文用斜体，紧接着的
解说用正体，两者在同一段里交替。丢掉斜体，读者无法分辨哪句是经文哪句是
注释——所以纯文本的 `_djvu.txt` 不可用，必须走带 `italic` 属性的 ABBYY XML。

原书**没有独立经文块，也没有脚注**。不得自作主张把斜体抽出来做成经文框。

## OCR 修复的边界

这份扫描件的错误高度成套，几乎全是连字与相似字形被拆错：

| 原字 | 被读成 | 例 |
|---|---|---|
| `li` | `U` / `H` / `h` | appUed · Hterally · hke |
| `ll` | `U` | aU · wiU |
| `ff` | `fi` / `flf` | efiect · scoflfers |
| `rn` | `m`（及反向） | modem(modern) · scomers(scorners) |
| `w` | `iv` / `vn` / `ui` / `tv` | ivith · vnth · uill · tvill |
| `r` | `i'` | fii'st · wi'iters |

修复流程三道闸，缺一不可：

1. **字形规则**穷举 1–2 次替换的候选；
2. **判词典**（`scripts/alexander_lexicon.py`）只放行落进词典的候选——
   这条保证 `shews` / `connexion` 这类 19 世纪拼法不会被「改正」成现代拼法；
3. **语料自证**要求候选在全书别处确实以正确形态出现过——
   这条拦住 `hang → liang`、`lieth → heth` 这种「换完仍是英文词」的错改。

三道闸都过不去的一律**原样保留**并记账，绝不猜。最后一轮的账目：

```
规则修复 1626 · 罗马数字 910 · 人工核定 103 · 真词错误 34
存疑未动 2383 · 过短未动 355
```

存疑未动的 2383 个 token 占全书 35 万词的 0.68%，绝大多数是专名、
希伯来文音译与拉丁术语，本来就不该动。逐条改动见
`logs/alexander_ocr_repair.tsv`。

三字母 token 单独设一道更高的门槛（语料里出现 20 次以上才放行）：
它们证据太薄，一次替换就能落到好几个真词上——`thg→thig`、`oui→ow`、
`Joh→Job`（把约翰福音的缩写改成约伯记）都是这么来的。

### 字面星号

OCR 文本里自带的 `*` 会和斜体标记混在一起，让整段的强调配对从那一点起
全部反相（诗篇 107 第 4 节整段后半就是这么坏的）。它们在抽取阶段先换成
私用区哨兵，由修复阶段按上下文定夺：`*'`/`**` 还原成开引号，
`fi*om`/`ai*e` 里的星号是 `r`，句末接大写的是句号，接小写的是噪点。
判不出来的 20 处全在希伯来活字读崩的残渣里，转义成 `\*` 原样保留。

## 页码标记

正文里的 `<!-- PAGE n -->` 标的是**书页上印的页码**，不是扫描页序号。
页码从页眉里取，缺失或读崩的按前一页 +1 推，推完校验过严格递增。
每篇开头的注释两个都给：`<!-- psalm 23 | 书页 115-117 | 扫描页 120-122 -->`。

## 完整性核验

按篇逐一比对「切片后的源字符数」与「抽取产物字符数」（只数字母与数字，
不受空格、连字符、斜体标记影响）：150 篇合计相差 **2 个字符**，
且没有任何一个源段落在产物里找不到。

## 节号的两套编号

节号形如 `7 (6).`：前者是希伯来文本的节号，括号里是英文圣经的节号。诗篇的
题注（"A Psalm of David"）在希伯来文里计为第一节、英译不计，两者因此常差
一节。**站内锚点与经文索引一律取英文节号**——其他注释、和合本都按英文编号，
取希伯来节号会让同一节在不同注释之间对不上。

## 尚未做的事

- **中译**。全书无中译本，站内也尚未翻译。
- 经文索引（verse-index）尚未生成。
