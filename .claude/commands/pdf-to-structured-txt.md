# PDF to Markdown + 发布到网站（含中文翻译）

将 Calvin 注释 PDF 转换为 Markdown 文件，完整保留结构与格式，发布为网站英文版书卷；并可将英文 MD 翻译成中文发布为中文版。

支持三种 PDF 格式——**开始前必须先诊断**（见"PDF 格式快速诊断"节）：
- **Ages Digital Library 双语格式**（如希伯来书、腓立比书）：英文+拉丁文两列，经文输出为 HTML 双语表格
- **CCEL 单列格式**（如使徒行传）：仅英文，经文为独立 block
- **CCEL 平行福音格式**（如福音书和谐马太卷二）：2-3 列平行福音经文，列数随章节不同，需动态检测

## 用法

```
/pdf-to-structured-txt <pdf路径> <输出md路径> [book_id] [book_name_en]
```

例如：
```
/pdf-to-structured-txt /Users/yanpeifa/Documents/论文/calvin_filibi.pdf ocr_output/phil/calvin_filibi.md philippians-en "Calvin on Philippians"
```

若不提供 `book_id`，只执行 PDF→Markdown 提取，不发布到网站。

## 命名规范

`ocr_output/` 下的子目录和 MD 文件名**必须使用英文，禁止使用拼音**。

| 书卷 | 正确命名 | 错误示例 |
|------|---------|---------|
| 腓立比书 | `ocr_output/phil/calvin_phil.md` | `filibishu/` |
| 哥林多前书卷一 | `ocr_output/1cor-vol1/calvin_1cor-vol1.md` | `gelinduo1/` |
| 哥林多前书卷二 | `ocr_output/1cor-vol2/calvin_1cor-vol2.md` | — |
| 哥林多后书 | `ocr_output/2cor/calvin_2cor.md` | — |

规则：
- 目录名用书卷缩写（`phil`、`1cor`、`acts` 等），多卷用 `-vol1`、`-vol2` 区分
- MD 文件名：`calvin_<目录名>.md`
- `book_id`（发布用）：`<书卷英文>-en`（如 `1corinthians-en`、`philippians-en`）

## 还原 PDF 的通用原则

目标是让网页与 PDF 原文在结构和内容上完全一致。以下原则适用于所有 Ages Digital Library Calvin 注释书卷。

### 0. 最高原则：以 PDF 原文为唯一依据，禁止猜测

**任何格式问题（对齐方式、分行、缩进、字体风格等）必须打开 PDF 原文核实，再做修改。**

- 用户指出某处有误 → 先读 PDF 对应页，确认正确格式，再改
- 不得根据"惯例""猜测""推断"决定格式
- 不得因用户否定 A 方案就自动切换到 B 方案——B 方案同样需要 PDF 核实
- 若不知道 PDF 路径，询问用户，不要自行假设

**反例（错误做法）**：用户说右对齐不对 → 未看 PDF 就改成居中 → 结果 PDF 是左缩进，改了两次都错。

### 1. 元素识别与输出对照

| PDF 元素 | 识别依据 | 网页输出 |
|---------|---------|---------|
| 一级标题 | 字体 ≥18pt | `# Title` |
| 二级标题 | 字体 14–17pt | `## Title` |
| 正文段落 | 左边距 ≤35px，且非居中 | 普通段落 |
| **居中段落** | **块中心 x ≈ 页面中心（误差 <10% 页宽）** | **`<p style="text-align:center">text</p>`** |
| 缩进引文 | 左边距 >35px，且非居中 | `> text`（blockquote） |
| 红色斜体行内引文 | 红色字体 | `<span style="color:#800000">*text*</span>` |
| 行内脚注序号 | 上标小字 | `[^f35]` |
| 圣经经文表格 | 双列区域，含表头 | HTML table（见下） |
| 脚注定义 | 脚注区，`FtN` 开头 | `[^ftn]: text` |
| 分页标记 | 页面边界 | `<!-- PAGE N -->` |

**对齐检测是关键**：左边距 > INDENT_X 的块不一定是缩进引文——居中文本和右对齐文本同样有较大的左边距。必须通过坐标几何而非左边距单项判断对齐方式。

#### 问题根源

PDF 里一个居中单词（如 "ON"）的 bbox 约为 `[296, y0, 316, y1]`，左边距 296 远大于 INDENT_X=35，若只看左边距会误判为缩进引文（blockquote）。正确做法是看块的**水平中心**是否与**页面中心**吻合。

#### 三步对齐分类（比单一阈值更通用）

```python
# ── Step 0: 从文档自动校准正文左边距（不硬编码 35）────────────────────────────
from collections import Counter

def calibrate_body_margin(doc, max_x=200):
    """采样所有普通块的左边距，众数即为正文左边距。
    返回: INDENT_X（正文左边距+10px缓冲，比此大视为非正文）"""
    xs = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0: continue
            x = round(b["bbox"][0])
            if x < max_x:
                xs.append(x)
    if not xs:
        return 35
    return Counter(xs).most_common(1)[0][0] + 10

def calibrate_right_margin(doc, max_x=200):
    """采样正文块的右边距，众数即为页面文本右边距（用于检测右对齐）。"""
    xs = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0: continue
            if b["bbox"][0] < max_x:
                xs.append(round(b["bbox"][2]))
    if not xs:
        return None
    return Counter(xs).most_common(1)[0][0]

INDENT_X   = calibrate_body_margin(doc)
BODY_RIGHT = calibrate_right_margin(doc)

# ── Step 1: 三向对齐判断函数 ──────────────────────────────────────────────────
def classify_alignment(block, page_w, body_right, tol_px=50):
    """
    对左边距 > INDENT_X 的块做三向分类：
      CENTERED   — 块水平中心 ≈ 页面中心（误差 < tol_px）
      RIGHT      — 块右边 ≈ 正文右边距（误差 < tol_px//2）
      BLOCKQUOTE — 其他（真正的缩进引文）

    tol_px=50：固定像素容差，比百分比容差更稳定——不随页面宽度放大
    （10% 容差在 900px 宽页上允许 ±90px，容易误判）。
    """
    bx0, bx1 = block["bbox"][0], block["bbox"][2]
    block_cx  = (bx0 + bx1) / 2

    if abs(block_cx - page_w / 2) < tol_px:
        return "CENTERED"
    if body_right and abs(bx1 - body_right) < tol_px // 2:
        return "RIGHT"
    return "BLOCKQUOTE"

# ── Stage 1 中使用（替换原来的 btype 判断）────────────────────────────────────
if block["bbox"][0] > INDENT_X:
    align = classify_alignment(block, page_w, BODY_RIGHT)
    if align == "CENTERED":
        is_italic = all(
            bool(s["flags"] & 2)
            for line in block["lines"] for s in line["spans"] if s["text"].strip()
        )
        items.append({"type": "CENTERED", "text": all_text, "italic": is_italic})
    elif align == "RIGHT":
        items.append({"type": "RIGHT", "text": all_text})
    else:
        items.append({"type": "BLOCKQUOTE", "text": all_text})
else:
    items.append({"type": "BODY", "text": all_text})
```

渲染时（Stage 2）：
```python
elif t == "CENTERED":
    text = format_inline(item['text'])
    text = convert_ages_greek(text)
    style = "text-align:center; font-style:italic" if item.get("italic") else "text-align:center"
    md_lines.append(f'\n<p style="{style}">{text}</p>\n')
elif t == "RIGHT":
    text = format_inline(item['text'])
    text = convert_ages_greek(text)
    md_lines.append(f'\n<p style="text-align:right; font-style:italic">{text}</p>\n')
```

#### 为何用像素容差而不是百分比容差

| 方案 | 问题 |
|------|------|
| `page_w * 0.10`（10%） | 600px 页 → ±60px 还好；900px 宽页 → ±90px，误判率高 |
| `tol_px = 50`（固定像素） | 不随页面宽度变化，在各种 PDF 尺寸下都稳定 |

如仍有误判，调小 `tol_px`（如 35px）而无需改动其他逻辑。

### 2. 圣经经文表格：必须还原跨列标题

PDF 中表格标题行（如 `PHILIPPIANS 2:5-11`）横跨英文和拉丁文两列。输出**必须**用 HTML 实现 `colspan=2`，不得用 Markdown `| title | |`（后者无法合并单元格）：

```html
<table class="calvin-scripture">
<thead><tr><th colspan="2" style="text-align:center">PHILIPPIANS 2:5-11</th></tr></thead>
<!-- text-align 从 PDF block x 坐标检测：x > 页宽20% → center，否则 left -->
<tbody>
<tr><td>5 . Let this mind...</td><td>5 . Hoc enim sentiatur...</td></tr>
</tbody>
</table>
```

Ages Digital Library PDF 中表格头有两种编码形式，均需识别：
- **有引用代码**：`<524104>PHILIPPIANS 1:1-6`，以 `<NNNNNN>` 开头，用 `re.match` 检测
- **无引用代码**：`PHILIPPIANS 2:1-4`，字体 ≥14pt、首行 x>80（居中），用 `is_plain_scripture_header_block()` 检测

### 3. 希腊文：必须转换为 Unicode

Ages Digital Library 用私有字体编码希腊文，PyMuPDF 提取到的是 ASCII 转写（如 `ejmo>i`）而非 Unicode（`ἐμοί`）。输出到 MD 前**必须**调用 `convert_ages_greek()` 转换，否则网页显示乱码。

转写规则：辅音直接映射；`j`=平气符；`>`/`<`/`~`=锐/重/抑扬音；`|`=iota 下标；`v`=词尾 sigma；双元音中的声调符属于第二个元音（如 `ejmo>i` → `ἐμοί`）。

检测 HTML 标签时**必须**用 `<[a-zA-Z/!][^>]*>`，不得用 `<[^>]+>`——后者会把 `to< ... <span>` 中的希腊文和标签一起误吞。

### 4. 跨页段落：必须合并

PDF 段落在页面边界或 block 边界断裂时，续行 block 的**首行不带段落缩进**（indent = 0），而新段落首行**有缩进**（indent ≥ INDENT_LOW）。Stage 1.5 以此纯结构信号判断是否合并，不看段落文字内容。

### 为什么不能用内容判断

| 内容规则（错误） | 会导致的问题 |
|-----------------|-------------|
| 下段首字小写 → 合并 | 合法续句首字大写（如专有名词、斜体词）无法合并 |
| 前段逗号结尾 + 大写 → 合并（`cur_ends_comma`）| Calvin 引文独立段落如 "asks," + "Who hath..." 被错误合并 |
| 只看标点/大小写 | 对任何新 PDF 都是猜测，只能适配特定内容 |

### 正确实现：纯结构化

每个 BODY item 必须记录其**首行 indent**（第一个有文字的行的 x0 − block_x0）。Stage 1.5 根据 indent 决定合并：

```python
# 构建 BODY item 时记录 indent
first_indent = 0
for line in b['lines']:
    ls = [s for s in line['spans'] if s['text'].strip()]
    if ls:
        first_indent = round(ls[0]['bbox'][0] - b['bbox'][0])
        break
items.append({'type': 'BODY', 'text': text, 'indent': first_indent})
```

```python
# Stage 1.5：纯结构化合并
# 结构信号：nxt_indent < INDENT_LOW → 无段落首行缩进 → 续行 block
# 安全兜底：前段未结句（防止段首无缩进的新章节首段被误合并）
# 特判：前段末有未闭合括号（如 "(2 Corinthians"）→ 强制合并，无论 nxt_indent
PARA_INDENT_LOW = 10  # 与 split_block_by_paragraph_indent 保持一致

idx = 0
while idx < len(all_items):
    if all_items[idx]['type'] == 'BODY':
        j = idx + 1
        while j < len(all_items) and all_items[j]['type'] == 'PAGE':
            j += 1
        if j < len(all_items) and all_items[j]['type'] == 'BODY':
            cur = all_items[idx]['text']
            nxt = all_items[j]['text']
            nxt_indent = all_items[j].get('indent', 0)
            cur_has_open_paren = bool(re.search(r'\([^)]*$', cur.rstrip()))
            if (nxt_indent < PARA_INDENT_LOW and not is_sentence_end(cur)) \
                    or (cur_has_open_paren and not is_sentence_end(cur)):
                all_items[idx]['text'] = cur.rstrip() + ' ' + nxt.lstrip()
                all_items[idx]['indent'] = min(
                    all_items[idx].get('indent', 0),
                    all_items[j].get('indent', 0))
                del all_items[j]
                continue
    idx += 1
```

⚠️ **严禁使用 `first_char`（首字大小写）或 `cur_ends_comma`（逗号结尾）作为合并条件**——这是内容判断，不是结构判断，已知会导致 Calvin 注释中圣经引文段落被错误合并。

**已知坑：括号内圣经引用跨页断裂**

**症状**：正文中有 `(2 Corinthians` 结尾的段落，下一页开头是 `6:14.)` 单独成一行且被居中（因为 indent > 20pt）。

**根因**：PDF 恰好在 `(书名` 和 `章:节)` 之间换页，导致 "6:14.)" 作为独立 BODY item 被 render 阶段加上居中 IAL。Stage 1.5 原本的 `nxt_indent < PARA_INDENT_LOW` 条件失效（indent > 20pt）。

**修复**：`cur_has_open_paren = bool(re.search(r'\([^)]*$', cur.rstrip()))` — 只要当前行末有未闭合括号且未结句，就无条件合并，同时取两者 indent 的较小值（保持较短的那段不居中）。

### 4.5 同页多节注释合并在同一 block：必须按节分割

**症状**：第 N 节注释的末尾句和第 N+1 节注释的开头（`**N+1.** *经文引用*...`）连在一起，没有段落分隔。

**原因**：PyMuPDF 有时把同一页上多个连续 commentary 段落（包含不同节号）提取为一个巨型 block。所有行都是相同字号（如 12pt），`split_block_by_size` 不会分割，导致多节注释输出为一个 body 段落。

**识别特征**：节号标记 `N.` 在 block 内部某行行首以 **bold 非斜体** 出现（标志新节开始），而非 block 第一行。

**修复**：在 block 分类前加一道 `split_block_by_verse_number` 分割——遇到行首 bold `N.` 就切割新块。两个 guard 条件防止误切圣经表格经节块：

```python
def block_has_right_col(block, table_split_x):
    """有右列内容（含拉丁文）的块，不是纯 commentary。"""
    for line in block["lines"]:
        spans = [s for s in line["spans"] if s["text"].strip()]
        if spans and spans[0]["bbox"][0] >= table_split_x:
            return True
    return False

def block_is_full_width(block, body_right, min_right=400):
    """全宽 commentary 块：无右列内容 且 右边距足够宽。"""
    return (not block_has_right_col(block, TABLE_SPLIT_X)
            and block["bbox"][2] > min_right)

def split_block_by_verse_number(block):
    """把同一 block 内不同节的注释拆成独立块。
    只对全宽 commentary 块生效；含右列（拉丁文）或窄块跳过。"""
    if block_has_right_col(block, TABLE_SPLIT_X):
        return [block]
    if not block_is_full_width(block, BODY_RIGHT):
        return [block]
    groups, current = [], []
    for i, line in enumerate(block["lines"]):
        spans = [s for s in line["spans"] if s["text"].strip()]
        if i > 0 and spans:
            s = spans[0]
            if (bool(s["flags"] & 16)          # bold
                    and not bool(s["flags"] & 2)   # not italic
                    and re.match(r"^\d+\.$", s["text"].strip())):
                if current:
                    groups.append(_rebuild_block(block, current))
                current = [line]
                continue
        current.append(line)
    if current:
        groups.append(_rebuild_block(block, current))
    return groups if len(groups) > 1 else [block]

def _rebuild_block(orig, lines):
    y0 = lines[0]["bbox"][1]; y1 = lines[-1]["bbox"][3]
    return {**orig, "bbox": [orig["bbox"][0], y0, orig["bbox"][2], y1], "lines": lines}
```

