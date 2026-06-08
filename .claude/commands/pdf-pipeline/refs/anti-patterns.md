# 反例 Trigger 表

每条都是已踩过的坑。**看到 Trigger 就立刻按 Fix 重做**，不要 debate 自己「应该差不多」。

---

## A. 输出包含原始星号 `*"*X*"*`

**Trigger**：grep 输出含 `*["“”]*` pattern。

**根因**：PDF 中引文起讫引号被切成独立 italic span；emit 时每段单独 `*…*`。

**Fix**：跑 `_fix_split_italic_quotes`（calvin_extract.py 行 255）；同时在 harmony_utils.py `process_section_blocks` body 入口加同款 regex。见 [principles §0.5](principles.md)。

---

## B. 输出含 `****` 四星序列

**Trigger**：`grep -c '\*\*\*\*' OUTPUT > 0`

**根因**：PyMuPDF 把同 style bold span 切成两段（如 `Matthew 5:42` + `.`），emit 后变 `**Matthew 5:42****.**`。

**Fix**：emit 出口 `result.replace('****', '')`。见 [principles §0.4](principles.md)。

**下游影响**：verse-nav JS 用 `firstElementChild.textContent` 匹配 `Book Ch:N\.` 整体——split 后首子元素缺句点，**点击不跳转**。

---

## C. 输出含 `<<<END` / `<<<END1>>>` 标记

**Trigger**：`grep -c '<<<END' OUTPUT > 0`

**根因**：Claude CLI 翻译 BATCH=1 时偶尔吐出分段标记到 front-matter / body 中。

**Fix**：publish 步骤的 transform 必须剥：

```python
text = '\n'.join(l for l in text.splitlines()
                 if not re.match(r'^\s*<<<END\d*>>>\s*$', l))
```

---

## D. 中文 front-matter 键名被翻译（`章：N` / `上一节：N` / `章节：N`）

**Trigger**：`grep -P '^[一-鿿]+[:：]' calvin/BOOK/N.md`

**根因**：Claude 翻译 BATCH=1 时把 front-matter 键也翻成中文。

**Fix**：publish 步骤 transform 必须 sweep 所有变体：

```python
fm_key_fixes = [
    (r'^章[：:]\s*(\d+)$',     r'chapter: \1'),
    (r'^章节[：:]\s*(\d+)$',   r'chapter: \1'),
    (r'^上一节[：:]\s*(\d+)$', r'prev_section: \1'),
    (r'^下一节[：:]\s*(\d+)$', r'next_section: \1'),
    (r'^上一节标签[：:]\s*"',  r'prev_label: "'),
    (r'^下一节标签[：:]\s*"',  r'next_label: "'),
]
```

---

## E. scripture-table 单元格内容混栏（其他列文本漏到本列）

**Trigger**：
- 第一列 `<td>` 内容明显短于其他列；其他列含本应在第一列的节号
- 单元格内文字逻辑跳跃（如「飞鸽走兽……主啊鞭子……」拼接 Mark+Luke 节）

**根因**：catastrophic block — PyMuPDF 把多栏文本合到一个 block，line bbox x0 是 col 0，但 line text 含 cols 1+2 内容。`split_block_by_columns` 看 line-level x0 失败。

**Fix**：
1. 短期：hand-fix 该 section（按 PDF 节号锚点重组三栏，**不是编造**）
2. 长期：在 split_block_by_columns 加 span-level x0 binning fallback（§0.6）

---

## F. scripture-box 内含 commentary 段（注释文本混入经文盒子）

**Trigger**：scripture-box 内出现 `*italic*` 标记（commentary 含 italic 引语，经文不应有）。

**根因**：`_is_scripture_block` 判断逻辑漏边：

```python
# 错：直接看 italic
'*' not in no_verse_nums

# 对：先剥 bold（避免 **,** 这种 bold 标点的星号误算 italic）
no_bold = re.sub(r'\*\*[^*]*\*\*', '', no_verse_nums)
return '*' not in no_bold
```

ch7 Matt 6:5-8 raw 含 `**7.**But praying**,** use not...`（bold 逗号），第一版判定误把整段当 commentary。

---

## G. verse-nav 出现裸数字 pill（如 `17` `18` `42`）

**Trigger**：页面 verse pills 里有不带卷名的数字。

**根因**：scripture-table 单元格 `<td><p><strong>N.</strong>verse text</p></td>` 被 JS Format B 路径当独立 verse 段头识别。当单元格只含 1 个节号时，原 `verseCount > 1` 守门未命中。

**Fix**：verse-nav JS 入口加 `p.closest('td') || p.closest('.scripture-table')` 直接跳过。

---

## H. footnote ref 与 def 数量不匹配

**Trigger**：
```bash
ref_count=$(grep -oE '\[\^[0-9]+\]' OUTPUT | grep -v ':' | sort -u | wc -l)
def_count=$(grep -cE '^\[\^[0-9]+\]:' OUTPUT)
# ref_count 应 == def_count
```

**根因（典型）**：
- 多页 FN 块被 `parse_ccel_footnote_block` 切碎（脚注 8 法文在 p24 block1，英译在 p24 block2）
- 跨页 FN 在某页只有 number 没有 body

**Fix**：同页所有 FN 块按 y 序合并为 virtual block 后再 parse：

```python
page_fn_blocks.sort(key=lambda b: b['bbox'][1])
merged_lines = []
for fb in page_fn_blocks:
    merged_lines.extend(fb.get('lines', []))
parse_ccel_footnote_block({'lines': merged_lines})
```

---

## I. 段落超长（> 1500 字符），明显是多段没拆分

**Trigger**：`awk 'NR>FM{if(length($0)>1500)print NR": "length}' OUTPUT`（FM = front matter 后）

**根因**：没跑 `split_lines_by_paragraph_indent`，把 PyMuPDF 一个 block 当一段。

**Fix**：
```python
groups = split_lines_by_paragraph_indent(body_lines, cfg['body_left'])
for grp in groups:
    md = ccel_spans_to_md(grp, fn_size_max=cfg['footnote_size_max'])
```

---

## J. 输出包含行末断字残留 `rob- bers`

**Trigger**：`grep -P '\b\w+- \w+' OUTPUT | head`

**根因**：没跑 `ccel_fix_hyphenation`。

**Fix**：emit 末尾追加 `text = ccel_fix_hyphenation(text)`。

---

## K. 输出含孤立页码行 / running header

**Trigger**：
- 段落中混入纯数字行
- 出现 `THE` `COMMENTARY` `Paget's Episle Dedicatory to the 1584 Edition` 等运行页眉文本

**根因**：没跑 `ccel_harmony_is_running_header` / `_is_page_number` 过滤。

**Fix**：进 emit 前必须先三件套过滤：
```python
if ccel_harmony_is_running_header(b, cfg): continue
if ccel_harmony_is_page_number(b, cfg): continue
if ccel_harmony_is_footnote(b, cfg):
    fn_blocks.append(b); continue
```

---

## L. 自己写了 `page.get_text('dict')` 循环

**Trigger**：脚本里出现 `doc.get_text('dict')` 而不是调用 `extract_ccel_harmony` 等入口。

**根因**：偷懒走捷径。

**Fix**：去 [helpers.md](helpers.md) 1.1/1.2 找现成函数。**只有现有 helpers 真的不覆盖时**才写新代码——并把新代码加到 calvin_extract.py 而不是 /tmp/。

