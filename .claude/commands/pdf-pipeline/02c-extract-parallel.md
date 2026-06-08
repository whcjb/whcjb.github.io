# Step 2c: 平行福音 PDF 提取

适用：旧版**马太注释卷二**（`harmony2`，原 `matthew-en`）。`format: 'ccel_parallel'`。

格式特征：**三栏并排**（左 Matthew，中 Mark，右 Luke），x0 三峰：
- 左列：`x0 ≈ 74`
- 中列：`x0 ≈ 230–274`
- 右列：`x0 ≈ 290–404`

与 Ages 双语（右列 `x0 ≈ 200+`）的区别：平行福音**右列起始 x0 更大**（≈ 290+）。

---

## 1. 主入口

```bash
python3 scripts/calvin_extract.py harmony2
```

调用 `extract_ccel_parallel(cfg)`。

---

## ⚠️ 已知坑：跨页经文表续接整页丢失（[anti-pattern O](refs/anti-patterns.md#o)）

CCEL parallel 格式 vol 2 中，**跨页 verse 续接块**的首 span 常是上一节的 footnote-ref 数字（6.6pt < `footnote_size_max`）。原 `ccel_pg_is_footnote` 只看首 span 字号 → **整页续接块被误判为脚注全部过滤**。

修复后逻辑：两个信号同时满足才判脚注：
```python
spans[0].size < footnote_size_max  AND  spans[1].size < 10
```

真脚注：first=6.3 + second=9.0 → IS fn ✓
经文续接：first=6.6 + second=12.0 → NOT fn ✓（第二 span 是正文字号说明本块是正文）

**写新提取器时**：每个 `is_*` 分类函数都问自己「光看首 span 够不够？」绝大多数情况都需要看第二 span / 字号分布 / block 位置等额外信号。

## ⚠️ 已知坑 2：narrow cols 跨列 span 合并 → 必须 word-level 提取（[§Q](refs/anti-patterns.md#q)）

vol 2 平行福音 cells ~187px 窄，PyMuPDF `get_text('dict')` 偶尔把**多列同 y 文本合并成单一 span**。span 起点 x0 在 Matt cell 内，但 span text 横跨 Matt + Luke 两列。span-level 和 line-level x0 分桶都无解。

修复：`extract_ccel_parallel` 在 verse_buf 收集时记录 word-level 数据：

```python
verse_buf.append((block, page.get_text('words'), span_size_map, page_idx))
```

`ccel_pg_build_verse_table` 按 word 的独立 bbox.x0 分桶，绕过 span 合并。

## ⚠️ 已知坑 3：跨页 word 排序必须含 page_idx（[§R](refs/anti-patterns.md#r)）

跨页 word 收集后排序，sort key **第一字段必须是 page_idx**：

```python
all_word_recs.sort(key=lambda r: (r[0], round(r[1]), r[2]))
#                                  ^页^    ^y^      ^x^
```

否则 p11 y=88 排到 p10 y=600 前 → cell 内容顺序错乱（v11 出现在 v7 之前）。

## ⚠️ 已知坑 4：`<td colspan="2">` 跨全宽行内容路由（[§S](refs/anti-patterns.md#s)）

PDF 中 Calvin 偶尔用跨全宽行表达「跨节经文引用」：在某 col 末尾标「Luke 16:16」label，下方跨全宽放该节经文。`transform_scripture_table` 必须检测 col 末尾 cross-ref label，把后续 colspan 内容路由到该 col：

```python
CROSS_REF_RE = re.compile(r'\b(Matthew|Mark|Luke|...)\s+\d+:\d+\s*\.?\s*$')
if 'colspan' in cell.attrs:
    target_col = 0
    for ci in range(n_cols):
        if col_texts[ci] and CROSS_REF_RE.search(col_texts[ci][-1].rstrip()):
            target_col = ci; break
    col_texts[target_col].append(cell.content)
```

无脑放第一栏 = Luke 16:16 内容跑到 Matt cell。

---

## 2. 关键 helper（`ccel_pg_*` 前缀）

见 [refs/helpers.md](refs/helpers.md) §1.3：

