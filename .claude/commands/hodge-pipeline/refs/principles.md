# 全局原则 §0.0–§0.6

每个步骤都必须遵守。违反任何一条 = 必然踩坑。

---

## §0.0 最高原则：以 PDF 原文为唯一依据，禁止猜测

**原文是什么样的，就要在网页上复现出一样的效果。** 双向约束：

**正向**：PDF 里有的视觉效果，必须在网页上还原。
- 经文块有边框 → `<div class="scripture-box">` 带边框
- 经文引用蓝色 → 用对应颜色
- 居中段落 → 居中
- 缩进引文 → blockquote

**反向**：PDF 里没有的视觉效果，不得自创。
- 经文块和注释看起来一样 → 保持原样，**不主动美化**
- 不得因"觉得应该区分"擅自加边框、背景色、缩进

**操作规则**：
- 用户指出有误 → **先读 PDF 对应页**，确认正确格式，再改
- 不得根据"惯例""猜测""推断"决定格式
- 用户否定 A 方案 ≠ B 方案正确——B 方案同样需要 PDF 核实
- 不知 PDF 路径就询问，不要假设

**反例**：
- 用户说右对齐不对 → 没看 PDF 就改成居中 → 实际是左缩进，错两次
- 经文块和注释视觉相同 → 擅自加 `border-left` → PDF 本就相同，被回退

---

## §0.1 圣经引用按「卷名头」分组，不按 `;` 计数

凡涉及 section header / verse 导航 pill / 多列表头 / 跨节合并的引用串：

| 条目形式 | 含义 |
|---|---|
| `Book Ch:V`（卷名开头）| 新卷的引用 |
| `Ch:V`（数字开头，无卷名前缀）| **延续前一卷** |

例：`MATTHEW 5:13-16; MARK 9:49-50; 4:21; LUKE 14:34-35; 8:16; 11:33` → **3 卷**（`4:21` 续 Mark；`8:16` / `11:33` 续 Luke），不是 6。

**规则**：数卷数必须按卷名头出现次数。**绝不能用 `header.count(';') + 1`**。

```python
import re
_BIBLE_REF_RE = re.compile(r'^([A-Z]+[A-Za-z]*)\b')

def split_bible_refs_by_book(header):
    """'BookA Ch:V; Ch:V; BookB Ch:V' → 按卷名分组"""
    parts = [p.strip() for p in header.split(';')]
    groups = []
    for p in parts:
        if _BIBLE_REF_RE.match(p):
            groups.append([p])
        elif groups:
            groups[-1].append(p)
        else:
            groups.append([p])
    return groups
```

`n_books = len(groups)`；列头 = `[ '; '.join(g) for g in groups ]`。

---

## §0.2 防御性过滤内化到 emit 函数，不要散在调用方

**问题**：emit 工件（block/sentinel/HTML）有多条产出路径时，过滤/验证只挂在某条路径 → 其他路径漏检。

例（已踩过）：
- 多列经文 emit 两条路径：① 直接 split → emit_multi_col；② 跨 block 合并 → emit_multi_col
- `cols_look_like_commentary` 先只挂在 ①，commentary 块从 ② 漏进 scripture-box

**正确**：把过滤器塞进 emit 函数自身，调用方只关心成功 / fall through：

```python
def emit_multi_col(cols) -> bool:
    """成功 → True；被过滤 → False"""
    if cols_look_like_commentary(cols):
        return False
    # ... 实际 emit ...
    return True

# 任意调用路径
if cols and emit_multi_col(cols):
    bi += 2; continue
# fall through 自然处理（不依赖调用方记得加过滤）
```

**规则**：
- 「保护性检查」属于产出函数的契约，不写在调用方
- 多调用点共用同一 emit → **先封装 emit 再加调用点**

---

## §0.3 几何信号做语义判断必须搭配内容/样式信号校验

**问题**：单一几何指标（行宽、x0、cx、bbox）判**语义类别**几乎必翻车。同一几何可由多种原因导致，几何不够。

| 几何信号（必要） | 配套内容/样式信号（语义） |
|---|---|
| 行宽超阈值 | span 间是否真有 > 25px 空白；中间 span 是否 bold 数字（节号）；含 italic（注释引语）→ 不是经文 |
| cx 紧贴页心 | lm/rm 是否对称且 > 一定值（区分居中 vs 两端对齐顶满）|
| 每列 ≥ N 行 | 行序列是否按 y 反复跨列（alternation rate）|

**PyMuPDF flag 位字段是金矿**：