---

## M. 中文翻译 raw 文件被 chmod 644 而不是 444

**Trigger**：`ls -l calvin_raw/BOOK/zh_chapters/*.md` 显示可写权限。

**根因**：translate_filibi.py 完成后没 chmod 444（skill §raw-preserve 规则）。

**Fix**：每次翻译完成立即 `chmod 444 calvin_raw/BOOK/zh_chapters/N.md`。

---

## M2. navy 引文跨块拆成两段（quote 与 bible-ref 分离）

**Trigger**：网页上某条 `<p style="text-align:center; color:#000080">` 引文段后，bible-ref `(BookName N:M)` 单独成独立段且未居中、未对齐到上段右侧。grep 出现连续 `<p ...color:#000080...>...</p>\s*<span style="color:#000080">[A-Z][a-z]+\s+\d+:\d+\)</span>` 模式。

**根因**：PyMuPDF 把 navy 引文拆成两个 block —— 第一个 [BODY] 块含 quote 文字 + 开括号 `(`，第二个 [FOOTNOTE] 含 Ages 跨引用代码 `<NNNNNN>` + bible book name + verse range + 闭括号 `)`。converter 第一段 emit 为居中 `<p>`，第二段（FOOTNOTE inline cross-ref）试图 fold 进 prior 但被 BLOCK_PREFIXES (`<p `) 拦下。

**Fix**：FOOTNOTE inline cross-ref 路径增加 navy quote special case ——

```python
prior = out[j] if j >= 0 else ''
is_navy_quote_p = bool(re.match(r'\s*<p\s+style="[^"]*color:#000080', prior))
if is_navy_quote_p and prior.rstrip().endswith('</p>'):
    before_close = re.sub(r'\s*</p>\s*$', '', out[j])
    # Peek past trailing </span>/</sty>/whitespace to find last visible char
    peek = re.sub(r'(?:</span>|</sty>|\s)+$', '', before_close.rstrip())
    sep = '' if peek.endswith(('(', '[')) else ' '
    body_styled = body if '<span' in body else f'<span style="color:#000080">{body}</span>'
    out[j] = before_close.rstrip() + sep + body_styled + '</p>'
```

**关键点**：
- peek 末位前必须剥 `</span>/</sty>` 才能看到真实最后字符（否则永远是 `>`）
- 注入 body 若无 `<span>` 须自动包 navy 色，否则文字回到默认色
- `(`/`[` 结尾不加空格，其他加单空格

---

## M3. 全大写短语 / 同 style span 跨块被拆成两段

**Trigger**：网页上 ALL-CAPS 短语（"ON THE SON" / "OF MAN," / 大写引用等）在两段中间被空行拆开；或两个相邻的 `<sty c="X" i="Y">...</sty>` 跨段。

**根因**：PyMuPDF 把跨行的同 style 短语拆成两个 block。converter 的 `_merge_paragraph_fragments` 因 next 段首字符是大写 → `_starts_with_continuation` 返回 False → 不合并。但「上段无标点 + 全大写短语 + 下段全大写起首」就是 PDF 排版换行的强信号。

**Fix**：`_starts_with_continuation` 增加两个 context-aware 信号：

```python
# Signal 1: 同 style 续接（最强）—— prev tail 以 sty 结尾，next head 同 sty
next_sty = re.match(r'^<sty c="([0-9a-fA-F]{6})" i="([01])">', line_for_style)
if next_sty and prev_full:
    prev_last_sty = re.search(
        r'<sty c="([0-9a-fA-F]{6})" i="([01])">[^<]*</sty>\s*$', prev_full)
    if prev_last_sty and prev_last_sty.groups() == next_sty.groups():
        return True

# Signal 2: 全大写短语 wrap —— prev 末尾全大写 + next 首字也全大写
prev_tail_stripped = re.sub(r'</?(?:sty[^>]*|span[^>]*|verse)>', '', prev_tail).rstrip()
if re.search(r'\b[A-Z]{2,}(?:\s+[A-Z]{2,})*\s*$', prev_tail_stripped):
    s_clean = re.sub(r'^(?:<sty[^>]*>|<span[^>]*>|<verse>)+', '', s)
    if re.match(r'^[A-Z]{2,}\b', s_clean):
        return True
```

**关键**：要传 `prev_full`（完整 buf，不只是 tail）给 continuation 检测，因为 sty 开标签可能超过 prev_tail 的 25 字符窗口。

---

## M4. 脚注 def 头部出现字面 `</span>` 文本

**Trigger**：`grep -E "^\[\^f[0-9]+\]: </span>" calvin/BOOK-en/*.md` 出现命中。渲染后页脚显示 `</span> "Pource qu'il est..."` 等开头是字面 HTML close 标签。

**根因 1**：structured.txt 的 `[FOOTNOTE]` 行形如 `<sty c="800000" i="0">ftN</sty> "body"` —— extractor 给 ftN label 上色，integralwraps 进 sty。converter 的 FN_DEF_RE 不匹配（开头是 `<sty>` 不是 `ft`），走 inline cross-ref 路径，body 被原样 emit。

**根因 2**：publish 脚本 `normalize_back_footnotes` 按 `\b[Ff][Tt]\d+\b` boundary split，把 `<span style="...">ftN</span> "body"` 切成 `<span style="...">` 与 `ftN</span> "body"`，body_part 提取后含 `</span> "body"`。

**Fix（两处都要改）**：

```python
# structured_to_md.py FOOTNOTE branch — FN_DEF_RE 测试前先剥 sty wrap：
content_for_fn = re.sub(
    r'^\s*<sty\s[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\s*</sty>\s*',
    r'\1 ', content)
fn_m = FN_DEF_RE.match(content_for_fn)

# publish_<book>_en.py normalize_back_footnotes — 先剥 span 包装：
line = re.sub(r'<span[^>]*>\s*([Ff][Tt]\d+[A-Za-z]?)\s*</span>', r'\1', line)
# 提取 body_part 后再剥前导 </span>/</sty>/whitespace：
body_part = re.sub(r'^(?:</span>|</sty>|\s)+', '', body_part)
```

**通用规则**：FN 检测正则在面对「label 被 inline style 包裹」时要先做 outer-wrap strip；body_part 提取后还要清理可能漏掉的孤儿 HTML close 标签。

---

## M5. 脚注 body 续接段散落在章节中部（"这些内容是哪里来的"）

**Trigger**：章节中部出现孤儿段落（"signifies Grace.", "*Jehohannan*, the reader may consult...", "illustrated in the *Institutes*...", "WHAT WAS MADE was in him life..."）—— 看起来像背景音乐插播。grep 命中诸如 `^signifies Grace\.$` / `^disoyent` / `^illustrated in` 等独立行。

**根因**：Ages PDF 后部 footnote section 中，每个 fn def 经常跨多个 PyMuPDF block：

```
[FOOTNOTE] <sty>ftN</sty> "first line of fn body"
[BODY]   "continuation rest of fn body"
[CENTERED] "centered continuation (e.g. WHAT WAS MADE...)"
[FOOTNOTE] <sty>ft<N+1></sty> ...
```

converter 把每个 `[BODY]` / `[CENTERED]` 当独立段 emit，孤儿段落散落在 ch.md 文件中（位置取决于 publish 脚本如何处理 fn section）。即使紧跟 `[^fN]:` 之后，kramdown 也不认为这些是 fn 续接（kramdown 续接需要四空格缩进或同行连续，不能跨空行）。

