# Step 4: 发布到 calvin/<book>-scan/

把整本 raw md 切成 preface + N.md 并加 front matter。

---

## 命令

```bash
python3 scripts/publish_ocr_zh.py \
  --book john \
  --book-name 约翰福音
```

默认产出：
- `calvin/john-scan/preface.md`
- `calvin/john-scan/1.md`, `2.md`, ..., `21.md`
- `calvin/john-scan/index.html` (`layout: calvin-book`, `has_preface: true`)

---

## 切分规则

按 `^# 第N章\s*$`（含中文/阿拉伯数字章号、十/百/二十一）分章。

- 第一章 → ch_num=1, 文件 `1.md`
- 第十一章 → ch_num=11, 文件 `11.md`
- preface = 第一章之前的全部内容

---

## front matter

```yaml
---
layout: calvin-chapter
book_id: john-scan
book_name: 约翰福音
chapter: 1
total_chapters: 21
header-img: img/post-bg-2015.jpg
date: 2026-06-03 09:30
---
```

`book_id` 默认 `{book}-scan` 以**避免覆盖**现有 `calvin/<book>/` 翻译。
要覆盖原版（用 OCR 版替换现有翻译），传 `--book-id <book>` + `--out-dir calvin/<book>`，并先备份原 `calvin/<book>/` 内容。

---

## 注册 yaml

在 `_data/calvin_books.yml` 加 entry。位置取决于 testament + canonical 顺序：

```yaml
old_testament:
  - id: john-scan
    name: 约翰福音（扫描版）
    chapters: 21
```

或新建 zh-scan section。

---

## 完成后

→ [05-finalize.md](05-finalize.md)
