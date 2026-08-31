# Commit Gate

每次 commit 前必跑下面 grep。**结果数字写到 commit message 里**——不写 = 没合格 = 不能 commit。

如果有任何 gate **不通过**，跑 [anti-patterns.md](anti-patterns.md) 对应 Fix 重做后再 commit。

---

## Gate 1：emit 层规范化（适用所有 raw/published md）

```bash
F=PATH/TO/FILE
echo "**** count:       $(grep -c '\*\*\*\*' $F)"             # 必须 = 0
echo "<<<END count:     $(grep -c '<<<END' $F)"               # 必须 = 0
echo "split italic:     $(grep -cE '\*[“”\"]\*' $F)"          # 必须 = 0（macOS 用 -E 非 -P）
```

- `****` 触发 [anti-pattern B](anti-patterns.md#b)
- `<<<END` 触发 [anti-pattern C](anti-patterns.md#c)
- split italic 触发 [anti-pattern A](anti-patterns.md#a)

---

## Gate 2：发布 md front-matter 清洁

```bash
F=calvin/BOOK/N.md
echo "zh fm keys:       $(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f' $F | grep -cE '^[^ -~]+[:：]')"  # 必须 = 0（仅查 fm 区，-E）
echo "book_id-en mix:   $(grep -c 'book_id: harmony-.*-en\b' $F)"  # 中文 md 应 = 0
```

- 中文 front-matter 键漏译 = [anti-pattern D](anti-patterns.md#d)

---

## Gate 3：scripture-table 单元格结构

```bash
F=calvin/BOOK/N.md
# 每个 <table class="scripture-table"> 都应只有一行 tbody（多 tr 应合并）
echo "table rows:       $(grep -c '<tbody><tr>' $F)"
echo "scripture-table:  $(grep -c 'scripture-table' $F)"
# 上面两个值应该相等（每张表 1 个 tbody-tr）
```

- 不相等 = 没合并行 = 走捷径用旧 calvin-scripture 模板 = [anti-pattern N](anti-patterns.md#n)

---

## Gate 4：scripture-table class 正确（共观福音类）

```bash
# harmony-1-en / harmony-2-en / harmony-3-en 都用 .scripture-table，不能用 .calvin-scripture
grep -c 'calvin-scripture' calvin/harmony-*-en/*.md   # 全部应 = 0
```

---

## Gate 5：footnote ref / def 配对

```bash
F=PATH/TO/FILE
# 兼容 [^N] 与 [^fN]/[^ftN] 标签（acts/1cor/2cor 等 Ages 书用 f-prefix）
ref=$(grep -oE '\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\](?!:)' $F | sort -u | wc -l)
def=$(grep -cE '^\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]: ' $F)
echo "fn refs:  $ref   fn defs: $def"   # 必须 ref == def
```

- 不等 = [anti-pattern H](anti-patterns.md#h)
- **ref ≫ def**：典型 root cause 是 extractor → structured_to_md 之间 def 漏识别。
  例如 2cor 踩过的 `<sty>ftN.</sty>` 带点 label，老 FN_DEF_RE 不允许尾点 →
  ft11–ft240 全部走 body 路径不进 `[^fN]:`（详见 02a-extract-ages §11.4 反例条目）。

---

## Gate 5g：跨页断句（一句被 `<!-- PAGE N -->` 截成两段）

发布英文版后**必须**跑，且必须为 0。中译在此之后才能开跑——否则会照着断句拆译，
事后修英文还得把受影响章节全部 `--resume` 重跑一遍。

```bash
# 单卷
python3 scripts/fix_page_split_paragraphs.py --dry-run calvin/<book>-en   # 必须"发现 0 处"
# 全库普查
python3 scripts/fix_page_split_paragraphs.py --dry-run
```

- 非 0 = [anti-pattern M3b](anti-patterns.md#m3b)
- Fix 后脚本会列出待 `--resume` 重跑中译的章节清单。判断哪些要重跑，须用
  `translate_filibi.py` BOOKS 条目里的 `out` 路径反查（目录名 ≠ 书名，如
  acts → `calvin_raw/acts-filibi/zh_chapters/`），不要按书名猜目录。
- OCR 中译书（**罗马书 / 约翰福音 / 以弗所书 / 歌罗西书**）不动、不可重译；
  **使徒行传是英译中，要重跑**。

---

## Gate 5d：OCR 扫描版 —— CUV bible-dump 尾巴溢出（假 verse-opener）

```bash
F=PATH/TO/FILE   # 如 calvin/john/10.md
# `**书 N:V。** *quote。* body` promoted 段，body 里若有 2+ 个 inline
# `<非数字非空白>\d+<CJK>` 模式（数字紧贴 CJK 且不在段首）→ CUV verse-
# marker 残留被 replace_circle 剥成裸数字后的痕迹。
grep -nE '\*\s+[^*]{0,10}[^0-9\s]\d{1,3}[一-鿿].{0,80}[^0-9\s]\d{1,3}[一-鿿]' $F | head
```

- 有命中 = 前一页整页 CUV 全章 dump 溢到当前段（page 0348→0349 踩过）
- 典型：`**约翰福音 10:40。** *洗的地方，就住在那里。* 1有许多人…2在那里信耶稣的人就多了`
- 修法：删该 verse-opener 段，从 body 后段找真正的 Calvin 引文（形如 `*耶稣又往约旦河外去。* 基督往约旦河外去…`）
- 根因：[anti-patterns.md M5e](anti-patterns.md#m5e-cuv-bible-dump-尾巴溢出)

---

## Gate 5f：OCR 扫描版 —— verse-anchor 漂移（段落挂错 verse）

```bash
F=PATH/TO/FILE   # 如 calvin/john/14.md
BOOK=john        # 与 verse-anchor id 前缀一致
CH=14

# F1：找 scripture-box 里出现但正文缺 verse-anchor 的 verse
python3 -c "
import re,sys
p=open('$F').read()
box=set()
for m in re.finditer(r'<strong>(\d+)\.</strong>', p): box.add(int(m.group(1)))
anc=set(int(m.group(1)) for m in re.finditer(r'verse-anchor\" id=\"$BOOK-$CH-(\d+)\"', p))
missing=sorted(box-anc)
if missing: print('MISSING verse-anchor for:', missing)
else: print('OK: 所有 scripture-box verse 都有 anchor')
"

# F2：找同一 verse-anchor 段内含 2+ 个 *keyword。* 段头
awk -v RS='<h2 class=\"verse-anchor\"' '
NR>1 { n=gsub(/\*[^*\n]+。\*/,"&"); if(n>=2) print "verse-anchor #"NR" 内含", n, "个 sub-phrase *X。*" }
' $F | head

# F3：找紧邻 `## 书 N:A-B` header 前的 orphan 段（无 verse 前缀、无 sub-phrase 前缀）
grep -B2 '^## 约翰福音' $F | grep -E '^[^\*<#].{5,200}$' | head
```

- F1 命中 = anchor 缺失，见 [anti-patterns.md M5f](anti-patterns.md#m5f)
- F2 命中 = 一个 anchor 下有多个 sub-phrase，可能吞掉了相邻 verse 的段
- F3 命中 = orphan 短句待归位

**Fix**：对照 `calvin_raw/<book>-scan/ocr/page_NNNN.md` 逐段核对 verse marker（`⑳`/`㉑`/`③9`），迁移段落 + 补 anchor + 加 `**书 N:V。**` 前缀。**严禁**用英文源反译判断段落归属。

---

## Gate 5c：OCR 扫描版 —— 脚注 def 泄漏进正文

```bash
F=PATH/TO/FILE   # 如 calvin/john/10.md
# body 段落里出现 "——中文编者注" / "——中文译者注" / "——编者注" 就是漏
grep -nE '^[^\[].*——中文?(编者|译者)?注' $F | head
```

- 有命中 = OCR raw 里的 `① def-text——中文编者注` 被错误当 body 段落（应进 `[^N]:`）
- 常见并发症：
  - 段首多余 `*` (伪 italic wrap，来自 `maybe_promote_verse_opener` 把 fn def 当 verse-opener promote)
  - 正文对应 inline `①` ref 被 replace_circle 当孤儿剥掉（`grep -o '①' $F` 应为 0，但对应 `[^N]` 也缺）
  - 跨页续段被 `_join_cross_page` 粘到 fn def 尾（表现为 `——中文编者注X`，X 是下一页首字如"裂"/"助"）
- 根因与修法：[anti-patterns.md M6](anti-patterns.md#m6-fn-def-泄漏正文)

---

## Gate 5b：`<p>` 含 kramdown markdown 必须带 `markdown="1"`

```bash
TARGET=calvin/           # 单文件或整目录皆可（-r 递归）
# 行首独立 <p ...> 块，含 [^fN] 或成对 *斜体*（中/英/引号后皆可），但无 markdown 属性
grep -rnE '^<p [^>]*>' $TARGET | grep -v 'markdown=' \
  | grep -E '\[\^[Ff]?[Tt]?[0-9]+\]|\*[^*]+\*' | head
```

三个关键点，缺一即漏判（都被踩过）：
- **`^<p `**（行首 + 带属性）：只查独立 block 级 `<p>`。表格单元格 `<td><p markdown="span">…`
  与无属性拉丁经文 `<p>Sermo…</p>` 另有机制，不能一起 flag（否则一堆误报）。
- **`grep -v 'markdown='`**（不是 `markdown="1"`）：`markdown="span"` 同样触发 kramdown，
  只排 `"1"` 会把正常的 span 块误报。
- **`\*[^*]+\*`**（成对星号任意字符），**不能**用 `\*[A-Za-z]`：中文斜体 `*"因为生命…"*`
  星号后是引号/CJK，旧写法漏判——1timothy/5 的居中经文块因此逃过审计
  （2026-07 用户发现，全库 1012 行受影响，be1e3b96 修）。

有匹配 = 该 `<p>` 漏 `markdown="1"`，里面 `[^fN]`/`*X*` 会渲染成字面字符。
- 2cor preface 也踩过：navy-quote 居中 `<p style="text-align:center; color:#000080">` 漏属性。
- 修法：structured_to_md.py 中所有 `out.append('<p ...>...</p>')` 含正文片段都加 `markdown="1"`（line ~1038 已含）；
  历史文件用上面的 grep 定位后**纯追加**补 `markdown="1"`（勿重生成，会覆盖脚注校准）。

---

## Gate 6：段落长度合理（无超长段）

```bash
F=PATH/TO/FILE
# 找 > 1500 字符的非空行（front-matter 以下）
awk 'NR>20 && length($0)>1500 {print NR": "length}' $F | head
```

- 有匹配 = [anti-pattern I](anti-patterns.md#i)（段落没拆分）

---

## Gate 7：行末断字残留

```bash
F=PATH/TO/FILE
grep -cE '[[:alnum:]]+- [[:alnum:]]' $F   # 应 ≈ 0（macOS 用 -E 非 -P）
```

- 多于 5 个 = [anti-pattern J](anti-patterns.md#j)（hyphenation 没跑）

---

## Gate 8：raw zh chmod 444 强保留

```bash
# 翻译完成后必查
ls -l calvin_raw/BOOK/zh_chapters/N.md   # 必须显示 -r--r--r--
```

- 显示 `-rw-` = [anti-pattern M](anti-patterns.md#m)，立刻 `chmod 444`

---

## Gate 9：`<sup>` fn ref 有 scroll-margin-top（backref 跳回不被 navbar 遮挡）

```bash
# _layouts/calvin-en.html 必须含此规则
grep -A2 'sup\[id\^="fnref:"\]' _layouts/calvin-en.html
```

- 应出现 `scroll-margin-top: 80px`
- 缺 = [anti-pattern M22](anti-patterns.md#m22)，用户会报告 "点击脚注无法跳转"

---

## Gate T：字形特征普查（产物 vs PDF）★ 最重要

```bash
python3 scripts/qa_ages_typography.py <源PDF> <发布目录>
```

**这是唯一一条验证「产物忠于 PDF」的 Gate，其余全部只验产物内部自洽。**

按 PDF 的 span 统计各类字形，与产物里对应标记比对，超出 ±15% 即报：

| 特征 | PDF 侧 | 产物侧 |
|---|---|---|
| bold | `flags & 16` 或字体名含 Bold 的字符数 | `**X**` 的字符数（排除 `**N.**` 节号） |
| italic | `flags & 2` 的字符数 | `*X*` 的字符数 |
| red | `color == 0x800000` 的字符数 | `<span style="color:#800000">` 内字符数 |
| greek | Koine 字体 span 按空格切词 | `[Ͱ-Ͽἀ-῿]+` 词块数 |
| centered | 几何居中的块（排除纯页码块） | `title-block-h1/h2` + 行首 `<p style="text-align:center` |

**三处口径必须校准，否则一直误报**（都实测踩过）：
- **页码块本身居中**：410 宽的页面上页码在 x≈198，1cor 有 401 个，
  不排掉「居中内容」这一项会被淹没（466 里 401 是页码）。
- **`**N.**` 节号不是 PDF 粗体**：那是发布阶段按站内约定加的
  （`bold_leading_verse_num`），算进来会多出 40% 以上。
- **希腊文按词不按字符**：AGES 转写码到 Unicode 不是 1:1
  （`lo>gov` 6 字符 → λόγος 5 字符），按字符数天然缩水约 18%。

**报错时的判断顺序**：先问「是不是口径问题」，再问「是不是管道吃了样式」。
上面三条是口径；真缺陷长这样——产物侧接近 0，或缺口成整数倍。

## Gate X：正文字符流比对（产物 vs PDF）★ 与 Gate T 同等重要

```bash
python3 scripts/qa_ages_text.py <源PDF> <发布目录> [--skip-tail N]
```

Gate T 只比**字形特征的数量**，证明不了正文一个字都没丢；本 Gate 比正文本身。
两侧归一到纯文字流后**按词** diff（百万字符按字符跑 SequenceMatcher 要几十
分钟，按词是秒级；定位到差异段再看字符也够用）。

归一规则（两侧都做，务求可比）：
- PDF 侧：AGES 希腊转写码 → Unicode（与产物同一函数）、空格大写折叠
  （`B o o k s` → `Books`）、去页码行、`--skip-tail` 去掉 AGES 卷尾广告页。
- 产物侧：剥 HTML → 再剥脚注标记（**顺序不能反**，脚注引用常包在 `<sup>`
  里，反了会剩 `[^]` 残骸）、去 markdown 标题号与强调标记。
- 脚注**单独成流**：AGES 把脚注全收在书末 FOOTNOTES 之后，产物按章分散，
  混在一起比会刷出大片假差异。
- 脚注引用还原成裸数字（PDF 里就是上标数字 `Nero. 1`，产物里是 `[^f1]`）。

**已知坑**：切分脚注区只能认书末那个 FOOTNOTES 标题——卷首的超链接目录里
也有一行「Footnotes」，不设页数下限（`i > page_count * 0.75`）会从第 5 页
就切开，把整本正文都算进脚注流。

**验收线**：正文相似度 ≥ 0.995，且剩余差异段逐条能归因（表示差异 vs 真缺陷）。
贺智实测：前书 0.99808、后书 0.99823，剩余 4 段全是脚本自身的表示差异。

**这道 Gate 当场查出两处真缺陷**，而所有既有 Gate 都报 0：
1. 脚注引用双层套嵌 31 处（`Nero.[^[^f1]]`，链接失效）——提取器吐 `[^f3]`
   后，`format_inline` 的裸引用规则又在其内部命中一次。Gate 5 的 ref/def
   配对用宽松正则，认不出套嵌。
2. 希腊转换吃掉 `<sty>` 标记 131 处——`convert_ages_greek` 保护 `<sty>` 的
   stash 正则写死 `c="…" i="…"`，不认后加的 `b="0"`，于是 `laid<sty c=…>`
   被当希腊文转成 `λαιδστψ c="800000" i="1" b="0">`。尤其隐蔽：`sty` 自己也
   被转成 `στψ`，grep `sty c=` 都搜不到。

## 整合脚本：一次跑完所有 gate

```bash
#!/usr/bin/env bash
F=$1
[ -z "$F" ] && { echo "Usage: $0 <md_file>"; exit 1; }

echo "=== $F ==="
echo "1. **** count:    $(grep -c '\*\*\*\*' $F)"
echo "2. <<<END:        $(grep -c '<<<END' $F)"
echo "3. split italic:  $(grep -cE '\*[“”\"]\*' "$F")"
# 4. 仅查 front-matter 区被译成中文的键（全文跑会把正文"他说："等误报）
fm4=$(awk 'NR==1&&/^---/{f=1;next} f&&/^---/{exit} f' "$F" | grep -cE '^[^ -~]+[:：]')
echo "4. zh fm keys:    $fm4"
echo "5. calvin-script: $(grep -c 'calvin-scripture' "$F")"
echo "6. long para:     $(awk 'NR>20 && length($0)>1500' "$F" | wc -l | tr -d ' ')"
echo "7. hyphen rem:    $(grep -cE '[[:alnum:]]+- [[:alnum:]]' "$F")"

ref=$(grep -oE '\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]' $F | grep -v ':$' | sort -u | wc -l)
def=$(grep -cE '^\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]: ' $F)
echo "8. fn ref/def:    $ref / $def $([ $ref = $def ] && echo OK || echo MISMATCH)"

# Gate 5b：独立 <p> 块漏 markdown 属性（含 markdown 却不处理 → 字面星号/[^fN]）
echo "9. <p> no md attr: $(grep -E '^<p [^>]*>' $F | grep -v 'markdown=' | grep -cE '\[\^[Ff]?[Tt]?[0-9]+\]|\*[^*]+\*')"
```

保存为 `scripts/audit-md.sh`，每次 commit 前跑：`bash scripts/audit-md.sh calvin/BOOK/N.md`。

> ⚠️ **Gate T 不在这个整合脚本里**，也不可能在——它是**逐卷**比对（需要源 PDF），
> 而本脚本是**逐文件**检查。commit 前两个都要跑：
> ```bash
> bash scripts/audit-md.sh <每个 md>                       # 内部自洽
> python3 scripts/qa_ages_typography.py <pdf> <发布目录>   # 忠于 PDF·字形
> python3 scripts/qa_ages_text.py       <pdf> <发布目录>   # 忠于 PDF·正文
> ```
（check 9 非 0 = 有 `<p>` 漏 `markdown="1"`，用 Gate 5b 的 grep 定位；其余 Gate 5c/5d/5f/9
按需单独跑。）

---

## commit message 模板

```
fix/feat: 描述

Audit (calvin/BOOK/N.md):
  ****=0 <<<END=0 split-italic=0
  zh-fm-keys=0 calvin-scripture=0
  long-para=0 hyphen-rem=0
  fn ref/def=N/N
```

数字粘到 commit body 里。**否则不算合格 commit。**
