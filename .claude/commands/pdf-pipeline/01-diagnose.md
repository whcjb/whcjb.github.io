# Step 1: PDF 格式诊断

**起手必做。** 不诊断就写脚本，本节就是反例。

---

## 1. 起手必查清单（5 条 yes/no）

填完才能进入下一步：

- [ ] **PDF 路径已知**：用户给了，或我从 `calvin_extract.py` 的 `VOLUMES` dict 查到
- [ ] **格式分类**：跑 diagnose 脚本，得出双峰 / 单峰 / 多峰
- [ ] **已有 volume entry**：在 `VOLUMES` 里找 `format` 字段值
- [ ] **明确目标产物**：raw txt？ 完整发布到 calvin/BOOK-en/？ 仅 preface？仅特定 chapter？
- [ ] **明确踩坑信号**：搜 [anti-patterns.md](refs/anti-patterns.md) 中与 PDF 类型相关的项

---

## 2. 诊断脚本（x0 分布采样）

```python
import fitz, collections
doc = fitz.open("YOUR_PDF_PATH")
xs = collections.Counter()
for i in range(min(10, len(doc)-1), min(20, len(doc))):
    for b in doc[i].get_text("dict")["blocks"]:
        if b["type"] == 0:
            xs[round(b["bbox"][0] / 10) * 10] += 1  # 10px 精度
for x, cnt in sorted(xs.most_common(6)):
    print(f"  x0≈{x:3d}: {cnt:3d} blocks")
doc.close()
```

---

## 3. 判断规则

先看页面元数据 + Ages 指纹，再看 x0 分布：

```python
# Ages 指纹：metadata 含 'AGES'、第一页含 "THE AGES DIGITAL LIBRARY"
# 经节锚点 <NNNNNN>（6 位数字 book+ch+v 编码）
ages_markers = sum(len(re.findall(r'<\d{6}>', doc[i].get_text()))
                   for i in range(min(50, len(doc))))
# > 5 个 → Ages 系列（acts/john/romans/1cor/phil 等）
```

| 信号组合 | 格式 | 入口 / step |
|---|---|---|
| **Ages 指纹 + 410×626 页 + 单峰 x≈30** | **ages_phil 单列**（acts / john / romans / 1cor 等）| [02a-extract-ages.md](02a-extract-ages.md) |
| Ages 指纹 + 双峰 x≈74/220 | **ages_heb / ages_phil 双语全篇**（heb / phil）| [02a-extract-ages.md](02a-extract-ages.md) |
| Ages 指纹 + 单峰 + scripture 区有 2 列 | **ages_phil 双语 scripture-only**（1cor / 2cor）| [02a-extract-ages.md §11](02a-extract-ages.md)（双语 table 路径必须走）|
| 无 Ages 指纹 + 单峰 `x≈74: 90 blocks` | **CCEL 单列**（matthew1 / harmony3）| [02b-extract-ccel.md](02b-extract-ccel.md) |
| 无 Ages 指纹 + 三峰 x≈74/230/310 | **CCEL 平行福音**（matthew old vol 2）| [02c-extract-parallel.md](02c-extract-parallel.md) |
| 单峰 + 章首多列经文 | CCEL Harmony（harmony1/3，含共观平行节）| [02b-extract-ccel.md](02b-extract-ccel.md)，必须开 `centering: True` |
| 无 Ages 指纹 + Quartz producer + 单峰 x≈60 + **楷体 FZKTK 经文** + 27pt 首字 | **中文单语注释**（非加尔文，如 RTF-USA 毕列志箴言）| 独立提取器，见 `scripts/extract_bridges_proverbs.py` + [anti-pattern M3c](refs/anti-patterns.md) |

**判断"双语 scripture-only"**（1cor 踩过）：x0 主峰单一不代表整本单列，因为 Ages
单列 PDF 仍可能在 scripture 段做 2 列布局（英文 / 拉丁文左右排）。必须翻几页
`<NNNNNN>` 锚点后面的内容 sample——左列 + 右列都有 `**N.**` 节号 = 双语。
不查 → 经文块拉丁文丢失。

**Ages 双语 vs 平行福音的区别**：
- Ages：右列起始 `x≈200` 左右（英文 + 拉丁文）
- 平行福音：右列起始 `x≈290+`（Matt + Mark + Luke）

---

## 4. 已注册的 PDF (calvin_extract.py VOLUMES)

| volume | format | PDF | 入口函数 |
|---|---|---|---|
| `matthew1` | `ccel_harmony` | `calvin_matai_make1.pdf` | `extract_ccel_harmony` |
| `harmony2` | `ccel_parallel` | `calvin_matai_make2.pdf` | `extract_ccel_parallel` |
| `harmony3` | `ccel_harmony` | `calvin_matai_make3.pdf` | `extract_ccel_harmony` |
| `acts1` | `ccel_acts` | `calvin_acts1.pdf` | `extract_ccel_acts` |
| `phil` | `ages_phil` | `calvin_filibi.pdf` | `extract_ages_phil` |
| `heb` | `ages_heb` | `calvin_xibolaishu.pdf` | `extract_ages_heb` |
| `john` | `ages_phil` | `CAL_JOHN.pdf` | `extract_ages_phil` |
| `acts` | `ages_phil` | `CAL_ACTS.pdf` | `extract_ages_phil` |
| `romans` | `ages_phil` | `CAL_ROMM.pdf` | `extract_ages_phil` |
| `1cor` | `ages_phil` | `CAL_1COR.pdf` | `extract_ages_phil`（双语 scripture-only，见 02a §11）|