**Fix**：converter 加 `pending_fn_idx` 状态机：

```python
pending_fn_idx: int | None = None

# emit fn def 时：
out.append(f'[^{label}]: {body}')
out.append('')
pending_fn_idx = len(out) - 2

# BODY 分支首段（在 navy/scripture-passage 检测之前）：
if pending_fn_idx is not None:
    cont_body = format_inline(content)
    cont_body = apply_verse_styling(cont_body)
    cont_body = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cont_body)
    cont_body = re.sub(r'\s+', ' ', cont_body).strip()
    if cont_body:
        out[pending_fn_idx] = out[pending_fn_idx].rstrip() + ' ' + cont_body
    i += 1
    continue

# CENTERED 分支同理（在 in_scripture 检测之前）

# 清除状态：
# H1 / CENTERED_H1 / CENTERED_H2 / 下一个 fn def 时 pending_fn_idx = None
```

**通用规则**：Ages PDF 后部 footnote def 跨 PyMuPDF block 是常态（fn 长则跨多块）。任何 emit 完 `[^fN]:` 后必须 arm 续接状态机，把后续 BODY/CENTERED 续接合并；只有遇到下一个 fn def 或章节标题才结束。

---

## M5b. 章节末出现 "(Acts 6:5;)" 类 orphan（fn def 中 inline cross-ref 没合并）

**Trigger**：章节末或中段出现 "Acts 6:5;) FULL Acts 6:8;)..." 类似的孤儿段，源于后部 fn def 含**多个 inline bible cross-ref**。grep `^[A-Z][a-z]+\s+\d+:\d+[;,]\)` 或 `^[^*\s].*Acts 6:5` 命中。

**根因**：Ages 后部 fn def 经常 body 含多个 inline bible 引用，PyMuPDF 把每个 `<NNNNNN>BookN:M` 切成独立 `[FOOTNOTE]` 块（开头是 `<NNNNNN>` 不是 `ftN`，FN_DEF_RE 不匹配）。FOOTNOTE inline cross-ref 分支检测 `out[j]` 是否以 BLOCK_PREFIXES 开头时，`'[^'` 在列表中 → prior 的 `[^fN]:` 被拒 → 当前 inline ref 单独 emit。

**Fix**：FOOTNOTE inline cross-ref 分支首先检查 `pending_fn_idx`（§M5 已 arm），若有则 append 到 pending fn 行，与 BODY/CENTERED 续接逻辑一致：

```python
else:  # inline cross-ref branch
    body = format_inline(content)
    body = apply_verse_styling(body, red=in_commentary_section)
    # 优先：在后部 fn def 中（pending_fn_idx armed），合进 fn 行
    if pending_fn_idx is not None:
        body_clean = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', body)
        body_clean = re.sub(r'\s+', ' ', body_clean).strip()
        if body_clean:
            peek = re.sub(r'(?:</span>|</sty>|\s)+$', '', out[pending_fn_idx].rstrip())
            sep = '' if peek.endswith(('(', '[')) else ' '
            out[pending_fn_idx] = out[pending_fn_idx].rstrip() + sep + body_clean
        i += 1
        continue
    # 否则按原逻辑 fold into preceding paragraph
```

**通用规则**：`pending_fn_idx` 续接状态必须 **同时覆盖** BODY/CENTERED/FOOTNOTE-inline-cross-ref 三种 tag。任何在 fn def 之后 emit 的非新-fn-def 内容都是续接，必须 append 到 pending fn。

---

## M6. 章末出现 "CHAPTER N" 居中标记（PDF 没有这内容）

**Trigger**：章节最末显示一个孤立的 "CHAPTER N" 居中标题，PDF 原文该位置无此标记。grep `<p class="title-block-h2"[^>]*>CHAPTER\s+\d+` 在章节文件中命中。

**根因**：Ages PDF 后部脚注 section 每页用 "CHAPTER N" 作为页眉（**深绿 #006411**，区别于真正章节头 H1 的**蓝色 #0000d4**）。structured.txt 出现 `[CENTERED_H2] <sty c="006411" i="0">CHAPTER N</sty>`，converter 默认 emit 为 `<p class="title-block-h2">CHAPTER N</p>`。publish 脚本 `collect_all_definitions` 的终止符不含 `<p`，导致这一行被前一个 fn def 当 continuation 吞掉，进而被 ch1（或上一章）body 引用 fn 时一起拖入章末。

**Fix**：converter `CENTERED_H1` / `CENTERED_H2` 分支起始处增加 SKIP 规则——若内容 strip sty/Ages 后是 `^CHAPTER \d+\s*$`，直接丢弃不 emit：

```python
elif tag in ('CENTERED_H1', 'CENTERED_H2'):
    test_text = re.sub(r'</?(?:verse|sty[^>]*)>', '', content)
    test_text = re.sub(r'<\d{6,7}>', '', test_text).strip()
    if re.match(r'^CHAPTER\s+\d+\s*$', test_text):
        pending_fn_idx = None
        i += 1
        continue
    # ... 原 emit 逻辑
```

**通用规则**：PDF 内部排版页眉（"CHAPTER N" 在后部脚注页、装饰短标题等）**永远不该 emit 为内容**。任何 CENTERED_Hx 在 strip 后等于已存在 H1 章节标题文本的，必须 SKIP。

---

## M7. PDF outline 子条目（`1./2./3.` 等）顶格无缩进

**Trigger**：preface 类页面有 outline 结构 —— 顶级 `I./II./III.` 顶格红色，子条目 `1./2./3.` PDF 中明显缩进（约 18px）；网页输出所有条目顶格平铺，子条目无缩进。

**根因**：PDF 子条目 block_lm ≈ 44（vs body_lm ≈ 26），是排版上的「缩进列表项」语义。extractor 默认按 BODY 输出，丢失 lm 信息。Worse: PDF 子条目 lm/rm 经常对称（lm=44 rm=45），被 `is_centered_block` 误判为居中标题 → 第一条 emit 为 `<p style="text-align:center">`。

**Fix（双管齐下）**：

```python
# extractor: 加 INDENT tag，双触发：列表项 OR 窄块
block_lm = block['bbox'][0]
block_w_local = block['bbox'][2] - block['bbox'][0]
is_outline_item = bool(re.match(r'^\s*[IVX]+\.\s|^\s*\d+\.\s|^\s*[liI]\.\s', block_text_preview))
is_narrow_indented = block_w_local < page_w * 0.55  # 短签名行 "J. O." / "W.P. AUCHTERARDER"
is_indented_subitem = (
    block_lm >= 35
    and not is_centered_block
    and line_class == 'BODY'
    and rm > 20
    and (is_outline_item or is_narrow_indented)
)
if is_indented_subitem:
    line_class = 'INDENT'

# is_centered_block 加内容 guard：起首是 numbered/Roman list item 永不算居中
starts_with_list_item = bool(re.match(r'^\s*[IVX]+\.\s|^\s*\d+\.\s', block_text_preview))
is_centered_block = is_centered_block_geom and not ends_with_continuation and not starts_with_list_item

# converter [INDENT] 分支 — 必须 markdown="1" 让 kramdown 展开 inline italic/fn
elif tag == 'INDENT':
    pending_fn_idx = None
    body = format_inline(content)
    body = apply_verse_styling(body)
    body = bold_leading_verse_num(body)
    out.append(f'<p style="margin-left:2em;" markdown="1">{body}</p>')
```

