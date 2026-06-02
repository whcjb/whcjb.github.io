# Step 3: raw → 英文版发布

把 `calvin_raw/BOOK/BOOK_raw.txt` 加工成 `calvin/BOOK-en/*.md` + `index.html`。

适用所有英文版书卷。

---

## 起手 checklist

- [ ] raw txt 已通过 [audit-gates.md](refs/audit-gates.md) Gate 1（**** / <<<END / split italic 都 = 0）
- [ ] `calvin_raw/BOOK/publish.py` 已存在或基于现有模板创建
- [ ] `_layouts/calvin-en.html` 和 `_layouts/calvin-en-book.html` 已存在
- [ ] section header → chapter 边界映射已确认（章节起始 section title 列表）
- [ ] 前后章导航 label 已查（每章一行 `(N, "FIRST_HEADER", "Chapter N — Title")`）

---

## 1. 主入口

```bash
python3 calvin_raw/BOOK/publish.py
```

模板见 `calvin_raw/matthew1/publish.py` 或 `calvin_raw/harmony3/publish.py`。

---

## 2. 发布流水线（process_section_blocks 调用顺序）

```python
from scripts.harmony_utils import process_section_blocks

def format_chapter_content(sections_list):
    chapter_blocks = []
    for header, body in sections_list:
        chapter_blocks.append(f'## {header}')
        chapter_blocks.extend(process_section_blocks(header, body))
    return '\n\n'.join(chapter_blocks)
```

`process_section_blocks` 内部依次跑：

```
body → split_rich_by_verse → join_orphan_verse_numbers
     → merge_split_paragraphs → expand_verse_refs
     → _scripture_box (多列 → <table class="scripture-table">)
```

详见 [refs/helpers.md](refs/helpers.md) §2。

---

## 3. scripture-box 渲染

`_scripture_box(header, paras)` 渲染规则：

| 输入 | 输出 |
|---|---|
| 单列 `**N.**` 经文段 | `<div class="scripture-box"><p class="scripture-ref">REF</p><p>...</p></div>` |
| 多列 `<!--SCRIPTURE col=N of=M-->` 段 | `<div class="scripture-box scripture-box--multi">` + `<table class="scripture-table">` |
| 含 `[^N]` 脚注引用 | 必须用 `_fnref_to_html` 转 `<sup>`（kramdown 不解析 HTML 块内 markdown）+ 加 `_fn_stub` 让 kramdown 仍生成 `<li id="fn:N">` |

---

## 4. front matter 模板

```yaml
---
layout: calvin-en
book_id: harmony-1-en
book_name: "Calvin on the Harmony of the Evangelists (Vol. 1)"
chapter: 5
header-img: psalm-bg-mountain.jpg
date: 2026-05-27 15:48
prev_section: 4
prev_label: "Matthew 3"
next_section: 6
next_label: "Matthew 5"
---
```

**`book_name` 统一格式**：`Calvin on the Harmony of the Evangelists (Vol. N)`。

---

## 5. 章节边界确认（必做）

### 已知坑：边界过晚 → 下章 H1 + 首表格泄漏到本章末尾

**症状**：某章末尾出现孤立 `| 3 . ...` markdown 行（表格被截断，头部留在上一章）。

**修复**：
1. 用 grep 定位下一章 H1 精确行号，缩小本章结束边界
2. 删除本章多余的 H1 标题和表格行
3. 把下一章文件开头替换为完整 HTML 经文表格

**快速定位**：
```bash
grep -c "^# " calvin/BOOK-en/*.md   # 值 ≥2 = 该章受污染
grep -n "^| [0-9]" calvin/BOOK-en/*.md   # 该章首个表格被截断
```

### 已知坑：脚注分隔符 `---` 把最后一段渲染为 `<h2>`

**症状**：章节最后一个正文段落渲染为粗体居中大字。

**原因**：`build_fn_section` 用 `'\n---\n'` 开头，而 `content.strip()` 去末换行，导致段落和 `---` 之间无空行。Kramdown 把 `---` 紧接段落后视为 Setext H2 下划线。

**修复**：
```python
# 错误：
parts = ['\n---\n']

# 正确：
parts = ['\n\n---\n']
```

---

## 6. 序言文件必须是 `preface.md`

`calvin-en-book.html` 目录页硬编码链接 `/calvin/BOOK-en/preface/`。publish 脚本中：
- 第一个 section（`'introduction'` label）输出 → `preface.md`
- 标题 → `# Preface` 或 `Translator's Preface`
- 导航 label → `"Preface"`

写成 `introduction.md` 会让目录页链接 404。

---

## 7. 多列经文表的渲染细节

多列 emit 用 `<!--SCRIPTURE col=N of=M-->` 标记 + 段内容。`_scripture_box` 把同一 section header 下的所有 col 标记合成一个 `<table>`：

```python
# 同一 section 多 col 块按 col 号聚合
cells_by_col = collections.defaultdict(list)
for block in scripture_blocks:
    info = _scripture_col_info(block)
    if info:
        col_idx, n_cols = info
        cells_by_col[col_idx].append(block_text_without_marker)

# 渲染：每列拼成单 <td><p>
n_cols = max(cells_by_col) + 1
cells_html = ''
for ci in range(n_cols):
    cell_text = ' '.join(cells_by_col[ci])
    cells_html += f'<td><p>{cell_text}</p></td>'
```

---

## 8. 章首多列经文跨页续接

PDF 经文表横跨两页时，第二页通常是单列续接片段（< 200px 宽）。extract 阶段已用 `last_col_centers` 跟踪上一节列 cx，发布阶段不需要特殊处理——只要 raw 里 `<!--SCRIPTURE col=N of=M-->` 标记齐全，`_scripture_box` 自动聚合。

---

## 9. 完成后 audit

```bash
for f in calvin/BOOK-en/*.md; do
  bash scripts/audit-md.sh $f
done
```

每个 chapter md 都必须通过 [audit-gates.md](refs/audit-gates.md) 全部 gate。

---

## 10. 进入下一步

英文发布 OK → [04-translate-zh.md](04-translate-zh.md)（翻译中文）或 [06-finalize.md](06-finalize.md)（直接 commit + push）
