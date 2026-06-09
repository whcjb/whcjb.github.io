# PDF to Markdown + 发布到网站（含中文翻译）

把 Calvin 注释 PDF 加工成网站发布产物。**这里是入口**——本文件只做决策与必查清单，详细方法在 `pdf-pipeline/` 各步骤文件。

---

## ⛔ 起手 STOP

**不许在没读完 §1 + §2 之前动手写代码。** 这两节是为防止上次的低质量产出（preface 一锅烩、跳过现成 helper、不跑 audit 就 commit）。

---

## §1. 任务类型决策树

| 用户要什么 | 必读 step（按顺序）| 跳过 |
|---|---|---|
| 新 PDF → 完整发布英文 | `01-diagnose` → `02x-extract-...` → `03-publish-en` → `06-finalize` | translate |
| 已有 raw → 重发布英文（修 bug、改样式）| `03-publish-en` → `06-finalize` | extract / translate |
| 英文已发布 → 翻译中文 | `04-translate-zh` → `05-publish-zh` → `06-finalize` | extract |
| 只重抽 preface / 单 section | `02x-extract-...` 限定页范围 → 手工修订 → `06-finalize` | 翻译 |
| 修 verse-nav / scripture-table 样式 | 改 `_layouts/calvin-en.html` → `06-finalize` | 全部 step |
| 修 bug（用户反馈某处不对）| 先读 `pdf-pipeline/refs/anti-patterns.md` 找对应 Trigger | 漫无目的查文件 |

**根据用户的请求选一行，按顺序读对应 step 文件。其他 step 文件不读，不要参考。**

---

## §2. 起手必查 5 条 checklist

任何任务起手都问自己（**心里答完才能开始**）：

