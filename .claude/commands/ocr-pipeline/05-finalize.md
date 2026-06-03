# Step 5: commit + push

发布完成后的收尾。

---

## 1. 验证生成内容

```bash
ls calvin/<book>-scan/
# 期望: preface.md 1.md 2.md ... N.md index.html
head -15 calvin/<book>-scan/1.md
```

---

## 2. 添加到 `_data/calvin_books.yml`

按书卷正典顺序插入新条目（不覆盖现有同名条目）。

---

## 3. Stage + commit

```bash
git -c core.fileMode=false add \
  calvin/<book>-scan/ \
  calvin_raw/<book>-scan/ \
  _data/calvin_books.yml \
  scripts/ocr_pdf.py \
  scripts/ocr_assemble.py \
  scripts/publish_ocr_zh.py
git -c core.fileMode=false commit -m "feat(ocr): 发布 <book> 扫描版 OCR 中文版到 calvin/<book>-scan/"
```

⚠️ **不要 commit `calvin_raw/<book>-scan/ocr/page_*.md`** 文件 OCR 耗时长且体积大 — 通过 `.gitignore` 排除：

```gitignore
calvin_raw/*-scan/ocr/
```

只 commit `calvin_raw/<book>-scan/calvin_<book>_zh.md`（assembled raw）和 published `calvin/<book>-scan/`。

---

## 4. push

按 [feedback_mobile_commit] 桌面端 push 需用户确认；用 AskUserQuestion 询问后再推送。

---

## 完成

OCR pipeline 结束。如要把扫描版替换现有翻译版（`calvin/<book>/`），需用户明确指示并先做备份。