在 Stage 1 block 处理循环中，将每个 block 先过一遍分割：

```python
# 把每个 block 先按节号分割，再按行类型分类
for sub in split_block_by_size(b):
    for sub2 in split_block_by_verse_number(sub):
        body_blocks.extend(split_block_by_paragraph_indent(sub2))
```

### 4.5b Ages PDF 段落首行缩进：同一 block 内多段合并，必须按缩进拆分

**症状**：原文中分段的多个连续段落（如注释一节经文的数个段落）在页面上合并为一个整段，无换行间距。

**原因**：Ages Digital Library PDF 的注释体正文，同一节（或同一页）内的多个段落往往被 PyMuPDF 提取为**同一个 block**。段落边界在 PDF 中由**首行缩进**标识——段首行 x0 = block_x0 + ~18pt，其余行 x0 = block_x0。`split_block_by_size` 和 `split_block_by_verse_number` 均不感知缩进，因此无法拆分这类合并。

**识别特征**：对某个全宽 body block，若某行（非第一行）第一个 span 的 x0 > block_x0 + 10pt 且 ≤ block_x0 + 60pt，则该行为一个新段落的开始；字号须 ≥ 11pt。大于 60pt 的深缩进行是居中引文（如圣经引用），**第一次出现**时也触发分段（后续深缩进行合为一个引文块，不再分）。注意：render 阶段居中阈值为 **>20pt**（见 4.5.1 节），但 split 阶段用 `INDENT_HIGH=60` 区分正文段落缩进 vs 引文行，两者独立。

**修复**：`split_block_by_paragraph_indent`，在 `split_block_by_verse_number` 之后应用：

```python
INDENT_LOW, INDENT_HIGH = 10, 60   # pt
BODY_SIZE_MIN = 11.0               # body text ≥12pt; footnote text ~9pt

def split_block_by_paragraph_indent(block):
    if block_has_right_col(block) or not block_is_full_width(block):
        return [block]
    block_x0 = block['bbox'][0]
    groups, current_lines = [], []
    first_nonempty_seen = False
    prev_was_deep = False   # 上一行是否为深缩进行（>INDENT_HIGH）
    for line in block['lines']:
        spans = [s for s in line['spans'] if s['text'].strip()]
        if not spans:
            current_lines.append(line); continue
        x0 = spans[0]['bbox'][0]
        size = spans[0]['size']
        indent = x0 - block_x0
        is_deep = indent > INDENT_HIGH and size >= BODY_SIZE_MIN
        first_char = spans[0]['text'].lstrip()[:1]
        is_para_start = (
            first_nonempty_seen
            and size >= BODY_SIZE_MIN
            and (
                (INDENT_LOW <= indent <= INDENT_HIGH)   # 普通段落首行缩进
                or (is_deep and not prev_was_deep       # 深缩进引文第一行（触发一次分段）
                    and not first_char.islower())        # 小写开头=换行续行，不切分
            )
        )
        if is_para_start and current_lines:
            groups.append(_make_sub_block(block, current_lines))
            current_lines = []
        current_lines.append(line)
        first_nonempty_seen = True
        prev_was_deep = is_deep
    if current_lines:
        groups.append(_make_sub_block(block, current_lines))
    return groups if len(groups) > 1 else [block]

# 在 block 处理循环中：
for sub in split_block_by_size(b):
    for sub2 in split_block_by_verse_number(sub):
        body_blocks.extend(split_block_by_paragraph_indent(sub2))
```

**注意**：该函数对 `block_has_right_col`（经文表格）和 narrow blocks 有 guard；字号检查过滤掉脚注定义块（9pt）。段落续行跨页时，由 Stage 1.5 合并（末句未结束 + 下句小写开头）。

缩进引文块独立成段后，**必须在 Markdown 渲染时加居中 IAL**，否则会左对齐，与 PDF 不符：

```python
# Render 阶段：BODY item indent > 20 → 居中引文
# 阈值说明：正文段落缩进约18pt，所有经文/拉丁文引用缩进均 >20pt
elif t == 'BODY':
    text = item['text']
    # ... 转义处理 ...
    md_lines.append(f'\n{text}\n')
    if item.get('indent', 0) > 20:
        md_lines.append('{: style="text-align: center"}\n')
```

**阈值历史**：原为 `> 60`（仅深缩进），后发现大量中度缩进经文引用（如 Matthew 18:18, John 15:16 等，缩进约 46pt）未居中，遂统一降至 `> 20`。经全书验证，正文段落缩进不超过 18pt，所有 >20pt 项均为引文。

Kramdown 会将 `{: style="text-align: center"}` 作为该段落的行内属性，渲染为 `<p style="text-align: center">...</p>`，脚注引用仍可正常处理。

### 4.6 表格 `<td>` 内脚注引用：必须转为 HTML 上标

**症状**：圣经经文表格某列出现字面文字 `[^44]`，而非上标链接。

**原因**：Kramdown 不处理 `<td>...</td>` 等 HTML 块内的 Markdown 语法，`[^N]` 不会被渲染为脚注上标。

**修复**：在 `build_table` 写入 `<td>` 内容前，`_fnref_to_html` 必须同时转换脚注引用和所有 Markdown 行内格式：

```python
def _fnref_to_html(text):
    """把 Markdown 行内标记转为 HTML，用于 <td> 内容。
    Kramdown 不处理 HTML 块内的 Markdown，必须在提取阶段转换。"""
    # 脚注引用：[^N] → <sup>
    text = re.sub(r'\[\^(\d+)\]',
                  lambda m: f'<sup><a href="#fn:{m.group(1)}" id="fnref:{m.group(1)}">{m.group(1)}</a></sup>',
                  text)
    # 粗斜体：***text*** → <em><strong>text</strong></em>
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<em><strong>\1</strong></em>', text)
    # 粗体：**text** → <strong>text</strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 斜体：*text* → <em>text</em>
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    return text

def build_table(header_text, rows):
    ...
    for en, la in rows:
        en_esc = _fnref_to_html(en.replace('|', '&#124;'))
        la_esc = _fnref_to_html(la.replace('|', '&#124;'))
        lines.append(f'<tr><td>{en_esc}</td><td>{la_esc}</td></tr>')
```

**注意**：漏掉斜体/粗体转换时，`*was*` 会在网页上显示为字面文字 `*was*`，而非斜体。

### 4.9 `spans_to_text`：不得包含跨 span 的后处理正则

**症状**：某些段落中斜体标记错位，如 `*By the will of God* While...to* acknowledge*`（`God*` 后的 `*` 消失，`to` 后多了 `*`），整段斜体格式混乱。

**原因**：原始 `spans_to_text` 包含一条"修补"正则 `re.sub(r'\*([^*]+?) \*', r'*\1* ', result)`，用来把 `*text *`（尾部空格在 `*` 之内）修正为 `*text* `。但该正则没有感知 span 边界，在多个斜体 span 拼接后的字符串上全局匹配，会把 `*italic1* plaintext *italic2*` 中的第一个 `*` 和第二个 `*` 之间的整段文字当作一个 match，产生错误替换。

**修复**：`format_span` 已经正确把空白移到标记外，`*text *` 不再出现，该正则已无用且有害，**直接删除**：

```python
def spans_to_text(spans):
    parts = []
    for span in spans:
        part = format_span(span)
        if not part:
            continue
        if parts:
            prev = parts[-1]
            needs_space = (prev and not prev[-1].isspace()
                           and not part[0].isspace()
                           and part[0] not in '.,;:!?)\'"_-')
                           # 注意：* 不在豁免列表中。相邻 *A**B* 情形（行尾斜体+行首斜体）
                           # 必须加空格，否则 ** 被 Kramdown 解析为 bold 开始标记。
            if needs_space:
                parts.append(' ')
        parts.append(part)
    result = ''.join(parts)
    result = re.sub(r' {2,}', ' ', result)   # collapse double spaces only
    return result.strip()
```

**不要写** `re.sub(r'\*([^*]+?) \*', ...)` 或任何跨 span 边界的斜体修补正则。

### 4.8 `format_span`：斜体/加粗 span 开头的空白必须移出标记之外

**症状**：页面上某些节号段落（如 `**3.** Grace be to you and peace For an exposition...`）显示居中，且斜体格式丢失——节名引用变成普通文字并附带字面星号（`* Grace be to you and peace*`）。

**原因**：PyMuPDF 提取的斜体 span 文字往往以空格开头（如 `" Grace be to you and peace"`）。`format_span` 直接加上 `*` 生成 `* Grace be to you and peace*`，但 Kramdown 规定**开头 `*` 后紧跟空格时不开启斜体**——因此 `*` 被渲染为字面字符。同时由于 bold span（如 `**3.**`）和 italic span 紧邻，生成 `**3.*** Grace be...`，其中 `***` 与 bold+italic 标记混淆，进一步破坏解析。

最终 Kramdown 生成 `<p><strong>3.</strong>* Grace be...* ...</p>`，CSS 规则 `p:has(> strong:only-child)` 匹配该段落（文本节点不算 element child），使该段居中。

**修复**：在 `format_span` 中，为所有斜体/加粗 span 把开头和结尾的空白移到标记之外：

```python
def format_span(span):
    t = span['text']
    if not t.strip():
        return t
    if is_footnote_ref(span):
        return f'[^{t.strip()}]'
    # Move leading/trailing whitespace outside emphasis markers so Kramdown
    # parses them correctly.  E.g. " Grace be" → " *Grace be*" not "* Grace be*"
    # (Kramdown treats "* text*" as literal * when * is followed by whitespace.)
    if is_bold(span) and is_italic(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}***{t.strip()}***{tail}'
    if is_bold(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}**{t.strip()}**{tail}'
    if is_italic(span):
        lead = t[:len(t) - len(t.lstrip())]
        tail = t[len(t.rstrip()):]
        return f'{lead}*{t.strip()}*{tail}'
    return t
```

**checklist 补充**：`grep -n '\*\* \*' output.md`（注意 `** *` = bold 结束后空格再 italic 开始，这是正确的）；而 `grep -n '\*\*\*[^ *]' output.md` 应只匹配真正的 bold+italic 文字，不应出现节号。

### 4.7 段首孤立脚注引用：必须移到前段末尾（Stage 1.6）

**症状**：正文段落开头出现超大上标数字（如 "⁹ He persuades them..."），该数字实为脚注引用，不属于这段文字的开头。

**原因**：PyMuPDF 有时将前一段末尾的脚注上标（如 `45`）提取到下一个 block 的开头。提取后该 block 的文字形如 `[^45] He persuades them...`，其中 `[^45]` 是 Kramdown 渲染时显示的大上标。

**修复**：Stage 1.6 将段首孤立脚注引用（`[^N] 正文...`）移到前一段末尾：

**两种情形**：
- **Case A**：`[^N] text...` — 脚注引用在段首，后面有正文 → 把 `[^N]` 移到前段末，本段保留剩余文字
- **Case B**：`[^N]` 独占整段（整个 BODY item 只有一个脚注引用）→ 把 `[^N]` 移到前段末，**删除本段**

```python
# Stage 1.6：把段首孤立脚注引用移到前段末尾（含仅含引用的整段情形）
idx = 0
while idx < len(all_items):
    if all_items[idx]['type'] == 'BODY':
        text = all_items[idx]['text']
        m_prefix = re.match(r'^(\[\^\d+\])\s+', text)          # Case A
        m_solo   = re.match(r'^(\[\^\d+\])$', text.strip())     # Case B
        if m_prefix or m_solo:
            fn_ref = (m_prefix or m_solo).group(1)
            rest   = text[m_prefix.end():] if m_prefix else ''
            prev_idx = idx - 1
            while prev_idx >= 0 and all_items[prev_idx]['type'] == 'PAGE':
                prev_idx -= 1
            if prev_idx >= 0 and all_items[prev_idx]['type'] == 'BODY':
                all_items[prev_idx]['text'] = all_items[prev_idx]['text'].rstrip() + fn_ref
                if rest:
                    all_items[idx]['text'] = rest
                else:
                    del all_items[idx]   # Case B：删除空段
                    continue
    idx += 1
```

### 5. 脚注区 `##` 标记：先用作边界，再过滤

PDF 脚注区按章节分组，每组开头有 `##` 标记（如 `## CHAPTER 1`、`## THE ARGUMENT`、`## SERMON 5` 等——**具体词语因书而异**）。这些标记有**双重作用**：

**① 划定 fn_sections 边界（Step 1 必做）**
`## CHAPTER N` 行标志着该行之后的脚注属于第 N 章，必须用其行号来精确设置各章的 `fn_sections`。不能将整个 fn 区当作一个整体，把所有脚注都放进同一章。

**② 发布时过滤（渲染时不输出）**
边界确定后，`##` 标记行本身不属于任何正文，渲染时过滤掉：

```python
fn = "".join(l for l in lines[fn_start:fn_end] if not re.match(r'^## ', l))
```

**注意**：正文（body）区的 `##` 标题是合法的副标题，**不**过滤。区分方式：fn 区从 `---` 分隔符之后开始，该分隔符之后的所有 `##` 均为组织标记。

### 6. Kramdown 安全输出

正文、blockquote、脚注定义中凡含以下字符，均需转义或重格式化，否则 Kramdown 误判：
- `|` → `\|`（防止被识别为表格列分隔符）
- **行首 `N. ` → `**N.**`（Calvin 注释节号，必须 bold）**

圣经经文表格已改用 HTML，不受 Kramdown 影响，无需转义。

#### 行首节号 bold 是通用强制约束

Kramdown 把段落行首的 `N. text`（数字+句号+空格）一律解析为**有序列表第 N 项**，渲染为缩进列表，CSS 计数器重置后序号显示错误（如 "1." 而非 "17."）。

**对于 Calvin 注释，`**N.**` 而非 `N\.`**：两种写法都能阻止 Kramdown 列表解析，但 `**N.**`（bold）是节号的正确语义格式，在页面上渲染为绿色节号锚点（via `calvin-en.html` CSS），`N\.` 只是普通文字。

| 提取路径 | 节号如何出现 | 落实机制 |
|---------|------------|---------|
| Ages / CCEL 单列（富文本） | `extract_block_rich` 在提取时输出 `**N.**` | `split_rich_by_verse` 处理段落内嵌节号 |
| CCEL 平行福音等（纯文本） | `get_block_text` 输出裸 `N.` | 发布脚本必须同时包含 `split_verse_commentary`（处理段落中间）和 `bold_verse_starts`（处理 block 开头） |

**⚠️ 这是跨格式通用约束**：无论哪种提取路径，发布后 MD 文件中绝不应出现以裸 `N. [大写]` 开头的段落 block。

## 执行步骤

