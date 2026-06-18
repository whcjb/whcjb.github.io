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
- [ ] **经文块是单列还是双语 2 列**？翻几页 scripture-section 看左/右两列是否都有
      `**N.**` 节号——是 → 必须走 §11 双语 table 路径（1cor / 2cor 等）
- [ ] 书名是否数字前缀（`1 CORINTHIANS / 2 JOHN`）？是 → SCRIPTURE_SEC_RE 必须含
      `\d?\s*` 前缀，否则 scripture-mode 无法激活（见 §11.1）
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

## 11. 双语 2 列经文块（1cor 等 Ages 双语 PDF）

部分 Ages PDF 经文区是**左英文 / 右拉丁文 2 列并排**（1 Corinthians、2 Corinthians、
romans 双语段落等）。**不可**简化成 "只保留英文" 或 "英文/拉丁文交替单列"——
两种都被用户打回过。必须按 PDF 原样还原 2 列布局。

### 11.0 用户底线（被反复强调过）

> "使用两列，一列英文，一列拉丁文，和 pdf 保持一致"
> "经文块应该怎么处理"

输出形态必须是单一 `<div class="scripture-box scripture-box--bilingual">` 包一个
`<table class="scripture-bilingual">`，每节一行 `<tr><td.scripture-en><td.scripture-la></tr>`。
不能是 6 个独立 `<p>`，也不能是英文+拉丁文塞同一段。

### 11.1 extractor (`phil_reconstruct_page`)

scripture-mode 状态机要点：

```python
LATIN_X_MIN = 200   # 由 diagnose 校准；1cor 410 页宽下 217 是 Latin 列起点
SCRIPTURE_BLOCK_WIDTH_MAX = 290

in_scripture_mode = False
scripture_buffer    = []   # 左列（English）累积
scripture_buffer_la = []   # 右列（Latin）累积  ← 旧版只有 EN buffer，把 Latin 丢了

# 进入 scripture-mode：H2 行匹配 <NNNNNN>BOOK Ch:V-V'
# 注意书名允许数字前缀：`\d?\s*[A-Z][A-Za-z]*...`
#   旧 regex `^[A-Z]...` 无法匹 `1 CORINTHIANS / 2 JOHN`，scripture-mode 不激活
SCRIPTURE_SEC_RE = re.compile(
    r'^<(\d{6,7})>\s*(\d?\s*[A-Z][A-Za-z]*(?:\s\d)?[A-Z\s]*?\d+:\d+(?:[-,]\d{1,3})?)\s*$'
)

# 在 scripture-mode 内对每个 block：
# 1. 按 line.bbox.x0 < LATIN_X_MIN 切左列 / 右列
# 2. 左列行 → scripture_buffer，右列行 → scripture_buffer_la
# 3. 跨 block 续行：上一项 endswith('-') 时拼回去（PDF 末尾断字 hyphen）
# 4. flush 时机：下一个 H2 / 全宽 block（注释起首） / page boundary

def flush_scripture_buffer():
    en_text = ' '.join(scripture_buffer)
    la_text = ' '.join(scripture_buffer_la)
    if not la_text.strip():
        # 单列（acts/john/romans 这类纯英文版）→ 走旧 [BODY] 路径，不要影响这些书
        output_lines.append(f'[BODY] {en_text}')
        return
    # 双列：按节号 split，配对后用 [SCRIPTURE_ROW] 投递给 structured_to_md
    en_verses = _split_verses(en_text)   # 拆 `1. ... 2. ... 3. ...` 为 [('1', txt), ...]
    la_verses = _split_verses(la_text)
    en_map = {n: t for n, t in en_verses}
    la_map = {n: t for n, t in la_verses}
    for n in sorted(set(en_map) | set(la_map), key=int):
        en = en_map.get(n, '').strip()
        la = la_map.get(n, '').strip()
        output_lines.append(f'[SCRIPTURE_ROW] {n}|||EN|||{en}|||LA|||{la}')
```

