# 赫奇森《约伯记释义》——底本与处理链

## 著者与著作

George Hutcheson（乔治·赫奇森，1615–1674，生卒年取 TCP 编目），苏格兰盟约派，
扉页署 *Minister of the Gospel*。本书是他在爱丁堡讲约伯记的 316 篇讲章的摘要
（扉页：*Being the Sum of CCCXVI Lectures, Preached in the City of Edenburgh*），
体例同他的约翰福音释义：每段先排出经文，再讲解、分条列教训。卷首有作者致读者、
作者自拟的勘误表；正文前有全书论旨（The Argument），每章前有章首提要。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A45240**（人工录入 TEI P5），github `textcreationpartnership/A45240`；`src/A45240.xml` 入库 |
| 版次 | London: Ralph Smith, 1669；ESTC R20540 |
| 授权 | EEBO-TCP Phase 2，CC0 1.0（转录文本；不含页面影像） |
| TCP 来源页图 | ProQuest EEBO 缩微胶片 image set 48911（Cambridge University Library 藏本） |
| 影像证人 | **尚未找**——缺字判读、14 章缺页都要等证人 |
| 其他在线文本 | Oxford Text Archive（同一 TCP 文本）；earlyenglishprintedsermons.org/segment/A45240/（现代拼写分段，同源，不是独立证人） |

中译：2026-11-02 网页搜索未见中译本（未逐一查微读书/恩道/三联书目）。

## 抽取（`scripts/extract_hutcheson_job.py`）

骨架照搬 `extract_hutcheson.py`（约翰福音），归一规则相同（长 ſ → s、`Ʋ` → U、
行末断词拼合、拼写照原样）。本书 TEI 与约翰福音的差别：

| 差别 | 处理 |
|---|---|
| 章首提要、全书论旨是 `<argument>` 元素（约翰是 `<div type="argument">`） | 同样出 `.hc-argument` 块 |
| 节号写作 `Vers. N.`；3:18 把经文首词包进了 bibl（`18. There`） | 节号正则放宽；包进去的词还回经文 |
| 38:11 节号 `<bibl>` 落在 `<p>` 外、经文在下一个 `<p>` | 接回那个空节号 |
| 扉页引经题词（雅各书 5:11，`<q><bibl><p>`） | `.hc-epigraph` 引文块 |
| 勘误表在卷首（front）；书末只有 FINIS | 页序：书名页 → 致读者 → 勘误表 → 论旨 → 1–42 章 |
| 段内分条 `<list>`（论旨四分、36:7 三条） | 每条 `<br>` 另起一行，仍在同段 |
| `<g ref="char:cmbAbbrStroke">`（一处，`whō`＝whom） | 照原样留组合横线 |

### 节号印错（2 处，照印本显示，锚点挂实际节）

| 位置 | 印作 | 经文 | 实为 |
|---|---|---|---|
| 21 章 | Vers. 22（第一次） | For what pleasure hath he in his house after him… | 21:21 |
| 33 章 | Ver. 3（第一次） | Behold, now I have opened my mouth… | 33:2 |

是原书印错还是 TCP 录错，未看影像，未定。登记在 `VNUM_FIX`；页面上节号旁有 title 说明。

### 缺页

TCP 在 14 章标 `<gap reason="missing" extent="2 pages">`（pb 196 前；按页码是原书第
194–195 页）。14:6 讲解到 `…or have a cessation` 中断，接上的是 14 章后段讲解，
14:7–12 的经文框全在缺页里。页面上以 `.hc-lost` 红框标明，待据他本补。

### 缺字

TCP `<gap reason="illegible">` 1656 处（1 字母 1403、2 字母 122、3 字母 29、4 字母 9、
5 字母 2、1 词 70、1 span 21）+ 认不清的标点 `char:punc` 69 处；抽出缺字点 1726 个，
发布后剩余可见记号 1725 个。**均未判读**，照录为 `•` / `〈◊〉` / `〈…〉` / `▪`。
判读走约翰福音那套（`manual_fixes.tsv`，按篇内次序落位，`hutcheson_common.use('job')`）。

**证人**：2026-11-02 查，1669 年版公开渠道没有页面影像——IA `bim_early-english-books` 胶片集
只有赫奇森的小先知书、讲章集等，无约伯记；Google Books 的 1669 本（4VgeswEACAAJ / DYkQMwEACAAJ）
与一种年份不明的重印本（_8rgoQEACAAJ）都是 no view。第 ②③ 层（看图判读）、扉页照原图手排、
14 章缺页补录都因此暂做不了。

**第 ① 层语料自证**（`scripts/hutcheson_job_gapfill.py --write`，判据同约翰福音）：1679 个缺字词里
语料可判 588（lex 534 / ctx 54），其余 skip 599（缺整词、标点、含数字、已知字母<3）、
ambig 387、none 55、rare 50。按 2026-10-16 起的规矩，语料自证**不直接落**，全部列在
`gap_pending_approval.tsv` 待用户同意。

**渲染层验收**（§4.4，2026-11-02）：凭空表格 0、`<ol>` 0、重复 id 0、`<em>` 首尾空白 0、
正文字面星号 0、渲染前后实词集合无缺失。

## 发布（`scripts/publish_hutcheson_job_en.py`）

照搬约翰福音的英文发布：按经文框分页（讲解不足 300 字符并入下一段），页名
`<章>-<首节>`，每章一页目录 `<章>.md`；layout `hutcheson-job-chapter` /
`hutcheson-job-book` 是从约翰福音复制的独立一份（每本书独立样式）。
604 页，其中正文 600 页。

## 重跑

```bash
python3 scripts/extract_hutcheson_job.py --apply
python3 scripts/publish_hutcheson_job_en.py --apply
python3 scripts/build_commentaries_index.py
```
