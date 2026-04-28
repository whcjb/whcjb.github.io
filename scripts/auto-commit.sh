#!/bin/sh
# PostToolUse hook: auto-commit calvin/*.md files after Write tool.
# Also downloads a unique background image and sets header-img.

LOG=/tmp/auto-commit-hook.log

FILE=$(cat | python3 -c "
import sys, re
data = sys.stdin.read()
m = re.search(r'\"file_path\"\s*:\s*\"([^\"]+)\"', data)
print(m.group(1) if m else '')
" 2>/dev/null)

echo "[$(date '+%Y-%m-%d %H:%M:%S')] file: $FILE" >> "$LOG"

case "$FILE" in
  */calvin/*.md) ;;
  *) exit 0 ;;
esac

cd /Users/yanpeifa/Documents/whcjb.github.io || exit 1

REL=$(python3 -c "import os; print(os.path.relpath('$FILE'))")
BOOK=$(echo "$REL" | cut -d/ -f2)
CHAP=$(basename "$REL" .md)

# --- Download background image ---
# Pool of pastoral/landscape Unsplash photo IDs (no unclean animals)
PHOTO_IDS="
1506905925346-21bda4d32df4
1472214103451-9374bd1c798e
1441974231531-c6227db76b6e
1465146344425-f00d5f5c8f07
1470770903676-69b98201ea1c
1501854140801-50d01698950b
1433086966358-54859d0ed716
1505765050516-f72dcac9c60e
1464822759023-fed622ff2c3b
1500622944204-b135684e99fd
1448375240586-882707db888b
1426604966848-d7adac402bff
1476820865390-c52aeebb9891
1464278533981-50106e6176b1
1519681393784-d120267933ba
1511497584788-876760111969
1542273917363-3b1817f69a2d
1418065460487-3e41a6c84dc5
1444464666168-49d633b86797
1500534314209-a25ddb2bd429
1518791841217-8f162f1912da
1486334823651-7b12ee6a6b52
1507003211169-0a1dd7228f2d
1508739773316-969344b9f54a
1527489672670-bf4764ee9395
"

# Pick photo based on book+chapter hash for variety
IDX=$(python3 -c "
import hashlib
h = int(hashlib.md5(b'${BOOK}${CHAP}').hexdigest(), 16)
ids = [x.strip() for x in '''$PHOTO_IDS'''.strip().split('\n') if x.strip()]
print(ids[h % len(ids)])
")

IMG_NAME="calvin-bg-${BOOK}-${CHAP}.jpg"
IMG_PATH="img/$IMG_NAME"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] downloading image $IDX -> $IMG_NAME" >> "$LOG"
curl -sL "https://images.unsplash.com/photo-${IDX}?w=1200&q=80" -o "$IMG_PATH"

# Update header-img in front matter
python3 - "$FILE" "$IMG_NAME" << 'PYEOF'
import sys, re
path, img = sys.argv[1], sys.argv[2]
content = open(path).read()
content = re.sub(r'header-img:.*', f'header-img: {img}', content)
open(path, 'w').write(content)
PYEOF

python3 /Users/yanpeifa/Documents/whcjb.github.io/scripts/update-recent.py
echo "[$(date '+%Y-%m-%d %H:%M:%S')] committing $REL" >> "$LOG"
git add "$REL" "$IMG_PATH" _data/ pages/
git commit -m "feat: add $BOOK chapter $CHAP" >> "$LOG" 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] done" >> "$LOG"