**为什么是 `_split_verses` 后再配对**：PyMuPDF 经常把 "Latin 节 N 末尾 + English
节 N+1 起首" 合并到同一个 block，分行后整段会出现 `1. Paulus... 2. Unto the
church...` 混着 Latin/English 的怪段。按节号 split 能消除这种合并产生的混乱。

### 11.2 structured_to_md：`[SCRIPTURE_ROW]` 处理器

⚠️ **kramdown 不处理 `<td>` 内 markdown**——即使外层 `<div class="scripture-box"
markdown="1">` 设了 `markdown="1"`，`<td>` 内部依然是纯 HTML。所以塞进 td 前要
手工转 `*X*`/`**X**`/`[^fN]` 这些 inline markdown：

```python
def _md_to_html_inline(s):
    s = format_inline(s)
    s = apply_verse_styling(s, red=False)
    s = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<em>\1</em>', s)
    # 1cor 用 [^f35] 风格脚注标签，兼容 [^N] 与 [^fN]
    s = re.sub(
        r'\[\^([Ff]?\d+[A-Za-z]?)\]',
        r'<sup id="fnref:\1"><a href="#fn:\1" class="footnote">\1</a></sup>',
        s,
    )
    return s.strip()

elif tag == 'SCRIPTURE_ROW':
    m = re.match(r'^(\d+)\|\|\|EN\|\|\|(.*?)\|\|\|LA\|\|\|(.*)$', content, re.DOTALL)
    if m:
        n_str, en_raw, la_raw = m.groups()
        scripture_rows.append((n_str, _md_to_html_inline(en_raw),
                                       _md_to_html_inline(la_raw)))
    continue
```

flush_scripture 的双语分支 render 完 table 后，还要 emit 一行 kramdown stub 让
`<sup>` 跳转目标 `<li id="fn:fN">` 仍被 kramdown 生成：

```python
# 从 <sup id="fnref:N"> 反向提取所有出现过的脚注编号，保序去重
ordered = unique_preserve_order(re.findall(r'id="fnref:([Ff]?\d+[A-Za-z]?)"', table_html))
if ordered:
    stub = ' '.join(f'[^{n}]' for n in ordered)
    out.append('')
    out.append(stub)
    out.append('{:.scripture-fnref-stub}')   # CSS display:none，仅做 kramdown ref 占位
```

`scripture_rows` 是和 `scripture_lines` 并列的状态。`flush_scripture` 判断：

```python
if scripture_rows:
    # 渲染 2 列 <table class="scripture-bilingual">
elif scripture_lines:
    # 旧的单列段落（acts/john/romans）
