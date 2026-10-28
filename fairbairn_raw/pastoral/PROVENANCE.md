# 费尔贝恩《教牧书信》——底本与处理链

## 著者与著作

Patrick Fairbairn（帕特里克·费尔贝恩，1805 年 1 月 28 日生—1874 年 8 月 6 日卒；生卒取 DNB vol.18，W. G. Blaikie 撰，
原文存 `dnb_fairbairn.txt`）。*The Pastoral Epistles: The Greek Text and Translation, with Introduction, Expository Notes,
and Dissertations*，Edinburgh: T. & T. Clark, 1874；序署 Glasgow, January 1874。

## 是否有中译本

2026-10-28 查（中英文检索）：未见中译。

## 底本：人工录入本

用户要求「找到人工录入版处理」。正文据：

| | 来源 | 用途 |
|---|---|---|
| 底本 | **StudyLight「Fairbairn's Commentary on Ezekiel, Jonah and Pastoral Epistles」**（代号 fbn）。页面版权栏：*Text Courtesy of BibleSupport.com*；书首页：*Prepared for Libronix Digital Library System … 2008 / Prepared for e-Sword / theWord*。即 BibleSupport 的 e-Sword 模块，与坎德利什那份第二证人同一来源体系。StudyLight 对脚本访问返回 403，网页经互联网档案馆快照取得：`http://web.archive.org/web/<ts>id_/https://www.studylight.org/commentaries/eng/fbn/<1-timothy-1>.html`（13 章页 + 3 个书卷首页，快照时间见 CDX 查询 `url=studylight.org/commentaries/eng/fbn/*`；titus-1 的快照是 gzip 存的，要先解压） | 全部正文 |
| 顺序证人 | **1874 年初版扫描本的 OCR 文本**：IA `pastoralepistle00fair`（Princeton Theological Seminary 藏本）`_djvu.txt` | 只用来恢复原书次序、查缺文，不改字句 |

`src/` 不入库：`src/studylight/*.html`、`src/scan/pastoralepistle00fair_djvu.txt`，按上面地址可重下。

ccbiblestudy 的提摩太前书英文目录（`New Testament/54 1Tim/54-1Timothy-E/`）没有费尔贝恩。

### 录入本的性质

- 原书页脚注已改作正文里的圆括号插注（如 5:11「(The future, καταστρηνιάσωσιν, seems the better reading …)」），照录。
- 三篇附录除在书卷首页末尾整篇出现外，又「为方便起见」整篇嵌在引到它们的经节之下（1 Tim. 2:5–6、3:2、3:12、6:2，
  Tit. 1:6、2:11–14），共 112 段。
- 按经节挂条目时挂错了 3 条：1 Tim. 1「Verse 8」实为 2:8 的注释；1 Tim. 1「Verse 15」实为 5:15；
  2 Tim. 2「Verses 9–10」实为 1 Tim. 2:9–10。
- 整节缺文 5 处（原书有、录入本无；OCR 覆盖检测 + 人工看过）：1 Tim. 1:8（pp. 85–86）、1:15（pp. 95–97）、
  5:19（pp. 219–220）、Tit. 3:14（p. 305）、2 Tim. 4:3（pp. 383–384）。
- 希腊文常把重音符拆成独立的组合字符并前后留空格（`Κυ ́ ριου`），清洗时合并并做 NFC。

### 处理

1. `scripts/extract_fairbairn.py`：src → `units.json`。
   - 段落清洗：只留 em/strong/sup/sub，修好错层嵌套（录入本常见 `<p><em>…</p></em>`）。
   - 每段按 6 词串在 OCR 里定位（只认注释区的命中——注释段常整句引经文，经文在前面「经文与译文」里也有），
     条目按原书位置重排；前后各 3 条邻居多数属于别章的，改挂过去（正好是上面那 3 条）。
   - 原书位置落在附录区的段落 = 嵌入经节的附录副本，删去。
   - 条目中途以「Ver. N.」起段的拆成子条目。
   - 缺文 5 处插占位条目（`MISSING` 表），页面注明，**不从 OCR 补**（待用户定）。
   - 书卷首页：序言、导论四节、三卷经文与译文（希腊文 / 英文各自接成连续文本，按章号 I. / II. … 切开）、附录 A–C（含 C 后的 Note on 1 Cor. 7:21）。
2. `scripts/publish_fairbairn_en.py --apply`：units.json → `fairbairn/{1timothy,titus,2timothy}/`。
   一章一页；序言、导论、附录放在 1timothy 下，三卷书首页都链过去；翻页顺序按原书。
   经节锚点 242/242（原书并讲的经节，锚点挂到讲它的那一条）。
3. `scripts/build_commentaries_index.py`：历代解经与对照注释登记。

原书没有单独出条的经节（并在前一节注释里讲）：1 Tim. 3:5、4:5，Tit. 2:10，2 Tim. 3:11——OCR 里同样没有单独的「Ver. N.」。
