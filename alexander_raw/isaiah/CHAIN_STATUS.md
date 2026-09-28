# 以赛亚链条现状：**不能重跑**（2026-09-28）

`bash scripts/chain_alexander_isaiah.sh` 现在能跑完并退出 0，但**跑完的产物比
跑之前差**。在修好下面列的回归之前，不要拿它重建 `alexander/isaiah/`。

## 怎么发现的

抽查卷二六张书页（`isaiah_page_proofread.py`）捞到 8 处真错，按规矩落进
`manual_fixes.tsv` 后重跑链条落盘——第一次就崩在这里：

```
✗ raw_fixes 第 2 章命中 0 次（应为 1）：'impart to this whole psalm a highly dramatic character'
```

`publish_alexander_en.py` 的 `RAW_FIXES` 写死成 `alexander_raw/psalms/raw_fixes.tsv`，
发布以赛亚时拿**诗篇**的补丁去匹配以赛亚第 2 章。这是 2026-09-23 给诗篇加
raw_fixes 时带进来的，**以赛亚的链条从那天起就跑不动了**，一直没人发现——
因为没人重跑过。已改成按书取表（`raw_fixes_path(book_id)`）。

修好之后链条跑到底，拿跑前快照逐词 diff，**94 处差异，其中大半是回归**。
证据留在 `logs/alexander_isaiah_chain_regression.tsv`（旧串 / 新串 / 待判定）。
产物已回滚到重跑前（`git checkout -- alexander/isaiah`），8 处判读结果
**直接落在已发布正文上**——这是明知故犯地欠下「判读只改产物＝没落盘」那笔债，
因为另一个选择是把 94 处回归留在页面上。条目同时写进了 `manual_fixes.tsv`，
链条修好后按正常机制落一遍即可，届时那 8 处应当原地不动。

## 重跑会引入的回归（按严重程度）

| # | 形态 | 规模 | 例 |
|---|---|---|---|
| ① | **整段消失** | 已知 1 处 | 第 42 章 v.2 整段（约 2000 字符）变成 `V..` |
| ② | **真词被改成非词 `be`→`le`** | 5 处 | `there shall be five cities`→`le five`、`lest your bands be strong`→`le strong`、`Jehovah be mighty`→`le mighty`、`I will not be still`→`le still`、`shall return and be for a consuming`→`le for` |
| ③ | **句末收引号被删** | 约 40 处 | `'is spiritually called Sodom' (Rev. 11: 8)` → 收引号没了；`the reproach of widowhood'` → 同 |
| ④ | 撇号/句点被动 | 2 处 | `praeteritum propheticum`→`prophetic.um`；`(pip';»r:>`→`(pip;»r:>` |
| ⑤ | `i.e.`→`i. e.` 归一 | 约 20 处 | `IE_SPACE` 是**按诗篇语料**定的体例（诗篇 736 带空格 / 165 不带）。
以赛亚没量过频次就跟着改了——**先量再用**，别照搬诗篇的结论 |

①②③ 是必须堵死的：②这一类本该被「逐词回退」闸拦下（诗篇那条线有
`psalms_regress_check.py`，以赛亚**没有对应的闸**）；③会连带毁掉引号配对。

顺带被重跑修对的（说明链条本身也有积累的进步，不是全盘退步）：
`bepaid`→`be paid`、`bar boured`→`harboured`、`Hor ace`→`Horace`、
`Epipbanes`→`Epiphanes`、`ch'. 35`→`ch. 35`。

## 修的顺序

1. 先给以赛亚补**逐词回退闸**（照搬 `psalms_regress_check.py`），否则②这一类
   下次还会悄悄写进去。
2. 查 ③ 的来源：`isaiah_english_rescan.py --apply` 与 `adjudicate` 都会动标点，
   诗篇那边踩过「重扫把读数两端的标点还回去」（chain 脚本注释里写着），
   这次很可能是同一个坑的另一个形态。
3. ① 单独查：`V..` 说明 `split_runon_verse` 或节号识别把整段吃了。
4. ⑤ 按 [[feedback_measure_before_applying_rule]] 先量以赛亚自己的频次。
5. 都修完再跑一次，与 `logs/alexander_isaiah_chain_regression.tsv` 对账，
   只剩「修对的」那几类才算过。

## 另外量到的

`alexander/isaiah/*.md` 里 **70 个文件有 36 个星号个数是奇数**——至少有一个
落单的 `*` 会在页面上显示成字面星号。诗篇那边这一类是靠渲染后的 `<em>` 查的
（数星号分不清开闭，但**奇偶**是硬的）。以赛亚没做过这项检查。