1. 从用户消息解析参数
2. 编写 PDF 提取脚本时，**必须逐条对照本 skill 的提取脚本模板**，确认以下功能全部实现，不得遗漏：
   - 同页多段合并（首行缩进）：`split_block_by_paragraph_indent`（见第4.5b节），在 `split_block_by_verse_number` 之后应用，把同一 block 内因首行缩进标识的多个段落拆分为独立块；guard 排除经文表格和脚注块
   - 同页多节注释合并：`split_block_by_verse_number`（见第4.5节），在 Stage 1 block 循环前对每个 block 执行，把 bold `N.` 行首的节分割为独立块；两个 guard 防止误切经文表格
   - 表格 `<td>` 内脚注转 HTML：`build_table` 中调用 `_fnref_to_html()` 把 `[^N]` 转 `<sup>` 标签（见第4.6节），否则 Kramdown 不处理 HTML 块内的 Markdown
   - Stage 1.6：段首孤立脚注引用移到前段末尾（见第4.7节），防止大上标出现在段落开头
   - `format_span` 空白外移：bold/italic/bold+italic span 开头尾空白必须移到标记之外（见第4.8节），否则 Kramdown 无法解析斜体，节号段落被 CSS 误判为居中
   - Stage 1.5：段落碎片合并——**纯结构化**：每个 BODY item 必须记录 `indent`（首行缩进），合并条件：`nxt_indent < PARA_INDENT_LOW AND not is_sentence_end(cur)`。**严禁使用 `first_char`、`cur_ends_comma` 等内容判断**（见第4节）
   - 跨页表格：`pending_header` 机制同时处理**两种情形**：A) 表头在页底无任何 verse → carry 裸 header；B) 部分 verse 在当前页、页面耗尽 → carry `{'header':…,'verses':[…]}` dict；用 `hit_commentary` 标志区分两种退出原因（见"已知坑"）
   - 希腊文转换：`convert_ages_greek()` 在所有输出路径上均被调用
   - 脚注标签标准化：`ft` 前缀统一去掉
   - Kramdown 安全：`|` 转义；**行首节号 bold**——富文本路径由 `extract_block_rich` 保证，纯文本路径发布脚本必须含 `split_verse_commentary` + `bold_verse_starts`（见第6节）
3. 运行提取脚本
4. 运行**提取质检 Checklist**（见下方），逐项排查
5. 若提供了 `book_id`，继续执行**发布到网站**步骤
6. 发布后再运行**发布质检 Checklist**，逐项排查

---

## 质检 Checklist

每次提取/发布完成后必须逐项过一遍，不得跳过。

### 提取质检（PDF → MD）

- [ ] **表格数量合理**：`output.count('calvin-scripture')` 与 PDF 中圣经经文表格数量一致；若为 0 或明显偏少，说明表格头未被识别（检查两种格式的检测逻辑）
- [ ] **无空 tbody 表格**：所有表格必须有至少一行内容。验证：
  ```python
  import re
  empties = [m.group() for m in re.finditer(r'<table class="calvin-scripture">.*?</table>', open('output.md').read(), re.DOTALL) if '<tr><td>' not in m.group()]
  print(f'空表格数: {len(empties)}')  # 必须为 0
  ```
  若有空表格：见"已知坑"情形 A（表头在页底，verse 完全在下页）。
- [ ] **无截断表格**：检查表格头声明的经文范围与实际行数是否一致——若表头写 `3:10-15` 但 tbody 只有 3 行（verse 10-12），说明 verse 13-15 在下一页被当作 body 处理了。见"已知坑"情形 B（verse 跨页，页面耗尽时误 emit 不完整表格）。验证：
  ```bash
  # 找出正文中形如 "13. Every man..." 等本应属于表格的 verse body 段落
  grep -n '^\*\*[0-9]\+\.\*\*' output.md | head -20
  ```
  有输出说明这些 verse 号被渲染成了 body 加粗段落而非表格行，需检查 `hit_commentary` 逻辑。
- [ ] **表格标题跨列**：所有表格均为 `<th colspan="2">`，无 `| **BOOK X:Y** | |` 形式的 Markdown 表格残留
- [ ] **希腊文已转换**：MD 文件中无 `>[a-z]` 或 `[a-z]<` 形式的 Ages 转写残留（用 `grep -P '[a-z][><~][a-z]'` 验证）；若有，检查 `convert_ages_greek()` 是否被调用
- [ ] **脚注数量合理**：`output.count('[^f')` 与 PDF 脚注数量大致对应；若为 0，说明脚注区未被检测到（注：计数用 `[^f` 而非 `[^ft`，因脚本已将 ft→f 标准化）
- [ ] **脚注引用与定义名称一致**：引用标签与定义标签必须完全匹配，否则 Kramdown 渲染为字面文字。验证：
  ```bash
  # 提取正文中所有引用标签（[^fN]）
  grep -oP '\[\^f\d+\]' output.md | sort -u > /tmp/refs.txt
  # 提取脚注定义标签（[^fN]:）
  grep -oP '\[\^f\d+\](?=:)' output.md | sort -u > /tmp/defs.txt
  # 找不匹配的项（有引用但无定义）
  comm -23 /tmp/refs.txt /tmp/defs.txt
  ```
  输出非空说明有脚注标签不匹配，需检查是否还有 `ft` 前缀未被标准化（脚注区标签 `FtN`/`ftN` → `fN`，正文引用 `[^fN]`，两者必须一致）
- [ ] **表格内无字面脚注引用和字面星号**：`<td>` 内不应有 `[^N]` 字面文字（应已转为 `<sup>`），也不应有 `*word*` / `**word**` 字面文字（应已转为 `<em>`/`<strong>`）；若有则说明 `_fnref_to_html()` 未完整实现斜体/粗体转换。快速验证：`grep -oP '<td>[^<]*\*[^<]*</td>' output.md`，输出非空则需修复。
- [ ] **无孤立脚注引用段**：两项都需通过：
  - `grep -P '^\[\^\d+\] [A-Z]' output.md` 应无输出（Case A：段首脚注+正文，Stage 1.6 未处理）
  - `python3 -c "import re,sys; s=open('output.md').read(); bad=re.findall(r'\n\n(\[\^\^?\d+\])\n\n', s); print(bad)"` 应输出 `[]`（Case B：整段只有脚注引用，需删除并移到前段）
- [ ] **节号段落斜体格式正确**：`grep -n '^\*\*[0-9]\+\.\*\*\*' output.md` 应无输出（`**N.***` 为错误格式，说明 `format_span` 未移出空白）；正确格式应为 `**N.** *经文引用*`（bold 后有空格再 italic）
- [ ] **段落数量合理**：body 段落数量应与 PDF 页数成比例（每页平均 2-4 段为正常）。若整本书只有 400 段而 PDF 有 290 页，说明 `split_block_by_paragraph_indent` 未执行——每段实际是多段合并。
- [ ] **节号注释未合并**：检查各章中每节注释（`**N.**`）是否都独立成段，无两节注释连在同一段落的情况。快速验证：
  ```python
  import re
  content = open('output.md').read()
  # 找到段落内含有两个及以上节号标记的（说明未分割）
  bad = [m.group()[:80] for m in re.finditer(r'\*\*\d+\.\*\*.*?\*\*\d+\.\*\*', content, re.DOTALL)
         if '\n\n' not in m.group()]
  print(f'未分割节段: {len(bad)}')
  for b in bad[:3]: print(b)
  ```
- [ ] **跨页段落已合并**：检查若干页面边界处（`<!-- PAGE N -->`），前后段落是否被错误断开
- [ ] **无乱入 H2 表格头**：MD 中无 `## PHILIPPIANS` 或 `## [书卷名]` 形式的行（说明表格头被误识别为 H2）
- [ ] **无行内引用代码残留**：MD 中无 `[<NNNNNN>]` 或 `(<NNNNNN>` 形式（用 `grep '<[0-9]' output.md` 验证）
- [ ] **对齐文本对照 PDF 逐条核实**：`grep "^> " output.md` 列出所有 blockquote，打开 PDF 对应页确认每条是否真为左缩进；同理检查所有 `<p style="text-align:center">` 和 `<p style="text-align:right">` 是否与 PDF 一致。**不得凭推断判断，必须看 PDF 原文。**

### 已知坑：跨页经文表格（两种情形，必须同时处理）

**共同症状**：表格不完整或为空，紧随其后出现以 `**N.**` 开头的正文段落（实为被误判为 body 的 verse 行）。

#### 情形 A：表头在页底，verse 行完全在下一页（空 tbody）

当前页 verse_blocks 为空 → 表格 `<tbody></tbody>` 为空；下一页 verse 行无表头归属 → 被当作 body。

#### 情形 B：verse 行跨越页边界（部分 verse 在当前页，部分在下一页）

verse 收集循环因**页面耗尽**（`j >= len(body_blocks)`）退出，不是因为遇到 commentary 块。当前页已收集部分 verse（如 10-12 节），旧代码直接 emit 不完整表格；下一页剩余 verse（13-15 节）无 `pending_header` 接收 → 变成 body 段落。

**两种情形的区分方式**：用 `hit_commentary` 标志区分循环是否因遇到 commentary 块而中断：

```python
# 情形 B 的漏洞：只判断 verse_blocks 是否为空，忽略了"页面耗尽"的情况
# ❌ 错误写法（只处理情形 A）：
if verse_blocks:
    emit_table(header, verse_blocks)   # 情形 B：部分 verse 被 emit，剩余 verse 无处归属
else:
    pending_header_out = header_block  # 仅当 verse_blocks 为空才 carry
```

**修复**：用 `hit_commentary` 标志区分两种退出原因，`pending_header` 支持携带部分 verse 块：

```python
# ✅ 正确写法（同时处理情形 A 和 B）

# process_page 中的表头处理：
elif is_table_header(b):
    header_block = b
    verse_blocks = []
    j = i + 1
    hit_commentary = False
    while j < len(body_blocks):
        nb = body_blocks[j]
        if is_table_header(nb) or is_h1(nb) or is_h2(nb):
            hit_commentary = True; break
        if block_is_full_width(nb):
            hit_commentary = True; break
        verse_blocks.append(nb); j += 1
    # hit_commentary=False 说明 j >= len(body_blocks)（页面耗尽）
    if not hit_commentary and not verse_blocks:
        pending_header_out = header_block                          # 情形 A
    elif not hit_commentary and verse_blocks:
        pending_header_out = {'header': header_block, 'verses': verse_blocks}  # 情形 B
    elif verse_blocks:
        table_html = extract_scripture_section(header_block, verse_blocks)
        items.append({'type': 'TABLE', 'html': table_html})        # 正常完整表格
    i = j

# process_page 开头处理跨页传入的 pending_header（同时兼容 A/B 两种情形）：
if pending_header is not None:
    # 区分 pending_header 是裸块（情形A）还是含部分 verse 的 dict（情形B）
    # 注意：PyMuPDF 块本身也是 dict，必须用 'header' key 来判断，不能用 isinstance
    if isinstance(pending_header, dict) and 'header' in pending_header:
        carry_header = pending_header['header']
        prev_verses  = pending_header['verses']
    else:
        carry_header = pending_header
        prev_verses  = []
    new_verses = []
    for b in body_blocks:
        if is_table_header(b) or is_h1(b) or is_h2(b) or block_is_full_width(b):
            break
        new_verses.append(b)
    table_html = extract_scripture_section(carry_header, prev_verses + new_verses)
    body_blocks = body_blocks[len(new_verses):]
    carried_table = {'type': 'TABLE', 'html': table_html}
else:
    carried_table = None

# 主循环
pending_header = None
for page_num in range(...):
    items, fn_defs, pending_header = process_page(page, page_num, pending_header)
```

### 发布质检（MD → 网站）

- [ ] **`date` 字段精确到分钟**：所有发布文件的 front matter `date` 格式必须为 `YYYY-MM-DD HH:MM`，不得只写日期。`DATE` 变量必须用 `date '+%Y-%m-%d %H:%M'` 获取**真实时间**，禁止写死占位时间戳（如 `12:44`）。如果文件已发布但时间戳有误，从 git log 找到初次提交的时间：`git log --follow --diff-filter=A --format="%ci" calvin/BOOK_ID/1.md | tail -1`，取到分钟精度（如 `2026-05-26 12:45`）更新 `publish.py` 并重新运行。
- [ ] **fn 区无分节标题残留**：对每个发布文件，`---` 分隔符之后不得有任何 `##` 行。验证：
  ```bash
  awk '/^---/{found++} found>=2 && /^## /{print FILENAME": "NR": "$0}' calvin/BOOK_ID/*.md
  ```
  有输出则说明 fn 区仍有组织标记未过滤（无论是 `## CHAPTER X`、`## THE ARGUMENT` 还是其他词，fn 区的 `##` 全都是 PDF 内部标记，一律不应出现在页面上）
- [ ] **无下一章 H1 泄漏到当前章**：`grep -c "^# " calvin/BOOK_ID/*.md` 每个文件应为 0 或 1；若某文件 ≥2，说明该章 `sections` 结束边界过晚，把下一章的 H1 标题包了进来（H1 内容是什么词无关，凡出现第二个 `^# ` 即为边界错误）
- [ ] **每章首页内容完整**：对照 PDF，每章第一个 `<!-- PAGE N -->` 对应的那一整页内容（页眉、章节标题、首个经文表格）必须完整出现在该章文件中，不得有一部分留在上一章。验证：打开浏览器查看每章第一屏，与 PDF 对应页比对。
- [ ] **各章首个经文表格完整**：每章文件 front matter 之后若有经文表格，必须是 `<table class="calvin-scripture">` 开头的完整 HTML；若出现孤立的 `| N . ...` Markdown 行，说明该表格的表头和前几节行落在了上一章（上一章 `sections` 结束边界过晚）
- [ ] **脚注无跨章污染**：每章文件的脚注编号范围与该章正文引用的编号一致，无上一章或下一章的脚注混入
- [ ] **脚注序号可点击**：页面脚注列表中每条序号（`1.` `2.`...）为蓝色可点击链接，点击后跳回正文引用位置；若失效，检查 `calvin-en.html` 中 `.fn-backref-num` CSS 和对应 JS 是否存在
- [ ] **无未转义的 `|`**：正文/脚注中无裸露 `|`（圣经表格已用 HTML，不受影响）
- [ ] **无行首裸节号**（所有格式通用，机器可验证）：
  ```bash
  grep -rn "^\*\{0,1\}[0-9]\+\. [A-Z]" calvin/BOOK-en/*.md \
    | grep -v "<table\|<tr\|<td\|<th\|<thead\|<tbody"
  ```
  输出必须为空。有输出 → 某 block 以裸 `N. ` 开头，Kramdown 将渲染为有序列表项（表现为缩进 + 序号从 1 开始）。修复：纯文本路径加 `bold_verse_starts`；富文本路径检查 `extract_block_rich` 是否正确输出 `**N.**`
