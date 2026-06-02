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
