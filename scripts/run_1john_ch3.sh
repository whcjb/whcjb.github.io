#!/bin/bash
cd /Users/yanpeifa/Documents/whcjb.github.io
LOG=/tmp/run_1john_ch3.log
echo "$(date '+%H:%M:%S') 开始 1john ch3" > $LOG
bash scripts/translate_serial.sh 1john 3 >> $LOG 2>&1
python3 -c "import re;f='calvin/1john/index.html';t=open(f).read();open(f,'w').write(re.sub(r'chapters: \d+','chapters: 5',t))"
git add calvin/1john/index.html >> $LOG 2>&1
git commit -q -m "fix(1john): index chapters 保持 5" >> $LOG 2>&1 && git push -q >> $LOG 2>&1 || true
echo "$(date '+%H:%M:%S') 1john ch3 完成" >> $LOG