**关键**：
- `<p ` 起首在 BLOCK_PREFIXES 中，自动阻断 `_merge_paragraph_fragments`，避免子条目被合到上一段
- `markdown="1"` 必加（否则 `*J. O.*` 在 `<p>` 内显示为字面 `*J. O.*`，不渲染为 `<em>`）
- 双触发：列表项 (`1./2./IVX./l.`) **或**窄块（`block_w < 55% page_w`）— 后者覆盖签名行如 "J. O." (w=23)

---

## M8. PDF 字体把数字 "1" 渲成字母 "l"/"I"/"i"

**Trigger**：PDF outline 子条目应该是 `1.` `2.` `3.`，但提取出 `l.` `2.` `3.` — 第一项的 "1" 被识别为小写字母 L（或大写 I 或小写 i）。

**根因**：PDF 某些字体（特别是 Symbol 或老式衬线）数字 "1" 的 glyph 与字母 L 几乎相同。PyMuPDF 按字符编码取，字体里"1"被映射到 L → 提取结果是 L。

**Fix**：任何处理"数字 N. ..."模式的正则**必须同时接受**这些字母变体：

```python
# 顺序：digits, Roman numerals (IVX), 单字母 L/I/i
re.match(r'^\s*\d+\.\s|^\s*[IVX]+\.\s|^\s*[liI]\.\s', text)

# 渲染时如确认是数字 1 的 misread，可恢复：
text = re.sub(r'^([liI])\.\s', r'1.\s', text)  # 仅在 outline 上下文中
```

不需要修复显示文本本身（让 "l. Election" 保持原文就好），但**识别逻辑**必须接受这种变体。

---

## M9. 双语 Ages PDF（Romans/1Cor 等）的 scripture 块如何渲染

**两种方案，按用户/书的偏好选**：

### 方案 A：双语 `<table class="calvin-scripture">`（左英右拉）
- 适用：希望忠实还原 PDF 双栏视觉的书卷
- extractor 在 bilingual block 内按 x0 分流 → emit `[TABLE_LEFT]` / `[TABLE_RIGHT]`
- converter 已有 TABLE_LEFT/RIGHT 渲染为 `<table>`

### 方案 B：单列 `<div class="scripture-box">`（仅英文，丢拉丁）
- 适用：用户偏好 john 同款视觉风格
- extractor scripture-mode 加 buffer，跨多个 PyMuPDF block 累积**仅** x<200 的英文 lines
- 累积时按行末连字符 `-` glue（无空格 join）
- exit scripture-mode（遇全宽 commentary block）或下一个 section header → flush 为单 `[BODY]`
- converter scripture-section 检测识别为单段经文 → 出 scripture-box

**关键代码（方案 B）**：

```python
# extractor 状态：
scripture_buffer = []

def flush_scripture_buffer():
    nonlocal scripture_buffer
    if scripture_buffer:
        joined = ' '.join(scripture_buffer)
        output_lines.append(f'[BODY] {joined}')
        scripture_buffer = []

# scripture-mode 内 (bilingual or narrow block)：
for ln in line_lefts:  # x < LATIN_X_MIN only
    txt = _render_spans_with_italic(ln['spans']).rstrip()
    if not txt.strip(): continue
    if scripture_buffer and scripture_buffer[-1].endswith('-'):
        scripture_buffer[-1] = scripture_buffer[-1][:-1] + txt.lstrip()
    else:
        scripture_buffer.append(txt)

# 进入新 section header / 退出 mode / 页末 → flush_scripture_buffer()
```

**重要**：converter `H2` 分支也要触发 scripture-box 状态机（之前只有 FOOTNOTE 分支会触发；Romans extractor 用 H2 直接标 section header）：

```python
elif tag == 'H2':
    line_for_sec = re.sub(r'</?sty(?:\s[^>]*)?>', '', content)
    sec_h2 = SCRIPTURE_SECTION_RE.match(line_for_sec.strip())
    if sec_h2:
        # ... same scripture-mode init as FOOTNOTE branch ...
        in_scripture = True
        scripture_ref = _build_ref_banner(...)
    else:
        out.append(f'## {cleaned}')
```

---

## M10. PDF 章节标题尾随脚注 ref（"CHAPTER 15 f432"）

**Trigger**：某章被错误降级为 CENTERED_H1，publish 时拆不出，章节缺失；或 publish 阶段 `find_chapter_starts` regex 不匹配，章节直接被跳过。

**根因**：PDF 有时给章节标题加脚注 ref（如 ROMANS CHAPTER 15 后跟 ` f432`），导致：
- extractor 的 `is_chapter_h1` regex `^CHAPTER\s+\d+\s*$` 不匹配（尾部有 ` f432`）→ 降级 H1
- 即使 H1 出来了，markdown 形如 `# CHAPTER 15 [^f432]`，publish 的 `find_chapter_starts` regex `^# CHAPTER (\d+)\s*$` 也不匹配

**Fix**（两端都要改）：

```python
# extractor: is_chapter_h1 检测前剥脚注尾巴
stripped_text_no_fn = re.sub(r'\s+f\d+[A-Za-z]?\s*$', '', stripped_text).strip()
is_chapter_h1 = bool(re.match(r'^CHAPTER\s+\d+\s*$', stripped_text_no_fn))

# publish 脚本: find_chapter_starts 容忍尾随 [^fN] ref
re.match(r'^# CHAPTER (\d+)(?:\s+\[\^f\d+[A-Za-z]?\])?\s*$', line)
```

---

## M12. CENTERED_H1/H2 emit 必须保留 `<sty>` 颜色 + 加 `markdown="1"`

**Trigger**：扉页 / 题献页大字标题在 PDF 是彩色（蓝 #0000d4 / 深绿 #006411 等），网页输出灰白默认色；或者标题内 `[^fN]` 字面残留没渲染为上标。

**根因**：CENTERED_H1/H2 emit 代码错误顺序——先 `re.sub(r'</?(?:verse|sty[^>]*)>', '', cleaned)` 剥掉 `<sty>` 然后才 emit，颜色信息丢失。且 `<p>` 包装没有 `markdown="1"`，kramdown 不展开内部的 `[^fN]` / `*italic*` / `**bold**`。

**Fix**：

```python
elif tag in ('CENTERED_H1', 'CENTERED_H2'):
    # ... CHAPTER N skip check first ...
    pending_fn_idx = None
    cleaned = collapse_spaced_caps(format_inline(content))
    cleaned = apply_verse_styling(cleaned)  # ← 必须：<sty> → <span style="color:#...">
    cleaned = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cleaned)  # 仅剥剩余空标签
    if cleaned.strip():
        size_class = 'title-block-h1' if tag == 'CENTERED_H1' else 'title-block-h2'
        font_size = '22px' if tag == 'CENTERED_H1' else '16px'
        out.append('')
        out.append(f'<p class="{size_class}" style="text-align:center; font-size:{font_size}; font-weight:bold; margin:18px 0 12px;" markdown="1">{cleaned}</p>')
```

**关键**：
- `apply_verse_styling` 在 `re.sub` 剥 sty 之前调用（颜色信息先转 `<span>`，剥的是空标签）
- `markdown="1"` 让 kramdown 展开 `[^fN]` 等 inline markdown