- [ ] **段落无异常换行**：随机抽查 3–5 处跨页位置，确认段落连续，无孤立的半句另起一段
- [ ] **希腊文显示正常**：页面中希腊文字符可见（如 τὸ αὐτὸ），无 ASCII 转写残留（如 `to< aujto<`）
- [ ] **表格标题跨全宽**：浏览器中 `PHILIPPIANS X:Y-Z` 标题横贯两列，无右侧空白单元格
- [ ] **表格横向可滚动，每节一行**：经文表格每节经文显示为一行（不在格内折行），超出屏幕宽度时可左右滑动。验证方法：缩窄浏览器窗口至 400px，确认表格出现横向滚动条而非文字换行。若仍换行，检查：① `td` 是否有 `white-space: nowrap`；② `tr/tbody/thead` 是否有 `width: 100%`（有则删除，它会锁死行宽阻止 overflow）

---

## 发布到网站

提取完成后，按以下步骤将英文原文书卷发布到 `/calvin/` 下。

### Step 1：分析 MD 文件结构

运行以下 Python 脚本，同时打印页面标记和标题行，便于精确定位边界：

```python
import re

with open("OUTPUT_MD_PATH", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if (re.match(r'^# ', line)
            or re.match(r'^## ', line)
            or re.match(r'^<!-- PAGE \d+', line)):
        print(f"{i:4d}: {line.rstrip()}")
```

输出示例：
```
 205:  <!-- PAGE 16 -->
 210:  <!-- PAGE 17 -->
 212:  <p ...>COMMENTARY ON</p>      ← 此行在 PAGE 17，属于第1章
 214:  ## THE EPISTLE OF PAUL...     ← 同上，属于第1章
 215:  # CHAPTER 1                   ← 第1章正文开始
```

**边界划定原则（必须遵守）**：

1. **以 `<!-- PAGE N -->` 为基准**：某章节第一个 `# HEADING` 之前的 `<!-- PAGE N -->` 标记所属的整页内容（从该 PAGE 标记到下一 PAGE 标记之间）都属于该章节，不得划入上一章。
2. **同页内容不拆分**：PDF 同一页上的所有内容（页眉、标题、正文）归属同一章节，不能一半在前言一半在第1章。
3. **fn_sections 用 `##` 标记划定**：fn 区的 `## WORD` 行是天然的脚注分节边界，其前的脚注属于上一节，其后的脚注属于下一节；分节标题行本身过滤掉。

根据输出确定边界（示例）：

| 段落 | 起始行 | 结束行（取该章第一个 PAGE 标记行） |
|------|--------|--------|
| 前言 | 19 | `# CHAPTER 1` 之前那个 `<!-- PAGE N -->` 的行号 |
| Chapter 1 | 上面确定的 PAGE 行 | `# CHAPTER 2` 之前那个 PAGE 行 |
| … | … | … |
| 脚注-前言 | fn 区起始 | fn 区 `## THE ARGUMENT` 行 |
| 脚注-THE ARGUMENT | `## THE ARGUMENT` 行+1 | fn 区 `## CHAPTER 1` 行 |
| 脚注-Chapter 1 | `## CHAPTER 1` 行+1 | fn 区 `## CHAPTER 2` 行 |
| … | … | … |

### 已知坑：章节边界过晚导致内容泄漏到上一章（发布环节）

**症状 A：其他章节的脚注出现在当前章**
fn_sections 边界划定时未利用 `##` 分界线，导致多个章节的脚注堆在同一文件里。
修复：重新对照 Step 1 输出，用 `##` 行号精确划定每章 fn 边界，各章脚注单独归档：
```python
fn = "".join(l for l in lines[fn_start:fn_end] if not re.match(r'^## ', l))
```

**症状 B：下一章 H1 标题 + 首个经文表格出现在上一章正文末尾**
`sections["N"]` 的结束行设得太晚，把下一章的 H1 标题和前几节经文行包进来。下一章文件 front matter 之后直接是孤立的 `| 3 . ...` Markdown 行（表格已被截断，头部留在上一章）。
修复步骤：
1. 用 Step 1 脚本定位下一章 H1 的精确行号，缩小 `sections["N"]` 结束边界
2. 将上一章多余的 H1 标题和表格行删除
3. 将下一章文件开头替换为完整的 HTML 经文表格（含表头和所有节）

**快速定位受影响章节**（与具体章节词无关）：
```bash
grep -c "^# " calvin/BOOK_ID/*.md          # 值 ≥2 的文件 → 该文件是受污染章
grep -n "^| [0-9]" calvin/BOOK_ID/*.md     # 有此行的文件 → 该章首个表格被截断
```

### 已知坑：脚注分隔符 `---` 导致最后一段被 Kramdown 识别为 `<h2>`（发布环节）

**症状**：章节最后一个正文段落（如 `**31.** ...`）渲染为粗体居中大字（`<h2>` 样式）。

**原因**：`build_fn_section` 中用 `'\n---\n'` 开头，而 `content.strip()` 去掉了末尾换行，导致 MD 文件中最后一段与 `---` 之间没有空行：
```
Mark the end that God has in view...
---
[^36]: ...
```
Kramdown 把 `---` 紧接在段落后视为 Setext 下划线，将该段升为 `<h2>`。

**修复**：`build_fn_section` 开头必须用两个换行：
```python
# 错误：
parts = ['\n---\n']

# 正确：
parts = ['\n\n---\n']
```
这样保证脚注分隔线前始终有一个空行，无论 `content.strip()` 是否移除末尾换行。

### Step 2：创建 Layout 文件

如果 `_layouts/calvin-en.html` 和 `_layouts/calvin-en-book.html` 不存在，从腓立比书英文版复制后修改，或重新创建：

- **`_layouts/calvin-en.html`**：正文页，渲染 Markdown，含前后章导航
- **`_layouts/calvin-en-book.html`**：书卷目录页，列出 Preface + Chapter 1–N

**序言文件名必须是 `preface.md`**：`calvin-en-book.html` 的目录页硬编码链接 `/calvin/BOOK_ID/preface/`。publish 脚本中第一个 section（`'introduction'` label）输出文件名必须写 `preface.md`，标题写 `Translator's Preface`，导航 label 也用 `preface`。若写成 `introduction.md` 则目录页链接 404，序言内容无法访问。

关键样式（`calvin-en.html` 内）：
```css
.calvin-en-content { font-family: Georgia, serif; font-size: 16px; line-height: 1.8; }
.calvin-en-content blockquote { margin-left: 2em; border-left: none; }
.calvin-en-content table { width: 100%; border-collapse: collapse; }
/* calvin-scripture：还原 PDF 两列经文表格，标题跨全宽，窄屏横向滚动 */
/* ⚠️ 经浏览器验证的最终版本，禁止添加 tr{width:100%} 等限宽规则 */
.calvin-en-content table.calvin-scripture {
  display: block;              /* 让 overflow-x 生效 */
  overflow-x: auto;            /* 窄屏横向滚动 */
  -webkit-overflow-scrolling: touch;
}
.calvin-en-content table.calvin-scripture th[colspan="2"] { font-size: 15px; }
.calvin-en-content table.calvin-scripture td {
  min-width: 280px;            /* 每列最小宽度，不被压窄 */
  white-space: nowrap;         /* 每节经文一行，不在格内折行 */
  vertical-align: top;
}
```

**常见陷阱（已踩过，禁止重复）：**

| 错误写法 | 为什么错 |
|---------|---------|
| `tr { width: 100% }` 或 `tbody { width: 100% }` | 把每行宽度锁死在容器宽度内，overflow 永远不会发生，横滑失效 |
| `td { white-space: normal }` | 文字在格内换行，每节经文变成多行，无法"一节一行" |
| `table { width: 100% }` 与 `display: block` 同时存在 | 表格被撑满容器，无超出，overflow-x 无效 |

**CSS 修改必须经浏览器验证后才能更新 skill**：不得在仅通过代码审查（未在浏览器中实际看到效果）的情况下将 CSS 写入 skill 模板。

若 `_layouts/calvin-en.html` 已存在，直接复用；若不存在，按上述样式新建。

**必须包含的功能：脚注序号可点击跳回引用位置**

无论是新建还是复用 `calvin-en.html`，都必须确认以下 CSS + JS 已存在（若缺失则补充）：

```css
/* 脚注区 */
.calvin-en-content .footnotes { margin-top: 40px; padding-top: 16px; border-top: 1px solid #ddd; font-size: 14px; color: #555; }
.calvin-en-content .footnotes ol { list-style: none; padding-left: 0; margin: 0; }
.calvin-en-content .footnotes li { display: flex; gap: 0.5em; margin-bottom: 8px; line-height: 1.7; }
.fn-backref-num { flex-shrink: 0; min-width: 1.8em; text-align: right; color: #0085a1; font-weight: bold; font-size: 0.9em; text-decoration: none; padding-top: 0.05em; }
.fn-backref-num:hover { text-decoration: underline; }
.calvin-en-content .footnotes li > p { margin: 0; flex: 1; }
.calvin-en-content .footnotes .reversefootnote { margin-left: 0.3em; color: #aaa; text-decoration: none; font-size: 0.85em; }
.calvin-en-content .footnotes .reversefootnote:hover { color: #0085a1; }
```

```javascript
// 脚注序号点击跳回引用位置
(function() {
  var lists = document.querySelectorAll('.calvin-en-content .footnotes ol');
  lists.forEach(function(ol) {
    ol.querySelectorAll('li[id]').forEach(function(li, idx) {
      var refId = li.id.replace(/^fn:/, 'fnref:');
      var a = document.createElement('a');
      a.href = '#' + refId;
      a.className = 'fn-backref-num';
      a.textContent = (idx + 1) + '.';
      a.title = '返回引用位置';
      li.insertBefore(a, li.firstChild);
    });
  });
})();
```

原理：Kramdown 渲染 `[^f1]` 时生成 `id="fn:f1"` 的 `<li>` 和 `id="fnref:f1"` 的行内 `<sup>`；JS 将 `fn:` 替换为 `fnref:` 即可定位引用锚点。

**⚠️ CSS 陷阱：`:only-child` 不计算文本节点**

绝对禁止用 `p:has(> strong:only-child)` 来匹配"仅含一个 `<strong>` 标签的段落"。

原因：CSS `:only-child` 判断的是"无兄弟**元素**"，文本节点不算元素。所以：
```html
<p><strong>24.</strong> commentary text...</p>
```
里的 `<strong>` 没有元素兄弟，被认为是 only-child，导致所有注释段落都命中该规则，字体变成 12px、居中、灰色。

**正确做法**：如需给"纯孤立 strong 段落"（无任何文本内容）加样式，必须用 JS 检测后加 class，再用 CSS 针对该 class：

```javascript
// 找出段落文本内容等于其唯一 strong 子元素文本内容的段落（真正的孤立标签）
document.querySelectorAll('.calvin-en-content p').forEach(function(p) {
  if (p.children.length === 1 && p.children[0].tagName === 'STRONG'
      && p.textContent.trim() === p.children[0].textContent.trim()) {
    p.classList.add('page-marker');
  }
});
```

```css
.calvin-en-content p.page-marker { color: #aaa; font-size: 12px; text-align: center; margin: 4px 0; }
```

**Acts 注释里不存在 page marker 块**（提取脚本已过滤所有页码），不需要加这段代码；如果不确定，直接省略即可。

### Step 3：运行 Python 发布脚本

将以下脚本中的边界替换为 Step 1 查到的实际值：

```python
import os

BOOK_ID   = "REPLACE_BOOK_ID"         # 如 philippians-en
BOOK_NAME = "REPLACE_BOOK_NAME"       # 如 Calvin on Philippians
MD_PATH   = "REPLACE_MD_PATH"
OUT_DIR   = f"/Users/yanpeifa/Documents/whcjb.github.io/calvin/{BOOK_ID}"
DATE      = "REPLACE_DATE"            # 必须精确到分钟！用 date '+%Y-%m-%d %H:%M' 获取真实时间，禁止写死占位时间

with open(MD_PATH, encoding="utf-8") as f:
    lines = f.readlines()

# ── 根据实际分析结果修改以下边界 ──────────────────────────────────────────
sections = {
    "preface": (19, 223),
    "1": (223, 523),
    "2": (523, 931),
    "3": (931, 1232),
    "4": (1232, 1470),
}
fn_sections = {
    "preface": (1474, 1548),
    "1": (1548, 1794),
    "2": (1794, 2022),
    "3": (2022, 2169),
    "4": (2169, len(lines)),
}
# ─────────────────────────────────────────────────────────────────────────────

chapter_keys = [k for k in sections if k != "preface"]
all_keys = ["preface"] + chapter_keys

labels = {"preface": "Preface"}
labels.update({k: f"Chapter {k}" for k in chapter_keys})

nav = {}
for idx, key in enumerate(all_keys):
    prev_k = all_keys[idx-1] if idx > 0 else ""
    next_k = all_keys[idx+1] if idx < len(all_keys)-1 else ""
    nav[key] = (prev_k, labels.get(prev_k,""), next_k, labels.get(next_k,""))

os.makedirs(OUT_DIR, exist_ok=True)

for key, (start, end) in sections.items():
    fn_start, fn_end = fn_sections[key]
    body = "".join(lines[start:end])
    # 去掉脚注区的分节标题（## CHAPTER X / ## SERMON X 等，PDF组织标记，不应出现在网页上）
    fn_raw = lines[fn_start:fn_end]
    fn   = "".join(l for l in fn_raw if not re.match(r'^## ', l))
    prev_s, prev_l, next_s, next_l = nav[key]

    fm = "---\n"
    fm += "layout: calvin-en\n"
    fm += f"book_id: {BOOK_ID}\n"
    fm += f'book_name: "{BOOK_NAME}"\n'
    fm += f'title: "{labels[key]}"\n'
    fm += f"date: {DATE}\n"
    if prev_s:
        fm += f"prev_section: {prev_s}\nprev_label: \"{prev_l}\"\n"
    if next_s:
        fm += f"next_section: {next_s}\nnext_label: \"{next_l}\"\n"
    fm += "---\n\n"

    with open(f"{OUT_DIR}/{key}.md", "w", encoding="utf-8") as f:
        f.write(fm + body.rstrip() + "\n\n---\n\n" + fn.rstrip() + "\n")
    print(f"Written {key}.md")

# index.html
with open(f"{OUT_DIR}/index.html", "w") as f:
    f.write(f"---\nlayout: calvin-en-book\nbook_id: {BOOK_ID}\n"
            f'book_name: "{BOOK_NAME}"\nchapters: {len(chapter_keys)}\n---\n')
print("Written index.html")
```

### Step 4：注册到书卷列表

在 `_data/calvin_books.yml` 的新约部分添加：

```yaml
  - id: BOOK_ID
    name: "Book Name (EN)"
    chapters: N
```

### Step 5：构建验证

```bash
~/.rbenv/shims/bundle exec jekyll build
```

访问 `/calvin/BOOK_ID/` 验证效果。

---

## 中文翻译 + 发布流程

在英文 MD 提取完成后，可进一步翻译成中文并发布为中文版网页。
中文版使用与英文版**完全相同的 layout（calvin-en）**，只有内容是中文。

### 翻译原则

- 只翻译英文内容，拉丁文/法文/希腊文原文保留并括注中文
- 保留所有格式标记：`[^fN]`、`<span>`、`<!-- PAGE N -->`
- 圣经书卷名用和合本标准译名（PHILIPPIANS→腓立比书 等）
- 脚注中的法文引文保留原文，破折号后附中文译文

### 翻译脚本（`scripts/translate_filibi.py` 为模板）