```

**关键**：BODY 注释段开始时（in_scripture 命中 fall-out 分支），必须**同时**检查
`scripture_lines` 和 `scripture_rows` 是否非空，任一非空就 flush。否则双语 box 会
落到注释段之后（用户视野里先看到注释、再看到经文，错位）。

### 11.3 CSS：`<table class="scripture-bilingual">`

```css
.calvin-en-content .scripture-bilingual {
  width: 100%; border-collapse: collapse; margin: 8px 0 0;
}
.calvin-en-content .scripture-bilingual td {
  vertical-align: top; padding: 6px 12px 6px 0; width: 50%;
}
.calvin-en-content .scripture-bilingual td.scripture-la {
  padding: 6px 0 6px 12px;
  border-left: 1px dotted #888;
  font-style: italic;       /* 拉丁文整列斜体 */
}
@media (max-width: 640px) {
  /* 窄屏堆叠：英文上 / 拉丁下，用点线横线分隔 */
  .calvin-en-content .scripture-bilingual,
  .calvin-en-content .scripture-bilingual tbody,
  .calvin-en-content .scripture-bilingual tr,
  .calvin-en-content .scripture-bilingual td { display: block; width: 100%; border: none; padding: 4px 0; }
  .calvin-en-content .scripture-bilingual td.scripture-la {
    border-left: none; border-top: 1px dotted #888; padding-top: 6px;
  }
}
```

### 11.4 反例（已踩过）

| 现象 | 根因 | Fix |
|---|---|---|
| 第 1/2 个 scripture-section 显示为 centered 标题，没框 | SCRIPTURE_SEC_RE 不允许 `1 CORINTHIANS` 数字前缀 → scripture-mode 不激活 | 加 `\d?\s*` 前缀 |
| 经文块只显示英文，拉丁文消失 | scripture_buffer 只收 line_lefts，line_rights 被丢 | 加 scripture_buffer_la 同步收集 + flush 时配对 |
| 经文块里 Latin/English 混在一段（`1. Paulus... 2. Unto the church...`）| PyMuPDF 把跨列邻行合并到同一 block，extractor 没按列切分就拼接 | 按 line.bbox.x0 切左/右列；flush 时按节号 split 再配对 |
| scripture-box 出现在注释段之后（错位）| BODY 注释命中 fall-out 只 flush `scripture_lines`，没 flush `scripture_rows` | fall-out 路径同时检查两个 buffer，任一非空就 flush |
| 用 `has_leading_italic = <sty c="*" i="1">` 当注释段标志 | 经文里 KJV 风格 `*to be*` 是 `i="1"` 黑斜体，会误判为注释 | 只匹红斜体 `<sty c="800000" i="1">` |
| 渲染时所有经文挤一段（不分行）| flush_scripture 用 `' '.join(scripture_lines)` 一段输出 | len==1 合并，len>1 各自一段；双语走 table 分支 |
| `<td>` 里出现原样 `*to be*` / `[^f35]` 字面字符 | kramdown 不处理 `<td>` 内 markdown（即便外层 div 有 markdown="1"）| SCRIPTURE_ROW 塞进 td 前手工转：`*X*`→`<em>`、`**X**`→`<strong>`、`[^fN]`→`<sup id="fnref:fN">`；并 emit `[^fN]\n{:.scripture-fnref-stub}` 占位让 kramdown 生成 `<li id="fn:fN">`（CSS `.scripture-fnref-stub{display:none}` 隐藏占位）|
| 脚注标签是 `[^f35]` 不是 `[^35]` 也要支持 | 1cor 用 `f` 前缀的 fnN 标签 | fnref regex 用 `\[\^([Ff]?\d+[A-Za-z]?)\]` 兼容 `[^N]` 和 `[^fN]` |
| Ages back-section 大量 `ftN.` 风格 def（带点）被丢，章节里只剩个位数 fn 定义 | 同一本 PDF 里 def 标签出现两种格式：`<sty>ftN</sty>` 不带点，`<sty>ftN.</sty>` 带点；structured_to_md 的 FN_DEF_RE / strip 正则只允许不带点版本，带点 def 走不到 `[^fN]:` 分支被当 body 正文 emit。2cor 前半 book 用了带点格式，ft11–ft240 全部漏译 | 两处正则都允许可选 `.`：`FN_DEF_RE = r'^\s*([fF][tT]?\d+)\.?\s+(.*)$'`；strip 内部 `<sty>...ftN\.?\s*</sty>` |
| 居中段落里出现字面 `[^f7]` / `*italic*` 而不是渲染为 sup / em | structured_to_md 某条 `out.append('<p style="...">{body}</p>')` 漏了 `markdown="1"` 属性 → kramdown 不处理 `<p>` 内 markdown | 任何 emit `<p>` 含正文片段的位置都必须带 `markdown="1"`（即便外层 div 有也不传染）；2cor preface 踩到的是 navy-quote 居中段（行 1025）|

---

## 12. scripture-box 视觉样式必须按 PDF 还原

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

## 13. 必读引用

- [refs/principles.md](refs/principles.md)
- [refs/helpers.md](refs/helpers.md) §1.5（`heb_*` / Ages 函数）
- [refs/anti-patterns.md](refs/anti-patterns.md)

---

## 14. 完成后 audit

跑 [refs/audit-gates.md](refs/audit-gates.md) 全部 gate。

---

## 15. 进入下一步

raw txt 干净后 → [03-publish-en.md](03-publish-en.md)
