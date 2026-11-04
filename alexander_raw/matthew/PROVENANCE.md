# 亚历山大《马太福音释义》——底本与处理链

## 著作

Joseph Addison Alexander（1809–1860），*The Gospel according to Matthew Explained*，New York: Charles Scribner,
1861（1864 年重印）。作者最后一部著作：逐节详注到第 16 章止；第 17–28 章只有每章一段纲要，序（署 S. D. A.，
1860 年 12 月）说纲要是他病后复笔、1860 年 1 月 18 日写完的，「离他去世一周又一天」；原拟的总导论没有写成。

## 是否有中译本

2026-11-04 中英文检索：未见。

## 底本：人工录入本 + 扫描本

| | 来源 | 用途 |
|---|---|---|
| 底本 | **Precept Austin** 网页录入本（据 1864 重印本），两页：`https://www.preceptaustin.org/matthew-commentary-joseph-alexander`（序、1–7 章）、`…/matthew-commentary-2-joseph-alexander`（8–28 章）。存 `src/preceptaustin_{1,2}.html` | 全部正文字句 |
| 扫描本（三证人） | IA 普林斯顿神学院藏：`gospelaccordingt00alex`（1861，主）、`gospelaccordin00alex`（1861，另一册）、`gospelaccordingt00alex_0`（1864）。各取 `_abbyy.gz`；主扫描本页图取 `_jp2.zip` | 斜体、经文头、脚注、录入本错字的证人 |
| 经文参照 | eBible.org KJV2006 USFM（`eng-kjv2006_usfm.zip` 的 `70-MATeng-kjv2006.usfm`） | 只当经文头 OCR 的同位证人 |

`src/`、`work/` 不入库（网页与扫描本可按上表重下）。

### 录入本的性质（逐词对齐实测）

- 序与 1–28 章齐全，22.2 万词；与主扫描本 OCR 对齐 21.8 万 / 22.2 万词，无低匹配块；按 6 词串全书比对，没有一处
  180 词以上的缺文。希腊文、希伯来文完整（带重音、元音点）。
- **斜体全丢**；**每节注释前大字排印的英文经文（经文头）整段删掉**，只留节号；**页脚注注文全丢**，注号留着
  （145 个，只漏 p.99 一个 ‖）。
- 经文出处改作现代写法（原书 `3, 2`，录入本 `3:2`）——照收。
- 少量 OCR 式错字（`This Terse`→verse、`raying`→saying 等 32 处），见 `body_fixes.tsv`；节号段头丢逗号 3 处
  （`4546.`→`45, 46.`），同表。另删一行网站导航「GO TO COMMENTARY ON MATTHEW 8-16」。

## 处理链（`scripts/extract_alexander_matthew.py` → `units.json` → `scripts/publish_alexander_matthew_en.py`）

骨架照搬使徒行传（`extract_alexander_acts.py`），改动：

1. **ABBYY 两种 schema**：1861 两份是 FineReader 6（`italic="true"`，正文 13–14 号），1864 是 FineReader 10
   （`italic="1"`，正文 12 号）。字号、x 高度一律相对本页正文判。
2. **经文头**：比本页正文大 2 号以上的段落（17–18 号）。页眉 `MATTHEW` 的各种读坏（`MAT THE AY`、`M A T T Ii E W`、
   `MATTHEAY`）不打断跨页经文头。录入本把几节并成一段注释、原书每节各印经文头的，按节序拼接。516/516 落位。
   - OCR 非词 → KJV 同位词；真词对真词只按 `head_confusions.tsv`（逐类看图：lie/he、hut/but、he/be、be/he、
     cloth/doth、hare/bare、had/bad、vent/went）。
   - 原书本作、照印的：3:10 thrown、6:17 thy head、8:26 he said、9:26 thereof、15:26 and cast (it)、16:9 Do ye not
     understand；原书排印错照印：14:5 ne、14:36 thy might、10:42 he reward。拼法 Judea、Cesarea 等不改。
   - `head_manual.tsv`：逐条看图手改 7 处。
3. **斜体**：三份扫描本逐词多数票（只有两份对上时须两份都是斜体）。
4. **页脚注**：x 高度矮于正文的小字段（字号标签不可靠：p.30、p.40 注与正文同号）。146 条，三份 OCR 投票出草稿后
   **逐条看主扫描本原图转录**（`footnotes.tsv`；转录工具 `alexander_matthew_fnbatch.py` / `fndraft.py` /
   `fnplan.py` / `fnsheets.py`）。原书排印错照印并在备注栏写明（Pererebuerat、requred、διεθήμισαν、Jerome..、
   未闭合括号等）。录入本注号按次序逐条配对、注号须一致。
5. **录入本错字**：三份扫描本同位读出同一真词、录入本不同的 53 处候选（`alexander_matthew_body_candidates.py`），
   逐处裁图：32 处录入本错，落 `body_fixes.tsv`；其余 21 处是三份 OCR 一起读错（b/h、in/m），录入本不动。
6. **发布**：一章一页 `alexander/matthew/<N>/`，序 `preface/`；第 17–28 章只有纲要，全章各节锚点挂在纲要前；
   第 5 章章首另有登山宝训（5–7 章）总说。经节锚点 `matthew-<章>-<节>` 1071/1071。

裁图：`scripts/crop_alexander_matthew.py`（tesseract 在原图上重新定位行，同使徒行传）。

## 未做

- 中译。
- 经文头 OCR 的标点（如 1:2 `Jacob and Jacob` 处 KJV 有分号）未逐条看图；与 KJV 不一致的真词差异 412 处留原样
  （`work/head_unresolved.log`，绝大多数是 1861 年冒号、分号前留空格的排版）。
