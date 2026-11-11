# 加尔文讲章（戈尔丁英译）——底本与处理链

2026-11-11 用户令「直接上站」。加尔文没有写约伯记、申命记的注释（他的旧约注释讲到以西结书 20 章就去世了，
申命记只在《摩西五经合参》里按主题拆讲），这两卷留下的是在日内瓦讲台上逐节讲的讲章，由书记员速记、
法文出版，阿瑟·戈尔丁（Arthur Golding，1536–1606）译成英文。

| | 约伯记 | 申命记 |
|---|---|---|
| 书名 | *Sermons of Master Iohn Caluin, vpon the booke of Iob* | *The Sermons of M. Iohn Caluin vpon the fifth booke of Moses called Deuteronomie* |
| 版本 | London: Henrie Binneman for Lucas Harison and George Bishop, 1574（colophon）；STC 4445 | London: Henry Middleton for George Bishop, 1583；STC 4442 |
| 底本 | EEBO-TCP **A69056**（Phase I，CC0 1.0），`job/src/A69056.xml`（入库） | EEBO-TCP **A17698**（Phase I，CC0 1.0），`deuteronomy/src/A17698.xml`（入库） |
| 讲章 | 159 篇，齐全 | 200 篇（讲于 1555-03-20 至 1556-07-15，日期见各篇标题） |
| 本站 | `/calvin/job-sermons/` | `/calvin/deuteronomy-sermons/` |

取法：`https://raw.githubusercontent.com/textcreationpartnership/<ID>/master/<ID>.xml`。

## 是否有中译本

2026-11-11 中文检索两轮（约伯记讲道集、申命记讲道）：未见正式出版的中译本。未逐家出版社书目核对。

## 处理链

1. `scripts/extract_calvin_sermons.py <书>` → `<书>/units.json`：行内/块级复用 `tcp_tei`（ſ→s、斜体、页码锚点、缺字记号），
   拼法照录原书。所讲经文（epigraph）→ 经文框；篇首提要（argument）→ `.cs-argument`；原书字面星号（旁注标记）转 `&#42;`。
2. `scripts/publish_calvin_sermons.py <书>` → `calvin/<书>-sermons/`：一篇一页 `<篇次>.md`，卷首各一页，书首页按章分组。
   date 存 `<书>/en_meta.json`，重跑不改。
3. 入口：`calvin/index.html` 的「讲章」区（手写）。

## 篇次与章次

- **约伯记**：TCP 的 `n` 有录错（第 11 篇作 13、第 110 篇作 10 等），原书标题也有印错（第 78 篇印 lxxvij.、第 112 篇印 Cij.）；
  159 个 div 齐全且按原书次序，篇次一律按顺序数。第 124 篇标题把 33 章印成 xxxiiij.（前后均为 33 章，本篇是「第 33 章第三篇」），
  `CH_FIX` 归 33 章，标题照录。第 17、101 篇跨章（4–5、27–28），标题出「Job 4–5」。
  第 3、47、103 篇无经文框（提要作「本篇仍讲上一篇的经文」）。
- **申命记**：191 个 div 对 200 篇。录入所据胶片本缺页 28 处（`<gap reason="missing" extent="2 pages">`），其中 9 处跨在两篇之间，
  后一篇的标题与开头散失、余文并在前一篇 div 里：39→38、48→47、61→60、67→66、84→83、107→106、111→110、117→116、157→156。
  **不按猜测拆开**：照 TCP 一页，标题作「Sermons 38 & 39」，页首说明；书首页目录以灰色虚线格列出，指向所在页。
  n 缺省的 div 标题作 threescore = 第 60 篇；第二个 n="70" 标题印 Lxx.，按日期与「第十章第五篇」实为第 73 篇（`DEUT_FIX`）。

## 缺字（未判读，页面标红）

| | 缺字母 | 缺整词 | 缺一段以上 | 缺页 |
|---|---|---|---|---|
| 约伯记 | 524 | 8 | 110 | 0 |
| 申命记 | 1741 | 288 | 324 | 28 处×2 页 |

尚未据他本补。补法须照本站惯例（看图读定才落、推断待用户同意，见 old-book-ocr skill）；申命记缺页要另找一份 1583 年版扫描本。

## 未收

卷末索引（约伯记 Scripture_index / subject_index；申命记两种 table）暂未出页。中译未开始（未奉令）。
