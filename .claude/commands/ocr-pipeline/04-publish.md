# Step 4: 发布到 calvin/<book>/

把 per-page OCR md 加工成 preface + 1.md..N.md + index.html。

按 harmony-1 / calvin-en layout 标准：scripture-anchor 锚点 + scripture-box
干净经文（CUV）+ `**{书卷} N:V。**` verse-nav 触发标记 + kramdown `[^N]` 脚注。

---

## 推荐脚本

```bash
# 通用 (适合任何 CUV 收录的卷)
python3 scripts/restructure_scan_book.py \
  --book colossians --cuv-book 51 --book-cn 歌罗西书 \
  --raw-dir calvin_raw/colossians-scan \
  --out-dir calvin/colossians \
  --all
```

## 🚫 对**已发布**的书禁止跑 `--all`（最重要的规则）

`restructure_scan_book.py --all` 会**完全覆盖** `out-dir` 里所有文件。如果该书已上线、有人工修复或用户校准过的章节，**禁止重跑 `--all`**——会：
- 覆盖手工修复的孤字段、verse 注释段补回、跨页错位 fix
- 引入 OCR 输入原有 artifact（页眉残留、模型对话残留、ephesians 附录污染等）
- 抹掉用户锁定章节（如 romans ch15/ch16）

**已发布书的正确修复流程**：
1. 跑下面的 Mandatory audit gates 找问题 → 用 `relocate_*` 脚本修
2. 跑 idempotent post-process 脚本 `scripts/fix_<book>_ocr_artifacts.py`
   （参考 `scripts/fix_romans_ocr_artifacts.py`：自动处理 Gate-9 双重主体段 /
   Gate-10 anchor 倒序 / Gate-11 主体段早于 anchor。**重跑安全**，LOCKED_CHAPTERS
   自动跳过）
3. 手工 patch（grep + Edit）脚本无法自动判断的剩余 artifact —— 主要是
   anchor 之后无副本的 Gate-11 case（主体段错位无重复，需要剪贴到 anchor 之后）
4. 修复后再跑一遍 audit gates，0 命中才 commit。**永不**重跑 publish。

实战教训（2026-06-17 romans）：跑了一次 `--all` 覆盖了用户校准好的 ch15/ch16（注入 ephesians 附录 + LLM 对话残留 "好的，这是根据您的要求..."），用户怒批"一上午白搞了"。**永不**重蹈。

锁定章节机制：wrapper 脚本（如 `restructure_romans_scan.py`）应设 `LOCKED_CHAPTERS = {15, 16}`，跑前检查跳过。

## ⚠️ Per-book wrapper（OCR 怪癖隔离）

**重要**：每本书 OCR 都会有书卷特有的版式 / 笔误 / 页眉怪癖（如罗马书
OCR 的 `加尔文集` 笔误）。把这些怪癖塞到通用
`restructure_scan_book.py` 会影响其他书卷的发布输出。

**正确做法**：每本 OCR 书建一个 wrapper 脚本，注入书卷特有的 strip
patterns + extra header alts，再调通用脚本。

参考 `scripts/restructure_romans_scan.py`：

```python
# 罗马书 OCR 特有的 fused-running-header glyphs
_ROMANS_EXTRA_HEADER_ALTS = [r"加尔文集"]  # OCR 笔误：丢了一个 "文"
_ROMANS_EXTRA_STRIP_LINES = [r"^加尔文集\s*$"]

import restructure_scan_book as pub
pub._BOOK_EXTRA_HEADER_ALTS = _ROMANS_EXTRA_HEADER_ALTS

# 默认填好 --book / --cuv-book / --book-cn / --raw-dir / --out-dir
# 调用 pub.main()
```

通用脚本：`restructure_scan_book.py` —— 处理任何书都对的逻辑。
书卷 wrapper：`restructure_<book>_scan.py` —— 注入 OCR 怪癖。
跑 `python3 scripts/restructure_<book>_scan.py --all` 即可。

参数：
- `--cuv-book` = CUV `assets/cuv.json` 的卷号（Genesis=1, Matt=40, John=43,
  Acts=44, Romans=45, ..., Colossians=51, Hebrews=58, James=59, Rev=66）
- `--book-cn` = 中文卷名（用于 verse-nav `**{book_cn} N:V。**` 和
  running-header strip）

默认产出（参 `restructure_scan_book.py`）：
- `calvin/<book>/preface.md`（layout: calvin-en, chapter:0, section_title: 序言）
- `calvin/<book>/1.md ... N.md`（layout: calvin-en, scripture-box + verse-nav）
- `calvin/<book>/index.html`（layout: calvin-book, `has_preface: true`）

---

## 切分规则

- **章页边界**：用 `detect_chapter_first_pages()` 扫 OCR 文件中
  `^# 第N章\s*$`，找各章首页。preface = 第 1 页到 ch1 首页 - 1。
- **节内切分（内容驱动）**：每章按 ~7 verses/section 分段，每段段落根据
  内容里检测到的 verse 号归入对应 section（不靠 page range 猜）。
  关键：检测 `**{书卷} N:V。**` bold prefix OR 用 `_verse_for_opener`
  做 CUV fuzzy 匹配。

---

## ⚠️ Publish stage 必须做的清理（OCR 翻译稿独有）

