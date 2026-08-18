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

### Ages 格式书卷（phil / heb / john / 1cor-vol1 / 2cor 等）：通用脚本

```bash
python3 scripts/publish_calvin_en.py <book>
```

`<book>` 是 `calvin_raw/<book>/` 子目录名（如 `john` / `phil` / `heb` / `1cor-vol1`）。脚本自动：
- 推导 `book_id = <book>-en`
- 读 `calvin_raw/<book>/calvin_<book>.md` 作为 source MD
- 输出到 `calvin/<book>-en/`
- 从 `_data/calvin_books.yml` english section 查 book_name（短名自动 prepend "Calvin on "）
- 包含所有 §M1-M6 anti-pattern 修复（pending_fn_idx / 后部 CHAPTER N skip / has_preface 等）

**绝不再为每本 Ages 书新写 publish_<book>_en.py**——通用脚本已覆盖。

可选 override：`--name N` / `--src P` / `--out P` / `--book-id ID`。

### CCEL Harmony 书卷（matthew1 / harmony3 / matthew vol2 等）：仍用各自模板

CCEL 格式 publish 流程不同（依赖 `harmony_utils.process_section_blocks`），仍各自有 `calvin_raw/BOOK/publish.py`。模板见 `calvin_raw/matthew1/publish.py` 或 `calvin_raw/harmony3/publish.py`。

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

### ⚠️ `index.html` 必须含 `has_preface: true`（否则目录页隐藏前言链接）

`_layouts/calvin-en-book.html` 用 `{% if page.has_preface %}` 判断是否渲染 `<a class="preface-link">Translator's Preface →</a>` 链接。**publish 脚本生成 index.html 时必须输出 `has_preface: true`**——否则 preface.md 虽然存在、`/calvin/BOOK-en/preface/` 路由可访问，但目录页**没有入口链接**，用户从导航过去看不到序言。

```python
# Step 7: index.html
index_path = OUT_DIR / 'index.html'
index_path.write_text(
    f'---\n'
    f'layout: calvin-en-book\n'
    f'book_id: {BOOK_ID}\n'
    f'book_name: "{BOOK_NAME}"\n'
    f'chapters: {len(chapter_keys)}\n'
    f'has_preface: true\n'         # ← 必须
    f'---\n',
    encoding='utf-8',
)
```

漏 `has_preface` 这一行 → 用户问"前言怎么没了"。

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

## 9. 脚注标签必须用原始 label（`f35` 不是 `2`）

### 9.0 用户底线（被反复打回）

> "这里用 f36, 就写 f36, 为什么使用 2"

PDF body 用 `f36` 上标 / 底部 `ft36 text` —— 显示出来必须是 `f36`，不能是
kramdown 自动计数的 `1./2./3.`。

### 9.1 kramdown 默认行为不对

kramdown 把 `[^f36]` 渲染成：

```html
<sup id="fnref:f36"><a href="#fn:f36" class="footnote">2</a></sup>
   ↑ id/href 是 f36（对的）           ↑ 显示文字是 "2"（错的）
```

底部 `<li id="fn:f36">` 用 `<ol>` 编号显示 "1./2./3."（也错）。

### 9.2 修复：calvin-en.html runtime JS 改写

不要改 publish 脚本（kramdown 还要靠它生成 fn def `<li id="fn:N">` 链路），
而是在 layout 加一段 DOMContentLoaded 后跑的 JS，把：

1. 正文 `<sup>` 内 `<a>` 文字 → 用 sup.id 抽出 `fnref:` 后的 label
2. 底部 `<li>` 行首 insert 一个 `.fn-backref-num` 锚，textContent 同样 label

```javascript
(function() {
  // 1. 正文 sup 链接
  document.querySelectorAll('.calvin-en-content sup[id^="fnref:"] > a.footnote').forEach(function(a) {
    a.textContent = a.parentElement.id.replace(/^fnref:/, '');
  });
  // 2. 底部 fn 列表前缀
  document.querySelectorAll('.calvin-en-content .footnotes ol li[id]').forEach(function(li) {
    var label = li.id.replace(/^fn:/, '');
    var a = document.createElement('a');
    a.href = '#fnref:' + label;
    a.className = 'fn-backref-num';
    a.textContent = label;
    a.title = '返回引用位置';
    li.insertBefore(a, li.firstChild);
  });
})();
```

CSS 配套：`.footnotes ol { list-style: none; padding-left: 0; }` 去 ol 编号，
`.fn-backref-num { ... }` 锚样式。

**为什么 JS 不 publish 阶段做**：kramdown 解析 `[^fN]` 链路依赖默认渲染流程，
build-time 改写正文 sup 会破坏 fn def 自动收集。runtime JS 改文字不动 id/href，
保留 kramdown 跳转能力。

### 9.3 反例

| 现象 | 根因 | Fix |
|---|---|---|
| 正文 sup 显示 `2`，PDF 是 `f36` | kramdown 用顺序计数当 `<a>` 文字，id 是对的但文字不是 | layout JS 用 `sup.id.replace('fnref:','')` 替换 `<a>` 文字 |
| 底部 fn 列表显示 `1./2./3.` 编号 | `<ol>` 默认编号 + 旧 JS 用 `idx+1` 当 backref num | `<ol> list-style:none` + JS 改用 li.id 的 label |
| 手工 emit `<sup id="fnref:fN"><a>fN</a></sup>` 时正文显示 `fN`，但 kramdown 自动生成的还是 `2` | 两种来源对显示文字处理不同 | runtime JS 一并扫所有 `sup[id^="fnref:"]`，把 `<a>` 文字统一为 id label |

---

## 10. 完成后 audit

```bash
for f in calvin/BOOK-en/*.md; do
  bash scripts/audit-md.sh $f
done
```

每个 chapter md 都必须通过 [audit-gates.md](refs/audit-gates.md) 全部 gate。

**其中 Gate 5g（跨页断句）必须在开跑中译之前过。** 一句话被 `<!-- PAGE N -->`
截成两段时，中译会照着断句拆译；事后再修英文，受影响章节的中译得全部 `--resume`
重跑一遍。跑一条命令即可：

```bash
python3 scripts/fix_page_split_paragraphs.py --dry-run calvin/<book>-en   # 必须 0 处
```


---

## 11. 进入下一步

英文发布 OK → [04-translate-zh.md](04-translate-zh.md)（翻译中文）或 [06-finalize.md](06-finalize.md)（直接 commit + push）
