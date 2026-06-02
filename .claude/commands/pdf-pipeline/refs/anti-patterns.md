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