OCR 输出不像 PDF-pipeline 有 `**{书卷} N:V。**` 干净标记，发布脚本依靠
启发式 (`^\d+\s+<CJK>` 开头）猜测每段属于哪个 verse。这会出错。**必须在
publish 阶段做以下三道清理**：

### 1. Running-header strip — publish 阶段必须再跑一遍

`ocr_assemble.py` 已经 strip 过 assembled md 中的页眉。但
`restructure_scan_book.py` 默认读 **per-page md**（不是 assembled），
所以页眉 leak 会原样进入发布。

**解决**：发布脚本必须接受 `--strip-line PATTERN`（multi-occurrence），
并在 normalize_page 阶段 strip。或者发布脚本默认 strip
**已知模式集合**（罗马书的 `加尔文文集` / `罗马书注释` / 数字页码等）。

发布完成后，跑：

```bash
# audit gate: 检查页眉残留
for f in calvin/<book>/*.md; do
  if grep -E '^(加尔文文集|罗马书注释|约翰福音注释|希伯来书注释)$' "$f" > /dev/null; then
    echo "LEAK: $f"
  fi
done
```

应该 0 命中。如有命中，写后处理脚本清掉，commit + push。

参考曾经的漏网：romans publish 后有 **97 处** `罗马书注释` / `加尔文文集`
页眉混在正文中，是因为 publish 没继承 strip-line 设置。

### 2. Verse-commentary 段落归位（必须！）

OCR **不会** 保留 `**罗马书 N:V。**` 加粗格式，发布脚本的 fallback heuristic
（按段落开头数字匹配 verse）会把段落放错 section。

发布完成后必须跑 **三个** relocation/排序脚本：

```bash
# 1. 章内迁移：v.32 段落被错放到 section 1:22-28 → 移到 1:29-32
python3 scripts/relocate_misplaced_verse_commentary.py \
  --book-cn 罗马书 --dir calvin/romans

# 2. 跨章迁移：v.22-36 段落被错放到 12.md（Rom 12 max 21）→ 移到 11.md
python3 scripts/relocate_cross_chapter_verse.py \
  --book-cn 罗马书 --dir calvin/romans

# 3. 同 section 内排序：v.14 段落出现在 v.9 之前（OCR 段落落地顺序乱）
python3 scripts/sort_intra_section_verses.py \
  --book-cn 罗马书 --dir calvin/romans
```

三脚本都依赖 `VERSE_COUNTS` 表（CUV chapter-max-verse counts）。新书要
在脚本里增加该书的 verse-count dict。

参考实战：
- romans：**93 处章内 + 14 处跨章 = 107 处 misplaced**
- john：**10 处跨 section + 65 处 section 内倒序 = 75 处**（之前漏了 sort_intra_section_verses 这一步，被用户截图打回 "4:14 出现在 4:9 之前"）
- john 第二轮（2026-06-22）：surgical OCR-artifact 修复后 **再生 36 处跨 section 错位**（ch6 v.55 出现在 6:43-49 section 之前，被用户截图打回 "55 怎么在 43，44 前面"）
- john 第三轮（2026-06-22）：surgical 后 **再生 47 处 section 内 verse 倒序**（ch6 v.47 出现在 v.48 / v.49 之后，被用户截图打回 "47 怎么在 48，49 后面"）。
  根因：`sort_intra_section_verses.py` 原算法仅按 marker 段单独排序，**未把
  marker 后的续段（非 marker 的注释续句、bold 小标题如 `**我是活的粮**`）作为
  block 一起搬移**，导致续段被遗弃在原位、与新位的 marker 脱节。已修：把
  "marker 段 + 直到下一个 marker 之间的所有 paras"打包成 block 再排序。
- john 第四轮（2026-06-22）：sort 后 **再生 48 处同 verse 重复 marker**（ch6 v.55
  既有"我的血真是可喝的"又有"我的肉是真正的食物"两段都标 `**约翰福音 6:55。**`，
  用户截图打回 "怎么又是两个"）。
  根因：Calvin 单 verse 多段评注 PDF 原本只第一段带节号，OCR/publish 给所有
  段都加了 `**N:V。**` marker；而 dedupe 脚本 **必须排在 sort 之后**（sort 让
  同 verse 的多段变成相邻，dedupe 才能识别）。历史上跑过 dedupe 但是在 sort
  之前——同 verse 段未相邻，dedupe 误以为不是重复。**正确顺序：sort →
  dedupe**（已写入 §2.1 的"四件套"步骤）。

### 2.1 ⚠️ Surgical 修复后必须再跑 relocate（被反复打回的根因）

**根因**：任何把 `**书名 N:V。**` marker 引入 / 移位 / 还原的 surgical fix，都
会把段落的"实际 verse 归属"信息改变。但段落仍在原 section 区域内。例如：

- bare-digit fix：`^26 你所见证的那位` → `**约翰福音 N:26。** *你所见证的那位。*`
  插入 marker 后段落物理位置没动，但 marker 暴露出"这段属 v.26"——若该 section
  覆盖 v.20-25，relocate 才能发现错位。
- bold-N-phrase fix：`^\*\*48我就是生命的粮。\*\*` → `**约翰福音 6:48。** *我就是生命的粮。*` 同理。
- CUV phrase-collision 修正：把误归 v.35 改为正确 v.59，新 verse 号往往跨 section。
- 章号 hardcode 修复：`**约翰福音 1:V。**` 在 ch6 文件中改为 `**约翰福音 6:V。**`，
  V 可能在 ch6 任意位置，几乎一定有跨 section 错位。
- dedupe / restructure 脚本拆 / 合段后留下的 marker。

**必须强制工序**（写入工序文档；surgical 阶段不可省）：

```bash
# 每次跑完 surgical sed/Edit/restructure 后立即跑四件套（顺序固定！）：
python3 scripts/relocate_misplaced_verse_commentary.py --book-cn <书名> --dir calvin/<book>
python3 scripts/relocate_cross_chapter_verse.py        --book-cn <书名> --dir calvin/<book>
python3 scripts/sort_intra_section_verses.py           --book-cn <书名> --dir calvin/<book>
python3 scripts/dedupe_same_verse_markers.py           --book-cn <书名> --dir calvin/<book>
# 然后跑 Gate-Section-Order 自检（同 section 内 marker 序列 + section 越界）
python3 -c "
import re; from pathlib import Path
book_cn, book_dir = '<书名>', 'calvin/<book>'
issues = 0
for f in sorted(Path(book_dir).glob('*.md')):
    if not f.stem.isdigit(): continue
    ch = int(f.stem); text = f.read_text(encoding='utf-8'); lines = text.split(chr(10))
    sections=[]; verses=[]
    for i,l in enumerate(lines):
        m = re.match(rf'^## {re.escape(book_cn)} {ch}:(\d+)(?:-(\d+))?', l)
        if m: sections.append((i,int(m.group(1)),int(m.group(2)) if m.group(2) else int(m.group(1))))
        m = re.match(rf'^\*\*{re.escape(book_cn)} {ch}:(\d+)。\*\*', l)
        if m: verses.append((i,int(m.group(1))))
    for si,(ln,lo,hi) in enumerate(sections):
        nxt = sections[si+1][0] if si+1<len(sections) else len(lines)
        seq = [v for l,v in verses if ln<l<nxt]
        for k in range(len(seq)-1):
            if seq[k] > seq[k+1]:
                print(f'{f.name}: {lo}-{hi} v.{seq[k]} > v.{seq[k+1]}'); issues += 1
        for v in seq:
            if v < lo or v > hi:
                print(f'{f.name}: {lo}-{hi} v.{v} 越界'); issues += 1
print(f'剩余: {issues}')
"   # 必须输出 "剩余: 0"
```

**Gate-Section-Order 抓两类**：
1. **section 内 verse 倒序**（如 6:43-49 出现 [43,44,48,49,47]）→ sort 脚本未跑
   / 续段未一起搬（[算法 root cause](#23-sort-脚本算法注意续段必须打包)）
2. **section 越界**（如 v.53 出现在 7:50-52 section）→ section 边界 / scripture-box
   经文边界不一致；要么扩 section header 同时扩 scripture-box，要么 relocate
   该 verse 到正确 section

**反例（约翰福音第二轮 root cause）**：用户在多轮对话里手工修了 ch3-21 共 1024
个 `**约翰福音 1:N。**` 硬编码、41 个 bare-digit、15 个 bold-N-phrase、5 个
CUV 冲突 ……每次只做了 marker 修正没跑 relocate，累计 36 段段落物理位置错。
直到用户截图打回 "55 怎么在 43，44 前面" 才发现。

### 2.3 sort 脚本算法注意：续段必须打包

`sort_intra_section_verses.py` 的稳定排序粒度必须是 **commentary block**，
不能是单 marker 段。Block 定义：

```
block = [
    verse-marker para,     # `**书名 ch:V。** *phrase。* commentary...`
    follow-up para 1,      # 续段：bold 小标题（如 `**我是活的粮**`）
    follow-up para 2,      # 续段：续注释正文
    ...                    # 直到下一个 marker para 之前所有 para
]
```

按 block 的 leading verse 号稳定排序——续段会跟着 marker 一起移动，
不会被遗弃在原位置。

**反例（已踩，2026-06-22 修）**：旧算法只把 marker 段单独移动：

```
原顺序 [v.48, v.49, "我是活的粮"续段, v.47]
旧算法排序后 [v.47, v.48, v.49, "我是活的粮"续段]  ← 续段留在原位脱节
正确结果      [v.47, v.48, "我是活的粮"续段, v.49]  ← 续段跟着 v.48 走
```

虽然就 ch6 这例子来看，旧算法结果跟续段当前位置接近（因为续段原本就在 v.48
后面、v.47 前面），但其他章会出 bug：用户当时打回 "段落都搞错了" 就是这个
原因，致我退缩不敢全跑 sort，留下 47 处倒序。修后算法对 ch6 输出
character byte 数完全不变（39924），仅顺序更新。

### 2.4 publish 阶段为何会产出乱序？（最深层根因）

`restructure_scan_book.py` 在 OCR raw → published md 时按 verse-anchor 启发
（CUV phrase fuzzy match）把每段塞进 section，但**段落顺序保持 OCR 物理顺
序**——而 OCR 物理顺序受以下三个噪声破坏：

1. PDF 跨页时下一 verse 注释开头被粘在前 verse 末段（OCR 拼页）
2. 脚注溢出 / 页眉 leak 把不连续段落拼到一起
3. CUV phrase fuzzy match 偶尔把 v.X 段误判成 v.Y，relocate 再移回时打乱原
   邻接关系

所以 publish 端不可能"一次性出对"，sort/relocate 三件套必须作为发布后的**确定性
后处理**（不是 best-effort）。已纳入 §2.1 强制工序。

**Gate-Surgical-Done**（自动化检查）：surgical 系列 commit message 含
`bare-digit` / `章号修正` / `CUV phrase` / `bold-N-phrase` 等关键词时，commit
前必须先跑过 relocate 三件套。手工 commit 用以下脚本兜底：

```bash
# .git/hooks/pre-commit or 手工 audit
if git diff --cached --name-only | grep -q '^calvin/<book>/[0-9]*\.md$'; then
  python3 scripts/relocate_misplaced_verse_commentary.py --book-cn <书名> --dir calvin/<book> --dry-run
  # 输出 "relocated 0 paragraphs" 才算 clean，否则强制中断 commit
fi
```

### 3. ⚠️ 内容丢失风险：Bible-dump 启发式不要太激进

`_strip_bible_text_dumps` form 3 的设计意图是删掉 OCR 抓到的 Bible 文本
碎片（scripture-box 已经渲染干净 CUV，重复的是噪音）。但 verse-opener
commentary 段也以 `21 因为，他们虽然知道上帝...` 形式开头，前几个字
看起来像 Bible 经文，整段会被误删。

**症状**：发布后某节注释 opener 段消失，只剩跨页尾段孤立成一句话碎片
（如 `出于偶然，亦非由其本身生成。但我们务必记得...`）。

**检测**：跨页孤立短段是丢失的 telltale。Audit 加 orphan-fragment gate：

```python
# Gate-7: orphan-fragment（短独立段，无 `**` 加粗，前后均无 verse opener）
# 长度 < 80 字符且不是 footnote 定义、scripture-box、html — 90% 概率是
# 上一段开头被误删后剩下的尾巴。
```

**反例**：`_looks_like_bible_fragment` 老版只识别 `N. CJK` / `N CJK` /
`N、CJK`，但 OCR 偶尔产出 `3 "主啊，他们..."`（数字+空格+**中文引号**+经文）。
引号字符不在 CJK Unicode 块 (一-鿿)，所以被判定为非 Bible 碎片漏删，
渲染时夹在 scripture-box 后面成为孤儿重复经文段（romans/11 中招）。
2026-06-12 加入 `^\d+\s+["“”""][一-鿿]` 引号开头形式。

**反例 2 (verse-opener commentary 跨页误删)**：OCR 跨页时经常把
"N <verse-phrase>…… <commentary-start>" 这种 PDF verse-marker
+ 经文短语 + 注释开头的混合行整段抓在一起，例如 romans/12 p260：

```
[OCR raw page 25/26 边界]
9 上帝可以见证我…… 保罗凭他爱心的结果...他更不能特别
<!-- PAGE 26 -->
地由于自己的劳苦来促进他们的救恩...
```

跨页**前段** (`9 上帝...他更不能特别`) 长度 < 80 + N+空格+CJK 形式
→ sub-rule 3a 命中 → **整段删除**。
跨页**后段** (`地由于...`) → 保留 → 段首单字 "地" 成孤儿。

**关键信号**：中文省略号 `……` 是 verse-phrase 与 commentary 的分
隔符。带 `……` 的 < 80 字符段不要 drop。2026-06-15 加入此规则。

**修复 (前向)**：form 3 length 阈值 < 200 → < 80，> 80 字符要靠
`_is_bible_verse_text` 做 CUV 相似度 ≥ 0.7 才删；< 80 字符且含
`……` 也不删。新书 publish 不会再产生该 bug。

---

#### 已发布 .md 历史损坏 — 安全恢复方案 v2

如果 publish 已经把 verse-opener 删掉、孤儿 continuation 留在
published 里（romans 实测 71+ 处），不能用粗暴 fingerprint 匹配
（会误插进 scripture-box `<p>` 里，2026-06-15 实测 378 处误插）。
要用以下严格算法：

**Step 1 — 候选孤儿段识别**（在 published）。段同时满足：
- (a) 段首是 CJK 汉字（非 `#`/`<`/`*`/数字/空格）
- (b) 段内不含 `<div class="scripture-box"` `<p class="scripture-ref"`
  `<table` `<thead` `<tbody` `<h2`
- (c) 段首 1 个 CJK 字符的"语义孤立度"：第 1 字符 + 第 2 字符**不
  在常见词头白名单**（你/我们/他/上帝/保罗/基督/虽然/然而/因为/
  所以/那/这/第/其/若/当/从/为/按/与/在/就/要/如/虽/所/本/又…）
- (d) 段前一段末尾字符不是结句符（`.。！？；;:`），暗示是跨页延续

**Step 2 — OCR raw 跨页前段定位**：扫 `<!-- PAGE N -->`，对每个
PAGE 注释取注释后第 1 段前 12 字符与 published 候选段前 12 字符
**完全一致** → 锁定，取注释前最后一段为跨页前段。

**Step 3 — 跨页前段必须是 verse-opener**：
- 段首 `^\d{1,2}\s+[一-鿿]`（数字+空格+CJK）
- 段末非结句符（开放式被切）
- 段长 30–500 字符
- 含 `……`/`…` 或 commentary 关键词（保罗/我们/在此/这里/本节）

**Step 4 — 双向唯一性**（关键防线）：
- OCR raw 跨页后段前 12 字符在所有 calvin/<book>/*.md 中**只出现 1 次**
  （否则放弃，避免误匹配 scripture-box 内经文）
- published 候选段位置往前 200 字符内**不含** `</div>`（防 scripture-box
  出口附近误判）

**Step 5 — 构造新段**：
```
**<书名> <章>:<节>。** ***<verse-phrase>*** <commentary><orphan段原内容>
```
- 章号从 published 文件路径推断
- 节号 = OCR raw 跨页前段的数字
- verse phrase = 数字后到第一个 `……`/`…` 之间
- commentary = `……` 后内容
- 跨页前段末尾的截断词（如"他更不能特别"）与孤儿首字符（"地"）**直接
  连成完整词**（"特别地"）

**Step 6 — Dry-run 报告**强制：默认 dry-run；加 `--apply` 才改文件。
每处打印 (文件:行号, OCR 来源段前 60 字, published 孤儿段前 60 字,
拟生成新段)，用户审核后再执行。

**Step 7 — 三层保险**：
1. `git stash` 当前未提交改动
2. `--apply` 后立刻 `bundle exec jekyll build`，build error → 自动
   `git checkout` 回退
3. 单文件 diff > 50 处插入 → 自动 abort（防止规模化误判）
4. 抽样 5 处随机渲染验证 + 已修复段（如 12:1）保持不变

**不在范围内（明确放弃）**：
- 整章误归位（romans 16 等需另议）
- A 类全丢（OCR raw 都没有，无法恢复）
- 非 verse-opener 跨页（纯 intro 段跨页）

### 4. OCR-fused running headers（页眉与正文拼成一行）

OCR 偶尔不在页眉和正文之间断行，得到：

- `第一章加尔文文集`（两个页眉拼一起，无内容）
- `第一章骄傲地高抬自己，他们就丧失了...`（页眉拼到正文）
- `加尔文文集12 保罗既对此...`（页眉拼到 verse 开头）

逐行匹配 `RUNNING_HDR_PATTERNS` 在这里失效（不完全匹配整行）。
`restructure_scan_book.py` 现有 `_strip_fused_running_headers` 在
load_chapter_paragraphs 入口前做前缀剥离，匹配链：
`第N章` / `加尔文文集` / `加尔文集`(OCR 笔误) / `{book_cn}注释` / `{book_cn}`。

新书做 OCR 发布时，如发现 audit gate 报 leak 但裸形式 strip 已覆盖，
检查是否是这种 fused 形式。

⚠️ **正则陷阱：alternation + lookahead 触发回溯**

`_strip_fused_running_headers` 早期版本写成：

```python
chain_re = re.compile(rf"^((?:{'|'.join(header_alts)})+)(?=\S)")
```

`(?=\S)` 要求 header chain 之后有非空字符。对 `罗马书注释` 一行：
1. 先匹配 `罗马书注释`（全部），但 `(?=\S)` 要求后续有 `\S` — 行尾失败
2. 回溯到 `罗马书`（更短的 alternative），后续 `注释` 是 `\S` → 成功
3. 剥掉 `罗马书`，留 `注释` 当孤立段

症状：发布后正文出现孤立 `注释` 标题样的短段（这恰好被 kramdown
渲染成 `<h2>注释</h2>`，看起来像章节标题，截图触目）。

**正确写法**：
1. 去掉 lookahead — chain 全匹配整段，无残骸
2. Alternative **按长度降序排**（python re 是 first-match，长前缀必须排在前）

```python
header_alts = [
    rf"{re.escape(book_cn)}注释",  # 罗马书注释 (5) — 长在前
    r"加尔文文集",                  # 5
    r"加尔文集",                    # 4 — OCR 笔误
    r"第[一二三四五六七八九十百〇零0-9]+章",
    re.escape(book_cn),             # 罗马书 (3) — 短在后
]
chain_re = re.compile(rf"^((?:{'|'.join(header_alts)})+)")
# 然后：rest = line[m.end():]; rest 空则 drop，否则保留 rest
```

新书加 OCR-pipeline 时，header 列表一律按长度降序，**永远不要**
用 `(?=\S)` 之类的 lookahead — 强制 first-match 即可。

### ⚠️ Chapter boundary regex —— `第N章` 后跟脚注圈号会被卡住

`detect_chapter_first_pages` 默认 regex 要求 `第N章` 行末是空白。
但 OCR 经常把脚注圈号粘上来，例如罗马书 page 18 头行就是 `第一章①`。
regex 卡住后，chapter_first[1] 被误设为下一处 bare `第一章` 行的 page
（往往是后续页的 sidebar 或重复出现），page 18-19 的 v.1 commentary
被划进 preface.md，正文丢失一大块。

**症状**：preface.md 尾段莫名其妙含 v.N commentary；section 1:1-7
缺少 v.1 commentary 主体（只剩跨页尾段孤立成短句）。

**修复**：regex 末尾允许跟 ①-⑳：

```python
CN_RE = re.compile(
    r"^#?\s*第([一二三四五六七八九十]+)章[\*①-⑳\s]*$", re.MULTILINE
)
```

发布后用 grep 校验：

```bash
# preface.md 不应包含 verse-opener bold prefix
grep -E '^\*\*[^\*]+ 1:1。\*\*' calvin/<book>/preface.md && echo "❌ v.1 commentary in preface"
```

### ⚠️ Promote 严格模式：只对带数字前缀的段加 `**book N:V。**`

`maybe_promote_verse_opener` 默认 4 个 form，最后一个（form 3）是 CUV
**文本相似度模糊匹配** —— 段落即便没有 leading 数字，只要内容跟 CUV
某节经文起首相似，也会被 promote 成 `**书卷 N:V。** *引文…* 余下注释`。

这在某些书是希望的（OCR 漏数字时用 CUV 补救），但**用户反馈对罗马书
不要这样**：

> 只有前面带数字的，改成书卷名加章节号，不带的不要加

具体例：
- `1 保罗…… 关于保罗这个名字...` → `**罗马书 1:1。** 保罗…… ...`（√，有数字）
- `耶稣基督的仆人，奉召为使徒…… 保罗这样指出他的身份...` → 保持原样
  （×，无数字前缀，**不要按 CUV 相似度模糊 promote**）

实现：模块 flag `restructure_john_scan_ch1.STRICT_DIGIT_ONLY`：

- 默认 False（约翰福音 / 歌罗西书 等书保持原行为）
- 罗马书 wrapper (`restructure_romans_scan.py`) 设 True：

```python
import restructure_john_scan_ch1 as ch1
ch1.STRICT_DIGIT_ONLY = True
```

新书做 OCR 发布时，**先跑一遍看 promote 出来对不对**：
- 如果某段无数字但被 promote 了，且引文跟 CUV 相似 → 这是模糊匹配
  - 如果你希望这样：保留 STRICT_DIGIT_ONLY=False
  - 如果用户希望"只对带数字的 promote"：在 wrapper 里设 True

同时加了 form 2.5 (`^N <CJK>...` 空格分隔的 OCR opener)，所有 OCR 书
受益，不需要 STRICT 开关。

### 5. ⚠️ Section 顺序错乱 —— detect_paragraph_verse 漏识 OCR 格式

OCR 输出的 verse opener 段格式有多种：

| 格式                              | 来源       | 例 |
|----------------------------------|-----------|---|
| `**罗马书 1:22。** ...`          | promote 后  | `**罗马书 1:22。** *自称为聪明* ...` |
| `22 **自称为聪明** ...`          | OCR raw    | bold lemma + 注释 |
| `15 所以情愿尽我的力量…… ...`     | OCR raw    | 空格 + CJK 直接 |
| `**自称为聪明** ...`             | OCR raw    | 仅 bold 无 digit |

**老 bug**：`detect_paragraph_verse` 只走 `verse_prefix_re`（要求
`**{书卷} N:V。**`）和 `_verse_for_opener` 模糊匹配。
对 `22 **自称为聪明**...` 这种**数字 + 空格 + bold + CJK**，
verse_prefix_re 不匹配，模糊匹配也碰不上（首字符是 `2`），返回 None。
结果该段落停留在 cur_sec（上一节的 section）。罗马书 1.md 出过：
- v.22 commentary 留在 section 1:15-21
- v.15/v.16 commentary 漂到 section 1:15-21 末尾
- v.24 注释（含 "意义是深远的"）随 cur_sec 错放

**修复**：detect_paragraph_verse 加 `^(\d{1,3})[ 、.]\s*\*{0,2}[一-鿿]`
匹配，先识 verse number，再范围校验：

```python
m = re.match(r"^(\d{1,3})[ 、.]\s*\*{0,2}[一-鿿]", para)
if m:
    v = int(m.group(1))
    if 1 <= v <= len(chapter_verses):
        return v
```

同步：`relocate_misplaced_verse_commentary.py` /
`relocate_cross_chapter_verse.py` / `_audit_gate` 的
`opener_re` 都用同一 pattern，**保持一致**才不会一边检测一边漏。

**根本错误判断**：之前看到 OCR 末尾多 "这件事意义是深远的。" 时误判为
Qwen-VL 幻觉，差点把 PDF 真文本删掉。按 [feedback_pdf_verify_before_change]
必须先读 PDF，但同时也要看清是**顺序问题**还是**内容问题**——
段落出现在错的 section 时，看起来就像"和原文不一样"。section 顺序
错乱是 publish 启发式的常见 bug，第一直觉应该是它，不是 OCR 幻觉。

### 7. ⚠️ OCR 幻觉风险（Qwen-VL 偶尔凭空添字）

Qwen-VL 7B 在以下场景偶尔会**添加 PDF 中不存在的文本**：

- 段落末尾添加"总结性"短句让段落"显得完整"
  - 实战例：罗马书 ch1 v.24 注释原文以"...羞辱的痕迹，是深而不可消除的。"结束，
    OCR 凭空多加 "这件事意义是深远的。" — 用户截图发现
- 列表末尾添加"等等" / "等等"
- 页脚断行处补完上一句

**自动检测困难**：脚本无法区分合理短句和幻觉短句。靠：
- 用户截图反馈后人工查 PDF（必须按 [feedback_pdf_verify_before_change]
  先读 PDF 再改，禁止猜测）
- 自查可疑模式：

```bash
# 找段落末尾 < 15 字符的孤立短句（页边幻觉的高发位置）
python3 - <<'PY'
import re, pathlib
for p in pathlib.Path('calvin/<book>').glob('*.md'):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    for para in re.split(r'\n\n+', text):
        if para.startswith(('<', '#', '**', '[^', '{:')): continue
        # Look for paragraph ending with a short trailing sentence
        sentences = re.split(r'(?<=[。！？])\s*', para.strip())
        if len(sentences) >= 2 and 4 <= len(sentences[-1].rstrip('。')) <= 12:
            tail = sentences[-1]
            print(f'  {p.name}: ...{sentences[-2][-20:]}「{tail}」')
PY
# 输出"前段尾巴 + 「可疑短句」"，对照 PDF 该位置确认。
```

**修复**：发现后直接 Edit 已发布的 md（不要碰 OCR raw — 按
[feedback_translation_raw_preserve] 保护）。重发会丢修正，所以发现一个
就 commit 一个，不批量延迟。

### 8.5 ⚠️ 跨页未完段接续合并（per-page assemble 的根因 bug）

`ocr_assemble.py` 按 per-page md 拼接时，page 之间插入空行 → markdown 上两段。但原 PDF 中 page 边界处常常是**同一段被切**：

```
[page N 末尾]  ...能够作圣徒或爱上帝的人的后裔        ← 段尾没有任何标点（未完）
[page N+1 头]  也是很重要的，因为上帝曾应许敬虔的列祖们…  ← 小词延续
```

publish 不识别这种"未完段+延续"模式，按两段输出，导致：
- verse 9:5 sub-heading 跟主段被强行拆开（用户截图反馈过两次）
- verse 9:18 主体段大半丢失（"对于蒙选的以"截断 + 后续 1000+ 字符 page 整页内容被归到其他 verse 区块）
- "色列人，" "为人为人。" "主了。" 等孤字段（OCR 把 page 末"以"+ page 首"色列人，" 切成两段）

**根因**：`restructure_scan_book.py` 的段落处理逻辑没有 `_merge_cross_page_continuations()`。

**修复启发式**（应加入通用脚本）：

```python
def _merge_cross_page_continuations(paras):
    """合并跨页未完段。上段末非结句符 + 下段非段首符号 → 合并"""
    SENTENCE_END = set('。！？；…："」』）)、')
    out = []
    for p in paras:
        s = p.strip()
        if not s:
            out.append(p); continue
        # 上段末未完 + 当前段是延续段
        if out:
            prev = out[-1].rstrip()
            if (prev and prev[-1] not in SENTENCE_END
                and not s.startswith(('**', '#', '<', '|', '[', '!', '{'))
                and not re.match(r'^\d', s)):
                out[-1] = out[-1].rstrip() + s  # 合并
                continue
        out.append(p)
    return out
```

加入后**所有 OCR 扫描书**受益。新书做 OCR publish 不会再产生孤字段。

### 8.6 ⚠️ 内容完整性 audit（防 verse 整段丢失）

`relocate_*` gates 只检查 verse 段是否**错位**，不检查是否**丢失**。但 publish 可能把 OCR raw 中某个 verse 的整段注释（如 page_0206 整页）放到错的 verse 区块或直接丢弃。这种丢失从格式上看不出来。

**audit 加 Gate-8: verse 字符数对比**：

```bash
# 对每个 verse N，比对 OCR raw 中该 verse 字符数 vs published 字符数
# 丢失率 > 50% → 警告（很可能 publish 漏抓了某 page）
python3 scripts/audit_verse_completeness.py --book romans
```

实战 (2026-06-17 romans)：用户截图 verse 9:18 注释只剩 "对于蒙选的以" 7 个字，page_0206 整页 1000+ 字符完全丢失。从 OCR raw `page_0205-0206` 手工补回。

**新书 publish 必跑此 gate**——0 命中再 commit。

### 8.7 ⚠️ 已发布书的 idempotent 修复脚本

如果手工 fix 了已发布的 .md（删孤字段、合并跨页、补回丢失段），**立即** commit 并固化成 idempotent post-process 脚本 `scripts/fix_<book>_ocr_artifacts.py`：

- 输入：扫 `calvin/<book>/*.md`
- 修复：明确的 pattern 替换（孤字段删除、噪声删除、合并跨页等）
- idempotent：重跑同结果，不会重复施加
- 跑前检查：跳过锁定章节 (`LOCKED_CHAPTERS`)

理由：手工 fix 不固化 → 一次 `git checkout` 全部丢失（2026-06-17 romans 实测：一上午所有修复因 git checkout HEAD 回滚全部抹掉，用户怒批）。**修了就 commit + 写脚本**，永远不要靠记忆和手工记录。

### 8.8 ⚠️ Sub-heading 段归位（无数字前缀的 verse 注释段）

`relocate_misplaced_verse_commentary.py` 用 `^N\s+CJK` 数字前缀识别 verse 归属。
但 verse 注释段中除了主体段（带 `N <经文 phrase> …` 数字前缀），还有 **sub-heading 段**：

```
**罗马书 9:30。** 这样我们可说什么呢…              ← 主体段（带数字 30）
那本来不追求义的外邦人…… 这里一方面外邦人本是…   ← sub-heading 段，无数字前缀
在本节的前半句，保罗的目的乃是…                  ← sub-heading 段，无数字前缀
保罗在此明明讲到公义，因为除了义…                ← sub-heading 段，无数字前缀
```

publish 脚本对这些**无数字前缀**段的 verse 归属判断是 "属于 cur_sec"（继承上一段的 verse）。
跨页错位 + cur_sec 状态错乱时，整组 sub-heading 段会被全部归到错的 verse（实战 2026-06-17 罗马书 9:30 注释 3 段被归到 9:29 后）。

**修复 (前向)**：`detect_paragraph_verse` 加 CUV phrase 相似度匹配——对无数字前缀段，
用该章每节经文 phrase 跟段首前 30 字做 fuzzy 匹配（threshold 0.7）。例如 "那本来不追求义的外邦人……" 高匹配 verse 9:30 经文 "那本来不追求义的外邦人反得了义" → 该段归 9:30 区块。

**audit (已有 .md 检查)**：见下 Gate-9，扫描"主体段 + sub-heading 段不在同一 verse 区块"。

### 8.9 ⚠️ 整段双重出现 (verse 区块内 + anchor 之前同时出现)

publish 时 sub-heading 段错位 + 主体段双重生成的复合 bug：

```
[verse 9:29 anchor]
[verse 9:29 注释]
那本来不追求义的外邦人……      ← verse 9:30 sub-heading 错位
在本节的前半句…              ← verse 9:30 sub-heading 错位
保罗在此明明讲到公义…          ← verse 9:30 sub-heading 错位
[scripture-box 9:30-33]
[verse 9:31 anchor]            ← anchor 倒序!
[verse 9:30 anchor]
**罗马书 9:30。** 这样我们可说…  ← 主体段 (正确位置)
在本节的前半句…                ← 重复 (跟前面 sub-heading 重复)
```

实战 2026-06-17 罗马书 9.md：用户截图 verse 9:9 后看到孤立"上帝，保罗现在就以人所能了解的说法…"段——是 verse 9:30 主体段被截断 + 错位到 verse 9:29 之后；正确位置 (L322) 又有完整主体段。

**症状识别**：grep "^\*\*罗马书 N:V。\*\*" 同一 (N,V) 出现 2+ 次 → 双重出现。

**修复**：删错位副本（在 anchor 之前的版本），保留正确位置（anchor 之后）。

### 8.A ⚠️ verse-anchor 顺序倒置（同章 anchor 必须递增）

publish 偶尔产生：

```
<h2 class="verse-anchor" id="romans-9-31">罗马书 9:31</h2>
<h2 class="verse-anchor" id="romans-9-30">罗马书 9:30</h2>
**罗马书 9:30。** ...
```

anchor 9:31 出现在 anchor 9:30 之前——前端导航跳转到错误位置。

**audit (Gate-10)**：

```python
# 同章 anchor 顺序必须严格递增
for ch in chapters:
    seq = re.findall(rf'class="verse-anchor"\s+id="romans-{ch}-(\d+)"', text)
    seq = [int(v) for v in seq]
    for i in range(len(seq)-1):
        assert seq[i] < seq[i+1], f'ch{ch}: anchor {seq[i]} > {seq[i+1]}'
```

应 0 失败再 commit.

### 8. Bible verse-count 表

```python
VERSE_COUNTS = {
    '罗马书': {
        1: 32, 2: 29, 3: 31, 4: 25, 5: 21, 6: 23, 7: 25, 8: 39,
        9: 33, 10: 21, 11: 36, 12: 21, 13: 14, 14: 23, 15: 33, 16: 27,
    },
    # 加新书时填这里
}
```

校验作用：
- `^22\s+[CJK]` 在 Rom 12 中是 false-positive（Rom 12 只到 21）
- 该段实际属于 Rom 11:22（v.22 在 Rom 11 范围内）→ 跨章 relocate

---

## front matter

```yaml
---
layout: calvin-en
book_id: john
book_name: "约翰福音"
chapter: 1
header-img: psalm-bg-mountain.jpg
date: 2026-06-04 10:11   # ← 必须是真实当前时间，不能硬编码
prev_section: preface     # 或 N-1
prev_label: "序言"        # 或 "第N章"
next_section: 2
next_label: "第二章"
---
```

⚠️ **date 字段必须用真实时间**（参 CLAUDE.md「date 字段必须使用真实时间」）。
脚本里用 `datetime.datetime.now().strftime("%Y-%m-%d %H:%M")`，
**不要写成固定字符串如 `2026-06-03 18:30`**。批量生成时各文件错开 1 分钟
更自然。曾经把 21 章 + preface 全部硬编码为 `18:30` 被用户截图问。

---

## 替换现有 ZH 翻译（OCR 版上线）

ocr-pipeline 默认输出 `calvin/<book>-scan/`（不覆盖现有 `calvin/<book>/`，
按 [feedback_translation_raw_preserve] 保护原翻译）。

要用 OCR 版 **替换**现有 ZH 版（如 john / colossians）：

```bash
BAK="/tmp/calvin_<book>_backup_$(date +%Y%m%d_%H%M%S)"
cp -r calvin/<book> "$BAK"       # 1. 备份老译本到 /tmp
rm -rf calvin/<book>
mv calvin/<book>-scan calvin/<book>
# 2. 把内容里 book_id: <book>-scan → <book>, 书名「（扫描版）」标签去掉
cd calvin/<book>
for f in *.md *.html; do
  sed -i '' 's/book_id: <book>-scan/book_id: <book>/g;
             s/<书名>（扫描版）/<书名>/g' "$f"
done
cd ../..
# 3. _data/calvin_books.yml 删 <book>-scan 条目, 保留 <book> 条目
#    更新 chapters: 数
# 4. 清 _site/calvin/<book>-scan/ stale dir
rm -rf _site/calvin/<book>-scan
```

⚠️ **替换时也要用腓立比书板式（layout: calvin-en）**，不要用 calvin-book-modern
之类的实验板式（曾用 romans 走过这坑，截图后用户要求改）。

---

## 注册 yaml

在 `_data/calvin_books.yml` 加 entry 或更新现有 entry 的 `chapters:` 数。

```yaml
new_testament:
  - id: john
    name: 约翰福音
    chapters: 21
```

---

## ✅ Mandatory audit gate（commit 之前必须 0 命中）

下面 audit 全部 0 命中之前**不能** commit + push。如果用户截图发现
任何一项有漏，说明这道门没把住。

### 用户底线（被打回 5+ 次，每次都说"为什么还有")

> "这是第三章了，为什么还显示 1:1"
> "26、27 是什么意思"（裸数字开头的段落）
> "怎么还有这个问题，为什么不彻底解决，我没那么多时间排查"
> "这一节怎么放在这里了"（4:14 出现在 4:9 之前）
> "为什么出现两个 4:9"（OCR 把 PDF 经文块当 commentary 错放）

verse-marker 段头格式有 **5 类**常见 bug，必须在发布前**一次性**扫干净——不要分批 fix，
用户每被打回一次就投入信任度急剧下降：

| Bug 模式 | 例 | 根因 |
|---|---|---|
| 章号硬编码为 1 | `**约翰福音 1:26。**` 出现在 ch3 | `restructure_<book>_scan_ch1.py:137` 把 `f"**{书} 1:{v}。**"` 写死，chapter.py 直接复用导致所有章都是 `1:` |
| 裸数字 + 空格 + 中文 | `26 你所见证的那位...` | OCR 提取出节号 `26` 但 verse-detection 失败时降级为 plain text，未包 markdown |
| 圈号被切碎 | `③0 耶稣...` → 落入 published 变 `0 耶稣...` | OCR 把 `㉚`（圈 30）切成 `③` + `0`，正则只匹 `\d+` 漏 ㉑-㉛ 全角圈数字 |
| scripture-text 误标 commentary | ch4 v.22-v.38 整页经文被当成 17 个 `**N:V。** *phrase。*` commentary 段 | OCR 抓 PDF 经文 block 时识别每节圈号，publish 沿用 verse-num 路由把整段经文当 commentary。检测：connected 段去 marker+italic+punct 后剩 < 25 字 |
| 截断 commentary | ch15 v.22 `他已经说过犹太人恨恶福音是因`（断在"因"字后）| OCR 跨页时 publish 没把下一页续段拼回，commentary 头有但 body 截断 |
| 同节多段都加 verse-ref | 一节有 phrase A + phrase B 两段评注时全部加 `**约翰福音 4:22。**`，导致页面显示两个 4:22 | PDF 原版圈号 ㉒ 只在第一段，第二段是 bold phrase 没有节号。publish-time 给每个 italic-phrase 开头都加 ref 太激进。修：跑 `scripts/dedupe_same_verse_markers.py` 把连续相同 verse-num 的第 2、3... 段 verse-ref 剥掉 |
| bold-wrapped `**N 短语。**` 当 verse-marker | `**1 上帝是个灵。**` 出现在 ch4（实际应是 v.24）/`**25 我已经告诉你们。**`（ch10 v.25）| OCR 把圈号 ㉔ 错读为 `②1`（splits double-digit circled num into ② + 1），publish 把 `## ②1` 输出成 `**1 ...**`。修：扫 `^\*\*(\d) ([一-鿿]+。)\*\*` 模式，用 CUV (和合本) phrase 匹配找回真实 verse-num，重写为 `**约翰福音 ch:V。** *短语。*` 形式 |
| phrase-only stub 残留 | `**约翰福音 5:10。** *褥子是不可的。*` 后面空一行，下一段是无 marker 的 Calvin 注释 | dump-strip 算法只截掉 dump body 留下 italic phrase，没把后续真实 Calvin 注释段的 marker 拼回来。修：phrase-only stub 检测后，要么 merge with next bare-italic 段，要么直接删除 stub（若没有真注释紧跟）|
| `**N**中文` 无空格紧贴变体 | `**26**因为父怎样在自己有生命。` (ch5)、`**44**你们是出于你们的父魔鬼。` (ch8) | OCR 处理圈号节号时偶尔丢空格，pattern `^\*\*\d+\*\* `（要求空格）会漏检。Gate-8 必须同时检 `^\*\*\d+\*\*[一-鿿]` 无空格紧贴中文的变体 |
| 整段重复（同章内 N+ 段重复出现）| ch7 v.17-v.19 commentary 6 段在同章内被复制两次 | publish/relocate 阶段 chunk 跨页拼接时整块二次塞入。检测：para 前 80 字 hash 重复出现 ≥2 次 → 删除第二次出现的整块（保留第一次）|

```bash
# Gate-1: BARE-DIGIT 段落开头但不在 section range
python3 scripts/relocate_misplaced_verse_commentary.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0

# Gate-2: 跨章 BARE-DIGIT overflow
python3 scripts/relocate_cross_chapter_verse.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0

# Gate-2b: 同 section 内 verse 顺序乱
python3 scripts/sort_intra_section_verses.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0（已 sort 完不会再动）

# Gate-2c: 同节连续多段都加 verse-ref（重复出现 4:22, 4:22 这种）
python3 scripts/dedupe_same_verse_markers.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0（已剥完）

# Gate-2d: phrase-only stub — verse-marker 后只有 italic phrase 没有 commentary body
# 触发例: `**约翰福音 5:10。** *褥子是不可的。*` 然后空行 — 是 dump-strip 残留
python3 -c "
import re
from pathlib import Path
for f in sorted(Path('calvin/<book>').glob('*.md')):
    if not f.stem.isdigit(): continue
    ch = int(f.stem)
    text = f.read_text(encoding='utf-8')
    for m in re.finditer(rf'\\*\\*<书名> {ch}:(\\d+)。\\*\\*\\s*\\*[^*]+\\*\\s*\\n\\n', text):
        print(f'{f.name} v.{m.group(1)}: phrase-only stub (delete or merge with next)')
"   # 应空 — 出现 = dump 删除时没拼回真实 commentary，需要：
    # (a) 若下一段有 bare-italic Calvin 注释 → merge 进同一行
    # (b) 否则直接删除 stub

# Gate-3: Running-header leak
for f in calvin/<book>/*.md; do
  grep -nE '^(加尔文文集|<书名>注释|<书名>·第[0-9一二三四五六七八九十百]+章)$' "$f"
done   # 应空

# Gate-4: CIRCLED-DIGIT prefix
grep -rE '^[①-⑳]' calvin/<book>/*.md   # 应空

# Gate-5: Orphan footnote refs
python3 - <<'PY'
import re, pathlib
for p in pathlib.Path('calvin/<book>').glob('*.md'):
    t = p.read_text(encoding='utf-8')
    body, _, fns = t.partition('\n## 脚注\n') if '## 脚注' in t else (t, '', '')
    refs = set(re.findall(r'\[\^(\d+)\]', body))
    defs = set(re.findall(r'^\[\^(\d+)\]:', fns, re.M))
    orphan = refs - defs
    if orphan: print(f'{p.name}: orphan {orphan}')
PY
# 应无输出

# Gate-6: Bible-text dump（OCR 抓整章 Bible 全段）
grep -lE '^[①②③④⑤⑥⑦⑧⑨⑩]{5,}' calvin/<book>/*.md   # 应空

# Gate-6b: scripture-text dump 误标为 commentary（连续多段 `**N:V。** *经文。*` 但无注释）
# 触发例：ch4 v.22-v.38 整页经文被 publish 当成 verse-marker commentary
python3 -c "
import re
from pathlib import Path
NOISE = re.compile(r'[\\s\"“”‘’。，！？；：（）\\[\\]<>]')
for f in sorted(Path('calvin/<book>').glob('*.md')):
    if not f.stem.isdigit(): continue
    ch = int(f.stem)
    text = f.read_text(encoding='utf-8')
    paras = re.split(r'\\n\\n+', text)
    suspects = []
    for idx, para in enumerate(paras):
        m = re.match(rf'^\\*\\*<书名> {ch}:(\\d+)。\\*\\*', para.split('\\n')[0])
        if not m: continue
        no_marker = re.sub(rf'^\\*\\*<书名> {ch}:\\d+。\\*\\*\\s*', '', para, count=1, flags=re.DOTALL)
        no_italic = re.sub(r'^\\*[^*]+\\*\\s*', '', no_marker, count=1)
        s = NOISE.sub('', no_italic)
        if len(s) < 25:
            suspects.append((idx, int(m.group(1)), para.split('\\n')[0][:80]))
    # Report clusters ≥3 consecutive (indices within distance 2)
    cur = []
    clusters = []
    for s in suspects:
        if cur and s[0] - cur[-1][0] <= 2: cur.append(s)
        else:
            if len(cur) >= 3: clusters.append(cur)
            cur = [s]
    if len(cur) >= 3: clusters.append(cur)
    for c in clusters:
        print(f'{f.name} cluster v.{c[0][1]}-v.{c[-1][1]} ({len(c)} dumps)')
"   # 应空 — 出现 = OCR 把 PDF scripture-block 错放成 commentary, 删掉这些段

# Gate-7: 章号硬编码 bug（**书名 1:N。** 出现在非 ch1 章）
for ch in $(seq 2 21); do
  bad=$(grep -c "\\*\\*<书名> 1:[0-9]\+。\\*\\*" calvin/<book>/$ch.md 2>/dev/null)
  [ "$bad" -gt 0 ] && echo "ch$ch: $bad wrong chapter refs"
done   # 应空 — 出现 = restructure_<book>_scan_ch1.py:137 把 ch 硬编码为 1

# Gate-8c: bold-wrapped "N text。" 当 verse-marker（OCR 错读圈号 ㉔→②1）
# 触发：`**1 上帝是个灵。** ...` (N + 空格 + 中文短语，整段在 bold 内)
# 来源：OCR 把圈号双位数 (㉔ ㉕ ㉖) 错读为 ②X，publish 沿用 X 当数字。
# 必须用 CUV (和合本) phrase 匹配找出真实 verse 号 (1→24, 5→25...)
python3 -c "
import re, json, opencc
from pathlib import Path
bible = json.load(open('scripts/zh_cuv.json', encoding='utf-8-sig'))
t2s = opencc.OpenCC('t2s')
# Adjust book index for non-John books — 42 for John, 44 for Romans, etc.
john = bible[42]
def best_verse(ch, phrase):
    cuv = {v+1: t2s.convert(john['chapters'][ch-1][v].replace(' ', '')) for v in range(len(john['chapters'][ch-1]))}
    target = re.sub(r'[，。！？；：\"“”]', '', phrase)[:20]
    if not target: return None
    best = (None, 0)
    for v, vt in cuv.items():
        score = sum(1 for c in target if c in vt[:30])
        if score > best[1]: best = (v, score)
    return best[0] if best[1] >= len(target)*0.5 else None
for f in sorted(Path('calvin/<book>').glob('*.md')):
    if not f.stem.isdigit(): continue
    ch = int(f.stem)
    text = f.read_text(encoding='utf-8')
    bad = re.findall(r'^\\*\\*(\\d{1,3}) ([一-鿿][^*]{0,80}?。)\\*\\*', text, re.MULTILINE)
    if bad: print(f'{f.name}: {len(bad)} bold-N-phrase markers (need CUV-match fix)')
"   # 应空 — 出现 = 跑 CUV-based 自动修复脚本（见 04 §11.4）

# Gate-8: 裸数字开头 + 中文（verse-marker emit 失败的降级）
python3 -c "
import re
from pathlib import Path
for f in sorted(Path('calvin/<book>').glob('*.md')):
    if not f.stem.isdigit(): continue
    text = f.read_text(encoding='utf-8')
    pats = {
        '裸数字': r'^\d{1,3} [^\n*<]',           # 28 你们自己...
        '0 开头': r'^0 [^\n*<]',                  # 0 耶稣... (OCR 把 ㉚ 切成 ③+0)
        'bold 带空格': r'^\*\*\d{1,3}\*\* ',     # **26** opener
        'bold 无空格紧贴中文': r'^\*\*\d{1,3}\*\*[一-鿿]',  # **26**因为父... (无空格 — 易被前一项漏检)
    }
    for n, p in pats.items():
        ms = re.findall(p, text, re.MULTILINE)
        if ms: print(f'{f.name} [{n}]: {len(ms)} - {ms[:2]}')
"   # 应空

# Gate-8b: verse 注释段顺序倒乱（同一 chapter 内 verse-marker 序列应单调不减）
python3 -c "
import re
from pathlib import Path
for f in sorted(Path('calvin/<book>').glob('*.md')):
    if not f.stem.isdigit(): continue
    ch = int(f.stem)
    text = f.read_text(encoding='utf-8')
    refs = [int(m.group(2)) for m in re.finditer(r'\\*\\*<书名> (\\d+):(\\d+)。\\*\\*', text) if m.group(1) == str(ch)]
    prev, issues = 0, 0
    for v in refs:
        if v < prev: issues += 1
        prev = max(prev, v)
    if issues: print(f'{f.name}: {issues} backward jumps')
"   # 应空 — 出现 = 跨 section relocate（relocate_misplaced_verse_commentary.py）
    # + 同 section 内排序（sort_intra_section_verses.py）都要跑过

# Gate-9: verse 主体段双重出现 (publish 错位副本)
python3 -c "
import re
from pathlib import Path
for p in sorted(Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    # 同一 verse 的 ** 主体段标记出现 2+ 次 → 错位副本
    from collections import Counter
    verses = re.findall(r'\*\*<书名>\s+(\d+:\d+)。\*\*', text)
    dups = [v for v, n in Counter(verses).items() if n > 1]
    if dups: print(f'{p.name}: 双重 verse 主体段 {dups}')
"
# 应无输出

# Gate-10: verse-anchor 顺序倒置 (同章应严格递增)
python3 -c "
import re
from pathlib import Path
for p in sorted(Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    ch = int(p.stem)
    seq = [int(v) for v in re.findall(rf'class=\"verse-anchor\"\s+id=\"<book>-{ch}-(\d+)\"', text)]
    for i in range(len(seq)-1):
        if seq[i] >= seq[i+1]:
            print(f'{p.name}: anchor {ch}:{seq[i]} >= {ch}:{seq[i+1]}')
"
# 应无输出

# Gate-11: verse 主体段位置早于其 anchor (publish 错位 root cause)
python3 -c "
import re
from pathlib import Path
for p in sorted(Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    ch = int(p.stem)
    for m in re.finditer(rf'\*\*<书名>\s+{ch}:(\d+)。\*\*', text):
        v = m.group(1)
        # 找该 verse 的 anchor 位置
        am = re.search(rf'class=\"verse-anchor\"\s+id=\"<book>-{ch}-{v}\"', text)
        if am and am.start() > m.start():
            print(f'{p.name}: ch{ch}:{v} 主体段在 anchor 之前')
"
# 应无输出

# Gate-12: 嵌入式 verse 主体段（**书 N:V。** 出现在段中而非段首）
# OCR 跨页时把下一 verse 主体段粘合到前段尾部, anchor 完全缺失
# 示例：v.16 末段 "...肯顺服圣灵的引**罗马书 9:17。** 因为经上有话..."
# 检测：main marker 前最近的 \n\n / </h2> / </div> 与 marker 之间有非空白文本
# 注意：Gate-11 抓不到这种 (因为同时缺 anchor → 不会触发"主体段早于 anchor")
python3 -c "
import re
from pathlib import Path
for p in sorted(Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    ch = int(p.stem)
    for m in re.finditer(rf'\*\*<书名>\s+{ch}:(\d+)。\*\*', text):
        ms = m.start()
        if ms == 0: continue
        before = text[:ms]
        para_start = max(before.rfind('\n\n')+2, before.rfind('</h2>'), before.rfind('</div>'))
        between = text[para_start:ms].strip()
        if between and not between.endswith(('>', '。', '\n')):
            print(f'{p.name}: ch{ch}:{m.group(1)} 主体段嵌在段中 @L{text[:ms].count(chr(10))+1}')
"
# 应无输出。命中需手工拆段 + 在 scripture-box 后补 anchor

# Gate-13: 有主体段但缺 verse-anchor（粘合后 anchor 完全丢失）
# 排除单 verse section（## 书 N:V 单独 heading 已有 scripture-anchor）
python3 -c "
import re
from pathlib import Path
for p in sorted(Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    ch = int(p.stem)
    main_v = {int(m.group(1)) for m in re.finditer(rf'\*\*<书名>\s+{ch}:(\d+)。\*\*', text)}
    anchor_v = {int(m.group(1)) for m in re.finditer(rf'class=\"verse-anchor\"\s+id=\"<book>-{ch}-(\d+)\"', text)}
    single = {int(m.group(1)) for m in re.finditer(rf'^## <书名> {ch}:(\d+)\s*$', text, re.MULTILINE)}
    missing = sorted(main_v - anchor_v - single)
    if missing:
        print(f'{p.name}: ch{ch} 缺 anchor → {missing}')
"
# 应无输出
```

**Gate-12 与 Gate-13 关联**：通常同时发生 —— 一次 OCR 跨页粘合既造成
"主体段嵌段中"（Gate-12）也造成"对应 verse 缺 anchor"（Gate-13）。修复时：

1. 找到嵌入位置，在 `**书 N:V。**` 之前加 `\n\n` 拆段
2. **句尾被截断时必须先去 OCR raw 跨页边界找原中文**（见下方"⚠️ 跨页截断修复"）
3. 在拆出来的 verse 主体段之前补 `<h2 class="verse-anchor" id="书-N-V">书名 N:V</h2>`
4. 检查相邻 verse（N±1）的主体段是否也被错位 / 重复（OCR 跨页 bug 常成片出现）

### ⚠️ 跨页截断修复：从 OCR raw 找原中文，**禁止从英文版翻译**

**绝对规则**：当 publish 后的中文段尾被 OCR 截断（如 "并肯顺服圣灵的引" 之类
看起来不完整的结尾），**禁止直接用 calvin/<book>-en/ 英文版翻译补译**。
原中文译文绝大概率就在 OCR raw 的**下一页开头**，被 OCR 漏识别在了
"页码 + 页眉" 行之后。

**原因 / 真实案例**（2026-06-17 罗马书 9:13）：
- publish 后 v.13 末段："...上帝的忿怒临到何处，何处就有死亡。然而何"
- 看起来 "然而何" 是 OCR 噪音 → 我误以为是 → 删掉 + 从英文版补译
  "他的爱在何处，何处就有生命"（英文 "where his love is, there is life"）
- **真实情况**：OCR raw `page_0201.md` 开头是
  ```
  196 处有上帝的慈爱，何处就有生命。
  加尔文文集
  ```
  原中文译文是 **"然而何处有上帝的慈爱，何处就有生命"** —— "然而何" 是这句
  的前 3 字，不是噪音。OCR 把 "处有上帝的慈爱..." 当下一页正文，把 "然而何"
  留在了上页末。我自己翻译的 "他的爱在何处" 是编造，与原译者用词不符。
- 用户发现，要求"按原文找 OCR raw 改"，并明令以后不准自己从英文翻译。

**修复流程**：

```bash
# 1. 定位被截断的 publish 段在 OCR raw 哪一页
grep -ln "<前段尾巴 12-20 字>" calvin_raw/<book>-scan/ocr/page_*.md

# 2. 看下一页开头（页码 + 页眉之后的第一段文字）
head -10 calvin_raw/<book>-scan/ocr/page_<N+1>.md

# 3. 续文几乎肯定在那里。把页末截断 + 下一页开头续文拼回完整句

# 4. 如果跨页边界明确无续文（如 v.6/v.7 缺 191 整页），先 grep
#    OCR raw 全文有没有遗漏到别处：
grep -l "<可能续文关键词>" calvin_raw/<book>-scan/ocr/*.md

# 5. 实在 OCR raw 没有 → 报告用户，让用户决定（截断 / 从英文翻 / 提供原文）
#    不要自己默默从英文版补译。
```

**触发 OCR 漏识别的形式**：跨页 OCR 漏字几乎都发生在物理 page 文件开头，
模式是 `<页码数字>\n\n<页眉>\n\n<正文>`，OCR 把页码识别成正文的一部分
（如 `196 处有上帝的慈爱` —— "196" 是页码，"处有上帝的慈爱..." 才是正文，
但 OCR 黏成一行）。**人眼一看就懂，脚本不易自动判断**，所以需要人工对照。

**唯一允许从英文版翻译的情况**：用户**明确**指出某书内页整页漏失（如
"原文 191 页漏掉了，对应 PDF 物理页数 196/197 之间，需要从英文版翻译补"），
此时 OCR raw 该页确实不存在 → 才可从英文版翻译，且翻译要承认是补译，不能
说成原中文。其他所有情况一律按 OCR raw 找。

### ⚠️ Gate-14：跨页强分段（OCR 跨页 → publish 把同段断成两段）

**Root cause**：`restructure_scan_book.py` 把每个 OCR per-page md 文件独立
读取，page 文件之间内容自然以 `\n\n` 分隔。当 PDF 一段跨两页（OCR 把同段
切到两个 page 文件）时，publish 把它当成两个段落，破坏了原段落结构。

**实战案例**（2026-06-17 罗马书 10:5）：
- PDF 物理页 221 末："...愚昧的罗马天主教徒想以空洞的许愿来证明功德的效果，
  是极其可憎的。"（同段未完）
- PDF 物理页 222 头："他们说：'上帝并没有徒然地将生命应许给敬拜他的人。'..."
  （承上"罗马天主教徒"继续论述）
- publish 后 10.md 两段被 `\n\n` 隔开，破坏阅读节奏
- 用户截图："原文这里没有分段，你怎么在这里分段了"

**检测规则**（detect-only，不自动合并以免误合）：
- 两个相邻段（中间 `\n\n`），都不以 `<` / `#` / `**` / `[^` / `*` / `|` 开头
- 前段最后非空字符**不在结句符号集** `。 ！ ？ ； " " 」 ） 】 > \n`
- 下段开头是**连接词**（"但 / 然而 / 因此 / 所以 / 又 / 再者 / 此外 / 故 /
  他们说 / 又如 / 即使 / 何况 / 至于 / 不过 / 可是 / 况且 / 于是" 等）

```python
python3 -c "
import re, pathlib
CONNECTORS = ('他们说', '但', '然而', '因此', '所以', '又', '再者', '故',
              '于是', '此外', '可是', '不过', '至于', '虽然', '从而', '由此',
              '另外', '其次', '况且', '尚且', '即使', '何况')
ENDERS = ('。', '！', '？', '；', '\"', '\"', '」', '）', '】', '>', '\n')
for p in sorted(pathlib.Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    paras = text.split('\n\n')
    for i in range(len(paras)-1):
        prev, nxt = paras[i].strip(), paras[i+1].strip()
        if not prev or not nxt: continue
        if prev.startswith(('<','#','**','[^','*','|','{:','---')): continue
        if nxt.startswith(('<','#','**','[^','*','|','{:','---')): continue
        if prev[-1] in ENDERS: continue
        for c in CONNECTORS:
            if nxt.startswith(c):
                line = text[:text.find(paras[i+1])].count(chr(10))+1
                print(f'{p.name} L{line}  ...{prev[-25:]} | {nxt[:25]}...')
                break
"
```

命中的需人工核查：对照 calvin_raw/<book>-scan/calvin_<book>_zh.md 看
两段之间是否有 `<!-- PAGE N -->` 标记——若有，几乎肯定是 OCR 跨页强分段
的 bug，删 `\n\n` 合并。

**长期修复**（publish 阶段）：`restructure_scan_book.py` 应在合并 per-page
md 之前，对每个 page 边界（`<!-- PAGE N -->` 注释处）检查前段末是否结句
符号——若不是，把 `\n\n` 改为空字符串合并段。但已发布的书只能 detect +
手工修，不再重跑 publish。

### ⚠️ Gate-15：sub-heading 总论段错位（在 section heading 之前）

**Root cause**：`detect_paragraph_verse` 启发式只识别带数字前缀的段（`14 …`）
或 CUV 经文模糊匹配。verse 注释开头的 **"总论段"** —— 无数字前缀、第一
人称论说体（如 "我在此不想提出别人的意见……" 这种 calvin 的 transition
段）—— 既不带数字也不引用经文，启发式 fallback 到 `cur_sec`，于是这种
本属于下一 section 的总论段被错放到上一 section 的最后位置（紧贴下一
`## 罗马书 N:A-B` heading 之前）。

**实战案例**（2026-06-17 罗马书 10:14）：
- OCR raw page_0227 顺序正确：v.16 / v.17 经文段 → "我在此不想提出别人的
  意见…" 总论段 → v.14 主体段（注：calvin 注释经常在 verse 组经文之后先有
  总论段，再进入逐节注释）
- publish 后总论段被错放到 `## 罗马书 10:14-17` heading 之前的 v.13
  注释末尾位置
- 用户截图：v.14-17 经文后应是"我在此不想提出..."，但网页是 scripture-box
  之前

**检测规则**（严格 opener 避免误报）：
- 扫每个 `## 罗马书 N:A-B` heading 紧前的最后一段
- 段首是 **特定 calvin 总论 opener**: "我在此不"、"我在此愿"、"我将坦然"、
  "我想在此" 等第一人称论说体（**不包括** "本节/本段/我们/对于" 等，因为
  这些在 verse 注释延续段中也很常见）
- 命中 → 报告，需人工核查上下文是否确属下一 section 总论

**修复操作**：
1. 确认段在 `calvin_raw/<book>-scan/calvin_<book>_zh.md` 中的位置——若在
   scripture-box 之后、下一 verse 主体段之前，则确为总论段错位
2. 把段从 section heading 之前剪出，粘贴到下一 section 的 `<verse-anchor N:A>`
   之后、`**书 N:A。**` 主体段之前
3. 再跑 audit 确认所有 gate 0 命中

**长期修复**（publish 阶段）：`detect_paragraph_verse` 应识别 sub-heading
段并归到下一 section——目前已开 STRICT_DIGIT_ONLY 关闭了 CUV 模糊匹配，
但缺正向识别。已发布书只能 detect + 手工修。

**Opener 列表是渐进的**：如果用户发现新的 sub-heading 错位 case，根据该段
首词加进 OPENERS 元组（见 `scripts/fix_romans_ocr_artifacts.py`）。务必
确保新加的 opener 不会与 verse 注释正常延续段冲突（如 "我们/本节/本段"
这种常见词不要加，会大量误报）。

### ⚠️ Gate-16：延续段重复（无 verse-marker 的段被输出两次）

**Root cause**：publish 把跨页延续段（无 `**罗马书 N:V。**` 主体段 marker
的 verse 注释 continuation 段）有时输出两次——一次错位在上一 section 末
（anchor 之前），一次在正常位置（anchor 之后）。Gate-9 只查带 marker 的
主体段双重，抓不到无 marker 的延续段重复。

**实战案例**（2026-06-17 罗马书 10:21）：
- "我整天伸手是着重语气的表示..." 段同时出现在 v.20 后（L210）和 v.21
  anchor 后（L223）
- 用户截图发现，要求 skill 修复

**检测**：扫所有段（按 `\n\n` 分割），排除控制段（HTML/heading/`**`/`[^`），
按段首 30 字符 hash，如果同 prefix 出现 ≥ 2 次 → 报告。当前对 1-10 章
扫到 22 处重复段（每处都是 publish 的真实 bug）。

```python
python3 -c "
import re, pathlib
for p in sorted(pathlib.Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    paras = text.split('\n\n')
    pos = 0
    seen = {}
    for para in paras:
        s = para.strip()
        if (s.startswith(('<','#','**','[^','*','|','{:','---','!')) or len(s)<60):
            pos += len(para)+2; continue
        prefix = s[:30]
        line = text[:pos].count(chr(10))+1
        seen.setdefault(prefix, []).append(line)
        pos += len(para)+2
    for k, v in seen.items():
        if len(v) >= 2: print(f'{p.name}: {v}  \"{k}...\"')
"
```

**修复**：保留 anchor 之后的版本，删除错位副本（位置在 anchor 之前的）。

### ⚠️ Gate-17：verse 主体段被跨页截断（段尾非结句符号 + 段短）

**Root cause**：PDF 跨页时同一 verse 主体段被拆，publish 没拼接 page
边界——结果主体段在 OCR 跨页处中断，最后是单字 + 立刻 `\n\n`。这是
Gate-14（跨页强分段）的特例，但主体段更严重（影响 verse 语义）。

**实战案例**（2026-06-17 罗马书 10:21）：
- v.21 主体段被截断为 "**罗马书 10:21。** 至于以色列人，他说保罗再一次提到
  上帝弃绝犹太人而恩"（"恩" 单字结尾，未接续 "待外邦人的理由..."）

**检测**：扫所有 `**罗马书 N:V。**` 主体段，整段长 < 100 字 + 段尾不是
结句符号集 `。！？；" 》 ） 】 * >` → 报告。

```python
python3 -c "
import re, pathlib
ENDERS = ('。','！','？','；','\"','\"','」','》','）','】','*','>')
for p in sorted(pathlib.Path('calvin/<book>').glob('*.md')):
    if not p.stem.isdigit(): continue
    text = p.read_text(encoding='utf-8')
    ch = int(p.stem)
    for m in re.finditer(rf'\*\*<书名>\s+{ch}:(\d+)。\*\*', text):
        end_m = re.search(r'\n\n', text[m.start():])
        para = text[m.start():m.start()+end_m.start()] if end_m else text[m.start():]
        if len(para) < 100 and para.rstrip()[-1] not in ENDERS:
            line = text[:m.start()].count(chr(10))+1
            print(f'{p.name}: v.{ch}:{m.group(1)} L{line}  tail=...{para[-25:]}')
"
```

**修复**：
1. 查 `calvin_raw/<book>-scan/ocr/page_NNNN.md` 边界确认续文
2. 若 OCR raw 跨页有续文 → 拼接到主体段末尾
3. 若 OCR raw 也漏 → 请求用户提供 PDF 物理页扫描（按
   [reference-calvin-pdf-path]）
4. **不要自己从英文版翻译续文**（[feedback-no-self-translation-from-en]）

### 软 gate（不阻塞，但要扫一眼）

```bash
# Soft-Gate-7: orphan-fragment（短独立段，疑似 Bible-dump 误删后的尾巴）
python3 scripts/audit_orphan_fragments.py calvin/<book>
# 输出 ★ LIKELY 标记的段（开头是续接词如 "出于"/"但"/"再者"...）
# 重点人工核查；对照 calvin_raw/<book>-scan/ocr/page_NNNN.md 上一页页尾。
```

误报率较高（60-80 字的合理 Calvin 短注释段也会触发），不进必过 gate。
但 ★ LIKELY 一栏务必扫一遍，**这是发现 Bible-dump 误删的最后防线**
（romans v.21 commentary opener 被误删整段，靠这个软 gate 才能在
publish 阶段发现，否则要等用户截图才暴露）。

不要让用户帮你查 — 上线前自己跑一遍，0 命中再 commit。

---

## 完成后

→ [05-finalize.md](05-finalize.md)
