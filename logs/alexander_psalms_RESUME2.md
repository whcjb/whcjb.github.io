# 亚历山大《诗篇注释》英文底本 —— 续跑说明（2026-10-08 更新）

## 现在是什么状态

九道闸全绿，链条幂等。一条命令全量复现：

```bash
bash scripts/chain_alexander_psalms.sh
# publish → adjudicate_ocr → hebrew → image(--replay) → manual
# 验收：跑完 alexander/psalms/*.md 逐字节不变
```

| 闸子 | 命令 | 现状（2026-09-28 复跑） |
|---|---|---|
| 链条幂等 | 连跑两次 `chain_alexander_psalms.sh` 后 `diff -rq` | 逐字节不变 |
| 逐词回退 | `alexander_regress_check.py [rev]` | 无「真词改成非词」 |
| 渲染层 | `psalms_render_check.py` | 全部通过，锚点 2446 |
| 账目 | `psalms_backlog.py` | 非词 6（判读 3 + 已核实原样 3）；节号单调 ✓；重出干净 ✓ |
| 双标点 | `psalms_double_punct.py` | 0 |
| 引号配对 | `psalms_quote_marks.py` | 0（另 21 处印面如此） |
| 引用格式 | `psalms_refs_check.py` | 0 |
| 引用范围 | `psalms_ref_range.py` | 0（查过 3916 条，另 8 处印面如此） |
| 显示节号 | `psalms_vnum_check.py` | 全部连号（另 1 处印面如此） |
| 拉丁乱码残渣 | `psalms_garbage_sweep.py` | 0（不看在不在括号里） |
| 译本引文丢斜体 | `psalms_italic_lost.py` | 0 |
| 结构四条 | `psalms_structure_sweep.py` | 书页连续 ✓／并词 0／页眉 0／混拉丁 0；近距重出 5-gram 44 处**是给人看的**（全是平行句） |
| 页边界吞整行 | `psalms_pagebreak_gap.py` | 0（558 个页边界；**词级吞并没查**） |
| 孤立虚词斜体 | `psalms_italic_stray.py` | 0（另 9 处印面确是斜体，见 `italic_printed_italic.tsv`） |

## 这一轮（2026-09-22~23）清掉了什么

| 类 | 处数 | 判据落在哪 |
|---|---|---|
| 段内引号配对不上 | 76 | `psalms_quote_marks.py` + `quote_print_unbalanced.tsv` |
| 双句点 `Ps.. xxxii` | 61 | 补 `psalms_double_punct.py` 的 `'..'` 分支 |
| 引用格式（书卷逗号/大写罗马/逗号无空格/缩写句点） | 291 | `psalms_refs_check.py`（按语料频次自校准） |
| 罗马 50 的 `l.` 读成 `1`/`I` | 44 | 同上 |
| 引用数字误读（清一色 3→8） | 37 | `psalms_ref_range.py`（和合本当尺子 + 希英节号差） |
| **整节丢失**（节号认不出→无锚点） | 11 | `psalms_vnum_check.py` + `raw_fixes.tsv` + publish 的 `split_runon_verse` |
| 页眉串进正文 | 3 | manual_fixes |
| 真词错（hones/hook/hy…） | 10 | `psalms_realword_witness.py` → 影像定案 |
| 括号里的希伯来残渣 | 24 | 逐张 600 dpi 裁图读原文 |
| 斜体误判 | 4 | 渲染后 `<em>` + 孤立性筛 → 影像 |

**根因治了一处**：`adjudicate_alexander_image._absorb_dup_punct` —— 影像读数自带的
句点与正文原有的重出，全书造出 47 个 `..`。修完双标点规则从 57 条降到 10 条。

## 三个台账（「已有结论的桶不再被后续判据覆盖」）

- `alexander_raw/psalms/quote_print_unbalanced.tsv` —— 印面自己不配对的引号 21 处
- `alexander_raw/psalms/ref_printed_as_is.tsv` —— 引用超范围但印面如此 9 处
- `alexander_raw/psalms/raw_fixes.tsv` —— 节号本身读坏、须在 transform 前打的补丁 4 处

闸子都按**精确形态**放行（引号按个数、引用按规范化串、节号按篇+号），
那一段一变就重新报，不会把「查过」悄悄变成默许。

## 还开着的

