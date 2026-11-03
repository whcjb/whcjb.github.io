# 迪克森《马太福音简释》——底本与处理链

## 著者与著作

David Dickson（大卫·迪克森，1583?–1663；DNB vol.15，T. F. Henderson 撰，原文存 `dnb_dickson.txt`；
ODNB 卒年作 1662）。*A Brief Exposition of the Evangel of Jesus Christ according to Matthew.* 1647 年格拉斯哥初版
（George Anderson 印，Wing D1398）；本站据 **1651 年伦敦第三版**（Printed for Ralph Smith，Wing D1400，ESTC R13881）。

## 是否有中译本

2026-11-03 中文检索：未见。未逐一查微读书／恩道／三联／橡树书目。

## 底本

| | |
|---|---|
| 主底本 | **EEBO-TCP A35949**（Phase 1），人工录入 TEI P5，github `textcreationpartnership/A35949`，`src/A35949.xml`（入库） |
| 授权 | EEBO-TCP，CC0 1.0 |
| 原书影像 1651 | archive.org `bim_early-english-books-1641-1700_a-brief-exposition-of-th_dickson-david_1651`（IA40313017-18，370 叶，800 ppi）。IA 自带 OCR 里搜不到 5:24–30 的讲解，**疑与 TCP 同一卷缺页胶片**，未看图确认 |
| 原书影像 1647 初版 | `…_dickson-david_1647`（IA40313017-18，415 叶）、`…_dickson-david_1647_0`（IA40313709-36，253 叶，影像较差）。两份的 IA OCR 都有 5:25–29 经文头，可补录缺页、作第二证人；初版与第三版排版不同、文字可能有修订 |

## 结构（`scripts/extract_dickson.py`）

TEI：`<div type="chapter">` × 28；章下 `<argument>`（本章提要）→ `<epigraph><q>`（首节经文）→ `<q>`（经文段）与
`<p>`（讲解）交替。一段经文一页，页名 `<章>-<首节>`，共 597 段；卷首 title / dedication（致劳登伯爵）/
to-the-reader / titles（「新约」与「马太福音」两段总题解）。行内与块级共用 `scripts/tcp_tei.py`，发布共用
`scripts/tcp_publish.py`。

录入本的怪处：

- 第二十六章 div `n="6"`、章题印作 `CHAP. VI.`：章号按 div 顺序取。
- 经文头节号印错／录错四处（经文对钦定本可证）：10:19 作 29；12:8 作 18、12:9 作 8；12:27 作 17。正文照录，
  `VNUM_FIX` 只改页名与节段。未看影像，不定是印错还是录错。
- 第五章 23 节后 `<gap reason="missing" extent="2 pages">`：缺原书 pp. 52–53（5:24–30 的讲解），下接 p.54
  「from thee: for it is profitable for thee that one of thy members should perish」（5:29–30）。发布页 5-23 节段
  因此是 5:23–30。补录文字放 `supplied/1.md`，发布时换进去（`publish_dickson_en.py`）。
- 四处 `<gap reason="duplicate">`（重拍的页）丢弃。

## 缺字

录入本 593 个 `<gap>`：1 字母 444、2 字母 77、3 字母 11、4 字母 1、1 词 53、污损 2、缺页 1、重页 4。
`dickson_witness.py gaps` 并组后 **573 组**（全在正文，无旁注），存 `gap_sites.json`。2026-11-03 上线时**一处未判**，
页面标红。判读走霍尔／巴洛同一套：`dickson_witness.py build/match/sheets` + `gap_review.tsv`
（规则见 `scripts/dickson_common.py` 文首）。**只有看图读出的直接落；推断写 P:xx 列清单待用户同意。**

## 链条

```
python3 scripts/extract_dickson.py --apply      # TEI → en_chapters/ + order.json + pages.json
python3 scripts/dickson_witness.py gaps         # → gap_sites.json
python3 scripts/publish_dickson_en.py --apply   # → dickson/matthew/
python3 scripts/build_commentaries_index.py     # 历代解经 + 对照抽屉
```
