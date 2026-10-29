# 亚历山大《使徒行传注释》——底本与处理链

## 著作

Joseph Addison Alexander（1809–1860），*The Acts of the Apostles Explained*，两卷，New York: Charles Scribner, 1857。
卷一第 1–12 章，卷二第 13–28 章。

## 是否有中译本

2026-10-29 查：未见正式中译（中英文搜索各一轮，只查到巫尔登注释的中译，不是本书）。

## 底本：用户指定「人工录入本」

| | 来源 | 用途 |
|---|---|---|
| 底本 | **Monergism Books 电子本**（ePub，2022）。直链 403，取自互联网档案馆快照：<br>`http://web.archive.org/web/20250425064438id_/https://www.monergism.com/thethreshold/sdg/jaalexander/The%20Acts%20of%20the%20Apostles%20Explai%20-%20Joseph%20Addison%20Alexander.epub` | 全部正文字句 |
| 扫描本（三证人） | IA 普林斯顿神学院藏 1857 初版 `actsofapostlesex01alex` / `actsofapostlesex02alex`（主）；同馆另一册 `actsofapostlese01alex` / `actsofapostlese02alex`；加州大学藏 `actsofapostlesex01alexiala` / `actsofapostlesex02alexiala`。各取 `_abbyy.gz` | 斜体、经文头、脚注、录入本错字的证人 |
| 经文参照 | eBible.org KJV2006 USFM（`eng-kjv2006_usfm.zip` 的 `74-ACTeng-kjv2006.usfm`） | 只当经文头 OCR 的同位证人，不直接抄 |

`src/`、`work/` 不入库（Monergism 文末声明保留其电子版权利；扫描本与 KJV 都可按上面地址重下）。

### 录入本的性质（逐词对齐实测）

- 1–28 章与序言、导论齐全，37.5 万词；常见 OCR 错字签名为零，干净程度相当于人工录入本。
- **斜体全丢**。本书以斜体标出所讲解的经文字词与他自己的译法，丢了就分不清经文与解说。
- **每节注释前大字排印的英文经文（经文头）整段删掉**，只留节号。
- **页脚注注文全丢**，正文里只留了 9 个注号（8 个 `*`、1 个 `†`）。
- 经文出处改作现代写法（原书 `3, 2. 5, 1`，录入本 `3:2; 5:1`）——照收，未回改。
- 少量错字（39 处）与一处多出的连字符（`respecting-him`），见下。

## 处理链（`scripts/extract_alexander_acts.py` → `units.json` → `scripts/publish_alexander_acts_en.py`）

1. **对齐**：两边按「字母数字小写键」切词，分块跑 SequenceMatcher（2500 词一块，6000 词搜索窗，块尾留重叠）。
   主扫描本对上 36.3 万 / 37.4 万词，无低匹配块。
2. **坏页替换**：主扫描本卷二有 7 页 OCR 错词率 > 12%（119 159 163 171 193 197 263），整页换用
   `actsofapostlese02alex` 同页（页序号一律 −2，逐页比对相似度 0.80–0.87）。只影响经文头与脚注的取字。
3. **斜体**：三份扫描本各自对齐录入本，逐词多数票（≥2/3；只有两份对上时须两份都是斜体）。
   普林斯顿两册卷二逐词比，斜体判断不一致 292 处 / 约 1.4 万斜体词——单证人会有误报（如导论首段把字距宽的
   `New` 标成斜体），投票后消失。三份都没对上的词夹在两个斜体词之间才补成斜体（只补格式）。
4. **经文头**：扫描本里字号 11 的段落（正文 9）。节号常读坏（`G.` `i.` `'lA.` `3G. 87.`），落位不靠节号，
   靠「与附近注释段那几节 KJV 的相似度」。跨页续行、页眉（`ACTS 1, 12. 17`、读坏的 `1G8 ACTS`）、
   页脚折标（`VOL. I.—18`）、页脚注都不打断经文头。961 条注释全部落位。
   - OCR 词不是真词 → 换成 KJV 同位词（大小写照 KJV，只在句首大写——OCR 把 w 读成 `W`/`Av`，照抄会得出句中的 `When`）。
   - 两边都是真词 → 只按 `head_confusions.tsv` 里逐类看图判为字形混淆的才换（lie/he、clay/day、Paid/Paul …）；
     其余照 OCR，因为亚历山大的经文头本与 KJV 有出入（show/shew、Judea/Judæa、Cesarea、didst/diddest、a high arm …）。
   - KJV 多出、OCR 没有的词**不补**。
   - 标点闸 `punct_gate()` 只动标点与大小写，字母不动（自检字母序列不变）：零散引号、词中句点、成对括号、
     段头节号残渣、词尾游离撇号。
   - `head_manual.tsv`：逐条看图手改（丢的问号/句点、ABBYY 漏读的整行 `began.`、拆读 `An gel` 等），每条须恰好命中一次。
5. **录入本错字**：三份扫描本同位读出同一个真词、录入本不同的 124 处，逐处裁图看过：39 处录入本错
   （`corrupttion` `friturity` `cripplo` `or`→`of` ×6 …），落 `body_fixes.tsv`；其余 85 处是三份 OCR 一起读错
   （同一副铅版，`but`→`hut`、`be`→`he`、`by`→`hy`），录入本不动。
6. **脚注**：`footnotes.tsv`，9 个注号逐条看原图转录（OCR 的拉丁文、希腊文不可用）。
   推断 2 处（原图字母残损：`diversi`、`scimus`）；`Conybeare and Howson, vol. i. 9. 310.` 照印；
   卷二 p237（第 20 章 `prophecy.*`）原书印了注号而本页、次页均无注文，页面注明缺注。
7. **发布**：一章一页 `alexander/acts/<N>/`，前置件 `preface/` `introduction/`；经节锚点 `acts-<章>-<节>` 1007/1007。
   书首页「文本说明」的四张改动表由上述 tsv 生成。

判读用裁图工具：`scripts/crop_alexander_acts.py`（ABBYY 坐标与 IA jp2 的坐标系对不上，改用 tesseract 在原图上定位行）。
