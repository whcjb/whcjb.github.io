#!/usr/bin/env python3
"""
PDF OCR 脚本 —— 调用本地 Qwen3 服务器
用法：
    python3 scripts/ocr_pdf.py <pdf路径> <输出目录> [起始页] [结束页]

示例：
    python3 scripts/ocr_pdf.py ~/Documents/论文/calvin_yaoyi3.pdf ~/Documents/论文/ocr_output/yaoyi3
    python3 scripts/ocr_pdf.py ~/Documents/论文/calvin_yaoyi2.pdf ~/Documents/论文/ocr_output/yaoyi2 1 100

输出：每页存为 page_NNNN.txt，支持断点续跑（已存在的文件自动跳过）。
"""
import base64, time, sys, warnings
from pathlib import Path
warnings.filterwarnings('ignore')

try:
    import fitz
except ImportError:
    sys.exit("缺少 PyMuPDF，请运行：pip install pymupdf")
try:
    import requests
except ImportError:
    sys.exit("缺少 requests，请运行：pip install requests")

OCR_SERVER = "http://10.192.2.11:8765"
DPI = 150   # 150dpi 足够文字识别，速度快 3-4 倍

def ocr_pdf(pdf_path: str, out_dir: str, start: int = 1, end: int = None):
    pdf_path = Path(pdf_path).expanduser()
    out_dir  = Path(out_dir).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)

    doc   = fitz.open(str(pdf_path))
    total = len(doc)
    end   = min(end or total, total)
    print(f"PDF: {pdf_path.name}，共 {total} 页，处理第 {start}–{end} 页", flush=True)

    ok = err = 0
    start_time = time.time()

    for i in range(start - 1, end):
        out_file = out_dir / f"page_{i+1:04d}.txt"
        if out_file.exists() and out_file.stat().st_size > 10:
            ok += 1
            continue
        try:
            pix  = doc[i].get_pixmap(dpi=DPI)
            b64  = base64.b64encode(pix.tobytes("png")).decode()
            resp = requests.post(f"{OCR_SERVER}/ocr", json={"image": b64}, timeout=180)
            resp.raise_for_status()
            text = resp.json()["text"]
            out_file.write_text(text, encoding="utf-8")
            ok += 1
            elapsed = time.time() - start_time
            avg = elapsed / ok
            eta = avg * (end - i - 1)
            print(f"[{i+1}/{end}] {len(text)}字  {avg:.1f}s/页  ETA={eta/60:.0f}min", flush=True)
        except Exception as e:
            err += 1
            print(f"[{i+1}/{end}] ERROR: {e}", flush=True)
            time.sleep(5)

    print(f"\n完成：{ok} 页成功，{err} 页失败")
    print(f"输出目录：{out_dir}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)
    pdf  = sys.argv[1]
    odir = sys.argv[2]
    s    = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    e    = int(sys.argv[4]) if len(sys.argv) > 4 else None
    ocr_pdf(pdf, odir, s, e)
