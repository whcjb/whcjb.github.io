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

## 完成后 → audit gates

跑 self-audit 不要让用户帮你查。脚本中已写好的检查项至少包括：

```python
# 0 issues 之前不能 commit
- BARE-DIGIT prefix (paragraph starts with `0X` `1X` etc.)
- CIRCLED-DIGIT prefix (未促进的 ① 等开头)
- MISPLACED verse-opener (该 verse 不在本 section range 内)
- MID-SENT-BREAK (前段无终止符 + 当前段以 `X，` 续)
- Orphan fn refs (`[^N]` 在 body 但无 `[^N]: text` 定义)
- Running header leak (`# {book_cn}·X章`、`# {book_cn}·纲要`、
  `加尔文文集·X注释` 等 OCR 跨页头部混入正文 — 必须在 normalize_page
  阶段 strip)
- Bible text dump (OCR 把整章 Bible 全段抓成一个长段，>= 5 个圆圈
  数字 + 长度 > 300 字。scripture-box 已有 CUV 干净版，应丢弃 dump)
```

---

## 完成后

→ [05-finalize.md](05-finalize.md)
