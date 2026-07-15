# Step 2b: CCEL Calvin Harmony 提取

适用：**matthew1（共观福音卷一）/ harmony3（卷三）/ acts1**。`format: 'ccel_harmony'` 或 `'ccel_acts'`。

平行福音（matthew old vol 2）见 [02c-extract-parallel.md](02c-extract-parallel.md)。

---

## 起手 5 条 checklist

进入本步骤前**必须**已完成 [01-diagnose.md](01-diagnose.md)。再问自己：

- [ ] 这本 PDF 含 italic 吗？ → 用 `ccel_spans_to_md` 处理 PyMuPDF flag bit 2
- [ ] 含 footnote 吗？ → 用 `parse_ccel_footnote_block`，**同页 FN 块按 y 序合并**后再 parse
- [ ] 含行末断字吗？ → 末尾追加 `ccel_fix_hyphenation`
- [ ] 含居中标题/经文吗？ → cfg 必须 `centering: True`
- [ ] 段落边界靠什么？ → `split_lines_by_paragraph_indent` 按首行缩进切

填完才能 emit。

---

## 1. 主入口

```bash
python3 scripts/calvin_extract.py matthew1   # or harmony3 / acts1
```

调用 `extract_ccel_harmony(cfg)` 或 `extract_ccel_acts(cfg)`，配置见 calvin_extract.py 行 27+ `VOLUMES`。

---

## 2. 标准提取循环（写新代码可复用）

```python
import sys
sys.path.insert(0, '/Users/yanpeifa/Documents/whcjb.github.io')
import fitz
from scripts.calvin_extract import (
    ccel_harmony_is_running_header,
    ccel_harmony_is_page_number,
    ccel_harmony_is_footnote,
    ccel_spans_to_md,
    split_lines_by_paragraph_indent,
    parse_ccel_footnote_block,
    ccel_fix_hyphenation,
    _fix_split_italic_quotes,
)

doc = fitz.open(PDF)
for pn in PAGES:
    page = doc[pn]
    d = page.get_text('dict')
    body_lines = []
    page_fn_blocks = []
    for b in d['blocks']:
        if b.get('type', 0) != 0: continue
        if ccel_harmony_is_running_header(b, cfg): continue
        if ccel_harmony_is_page_number(b, cfg): continue
        if ccel_harmony_is_footnote(b, cfg):
            page_fn_blocks.append(b)
            continue
        body_lines.extend(b.get('lines', []))
    
    # 段落切分（按首行缩进）
    groups = split_lines_by_paragraph_indent(body_lines, cfg['body_left'])
    for grp in groups:
        md = ccel_spans_to_md(grp, fn_size_max=cfg['footnote_size_max'])
        md = ccel_fix_hyphenation(md)
        md = _fix_split_italic_quotes(md)   # §0.5
        if md:
            paragraphs.append(md)
    
    # 脚注：同页所有 FN 块按 y 序合并为 virtual block
    if page_fn_blocks:
        page_fn_blocks.sort(key=lambda b: b['bbox'][1])
        merged_lines = []
        for fb in page_fn_blocks:
            merged_lines.extend(fb.get('lines', []))
        for num, text in parse_ccel_footnote_block({'lines': merged_lines}):
            footnote_defs[int(num)] = text
```

