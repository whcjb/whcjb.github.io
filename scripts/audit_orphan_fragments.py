#!/usr/bin/env python3
"""手动审计：找出可疑的孤立短段（疑似 Bible-dump 误删后的尾巴）。

误报率高，所以不放进 audit gate。建议人工浏览输出，重点看：
  - 长度 < 70 字符
  - 开头是续接词：出于/且/但/而/则/又/即/不/非/没/也/所以/因此...
  - 末尾是 `。` 闭合（孤立但语义完整）

如怀疑某段确是被 _strip_bible_text_dumps 误删后的尾巴，到 OCR
raw 文件（calvin_raw/<book>-scan/ocr/page_NNNN.md）核查上一页页尾。

Usage:
  python3 scripts/audit_orphan_fragments.py calvin/romans
"""
from __future__ import annotations
import re
import sys
from pathlib import Path


CONTINUATION_HINTS = (
    "出于", "且", "但", "而", "则", "又", "即", "不", "非", "没",
    "也", "所以", "因此", "于是", "然后", "因为", "由于", "再者",
    "其次", "另外", "此外", "至于", "至", "亦",
)


def audit(d: Path) -> int:
    n = 0
    for p in sorted(d.glob("*.md")):
        if not p.stem.isdigit():
            continue
        lines = p.read_text(encoding="utf-8").split("\n")
        i = 0
        while i < len(lines):
            if not lines[i].strip():
                i += 1; continue
            s = i
            while i < len(lines) and lines[i].strip():
                i += 1
            block = lines[s:i]
            if len(block) != 1:
                continue
            ln = block[0].strip()
            if not (30 <= len(ln) <= 80):
                continue
            if ln.startswith(("**", "[^", "<", "#", "!", "|", "{:")):
                continue
            if re.match(r"^\d{1,3}[ 、.]", ln):
                continue
            if ln[0] in '“「『':
                continue
            # Heuristic boost: starts with continuation hint
            tag = "  ORPHAN?"
            if any(ln.startswith(h) for h in CONTINUATION_HINTS):
                tag = "★ LIKELY"
            print(f"{tag} {p.name}:{s+1}  ({len(ln)}c) {ln[:60]}…")
            n += 1
    print(f"\n{n} candidate(s). Review LIKELY ★ ones first.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(audit(Path(sys.argv[1])))