0. ~~开斜体贴着词距，整节译文的斜体在页面上全丢（6 篇）~~ **已清（2026-10-08，`1dc72fb7f`）**。
   `<span class="ax-vnum">6.</span> * Then shall I not be shamed…` —— kramdown
   要求开的那个 `*` 右边紧跟非空白，否则它根本不是强调，**两个星号原样印在
   页面上**。既有的「`<em>` 首尾带空白」看不见它：这里压根没有 `<em>` 生出来。
   诗 **35 / 91 / 96 / 119 / 126 / 132** 六篇中招（以赛亚同样 4 章，已修）。

   修法已经落在共用的 `publish_alexander_en.py` 里（`OPEN_STAR_SPACE`，
   把「空白 + 星号 + 空白」归一成「空白 + 星号」），
   `alexander_render_check.py` 也补了这道闸。
   2026-10-08 重跑了 `chain_alexander_psalms.sh`：**除这 6 处外产物逐字节不变**
   （诗篇不像以赛亚那次，已提交正文确实就是链条跑出来的），连跑两次幂等，
   十四道闸复跑全绿。

1. **斜体检测**（ABBYY 不稳）。已量：渲染后虚词斜体 286 处，其中「孤立」13 处
   已逐处核完（真误判 4）。**剩下 273 处成簇出现的没有逐处核**，抽样 3/3 正确。
   要继续就把「孤立」的阈值放宽（140 字符 → 60 字符）再筛一轮。
   括号补词那 1350 处已由 `psalms_italic_parens.py` 处理过。
2. **逐页实读**。两个新判据（引用范围、显示节号）证明「闸子只看得见已知类型」：
   六道闸全绿之后仍捞出 400 余处。

   **覆盖台账（续做前先看这张表）**

   *（a）整页影像比对* —— `psalms_page_proofread.py`，把页面影像和我们的正文
   一起送去只问「哪里对不上」，两遍独立跑、只取两遍都报的：

   | 轮 | 覆盖 | 产物 |
   |---|---|---|
   | round 1 | **书页 14–572 全书 558 页** | `logs/alexander_psalms_page_round1.tsv` |
   | round 2 | 476 页 = round 1 报过差异的**全部** 475 页 + 书页 17 | `logs/alexander_psalms_page_round2.tsv` |
   | 两遍交集 → 单点候选 | 涉及 247 页、381 条 | `logs/alexander_psalms_page_candidates.tsv` |
   | 两遍交集 → 须人工的 | 涉及 173 页、232 条 | `logs/alexander_psalms_page_manual.tsv` |

   **两遍是这么分工的（2026-09-28 核实，改正前一版的误判）**：
   round 2 是带 `--only-hits` 跑的——**只重跑 round 1 报过差异的那 475 页**。
   round 1 报 NONE 的 83 页不跑 round 2，因为这一层只取两遍都报的，
   交集必为空，跑了也出不来东西。核对过：round1 报过差异的 475 页
   **一页不缺**都有 round 2。所以**这里没有覆盖缺口**。

   真正的缺口只有一个，已补：
   · **书页 24** —— 当时 `<!-- PAGE 24 -->` 标记整个丢了（见 `13f5d1c87`），
     抽页按标记取页就取不到它，两轮都没跑过。标记补好后 2026-09-28 补跑两轮，
     **捞到 1 处真错**：诗 2「第一节 (ver. 1-8)」印面是 `(ver. 1-3)`——
     同一句里第二节写 4-6、第三节写 7-9，文内自证，属已知的「3 被读成 8」那一类
     （`psalms_ref_range.py` 查不到它：诗 2 有 12 节，1-8 不越界）。
     另 1 处 `Rom ix. 4.)` 印面无句点，按全书缩写句点的归一取舍留作现状。

   **这一层剩下的软肋不是覆盖，是「NONE 不可信」**（见 memory
   `feedback_model_none_unreliable`）：83 页靠 round 1 一家之言判定干净，
   而诗 10 引号那次两遍都报 NONE、影像上印得清清楚楚。要加固就重跑这 83 页的
   round 2（实测 $0.07/页、12 秒/页 → 约 $6、17 分钟），把它们也变成两证人。

   *（b）人眼逐字实读* —— 影像比对只报「对不上」，它读不出的类型（斜体丢失、
   缺空格、孤立字母）只能靠眼睛：

   | 日期 | 书页 | 捞到 | 由此产出的判据 | commit |
   |---|---|---|---|---|
   | 2026-09-22 | 引号裁图约 50 张（约 8 页，页号未记） | 9 | —（当时只逐条修） | 引号那轮 |
   | 2026-09-23 | 61、193、331、472 | 40 | `psalms_italic_lost.py`（引文括号丢斜体 29）、页眉补 `Psalm] N:M` 形态、`hy→by` | `e2f8a8d5c` |
   | 2026-09-23 | 61（复读） | 2 | 逗号被读成句点 | `3a7dba834` |
   | 2026-09-24 | 137、404 | 44 | 逗号/括号缺空格（28，含「逗号前不能是单字母词」护栏）、孤立单个拉丁字母（16） | `3721075e8` |

   **有页号的实读 6 页 / 558**（约 1%），平均每页 7 处——注意这 6 页
   **全都在影像比对跑过之后**，也就是说人眼捞到的是影像比对这一层也漏掉的。
   每次实读都带出一整类新判据，全书扫一遍才是大头，所以「每页 7 处」
   不能直接乘 552 当残留量，但剩余数百处这个量级是站得住的。

   下一条最可能有产出的判据：**跨页处的词级吞字/并词**
   （`psalms_pagebreak_gap.py` 已查过「整行被吞」，558 个页边界 0 处，
   但**词级的吞并没查**）；以及**页眉/页脚残留**（已清 5 处，判据现覆盖
   `*Psalm N:M*` 与 `*Psalm] N:M*` 两种形态）。

