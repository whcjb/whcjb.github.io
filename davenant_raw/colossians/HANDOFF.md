# Davenant 校勘：当前进度与恢复指引

最后更新：2026-09-15。上一次可用提交 `a7f7d2229`（正文第一到三章那一轮）。

## 一句话状态

规则与人工核定表都已就绪并逐条试跑验证过，**但已发布的 md 是用旧规则建的**
（产物 09-15 11:26，脚本 09-15 14:27）。恢复工作时**第一件事是重跑完整重建**。

## 立刻要做的三步

```bash
# ① 从干净基线重建（约 45 分钟，四段：正文→发布→附卷→索引）
git checkout -- davenant/colossians davenant_raw/colossians/davenant_colossians_{structured,appendix,index}.txt
bash scripts/davenant_rebuild_all.sh
# ② 验收
bash scripts/davenant_verify.sh
# ③ 逐条核 verify 里「词→词改动」那一档，没问题就提交
```

三个工具脚本都已入库，不在 scratchpad 里：

| 脚本 | 做什么 |
|---|---|
| `scripts/davenant_rebuild_all.sh` | 四段重建：正文抽取→发布→附卷→索引 |
| `scripts/davenant_verify.sh` | 五关验收：回退闸 / 结构闸 / 渲染层 / 已识别错误类残留普查 |
| `scripts/davenant_dryrun.py` | **加任何新规则后必跑**：把规则在全书 3.3 万行上试跑，按规则分类列出它想改的全部改动 |

## 这一轮做了什么

按用户要求「按章分段读——读一段修一类」，用眼睛读完了
**第四章、附卷七章、法国之争、六种索引**（前三章是上一轮读的）。

### 新增规则（`scripts/davenant_witness.py`，除非另注）

| 规则 | 修什么 | 量级 |
|---|---|---|
| `quote_repair` | 前导双引号 `"The` → `The`（原书用斜体标引语，正文根本不排双引号） | ~100 |
| `ifit_repair` | `Jf/Jt/?f/[t/[f/Js/?s/[s/Jn//f//t/\|f/\|t/!f` → If/It/Is/is/In | ~40 |
| `iglyph_repair` | 孤立大写 `I` 被读成 `l \| ] [ 1 4 J L / Y i`，靠**闭合动词表**定位 | ~25 |
| `one_repair` | 书卷序号位 `] Cor.` → `1 Cor.` | 7 |
| `romanref_repair` | 引文位罗马数字 `in./ill./i1./iw./ti./vill.` | 5 |
| `fndot_repair` | 功能词后多余句点 `power of. the` | ~35 |
| `fw_repair` | 短功能词读花 `ts→is` `aud→and` `bv→by` | ~570 |
| `letter_repair` | 词内单字母字形 `servaut→servant`（≥6 字母） | ~200 |
| `apos_head_repair` | `T'he` → `The` | 少量 |
| `glue_repair` 扩充 | `A//`→`All`、`£o/(o`→`to` | 13 |
| 逐位粘连 | 证人在该处拆成两词且我方不是词 → 采信 | ~15 |
| `STRAY_PUNCT` 扩充 | 加 `: ! ) ° · ' '` | ~25 |
| 书眉剥离（提取器） | `250 AN EXPOSITION OF $T. PAUL'S Chap. iv.` 嵌在段落中缝 | 19 |
| `HYPHEN_SPLIT`（提取器） | `ef- fect` → `effect` | 11 |
| `DOT_SPLIT`（提取器） | 换行连字符被读成句点 `Chris. tian` → `Christian` | 26 |
| 点线残渣（索引） | 硬/软两档，软档单独出现时不收（那多半是卷号） | ~40 |
| `fix_vol`（索引） | 卷号 `1I./IT./Il./LI.` → `II.`，按**笔画数**还原 | ~48 |
| `qa_davenant_regress.py` | 新增「词→词改动」一档报告 | — |

`davenant_raw/colossians/manual_votes.json`：**157 条**按位置核定的条目
（键是 `卷\|扫描页号\|词形`）+ 11 条 `_` 开头的「不要改」备注。