| 函数 | 作用 |
|---|---|
| `ccel_pg_is_page_header` | 顶端运行页眉 |
| `ccel_pg_is_page_number` | 页码 |
| `ccel_pg_is_footnote` | 脚注块（小字号）|
| `ccel_pg_is_section_header` | section 标题 |
| `ccel_pg_is_col_label` | 列标签（"Matthew 11:1-6", "Mark ..." 等）|
| `ccel_pg_extract_col_info` | 提取列结构 (col_titles, col_x0s) |
| `ccel_pg_is_verse_block` | 经文块 |
| `ccel_pg_is_index_start` | 索引页（停止信号）|
| `ccel_pg_spans_to_md` | spans → md，节号包成 `**N.**` |
| `ccel_pg_build_verse_table` | 渲染为 `<table>` HTML |

---

## 3. 输出格式（已重构为 scripture-table）

**注意**：原来 harmony2 raw 用 `<table class="calvin-scripture">`（横滚 sliding 表），已重构为 `<table class="scripture-table">`（多列同时显示，与共观福音卷一/三统一）。

输出结构：

```html
<div class="scripture-box scripture-box--multi">
<p class="scripture-ref">Matthew 11:1-6; Luke 7:18-23</p>
<table class="scripture-table">
<thead><tr><th>Matthew 11:1-6</th><th>Luke 7:18-23</th></tr></thead>
<tbody><tr>
  <td><p>1. ... 2. ... 3. ... 4. ... 5. ... 6. ...</p></td>
  <td><p>18. ... 19. ... 22. ... 23. ...</p></td>
</tr></tbody>
</table>
</div>
```

**每栏的多行合并为单个 `<p>`，多行 `<tr>` 合并为单行 `<tr>`，跨列 `<td colspan="N">` 内容追加到第一栏**。

---

## 4. 跨列内容（`<td colspan="2">`）的合并规则

某些 verse 只出现在一个 Gospel（如 Matt 13:24-30 没有 Mark/Luke 对应）。原 raw 用 `<td colspan="2">` 渲染。重构时：

- 把 `colspan` 单元格内容**追加到第一栏**（与 vol 1 ch10 处理一致）

```python
def transform_table(raw_html):
    for row in rows:
        cells = list(CELL_RE.finditer(row))
        if len(cells) == 1 and 'colspan' in cells[0].group('attrs'):
            col_texts[0].append(cells[0].group('content').strip())
        else:
            for ci, c in enumerate(cells[:n_cols]):
                col_texts[ci].append(c.group('content').strip())
```

---

## 5. CSS：scripture-table 等宽不滑动

```css
.calvin-en-content .scripture-table {
  width: 100%;
  table-layout: fixed;          /* 强制 N 栏等宽 */
  border-collapse: collapse;
}
.calvin-en-content .scripture-table th,
.calvin-en-content .scripture-table td {
  word-wrap: break-word;
  overflow-wrap: break-word;     /* 长词软断行 */
  padding: 8px 12px;
  vertical-align: top;
}
@media (max-width: 640px) {
  .calvin-en-content .scripture-table th,
  .calvin-en-content .scripture-table td {
    padding: 5px 6px;
    font-size: 13px;
  }
}
```

⚠️ **`.calvin-scripture`（旧类）不能用于共观福音**——`overflow-x: auto + min-width: 280px + white-space: nowrap` 会触发横向滑动（[anti-pattern N](refs/anti-patterns.md#n)）。

---

## 6. 命名统一

- 目录：`calvin/harmony-2-en/`（不是 `calvin/matthew-en/`）
- raw：`calvin_raw/harmony2/harmony2_raw.txt`
- yaml 短名：`Harmony of the Evangelists (Vol. 2)`
- 中文短名：`共观福音（卷二）`

---

## 7. 必读引用

- [refs/principles.md](refs/principles.md)
- [refs/helpers.md](refs/helpers.md) §1.3（`ccel_pg_*`）
- [refs/anti-patterns.md](refs/anti-patterns.md) §N（scripture-table 滑动）

---

## 8. 进入下一步

raw txt 干净后 → [03-publish-en.md](03-publish-en.md)
