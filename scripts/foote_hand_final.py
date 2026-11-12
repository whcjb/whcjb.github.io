#!/usr/bin/env python3
"""福特《路加福音讲义》链条最末一层人工修正：hand_final_fixes.tsv。

逐条裁原生分辨率页图读定（不经模型）——段首游离墨点被读成句点、各讲经文段开头读花的开引号等。
放在最末是因为这些行前面各层都没动过、残形就是终态，按终态写串最稳。

    python3 scripts/foote_hand_final.py --apply
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import foote_image_check as I  # noqa: E402

TABLE = I.RAW / 'hand_final_fixes.tsv'

if __name__ == '__main__':
    if '--apply' in sys.argv and TABLE.exists():
        I.apply_multiline(TABLE)
