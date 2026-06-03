# Step 3: 合并 per-page OCR

把 `calvin_raw/<book>-scan/ocr/page_NNNN.md` 合成一个整本 raw md。

---

## 命令

```bash
python3 scripts/ocr_assemble.py \
  --raw-dir calvin_raw/john-scan \
  --book john
```

产出：`calvin_raw/john-scan/calvin_john_zh.md`

---

## 默认清理

`ocr_assemble.py` 自动：

1. **去除运行页眉**（默认匹配 `# 加尔文文集.*约翰福音注释` 等模式）
2. **插入 `<!-- PAGE NNN -->` 标记**便于追溯
3. **3+ 空行折叠为 2**

---

## 自定义页眉清理

不同书籍页眉文本不同，传 `--strip-line`：

```bash
python3 scripts/ocr_assemble.py \
  --raw-dir calvin_raw/romans-scan \
  --book romans \
  --strip-line '^#\s*加尔文文集.*罗马书注释\s*$' \
  --strip-line '^罗马书注释\s*$'
```

如默认 pattern 不适用，加 `--no-default-strip` 完全不用默认。

---

## 验证

```bash
# 章节数（应等于书卷章节数，e.g. 约翰福音 21）
grep -c "^# 第.*章" calvin_raw/<book>-scan/calvin_<book>_zh.md

# 字符总数（参考量）
wc -c calvin_raw/<book>-scan/calvin_<book>_zh.md
```

---

## 完成后

→ [04-publish.md](04-publish.md)