翻译脚本的**最终输出是一个完整的中文 MD 文件**（如 `ocr_output/BOOK/calvin_BOOK_zh.md`），保存英文版的完整结构，所有英文正文替换为中文。该文件是发布脚本的输入源，必须先生成并检查后再执行发布。

```bash
# 全量翻译（耗时较长）
python3 scripts/translate_filibi.py

# 断点续翻（已翻译的段落直接读缓存）
python3 scripts/translate_filibi.py --resume

# 只统计各类型行数，不翻译
python3 scripts/translate_filibi.py --dry-run
```

脚本特点：
- 使用 **claude CLI** 翻译，每批 20 段（`<<<N>>>` 格式）
- 每段以 MD5 hash 为 key 缓存到 `ocr_output/BOOK/zh_cache/`，中断可续翻
- 行类型自动识别：H1/H2、blockquote、footnote、Markdown 表格行（左列英文→译，右列拉丁→保留）、普通段落
- **翻译完成后将所有段落按原顺序拼合，写入 `ocr_output/BOOK/calvin_BOOK_zh.md`**

为新书卷创建翻译脚本时，复制 `translate_filibi.py` 并修改：
- `SRC`（英文 MD 路径）、`CACHE_DIR`（缓存目录）、`OUT`（中文 MD 输出路径，如 `ocr_output/BOOK/calvin_BOOK_zh.md`）
- `SYSTEM` 提示中的书卷名映射（如 EPHESIANS→以弗所书）

翻译完成后，**必须检查中文 MD 文件**再执行发布：
```bash
# 确认中文 MD 已生成且非空
wc -l ocr_output/BOOK/calvin_BOOK_zh.md

# 抽查若干段落，确认翻译质量
sed -n '100,120p' ocr_output/BOOK/calvin_BOOK_zh.md
```

### 发布脚本（`scripts/publish_filibi_zh.py` 为模板）

```bash
python3 scripts/publish_filibi_zh.py
```

脚本执行：
1. 读取中文 MD，按章节边界切分（`SECTIONS` / `FN_SECTIONS`）
2. 将 Markdown 经文表格（`| **BOOK X:Y** | |`）转换为 HTML `<table class="calvin-scripture">`
3. 过滤脚注区 `## ` 分节标题
4. 写入目标目录，使用 `layout: calvin-en` 和中文 front matter（前言/第一章…）
5. 生成 `index.html`（`layout: calvin-en-book`）

为新书卷创建发布脚本时，复制 `publish_filibi_zh.py` 并修改：
- `MD_PATH`、`OUT_DIR`、`BOOK_ID`、`BOOK_NAME`
- `SECTIONS` / `FN_SECTIONS`：运行 `grep -n "^# " ZH_MD` 确认实际行号
- `LABELS`：前言/各章中文名称
- `CH_KEYS`：章节键列表

### 翻译质检 Checklist

- [ ] **表格左列已翻译**：`grep -n "^| [A-Z]" calvin/BOOK_ID/*.md` 结果为空（英文句子不应出现在左列）
- [ ] **拉丁文列未被翻译**：右列仍为拉丁文（如 `Paulus et Timotheus...`）
- [ ] **脚注引用标记完整**：`grep "[^f\d]" calvin/BOOK_ID/*.md`（确认 `[^f1]` 等未被误译）
- [ ] **无多余说明文字**：页面无"以下是翻译："等 claude 生成的前言
- [ ] **表格已转 HTML**：`grep -n "^| [0-9]" calvin/BOOK_ID/*.md` 为空

---

## PDF 提取脚本

## Python 脚本

```python
import fitz, re, os

PDF_PATH = "REPLACE_WITH_PDF_PATH"
OUTPUT_PATH = "REPLACE_WITH_OUTPUT_PATH"

doc = fitz.open(PDF_PATH)
TABLE_SPLIT_X = 200

# ── 自动校准正文左/右边距（不硬编码）────────────────────────────────────────
from collections import Counter as _Counter

def _calibrate(doc, side="left", max_x=200):
    xs = []
    for page in doc:
        for b in page.get_text("dict")["blocks"]:
            if b["type"] != 0: continue
            x = round(b["bbox"][0] if side == "left" else b["bbox"][2])
            if b["bbox"][0] < max_x:
                xs.append(x)
    return _Counter(xs).most_common(1)[0][0] if xs else (35 if side == "left" else None)

INDENT_X   = _calibrate(doc, "left")  + 10  # 正文左边距+缓冲
BODY_RIGHT = _calibrate(doc, "right")        # 正文右边距（用于检测右对齐）

def classify_alignment(block, page_w, tol_px=50):
    """左边距 > INDENT_X 的块做三向分类：CENTERED / RIGHT / BLOCKQUOTE。
    用固定像素容差（不用 page_w 百分比）——更稳定，不随 PDF 页宽放大。"""
    bx0, bx1 = block["bbox"][0], block["bbox"][2]
    if abs((bx0 + bx1) / 2 - page_w / 2) < tol_px:
        return "CENTERED"
    if BODY_RIGHT and abs(bx1 - BODY_RIGHT) < tol_px // 2:
        return "RIGHT"
    return "BLOCKQUOTE"

# 自动检测脚注区起始页（含 "FOOTNOTES" H1 标题，且在文档后40%位置）
FOOTNOTE_SECTION_START = len(doc)
for i, page in enumerate(doc):
    if "FOOTNOTES" in page.get_text() and i > len(doc) * 0.4:
        FOOTNOTE_SECTION_START = i
        break

# ── Ages Digital Library 希腊文转写 → Unicode ────────────────────────────────
# Ages 转写规则：辅音直接映射；元音后跟 j=平气，><~ 重/锐/抑扬音，|=iota下标；v=词尾sigma
# 双元音中的声调符夹在两个元音之间时属于第二个元音（如 ejmo>i → ἐμοί）
_GCOMB = {'j':'\u0313','>':'\u0301','<':'\u0300','~':'\u0342','|':'\u0345'}
_GBASE = {
    'a':'α','b':'β','g':'γ','d':'δ','e':'ε','z':'ζ','h':'η','q':'θ',
    'i':'ι','k':'κ','l':'λ','m':'μ','n':'ν','x':'ξ','o':'ο','p':'π',
    'r':'ρ','s':'σ','t':'τ','u':'υ','v':'ς','f':'φ','c':'χ','y':'ψ','w':'ω',
    'A':'Α','B':'Β','G':'Γ','D':'Δ','E':'Ε','Z':'Ζ','H':'Η','Q':'Θ',
    'I':'Ι','K':'Κ','L':'Λ','M':'Μ','N':'Ν','X':'Ξ','O':'Ο','P':'Π',
    'R':'Ρ','S':'Σ','T':'Τ','U':'Υ','V':'Σ','F':'Φ','C':'Χ','Y':'Ψ','W':'Ω',
}
_GVOWELS = set('aehiouwAEHIOUW')
_GDIPH = {'a':'iu','e':'iu','o':'iu','h':'u','u':'i','A':'IU','E':'IU','O':'IU','H':'U','U':'I'}

def _ages_token(tok):
    import unicodedata as _ud
    res=[]; i=0; n=len(tok); pend=''
    while i < n:
        ch = tok[i]
        if ch not in _GBASE: i+=1; continue
        base=_GBASE[ch]; i+=1; comb=pend; pend=''
        if ch in _GVOWELS:
            if i<n and tok[i]=='j': comb+=_GCOMB['j']; i+=1
            if i<n and tok[i] in '><~':
                acc=tok[i]; nxt=tok[i+1] if i+1<n else ''
                if nxt in _GVOWELS and nxt in _GDIPH.get(ch,''):
                    pend=_GCOMB[acc]; i+=1
                else:
                    comb+=_GCOMB[acc]; i+=1
            if i<n and tok[i]=='|': comb+=_GCOMB['|']; i+=1
            elif i+1<n and tok[i]=='\\' and tok[i+1]=='|': comb+=_GCOMB['|']; i+=2
        res.append(_ud.normalize('NFC', base+comb))
    return ''.join(res)

_AGES_PAT = re.compile(r'[a-zA-Z][a-zA-Z><~j|\\]*(?:[><~]|\\[|]|\|)[a-zA-Z><~j|\\]*')

def convert_ages_greek(text):
    """将 Ages Digital Library 希腊文转写替换为 Unicode。跳过 HTML 标签内部。
    注意：用 <[a-zA-Z/!] 严格匹配 HTML 标签开头，避免 to< ... <span> 被误识别为标签。"""
    _pat = re.compile(
        r'(<[a-zA-Z/!][^>]*>)'              # group 1: HTML tag
        r'|([a-zA-Z][a-zA-Z><~j|\\]*'
        r'(?:[><~]|\\[|]|\|)'
        r'[a-zA-Z><~j|\\]*)'               # group 2: Ages Greek token
    )
    def _repl(m):
        if m.group(1): return m.group(1)   # HTML tag: 原样保留
        tok = m.group(2)
        c = _ages_token(tok.replace('\\|','|'))
        return c if any('\u0370'<=x<='\u03ff' or '\u1f00'<=x<='\u1fff' for x in c) else tok
    return _pat.sub(_repl, text)
# ─────────────────────────────────────────────────────────────────────────────

def is_table_header_text(text):
    # 仅匹配以 <NNNNNN> 开头的行（表格头），排除行内引用如 (<422447>Luke 24:47)
    return bool(re.match(r'\s*<\d{6,7}>', text))

def clean(text):
    # 消除大写字母间多余空格（spaced-caps渲染产物）："T HE" → "THE"
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r'\b([A-Z]) ([A-Z]+)', r'\1\2', text)
    return re.sub(r' {2,}', ' ', text).strip()

def join_lines(lines):
    # 合并块内各行，处理行末连字符（如 "some-\nthing" → "something"）
    parts = [t for _, t in lines]
    result = ""
    for p in parts:
        if result.endswith('-'):
            result = result[:-1] + p   # 去掉连字符，直接拼接
        else:
            result = result + (" " if result else "") + p
    return result

def is_sentence_end(text):
    # 判断文本是否以句子结尾（考虑尾部引号/括号）
    stripped = text.rstrip().rstrip('"\')}]')
    if not stripped:
        return True
    return stripped[-1] in '.!?…'

def format_inline(text):
    # Ages 行内圣经引用代码（内部索引，无内容价值）→ 剥除，只保留后面的经文引用文字
    text = re.sub(r'\[?<\d{6,7}>\]?\s*', '', text)
    # 红色斜体引文 → colored italic
    text = re.sub(r'<verse>(.*?)</verse>',
                  r'<span style="color:#800000">*\1*</span>', text)
    # 行内脚注序号 → Markdown footnote ref
    text = re.sub(r'\[([fF][tT]?\d+)\]', r'[^\1]', text)
    return text

def span_inline(text, size, color, flags):
    is_italic = bool(flags & 2)
    is_super  = bool(flags & 1)
    is_red    = (color == 0x800000)
    if is_red and is_super and size <= 9:
        return f"[{text}]"
    if is_red and is_italic:
        return f"<verse>{text}</verse>"
    return text

def block_lines(block):
    result = []
    for line in block["lines"]:
        if not line["spans"]: continue
        x = line["spans"][0]["origin"][0]
        parts = [span_inline(s["text"].strip(), round(s["size"]), s["color"], s["flags"])
                 for s in line["spans"] if s["text"].strip()]
        if parts:
            result.append((x, clean(" ".join(parts))))
    return result

def block_heading_type(block):
    for line in block["lines"]:
        for span in line["spans"]:
            s = round(span["size"])
            if s >= 18: return "H1"
            if s >= 14: return "H2"
    return None

def block_font_size(block):
    for line in block["lines"]:
        if line["spans"]:
            return round(line["spans"][0]["size"])
    return 12

def in_table(bbox, table_regions):
    for tr in table_regions:
        if bbox[1] >= tr[0] - 1 and bbox[3] <= tr[1] + 10:
            return True
    return False

def is_plain_scripture_header_block(b, lines):
    """检测无 <NNNNNN> 代码的表格头块：居中（x>80）+ 大字体（≥14pt）+ 包含圣经引用格式。
    例：PHILIPPIANS 2:1-4（在 PDF 中以大字体居中显示）。"""
    if not b["lines"] or not b["lines"][0]["spans"]:
        return False
    first_span = b["lines"][0]["spans"][0]
    if round(first_span["size"]) < 14:
        return False
    if first_span["origin"][0] < 80:   # 必须居中，不能是左对齐正文
        return False
    if not lines:
        return False
    return bool(re.search(r'\b[A-Z]{3,}\s+\d+:\d+', lines[0][1]))

# ── Stage 1: collect structured items ────────────────────────────────────────
items = []

for page_num, page in enumerate(doc):
    items.append({"type": "PAGE", "text": str(page_num + 1)})
    in_fn = (page_num >= FOOTNOTE_SECTION_START)
    page_w = page.rect.width

    blocks_raw = [b for b in page.get_text("dict")["blocks"] if b["type"] == 0]
    blocks = [(b, block_lines(b)) for b in blocks_raw]

    # 找表格区域（支持两种表格头格式）
    table_regions = []
    for b, lines in blocks:
        all_line_text = " ".join(t for _, t in lines)
        if is_table_header_text(all_line_text) or is_plain_scripture_header_block(b, lines):
            table_regions.append([b["bbox"][1], b["bbox"][3]])

    for tr in table_regions:
        y_header = tr[0]
        for b, lines in blocks:
            by0 = b["bbox"][1]
            if by0 <= y_header: continue
            bw  = b["bbox"][2] - b["bbox"][0]
            bx0 = b["bbox"][0]
            has_right = any(x >= TABLE_SPLIT_X for x, _ in lines)
            if bw > page_w * 0.6 and bx0 < 50 and not has_right:
                break
            tr[1] = max(tr[1], b["bbox"][3])

    for block, lines in blocks:
        if not lines: continue
        all_text = join_lines(lines)

        if in_fn:
            s = block_font_size(block)
            if s >= 18:   items.append({"type": "H1", "text": all_text})
            elif s >= 14: items.append({"type": "H2", "text": all_text})
            else:         items.append({"type": "FOOTNOTE", "text": all_text})
            continue

        if in_table(block["bbox"], table_regions):
            if is_table_header_text(all_text):
                # 旧格式：含 <NNNNNN> 代码，从 block x 坐标判断对齐
                hdr_x = block["bbox"][0]
                page_w = page.rect.width
                align = "center" if hdr_x > page_w * 0.2 else "left"
                for x, t in lines:
                    if is_table_header_text(t):
                        items.append({"type": "TABLE_HEADER", "text": t, "align": align})
                    elif x < TABLE_SPLIT_X:
                        items.append({"type": "TABLE_LEFT", "text": t})
                    else:
                        items.append({"type": "TABLE_RIGHT", "text": t})
            elif is_plain_scripture_header_block(block, lines):
                # 新格式：居中大字体（x>80），对齐直接取自 PDF 块位置
                hdr_x = block["bbox"][0]
                page_w = page.rect.width
                align = "center" if hdr_x > page_w * 0.2 else "left"
                items.append({"type": "TABLE_HEADER", "text": lines[0][1], "align": align})
                for x, t in lines[1:]:
                    ltype = "TABLE_RIGHT" if x >= TABLE_SPLIT_X else "TABLE_LEFT"
                    items.append({"type": ltype, "text": t})
            else:
                for x, t in lines:
                    ltype = "TABLE_RIGHT" if x >= TABLE_SPLIT_X else "TABLE_LEFT"
                    items.append({"type": ltype, "text": t})
            continue

        ht = block_heading_type(block)
        if ht:
            items.append({"type": ht, "text": all_text})
            continue

        if block["bbox"][0] > INDENT_X:
            align = classify_alignment(block, page_w)
            if align == "CENTERED":
                is_italic = all(
                    bool(s["flags"] & 2)
                    for line in block["lines"] for s in line["spans"] if s["text"].strip()
                )
                items.append({"type": "CENTERED", "text": all_text, "italic": is_italic})
            elif align == "RIGHT":
                items.append({"type": "RIGHT", "text": all_text})
            else:
                items.append({"type": "BLOCKQUOTE", "text": all_text})
        else:
            items.append({"type": "BODY", "text": all_text})

# ── Stage 1.5: merge paragraph fragments (structural, not content-based) ─────
# 纯结构化：nxt_indent < PARA_INDENT_LOW = 无段落首行缩进 = 续行 block
# 安全兜底：not is_sentence_end(cur) 防止段首无缩进的新章节首段被误合并
# ⚠️ 严禁使用 first_char（大小写）或 cur_ends_comma——内容判断会误合并引文段落
PARA_INDENT_LOW = 10  # 与 split_block_by_paragraph_indent 保持一致

idx = 0
while idx < len(items):
    if items[idx]["type"] in ("BODY", "BLOCKQUOTE"):
        cur_type = items[idx]["type"]
        j = idx + 1
        while j < len(items) and items[j]["type"] == "PAGE":
            j += 1
        if j < len(items) and items[j]["type"] == cur_type:
            cur_text = items[idx]["text"]
            nxt_text = items[j]["text"]
            nxt_indent = items[j].get("indent", 0)
            if nxt_indent < PARA_INDENT_LOW and not is_sentence_end(cur_text):
                items[idx]["text"] = cur_text.rstrip() + " " + nxt_text.lstrip()
                items.pop(j)
                continue
    idx += 1

# ── Stage 2: render to Markdown ───────────────────────────────────────────────
TABLE_TYPES = {"TABLE_HEADER", "TABLE_LEFT", "TABLE_RIGHT"}

def render_table_group(group):
    header = None
    rows = []
    cur_left, cur_right = [], []
    in_right = False

    header_align = "center"
    for item in group:
        t, text = item["type"], item["text"]
        if t == "TABLE_HEADER":
            header = text
            header_align = item.get("align", "center")
        elif t == "TABLE_LEFT":
            if in_right:
                rows.append((" ".join(cur_left), " ".join(cur_right)))
                cur_left, cur_right = [], []
                in_right = False
            cur_left.append(text)
        elif t == "TABLE_RIGHT":
            in_right = True
            cur_right.append(text)

    if cur_left or cur_right:
        rows.append((" ".join(cur_left), " ".join(cur_right)))

    # 输出 HTML table，标题对齐从 PDF 检测，不 hardcode
    display = re.sub(r'<\d{6,7}>\s*', '', header).strip() if header else ''
    lines = ['<table class="calvin-scripture">']
    if display:
        lines.append(f'<thead><tr><th colspan="2" style="text-align:{header_align}">{display}</th></tr></thead>')
    lines.append('<tbody>')
    for left, right in rows:
        left  = convert_ages_greek(format_inline(left))
        right = convert_ages_greek(format_inline(right))
        lines.append(f'<tr><td>{left}</td><td>{right}</td></tr>')
    lines.append('</tbody>')
    lines.append('</table>')
    return "\n".join(lines)

md_lines = []
i = 0
while i < len(items):
    item = items[i]
    t = item["type"]

    if t == "PAGE":
        md_lines.append(f"\n<!-- PAGE {item['text']} -->\n")
        i += 1
    elif t == "H1":
        md_lines.append(f"\n# {item['text']}\n")
        i += 1
    elif t == "H2":
        md_lines.append(f"\n## {item['text']}\n")
        i += 1
    elif t == "BODY":
        text = format_inline(item['text'])
        text = convert_ages_greek(text)   # Ages希腊转写 → Unicode
        text = re.sub(r'(?<!\\)\|', r'\\|', text)
        text = re.sub(r'^(\d+)\s*\.', lambda m: m.group(1) + '\\.', text)
        md_lines.append(f"\n{text}\n")
        i += 1
    elif t == "CENTERED":
        text = format_inline(item['text'])
        text = convert_ages_greek(text)
        style = "text-align:center; font-style:italic" if item.get("italic") else "text-align:center"
        md_lines.append(f'\n<p style="{style}">{text}</p>\n')
        i += 1
    elif t == "RIGHT":
        text = format_inline(item['text'])
        text = convert_ages_greek(text)
        md_lines.append(f'\n<p style="text-align:right; font-style:italic">{text}</p>\n')
        i += 1
    elif t == "BLOCKQUOTE":
        text = format_inline(item['text'])
        text = convert_ages_greek(text)
        text = re.sub(r'(?<!\\)\|', r'\\|', text)
        text = re.sub(r'^(\d+)\s*\.', lambda m: m.group(1) + '\\.', text)
        md_lines.append(f"\n> {text}\n")
        i += 1
    elif t in TABLE_TYPES:
        group = []
        while i < len(items) and items[i]["type"] in TABLE_TYPES:
            group.append(items[i])
            i += 1
        md_lines.append(f"\n{render_table_group(group)}\n")
    elif t == "FOOTNOTE":
        text = item["text"]
        m = re.match(r'\s*([fF][tT]?\d+)\s*(.*)', text, re.DOTALL)
        if m:
            fn_text = convert_ages_greek(m.group(2).strip())
            fn_text = re.sub(r'(?<!\\)\|', r'\\|', fn_text)
            # 统一去掉 "t"：PDF 脚注区标签 ft18→f18，与正文引用 [^f18] 保持一致
            label = re.sub(r'^ft', 'f', m.group(1).lower())
            md_lines.append(f"\n[^{label}]: {fn_text}\n")
        else:
            fn_text = convert_ages_greek(text)
            fn_text = re.sub(r'(?<!\\)\|', r'\\|', fn_text)
            md_lines.append(f"\n> {fn_text}\n")
        i += 1
    else:
        i += 1

output = "\n".join(md_lines)
os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_PATH)), exist_ok=True)
with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
    f.write(output)

print(f"Done. {len(output):,} chars → {OUTPUT_PATH}")
print(f"Tables:    {output.count('|---|---|')}")
print(f"Footnotes: {output.count('[^ft')}")
print(f"Colored:   {output.count('color:#800000')}")
```

