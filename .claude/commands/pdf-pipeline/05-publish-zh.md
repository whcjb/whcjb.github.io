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
    # 1. 去 Claude 偶尔吐出的分段标记
    lines = [ln for ln in raw.splitlines()
             if not re.match(r'^\s*<<<END\d*>>>\s*$', ln)]
    text = '\n'.join(lines)
    
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
