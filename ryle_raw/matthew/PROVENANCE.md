# J. C. Ryle, *Expository Thoughts on the Gospels: St. Matthew* — 底本来源

下载于 2026-10-23，`src/` 不入库，校验和见 `src.sha256`。

| 文件 | 来源 | 说明 |
|---|---|---|
| `src/matthew.txt` | https://ccel.org/ccel/r/ryle/matthew/cache/matthew.txt | CCEL 数字录入本，底本 New York: Robert Carter, 1860；28 章 93 段齐全；**缺序言** |
| `src/matthew.pdf` | https://ccel.org/ccel/r/ryle/matthew/cache/matthew.pdf | 同上排版 PDF（278 页，文本层） |
| `src/ia_1857/expositorythough01ryle.pdf` | https://archive.org/details/expositorythough01ryle | 原书扫描件，New York: R. Carter, 1857，第 1 卷（马太），442 帧；含序言，可作看图核对的证人 |
| `src/ia_1857/expositorythough01ryle_djvu.txt` | 同上 | IA 的 OCR 文本 |

CCEL 的 ThML/HTML 下载地址返回 404，未取得。

## 2026-10-23 核查：网上的数字录入本都不是原书原文

拿 IA 1857 扫描件第 1–4 页（马太 1:1–17）逐句对照：

| 本子 | 与 1857 原文的出入 |
|---|---|
| CCEL `matthew.txt` | 整句改写（"Let us remember our deep responsibility." → "Let us never forget the deep responsibility which possession of the Bible entails on us."；"Learn from this list…" → "We learn, for one thing…"）；斜体要点全丢；出处改阿拉伯数字且有误（Num. xxiii. 19 → "Num 13:19"）；无钦定本经文、无脚注、无序言 |
| Monergism `src/monergism/ryle_gospels.pdf`（calibre 2018，四福音合集，2542 页） | 措辞大体随原书，但美式拼写（Saviour→Savior、practise→practice）；引文换成现代译本（"He abideth faithful: He can not deny Himself" → "He remains faithful--He cannot deny Himself"）；出处改阿拉伯数字；无钦定本经文、无斜体 |
| Precept Austin 网页 | 与 Monergism 同一系（Savior、阿拉伯数字出处） |

Project Gutenberg、Wikisource、Faded Page 均无此书。StudyLight 的 Ryle 只有约翰福音的 Notes，且是 OCR 本（"Terse"=verse）。

## 最接近原书的一份：e-Sword 模块（2009）

`src/esword/Ryle.cmtx`（SQLite/RTF，12.9 MB），下载自 http://www.sg-audiotreasures.org/proverbs/Ryle.cmtx
（发布页 http://www.eternallifeministries.org/e-sword-ryle.htm，2009-09/11，马太、马可、路加）。马太 96 条＝93 段注释 + 序言 + 脚注。

- **保留**：原书措辞、斜体要点（`\i`）、首词小型大写、序言（落款 Helmingham Rectory, December, 1856）、原书脚注（如 26:26 的 Ferus/Mayence 长注）。
- **改动**（都是成体系的，可程序化识别）：Saviour→Savior（马太 47 处，1857 原书 52 处全作 Saviour）；"St. Matthew"→"Matthew"（原书 14 处，模块剩 1 处）；出处改 e-Sword 格式（`Gen_12:3`，原书作 Gen. xii. 3）；practise→practice。
- **缺**：每段前的钦定本经文。

逐词三元组对照 IA 1857 OCR（全书，OCR 本身有噪声）：e-Sword 94.3%、CCEL 85.0%、Monergism 83.0%。

可行路线：以 e-Sword 本为底本，按位置对齐 1857 扫描件逐处回改上述成体系改动、出处恢复罗马数字，钦定本经文按 1857 版式补齐；任何改动以页面影像为准。

## 2026-10-23 英文版上线（/ryle/matthew/）

链条（全部可重跑，验收＝重跑后 sections.json 逐字节不变）：

```
python3 scripts/extract_ryle_matthew.py     # e-Sword RTF → esword_sections.json（96 段、序言、15 条脚注）
python3 scripts/ryle_collate.py             # 全书逐词对齐 1857 hOCR → collation_diffs.tsv（~50 秒）
python3 scripts/ryle_review.py              # 实词出入裁原书行图 → review/sheet_NN.png + review.tsv（判读表）
python3 scripts/ryle_verdict.py 12=1857 …   # 填判读
python3 scripts/ryle_apply.py               # → sections.json + applied.tsv
python3 scripts/ryle_kjv.py --build         # 经文框：1769 钦定本 × 1857 框内小字 → kjv_1857.json
python3 scripts/publish_ryle_en.py --apply  # → ryle/matthew/{1..28,preface}.md + index.html
python3 scripts/build_commentaries_index.py # 历代解经 / 对照抽屉
```

- 段落：96 段，与 1857 原书一致（CCEL 本漏了 14:1、14:13、22:34 三段）。原书页眉两处误印节号（VIII. 16—26、IX. 27—37），按经文框实际所印取 16—27、27—38；e-Sword 把 24:36—51 误作 36—46，已改。
- 判读：220 处实词出入全部看图，121 处照原书回改，99 处 e-Sword 对（OCR 错或段落位置）。e-Sword 的改动类型：引经改成现代措辞（looketh at、before the eyes…）、改词（justness→justice、goodness→godliness、crushed→cursed…）、调词序、删 St.（33 处）、拼写美式化（109 处，整族回改）。
- 原书误植沿用 e-Sword 改正的：is this world→in this world、Due Veil→Du Veil；出处误植 7 处列在书首页勘误表（James ii. 11 一条引文实在 2:17，沿用 e-Sword 的 2:20，待定）。
- 经文框：1857 年版所印钦定本与 1769 牛津本有 31 处不同（laborers、honor、ax、cloak、hungered、how often、He said、things which are God's、a little farther…），照 1857。
