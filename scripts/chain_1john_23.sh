#!/bin/bash
cd /Users/yanpeifa/Documents/whcjb.github.io
LOG=/tmp/chain_1john.log
echo "$(date '+%H:%M:%S') 链启动，等待 ch2 翻译进程结束…" > $LOG
# 等当前 ch2 翻译结束（bare translate_filibi 进程）
while pgrep -f "translate_filibi.py --book 1john --chapter 2 --resume" >/dev/null; do sleep 20; done
echo "$(date '+%H:%M:%S') ch2 翻译已结束，串行跑 translate_serial 1john 2 3 (ch2 缓存命中→秒发, 再翻 ch3)" >> $LOG
bash scripts/translate_serial.sh 1john 2 3 >> $LOG 2>&1
# index chapters 保护成 5（CCEL ch4-5 仍可读）
python3 -c "import re;f='calvin/1john/index.html';t=open(f).read();open(f,'w').write(re.sub(r'chapters: \d+','chapters: 5',t))"
git add calvin/1john/index.html >> $LOG 2>&1
git commit -q -m "fix(1john): index chapters 保持 5（CCEL ch4-5 未译前不隐藏）" >> $LOG 2>&1 && git push -q >> $LOG 2>&1
echo "$(date '+%H:%M:%S') 链完成：1john ch2 + ch3 已发布" >> $LOG
