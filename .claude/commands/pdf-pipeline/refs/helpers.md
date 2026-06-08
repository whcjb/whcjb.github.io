# Helper 函数索引

不要自己写新提取逻辑。先看这里有没有现成的。所有路径相对 `scripts/`。

---

## 1. calvin_extract.py — PDF → raw text

### 1.1 通用（任何 CCEL 格式都用）

| 函数 | 作用 | 关键参数 |
|---|---|---|
| `ccel_spans_to_md(lines, fn_size_max=None)` | spans → markdown，处理 italic/bold/footnote-ref，规范化 `**N.**` 节号 | `fn_size_max`：小于此 font size 的数字 span 视为 `[^N]` 脚注引用 |
| `ccel_fix_hyphenation(text)` | 修复行末断字 `rob-\nbers` → `robbers` | — |
| `_fix_split_italic_quotes(text)` | 引文起讫引号被切独立 italic span 时扩 italic 包整句（§0.5）| — |
| `split_block_by_columns(block, page_mid, col_gap_min=50, expected_slot_x0s=None)` | block 内行按 x0 聚簇 → 多列输出 | `expected_slot_x0s`：section 锁定后传入，强制按这些 x0 切 |
| `split_lines_by_paragraph_indent(lines, body_left, indent_min=10, indent_max=60)` | 按首行缩进切段 | 首行 x0 ∈ [body_left+10, body_left+60] = 新段起 |
| `classify_lines_by_centering(lines, cfg)` | 标记每行是否居中，含开引号前向 promotion | cfg 含 `body_left/body_right/page_w` |

### 1.2 CCEL Calvin Harmony（matthew1, harmony3）

格式特征：单栏 PDF 含居中标题；可能多列经文表；脚注小字号。

| 函数 | 作用 |
|---|---|
| `ccel_harmony_is_running_header(block, cfg)` | 顶端 `THE`/`COMMENTARY` 等运行页眉，按 `header_y_max` + flag bit 2 判断 |
| `ccel_harmony_is_page_number(block, cfg)` | 数字行 + x0 > `page_num_x_min` |
| `ccel_harmony_is_footnote(block, cfg)` | 字号 < `footnote_size_max`（默认 9.5）|
| `parse_ccel_footnote_block(block)` | 脚注块解析为 [(num, text)]，处理 `<num>` 单独行模式 |
| `ccel_harmony_is_section_header(block)` | bold ALL-CAPS `MATTHEW 5:1-12; LUKE 6:20-26` 类标题 |
| `ccel_harmony_is_blue_label(block)` | 蓝色细标题（多列经文表头）|
| `ccel_harmony_is_index_start(block)` | 索引页起始（停止抽取标志）|
| `extract_ccel_harmony(cfg)` | 入口：完整抽取流程 |

**典型用法**（preface / 段落级提取）：

```python
for block in page.get_text('dict')['blocks']:
    if block.get('type', 0) != 0: continue
    if ccel_harmony_is_running_header(b, cfg): continue
    if ccel_harmony_is_page_number(b, cfg): continue
    if ccel_harmony_is_footnote(b, cfg):
        # 收集到 fn_blocks，同页 FN 块按 y 序合并后送给 parse_ccel_footnote_block
        # ↑ 单独 block 解析会把跨 block 的法文 + 英译切碎！
        ...
    else:
        body_lines.extend(b.get('lines', []))

# 段落切分
groups = split_lines_by_paragraph_indent(body_lines, cfg['body_left'])
for grp in groups:
    md = ccel_spans_to_md(grp, fn_size_max=cfg['footnote_size_max'])
    md = ccel_fix_hyphenation(md)
```

### 1.3 CCEL Parallel（matthew old format / acts）

旧版平行福音格式，2-3 列对照。

| 函数前缀 | 函数列表 |
|---|---|
| `ccel_pg_*` | `is_page_header`, `is_page_number`, `is_footnote`, `is_section_header`, `is_col_label`, `extract_col_info`, `is_verse_block`, `is_index_start`, `is_decoration`, `spans_to_md`, `build_verse_table` |
| 入口 | `extract_ccel_parallel(cfg)` |

