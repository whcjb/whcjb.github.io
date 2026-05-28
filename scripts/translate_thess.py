#!/usr/bin/env python3
"""
将 clavin_geluoni_tiesaluonijia.pdf 中帖撒罗尼迦前后书（pp.215-335）
逐页翻译成中文，保存到 calvin_raw/thess/page_NNNN.txt

用法：
    python3 scripts/translate_thess.py
    python3 scripts/translate_thess.py 215 286   # 只处理帖前
    python3 scripts/translate_thess.py 287 335   # 只处理帖后
"""
import base64, sys, time
from pathlib import Path
import fitz, requests

PDF    = Path('/Users/yanpeifa/Documents/论文/clavin_geluoni_tiesaluonijia.pdf')
OUT    = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin_raw/thess')
SERVER = 'http://10.192.2.11:8765'
DPI    = 200

START  = int(sys.argv[1]) if len(sys.argv) > 1 else 215
END    = int(sys.argv[2]) if len(sys.argv) > 2 else 335

PROMPT = (
    "请将图片中的英文文字翻译成流畅的中文。要求：\n"
    "1. 忠实原文，保持原有段落分隔\n"
    "2. 经文引用保留节号数字，如 '1. Paul and Silvanus' → '1 保罗、西拉'\n"
    "3. 拉丁文保留原文并在其后括号内附中文意思，如 'gratia（恩典）'\n"
    "4. 页码数字（单独一行的数字）和"Chapter X"章节标题直接跳过不翻译\n"
    "5. 脚注编号如 488、489 等保留原样\n"
    "6. 只输出译文，不要添加任何说明或前言"
)

doc = fitz.open(str(PDF))
OUT.mkdir(parents=True, exist_ok=True)

print(f"翻译 PDF pp.{START}–{END}，共 {END-START+1} 页")
print(f"输出: {OUT}")

ok = skip = err = 0
t0 = time.time()

for page_num in range(START, END + 1):
    out_file = OUT / f'page_{page_num:04d}.txt'
    if out_file.exists() and out_file.stat().st_size > 50:
        skip += 1
        continue

    idx = page_num - 1  # 0-indexed
    pix = doc[idx].get_pixmap(dpi=DPI)
    b64 = base64.b64encode(pix.tobytes('png')).decode()

    try:
        resp = requests.post(
            f'{SERVER}/ocr',
            json={'image': b64, 'prompt': PROMPT},
            timeout=300
        )
        resp.raise_for_status()
        text = resp.json()['text'].strip()
        out_file.write_text(text, encoding='utf-8')
        ok += 1
        elapsed = time.time() - t0
        avg = elapsed / ok
        eta = avg * (END - page_num)
        print(f'[p{page_num}] {len(text)}字  avg={avg:.0f}s  ETA={eta/60:.0f}min', flush=True)
    except Exception as e:
        err += 1
        print(f'[p{page_num}] ERROR: {e}', flush=True)
        time.sleep(5)

print(f'\n完成: {ok} 页翻译, {skip} 页跳过, {err} 页失败')
print(f'总耗时: {(time.time()-t0)/60:.0f} 分钟')