3. ~~斜体没闭合 5 段~~ **已清（2026-09-28）**。判据是「一段里未转义星号个数为
   奇数」——数星号分不清开闭，但**奇偶是硬的**。既有的「`<em>` 过长」一段也没报出来。
   五处逐一翻了 1864 影像（$0.04/页，问「这个短语是正体还是斜体」）：
   · 诗 127:5 整节译文是斜体，开斜体的星号在 OCR 里丢了 → `raw_fixes.tsv`
   · 诗 51 `"If thou wilt open my lips, my mouth"` 影像上是**正体**（同页
     `open thou my lips`、`thou shalt open my lips, O Lord`、`Open my lips` 才是斜体）
     → 删掉那个星号
   · **另外三处是我们自己的修复带偏的**：诗 48 的 `(mizmor)→(mizmôr)*` 手误多打一个星号；
     诗 87 的 `(or *hy)→(or *by*)` 多补一个收星号，把整条标题的斜体劈断
     （影像：只有 `(or` 是正体，`by` 起到 `His foundation` 全是斜体）；
     诗 36 把希伯来两词换回正序时留下一个没人配对的星号。
   **教训**：修复表自己也会制造错误，而且这一类错**只有奇偶判据看得见**。
4. **中译 11–150**（140 篇）。`translate_alexander_psalms.py` → `publish_alexander_psalms_zh.py`。

## 判读一次要花多少（2026-09-28 实测）

`psalms_page_proofread.py` 的每次调用（300 dpi 整页图 + 该页正文 ~4.2k 字符）：

| 项 | 量 |
|---|---|
| 输入 | 5,261 token（其中 **图约 3,130**、正文约 1,000、system prompt 约 450、CLI 前缀 265） |
| 输出 | 1,038 token（**1,033 是 thinking**，正文答案就 "NONE" 5 个 token） |
| 费用 | **$0.07 / 页**，12 秒 / 页 |

**CLI 上下文已经砍干净**：四开关齐全（`--safe-mode --strict-mcp-config
--disallowedTools '*' --system-prompt`），裸 prefix 实测 **265 token**，
MCP 一个不加载、工具全禁。不砍的话是 2.9 万 token/次（见 memory
`feedback_trim_claude_cli_for_translation`）。

**还能省但不建议动的**：图按 300 dpi 渲染，服务端没有替我们缩小，
按像素计费——降到 200 dpi 省约 1,100 token/页（成本降三成），
但判读靠的就是字形细节，为省几块钱换判读质量不划算
（见 memory `feedback_native_resolution_first`）。

## 一次性扫法（不在链条里，随手可跑）

```bash
# 括号里还有没有拉丁残渣
python3 - <<'PY'
import re,glob
for f in sorted(glob.glob('alexander/psalms/*.md')):
    t=open(f,encoding='utf-8').read()
    for m in re.finditer(r'\([^()]{1,26}\)',t):
        s=m.group(0)
        if re.search(r'[֐-׿Ͱ-Ͽ]',s) or re.match(r'^\([0-9ivxlcdm ,.\-–—]+\)$',s): continue
        if re.search(r'[\^\]\[|}{<>~`\\]|\d[A-Za-z]|[A-Za-z]\d',s): print(f,s)
PY

# 渲染后的虚词斜体（数 markdown 星号是数不清开闭的，必须过 kramdown）
```

## 教训（已写进 memory）

- **闸子只看得见已知类型**：说「处理完了」之前先问「有没有一整类判据我根本没写」
- **新判据先量频次再用**：「书卷缩写后应有句点」按直觉写会改坏 114 处
- **模型报「没有」不可信**：让它读影像判有没有某标记，NONE 必须自己复核
- **数星号分不清开闭**：斜体一律看渲染后的 `<em>`
