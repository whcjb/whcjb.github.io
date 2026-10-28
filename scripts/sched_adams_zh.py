#!/usr/bin/env python3
"""夜里把亚当斯《彼得后书注释》第 2、3 章译完，白天不占额度。

时段：每晚 00:00 开工，05:00 之后不再开新篇（2026-10-28 用户指定「改成夜间翻译，00:00-05:00」）。
范围：第 1 章 23 篇白天已译完（10-27）。本守护只排第 2、3 章正文各篇（slug 以 2- / 3- 开头）；
卷首扉页 title1、卷二扉页 title2、书末索引、勘误表**不在队列里**，未经用户同意不译。

不排 FIFO 锁：开这个守护时其他夜间翻译守护都已不在跑。撞会话额度（退出码 42）当夜收工、次夜续。

每夜做的事（同 sched_perkins_zh.py）
------------------------------------
1. 睡到 `--start`；
2. 逐篇跑 `translate_adams.py --section <slug> --resume --jobs 1`——它自己发布、提交、推送；
   有段落重试后仍不合格的篇不写出不发布（退出码非零），跳过，次夜会重数到它再试；
3. 过了 `--stop` 就不再开新篇（正在跑的那篇跑完）；
4. 全部译完 → 记一笔然后退出。

用法
----
    python3 scripts/sched_adams_zh.py             # 每晚 00:00 起，05:00 后不开新篇
    python3 scripts/sched_adams_zh.py --status
    python3 scripts/sched_adams_zh.py --stop-now
    python3 scripts/sched_adams_zh.py --self-test
"""
import argparse
import json
import datetime as dt
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
PAGES = ROOT / 'adams_raw/2peter/pages_en.json'
ZH_RAW = ROOT / 'adams_raw/2peter/zh_chapters'
LOGF = ROOT / 'logs/adams_translate_night.log'
PIDF = Path('/tmp/sched_adams_zh.pid')

sys.path.insert(0, str(ROOT / 'scripts'))
import fifo_lock  # noqa: E402


def log(msg):
    with LOGF.open('a', encoding='utf-8') as f:
        f.write(f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n')


def pending():
    """第 2、3 章还没译的篇，按全书顺序。每夜重数一遍。"""
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    return [p['slug'] for p in json.loads(PAGES.read_text(encoding='utf-8'))
            if p['slug'] not in done and re.match(r'[23]-', p['slug'])]


def hhmm(s):
    m = re.fullmatch(r'(\d{1,2}):(\d{2})', s)
    if not m:
        raise argparse.ArgumentTypeError(f'时刻要写成 HH:MM，给的是 {s!r}')
    return int(m.group(1)), int(m.group(2))


def next_at(h, m, after=None):
    now = after or dt.datetime.now()
    t = now.replace(hour=h, minute=m, second=0, microsecond=0)
    return t if t > now else t + dt.timedelta(days=1)


DRY = False


def translate(sec):
    """跑一章。返回 CLI 的退出码（42 = 撞会话额度）。"""
    if DRY:
        log(f'[self-test] 假装译 {sec}（不调 CLI）')
        time.sleep(2)
        return 0
    with LOGF.open('a', encoding='utf-8') as out:
        return subprocess.run(
            [sys.executable, '-u', 'scripts/translate_adams.py',
             '--section', sec, '--resume', '--jobs', '1'],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT).returncode


def run_night(stop_h, stop_m):
    """一夜的班。返回 False 表示该收工（章译完了）。"""
    todo = pending()
    if not todo:
        log('全部页都已译完，守护退出。')
        return False
    deadline = next_at(stop_h, stop_m)
    log(f'开工：还剩 {len(todo)} 页 {todo[:8]}{"…" if len(todo) > 8 else ""}；'
        f'{deadline:%m-%d %H:%M} 之后不再开新页')
    for sec in todo:
        if dt.datetime.now() >= deadline:
            log(f'到 {stop_h:02d}:{stop_m:02d} 了，今夜收工，{sec} 留到明晚。')
            break
        t0 = time.time()
        rc = translate(sec)
        dur = int(time.time() - t0)
        log(f'{sec} rc={rc} 用时 {dur // 60}分{dur % 60}秒')
        if rc == 42:
            log('撞会话额度（退出码 42），今夜收工。')
            break
        if rc != 0:
            log(f'{sec} 非零退出，跳过，继续下一篇。')
    return True


def daemonize():
    """双 fork，脱离终端与会话；孙进程被 launchd 收养（PPID=1）。"""
    if os.fork() > 0:
        os._exit(0)
    os.setsid()
    if os.fork() > 0:
        os._exit(0)
    os.chdir(ROOT)
    fd = os.open(os.devnull, os.O_RDWR)
    for k in (0, 1, 2):
        os.dup2(fd, k)


def status():
    todo = pending()
    print(f'还没译的页：{len(todo)} 页 {todo[:12]}{"…" if len(todo) > 12 else ""}')
    if PIDF.exists():
        pid = int(PIDF.read_text().strip() or 0)
        alive = fifo_lock.alive(pid) if pid else False
        print(f'守护进程 pid={pid} {"在跑" if alive else "已不在"}')
    else:
        print('没有守护进程在跑')
    print(f'日志：{LOGF}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=hhmm, default=(0, 0), help='每夜开工时刻')
    ap.add_argument('--stop', type=hhmm, default=(5, 0), help='此后不再开新页')
    ap.add_argument('--status', action='store_true')
    ap.add_argument('--stop-now', action='store_true', help='停掉守护')
    ap.add_argument('--self-test', action='store_true',
                    help='不调 CLI，立刻空跑一夜：验排班、FIFO 锁、到点收工')
    a = ap.parse_args()

    if a.self_test:
        global DRY
        DRY = True
        h, m = (dt.datetime.now() + dt.timedelta(minutes=1)).timetuple()[3:5]
        print(f'[self-test] 不调 CLI；{h:02d}:{m:02d} 之后不再开新章 → '
              f'应当只「译」几章就收工')
        run_night(h, m)
        print(f'[self-test] 完。日志：{LOGF}')
        print(f'[self-test] 队列残留：', end='')
        print('（本守护不用 FIFO 锁）')
        return 0

    if a.status:
        status()
        return 0
    if a.stop_now:
        if not PIDF.exists():
            print('没有守护进程在跑')
            return 0
        pid = int(PIDF.read_text().strip() or 0)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print(f'已给 pid={pid} 发 SIGTERM（当前正在跑的那一章不会被打断，'
                      f'它是独立子进程）')
            except ProcessLookupError:
                print(f'pid={pid} 已经不在了')
        PIDF.unlink(missing_ok=True)
        return 0

    if not pending():
        print('所有页都已译完，不用起守护。')
        return 0

    daemonize()
    PIDF.write_text(f'{os.getpid()}\n')
    log(f'daemon 启动 pid={os.getpid()} ppid={os.getppid()}（PPID=1 才算脱离会话）'
        f'；每夜 {a.start[0]:02d}:{a.start[1]:02d} 开工，'
        f'{a.stop[0]:02d}:{a.stop[1]:02d} 后不再开新页')
    try:
        while True:
            target = next_at(*a.start)
            log(f'睡到 {target:%Y-%m-%d %H:%M}')
            while dt.datetime.now() < target:
                time.sleep(30)          # 墙钟轮询：机器挂起苏醒后自动纠偏
            if not run_night(*a.stop):
                break
    finally:
        PIDF.unlink(missing_ok=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
