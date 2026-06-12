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

### 3. Bible verse-count 表

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

不要让用户帮你查 — 上线前自己跑一遍，0 命中再 commit。

---

## 完成后

→ [05-finalize.md](05-finalize.md)