通用规则：**任何 emit `<p ...>` 包装内容（无论 CENTERED / INDENT / 其它）都要 `markdown="1"`**——否则 kramdown 把整个 `<p>` 当 HTML 块跳过 inline 解析。

---

## M13. `collapse_spaced_caps` 第二趟必须排除 'A'/'I' 单字母英文词

**Trigger**：标题或居中段含 "A MAN" 被错合并为 "AMAN"；"I AM" → "IAM"。

**根因**：第二趟正则 `\b([A-Z]) ([A-Z]+)\b` 把 single-cap + multi-cap 都视为 spaced-caps（PDF 装饰用法），但 "A" / "I" 在英文中是合法单字母词，应保留为词间空格。

**Fix**：

```python
# 加负向先行 (?![AI]\b) 排除 'A'/'I' 单字母词
text = re.sub(r"(?<!['‘’])\b(?![AI]\b)([A-Z]) ([A-Z]+)\b", r'\1\2', text)
```

**注意**：边缘 case 仍可能有问题（如 PDF small-caps 形式 "I N THE BEGINNING" 应该是 "IN THE BEGINNING"——但因 `I` 被排除，"N THE" 被合并为 "NTHE"）。这种 case 罕见，暂时接受。

---

## M14. 全斜体缩进引文段被误判为 CENTERED（斜体丢失）

**Trigger**：PDF 中整段斜体的缩进引文段（如 "The subject then of these chapters..."），网页输出非斜体且居中。

**根因**：PDF 这种 citation/quote 段 lm/rm 经常对称（lm=44 rm=50，|lm-rm|=6 < 8），被 `is_centered_block_geom` 判中。CENTERED emit 时 `re.sub(剥 sty)` 在 apply_verse_styling 之前调用，斜体（`<sty c="000000" i="1">`）信息丢失。

**Fix（两端）**：

```python
# extractor: 加 is_all_italic 检测
total_chars = 0
italic_chars = 0
for line in block['lines']:
    for s in line['spans']:
        t = s['text'].strip()
        if not t: continue
        total_chars += len(t)
        if s['flags'] & 2:
            italic_chars += len(t)
is_all_italic = total_chars > 50 and italic_chars / total_chars > 0.9

# is_centered_block 加 guard：is_all_italic 不算居中
is_centered_block = is_centered_block_geom and not ends_with_continuation \
                    and not starts_with_list_item and not is_all_italic

# INDENT 检测加第三触发
is_indented_subitem = (
    block_lm >= 35 and not is_centered_block and line_class == 'BODY' and rm > 20
    and (is_outline_item or is_narrow_indented or is_all_italic)
)

# converter CENTERED 分支也要 apply_verse_styling + markdown="1"
elif tag == 'CENTERED':
    cleaned = collapse_spaced_caps(format_inline(content))
    cleaned = apply_verse_styling(cleaned)  # 保留斜体/颜色
    cleaned = re.sub(r'</?(?:verse|sty(?:\s[^>]*)?)>', '', cleaned)
    out.append(f'<p style="text-align:center" markdown="1">{cleaned}</p>')
```

**通用规则**：**任何 emit `<p>` 包装前**调用顺序必须是「先 `apply_verse_styling` 转 `<sty>` → `<span>`，再 `re.sub` 剥剩余空 sty/verse 标签」。颠倒顺序就丢颜色/斜体。

---

## M15. 右对齐窄 byline / 题献落款（PDF lm>>rm）

**Trigger**：PDF 扉页或题献页有窄行 byline / 落款（如 "by John Calvin" / "Yours respectfully, J. Smith"）PDF 排版在页面右侧（lm 大、rm 小），网页输出左对齐。

**根因**：单凭 `lm >= 35 + narrow + non-centered` 触发 INDENT 会把右对齐 byline 当左缩进列表项，输出 `margin-left:2em`（位置错）。需要识别"右偏"几何：lm > 2*rm。

**Fix**：extractor 加 `RIGHT` tag，**优先级在 INDENT 之前**：

```python
is_right_aligned = (
    block_lm > 100  # well past page center
    and lm > rm * 1.5
    and block_w_local < page_w * 0.5
    and not is_centered_block
    and line_class == 'BODY'
)
if is_right_aligned:
    line_class = 'RIGHT'
# else if outline/narrow/all-italic → INDENT

# converter RIGHT 分支
elif tag == 'RIGHT':
    pending_fn_idx = None
    body = format_inline(content)
    body = apply_verse_styling(body)
    out.append(f'<p style="text-align:right;" markdown="1">{body}</p>')
```

PDF byline 类典型几何（Romans p0 "by John Calvin"）：
- `x=278-350 w=73 lm=278 rm=60 sym=218 sz=12 fl=6(italic)`

---

## M16. `_starts_with_continuation` verse-num 正则 必须接受 `**N.**` bold 形式

**Trigger**：同章 verse 5 / verse 12 commentary 段被合到 verse 4 / verse 11 段尾，形如 `... "He was crucified." [^f18] **5.** *To whom be glory*. By this sudden...` 单行连续，不换段。

**根因**：`_starts_with_continuation` 检查 next 段是否以 verse-num 起首：

```python
if c.isdigit() and not re.match(r'^\d+\.\s', s):  # ❌ 要求 \d+\. 紧跟 \s
    return True  # 数字开头但不是 verse-num → 续接
```

但实际 markdown 形式是 `**N.** ` (bold-wrapped)。我的代码 strip 前导 `\*+\s+` 后 `s = '5.** *To whom...'`。`^\d+\.\s` 不匹配（`.` 后是 `*` 不是 `\s`）→ 误判为续接（普通数字开头）→ merge 到上段。

**Fix**：正则改为 `^\d+\.\**\s` 接受任意 `**` 包裹：

```python
if c.isdigit() and not re.match(r'^\d+\.\**\s', s):
    return True
```

**通用规则**：任何"verse-num 检测正则"都要同时接受 raw `N. ` 和 bolded `N.** ` 两种形式（实际产物是 bold 包裹的）。

---

## M17. PyMuPDF 上标小字提取丢数字（PDF 源 bug，非本管线问题）

**Trigger**：注释段中本应是 `[^fN]` 上标 fn ref，输出残留**孤立红色 `f`**（没数字）。grep 出现 `<span[^>]*color:#800000[^>]*>f</span>` 类（单字符）。

**根因**：某些 PDF 字体的上标 fn ref（如 "f19"）用 ligature 渲染，PyMuPDF 提取时只拿到 `f` 字符，数字 `19` 丢失。这是 **PDF 源数据/字体问题**，无法在 PyMuPDF 层修复。

**当前对策**：留作已知 SEV-1 残留，不阻断发布。下游可加 fail-fast 警告：

```bash
grep -n '<span[^>]*color:#800000[^>]*>f</span>' calvin/BOOK-en/*.md
# 命中时报警：可能是 PyMuPDF 提取丢数字的 orphan f
```

**可选 fix（未实现）**：扫描 fn def 序列找缺号位（如 def 有 f18 / f20 但缺 f19）+ 体内出现孤立 `<span color:#800000>f</span>` → 推断是 f19，回填 ref + 用 PDF 文本无关方法（如打 OCR）寻找 missing def。

---

