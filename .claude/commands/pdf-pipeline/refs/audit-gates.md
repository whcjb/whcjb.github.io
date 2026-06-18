# Commit Gate

每次 commit 前必跑下面 grep。**结果数字写到 commit message 里**——不写 = 没合格 = 不能 commit。

如果有任何 gate **不通过**，跑 [anti-patterns.md](anti-patterns.md) 对应 Fix 重做后再 commit。

---

## Gate 1：emit 层规范化（适用所有 raw/published md）

```bash
F=PATH/TO/FILE
echo "**** count:       $(grep -c '\*\*\*\*' $F)"             # 必须 = 0
echo "<<<END count:     $(grep -c '<<<END' $F)"               # 必须 = 0
echo "split italic:     $(grep -cP '\*[\"\"]\*' $F)"          # 必须 = 0
```

- `****` 触发 [anti-pattern B](anti-patterns.md#b)
- `<<<END` 触发 [anti-pattern C](anti-patterns.md#c)
- split italic 触发 [anti-pattern A](anti-patterns.md#a)

---

## Gate 2：发布 md front-matter 清洁

```bash
F=calvin/BOOK/N.md
echo "zh fm keys:       $(grep -cP '^[一-鿿]+[:：]' $F)"      # 必须 = 0
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

## Gate 5b：`<p>` 含 kramdown markdown 必须带 `markdown="1"`

```bash
F=PATH/TO/FILE
# 找含 [^fN] 或 *italic* 的 <p>，但缺 markdown="1" 属性 → kramdown 不会处理
grep -nE '<p[^>]*>(?:[^<]*\[\^|[^<]*\*[A-Za-z])' $F | grep -v 'markdown="1"' | head
```

- 有匹配 = 该 `<p>` emit 漏 `markdown="1"`，里面的 `[^fN]` / `*X*` 会渲染成字面字符
- 2cor preface 踩过：navy-quote 居中 `<p style="text-align:center; color:#000080">` 漏 `markdown="1"`
  → `[^f7]` `[^f8]` 显示为字面文本（详见 02a-extract-ages §11.4 反例条目）
- 修法：structured_to_md.py 中所有 `out.append('<p ...>...</p>')` 含正文片段都加 `markdown="1"`

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
grep -cP '\b\w+- \w+' $F   # 应 ≈ 0
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

## 整合脚本：一次跑完所有 gate

```bash
#!/usr/bin/env bash
F=$1
[ -z "$F" ] && { echo "Usage: $0 <md_file>"; exit 1; }

echo "=== $F ==="
echo "1. **** count:    $(grep -c '\*\*\*\*' $F)"
echo "2. <<<END:        $(grep -c '<<<END' $F)"
echo "3. split italic:  $(grep -cP '\*[\"\"]\*' $F)"
echo "4. zh fm keys:    $(grep -cP '^[一-鿿]+[:：]' $F)"
echo "5. calvin-script: $(grep -c 'calvin-scripture' $F)"
echo "6. long para:     $(awk 'NR>20 && length($0)>1500' $F | wc -l)"
echo "7. hyphen rem:    $(grep -cP '\b\w+- \w+' $F)"

ref=$(grep -oE '\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]' $F | grep -v ':$' | sort -u | wc -l)
def=$(grep -cE '^\[\^[Ff]?[Tt]?[0-9]+[A-Za-z]?\]: ' $F)
echo "8. fn ref/def:    $ref / $def $([ $ref = $def ] && echo OK || echo MISMATCH)"
```

保存为 `scripts/audit-md.sh`，每次 commit 前跑：`bash scripts/audit-md.sh calvin/BOOK/N.md`。

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
