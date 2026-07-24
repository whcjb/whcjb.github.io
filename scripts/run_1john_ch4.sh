#!/bin/bash
cd /Users/yanpeifa/Documents/whcjb.github.io
LOG=/tmp/run_1john_ch4.log
echo "$(date '+%H:%M:%S') 等待 ch3 任务结束…" > $LOG
while pgrep -f run_1john_ch3.sh >/dev/null || pgrep -f "1john --chapter 3 --resume" >/dev/null; do sleep 20; done
echo "$(date '+%H:%M:%S') ch3 已完成，开始 ch4" >> $LOG
bash scripts/translate_serial.sh 1john 4 >> $LOG 2>&1
python3 -c "import re;f='calvin/1john/index.html';t=open(f).read();open(f,'w').write(re.sub(r'chapters: \d+','chapters: 5',t))"
git add calvin/1john/index.html >> $LOG 2>&1
git commit -q -m "fix(1john): index chapters 保持 5" >> $LOG 2>&1 && git push -q >> $LOG 2>&1 || true
echo "$(date '+%H:%M:%S') 1john ch4 完成" >> $LOG
