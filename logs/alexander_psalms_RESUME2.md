# 亚历山大《诗篇注释》英文底本 —— 续跑说明（2026-09-23 暂停）

## 现在是什么状态

九道闸全绿，链条幂等。一条命令全量复现：

```bash
bash scripts/chain_alexander_psalms.sh
# publish → adjudicate_ocr → hebrew → image(--replay) → manual
# 验收：跑完 alexander/psalms/*.md 逐字节不变
```

| 闸子 | 命令 | 现状 |
|---|---|---|
| 链条幂等 | 连跑两次 `chain_alexander_psalms.sh` 后 `diff -rq` | 逐字节不变 |
| 逐词回退 | `psalms_regress_check.py [rev]` | 无「真词改成非词」 |
| 渲染层 | `psalms_render_check.py` | 全部通过，锚点 2446 |
| 账目 | `psalms_backlog.py` | 非词 6（判读 3 + 已核实原样 3） |
| 双标点 | `psalms_double_punct.py` | 0 |
| 引号配对 | `psalms_quote_marks.py` | 0（另 21 处印面如此） |
| 引用格式 | `psalms_refs_check.py` | 0 |
| 引用范围 | `psalms_ref_range.py` | 0（另 8 处印面如此） |
| 显示节号 | `psalms_vnum_check.py` | 全部连号（另 1 处印面如此） |
| 括号残渣 | 见下「一次性扫法」 | 0 |

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

1. **斜体检测**（ABBYY 不稳）。已量：渲染后虚词斜体 286 处，其中「孤立」13 处
   已逐处核完（真误判 4）。**剩下 273 处成簇出现的没有逐处核**，抽样 3/3 正确。
   要继续就把「孤立」的阈值放宽（140 字符 → 60 字符）再筛一轮。
   括号补词那 1350 处已由 `psalms_italic_parens.py` 处理过。
2. **逐页实读**。两个新判据（引用范围、显示节号）证明「闸子只看得见已知类型」：
   六道闸全绿之后仍捞出 400 余处。为引号任务读的约 50 张裁图里顺带发现 9 处
   无人报告的错（约 8 页 → **每页约 1 处**）。全书 558 页，这是残留量的可用估计。
   下一条最可能有产出的判据：**跨页处的吞字/并词**（`Andbrought`、`enenies`
   这类已经撞见过），以及**页眉/页脚残留**（已清 3 处，判据只覆盖 `*Psalm N:M*` 一种形态）。
3. **中译 11–150**（140 篇）。`translate_alexander_psalms.py` → `publish_alexander_psalms_zh.py`。

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