---

## ⚠️ 开始提取前必做：PDF 格式快速诊断

**在写任何提取脚本之前，必须运行以下诊断代码，确认 PDF 是 Ages 双语格式还是 CCEL 单列格式。不诊断就写脚本，是本节错误的根源。**

```python
import fitz, collections
doc = fitz.open("YOUR_PDF_PATH")
# 采样第 10-20 页，统计 block 的 x0 分布
xs = collections.Counter()
for i in range(min(10, len(doc)-1), min(20, len(doc))):
    for b in doc[i].get_text("dict")["blocks"]:
        if b["type"] == 0:
            xs[round(b["bbox"][0] / 10) * 10] += 1  # 10px 精度
for x, cnt in sorted(xs.most_common(6)):
    print(f"  x0≈{x:3d}: {cnt:3d} blocks")
doc.close()
```

**判断规则：**
- **双峰分布**（如 x≈74: 50 blocks 和 x≈220: 40 blocks）→ **Ages 双语格式**，经文区有英文+拉丁两列
- **单峰分布**（如 x≈74: 90 blocks）→ **CCEL 单列格式**

Ages 双语格式必须用下面的双语提取模板；CCEL 单列必须用 CCEL 提取模板。**不得混用。**

---

## Ages 双语格式 PDF（如希伯来书、腓立比书）

Ages Digital Library 的圣经注释 PDF 采用**左英文 / 右拉丁文两列并排**布局：
- 英文列：`block["bbox"][0] < LATIN_X_MIN`（通常 `LATIN_X_MIN=200`）
- 拉丁文列：`block["bbox"][0] >= LATIN_X_MIN`

经文区（scripture section）必须输出为 HTML 双语表格；注释区（commentary）只取英文列。

### 关键识别函数

```python
LATIN_X_MIN = 200   # 经实际 PDF 确认，可能需调整

def is_pure_latin_block(block):
    """整个 block 都在拉丁文列（bx0 >= LATIN_X_MIN）。"""
    return block["bbox"][0] >= LATIN_X_MIN

def is_verse_block(block):
    """经文块：首个英文列行以 bold 数字开头（size>=10，排除 6.6pt 脚注引用上标）。"""
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        if not spans: continue
        lx = line["bbox"][0]
        if lx >= LATIN_X_MIN: continue   # 跳过拉丁行，找第一个英文行
        fs = spans[0]
        flags = fs.get("flags", 0)
        size = fs.get("size", 0)
        t = fs["text"].strip()
        # size >= 10 排除脚注引用上标（通常 6-7pt）
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            return True
        break
    return False

def is_scripture_header(block):
    """经文段落标题：'Book N:M' 或 'Book Chapter N:M'，bold+italic，字号>=14。"""
    span = get_first_span(block)
    if not span: return False
    size = span.get("size", 0)
    flags = span.get("flags", 0)
    x0 = block["bbox"][0]
    if size >= 14 and (flags & 20) and 80 < x0 < 300:
        text = get_block_text(block).strip()
        if re.match(r'^(Hebrews|Philippians|Romans|...)\s+(Chapter\s+)?\d+:\d+', text):
            return True
    return False
```

### 逐行富文本提取（处理分裂节号）

Ages PDF 经常把节号 `1` 和句点 `. text...` 拆成两个 span：

```python
def extract_line_rich(line):
    """从单行提取富文本，把 bold 节号包装为 **N.**。
    处理节号被拆分为 '1' + '. text' 两个 span 的情况。"""
    spans = [s for s in line.get("spans", []) if s.get("text", "")]
    if not spans: return ""
    parts = []
    skip_dot = False
    for span in spans:
        text = span["text"]
        flags = span.get("flags", 0)
        size = span.get("size", 0)
        t = text.strip()
        if skip_dot:
            skip_dot = False
            if text.startswith('.'):
                text = text[1:]   # 去掉被分离的句点，保留后续空格
            parts.append(text)
            continue
        # size >= 10 防止把 6.6pt 脚注引用上标也包装成节号
        if (flags & 4) and size >= 10 and re.match(r'^\d+\.?$', t):
            num = t.rstrip('.')
            parts.append(f"**{num}.**")
            if not t.endswith('.'):
                skip_dot = True   # 句点在下一个 span 开头
        else:
            parts.append(text)
    return "".join(parts).strip()
```

### 双语表格构建

```python
def build_verse_table(section_header, verse_blocks):
    """把经文 block 列表组装为 HTML 双语表格（英文|拉丁文）。"""
    verses = {}   # {verse_num (int): {'en': [], 'la': []}}

    for block in verse_blocks:
        cur_en = cur_la = None
        for line in block.get("lines", []):
            spans = [s for s in line.get("spans", []) if s.get("text", "").strip()]
            if not spans: continue
            lx = line["bbox"][0]
            line_text = extract_line_rich(line)
            if not line_text: continue
            vn_m = re.match(r'\*\*(\d+)\.\*\*', line_text)
            if lx >= LATIN_X_MIN:
                if vn_m: cur_la = int(vn_m.group(1))
                if cur_la is not None:
                    verses.setdefault(cur_la, {'en': [], 'la': []})['la'].append(line_text)
            else:
                if vn_m: cur_en = int(vn_m.group(1))
                if cur_en is not None:
                    verses.setdefault(cur_en, {'en': [], 'la': []})['en'].append(line_text)

    if not verses: return ''

    def md_to_html(text):
        """<td> 内 Kramdown 不处理 Markdown，必须转为 HTML。"""
        text = text.replace('|', '&#124;')
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text

    html = ['<table class="calvin-scripture">']
    html.append(f'<thead><tr><th colspan="2" style="text-align:center">{section_header}</th></tr></thead>')
    html.append('<tbody>')
    for vn in sorted(verses.keys()):
        en = md_to_html(' '.join(verses[vn].get('en', [])))
        la = md_to_html(' '.join(verses[vn].get('la', [])))
        html.append(f'<tr><td>{en}</td><td>{la}</td></tr>')
    html.append('</tbody></table>')
    return '\n'.join(html)
```

⚠️ **`<td>` 内必须用 `<strong>` 而非 `**`**：Kramdown 不处理 HTML block 内的 Markdown 标记，`**N.**` 会以字面文字渲染。

### 提取主循环（状态机）

经文区（scripture section）和注释区（commentary）需要状态机切换：

```python
in_verse_section = False
current_section_header = None
verse_buf = []

def flush_verse_buf():
    nonlocal verse_buf
    if verse_buf and current_section_header:
        table = build_verse_table(current_section_header, verse_buf)
        if table:
            output_blocks.append(table)
    verse_buf = []

for block in blocks:
    if is_scripture_header(block):
        flush_verse_buf()
        current_section_header = normalize_scripture_header(text)
        output_blocks.append(f"\n## {current_section_header}\n")
        in_verse_section = True

    elif in_verse_section and (is_pure_latin_block(block) or is_verse_block(block)):
        # ⚠️ 拉丁文列 block 也要收集！is_pure_latin_block 不可漏掉
        verse_buf.append(block)

    elif in_verse_section:
        # 遇到注释文字 → 冲刷经文缓冲，切换到注释模式
        flush_verse_buf()
        in_verse_section = False
        handle_commentary(block)

    else:
        handle_commentary(block)
```

### Ages 双语格式质检 Checklist

- [ ] `grep -c '<table class="calvin-scripture">' raw.txt` → 数量与 PDF 中经文段数一致
- [ ] 检查首章：`grep -A 4 '<thead>' calvin/BOOK-en/1.md` → 表头含书卷名和章节号
- [ ] 检查 `<td>` 内无字面 `**N.**`：`grep '\*\*[0-9]' calvin/BOOK-en/1.md` → 无输出
- [ ] 每行 `<tr>` 两列均非空（拉丁文列有内容）
- [ ] `grep "^\*\*[0-9]\+\.\*\*$" raw.txt` → 孤立节号为 0（否则检查 `extract_line_rich` 的 `skip_dot` 逻辑）

---

## CCEL 格式 PDF（如使徒行传）

CCEL（Christian Classics Ethereal Library）格式与 Ages Digital Library 格式**完全不同**，必须用独立的提取脚本，不得套用 Ages 模板。

### 格式差异对比

| 特征 | Ages Digital Library | CCEL |
|------|---------------------|------|
| 页面结构 | 双列（拉丁文 + 英文） | 单列英文 |
| 希腊文 | ASCII 转写（需转 Unicode） | 已是 Unicode 或无 |
| 章节标题 | 脚注区 `## CHAPTER N` | 正文内独立块 `CHAPTER N` |
| 经文段落 | 表格形式（含表头） | 独立 block，bold+italic 节号开头 |
| 脚注内容 | 专属脚注区，`FtN` 开头 | 页底小字，内容行以 `N "文本"` 开头（**Unicode 弯引号**） |
| 脚注引用 | 行内上标 | 行内数字（嵌入正文，无法精确分离） |