| flag | 含义 | 典型用途 |
|---|---|---|
| `& 1` | superscript | 行内脚注引用、节号上标 |
| `& 2` | italic | Calvin 注释里的经文引语标记 |
| `& 16` | bold | 经文节号、卷名加粗 |

**bold 数字 = 节号；sup 数字 = 脚注 ref**——同样数字 span，flag 不同含义完全不同。

**规则**：写 `if line_w > X` 类判定前，先问「同样几何还能由哪些**非目标场景**造成？」每种都列内容/样式排除信号。

---

## §0.4 emit markdown 前必须合并同 style 紧邻 span

**问题**：PyMuPDF 偶尔把同 style 连续文本切成两个 span（如 `Matthew 5:42.` bold 拆成 `Matthew 5:42` + `.`）。每个 span 单独包 `**…**` → `**Matthew 5:42****.**`。

kramdown 渲染为**两个相邻 `<strong>`**：
```html
<strong>Matthew 5:42</strong><strong>.</strong>
```

下游 verse-nav JS 用 `firstElementChild.textContent` 匹配 `^Book Ch:N\.$` 整体——第一个 `<strong>` 缺句点，匹配失败，点击不跳转。matthew1 全书命中 127 处。

**修复**：emit 出口必须 collapse：

```python
result = result.replace('****', '')   # 四星只能由 `**A**` 紧贴 `**B**` 产生
```

`****` 在合法 markdown 中无意义（三星号 `***` 后必有内容字符，不形成纯 4 星）。

**规则**：
- 把 PyMuPDF span 转 markdown 包裹符（`**`/`*`/`***`）的 emit 函数末尾必须合并 abutting 标记
- markdown→HTML 后用 `firstElementChild.textContent` 正则匹配的 JS **强假设首子元素已合并**

---

## §0.5 PDF 引文起讫引号被切成独立 italic span 时必须扩 italic 包整句

**问题**：PDF 中引文的左右引号（`"` / `"` / `'`）常被切成独立 italic span，extract 每段单独包 `*…*`，产出：

```
*"*X*,"*    （两侧都 italic）
*"*X"       （仅 open 带 italic）
```

kramdown 解析失败——`*"*` 两侧 `*` 与引号字符位置导致无法构成有效 emphasis，渲染为字面星号。

**修复**：在 `block_to_markdown` 出口 + `process_section_blocks` body 入口各应用两个正则：

```python
QUOTE_OPEN   = r'["“”\'‘’]'
QUOTE_DOUBLE = r'["“”]'

# Pattern A: 两侧 italic → italic 包整句
re.sub(rf'\*({QUOTE_OPEN})\*([^*]+?)\*([,.;:!?]*{QUOTE_OPEN})\*',
       r'*\1\2\3*', text)
# Pattern B: 仅 open italic → 补 close italic 包整句
re.sub(rf'\*({QUOTE_OPEN})\*([^*]+?{QUOTE_DOUBLE})',
       r'*\1\2*', text)
```

apostrophe `'`/`'` 故意从 Pattern B close 集合排除，避免 `king's` possessive 误截断。

---

## §0.6 多列分簇要容忍噪声/短栏，section_col_layout 锁定后用 fallback 而非放弃

**失败模式**：block 内主要是多栏交替，但夹杂 1–2 行空白 span / `\xa0` / 短跨段，让簇过滤把短栏过滤掉 → 簇数变 1 → 整 block 退化为单栏 fallback → 多栏内容堆成一段。

**典型现场**：ch10 Matt 10:26-31 三栏中，col=2 「灾难块」56 行混入 cols 0+1+2 文本。

**修复原则**：
1. **clustering 前先剥噪声**：line 内全 `\xa0`/纯空白 span 不计入 x0 统计
2. **section_col_layout 锁定时**：簇检测失败仍要按锁定的 x0 slots（来自该 section 第一个成功 block）**强制 span-level 分桶**，不退化为单栏 fallback
3. **dump-to-single-col 是 last resort**：必须 emit warning 让人审计，不静默退化

与 §0.3 互补（§0.3 解决「用什么信号」，§0.6 解决「噪声鲁棒」）。

---

## 整体心法

- 这 7 条都是从踩坑反过来归纳的——每条对应一个具体反例
- 写新代码前如果**说不清这段对应哪条原则**，多半要踩坑
- emit 函数的契约：「输出归一化，下游可假设输入干净」是数据层最小不变量
- 几何信号永远只是必要条件，永远要搭配 PyMuPDF flag 位 / 文本内容信号
