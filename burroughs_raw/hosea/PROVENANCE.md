# 巴罗夫《何西阿书讲解》来源与处理记录

## 底本（录入本）

EEBO-TCP 人工双录入本，CC0，GitHub `textcreationpartnership/<ID>`，存 `src/`：

| 卷 | TCP | 章 | 版次 | 词数（约） |
|---|---|---|---|---|
| 1 | A30572 | 1–3 | 1652「第二版，新校」，R. Dawlman | 33 万 |
| 2 | A77979 | 4–7 | 1650，Peter Cole（「第五书」） | 26 万 |
| 3 | A30574 | 8–10 | 1650，Peter Cole（「第六书」） | 19 万 |
| 4 | A30575 | 11–13 | 1651，Peter Cole（「第七书」） | 20 万 |

巴罗夫讲到 13:11 去世（第四卷卷末「校订者致读者」）；13:12–16 霍尔、第 14 章雷诺兹续完，另成书，不收。

## 证人（原书实物扫描，Internet Archive，400–500 ppi，ABBYY 文本层带词坐标）

| 卷 | 证人 | 藏处 | 与底本 |
|---|---|---|---|
| 1 | `expositionofprop01burr` | 杜克大学（Frank Baker 藏） | **他版**：1643 初版（W. B. and J. G. for R. Dawlman，Caryl 准印 1643-08-10） |
| 1 | `anexpositionpro00burrgoog` | 密歇根大学（Google） | 他版，同为初版系；未用 |
| 2 | `expositionofprop02burr` | 杜克 | 同版 |
| 3 | `expositionofprop03burr` | 杜克 | 同版 |
| 3 | `expositionwithpr00jere` | 西弗吉尼亚卫斯理学院（Asbury 旧藏，1668 年 Joseph Browne 题记） | 同版，第二份 |
| 4 | `expositionofprop04burr` | 杜克 | 同版 |
| 全 | `expositionofprop00burr` | 普林斯顿神学院 | 1863 Nichol 重排本（Sherman 编），现代拼法；只作最后一道旁证，暂未用 |

1652 年版本身网上无扫描（只有 EEBO 胶片，即 TCP 录入所据）。

## 缺字处理（old-book-ocr 第 ②③ 层）

`scripts/burroughs_witness.py`：
1. `pages`：录入本每页 → 证人叶号（3-gram 重合，单调）。
2. `match`：缺字组左右各取约 12 个字符作锚，在证人连写字串里近似定位（ratio ≥ .84，位置唯一），夹在中间的字母与录入本残字逐字母相合
   （ſ/f、u/v、i/j 同形），补出的词须在录入本里另见 ≥2 次——**判词典不兜底**（`•in` 被 ABBYY 读成 `iin`、判词典接成 `jin`，影像是 ſin）。
3. 抽样看图（2026-11-26）：同版 32 条中看得到的 26 条全对；初版 16 条中看得到的 15 条全对。整类落盘：同版 → `gap_review.tsv`（依据「证人OCR」，排正文）；
   初版 → `gap_approved.tsv`（「初版同处」，加方括号）。
4. 其余逐条裁图看（`sheets` → `put`）：同版影像读出的进 `gap_review.tsv`（「看图」）；第 1 卷读的是初版影像，进 `gap_approved.tsv`（「初版影像」）。
   扫描本同处也残缺的记 `?`，备注写 `P:推断`，不落。裁片里看不到缺字的记 `witness_seen.tsv`，换裁法再看。
5. 录入本字数或分词与影像不合的（`mad•` 影像作 make、`a• m•` 影像作 such a time），整组按影像写，备注注明。

## 原书误植

照录（与格林希尔同政策），只在 `PROOFREAD_STATUS.md` 记一笔。

## 扉页（manual_pages/）

四卷扉页照原书影像手排（old-book-ocr §5.7），录入本抽出的扉页压成一段、还丢行，不用。
第 2–4 卷对杜克藏本同版扉页（02/03/04 各卷 n6、n6、n4）逐行排：字号、加宽字距、花线、出版人两栏大括号。
第 1 卷 1652 再版无影像：文字与分行照录入本，字号参照 1643 初版扉页（01 n4），页内注明与初版的出入。
