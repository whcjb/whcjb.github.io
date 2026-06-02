# Step 2a: Ages 双语 PDF 提取

适用：**phil / heb / john**（Ages Digital Library 出版的圣经注释）。`format: 'ages_phil'` / `'ages_heb'`。

格式特征：**左英文 / 右拉丁文两列并排**。x0 双峰分布：
- 英文列：`block['bbox'][0] < 200`
- 拉丁文列：`block['bbox'][0] >= 200`

经文区输出 HTML 双语表格；注释区只取英文列。

---

## 起手 5 条 checklist

进入本步骤前**必须**已完成 [01-diagnose.md](01-diagnose.md)。再问自己：

- [ ] LATIN_X_MIN 已校准（通常 200，可能需调）
- [ ] 含希腊文吗？ → 必须转 Unicode（见 §4）
- [ ] 含 Ages 红色斜体经文吗？ → 染色阶段二（见 §5）
- [ ] 段落首行缩进阈值已确认（PARA_INDENT_LOW）
- [ ] 脚注区在文档末尾还是每页底？ → ages_heb 在末尾集中

---

## 1. 主入口

```bash
python3 scripts/calvin_extract.py phil   # or heb / john
```

调用 `extract_ages_heb(cfg)` 或 `extract_ages_phil(cfg)`。

---

## 2. 关键识别函数

```python
LATIN_X_MIN = 200   # 由 diagnose 校准

def is_pure_latin_block(block):
    """整 block 在拉丁文列。"""
    return block['bbox'][0] >= LATIN_X_MIN

def is_verse_block(block):
    """经文块：首个英文列行以 bold 数字开头（size>=10 排除脚注上标）"""
    for line in block.get('lines', []):
        spans = line.get('spans', [])
        if not spans: continue
        lx = line['bbox'][0]
        if lx >= LATIN_X_MIN: continue   # 跳过拉丁行
        fs = spans[0]
        flags = fs.get('flags', 0)
        size = fs.get('size', 0)
        t = fs['text'].strip()
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            return True
        break
    return False

def is_scripture_header(block):
    """'Book N:M' / 'Book Chapter N:M'，bold+italic，size>=14"""
    span = get_first_span(block)
    if not span: return False
    if size >= 14 and (flags & 20) and 80 < x0 < 300:
        text = get_block_text(block).strip()
        if re.match(r'^(Hebrews|Philippians|Romans|...)\s+(Chapter\s+)?\d+:\d+', text):
            return True
    return False
```

详细见 [refs/helpers.md](refs/helpers.md) §1.5（`heb_*` 函数列表）。

---

## 3. 节号分裂处理（Ages 特有）

Ages PDF 经常把节号 `1` 和 `. text...` 拆成两个 span：

```python
def extract_line_rich(line):
    spans = [s for s in line.get('spans', []) if s.get('text', '')]
    parts = []
    skip_dot = False
    for span in spans:
        text = span['text']
        flags = span.get('flags', 0)
        size = span.get('size', 0)
        t = text.strip()
        if skip_dot:
            skip_dot = False
            if text.startswith('.'):
                text = text[1:]
            parts.append(text)
            continue
        # size >= 10 防止 6.6pt 脚注引用上标被误包成节号
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            num = t.rstrip('.')
            if not t.endswith('.'):
                skip_dot = True   # 句点在下一个 span
            parts.append(f'**{num}.**')
            continue
        # ... 处理 italic/bold/普通文本
```

见 `heb_extract_line_rich` 实现（scripts/calvin_extract.py 行 1508+）。

---

## 4. 希腊文转 Unicode

**Ages 用自定义转写编码**，必须转 Unicode：

```python
# Ages 转写规则：
# - 辅音直接映射（a→α, b→β, g→γ, d→δ, e→ε, z→ζ, h→η, q→θ, i→ι, k→κ, ...）
# - 元音后跟 j=平气，><~ 重/锐/抑扬音，|=iota 下标
# - v=词尾 sigma
# - 双元音中声调符夹在两元音之间时属于第二个元音（ejmo>i → ἐμοί）
```

**触发条件**：
- 必须含 `><~{}+]` 之一才触发主 regex（避免误转纯英文）
- 主 regex 后做常见无 markers 的 Greek 短词显式替换（如 `ejn` → `ἐν`）

调用：见 calvin_extract.py 行 1922+ 的 `ages_greek_to_unicode`。

---

## 5. 红色斜体经文短语（Calvin 注释约定）

Calvin 注释中**经文引语**用红色斜体。Ages PDF 表现为：
- 斜体 span（flag bit 2）
- 颜色 #800000 红（或 #B22222 等深红）

**处理分两阶段**：

### 阶段 1：extractor 保留斜体跨度

```python
# 相邻同 style italic span 合并为一个完整 italic 段
# 不要 emit 每 span 单独 *…*，否则跨 span 边界丢失
```

### 阶段 2：converter 按段落上下文决定染色