**关键**：FN 块**同页合并**——不合并会导致脚注 8（法文）+ 脚注 8（英译续行）分在两 block 时只保留法文部分，丢英译。见 [anti-pattern H](refs/anti-patterns.md#h)。

---

## 3. 多列章首平行经文（共观福音 N 列表格）

CCEL Harmony PDF 章首常有 2-3 栏并排经文（如 `MATTHEW 4:1-4; MARK 1:12-13; LUKE 4:1-4`）。**这是 ccel_harmony 格式独有的复杂场景**。

### 3.1 section_col_layout 锁定机制

```python
# section header 出现时按卷名计列数
n_books = len(split_bible_refs_by_book(section_text))   # [principles §0.1]
if n_books >= 2:
    bl, br = cfg['body_left'], cfg['body_right']
    slot_w = (br - bl) / n_books
    slot_x0s = [bl + i * slot_w + 5 for i in range(n_books)]
    section_col_layout = (n_books, slot_x0s)
else:
    section_col_layout = None
```

后续每个 block 进入 `split_block_by_columns` 时传 `expected_slot_x0s=slot_x0s`，强制按这些 x0 分桶（不靠每个 block 自己聚簇）。

### 3.2 multi-col emit

```python
def emit_multi_col(cols) -> bool:
    """[principles §0.2] 过滤内化到 emit"""
    if cols_look_like_commentary(cols):
        return False
    # 输出 <!--SCRIPTURE col=N of=M--> 标记
    for i, col_md in enumerate(cols):
        output_blocks.append(f'<!--SCRIPTURE col={i} of={len(cols)}-->\n{col_md}')
    return True
```

调用方：
```python
cols = split_block_by_columns(block, page_mid, expected_slot_x0s=slot_x0s)
if cols and emit_multi_col(cols):
    bi += 1; continue
# fall through to single-col processing
```

### 3.3 跨 block 前瞻合并

PyMuPDF 偶尔把章首多列经文拆成「小 intro 块 + 主体大块」。**单独 split 都不够多列**，需要前瞻合并：

```python
if block_looks_like_scripture_fragment(block) and bi + 1 < len(blocks):
    nb = blocks[bi + 1]
    if (nb['type'] == 0 and not is_header/pgnum/footnote/section):
        fake_blk = {'lines': list(block['lines']) + list(nb['lines'])}
        cols = split_block_by_columns(fake_blk, page_mid, expected_slot_x0s=slot_x0s)
        if cols and emit_multi_col(cols):
            bi += 2  # 两个 block 一起消费
            continue
```

### 3.4 跨页单列续接块

前面 emit 多列后，下一页可能只有某一列的续接小段（< 200px 宽）。按 x0 / cx 匹配到 `last_col_centers` 的某列再 emit `col=N of=M`。

### 3.5 灾难块（catastrophic block）—— §0.6 仍未完全解决

**症状**：单 block 内多列文本被 PyMuPDF 平面化（line bbox x0 是 col 0，但 line text 含 cols 1+2 内容）。`split_block_by_columns` 看 line-level x0 fail。

**典型现场**：ch10 Matt 10:26-31，col=2 倾倒 56 行混入三栏文本。

**临时方案**：hand-fix 该 section（按 PDF 节号锚点重组三栏）。**不是编造**——所有文字都来自原 PDF，只是按节号重新分到对应列。

**长期方案**：在 split_block_by_columns 加 span-level x0 binning fallback（待实现）。

---

## 4. 节号 verse marker 处理

CCEL PDF 中节号通常是 bold 数字。`ccel_spans_to_md` 自动包成 `**N.**`：

```python
# 在 ccel_spans_to_md 内部
if is_bold and re.match(r'^\d+$', t.strip()):
    # consume optional non-bold period + optional bold NBSP
    parts.append(f'**{num}.**')
```

**陷阱**：bold 节号偶尔被切成 `N` + `.` 两段（不同 size 或 flags）。emit 出口必须 `result.replace('****', '')` 收尾（§0.4）。

---

## 5. 同 block 内段首缩进必须拆段

某些 PDF 把多段挤在一个 PyMuPDF block 内（无空行隔开）。靠**首行缩进**（line.x0 > body_left + 10）切：

```python
groups = split_lines_by_paragraph_indent(lines, cfg['body_left'])
# 每个 group 一段
```

未拆分 = 段落超长 = [anti-pattern I](refs/anti-patterns.md#i)。

---

## 6. 居中检测（标题 / 经文引用）

```python
classify_lines_by_centering(lines, cfg)
```

返回 `[is_centered, line_obj, text]` 列表。注意：
- 拒绝**uniform-margin 块**（每行 lm/rm 都相同 → 一般是 narrow 列正文，不是居中）
- 开引号 `"` 前向 promotion：上一行以 `"` 结尾 + 当前行居中 → 上一行也提升为居中（处理跨行开引号）

---

## 7. 必读引用

- [refs/principles.md](refs/principles.md) — 7 条全局原则
- [refs/helpers.md](refs/helpers.md) §1.2 — CCEL Harmony helper 函数列表
- [refs/anti-patterns.md](refs/anti-patterns.md) — A/B/C/E/F/H/I/J/K/L 都与 CCEL 提取相关

---

## 8. 完成后 audit

跑 [refs/audit-gates.md](refs/audit-gates.md) 全 8 gate。raw txt 必须通过 Gate 1（emit 规范化）+ Gate 5（fn ref/def）。

---

## 9. 进入下一步

raw txt 干净后 → [03-publish-en.md](03-publish-en.md)
