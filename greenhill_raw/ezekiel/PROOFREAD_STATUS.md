# 格林希尔《以西结书释义》抽章实读记录（old-book-ocr §4.5）

收敛判据：连续 5 个随机抽章，每章错处密度 < 1 处/页。底本 EEBO-TCP 人工录入本；对照 EEBO 胶片（IA bim）整页图，每页只读一次。

| 轮 | 抽章 | 卷 | 原书页 | 页数 | 本章错处 | 每页 | 全书同类 |
|---|---|---|---|---|---|---|---|
| 1 | 16-60 | 3 | — | — | 版式（此前一轮，按 §3.3a 排版对齐，未逐页计错） | — | — |
| 2 | 32-1 | 5 | 61–74 | 14 | 7 | 0.50 | 见下 |

## 第 2 轮：32-1（2026-11-25）

本章 7 处：
- 录入本错字 5：`catch chat old`→that、`fighing`→sighing（ſ 录作 f）、`Chaldaans`→Chaldaeans（æ 漏 e）、`Jehosaephat`→Jehosaphat、`2 Chr. 1.8.`→18.
- 版式 2：章标题 `CHAP. XXXII.` 原书正体，产物排成斜体；p.62「1. Is from…」「2. From…」原书缩进成条，产物作普通段（未改，见下）。

全书同类清理：
- 章标题斜体：`head_md()` 加 CHAP. N 判正体，全书 42 处。
- ſ 录作 f：判词典 + 语料自证（f 形非词、换 s 成词且 s 形全书 ≥2 次）全书试跑 17 条，逐条看上下文，落 7 条（confulted defert fense fiege fome luft mifery）；
  其余为拉丁/法文真词（fui fune fus fol）、专名（Flanders）、希伯来转写（Af）或另类问题，不动。
- u/o：`full uf comeliness`→of，1 条。
- 未落、待看图：`af er their`（13-10，第二卷无胶片，疑 after）、`rhe Mediatour`（16-7）、`tbe Prophets`（13-8）——可能是原书误植，按政策照录，须看图才定。
- 已知未改：总括段里的「1. 2.」分条原书缩进，录入本作普通 `<p>`，产物未排成条目。