## M18. PDF 后部"CALVIN'S VERSION"重译附录污染最后章节（500+ 行垃圾）

**Trigger**：最后一章 .md 文件远大于其他章节（如 ch6 = 123 KB vs ch1 = 60 KB），尾部包含 `END OF THE COMMENTARIES`、`A TRANSLATION OF CALVIN'S VERSION`、整本 Eph 1-6 双语经文重译、独立的 `TRANSLATION FOOTNOTES` section。

**根因**：某些 Ages PDF（Ephesians 等）在主体注释 + 真正 FOOTNOTES def section 之间，插入一段"CALVIN'S VERSION"双语重译。结构如下：

```
[main body ch1-6] ... [END OF THE COMMENTARIES] ... 
[CALVIN'S VERSION re-translation Eph 1-6, 双语 ~300 行] 
[FOOTNOTES heading] ... [^f1]: ... [^f132]: 
```

publisher 默认按 `# CHAPTER N` 分章，最后一章吞下从 ch6 起一直到 file end 的所有内容 → 包括 END + appendix + FOOTNOTES。

**Fix（关键：选择性 excise，不要全切）**：

```python
def excise_translation_appendix(lines: list[str]) -> list[str]:
    """切除 END..FOOTNOTES 之间的 translation appendix，保留 FOOTNOTES def section。"""
    end_idx = fn_idx = None
    for i, line in enumerate(lines):
        t = re.sub(r'<[^>]+>', '', line).strip()
        if end_idx is None and re.search(r'END OF THE COMMENTARIES', t, re.I):
            end_idx = i
        elif end_idx is not None and re.match(r'^\s*(?:#\s+)?FOOTNOTES\s*$', t, re.I):
            fn_idx = i
            break
    if end_idx is None:
        return lines  # no appendix
    if fn_idx is None:
        return lines[:end_idx]  # cut everything after END if no FOOTNOTES heading
    return lines[:end_idx] + lines[fn_idx:]  # keep FOOTNOTES def section
```

**通用规则**：
- `appendix_start` (END marker) **必须** 在 `collect_all_definitions` 之前 excise
- **绝不要**直接 `lines = lines[:end_idx]`（会把合法 FOOTNOTES def section 也丢）
- excise 之后 publisher 正常工作；ch6.md 由 78 KB 降到 49 KB

---

## M19. 跨段冠词/介词后大写词应合并（"...2. The | Gentiles were 'aliens'..."）

**Trigger**：PDF 一句话被切成两段，prev 段以 `The` / `A` / `An` / `Of` 等冠词/介词结尾（无标点），next 段大写起首（如专有名词）。

**根因**：`_starts_with_continuation` 原检查 `\b(?:and|or|but|nor|for|yet|so)\s*$` 只覆盖连词。Calvin 注释中常见"...2. The Gentiles were 'aliens'..."这种"冠词在末尾断"的情况（PyMuPDF block 边界恰在冠词后）。

**Fix**：

```python
# Conjunction + capitalized continuation (既有)
if re.search(r'\b(?:and|or|but|nor|for|yet|so)\s*$', prev_tail):
    if c.isupper(): return True
# Article / preposition + capitalized continuation (新增)
if re.search(r'\b(?:The|A|An|Of|In|On|At|To|For|With|By|From|Through)\s*$', prev_tail):
    return True
```

注意是 `\bThe\s*$` 不是简单 `the\s*$`——需要大写形式（PDF 中跨行后第二段总以大写起首，第一段尾词遵循"原句词形"，所以大写 `The/A/An`）。

---

## M20. `_build_ref_banner` 正则必须接受 title-case 卷名（不只全大写）

**Trigger**：scripture-box 顶部 ref banner 显示为纯文本 `<p class="scripture-ref">Colossians 1:1-8</p>`，缺失 `<span class="ages-code">` / `book-name` / `verse-range` 三段 span。前端样式 (small-caps、暗红 Ages 代码) 无法应用。

**根因**：`_build_ref_banner` 解析 `BOOK Ch:V-V'` 正则只接受全大写卷名：

```python
# ❌ 只匹配 "JOHN 1:1-5" 不匹配 "Colossians 1:1-8"
m = re.match(r'^([A-Z][A-Z\s]*?)\s+(\d+:\d+(?:[-,]\d+)?)\s*$', book_verse)
```

PDF section header 形式因书而异：
- John PDF：`<430101>J OHN 1:1-5` (small-caps 全大写)
- Colossians PDF：`<510101>Colossians 1:1-8` (title case)
- 1 Corinthians PDF：`<460101>1 Corinthians 1:1-3` (含数字前缀 + title case)

**Fix**：

```python
m = re.match(
    r'^([1-3]?\s*[A-Z][A-Za-z\s]*?)\s+(\d+:\d+(?:[-,]\d+)?)\s*$',
    book_verse,
)
```

- `[1-3]?\s*` — 接受 "1 Corinthians" / "2 Thessalonians" / "3 John" 前缀
- `[A-Z][A-Za-z\s]*?` — 首字大写 + 后续 mixed case + 空格

---

## M21. `excise_translation_appendix` 必须识别 HTML-wrapped FOOTNOTES heading

**Trigger**：审计发现最后一章 .md 末尾还残留 `END OF THE COMMENTARY` + `<p class="title-block-h1">FOOTNOTES</p>` + `<p class="title-block-h2">ARGUMENT</p>` + 多个空白 `<!-- PAGE -->` markers。

**根因**：M18 修复时正则只匹配 markdown `# FOOTNOTES` heading：

```python
# ❌ 不匹配 HTML wrapper
_FOOTNOTES_HEADING_RE = re.compile(r'^\s*(?:#\s+)?FOOTNOTES\s*$', re.IGNORECASE)
```

但 PDF FOOTNOTES 大字标题被 emit 成 `<p class="title-block-h1">...<span>FOOTNOTES</span></p>` （CENTERED_H1 路径），不是 markdown H1。

**Fix（双管齐下）**：

1. 正则加 HTML wrapper 形式：

```python
_FOOTNOTES_HEADING_RE = re.compile(
    r'^\s*(?:#\s+FOOTNOTES\s*$|<p[^>]*>\s*(?:<span[^>]*>\s*)?FOOTNOTES\s*(?:</span>\s*)?</p>\s*$|FOOTNOTES\s*$)',
    re.IGNORECASE,
)
```

2. 接受 "END OF THE COMMENTARY" 单数也接受复数 "COMMENTARIES"：

```python
_APPENDIX_END_RE = re.compile(r'END OF THE COMMENTAR(?:Y|IES)', re.IGNORECASE)
```

3. 切除范围扩展到**第一个 `[^fN]:` def**（避免 FOOTNOTES heading 之后的空白 PAGE markers / ARGUMENT 子标题等被保留）：

```python
fn_def_start = None
search_start = (fn_idx + 1) if fn_idx is not None else end_idx + 1
for i in range(search_start, len(lines)):
    if re.match(r'^\[\^f\d+[A-Za-z]?\]:', lines[i]):
        fn_def_start = i
        break
return lines[:end_idx] + lines[fn_def_start:]
```

---

## M11. 添加新书继承现有 PDF 样式：CSS 用逗号选择器

**Trigger**：新书（如 romans-en / galatians-en）需要复用 john-en 的 PDF-faithful scripture-box 样式。

