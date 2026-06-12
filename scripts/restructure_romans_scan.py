#!/usr/bin/env python3
"""罗马书专用 OCR 发布脚本（包 restructure_scan_book.py 的 wrapper）。

为什么独立：罗马书 OCR 有书卷特有的怪癖（页眉笔误、版式特殊页码），
不能混进通用 restructure_scan_book.py，免得影响约翰福音 / 歌罗西书
等其他书卷的发布。

通用增强（detect_paragraph_verse / chapter boundary regex /
_strip_bible_text_dumps CUV 检查）已留在 restructure_scan_book.py。
本 wrapper 只注入罗马书特定的：
  - `加尔文集` running-header OCR 笔误 strip
  - 其他后续可能发现的 quirk

用法：
  python3 scripts/restructure_romans_scan.py --all
等价于：
  python3 scripts/restructure_scan_book.py \
    --book romans --cuv-book 45 --book-cn 罗马书 \
    --raw-dir calvin_raw/romans-scan --out-dir calvin/romans \
    --strip-line ... --all
"""
from __future__ import annotations
import sys
from pathlib import Path

# Inject romans-specific extras BEFORE importing publish module
import re

# 罗马书 OCR 特有的 fused-running-header glyphs
_ROMANS_EXTRA_HEADER_ALTS = [
    r"加尔文集",  # OCR 笔误：丢了一个 "文"
]

# 罗马书额外的整行 running-header strip patterns（无 `#` 无 `·` 的裸形式）
_ROMANS_EXTRA_STRIP_LINES = [
    r"^加尔文集\s*$",   # 笔误的整行版本
]

# Push to publish module's globals before its main runs
sys.path.insert(0, str(Path(__file__).resolve().parent))
import restructure_scan_book as pub
import restructure_john_scan_ch1 as ch1

pub._BOOK_EXTRA_HEADER_ALTS = _ROMANS_EXTRA_HEADER_ALTS

# 罗马书要求：只有显式数字前缀的段落才 promote 成 **罗马书 N:V。**
# 不要按 CUV 文本相似度自动给无数字段落加 prefix
ch1.STRICT_DIGIT_ONLY = True


def main() -> int:
    # Inject romans defaults into argv if not provided
    argv = list(sys.argv[1:])

    def has(flag):
        return any(a == flag or a.startswith(flag + "=") for a in argv)

    if not has("--book"):
        argv += ["--book", "romans"]
    if not has("--cuv-book"):
        argv += ["--cuv-book", "45"]
    if not has("--book-cn"):
        argv += ["--book-cn", "罗马书"]
    if not has("--raw-dir"):
        argv += ["--raw-dir", "calvin_raw/romans-scan"]
    if not has("--out-dir"):
        argv += ["--out-dir", "calvin/romans"]
    # Always append romans extra strip-lines (additive)
    for pat in _ROMANS_EXTRA_STRIP_LINES:
        argv += ["--strip-line", pat]

    sys.argv = [sys.argv[0]] + argv
    return pub.main()


if __name__ == "__main__":
    sys.exit(main())
