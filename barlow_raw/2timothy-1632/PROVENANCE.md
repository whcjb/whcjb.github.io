# 巴洛 1632 年对开本（提后 1–2 章）——第二章底本调查（暂停）

2026-10-28 用户要处理第二章，量完引擎后决定**先暂停**。

## 底本

- IA `bim_early-english-books-1475-1640_an-exposition-of-the-fis_barlow-john_1633`（IA 题 1633，扉页 1632），665 叶，800 ppi 缩微胶片，**只此一份**；无 TCP 录入本，HathiTrust / Google Books 无本。
- 第二章：叶 264 本章扉页，266–270 本章要目表，271 空白，272 起正文（第二章页码从 1 重起），至书末。
- 取图：`scripts/barlow1632_fetch.py 264-664`（`ia_rangezip.py` 按 Range 一次取一叶 jp2，缩半存 `witness/img/`，≈400 ppi，1.9G，不入库）。IA 单路带宽约 60KB/s，14 路并发一小时取完。
- 版面：单栏正文，旁注在外侧（正面右、反面左）。`scripts/barlow1632_ocr.py` 已能切栏。

## 引擎实测（第一章叶 38/40/42，对 1625 TCP 录入本）

| 引擎 / 预处理 | 对上率* | 非词率 |
|---|---|---|
| tesseract eng，灰度+中值 | 0.508 | — |
| tesseract eng+enm，背景展平 41 + 中值 | **0.641** | 17–21% |
| tesseract 自适应 / Sauvola / CLAHE | 0.28–0.46 | — |
| kraken + CATMuS-Print Large（zenodo 10592716） | **0.682** | 18–20% |

\* 对上率受两版差异压低：1632 版把 First/Secondly 改成 1. 2.、拼法改动（wee→we、deede→deed），上限明显低于 1。
主要错型：斜体 the→tbe/ibe、c/e、h/b 混淆、词间粘连（itis、toscoffe）。

## 结论与可选路线（待用户定）

两个非生成式引擎单用都不够发布。可选：① 加视觉模型整页转录当证人（约 $45，只印证不进正文）；
② 两引擎互证（红块约四分之一）；③ 用第一章版面 + 1625 录入本微调 kraken 后再跑。
kraken 装在 `~/.venvs/kraken`，模型在 `~/.venvs/kraken-models/`。
