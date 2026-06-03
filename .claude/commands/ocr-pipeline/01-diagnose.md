# Step 1: 扫描版 PDF 诊断

判断 PDF 是否为扫描版，是否需要走 OCR pipeline。

---

## 1. 起手 checklist

- [ ] PDF 路径已知
- [ ] 已用 `fitz.get_text()` 抽样 5 页，判断有无可用文本层
- [ ] 已确认 Qwen-VL OCR 服务 (`http://10.192.2.11:8765/ocr`) 可用
- [ ] 已估算页数 × 单页时长，得到总耗时和并发选择

---

## 2. 检测有无可用文本层

```python
import fitz
doc = fitz.open(PDF)
print(f"Pages: {len(doc)}, size: {doc[0].rect}")
# Sample mid-book pages — title pages may be image even in non-scanned books
for i in [10, 50, 100]:
    t = doc[i].get_text()
    print(f"  page {i+1}: {len(t)} chars  preview: {t[:100]!r}")
```

判断规则：
- **完全无文本** (`len(t) == 0`) → 必须 OCR
- **文本明显错乱** (e.g. `第一胃` 应为 `第一章`、`第H 章` 应为 `第三章`) → 推荐 OCR 重做
- **文本干净且字号信息丰富** → 走 [pdf-pipeline](../pdf-pipeline/01-diagnose.md) 不需 OCR

---

## 3. OCR 服务健康检查

```bash
curl -s http://10.192.2.11:8765/health | head
# 期望返回: {"gpus":[...],"model":"Qwen2.5-VL-7B-Instruct","status":"ok"}
```

如果 504/连接拒绝，先排查网络/服务。

---

## 4. 估时

| 并发 workers | 单页时延 | 662 页耗时 |
|---|---|---|
| 1 | 30–40s | ~6 小时 |
| 3 | ~35s | ~2.3 小时 |
| 4 | ~36s | ~2 小时 |
| 6+ | 受 GPU 显存限制可能 OOM | 不推荐 |

模型在 RTX 4090 D (24GB)，已用约 16GB。**默认用 4 workers**。

---

## 5. 输出位置规范

- **raw**: `calvin_raw/<book>-scan/ocr/page_NNNN.md` (per-page) + `calvin_<book>_zh.md` (assembled)
- **published**: `calvin/<book>-scan/` （**绝不覆盖现有的 `calvin/<book>/`**，因为后者可能是另一来源的翻译；按 [feedback_translation_raw_preserve] 保护原翻译）

---

## 下一步

确认走 OCR 后 → [02-render-ocr.md](02-render-ocr.md)