### 五次差点改坏，都被回读或全书试跑拦下

| 改坏的 | 处数 | 根因 | 补的守卫 |
|---|---|---|---|
| `bad`→`had` | 21 | 短功能词规则缺「本来就是词」 | 加 `attested`；**不能**用「本书里 bad 出现 0 次」当判据——语料就是被改坏的产物，判据自我强化 |
| `member`→`memher`、`Mediator`→`Mediafor` | 12 | 断词跨行，后半 `ber,` 孤立看像 `her,`，`dehyph` 一接成假词 | 行首与带连字符的 token 不碰 |
| `Galat.`→`Gala†.`、`Rhet.`→`Rhe†.` | 8 | 词尾脚注符规则收了 `t` | 撤回——拉丁缩写多以 t 结尾 |
| `4to.`→`4to`、`No.`→`No`、`A.`→`A` | 5 | `_norm` 剥掉数字大小写，`4to.` 看着就是 `to.` | 判据改看原串 + 人名缩写/编号两道 |
| `NS`→`us`、`SOR`→`for`、`Hab.`→`Has.` | ~180 | 全大写碎片被当读花的功能词 | 全大写不碰 + 圣经/引书缩写表 |

**方法上最值钱的一条**：后两组是「把规则在全书上试跑一遍、把它想改的全部
列出来逐条看」才发现的，抽样看不出来。恢复后新加任何规则都要走这一步
（`scripts/davenant_dryrun.py`）。

另有一处判据问题：`web2` 只收词元，`withdrew` `interred` `bidden`
`qualifies` `dented` `proscribed` 查过去全是 False，于是这些**真词**被
`letter_repair` 列进候选。补了 `_stems()` 反向还原词干（不规则表 + 辅音重复
+ y→ies）。⚠️ 这条**只挂在 `letter_repair` 里，不能进全局 `attested`**：
`uppoint` 与 `loud` 也在 web2 里，进去会把 `uppointed`/`louded` 这两个
文件里记着的反例一起判成真词。

### 查出来「原书如此」，没改

- `Suares`（全书 14 次 vs `Suarez` 1 次）、`Auverne`（3 vs 1）
- `Levins` —— 书末勘误表自己写着「Page 325, Note, line 2, for Levins, read Lerins」
- `withcrafts`、分号冒号前的空格（19 世纪英式排法，全书 2070 处）

## 已知残留（都量化过，别当成没查）

1. **15 页、478 行编者长注落在正文里**，还被一行一段拆开
   （v1 p81/103/160/172/214/255/256/260/263/343/440/506/621、v2 p329/468）。
   成因与三次失败的补救尝试写在 `scripts/extract_davenant.py` 的 `split_page` 里。
   要修得先统一 `fn_max` 在管线内外的口径，再拿这 15 页当基准集。
2. 索引里判不出原文的：`Ape, Christ the head of`（首条条目词）、
   `Grabbon`、`Staphilus … 994`、`II. To Afilictions` 里那个被读花的页码。
3. `v2p355` 的 `put at from you`（应为 `put it`）——`at` 在同页出现 3 次，
   按页定位会落错处。
4. `v1p315` 的 `Wi. de`（原文 `Vide`）——W→V 已按位置修，但后半的 `de` 接不
   回去：`DOT_SPLIT` 有意不碰以 `de` 打头的后半（拉丁引文虚词靠它保住）。
5. 希腊文：互证不过的片段一律保留拉丁乱码，不采信。这是有意的。

## 验收口径

- `qa_davenant_regress.py`：逐词回退必须 **0 处**；「词→词」那一档要逐条核
  是不是人工核定的（规则本该只把非词修成词）。
- `qa_davenant.py` / `qa_davenant_appx.py`：结构闸 A–G。
- 渲染层：脚注配平、`<div>/<span>/<em>/<p>` 配对、无私用码残留、无重复锚点 id。

## 用户还在等的事

中文翻译仍**停着**（用户在本任务开始时说「中文先别动」）。`zh_cache` 里有
438 个已译块，zh 页面还建在旧英文上。英文这边收尾后才谈中文。