```python
def apply_verse_styling(body, red=False):
    """red=True 时把 *italic* 换成 <span style='color:#800000'>*italic*</span>"""
    
# 调用点：用「段落是否以 `N. ` 开头」决定 red 参数
in_commentary_section = False
for block in body_items:
    if is_h1(block):   # CHAPTER N → 重置
        in_commentary_section = False
    elif is_scripture_section_header(block):
        in_commentary_section = True
    elif is_body(block):
        red = in_commentary_section and not is_scripture_box(block)
        block = apply_verse_styling(block, red=red)
```

经文段（scripture-box 内）**不染色**——书名引用不该红。

---

## 6. 段落首行缩进拆段（Ages 特有）

Ages PDF 同一 PyMuPDF block 内常含多个段落（无空行）。**按段首缩进切**：

```python
# 阈值（必须从 PDF 校准，不硬编码）
PARA_INDENT_LOW  = 16   # 段首行 x0 - body_left 下限
PARA_INDENT_HIGH = 24   # 上限

# 构建 BODY item 时记录 indent
for line in block.get('lines', []):
    line_x0 = line['bbox'][0]
    indent = line_x0 - body_left
    items.append({'text': ..., 'indent': indent})

# Stage 1.5: 纯结构化合并
# - nxt_indent < PARA_INDENT_LOW → 无段首缩进 → 续行
# - 安全兜底：前段未结句（防止段首无缩进的新章节首段被误合并）
# - 特判：前段末有未闭合括号 → 强制合并（如 '(2 Corinthians'）
```

**⚠️ 严禁用 first_char（大小写）或 cur_ends_comma 等内容判断**——会误合并引文段落。

见 calvin_extract.py 行 3081+ Stage 1.5 实现。

---

## 7. Render 阶段：缩进 → 居中引文

```python
# BODY item indent > 20 → 居中引文（PDF 经文/拉丁文引用缩进均 > 20pt）
# 阈值说明：正文段落缩进约 18pt，所有引用 > 20pt
if item['indent'] > 20:
    md = f'<p style="text-align:center">{md}</p>'
```

---

## 8. 表格 `<td>` 内脚注引用

scripture-box / scripture-table 内的 `[^N]` kramdown 不会渲染（HTML 块内）。必须手工转：

```python
def fnref_to_html(text):
    """[^N] → <sup id="fnref:N"><a href="#fn:N" class="footnote">N</a></sup>"""
    return re.sub(r'\[\^([0-9]+)\]',
        r'<sup id="fnref:\1"><a href="#fn:\1" class="footnote">\1</a></sup>',
        text)
```

同时需要保留一个**隐藏 stub**让 kramdown 仍生成 `<li id="fn:N">` 定义：

```python
def fn_stub(refs):
    """<p class="scripture-fnref-stub" style="display:none">[^N1] [^N2]</p>"""
    refs_md = ' '.join(f'[^{n}]' for n in refs)
    return f'<p class="scripture-fnref-stub" style="display:none">{refs_md}</p>'
```

CSS：`.scripture-fnref-stub { display: none }`。

---

## 9. 段首孤立脚注引用：移到前段末尾（Stage 1.6）

PDF 偶尔把脚注引用 `^N` 放在新段开头（视觉上属于前段末尾的标点后）。Stage 1.6 处理：

```python
# 把段首孤立脚注引用移到前段末尾（含仅含引用的整段情形）
def move_orphan_fnref(items):
    for i in range(1, len(items)):
        cur = items[i]['text']
        m = re.match(r'^\s*(\[\^[0-9]+\])\s+(.*)$', cur)
        if m:
            ref, rest = m.group(1), m.group(2)
            items[i-1]['text'] += ref
            items[i]['text'] = rest
```

---

## 10. 跨页段落必须合并

```python
# 结构信号：nxt_indent < INDENT_LOW = 无段首缩进 = 续行
# 安全兜底：not is_sentence_end(prev) 防止段首无缩进的新章节首段被误合并
# 特判：prev_text 末有未闭合括号 → 强制合并
```

---

## 11. scripture-box 视觉样式必须按 PDF 还原

Ages PDF 经文区有**双蓝边框 + 浅黄底 + 灰色 ref banner**。john-en 必须保留这套样式：

```css
.calvin-en-content[data-book="john-en"] .scripture-box {
  border: 3px double #1d28e0;
  background: #fffce8;
  padding: 0;
}
.calvin-en-content[data-book="john-en"] .scripture-box .scripture-ref {
  background: #dcdcdc;
  text-align: center;
  font-size: 19px;
  font-weight: bold;
}
```

样式按 PDF 原样还原（[principles §0.0](refs/principles.md)），不能用通用样式凑合。

---

## 12. 必读引用

- [refs/principles.md](refs/principles.md)
- [refs/helpers.md](refs/helpers.md) §1.5（`heb_*` / Ages 函数）
- [refs/anti-patterns.md](refs/anti-patterns.md)

---

## 13. 完成后 audit

跑 [refs/audit-gates.md](refs/audit-gates.md) 全部 gate。

---

## 14. 进入下一步

raw txt 干净后 → [03-publish-en.md](03-publish-en.md)
