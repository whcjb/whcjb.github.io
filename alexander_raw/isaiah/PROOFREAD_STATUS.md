# 以赛亚书正文校对进度（续做看这一份）

最后更新：2026-09-30

## 已经读完的

**全书 1153 页的印面影像都比对过了**（`scripts/isaiah_page_proofread.py`，
把页面影像与我们的正文一起送去只问「哪里对不上」）。这一遍落盘 646 处。
先前逐句实读的四篇前置件与第 1、12、40 章另计（约 150 处）。

**不必再逐章实读**——`--done` 现在就是全书。后续的错要靠**新判据**而不是
再读一遍：2026-09-30 那两轮就是这么捞出 104 处的（双标点、词距、括号配对、
引号顶词距、开斜体贴词距），每一类在读页那一遍里都没人报。

人工条目累计 **约 300 条**在 `manual_fixes.tsv`；带闸的规则在
`scripts/adjudicate_alexander_isaiah.py` 的 `MANUAL_RE` 与几个 `fix_*` 函数里。
闸子的现状看 `CHAIN_STATUS.md` 末尾那张表。

## 还剩什么

不是「还有哪几章没读」，而是「**还有哪一整类判据没写**」
（[[feedback_gates_only_see_known_types]]）。已经想到、还没写的：
斜体范围与印面是否逐字吻合（本轮影像里见到两处 `(or *driven)` 这类闭合位置
差一个字符的，量不出信噪比干净的判据，暂缓）。

## 怎么接着做

1. `Read` 一章正文（跳过 front matter），逐句读。
2. 捞到的每一处按三档定：
   - 先拿 `alexander_raw/isaiah/src/*.txt` 里另外几份 IA 扫描件比多数读法
     （`scratchpad/verify.py` 那个小工具，重写很快）；
   - 证人也跟着崩、或差在标点与变音符的，翻页面影像
     （`scripts/crop_alexander_isaiah.py --find "一句话"`，或直接 fitz 裁行）；
   - 行末断词按「拼回去是不是词」判。
3. **同一类出现三次以上就做成带闸的规则**（`MANUAL_RE` 或单独函数），
   只出现一两次的逐条进 `manual_fixes.tsv`。
4. 规则上线后**必须 diff 复核每一处改动**（跑链条前先 `cp -r alexander/isaiah` 存一份快照）。
5. `bash scripts/chain_alexander_isaiah.sh` 重跑，复扫，提交。

## 已经归纳出来的错误类型（规则都已落地）

| 类型 | 例子 | 落在哪 |
|---|---|---|
| 问号被扫成 `1` | `why continue to revolt 1*` | `fix_ocr_one` |
| 大写 I 被扫成 `1` | `*and 1 will avenge*` | `fix_ocr_one` |
| 开引号被扫成 `c`/`f`/`<` | `—c Jehovah alone`、`f full of the east wind,'` | `MANUAL_RE` |
| 节号 `§` | `&lt;§> 116. 3` | `MANUAL_RE` |
| 字母 k 被扫成 `Jc` / `Ic` | `HezeJciah`、`Icings` | `MANUAL_RE` / `fix_ic` |
| 字母 f 被扫成 `/` | `—/or *thou wast angry*` | 人工 |
| 空格被扫成句点或连字符 | `of.their`、`on- the`、`usa.ge` | `fix_split_words` |
| 度数号 `°` 是空格或字母 o | `n°t`、`dispelled°by` | `fix_split_words` |
| 双逗号 | `Palestine,, a country` | `MANUAL_RE` |
| 章号罗马数字尾字母 | `ch. vin—xu` = `viii—xii` | `fix_roman_refs` |
| 变音符 | Havernick→Hävernick、Konigsberg→Königsberg、Riickert→Rückert | `MANUAL_RE` |
| 人名缩写 | `August!`→Augusti、`Urn.`→Um.、`Mai.`→Mal. | `MANUAL_RE` |
| 书眉混进正文 | `\IV I N T R O 1)11 C T I ON.` | `extract` 的 `is_runhead` |
| 行末断词甩后缀 | `snort ing`、`comprehensive ness` | **只能人工**（词表对 词+后缀 太宽松） |

## 底本自己印错的——不要改

逐条翻过页面影像确认过，改了就不是复现原书：

`neccessary`、`that Uzziah was deprived`（该说 Isaiah）、
`even where is agreement`（漏了 there）、`ch. XL-XLVI`（该说 XL-LXVI，两处）、
`Commentary on Isai h`（活字缺 a）、`heir judgments`（活字缺 t）、
`so ordered us`（该说 as）、`asumption`、`Pasargada`、`m anyother`。

理由都写在 `manual_fixes.tsv` 的注释里。

## 另一本账：外文活字残渣