---

## 5. 关键配置字段

每个 VOLUMES entry 必须有：

| 字段 | 含义 | 典型值 |
|---|---|---|
| `format` | 决定 dispatch 入口 | `ccel_harmony` / `ages_phil` 等 |
| `pdf` | 绝对路径 | `'/Users/.../calvin_xxx.pdf'` |
| `out` | raw txt 输出 | `calvin_raw/BOOK/BOOK_raw.txt` |
| `skip_pages` | 跳过的前 N 页（封面 / TOC）| 8–29 视 PDF 而定 |
| `header_y_max` | 页眉 y 阈值 | 55–62 |
| `footnote_size_max` | 脚注字号上限 | 7.5（Ages）/ 9.5（CCEL）|
| `page_num_x_min` | 页码 x 阈值 | 450 |
| `page_w` | 页宽 | 612.0 |
| `body_left` | 正文左边距 | 108.0（CCEL）/ 74.0（Ages）|
| `body_right` | 正文右边距 | 504.0 |
| `centering` | 是否开居中检测（**同时**门控多列检测）| `True` for harmony1/3，`False` for acts |

⚠️ **`centering` 门控陷阱**：`centering: True` 同时打开居中检测 **+** 多列经文检测（`split_block_by_columns` 调用都在 `if cfg.get('centering'):` 内）。harmony3 之前 `centering: False` 导致多列经文表没渲染，是这个耦合的踩坑。

---

## 6. 自动校准 body_left / body_right（不要硬编码）

```python
from collections import Counter

def calibrate_body_margin(doc, max_x=200):
    """采样所有普通块的左边距，众数 + 10px = INDENT_X 阈值"""
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
```

每本新书必跑这个校准，**不要硬编码 INDENT_X=35**。

---

## 7. 自动检测脚注区起始页

```python
def detect_fn_start_page(doc):
    """找含 'FOOTNOTES' H1 标题、且在文档后 40% 位置的页"""
    n = len(doc)
    for i in range(int(n * 0.6), n):
        text = doc[i].get_text()
        if re.search(r'^\s*FOOTNOTES\s*$', text, re.M):
            return i
    return None
```

Ages 格式脚注通常在文档末尾集中存储；CCEL 格式脚注就在每页底部。

---

## 8. 三向对齐分类（重要！判断段落是居中 / 缩进 / 左对齐）

```python
def classify_line_alignment(line_bbox, page_w, body_left, body_right):
    """返回 'centered' / 'left' / 'right' / 'indented'"""
    lx0, _, lx1, _ = line_bbox
    cx = (lx0 + lx1) / 2
    page_cx = page_w / 2
    left_margin = lx0 - body_left
    right_margin = body_right - lx1
    
    # 居中：cx 接近页中 + 两侧均匀
    if abs(cx - page_cx) < 8 and left_margin > 2 and right_margin > 2:
        return 'centered'
    # 缩进引文：左缩进 > 30px
    if left_margin > 30 and right_margin < 30:
        return 'indented'
    # 右对齐：右边距 < 5
    if right_margin < 5 and left_margin > 50:
        return 'right'
    return 'left'
```

**⚠️ 反例**：单看 `cx ≈ page_cx` 就判居中——两端对齐 body 行也会满足！必须配合 `left_margin > 2 AND right_margin > 2`（[principles §0.3](refs/principles.md#03-几何信号做语义判断必须搭配内容样式信号校验)）。

---

## 9. 元素 → 输出对照表

| PDF 元素 | 识别依据 | 输出 |
|---------|---------|---------|
| H1 标题 | 字体 ≥18pt | `# Title` |
| H2 标题 | 字体 14–17pt | `## Title` |
| 正文段落 | 左边距 ≤ body_left+5 | 普通段落 |
| **居中段落** | **块 cx ≈ 页 cx，两侧均匀**| `<p style="text-align:center">text</p>` |
| 缩进引文 | 左边距 > body_left+30 | `> text` (blockquote) |
| 红色斜体引文 | 红色字体 | `<span style="color:#800000">*text*</span>` |
| 行内脚注引用 | 上标小字 | `[^f35]` |
| 经文表格 | 双列区域含表头 | HTML table（见 publish-en） |
| 脚注定义 | 脚注区 `FtN` 开头 | `[^ftn]: text` |
| 分页标记 | 页面边界 | `<!-- PAGE N -->` |

---

## 下一步

诊断完成后：
- CCEL → [02b-extract-ccel.md](02b-extract-ccel.md)
- Ages → [02a-extract-ages.md](02a-extract-ages.md)
- 平行福音 → [02c-extract-parallel.md](02c-extract-parallel.md)