**⚠️ 关键设计**：
- `ccel_pg_is_footnote` 用**双信号验证**（首 span + 第二 span 字号），不能只看首 span — 否则跨页 verse 续接整页丢失（[§O](anti-patterns.md#o)）
- `ccel_pg_build_verse_table` 接受 `verse_buf` 中**每项是 `(block, words_list, span_size_map, page_idx)` 4-元组**而非单 block — PyMuPDF dict 模式在 narrow cols 会合并跨列 span，必须 word-level 分桶（[§Q](anti-patterns.md#q)）
- `ccel_pg_extract_col_info` 返回 `[(text, x0, x1)]` 3-元组（含 label bbox 右边界）
- word 排序 sort key 必须含 page_idx（[§R](anti-patterns.md#r)）：`key=(page_idx, round(y0), x0)`

### 1.4 CCEL Acts

| 函数前缀 | 函数列表 |
|---|---|
| `ccel_acts_*` | `is_scripture_header`, `is_page_header`, `is_page_number`, `is_footnote`, `is_verse_block`, `extract_block_rich`, `split_rich_by_verse` |
| 入口 | `extract_ccel_acts(cfg)` |

### 1.5 Ages 希伯来书 / 腓立比书 / 约翰福音

| 函数前缀 | 函数列表 |
|---|---|
| `heb_*` | `is_page_header`, `is_page_number`, `is_footnote`, `is_decorative_header`, `is_scripture_header`, `extract_line_rich`, `extract_english_lines`, `build_verse_table`, `split_rich_by_verse` |
| 入口 | `extract_ages_heb(cfg)` |

### 1.6 体力工具

| 函数 | 作用 |
|---|---|
| `get_first_span(block)` | 取首 span（拿 size / flags）|
| `get_block_text(block)` | block 全文 |
| `_make_sub_block(orig, lines)` | 构造子 block（保留 bbox 风格）|
| `write_txt_output(blocks, out_path)` | 写 raw.txt，含 hyphenation 修复 |
| `apply_mojibake_fixes(text, fixes)` | 应用 CCEL 希伯来文乱码修复表 |

---

## 2. harmony_utils.py — raw → publish md

### 2.1 段落处理流水线

| 函数 | 作用 | 顺序 |
|---|---|---|
| `split_rich_by_verse(blocks)` | 同 block 多节合并 → 按 `**N.**` 拆 | 1 |
| `join_orphan_verse_numbers(blocks)` | 孤立 `**N.**` 块附前段 | 2 |
| `merge_split_paragraphs(blocks)` | 段间合并（未结句续接 + 续接信号）| 3 |
| `expand_verse_refs(blocks)` | `**N.**` → `**Book Ch:N.**` 按 section 推断 | 4 |

### 2.2 经文盒子（多列表）

| 函数 | 作用 |
|---|---|
| `_scripture_col_info(block)` | 解析 `<!--SCRIPTURE col=N of=M-->` |
| `_is_scripture_block(block)` | 判定纯经文段（`**N.**` 起首 + 无 italic）|
| `_scripture_box(header, text)` | 渲染 scripture-box HTML（多列时用 `<table>`，单列时段落）|
| `_fnref_to_html(text)` | kramdown 不解析 HTML 块内 `[^N]` → 手工转 `<sup>` |
| `_collect_fn_refs(paras)` | 找段内所有 fn refs |
| `_fn_stub(refs)` | 生成 stub `<p class="scripture-fnref-stub">` 让 kramdown 仍生成 `<li>` 定义 |

### 2.3 入口

```python
def process_section_blocks(header, body):
    """单 section 处理：收 scripture-box + 走 commentary pipeline"""
```

调用方（publish.py）：

```python
from scripts.harmony_utils import process_section_blocks
for header, body in sections:
    blocks = process_section_blocks(header, body)
    out_md += '\n\n'.join(blocks)
```

---

## 3. translate_filibi.py — 中文翻译

```bash
python3 scripts/translate_filibi.py --book BOOK --chapter N --resume
python3 scripts/translate_filibi.py --book BOOK --chapter all
python3 scripts/translate_filibi.py --book BOOK --dry-run
```

**BOOKS 配置**（行 27+）：每本书有 `src`/`cache`/`out`/`system` 四项。`src` 是英文源 dir 或单文件；`cache` 是 md5 → translation 持久化目录；`out` 是中文 raw 输出。

**单段 BATCH=1**；Claude CLI 失败自动重试 3 次（5/15/30s 指数退避）。

---

## 4. 入口配置（calvin_extract.py 行 27+）

```python
VOLUMES = {
    'matthew1':  {'format': 'ccel_harmony',  'pdf': '...', 'centering': True, ...},
    'harmony2':  {'format': 'ccel_parallel', 'pdf': '...', ...},
    'harmony3':  {'format': 'ccel_harmony',  'pdf': '...', 'centering': True, ...},
    'acts1':     {'format': 'ccel_acts',     ...},
    'phil':      {'format': 'ages_phil',     ...},
    'heb':       {'format': 'ages_heb',      ...},
    'john':      {'format': 'ages_phil',     ...},
}
```

`centering: True` **同时门控** 居中检测 + 多列经文检测（split_block_by_columns 调用都在 `if cfg.get('centering'):` 内）。

---

## 不要做的事

- **不要从 page.get_text('dict') 自己写循环**——上面函数已经处理。新写循环 = 漏 italic/bold flag / 漏 footnote / 漏 hyphenation
- **不要复用 ccel_spans_to_md 到 Ages 格式**——Ages 用 `heb_extract_line_rich`
- **不要在 footnote 区调 ccel_spans_to_md** —— footnotes 用 `parse_ccel_footnote_block`（同页 FN 块要先按 y 序合并！）
