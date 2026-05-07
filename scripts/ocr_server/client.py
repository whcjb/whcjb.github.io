#!/usr/bin/env python3
"""
OCR Client - 将PDF页面发送到OCR服务端识别，输出文本文件。
在本地Mac上运行。

用法:
  python client.py --server http://192.168.1.100:8765 --pdf /path/to/book.pdf --output /tmp/ocr_output/
  python client.py --server http://192.168.1.100:8765 --pdf /path/to/book.pdf --pages 7-100 --output /tmp/ocr_output/
"""

import argparse
import base64
import io
import json
import os
import sys
import time
from pathlib import Path

import fitz  # PyMuPDF
import requests


def pdf_page_to_base64(doc, page_num: int, dpi: int = 300) -> str:
    """Convert a PDF page to base64-encoded PNG."""
    page = doc[page_num]
    pix = page.get_pixmap(dpi=dpi)
    img_bytes = pix.tobytes("png")
    return base64.b64encode(img_bytes).decode("utf-8")


def ocr_single_page(server_url: str, img_b64: str, timeout: int = 120) -> str:
    """Send one page to OCR server and return text."""
    resp = requests.post(
        f"{server_url}/ocr",
        json={"image": img_b64},
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"])
    return data["text"]


def parse_page_range(page_str: str, total: int) -> list[int]:
    """Parse page range string like '7-100' or '5,10,20-30'."""
    pages = []
    for part in page_str.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-", 1)
            a = int(a) - 1  # convert to 0-indexed
            b = int(b) - 1
            pages.extend(range(a, min(b + 1, total)))
        else:
            pages.append(int(part) - 1)
    return [p for p in pages if 0 <= p < total]


def main():
    parser = argparse.ArgumentParser(description="PDF OCR Client")
    parser.add_argument("--server", required=True, help="OCR server URL, e.g. http://192.168.1.100:8765")
    parser.add_argument("--pdf", required=True, help="Path to PDF file")
    parser.add_argument("--output", required=True, help="Output directory for text files")
    parser.add_argument("--pages", default=None, help="Page range (1-indexed), e.g. '7-100' or '1,5,10-20'")
    parser.add_argument("--dpi", type=int, default=300, help="DPI for rendering (default: 300)")
    parser.add_argument("--timeout", type=int, default=120, help="Request timeout in seconds")
    parser.add_argument("--resume", action="store_true", help="Skip pages that already have output files")
    args = parser.parse_args()

    # Check server health
    try:
        resp = requests.get(f"{args.server}/health", timeout=10)
        health = resp.json()
        print(f"Server: {health['model']}, GPUs: {len(health['gpus'])}")
        for gpu in health["gpus"]:
            print(f"  GPU {gpu['id']}: {gpu['name']} ({gpu['memory_total_gb']}GB)")
    except Exception as e:
        print(f"ERROR: Cannot reach server at {args.server}: {e}")
        sys.exit(1)

    # Open PDF
    doc = fitz.open(args.pdf)
    total_pages = len(doc)
    print(f"PDF: {args.pdf} ({total_pages} pages)")

    # Determine pages to process
    if args.pages:
        page_list = parse_page_range(args.pages, total_pages)
    else:
        page_list = list(range(total_pages))

    print(f"Processing {len(page_list)} pages")

    # Create output directory
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Process each page
    success = 0
    errors = 0
    total_chars = 0
    start_time = time.time()

    for idx, page_num in enumerate(page_list):
        out_file = out_dir / f"page_{page_num + 1:04d}.txt"

        # Resume: skip if output exists
        if args.resume and out_file.exists() and out_file.stat().st_size > 10:
            print(f"  [{idx+1}/{len(page_list)}] Page {page_num+1}: SKIP (exists)")
            success += 1
            continue

        try:
            # Render page to image
            img_b64 = pdf_page_to_base64(doc, page_num, dpi=args.dpi)

            # Send to OCR server
            text = ocr_single_page(args.server, img_b64, timeout=args.timeout)

            # Save result
            out_file.write_text(text, encoding="utf-8")
            total_chars += len(text)
            success += 1

            elapsed = time.time() - start_time
            avg = elapsed / (idx + 1)
            remaining = avg * (len(page_list) - idx - 1)
            print(f"  [{idx+1}/{len(page_list)}] Page {page_num+1}: {len(text)} chars "
                  f"(avg {avg:.1f}s/page, ETA {remaining/60:.0f}min)")

        except Exception as e:
            errors += 1
            print(f"  [{idx+1}/{len(page_list)}] Page {page_num+1}: ERROR - {e}")

    # Summary
    elapsed = time.time() - start_time
    print(f"\nDone: {success} pages OK, {errors} errors, {total_chars} total chars")
    print(f"Time: {elapsed:.0f}s ({elapsed/60:.1f}min)")
    print(f"Output: {out_dir}/")


if __name__ == "__main__":
    main()