### 关键块的识别

#### 1. 必须过滤的块

```python
SKIP_PAGES = 6  # 跳过前 N 页（标题页 + 目录）

def is_page_header(block):
    """页顶页眉：y0 < 55，含 'John Calvin' 或 'Comm on Acts'。"""
    if block["bbox"][1] > 55: return False
    text = get_block_text(block).strip()
    return "John Calvin" in text or "Comm on Acts" in text or re.match(r'^\d+$', text)

def is_page_number(block):
    """页码：纯数字 + 字号 ≤ 10。"""
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text): return False
    span = get_first_span(block)
    return span and span.get("size", 0) <= 10

def is_footnote_block(block):
    """脚注内容块：y0 > 705（页底区域），首 span 字号 < 8。"""
    if block["bbox"][1] < 705: return False
    span = get_first_span(block)
    return span and span.get("size", 0) < 8
```

#### 2. 章节标题块（⚠️ 必须过滤）

CCEL PDF 每章开头有**独立的 `CHAPTER N` 文本块**，位于正文区域内（不是页眉）。这与 Ages 格式完全不同。**必须在发布脚本（不是提取脚本）中过滤**，因为它们是内容块而非结构元素。

```python
# 发布脚本 is_skip_block 中加入：
if re.match(r'^CHAPTER\s+\d+$', t):
    return True
```

**为什么会漏掉**：`is_page_header` 检测的是 y0 < 55 的块，而 `CHAPTER N` 块出现在页面内部（y0 > 100），所以不会被捕获。

#### 3. 脚注内容块（⚠️ 注意 Unicode 弯引号）

CCEL 脚注内容块格式：`364 "Sed tanum hoc quaerint," but the only thing they ask is.`

注意引号是 Unicode 弯引号（`"` U+201C），不是 ASCII `"`。正则必须同时匹配：

```python
# 错误（不匹配）：
FOOTNOTE_RE = re.compile(r'^\d+\s+"')

# 正确：
FOOTNOTE_RE = re.compile(r'^\d+\s+[""''"\'a-z]')
# 同时覆盖：弯引号开头（脚注定义）和小写字母开头（脚注续行块）
```

**脚注续行块**：长脚注会在下一页顶部续行，格式为 `N 正文文字...`（数字+空格+小写，无引号），同样需要过滤。上面的正则通过 `[a-z]` 分支处理了这种情况。

### 跨页段落合并

CCEL 格式中，段落跨页后续行 block **没有 indent=0 的结构信号**（与 Ages 不同）。必须在**发布脚本**的后处理阶段用内容启发式合并：

```python
def join_orphan_verse_numbers(blocks):
    # Join standalone **N.** blocks (verse number with no text on same page)
    # with the following commentary block.
    # These occur when PyMuPDF sees the verse number and commentary text as
    # separate blocks across a page boundary.
    result = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        if re.match(r'^\*\*\d+\.\*\*$', block.strip()):
            if i + 1 < len(blocks) and not blocks[i + 1].startswith('##'):
                result.append(block.strip() + ' ' + blocks[i + 1].lstrip())
                i += 2
                continue
        result.append(block)
        i += 1
    return result


def merge_split_paragraphs(blocks):
    # Merge cross-page paragraph splits.
    # Rule: next block starts with lowercase letter = continuation of current block.
    # This holds for 16th century English commentary regardless of end punctuation
    # (the previous block may end with ?, ;, ), etc. and still continue on the
    # next page — do NOT add an end_char check).
    # Never merge across ## section headers.
    merged = []
    i = 0
    while i < len(blocks):
        block = blocks[i]
        while i + 1 < len(blocks):
            next_block = blocks[i + 1]
            if block.startswith('##') or next_block.startswith('##'):
                break
            next_start = next_block.lstrip()[0] if next_block.lstrip() else ''
            if next_start.islower():
                block = block.rstrip() + ' ' + next_block.lstrip()
                i += 1
            else:
                break
        merged.append(block)
        i += 1
    return merged
```

调用位置：`group_by_chapter` 中，对每个章节的 blocks 列表完成分组后调用。**必须先 `join_orphan_verse_numbers`，再 `merge_split_paragraphs`**：

```python
for ch in chapters:
    chapters[ch] = join_orphan_verse_numbers(chapters[ch])
    chapters[ch] = merge_split_paragraphs(chapters[ch])
```

**为什么不在 extract.py 里合并**：提取阶段的 `pending_continuation` 只处理末尾连字符（`word-`），无连字符跨页无法在提取时判断——因为要判断"下一块是否以小写开头"，需要看到下一块，而下一块可能属于不同的章节。发布脚本已经按章节分组，合并只在章节内进行，更安全。

### CCEL 提取脚本模板

```python
#!/usr/bin/env python3
import fitz, re, os

PDF_PATH = "REPLACE_WITH_PDF_PATH"
OUT_PATH  = "REPLACE_WITH_OUTPUT_PATH"
SKIP_PAGES = 6          # 跳过标题/目录页
HEADER_Y_MAX = 55       # 页顶页眉区域
FOOTER_Y_MIN = 705      # 页底脚注区域

def get_block_text(block):
    lines = []
    for line in block.get("lines", []):
        lines.append("".join(s["text"] for s in line.get("spans", [])))
    return "\n".join(lines)

def get_first_span(block):
    lines = block.get("lines", [])
    if not lines: return None
    spans = lines[0].get("spans", [])
    return spans[0] if spans else None

def is_page_header(block):
    if block["bbox"][1] > HEADER_Y_MAX: return False
    text = get_block_text(block).strip()
    return ("John Calvin" in text or "Comm on" in text
            or re.match(r'^\d+$', text))

def is_page_number(block):
    text = get_block_text(block).strip()
    if not re.match(r'^\d+$', text): return False
    s = get_first_span(block)
    return s and s.get("size", 0) <= 10

def is_footnote_block(block):
    if block["bbox"][1] < FOOTER_Y_MIN: return False
    s = get_first_span(block)
    return s and s.get("size", 0) < 8

def is_scripture_header(block):
    """经文段落标题：居中，字号≥14，bold+italic（flags&20），匹配 'Book N:M'。"""
    s = get_first_span(block)
    if not s: return False
    if s.get("size", 0) < 14 or not (s.get("flags", 0) & 20): return False
    x = block["bbox"][0]
    if x < 180 or x > 360: return False
    return bool(re.match(r'^\w+ \d+:\d+', get_block_text(block).strip()))

def is_verse_block(block):
    """注释段落：x≈74，首 span bold（flags&4），文本匹配 'N.'。"""
    x0 = block["bbox"][0]
    if x0 < 65 or x0 > 85: return False
    lines = block.get("lines", [])
    if not lines: return False
    spans = lines[0].get("spans", [])
    if not spans: return False
    fs = spans[0]
    return (fs.get("flags", 0) & 4) and re.match(r'^\d+\.$', fs["text"].strip())

def extract_block_rich(block):
    """提取 block 文本，对 bold 节号加 **N.** markdown。"""
    parts = []
    for line in block.get("lines", []):
        line_parts = []
        for span in line.get("spans", []):
            text = span["text"]
            t = text.strip()
            if (span.get("flags", 0) & 4) and re.match(r'^\d+\.$', t):
                line_parts.append(f"**{t}**")
            else:
                line_parts.append(text)
        parts.append("".join(line_parts))
    return " ".join(parts).strip()

def split_rich_by_verse(rich):
    """Split rich text at **N.** markers that appear mid-text.
    Handles the case where PyMuPDF merges commentary for multiple verses
    into one block (is_verse_block only checks the first span).
    """
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]

def is_index_start(text):
    return text.strip().upper() in (
        "INDEX", "INDEX OF SCRIPTURE REFERENCES",
        "SUBJECT INDEX", "INDEX OF SUBJECTS")

def process_pdf():
    doc = fitz.open(PDF_PATH)
    output_blocks = []
    pending = None  # 末尾连字符跨页

    for page_idx in range(SKIP_PAGES, len(doc)):
        page = doc[page_idx]
        blocks = sorted(
            page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"],
            key=lambda b: b["bbox"][1])

        for block in blocks:
            if block["type"] != 0: continue
            if is_page_header(block): continue
            if is_page_number(block): continue
            if is_footnote_block(block): continue

            text = get_block_text(block).strip()
            if not text: continue

            if is_index_start(text):
                if pending: output_blocks.append(pending); pending = None
                doc.close(); write_output(output_blocks); return

            if is_scripture_header(block):
                if pending: output_blocks.append(pending); pending = None
                output_blocks.append(f"\n## {text.replace(chr(10), ' ')}\n")
            elif is_verse_block(block):
                if pending: output_blocks.append(pending); pending = None
                output_blocks.append(extract_block_rich(block))
            else:
                rich = extract_block_rich(block)
                if rich.endswith("-"):          # 连字符跨页
                    pending = (pending or "") + rich[:-1]
                else:
                    if pending:
                        rich = pending + rich
                        pending = None
                    for sub in split_rich_by_verse(rich):
                        output_blocks.append(sub)

    if pending: output_blocks.append(pending)
    doc.close()
    write_output(output_blocks)

def write_output(blocks):
    os.makedirs(os.path.dirname(os.path.abspath(OUT_PATH)), exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + "\n")
    print(f"Written: {OUT_PATH} ({len(blocks)} blocks)")

if __name__ == "__main__":
    process_pdf()
```

### ⚠️ 提取后必做：发布前抽查（防止漏检错误上线）

**run extract.py → 必须先做以下抽查 → 再 run publish.py**

这一步是防止错误上线的关键。提取脚本运行完后，在运行发布脚本之前，必须用以下命令对 raw txt 做快速自检：

```bash
RAW=ocr_output/BOOK/BOOK_raw.txt
PUB=calvin/BOOK-en

# 1. 检查 CHAPTER N 块是否已被过滤（如果还有，发布脚本必须过滤）
grep -n “^CHAPTER [0-9]” $RAW | head -5

# 2a. 富文本 raw：检查节号合并（两个 **N.** 出现在同一行 → split_rich_by_verse 未生效）
grep -n “\*\*[0-9]\+\.\*\*.*\*\*[0-9]\+\.\*\*” $RAW | head -10

# 2b. 纯文本 raw：检查内嵌节号（同一 block 出现 2+ 个 “. N. 大写” → split_verse_commentary 未加到发布脚本）
python3 -c “
import re
with open('$RAW') as f: content = f.read()
blocks = re.split(r'\n{2,}', content)
for i, b in enumerate(blocks):
    if b.startswith('##') or b.startswith('<table'): continue
    hits = re.findall(r'(?<=\.) \d+\. [A-Z]', b)
    if len(hits) >= 2:
        print(f'Block {i}: {len(hits)} inline verse starts: {hits[:3]}')
        print(repr(b[:120]))
“ | head -20

# 3. 检查脚注内容是否泄漏（应为空）
python3 -c “
import re
with open('$RAW') as f: content = f.read()
blocks = re.split(r'\n{2,}', content)
leaks = [b[:80] for b in blocks if re.match(r'^\d+\s+[\”\”\”\'a-z]', b.strip())]
print(f'Footnote leaks: {len(leaks)}')
for l in leaks[:3]: print(repr(l))
“

# 4. 抽查 3 处章节边界，确认段落不在边界断裂
grep -n “^## “ $RAW | head -5
# 然后 Read 对应行前后各 3 行，目视确认无孤立半句

# 5. 发布后：检查孤立节号块（应为空，否则 join_orphan_verse_numbers 未生效）
grep -rn “^\*\*[0-9]*\.\*\*$” $PUB/*.md | head -10

# 6. 发布后：检查小写开头孤立块（应为空，否则 merge_split_paragraphs 未覆盖）
python3 -c “
import re, glob
for f in sorted(glob.glob('$PUB/*.md')):
    with open(f) as fh: content = fh.read()
    body = content.split('---', 2)[-1] if content.startswith('---') else content
    blocks = re.split(r'\n{2,}', body)
    for i, b in enumerate(blocks):
        stripped = b.strip()
        if stripped and stripped[0].islower() and not stripped.startswith('##'):
            print(f'{f}: block {i}: {stripped[:80]}')
“ | head -20
```

**判断标准**：
- 命令 1 有输出 → `is_skip_block` 加 `CHAPTER N` 过滤（正常，发布脚本已处理）
- 命令 2a 有输出 → `split_rich_by_verse` 未生效，检查 extract.py（富文本路径）
- 命令 2b 有输出 → `split_verse_commentary` 缺失，加到 publish.py 的 `group_by_chapter`（纯文本路径）
- 命令 3 有输出 → `FOOTNOTE_RE` 未匹配，检查引号类型（Unicode vs ASCII）
- 命令 4 视觉检查失败 → `merge_split_paragraphs` 需调整
- 命令 5 有输出 → `join_orphan_verse_numbers` 未调用或逻辑错误
- 命令 6 有输出 → `merge_split_paragraphs` 有遗漏，检查是否加了 end_char 判断（禁止）

**发布后必做：打开浏览器目视检查一个章节**，确认：
1. 经文段落（scripture text）和注释段落（commentary）字体大小相同（都是 16px）
2. 注释段落左对齐/两端对齐，不是居中
3. 节号（**24.**）显示为绿色带下划线（verse-anchor），经文段落内的节号无特殊样式
   - 如果注释段落字体变小且居中，立即检查 `calvin-en.html` 的 CSS，查找 `p:has(> strong:only-child)` 并删除（这是已知陷阱，见上方 CSS 警告）

### CCEL 发布脚本模板（发布到 calvin/BOOK-en/）

参见 `ocr_output/acts1/publish_acts.py`，关键点：

1. `is_skip_block` 必须包含 `^CHAPTER\s+\d+$` 过滤
2. `FOOTNOTE_RE = re.compile(r'^\d+\s+[""''"\'a-z]')` 覆盖弯引号和续行
3. `group_by_chapter` 完成分组后**按以下顺序调用**（顺序不可颠倒）：
   - `split_verse_commentary`（纯文本 raw 必须；富文本 raw 可省略但加上无害）
   - `bold_verse_starts`（纯文本 raw 必须；见下方说明）
   - `join_orphan_verse_numbers`
   - `merge_split_paragraphs`
4. 按章节号分组：所有 `## Book N:M-P` section 属于章节 N
5. **禁止**在 `merge_split_paragraphs` 里加 end_char 判断：16 世纪英文注释里，下一块小写开头就是跨页续行，无论上一块末尾是 `.`、`?`、`;` 还是 `)`

### 同一 block 内多节注释合并（两种情形，对应两种修复位置）

**症状**：第 N 节注释末尾和第 N+1 节注释开头在同一段落内，无分行。

**根因**：PyMuPDF 把多个段落（不同节号）提取为一个 block，`is_verse_block` 只检测 block 首 span，内部节号被漏掉。

**情形 A（富文本提取：`extract_block_rich` / `spans_to_md`，节号有 `**N.**` 标记）**

raw.txt 中节号以 `**N.**` 出现。必须**在提取阶段**切分（publish.py 无法区分节号和行内引用中的数字）：

**修复（extract.py）**：在 commentary block 处理中，对 `extract_block_rich` 的输出做按节号切分：