1. **PDF 路径已知？** 用户给了？或 `scripts/calvin_extract.py` 的 `VOLUMES` dict 里能查到？不知就询问，不要假设。
2. **格式已分类？** CCEL 单列 / Ages 双语 / 平行福音 / 共观福音？跑 [01-diagnose.md](pdf-pipeline/01-diagnose.md) §2 的 x0 分布脚本。
3. **能用现成 helper 吗？** 看 [pdf-pipeline/refs/helpers.md](pdf-pipeline/refs/helpers.md)。**绝大多数情况都用现成的**——自己写 `page.get_text('dict')` 循环就是 [anti-pattern L](pdf-pipeline/refs/anti-patterns.md#l)。
4. **目标产物是什么？** raw txt？发布英文？发布中文？index 更新？精确范围一句话说清。
5. **本任务对应哪条 §0 原则？** [pdf-pipeline/refs/principles.md](pdf-pipeline/refs/principles.md) §0.0–§0.6 中任何一条。说不清 → 八成要踩坑。

---

## §3. commit 前必跑 gate

**每次 commit 必须报 audit 数字到 commit message**。完整脚本见 [pdf-pipeline/refs/audit-gates.md](pdf-pipeline/refs/audit-gates.md)。

最低限：

```bash
F=PATH/TO/FILE.md
echo "1. **** =          $(grep -c '\*\*\*\*' $F)"             # 必须 = 0
echo "2. <<<END =        $(grep -c '<<<END' $F)"               # 必须 = 0
echo "3. split italic =  $(grep -cP '\*[\"\"]\*' $F)"          # 必须 = 0
echo "4. zh fm keys =    $(grep -cP '^[一-鿿]+[:：]' $F)"       # 必须 = 0
echo "5. long para =     $(awk 'NR>20 && length>1500' $F|wc -l)"  # 必须 = 0
echo "6. hyphen-rem =    $(grep -cP '\b\w+- \w+' $F)"          # < 5
ref=$(grep -oE '\[\^[0-9]+\]' $F | grep -v ':' | sort -u | wc -l)
def=$(grep -cE '^\[\^[0-9]+\]: ' $F)
echo "7. fn ref/def =    $ref/$def"                            # 必须相等
```

**任何 gate 不通过 = 不能 commit**。回 [refs/anti-patterns.md](pdf-pipeline/refs/anti-patterns.md) 找对应 Fix。

---

## §4. 反例 Trigger 简表（看到这个就立刻重做）

完整版见 [pdf-pipeline/refs/anti-patterns.md](pdf-pipeline/refs/anti-patterns.md)。最常踩：

| 看到 | 是什么坑 | 立刻 |
|---|---|---|
| `*"*X*"*` 在输出 | 引文引号 italic split (§0.5) | 跑 `_fix_split_italic_quotes` |
| `****` 四星 | abut-bold 没合并 (§0.4) | `result.replace('****', '')` |
| `<<<END` 在 md | Claude 翻译杂质 | publish transform 剥掉 |
| `章：N`/`上一节：N` 在 front-matter | Claude 翻 fm 键名 | publish transform 加 `fm_key_fixes` |
| 单元格混栏（Mark 文本漏到 Matt 列）| 灾难块 (§0.6) | hand-fix 按 PDF 节号重组 |
| `<p>` > 1500 字符 | 段落没拆分 | 跑 `split_lines_by_paragraph_indent` |
| 自己写 `page.get_text('dict')` 循环 | 偷工绕过 helper | 去 [refs/helpers.md](pdf-pipeline/refs/helpers.md) 找现成 |
| scripture 表横向滑动 | 用了 calvin-scripture 而非 scripture-table | 改 class + 加 `table-layout: fixed` |
| navy 引文 `<p>...</p>` 后单独跟 `<span>(Genesis 1:1)</span>` | bible-ref 跨块没合进 navy 居中段 (§M2) | FOOTNOTE inline-cross-ref 路径加 navy quote 特例（注入到 `</p>` 前）|
| 全大写短语 ("ON THE SON" / "OF MAN,") 跨段被拆 | 同 style span 跨 block + 大写起首被 merge 拒 (§M3) | `_starts_with_continuation` 加同 sty 续接 + 全大写续接两信号 |
| `[^fN]: </span> "body..."` 字面 `</span>` 残留 | extractor 给 ftN 上色 + normalize_back_footnotes 切错 boundary (§M4) | structured_to_md 剥 `<sty>ftN</sty>` wrap；publish 脚本剥 `<span>ftN</span>` + body 头部 `</span>` |
| 章节中部出现 "signifies Grace." / "Jehohannan, the reader..." / "WHAT WAS MADE was..." 孤儿段 | 后部 fn def 跨多个 PyMuPDF block，BODY/CENTERED 续接被当独立段 (§M5) | converter 加 `pending_fn_idx` 状态机：emit `[^fN]:` 后 arm，下个 BODY/CENTERED append；H1/下个 fn def 清除 |
| 章末出现孤立 "CHAPTER N" 居中标记（PDF 没有）| 后部脚注页页眉 #006411 深绿 CHAPTER N 被 emit 又被 fn def 吞 (§M6) | converter CENTERED_H1/CENTERED_H2 起始 SKIP 内容 `^CHAPTER \d+$` 的块 |
| 用户问"前言怎么没了" | publish 脚本生成 index.html 缺 `has_preface: true` → 目录页前言链接被 `{% if %}` 隐藏 | publish 脚本 Step 7 index.html front matter 必须含 `has_preface: true` |
| 中文翻译 raw 没 chmod 444 | 违反保留规则 | 立刻 `chmod 444` |
| narrow cols 表格 cell 含别 col 内容（Matt cell 含 Luke v27 末尾）| PyMuPDF dict 跨列 span 合并 (§Q) | 用 `page.get_text("words")` 替代 span-level 分桶 |
| cell 内容顺序错乱（跨页时 p11 y=88 排到 p10 y=600 前）| word sort key 漏 page_idx (§R) | sort key 第一字段 = page_idx |
| Luke 16:16 经文出现在 Matt cell | `<td colspan>` 无脑放第一栏 (§S) | 按 cross-ref label `Book N:M$` 路由到对应 col |
| narrow N-col 表格某 cell 含别 col 词（"into their the synagogue" 等 word merging）| col split 用了 label/K-means（内容分布敏感）(§R3) | 改 page 几何等分 BODY_LEFT=74 BODY_RIGHT=538 |
| cell 内容每词出现两次连续（"87 87 that that they they should should"）| PyMuPDF 多 block bbox 重叠，word 被收集两次 (§R4) | build_verse_table 收集时按 (pn, y, x, text) dedupe |
| 续接经文（Mark v11-12 等）跑错 col（Mark 末尾续接到了 Matt cell）| extract 用了 `<td colspan>` 单 col 行 (§R5) | extract 一律 emit per-col `<td>`，不塌成 colspan |
| section header 与 col labels 不对应（A 的 header + B 的 col labels + A+B 内容合并成超大畸形表）| section header x0 阈值 ≥100 过严，x0=99.8 失败 (§R6) | 阈值改 ≥80；size+uppercase 已足够区分 |
| scripture-table cell 含 Calvin commentary 文字（"**4.** *Bear forth fruit*" 风格）| commentary 段头被 is_verse_block 误判 (§R7) | is_verse_block 加 sp1 italic 排除 |
| multi-col 检测把 commentary 含缩进 quote 段误判 multi-col | cluster 数判定不看位置 (§R8) | line.x0 cluster 必须在 page-geom col 位置 ±12px 命中 ≥n_cols-1 |
| 单 col section cell 含整页 commentary 续接 | 跨页 top 续接判定对 single-col commentary 失效 (§R9) | 统计粗体数字 + 紧跟非-italic span 数 ≥ 2 OR 极短块 (h<60px) → scripture |
| multi-col 表后跟着 3-col 交织成段 commentary（v31-32 等暴露在表外） | PyMuPDF 把续接拆成 y-overlap 兄弟 block，同页续接判定漏 (§R10) | 同页续接改用 `page_idx in {buf_pages}` 集合，不再用 `== earliest` |
| multi-col 表某 col 跨页续接（如 Matt v4 末尾「and adulterous nation...」）暴露在表外 | 续接 block 仅 1 col 内容，multi-col layout 检查误杀 (§R11) | cross-page-top + h < 100px 即使非 multi-col layout 也接受 |
| commentary 段中 fn ref 数字（如 `399`）以正常字号出现，且独立成段 | PyMuPDF 把同段拆成两个相邻 block + sup flag 缺失 (§M5c, §P 末注) | handle_commentary 加 y 间距 ≤5px 合并 + ccel_pg_spans_to_md sup 判定加视觉小字号识别 |

---

## §5. 文件布局

```
.claude/commands/
  pdf-to-structured-txt.md        ← 你在这里（orchestrator）

  pdf-pipeline/
    refs/                          ← 通用参考（任何 step 可引用）
      principles.md                ← §0.0–§0.6 全局原则
      helpers.md                   ← calvin_extract / harmony_utils 函数索引
      anti-patterns.md             ← 反例 Trigger 全表
      audit-gates.md               ← commit 前 grep 检查脚本

    01-diagnose.md                 ← Step 1：PDF 格式诊断 + 起手清单
    02a-extract-ages.md            ← Step 2a：Ages 双语 PDF（phil/heb/john）
    02b-extract-ccel.md            ← Step 2b：CCEL Calvin Harmony（matthew1/harmony3/acts1）
    02c-extract-parallel.md        ← Step 2c：平行福音（harmony2，旧 matthew vol 2）
    03-publish-en.md               ← Step 3：raw → calvin/BOOK-en/
    04-translate-zh.md             ← Step 4：translate_filibi.py 中文翻译
    05-publish-zh.md               ← Step 5：zh raw → calvin/BOOK/
    06-finalize.md                 ← Step 6：index.html + commit + push
```

每个 step 文件 ≤500 行，自带 5 条起手 checklist、必读 ref 链接、完成后 audit 提示。

---

## §6. 资源与约定

### 6.1 项目目录结构

```
/Users/yanpeifa/Documents/whcjb.github.io/
  scripts/
    calvin_extract.py        ← PDF → raw txt（所有 helper 函数）
    harmony_utils.py         ← raw → publish md（段落处理流水线）
    translate_filibi.py      ← 中文翻译执行（含 BOOKS dict 配置）
  calvin_raw/<book>/
    <book>_raw.txt           ← 英文 raw
    publish.py               ← 该书的发布脚本
    zh_chapters/N.md         ← 中文 raw（chmod 444 强保留）
    zh_cache/<md5>.txt       ← 翻译缓存（绝不可删）
  calvin/<book>-en/N.md      ← 英文发布
  calvin/<book>/N.md         ← 中文发布
  _data/calvin_books.yml     ← 书卷列表（中英双语条目）
  _layouts/calvin-en.html    ← 章节页 layout（含 CSS + verse-nav JS）
```

### 6.2 命名规则

- 目录 ID：`harmony-1` / `harmony-1-en`（中文用基础名，英文加 `-en`）
- 中文 book_name 统一：`共观福音（卷N）`
- 英文 book_name 统一：`Calvin on the Harmony of the Evangelists (Vol. N)`
- 序言文件名必须是 `preface.md`（layout 硬编码 `/calvin/BOOK/preface/`）

### 6.3 中文翻译产物强保留（最高规则）

`calvin_raw/<book>/zh_chapters/*.md` 和 `zh_cache/` 绝不可删除或无备份覆盖。重跑全量翻译成本极高。详见 [04-translate-zh.md](pdf-pipeline/04-translate-zh.md) §⚠️。

---

## §7. 工作流程示意

```
PDF
 │ scripts/calvin_extract.py <volume>
 ▼
calvin_raw/<book>/<book>_raw.txt        ← [refs/audit-gates.md] Gate 1 必跑
 │ calvin_raw/<book>/publish.py
 ▼
calvin/<book>-en/*.md                    ← [refs/audit-gates.md] 全 gate 必跑
 │ scripts/translate_filibi.py --book <book> [--chapter N] [--resume]
 ▼
calvin_raw/<book>/zh_chapters/*.md       ← chmod 444 强保留！
 │ publish-zh transform（去 <<<END>>>、****合并、<th> 卷名英→中、fm 键修正）
 ▼
calvin/<book>/*.md                       ← [refs/audit-gates.md] 全 gate 必跑
 │ 更新 index.html + _data/calvin_books.yml
 ▼
git commit（含 audit 数字）+ git push   ← GitHub Pages 1-2 分钟部署
```

---

## §8. 最后

- 读完本文件后，**根据 §1 决策树选 step**，跳到对应文件继续
- 不要回头再读本文件——决策已定
- 完成任务后跑 §3 audit gates，commit message 含数字
- 任何环节卡住 → 查 [refs/anti-patterns.md](pdf-pipeline/refs/anti-patterns.md) 对应 Trigger，不要硬猜
