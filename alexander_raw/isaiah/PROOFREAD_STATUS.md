# 以赛亚书正文校对进度（续做看这一份）

最后更新：2026-09-15

## 已经读完的

**逐句实读过**（不是扫描，是整篇读下来）：

| 文件 | 篇幅 | 捞到 |
|---|---|---|
| `preface.md` `introduction.md` `later-preface.md` `later-introduction.md` | 约 40 万字符 | 109 处 |
| `1.md` | 第 1 章 | 10 处 |
| `2.md` | 只读了用户截图那一段（v. 18） | 4 处 |
| `12.md` | 第 12 章 | 13 处 |
| `40.md` | 第 40 章 | 20 处 |

**按已知错误类型程序化扫过全书 66 章**，捞到约 300 处。

人工条目累计 **约 240 条**在 `manual_fixes.tsv`；带闸的规则在
`scripts/adjudicate_alexander_isaiah.py` 的 `MANUAL_RE` 与几个 `fix_*` 函数里。

## 还没读的

**第 3–11、13–39、41–66 章，共 62 章。**

按第 1、12、40 三章的实测，**每章还能捞到五到八处检测器覆盖不到的错**，
62 章折下来大约 **300–500 处**。检测器只能找它已经知道的类型，新类型只能靠眼睛。

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
