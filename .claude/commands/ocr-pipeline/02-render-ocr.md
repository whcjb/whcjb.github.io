# Step 2: 渲染 + OCR

每页 PDF → PNG → POST `/ocr` → 落到 `<raw_dir>/ocr/page_NNNN.md`。

---

## 命令

```bash
python3 scripts/ocr_pdf.py \
  --pdf "/Users/yanpeifa/Documents/论文/calvin/加尔文--约翰福音注释.pdf" \
  --out-dir calvin_raw/john-scan \
  --workers 4 --dpi 200 --ext md --markdown-prompt
```

662 页 ≈ 2 小时。建议用 `nohup ... > /tmp/<book>_ocr.log 2>&1 &` 后台跑。

---

## 关键参数

| flag | 默认 | 说明 |
|---|---|---|
| `--workers` | 4 | 并发；GPU 显存吃紧改 3 |
| `--dpi` | 200 | 字号小可调 240 |
| `--markdown-prompt` | 关 | 必开 — 让 VLM 输出 `#`/`##` 标题层级 |
| `--ext md` | `md` | OCR-pipeline 用 md |
| `--start`, `--end` | 0, N | 调试时只跑前几页 |
| `--no-strip-cjk-spaces` | 关 | 默认会删 OCR 在汉字间插入的多余空格 |

---

## Prompt（脚本内置 MARKDOWN_PROMPT）

```
请OCR这张图片，输出 Markdown 格式：
- 大标题（如『第N章』、卷头题目）用 # 开头
- 小节标题（小字号居中标题）用 ## 开头
- 正文段落保留原换行/分段（段落间空行）
- 脚注标记（①②③等圈号）原样保留
- 希腊文/拉丁文/经文引用原样保留
- 不要添加任何解释或额外内容，只输出 OCR 结果
```

⚠️ Qwen-VL **不能输出字体/字号**，只能用 Markdown 标题级别近似视觉层级。要绝对像素级保真，得换 layout-aware OCR（如 PaddleOCR-PP-Structure / MinerU）。

---

## 断点续传

脚本会跳过已有的非空 `page_NNNN.md`。kill 之后重启同样命令即可继续。

---

## 监控

```bash
tail -f /tmp/<book>_ocr.log
ls calvin_raw/<book>-scan/ocr/ | wc -l   # 已完成页数
```

---

## 完成后

→ [03-assemble.md](03-assemble.md)
