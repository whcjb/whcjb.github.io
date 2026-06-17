#!/usr/bin/env python3
"""OCR a scanned PDF page-by-page via Qwen-VL endpoint.

Each PDF page is rendered to PNG, POSTed to the OCR endpoint, and written
to a per-page output file in OUT_DIR/ocr/ . Resumable: pages with an
existing non-empty output file are skipped, so a kill/restart picks up
where it stopped.

Two CLI styles supported:

  # Modern (named flags) — used by the ocr-pipeline skill.
  python3 scripts/ocr_pdf.py \
      --pdf "/Users/.../加尔文--约翰福音注释.pdf" \
      --out-dir calvin_raw/john-scan \
      --workers 4 --dpi 200 --ext md --markdown-prompt

  # Legacy (positional) — kept for compat with older one-off jobs.
  python3 scripts/ocr_pdf.py <pdf> <out_dir> [start] [end] [server]
  # ↑ writes page_NNNN.txt at DPI 150 single-threaded, default Qwen prompt.

After all pages are OCR'd, run scripts/ocr_assemble.py to merge per-page
files into a single book-level markdown.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import fitz  # PyMuPDF


OCR_URL_DEFAULT = "http://10.192.2.11:8765/ocr"

# Markdown-output prompt: ask the VLM to emit structured markdown so the
# downstream assemble step can detect chapter boundaries by `# 第N章`.
MARKDOWN_PROMPT = (
    "请仔细 OCR 这张扫描页面，按字号、字重和视觉层级输出 Markdown：\n"
    "\n"
    "【⚠️ 严格转写规则 - 最高优先级】\n"
    "- 只输出图片上能看到的字，**禁止**补全、推断、续写任何内容\n"
    "- 段尾如果是不完整词（如页末只有「保」字，下文在另一页），就输出\n"
    "  到「保」为止，**不要**自己续写「罗」或猜测后文\n"
    "- 模糊看不清的字用 □ 占位，**不要**凭语义猜测填字\n"
    "- 不要修正原文错别字、不要润色、不要补全句号\n"
    "- 如果一段在页底被截断（无句号结尾），保留原样，不要加句号\n"
    "\n"
    "【标题层级 - 按字号区分】\n"
    "- 最大字号（卷头标题，如『加拉太书注释』）用 # 开头\n"
    "- 大字号（章标题，如『第一章』、『歌罗西书纲要』）用 # 开头\n"
    "- 中等字号居中小标题（节标题、Lecture 编号）用 ## 开头\n"
    "- 不要把正文当成标题\n"
    "\n"
    "【字重和字形】\n"
    "- 黑体 / 加粗（比周围文字明显更粗）用 **文字** 包裹\n"
    "  Calvin 注释里每段开头的经文短句通常是黑体（如 **太初有道。**\n"
    "  **道成了肉身。**），必须保留\n"
    "- 斜体 / 倾斜字（italic / oblique）用 *文字* 包裹\n"
    "- 下划线用 <u>文字</u> 包裹\n"
    "\n"
    "【经文段（Bible passage block）】\n"
    "- 当一段是整段圣经经文（通常字号略小、缩进或与正文有视觉分隔，\n"
    "  连续多个 verse 编号 ①②③… 紧密相连），用 markdown blockquote\n"
    "  「> 」开头每行，整段统一格式：\n"
    "  > ① 经文1...②经文2...③经文3...\n"
    "- 单独的 verse 引用（仅一句被引用作 commentary 切入）不要 blockquote\n"
    "\n"
    "【脚注 - 区分引用和定义】\n"
    "- 脚注引用（正文中央的小数字上标）：在原位置保留 ①②③④⑤⑥⑦⑧⑨⑩\n"
    "  ⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳ 等圆圈数字字符\n"
    "- 脚注定义（页脚通常用横线分隔的小字解释）：每条独占一行，以\n"
    "  圆圈数字开头，例如：\n"
    "    ① 译注：原文是 logos...\n"
    "    ② Pringle 译本作 The Speech\n"
    "  保持每条脚注定义独立一行，不要和正文合并\n"
    "\n"
    "【其他】\n"
    "- 段落间空一行；保留原文换行结构\n"
    "- 希腊文 / 拉丁文 / 英文 / 圣经引用书卷章节（如 罗 1:16）原样保留\n"
    "- 页眉（书名、章名重复出现的小字）也输出，方便后续清理\n"
    "- 页码（如「54」「123」）独立一行输出\n"
    "- 不要添加任何说明，只输出 OCR 文本\n"
)


def ocr_request(url: str, png_bytes: bytes, prompt: str | None, timeout: int) -> str:
    body = {"image": base64.b64encode(png_bytes).decode()}
    if prompt:
        body["prompt"] = prompt
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return data.get("text", "")


def render_page(doc: fitz.Document, page_idx: int, dpi: int) -> bytes:
    pix = doc[page_idx].get_pixmap(dpi=dpi)
    return pix.tobytes("png")


def strip_inner_cjk_spaces(text: str) -> str:
    """OCR sometimes inserts a single space between adjacent CJK chars;
    drop those. Keeps spaces around ASCII / Greek / Latin tokens."""
    return re.sub(r"(?<=[一-鿿]) +(?=[一-鿿])", "", text)


def run(pdf: str, out_dir: Path, workers: int, dpi: int, ext: str,
        start: int, end: int | None, url: str, prompt: str | None,
        timeout: int, strip_spaces: bool) -> int:
    out_dir = out_dir / "ocr"
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf)
    n = len(doc)
    end_eff = n if end is None else min(end, n)
    todo: list[int] = []
    for p in range(start, end_eff):
        path = out_dir / f"page_{p+1:04d}.{ext}"
        if path.exists() and path.stat().st_size > 0:
            continue
        todo.append(p)

    print(f"[ocr] PDF: {pdf}", flush=True)
    print(
        f"[ocr] Pages: total={n} range=[{start},{end_eff}) "
        f"skipped={(end_eff-start)-len(todo)} todo={len(todo)} "
        f"workers={workers} dpi={dpi} ext={ext}",
        flush=True,
    )
    if prompt:
        print(f"[ocr] prompt: {prompt[:60]}...", flush=True)
    if not todo:
        print("[ocr] Nothing to do.", flush=True)
        return 0

    t0 = time.time()
    done = 0
    fails = 0

    def work(p: int):
        png = render_page(doc, p, dpi)
        t_start = time.time()
        text = ocr_request(url, png, prompt, timeout)
        if strip_spaces:
            text = strip_inner_cjk_spaces(text)
        return p, text, time.time() - t_start

    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(work, p): p for p in todo}
        for fut in as_completed(futs):
            p = futs[fut]
            try:
                pidx, text, dur = fut.result()
                (out_dir / f"page_{pidx+1:04d}.{ext}").write_text(text, encoding="utf-8")
                done += 1
                elapsed = time.time() - t0
                rate = done / max(elapsed, 0.1)
                eta_min = (len(todo) - done) / max(rate, 0.01) / 60
                print(
                    f"[ocr] p{pidx+1:04d} {len(text):5d}c {dur:5.1f}s "
                    f"({done}/{len(todo)} rate={rate:.2f}/s eta={eta_min:.1f}m)",
                    flush=True,
                )
            except Exception as e:
                fails += 1
                print(f"[ocr] p{p+1:04d} FAIL: {e}", flush=True)

    elapsed_min = (time.time() - t0) / 60
    print(
        f"[ocr] Done. ok={done} fail={fails} pages in {elapsed_min:.1f}m",
        flush=True,
    )
    doc.close()
    return 0 if fails == 0 else 2


def main() -> int:
    # Detect legacy positional vs. modern flag style.
    argv = sys.argv[1:]
    legacy = bool(argv) and not argv[0].startswith("-")
    if legacy:
        # python ocr_pdf.py <pdf> <out_dir> [start] [end] [server]
        if len(argv) < 2:
            print(__doc__)
            return 1
        pdf = argv[0]
        out_dir = Path(argv[1])
        start_1based = int(argv[2]) if len(argv) > 2 else 1
        end_1based = int(argv[3]) if len(argv) > 3 else None
        srv = argv[4] if len(argv) > 4 else None
        url = (srv.rstrip("/") + "/ocr") if srv else OCR_URL_DEFAULT
        return run(
            pdf=pdf,
            out_dir=out_dir,
            workers=1,
            dpi=150,
            ext="txt",
            start=start_1based - 1,
            end=end_1based,
            url=url,
            prompt=None,
            timeout=900,  # 5x the historical 180s default
            strip_spaces=True,
        )

    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out-dir", required=True, help="e.g. calvin_raw/john-scan (ocr/ subdir auto-created)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--ext", default="md", choices=["md", "txt"])
    ap.add_argument("--start", type=int, default=0, help="first page index (0-based, inclusive)")
    ap.add_argument("--end", type=int, default=None, help="last page index exclusive")
    ap.add_argument("--url", default=OCR_URL_DEFAULT)
    ap.add_argument("--timeout", type=int, default=1500,
                    help="Per-request OCR timeout in seconds (default 1500=25min). "
                         "GPU contention / large pages can stretch a single page "
                         "well past the 5-min default; 25min gives plenty of margin.")
    ap.add_argument(
        "--markdown-prompt", action="store_true",
        help="Send the Markdown-output prompt to the VLM (writes structured md)",
    )
    ap.add_argument("--prompt", default=None, help="Custom prompt (overrides --markdown-prompt)")
    ap.add_argument(
        "--no-strip-cjk-spaces", action="store_true",
        help="Keep OCR-inserted spaces between adjacent CJK characters",
    )
    args = ap.parse_args()

    if args.prompt:
        prompt = args.prompt
    elif args.markdown_prompt:
        prompt = MARKDOWN_PROMPT
    else:
        prompt = None

    return run(
        pdf=args.pdf,
        out_dir=Path(args.out_dir),
        workers=args.workers,
        dpi=args.dpi,
        ext=args.ext,
        start=args.start,
        end=args.end,
        url=args.url,
        prompt=prompt,
        timeout=args.timeout,
        strip_spaces=not args.no_strip_cjk_spaces,
    )


if __name__ == "__main__":
    sys.exit(main())