正文里还有约 **2900 处**希伯来／希腊活字被 ABBYY 读成拉丁乱码
（`b-fcs`、`D^bxn b^s`、`jra`、`r\M` 这种），加上 **待判 86 处**
（其中只能翻影像的 59）。**这不是校对能解决的**，要走重扫流水线
（`scripts/isaiah_hebrew_ocr.py`，跑一趟一个多钟头）或逐处翻影像。

## 流水线上踩过的坑（别再踩）

- **改完脚本必须重跑整条链**，只改脚本不重跑＝修复没发生。比 mtime：脚本 ≤ 数据 ≤ 产物。
- **判读一遍收不干净**，已改成跑到一轮零写入才收敛。
- **重扫排在判读之后、直接改已发布正文**，它改过的地方要补一遍判读；
  链条末尾已经加了。
- **人工条目的 before 要按判读改完之后的串写**（`apply_manual` 排在 `apply_fixes` 之后），
  否则两边来回推收敛不了（`popule meus` 的 meus 全体证人都读成 mens）。

## 2026-11-17 抽章第 54 章 → 全书同类清理

第 54 章（书页 279–295）逐页看图：外文 28、英文/斜体/标点 42（追记 foreign_image.tsv / manual_fixes.tsv）。
据此写的全书判据（都直接改发布页；**全链条现与发布页对不上，别重跑 chain**——单跑 adjudicate 会把二十几章写坏）：

| 类 | 处数 | 脚本 |
|---|---|---|
| 括注异读斜体收尾在括号外 `(or *X) Y*` | 627（罕见前缀 29 处逐条看图，8:6 例外手改） | `scripts/isaiah_sweep_paren_italic.py` |
| 开引号后多空格（按段配对，只动确定为开引号的） | 358 | `scripts/isaiah_sweep_quote_space.py` |
| 经文出处冒号后缺空格 `5:18` | 391 | `scripts/isaiah_sweep_colon_dash.py` |
| 破折号前后多空格 | 533 | 同上 |
| `I *will` → `*I will` | 54 | 一次性 re.sub |

### 第 1 轮（五轮抽查）：第 8 章（卷一 135–153）

本章 55 处（外文 27）。全书同类：`*'*` 夹开引号 107、出处 `10 : 8` 105、斜体希伯来 39、斜体内 `(or X)` 43 行、
ἐν 读成 lv/iv 3、德文变音 6（`scripts/isaiah_sweep_round2.py`）；句中误句点 49（36 处裁图判读，余按上下文，记入 manual_fixes.tsv）。
句点后丢希伯来词而图上读不全的（19 章 mag、25 章 fortress.、27 章 siatfja、66 章 ana 等）留给外文账。

### 第 2 轮：第 28 章（卷一 469–491）

本章 58 处（外文 37：b/a→ל/ב/כ、bab→נבל、ITS→מדי、nrsiatti→שמועה 等；拉丁 quern/audituml/lade→quem/auditum?/lacte）。
全书同类：希伯来词后黏着的 OCR 问号/冒号 61 处（句末真冒号逐条看图保留 4、修 2：טכמי→שכמו、משליםמשלים 叠印）；
希伯来单字母读成 a/b 12 处逐条看图（ל/ב/כ/ם）。

### 第 3 轮：第 57 章（卷二 319–336）

本章 55 处（外文 30：i→ו、tnax→אנחם、rnrrin→תשורה、ftbinri→החוסה、Tistfx/yisaix→אשכון、Ort→שובב 等；
英文 ivories→works、dear→clear、hibemis→hibernis、hie→hic、De. Wette 等）。
全书同类：希伯来 ו/ל/ב/חצי 读成 i/1/b/a/n 的 9 处逐条看图。

### 第 4 轮：第 24 章（卷一 417–428）

本章 32 处（外文 18：a→כ、ps→ארץ、rs/r→יכת、nan→חמה、Koppe ממרום、ארפה→אדמה 等；句号丢失、Jarch→Jarchi 等）。
全书同类：经文斜体在 ; — 等处被切成两段 157 处合回（`scripts/isaiah_sweep_italic_join.py`，8 处抽样看图）。

### 第 5 轮：第 51 章（卷二 214–231）

本章 32 处（外文 15："O/en?/Kim/niin/rviaai?/1513/-,3/,5 → כי/נחם/תוא/הוגה/לנטות/כמו כן/כן；final ך→ן；בורבור→בור 叠印；
英文 House→Rouse、Hdlle sendcn→Hölle senden、Lehrgebaude、ofch 等）。
全书同类：括注斜体判据漏掉「括号后经文里夹补词括号」的 57 处（判据已补，`isaiah_sweep_paren_italic.py` 正则放宽）。

### 五轮小结（2026-11-17）

