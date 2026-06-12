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

发布完成后必须跑 **两个** relocation 脚本：

```bash
# 章内迁移：v.32 段落被错放到 section 1:22-28 → 移到 1:29-32
python3 scripts/relocate_misplaced_verse_commentary.py \
  --book-cn 罗马书 --dir calvin/romans

# 跨章迁移：v.22-36 段落被错放到 12.md（Rom 12 max 21）→ 移到 11.md
python3 scripts/relocate_cross_chapter_verse.py \
  --book-cn 罗马书 --dir calvin/romans
```

两脚本都依赖 `VERSE_COUNTS` 表（CUV chapter-max-verse counts）。新书要
在脚本里增加该书的 verse-count dict。

参考 romans 实战：**93 处章内 + 14 处跨章**，共 107 处 misplaced。

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

**修复**：form 3 length 阈值从 < 200 改为 < 80，超过 80 字符要靠
`_is_bible_verse_text` 做 CUV 相似度 ≥ 0.7 才删。Romans 实战恢复 ~700
行漏删内容。

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

下面 6 项 audit 全部 0 命中之前**不能** commit + push。如果用户截图发现
任何一项有漏，说明这道门没把住。

```bash
# Gate-1: BARE-DIGIT 段落开头但不在 section range
python3 scripts/relocate_misplaced_verse_commentary.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0

# Gate-2: 跨章 BARE-DIGIT overflow
python3 scripts/relocate_cross_chapter_verse.py \
  --book-cn <书名> --dir calvin/<book>   # 应输出 Total: 0

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

```

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