```python
def split_rich_by_verse(rich):
    """Split at **N.** markers that appear after content (not at block start)."""
    parts = re.split(r'(?<=\S)\s+(\*\*\d+\.\*\*)', rich)
    if len(parts) == 1:
        return [rich]
    result = []
    i = 0
    while i < len(parts):
        chunk = parts[i].strip()
        if i + 1 < len(parts) and re.match(r'^\*\*\d+\.\*\*$', parts[i + 1]):
            if chunk:
                result.append(chunk)
            combined = parts[i + 1]
            if i + 2 < len(parts):
                combined += ' ' + parts[i + 2].lstrip()
            result.append(combined.strip())
            i += 3
        else:
            if chunk:
                result.append(chunk)
            i += 1
    return result if result else [rich]
```

在 `process_pdf` 的 commentary 分支中调用：
```python
else:
    rich = extract_block_rich(block)
    if rich.endswith("-"):
        pending_continuation = (pending_continuation or "") + rich[:-1]
    else:
        if pending_continuation:
            rich = pending_continuation + rich
            pending_continuation = None
        for sub in split_rich_by_verse(rich):
            output_blocks.append(sub)
```

**情形 B（纯文本提取：`get_block_text()`，节号无 bold 标记，如平行福音卷二 matthew-en）**

raw.txt 中节号以 `4. Go and relate to John` 形式内嵌在段落中（无 `**`）。**不能在提取阶段切分**（`extract.py` 已不保留格式信息）；**必须在发布阶段**切分。

判别依据：`. N. 大写` 模式——句号结尾后跟节号、再跟大写文字——在 Calvin 注释中唯一出现在节号处；括号引用（`(John 3:29.)`、`(2 Corinthians 11:2,)`）均不匹配此模式。

**修复（publish.py）**：在 `group_by_chapter` 内，`join_orphan_verse_numbers` **之前**调用：

```python
def split_verse_commentary(blocks):
    """将纯文本 block 中内嵌的多节注释拆分为独立段落。
    匹配模式：句号结尾 + 空格 + N. + 大写字母（仅节号处出现此模式）。"""
    result = []
    for block in blocks:
        if block.startswith('##') or block.startswith('<table'):
            result.append(block)
            continue
        parts = re.split(r'(?<=\.) (\d+)\. (?=[A-Z])', block)
        if len(parts) <= 1:
            result.append(block)
            continue
        result.append(parts[0].rstrip())
        i = 1
        while i < len(parts) - 1:
            result.append(f"**{parts[i]}.** {parts[i + 1]}")
            i += 2
    return [b for b in result if b.strip()]

# 在 group_by_chapter 中：
for ch in chapters:
    chapters[ch] = split_verse_commentary(chapters[ch])   # ← 新增，最先执行
    chapters[ch] = join_orphan_verse_numbers(chapters[ch])
    chapters[ch] = merge_split_paragraphs(chapters[ch])
```

**⚠️ 正则安全性**：`(?<=\.) (\d+)\. (?=[A-Z])` 要求节号左侧必须是句号（`.`），右侧必须是大写字母。常见括号引用的反例：`(John 3:29.)` 的 `. ` 后面是 `A`（大写），但 `.` 前面是 `)` 不是 `.`，故不误切；`(1 Peter 2:8.)` 同理；`Matthew 11:1.` 前面是 `:1` 非 `.`，也不误切。

**`bold_verse_starts`（纯文本 raw 独有问题）**

**症状**：经文表格之后，注释段落首行显示为带缩进的列表项，序号错误（如显示 "1." 而非 "17."）。

**根因**：纯文本提取不加 bold 标记，standalone 的注释 block 以 `17. And the seventy returned.` 开头；Kramdown 把行首的 `N. ` 解析为**有序列表第 N 项**，渲染出缩进和错误序号（CSS 重置计数器后显示为 1）。`split_verse_commentary` 只处理段落**中间**内嵌节号，无法处理 block **开头**的 `N. ` 情况。

**修复**：`bold_verse_starts` 把所有以 `N. 大写` 开头的 block 转为 `**N.** 大写`：

```python
def bold_verse_starts(blocks):
    """将 block 开头的 'N. Text' 转为 '**N.** Text'，防止 Kramdown 解析为有序列表。"""
    result = []
    for block in blocks:
        if block.startswith('##') or block.startswith('<table') or block.startswith('**'):
            result.append(block)
            continue
        m = re.match(r'^(\d+)\. ', block)
        if m:
            result.append(f"**{m.group(1)}.** {block[m.end():]}")
        else:
            result.append(block)
    return result
```

必须在 `split_verse_commentary` **之后**、`join_orphan_verse_numbers` **之前**调用，防止被 `join_orphan_verse_numbers` 的 `**N.**` 独立块模式先行处理。

### CCEL 平行福音版式（福音书和谐，如马太卷二）

CCEL 福音书和谐注释（Harmony of the Evangelists）有特殊的**平行福音列**版式，与单列 CCEL 格式完全不同：

| 特征 | 单列 CCEL（使徒行传） | 平行福音 CCEL（马太卷二） |
|------|-------------------|-----------------------|
| 经文版式 | 单列文本 | 2-3 列并排（Matthew/Mark/Luke） |
| 列数 | 1 | 按章节不同，2 列或 3 列 |
| 列标签块 | 无 | 每节前有列标签 block（size 14-17，bold） |
| Block 结构 | 每列独立 block | 多列内容可能在同一个 block 内 |

#### 诊断：区分普通 CCEL 和平行福音 CCEL

```python
# 对 x0 做分布检查，但注意平行福音的 x0 分布有 2-3 个峰
# 峰约在 x0≈74（左列）, x0≈230-274（中列，Mark）, x0≈308-404（右列，Luke）
# 与 Ages 双语（x≈74 英文 + x≈200+ 拉丁）的区别：Ages 的右列起始 x 较小（≈200）
# 平行福音的右列起始 x 较大（≈290+）
```

运行基础诊断后若发现多峰 x0，同时在 `## MATTHEW N:M; MARK N:M; LUKE N:M` 格式标题块旁有 size 14-17 bold 的列标签块，即确认为**平行福音格式**。

#### 三个关键技术坑（已被 matthew-en 验证）

**坑 1：`is_verse_block()` 句号在下一个 span**

部分经节序号（如 `24`）独占一个 span，句号 `.\xa0` 在下一 span 中。匹配 `r'^\d+[.\xa0]'` 会失败。

**修复**：接受纯数字 span：`r'^\d+([.\xa0]|$)'`

```python
def is_verse_block(block):
    span = get_first_span(block)
    if not span: return False
    if not (span.get("flags", 0) & 16): return False  # bold
    size = span.get("size", 0)
    if not (10 <= size <= 14): return False
    t = span["text"].strip()
    return bool(re.match(r'^\d+([.\xa0]|$)', t))
```

**坑 2：`is_col_label_block()` x0 阈值过高**

列标签块（如 `Luke 6:6-10\nMark 3:1-5\nMatthew 12:9-13`）多行时整体 x0 由最左行决定，可能低至 x0≈98。`if block["bbox"][0] < 100: return False` 会漏检，导致列标签被当作注释处理，同时 `in_verse_section` 被错误重置。

**修复**：阈值降至 50：`if block["bbox"][0] < 50: return False`

**坑 3：build_verse_table() 用 block x0 而非 line x0 分列**

PDF 有时将 2-3 列内容提取到同一个 block（block.bbox[0] = 所有行中最小 x0）。用 block x0 分列会把右列内容全部归入左列。

**修复**：必须在 **LINE 级别**（而非 block 级别）用 `line["bbox"][0]` 判断列归属。

**坑 4：commentary block 用 `get_block_text()` 而非 `spans_to_md()` —— bold/italic 丢失**

**症状**：注释段落的节号标题（如 "Matthew 11:20."）应为粗体，经文引用（如 "Then he began to upbraid."）应为斜体，但页面上全部显示为普通文本。

**根因**：`get_block_text()` 只拼接 span 文字，忽略 `flags`（bold/italic）。经文表格使用 line-level x0 分列，代码复杂度高，commentary 部分为了简洁沿用了 `get_block_text()`，导致格式信息在提取阶段永久丢失。

**这是提取阶段的根本性错误**：与发布阶段可以后处理弥补的 bug 不同，格式信息一旦在 extract.py 中丢弃就无法在 publish.py 中恢复。

**修复**：`handle_commentary` 必须接收 block 对象并调用 `spans_to_md(block)`：

```python
def handle_commentary(block):
    nonlocal pending_continuation
    rich = spans_to_md(block)
    rich = re.sub(r'-\s+([a-z])', r'\1', rich)  # merge hyphenated words
    if not rich:
        return
    if rich.endswith('-'):
        pending_continuation = (pending_continuation or '') + rich[:-1]
    else:
        if pending_continuation:
            rich = pending_continuation + rich
            pending_continuation = None
        output_blocks.append(rich)
```

调用处：`handle_commentary(block)`（不再传 `text`）。

同时，publish.py 的处理链改为富文本路径：`split_rich_by_verse` + `join_orphan_verse_numbers` + `merge_split_paragraphs`（移除仅用于纯文本的 `split_verse_commentary` 和 `bold_verse_starts`）。

**⚠️ 通用原则：任何格式的 Calvin 注释提取脚本，commentary block 必须用 `spans_to_md()` 而非 `get_block_text()`**。经文表格复杂不代表注释部分也需要简化——两者用不同函数处理，commentary 始终用富文本。

#### 动态列分割：从列标签 block 提取分割阈值

2 列和 3 列的分割点不能硬编码，必须从列标签 block 的行 x0 动态计算：

```python
def extract_col_info(block):
    """返回 [(label, x0), ...] 按 x0 升序排列"""
    cols = []
    for line in block.get("lines", []):
        lx0 = line["bbox"][0]
        text = "".join(s["text"] for s in line.get("spans", []))
        if text.strip():
            cols.append((text.strip(), lx0))
    return sorted(cols, key=lambda c: c[1])

def compute_col_splits(col_info):
    """从列标签 x0 计算分割阈值（取相邻列的中点）"""
    if len(col_info) < 2:
        return [290]  # fallback
    xs = [x for _, x in col_info]
    return [(xs[i] + xs[i+1]) / 2 for i in range(len(xs) - 1)]

def assign_col(line_x0, splits):
    for i, s in enumerate(splits):
        if line_x0 < s:
            return i
    return len(splits)
```

#### build_verse_table() 完整实现（支持 2-3 列）

```python
def build_verse_table(section_header, verse_blocks, col_info):
    splits = compute_col_splits(col_info)
    n_cols = len(splits) + 1
    col_lines = [[] for _ in range(n_cols)]

    for block in verse_blocks:
        for line in block.get("lines", []):
            line_x0 = line["bbox"][0]
            line_text = "".join(s["text"] for s in line.get("spans", []))
            line_text = re.sub(r'\s+', ' ', line_text.replace('\xa0', ' ')).strip()
            if not line_text:
                continue
            ci = assign_col(line_x0, splits)
            is_verse_start = bool(re.match(r'^\d+\.?\s', line_text))
            col_lines[ci].append((is_verse_start, line_text))

    def lines_to_rows(lines):
        rows, current = [], []
        for is_start, text in lines:
            if current and is_start:
                rows.append(' '.join(current))
                current = [text]
            else:
                current.append(text)
        if current:
            rows.append(' '.join(current))
        return rows

    col_rows = [lines_to_rows(l) for l in col_lines]
    if not any(col_rows): return ''

    max_rows = max(len(r) for r in col_rows)
    for r in col_rows:
        while len(r) < max_rows: r.append('')

    col_labels = [c[0] for c in col_info] if col_info else [''] * n_cols
    html = ['<table class="calvin-scripture">']
    html.append(f'<thead><tr><th colspan="{n_cols}" style="text-align:center">{section_header}</th></tr></thead>')
    if any(col_labels):
        html.append('<thead><tr>' + ''.join(f'<th>{l}</th>' for l in col_labels) + '</tr></thead>')
    html.append('<tbody>')
    for row_idx in range(max_rows):
        cells = [col_rows[ci][row_idx] for ci in range(n_cols)]
        non_empty = sum(1 for c in cells if c)
        if non_empty == 0: continue
        if non_empty == 1 and n_cols > 1:
            for ci, c in enumerate(cells):
                if c:
                    html.append(f'<tr><td colspan="{n_cols}">{c}</td></tr>')
                    break
        else:
            html.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
    html.append('</tbody></table>')
    return '\n'.join(html)
```

#### CSS：支持 2 列和 3 列

```css
/* colspan 标题居中（不限 colspan 数值）*/
.calvin-en-content table.calvin-scripture th[colspan] {
  text-align: center;
  font-size: 15px;
  letter-spacing: 0.03em;
}
/* 非 colspan 的 th（列标签行）和 td 均需 min-width + nowrap */
.calvin-en-content table.calvin-scripture td,
.calvin-en-content table.calvin-scripture th:not([colspan]) {
  min-width: 280px;
  white-space: nowrap;
  vertical-align: top;
}
```

#### 发布脚本：非连续章号（如马太卷二 11-22, 25 章）

章号不连续时，**不能用** `layout: calvin-en-book`（它的 `{% for i in (1..chapters) %}` 假设从 1 开始连续）。需要在 publish.py 中生成包含显式章节链接的 `index.html`：

```python
def write_index(chapter_nums, book_id, book_name, date):
    chapter_links = "\n".join(
        f'        <a href="{{{{ site.baseurl }}}}/calvin/{book_id}/{ch}/" class="list-group-item">Chapter {ch}</a>'
        for ch in sorted(chapter_nums)
    )
    content = f"""---
layout: default
...
---
<div class="list-group">
{chapter_links}
</div>
"""
```

注意 Python f-string 中 `{{{{ ... }}}}` → Liquid `{{ ... }}`。

### CCEL 质检 Checklist

**提取阶段（raw txt）**：
- [ ] `grep "^CHAPTER [0-9]" raw.txt` → 有输出则确认发布脚本已过滤
- [ ] **富文本 raw**：`grep "\*\*[0-9]\+\.\*\*.*\*\*[0-9]\+\.\*\*" raw.txt` → **必须为空**（有则 `split_rich_by_verse` 未生效）
- [ ] **纯文本 raw**：`python3 -c "import re,sys; [print(repr(b[:120])) for b in re.split(r'\n{2,}', open('raw.txt').read()) if not b.startswith('##') and not b.startswith('<table') and len(re.findall(r'(?<=\.) \d+\. [A-Z]', b)) >= 2]"` → **必须为空**（有则 `split_verse_commentary` 未加到发布脚本）
- [ ] 脚注泄漏检查脚本 → **必须为 0**
- [ ] 末尾到达 Index 页前正常停止

**发布阶段（calvin/BOOK-en/）**：
- [ ] 无独立 `CHAPTER N` 行出现在章节内容中（`grep "^CHAPTER" calvin/BOOK-en/*.md`）
- [ ] 随机抽查 3 章，每节注释独立成段，无相邻节号合并
- [ ] **纯文本 raw**：`grep -rn "^\d\+\. [A-Z]" calvin/BOOK-en/*.md | grep -v "^<"` → **必须为空**（有则 `bold_verse_starts` 缺失，行首裸 `N.` 会被 Kramdown 渲染为有序列表）
- [ ] 末章内容完整
- [ ] `## Book N:M-P` 格式的经文标题正确居中显示
