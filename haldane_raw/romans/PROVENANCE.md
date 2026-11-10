# 霍尔丹《罗马书释义》英文版 · 底本与处理

## 底本
- **StudyLight「hal」**（Haldane's Exposition on the Epistle to the Romans），页面版权栏：*These files are public domain. Text Courtesy of BibleSupport.com*。
  StudyLight 对脚本返回 403，经互联网档案馆快照取原始 HTML：`scripts/fetch_haldane.sh`（CDX 索引 → `web.archive.org/web/<ts>id_/<url>`），
  16 章页 + 书卷页存 `src/studylight/`（书卷页是 Remmers 的书卷概论，不是霍尔丹的，不用）。
- 录入本里残留 AGES 经文锚点编码（`<19D601>`），可见是从 AGES 数字版转来的。用户原定走 AGES PDF（sabda.org `HAL_ROMA.PDF`），
  2026-11-10 sabda 停摆下载不了，用户改令用 StudyLight。
- **对照证人**：1874 年第九版扫描本 OCR，IA `expositionofthee00halduoft`（`src/scan/`，只作核对，不改字句）。

## 录入本覆盖范围
- 有：第 1–16 章逐节注释（13 章有章首概述 Introduction），脚注 56 条。
- 无（1874 版页码）：Preface 与 Introduction（pp. 3–18）；专论 The State of the Heathen World Destitute of the Gospel（含 Case of Cornelius）、
  Sanctification of the Sabbath（pp. 653–702）；Conclusion（pp. 703–712）；Appendix（致 Bickersteth 函，评 Stuart / Macknight / Tholuck，pp. 713–730）。待用户定是否从扫描本转录。
- 脚注：正文有注号、录入本缺正文的 7 条（22 23 34 38 56 57 58），页面给说明性定义；全书无第 1 号。

## 核对
- 抽取 vs 网页注释区逐章词数：每章只差注号数字（1–11 词）。
- 1874 扫描本正文部分（1.7%–88%）对抽取文本 5 词串覆盖 96.4%，**以英文为主、≥25 词的未覆盖段 0 处**（余为页眉页码、希腊文 OCR 噪声）。

## 抽取三个坑（都已修在 extract_haldane.py）
1. 导航栏结束标记在页顶也出现一次 → 每章末条被截空（16 章全中）。
2. 有的段落没包 `<p>` → 段外游离文字也收（第 5 章注 33 所在段曾丢）。
3. 第 9 章章首概述 `data-entry=""` 空 → 按 introduction 收（曾丢约 2,000 词）。

## 链条
`fetch_haldane.sh` → `extract_haldane.py`（units.json）→ `publish_haldane_en.py`（haldane/romans/，重跑逐字节不变）→ `build_commentaries_index.py`。
