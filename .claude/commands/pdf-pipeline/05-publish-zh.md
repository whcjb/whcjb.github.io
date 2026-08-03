# Step 5: 中文 raw → 中文版发布

把 `calvin_raw/BOOK/zh_chapters/N.md` 加工成 `calvin/BOOK/N.md`。

---

## 起手 checklist

- [ ] 中文 raw 已存在 + chmod 444（[anti-pattern M](refs/anti-patterns.md#m)）
- [ ] publish 脚本（如 `/tmp/publish_zh.py` 或 `scripts/publish_filibi_zh.py`）已就绪
- [ ] 每章 prev/next label 已查（中文 chapter 标签）
- [ ] index.html 待更新章节范围已确认

---

## 1. transform 必做的 6 件事

raw zh → published zh，发布脚本中 `transform()` 函数必须依次跑：

```python
def transform(raw, ch):
    # 1. 去 Claude 偶尔吐出的分段标记(<<<END>>> / <<<END1>>> / <<</1>>> 等变体, 含行内残留)
    text = re.sub(r'<<<[^>]*?>>>', '', raw)
    
    # 2. abut-bold 合并（§0.4）
    text = text.replace('****', '')
    
    # 3. split italic quote 修复（§0.5）
    QUOTE_OPEN = r'["“”\'‘’]'
    QUOTE_DOUBLE = r'["“”]'
    text = re.sub(rf'\*({QUOTE_OPEN})\*([^*]+?)\*([,.;:!?]*{QUOTE_OPEN})\*',
                  r'*\1\2\3*', text)
    text = re.sub(rf'\*({QUOTE_OPEN})\*([^*]+?{QUOTE_DOUBLE})',
                  r'*\1\2*', text)
    
    # 4. <th> 卷名英→中
    for en, zh in [('Matthew', '马太福音'), ('Mark', '马可福音'),
                   ('Luke', '路加福音'), ('John', '约翰福音')]:
        text = re.sub(rf'<th>{en} ', f'<th>{zh} ', text)
    
    # 5. front-matter book_id / book_name
    text = re.sub(r'book_id: harmony-1-en\b', 'book_id: harmony-1', text)
    text = re.sub(r'book_name: "[^"]+"',
                  'book_name: "共观福音（卷一）"', text, count=1)
    
    # 6. front-matter 键名漏译修正（[anti-pattern D]）
    fm_key_fixes = [
        (r'^章[：:]\s*(\d+)$',     r'chapter: \1'),
        (r'^章节[：:]\s*(\d+)$',   r'chapter: \1'),
        (r'^上一节[：:]\s*(\d+)$', r'prev_section: \1'),
        (r'^下一节[：:]\s*(\d+)$', r'next_section: \1'),
        (r'^上一节标签[：:]\s*"',  r'prev_label: "'),
        (r'^下一节标签[：:]\s*"',  r'next_label: "'),
    ]
    for pat, rep in fm_key_fixes:
        text = re.sub(pat, rep, text, flags=re.M)
    
    return text
```

---

## 1b. 【合参书专属】注释头必写「书卷 章:节」

合参(harmony)书——摩西五经合参(`harmony-law-1/2/3/4`)、共观福音合参(`harmony-1/2/3`)——
**每节经文的注释头不能只写节号** `**N.**`，必须写全「书卷 章:节。」，与既有全引用头
（如「出埃及记 23:14。」）一致（纯文本、非粗体）。

书卷+章由上下文推断，取**最近者**：绿色 h2 章标题
（`<span style="color:#006411">申命记 16</span>`）/「前往」指引 / 已有全引用头 /
经文框 thead 英文引用（`<th>…DEUTERONOMY 16:1</th>`，英→中）。

跑 `scripts/add_verse_refs_harmony.py`（幂等；无上下文可定位则**保留原样+打印警告**，绝不臆造）：

```bash
python3 scripts/add_verse_refs_harmony.py --all-law                 # 全 law 卷
python3 scripts/add_verse_refs_harmony.py calvin/harmony-law-3/14.md  # 指定文件
```

**发布每章后必跑此步**（harmony-law 已内联进 `publish_harmony_law_zh.py`）。
校验：发布章正文不应再有行首 `**\d+\.**` 注释头（除非该头确无上下文而被警告保留）。

## 2. 末章 next-link 必须剥

最后一章的 raw zh 仍带 `next_section: 11` 这种**不存在的链**，会 404。发布末章后必须删：

```python
if ch == LAST_CHAPTER:
    text = re.sub(r'^next_section: \d+\n', '', text, flags=re.M)
    text = re.sub(r'^next_label: "[^"]+"\n', '', text, flags=re.M)
```

---

## 3. 中文 book_name 统一规则

| 书卷 | 中文 book_name |
|---|---|
| `harmony-1` | `共观福音（卷一）` |
| `harmony-2` | `共观福音（卷二）` |
| `harmony-3` | `共观福音（卷三）` |

详见 [refs/principles.md](refs/principles.md)（命名一致性）。

---

## 4. publish 脚本模板

```python
#!/usr/bin/env python3
"""把 raw zh → calvin/BOOK/N.md"""
import re
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
RAW_DIR = ROOT / 'calvin_raw/matthew1/zh_chapters'
OUT_DIR = ROOT / 'calvin/harmony-1'

META = {
    5: {'prev_label': '马太福音 3', 'next_label': '马太福音 5'},
    6: {'prev_label': '马太福音 4', 'next_label': '马太福音 6'},
    # ...
}

def transform(raw):
    # ...（见 §1）
    return text

for ch in CHAPTERS:
    raw_p = RAW_DIR / f'{ch}.md'
    raw = raw_p.read_text(encoding='utf-8')
    out = transform(raw)
    (OUT_DIR / f'{ch}.md').write_text(out, encoding='utf-8')
```

---

## 5. 翻译质量抽查

```bash
# 1. 检查中文段是否包含未翻译的英文长片段（> 50 字符英文连续）
grep -P '[A-Za-z]{50,}' calvin/BOOK/N.md | head

# 2. 检查脚注 ref/def 配对
ref=$(grep -oE '\[\^[0-9]+\]' calvin/BOOK/N.md | grep -v ':' | sort -u | wc -l)
def=$(grep -cE '^\[\^[0-9]+\]: ' calvin/BOOK/N.md)
echo "ref=$ref def=$def"

# 3. 抽查 5 处段落
for n in 50 100 200 400 800; do
  echo "--- line $n ---"
  sed -n "${n}p" calvin/BOOK/N.md | head -c 200
  echo
done
```

---

## 6. 完成后 audit

跑 [refs/audit-gates.md](refs/audit-gates.md) 全 8 gate。

---

## 7. 进入下一步

中文发布 OK → [06-finalize.md](06-finalize.md)

新增/重发已有书卷时也要重跑经文索引 → [07-verse-index.md](07-verse-index.md)
（publish 脚本里必须内联 `relocate_anchors_in_body`，否则锚点会留在经文块前面，
点击索引跳到经文而非注释。详见 07-verse-index §1–2。）
