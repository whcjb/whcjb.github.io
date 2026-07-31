#!/usr/bin/env python3
"""定时翻译守护进程（仅翻译，产出 raw+缓存，不发布/不提交）。
用法: python3 scripts/sched_translate_daemon.py HH:MM <book> <ch1> [ch2] ...
- Python 双 fork 守护化 → 脱离终端/会话，PPID=1(launchd)，会话结束仍存活。
- 墙钟轮询(每30s查 time.time())，macOS 挂起苏醒后自动纠偏(最多晚30s)。
- 目标时刻已过则排到明天。
- 带 mkdir 锁: 多个翻译任务串行排队，避免并发调用 claude CLI 撞会话额度。
"""
import sys, os, time, subprocess, datetime, errno

ROOT = "/Users/yanpeifa/Documents/whcjb.github.io"
LOCK = "/tmp/translate_filibi.lock"

def log(msg):
    with open(LOGF, "a") as f:
        f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {msg}\n")

if len(sys.argv) < 4:
    print("usage: sched_translate_daemon.py HH:MM book ch1 [ch2]..."); sys.exit(1)
TIME = sys.argv[1]; BOOK = sys.argv[2]; CHS = sys.argv[3:]
LOGF = f"/tmp/sched_{BOOK}_{TIME.replace(':','')}.log"

# ---- 双 fork 守护化 ----
if os.fork() > 0: sys.exit(0)     # 父退出
os.setsid()
if os.fork() > 0: sys.exit(0)     # 一级子退出 → 孙进程被 launchd 收养(PPID=1)
os.chdir(ROOT)

log(f"daemon 启动 pid={os.getpid()} ppid={os.getppid()} → 计划 {TIME} 翻译 {BOOK} 章 {CHS}")

# ---- 计算目标时刻 ----
now = datetime.datetime.now()
hh, mm = map(int, TIME.split(":"))
target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
if target <= now:
    target += datetime.timedelta(days=1)
log(f"目标时刻 {target.strftime('%Y-%m-%d %H:%M:%S')} (PPID={os.getppid()})")
target_ep = target.timestamp()

# ---- 墙钟轮询等待 ----
while time.time() < target_ep:
    time.sleep(30)
log("到点。等待翻译锁…")

# ---- 获取串行锁 ----
while True:
    try:
        os.mkdir(LOCK); break
    except OSError as e:
        if e.errno == errno.EEXIST:
            time.sleep(30)
        else:
            raise
log("已获锁，开始翻译。")
try:
    for ch in CHS:
        log(f"translate_filibi {BOOK} ch{ch} 开始")
        with open(LOGF, "a") as out:
            subprocess.run(
                ["python3", "-u", f"{ROOT}/scripts/translate_filibi.py",
                 "--book", BOOK, "--chapter", ch, "--resume"],
                cwd=ROOT, stdout=out, stderr=subprocess.STDOUT)
        raw = f"{ROOT}/calvin_raw/{BOOK}/zh_chapters/{ch}.md"
        if os.path.exists(raw):
            os.chmod(raw, 0o444); log(f"ch{ch} 完成, raw chmod 444")
        else:
            log(f"ch{ch} raw 未生成(可能撞额度), 下次 --resume 从缓存续")
finally:
    try: os.rmdir(LOCK)
    except OSError: pass
log(f"全部完成: {BOOK} {CHS}")