| 轮 | 章 | 本章 | 全书同类 |
|---|---|---|---|
| 1 | 8 | 55 | 352 |
| 2 | 28 | 58 | 75 |
| 3 | 57 | 55 | 9 |
| 4 | 24 | 32 | 157 |
| 5 | 51 | 32 | 57 |

每页仍有约 1.5–3 处，七成是希伯来词读成拉丁乱码（无固定形态，判据抓不全，只能逐页看图）。

### 第 6 轮：第 48 章（卷二 151–169）

本章 35 处（外文 15：353/riaapi/nisa/nnea *taregmas*/na "wana → נסכי/תבגוד/מעותיו/טפחה ἐστερέωσε/בחרתי בחנתי 等；
英文 lam/aho/Ikneiv/50 as/onlysafe/CEcolampadius 等）。
全书同类 14 处：CE→Œ、lam→I am 3、冒号后 I→1 3、*1 knew*→*I knew*、ἴδε o→ὁ、naivete→naïveté 5。

### 第 7 轮：第 31 章（卷一 528–533）

本章 6 处全是外文（ea→גם、?→על、פסת→פסח、ארש→איש、1022→מנסו 等）。
全书同类：希伯来词读成多位数字 5 处逐条看图（22→בם、0133→ידענים、23→עצד、157→יתן、012→נוס）。

### 第 8 轮：第 21 章（卷一 375–385）

本章 15 处（外文 8：漏 ל/בא、גלות→גולה、n→אריה、rn→ארח、补回 For בערב 等；Rosemmjller、aprefatory、Eljandilon、lam 等）。
全书同类：前置词粘连真词（`a/the/of`+词）普查 40 条，唯 9 章 theforegoing 一处是错；人名 OCR 残形普查 0。

### 第 9 轮：第 29 章（卷一 491–504）

本章 19 处（外文 9：in→חנה、*מצב -]by* וצרתי→וצרתי עליך מצב、ירדע→ידע、לבר→דבר、ex→את、补 כי/אל 等；
ואת hie→Nihil hic、οἱ→of、cas ethe、Arid→Ariel、verkehrtl 等）。
全书同类：数字区间里的 —/– 统一为 -（主流 1740 处）83 处；59 章 3—3 … as—50 → כ—כ … as—so（看图）。

### 第 10 轮：第 49 章（卷二 169–197）

本章 52 处（外文 28：Dx/ttifia/iban/din/ns/naja/rrnex/lias/'p/"(sn → איים/נפש/הגלו/חום/יפצחו/גשה/אשבה/אשר/קוי/חצן；
补回丢失的 ישראל/נצורי/עני/ילד/לי/שבי 等；希腊 μόνος? 残渣）；u-ho、tokenof、(he sake、FOR so HATH 小型大写 等 24。
全书同类：标点前多空格（` ;` ` ?` ` :`）43 处；希伯来词整个丢失只剩孤立逗号/问号 8 处逐条看图回填。

### 第二个五轮小结

| 轮 | 章 | 本章 | 全书同类 |
|---|---|---|---|
| 6 | 48 | 35 | 14 |
| 7 | 31 | 6 | 5（+9 章 crib→להם） |
| 8 | 21 | 15 | 1 |
| 9 | 29 | 19 | 84 |
| 10 | 49 | 52 | 51 |

### 第 11 轮：第 38 章（卷一 628–645）

本章 34 处（外文 25：Vs→על、b→ל、s→ב、w→ימי、.JLjo→مسلم、fra/"prim/ax→מה/שחין/אט、Gig→σίς 等；Jigs→figs、Aha z、hint→him 等）。
全书同类 15 处逐条看图：Vs→כל 3、b→ל 8、s→ב/צל/על 3、w→עבד/יתר 2（含 65 章 lam→I am）。

### 第 12 轮：第 65 章（卷二 443–469）

本章 44 处（外文 19：rncrvi→והמיתך、iitfx/ittsxs→אשר/כאשר、h?/'aa→מני、cvja→בטרם、un;→נחש、cd→שם、r.→ימות 等；
arid→and、lie→he、he→be、111→Ill、Menij、Ldmmlein、cjcaudiam、ᾧ ῶ→ἐρῶ 等 25）。
全书同类：arid→and 10（保留 42 章 arid desert）、50 章 lie→he、58 章 111→רוד、52 章 'arc→שבי（看图）。

### 第 13 轮：第 6 章（卷一 85–100）

本章 21 处（外文 7：*x*→אל、153→היתה לבער、is a/מאבת→בער/מצבת、da/na→בם/בה、διότι 叠印补全句；
quern/nee→quem/nec、Angusti、Ischylus→Æschylus、[accomplishment 等 14）。
全书同类：拉丁 quern→quem 4、nee→nec 4（逐条核上下文皆拉丁）、开引号后空格 2。
