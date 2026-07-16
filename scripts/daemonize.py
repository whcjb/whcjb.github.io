#!/usr/bin/env python3
"""daemonize.py <logfile> <cmd> [args...] —— 双fork+setsid 守护化(PPID=1), 脱离会话长跑。
macOS 无 setsid 命令, 故用 Python os.setsid()。输出重定向到 logfile。"""
import os, sys

log = sys.argv[1]
cmd = sys.argv[2:]
if os.fork() > 0:
    os._exit(0)
os.setsid()
if os.fork() > 0:
    os._exit(0)
fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
os.dup2(fd, 1)
os.dup2(fd, 2)
devnull = os.open(os.devnull, os.O_RDONLY)
os.dup2(devnull, 0)
os.execvp(cmd[0], cmd)