**Fix**：在 `_layouts/calvin-en.html` 的 `.scripture-box` CSS 规则上把新 book-id 作为额外选择器**逗号扩展**——**每条 CSS 规则的每个选择器都完整路径到 `.scripture-box`**：

```css
.calvin-en-content[data-book="john-en"] .scripture-box,
.calvin-en-content[data-book="romans-en"] .scripture-box,
.calvin-en-content[data-book="galatians-en"] .scripture-box {
  border: 3px double #1d28e0;
  background: #fffce8;
  /* ... */
}
/* 重复 7 条规则 — .scripture-ref / .ages-code / .book-name / .verse-range / p / strong */
```

**陷阱（已被多次踩中）**：用 `replace_all` 或 sed 替换 `romans-en` → `romans-en,\ngalatians-en` 会产生**错误嵌套**：

```css
/* ❌ 错：第二个 selector "data-book=galatians-en" 后接 .scripture-box，
   但 john-en 后是 .scripture-box;  romans-en 没有 — 整个 content 区被选中 */
.calvin-en-content[data-book="john-en"] .scripture-box,
.calvin-en-content[data-book="romans-en"],
.calvin-en-content[data-book="galatians-en"] .scripture-box {
  ...
}
```

正确写法：**完整复写每个 selector**（不要尝试用 replace 简化）：

```css
[A] .scripture-box,
[B] .scripture-box,
[C] .scripture-box {
  ...
}
```

---

## O. ccel_pg_is_footnote 只看首 span 字号 → 经文续接整页丢失

**Trigger**：harmony-2-en 某章 scripture-table 末尾 verse 缺失（如 Matt 21:1-9 只到 v3，Mark 11:1-10 只到 v3）。对照 PDF 多页表格的**第二页内容完全没出现**在 raw txt。

**根因**：CCEL parallel 格式（vol 2）中，跨页 verse 续接块的首 span 常是上一节的 footnote-ref 数字（如 `699 4. Now all this was done...`），字号 6.6pt < `footnote_size_max` (7.5)。原 `ccel_pg_is_footnote` 只看首 span 字号 → **整页跨页续接块被误判为脚注 → 全部过滤掉**。

具体踩坑现场（matthew_make2.pdf p283）：
- B2 y=185 首 span=6.6 「699」第二 span=12.0 「 4. Now all this was done...」
- B3 y=246 首 span=6.6 「708」第二 span=12.0 「 said to them...」
- 两块共含 Matt v4-9 / Mark v3 续-10 / Luke v32-38 完整内容

**Fix**：两个信号同时满足才判脚注：
```python
def ccel_pg_is_footnote(block, cfg):
    spans = [s for line in block.get('lines', [])
             for s in line.get('spans', []) if s.get('text', '').strip()]
    if not spans:
        return False
    if spans[0].get('size', 0) >= cfg['footnote_size_max']:
        return False
    # 首 span 小，再看第二 — 正文字号则不是脚注
    if len(spans) >= 2 and spans[1].get('size', 0) >= 10:
        return False
    return True
```

**通用启示**（见 [principles §0.3](principles.md)）：「首 span 几何特征」是单点信号，需配合「第二 span 字号」「block 位置」等内容信号联合判断。光看首 span 字号是单几何信号的反例。

---

## P. scripture-table 单元格里行内 fn-ref 数字未渲染为上标

**Trigger**：harmony-2-en 表格 cell 中出现裸数字（如 `Gospel. 5 6. And blessed...`）夹在两节经文之间——这个 `5` 应该是上一节的脚注引用（`<sup>5</sup>`），但被当成普通字符显示。

**根因**：`ccel_pg_build_verse_table` 直接 `''.join(s['text'] for s in spans)` 拼行文本——**完全跳过了 span 字号/flags 判定**。CCEL parallel PDF 中行内 fn-ref 是 6.6pt + flags=5 (`sup|serif`) 的小数字，与正文 12pt 区分明显，但暴力 join 后看不出。

**Fix**：build 行文本时按 span 处理，小字号 sup 数字包成 `<sup>N</sup>`：

```python
parts = []
for sp in line.get('spans', []):
    t = sp['text']
    sz = sp.get('size', 0)
    is_sup = bool(sp.get('flags', 0) & 1)
    stripped = t.strip()
    if is_sup and stripped.isdigit() and sz < 9.5:
        parts.append(f'<sup>{stripped}</sup>')
    else:
        parts.append(t)
line_text = ''.join(parts).strip()
```

**通用启示**：`ccel_pg_spans_to_md`（正文用）已经处理了 fn-ref → `<sup>`，但 `ccel_pg_build_verse_table`（表格用）是独立路径——**两条路径都需要同样的 fn-ref 包装逻辑**。新格式提取器抄正文路径的 span→md 逻辑时容易漏复制。

---

## Q. PyMuPDF dict 模式下 narrow cols 多列同 y 文本合并成单一 span → 必须 word-level 提取

**Trigger**：scripture-table 某 col cell 含明显属于另一 col 的文字（如 Matt v11 里串入 Luke v27 末尾「will prepare the way before thee」+ Luke v28 marker「28.」）。raw 中**单一 span x0 看起来在 Matt cell 起点**但 span 文本横跨两列。

**根因**：PyMuPDF `get_text('dict')` 在 narrow cols（vol 2 平行福音 ~187px/col）+ 多列同 y 文本时偶尔把**多列的相邻文本合并到一个 span**：

```
B0 line0 spans:
  x0=74  "will prepare the way before thee. "     (Matt v10 end)
  x0=244 "11"                                      (Matt v11 marker)
  x0=256 ".\xa0Verily, I will prepare the way before thee. "  ← 跨列合并！
  x0=466 "28"                                      (Luke v28 marker)
  x0=478 ".\xa0For I say to"                       (Luke v28 start)
```

x0=256 的 span 起点在 Matt cell 内，但 span text 含 Matt v11 起首「Verily, I」+ Luke v27 末尾「will prepare the way before thee」**全在一个 span**。span-level 和 line-level x0 分桶都无解——单点 x0 不能反映 span 跨越的物理位置。

**Fix**：用 **word-level** 提取（`page.get_text("words")` 给每个 word 独立 bbox）：

```python
def block_to_verse_buf_entry(block, page, page_idx):
    x0, y0, x1, y1 = block['bbox']
    page_words = page.get_text('words')
    wlist = [w for w in page_words
             if y0 - 1 <= w[1] and w[3] <= y1 + 1]
    # span_size_map: (round(y0), round(x0)) → (size, is_sup) 让 word
    # 也能识别 sup fn-ref（words 没字号/flags 信息）
    sm = {}
    for line in block.get('lines', []):
        for sp in line.get('spans', []):
            if not sp.get('text', '').strip(): continue
            sm[(round(sp['bbox'][1]), round(sp['bbox'][0]))] = (
                sp.get('size', 12.0), bool(sp.get('flags', 0) & 1)
            )
    return (block, wlist, sm, page_idx)
```

`build_verse_table` 按 word 的 x0 分桶（不是 span/line 的 x0）。

**通用启示**（与 §0.3 互补）：
- 同一物理特征（span x0）在不同密度下含义不同——稀疏布局可靠，密集布局欺骗
- 「**几何信号**」必须配合「**几何粒度**」一起判断：span 在 narrow cols 不可靠，需降到 word 粒度
- 新写多列检测时**默认用 words 路径**，仅在 spans 已被验证足够时降级

---

## R2. scripture-table col split 必须用 word-x0 histogram，不用 label 位置

**Trigger**：narrow N-col 表格某 cell 含明显属于别 col 的内容（如 Luke 开头「he 1.」——「he」是 Mark 末尾词；或 Matt v3-4 含 Mark v25-26 的「high-priest」词）。

**根因**：固定 split 策略对 narrow cols 不够精确——任何**外部信号**（label x、page 几何）都无法精确反映 cell 内容边界：

| 策略 | 问题 |
|---|---|
| page 几何等分（body_left + cw×i） | 假设 cell 等宽，但布局可能偏移 |
| label gutter midpoint（`(col[i].x1 + col[i+1].x0)/2`）| label 位置 ≠ cell 边界（label 在 cell 内 left/center-aligned）|
| empirical 305（2-col vol 2）| 仅对特定布局有效 |

narrow cols（~143px/col）中 word x0 在不同行漂移 30+px，**外部信号 split 都不能完美对齐**。

**正解：用 section-level word-x0 histogram + 期望位置匹配**（让内容自己决定 cell 边界）

⚠️ **不能按 gap width 排序选 top n-1**——页边 gap（body_left 之前的空白）常比 cell 间 gutter 更宽，会优先误选页边而漏真 gutter。

正确：用 page 几何等分作为「期望 split 位置」，对每个期望找**最近的 empty run**：

```python
def find_splits_by_histogram(words, n_cols, body_left=74, body_right=504):
    if len(words) < 20 or n_cols < 2:
        return None
    xmin, xmax = min(words), max(words)
    bin_w = 2
    bins = [0] * ((xmax - xmin) // bin_w + 2)
    for x in words:
        bins[(x - xmin) // bin_w] += 1
    # 找连续 ≥3 bins（≥6px）的空 bin 段
    empty_runs = []
    i = 0
    while i < len(bins):
        if bins[i] == 0:
            j = i
            while j < len(bins) and bins[j] == 0:
                j += 1
            if j - i >= 3:
                empty_runs.append((j - i, (i + j) / 2 * bin_w + xmin))
            i = j
        else:
            i += 1
    # 期望位置 = page 几何等分
    cw = (body_right - body_left) / n_cols
    expected = [body_left + cw * (i + 1) for i in range(n_cols - 1)]
    # 对每个期望位置找最近 empty run（必须在 body 范围内，距期望 < 60px）
    chosen = []
    for exp in expected:
        cands = [r for r in empty_runs
                 if body_left < r[1] < body_right and r not in chosen]
        if cands:
            closest = min(cands, key=lambda r: abs(r[1] - exp))
            if abs(closest[1] - exp) < 60:
                chosen.append(closest)
    if len(chosen) == n_cols - 1:
        return sorted([r[1] for r in chosen])
    return None
```

**实测（vol 2 Matt 12:9-13 三栏 narrow table）**：
- Matt v9-13 **完整干净** ✓
- Mark v1-5 **完整干净** ✓
- Luke v6-10 **完整干净** ✓

之前用 gap-width 排序的版本会选 [88, 394]（页边 + 错位 gutter），现在用 expected-position 匹配选 [226, 394]（接近真 gutter）。

**回退顺序**（histogram 找不够 gutter 时）：
1. 3-col → label gutter midpoint
2. 2-col → empirical 305
3. 兜底 → page 几何等分

**通用启示**（与 §0.3 互补）：
- **直接从内容自身决定 cell 边界**最可靠（histogram 看 word 位置分布）
- label / page 几何是**间接信号**，narrow 布局下不够精确
- 「让数据说话」优于「让几何说话」当内容密度高时

---

## R. 跨页 word 排序必须含 page_idx，否则 p11 y=88 排到 p10 y=600 前

**Trigger**：scripture-table cell 内容顺序错乱——后页 v11 出现在前页 v7 之前，或 cross-ref 注脚跑到 cell 顶部。

**根因**：用 word-level 提取多页内容时（§Q），sort key 只用 `(y0, x0)`。PDF 每页 y 范围都是 0-792，所以 p11 的 y=88（顶部）会**排到 p10 的 y=600（底部）前**。

**Fix**：sort key 必须含 page_idx 作为**最高优先级**：

```python
all_word_recs.append((page_idx, y0, x0, x1, text, size, is_sup))
all_word_recs.sort(key=lambda r: (r[0], round(r[1]), r[2]))
#                                  ^页^    ^y^     ^x^
```

verse_buf 记录条目时也必须**保留 page_idx**（不能只存 block）：

```python
verse_buf.append(block_to_verse_buf_entry(block, page, page_idx))
                                          # ↑ 必传
```

**通用启示**：任何跨页/跨文档的字符级排序，**page_idx / doc_idx 必须是 sort key 的第一字段**。这种 bug 不会 fail loudly——content 在但顺序错。

---

## S. scripture-table `<td colspan="N">` 跨全宽行内容必须按 cross-ref label 路由到正确 col

**Trigger**：scripture-table Matt cell 末尾出现明显属于 Luke 的内容（如「16. The Law and the Prophets (were) till John...」是 Luke 16:16 经文，但出现在 Matt cell）。

**根因**：PDF 原文有 `<tr><td colspan="2">` 跨全宽行表达「跨节经文引用」——Calvin 在 Luke col 末尾标「Luke 16:16」label，下方跨全宽放该节经文（视觉上跨两 col 底部）。`transform_scripture_table` 旧逻辑无脑放第一栏 (Matt)。

**Fix**：检测前面已渲染 col 的末尾是否含 cross-ref label 模式 `Book N:M$`，有则把 colspan 内容追加到该 col：

```python
CROSS_REF_RE = re.compile(
    r'\b(Matthew|Mark|Luke|John|Acts|Romans|[12] Corinthians|...)'
    r'\s+\d+:\d+\s*\.?\s*$'
)
if 'colspan' in cell.attrs:
    target_col = 0   # 默认放第一栏（兼顾 Matt-only 无 Luke 平行的旧情况）
    for ci in range(n_cols):
        if col_texts[ci] and CROSS_REF_RE.search(col_texts[ci][-1].rstrip()):
            target_col = ci
            break
    col_texts[target_col].append(cell.content)
```

**通用启示**：HTML 结构信号（如 `colspan="N"`）的语义往往依赖**上下文**——同一个 colspan 在不同上下文里可能是「Matt-only 段」「Luke cross-ref」「真正跨栏分享」。需要看**前后 col 内容**才能判断正确路由。

---

## N. 多栏 scripture-table 在窄屏横向滚动

**Trigger**：用户报告"经文表滑动"且仅出现在共观福音类书卷。

**根因**：scripture-table 用了旧 calvin-scripture 类（`display:block; overflow-x:auto; min-width:280px`）。

**Fix**：
- 共观福音类（harmony-1-en / harmony-2-en / harmony-3-en）必须用 `<table class="scripture-table">`，**不是** `<table class="calvin-scripture">`
- `.scripture-table` CSS 必须有 `table-layout: fixed` + `overflow-wrap: break-word`

---

## 通用法则

**看到 Trigger 时的反射**：
1. 不要 debate「也许这个例外可以接受」
2. 不要"先 commit 再说"
3. 立刻跑 Fix 重做
4. 跑 [audit-gates.md](audit-gates.md) 全部 grep 通过才 commit
