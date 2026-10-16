#!/usr/bin/env python3
"""夜里把珀金斯《加拉太书注释》剩下的篇译完，白天不占额度。

时段：每晚 23:00 开工，次日 03:00 之后不再开新篇（2026-10-16 用户指定）。

⚠️ **不排 FIFO 锁**：赫奇森守护 20:00–03:00 整夜占着锁（555 页，一夜译不完），
珀金斯排在它后面要到 03:00 才轮到、正好到点收工，一篇也译不了。用户选「两本同时跑」，
所以这里与赫奇森并行调 CLI——代价是两边一起耗额度，更容易撞会话上限（退出码 42 即收工，
下一夜自动接着跑）。

2026-10-16 白天已译 85/103 篇后暂停，剩 18 篇（含最长的 6-1），约两三晚。

每夜做的事（同 sched_alexander_isaiah_zh.py）
----------------------------------------------
1. 睡到 `--start`；
2. 不排 FIFO 锁，直接开工（见上）；
3. 逐篇跑 `translate_perkins.py --section <slug> --resume`——它自己发布、提交、推送（只提交自家路径）；
4. 过了 `--stop` 就不再开新页（正在跑的那页跑完），放锁，睡到明晚；
5. 全部译完 → 记一笔然后退出。

每夜开工前按 pages_en.json 的顺序重数一遍还剩哪些页，中途手工插译或撞额度中断，
下一夜自己对上。撞额度（退出码 42）当夜立即收工。

用法
----
    python3 scripts/sched_perkins_zh.py             # 今晚 23:00 起，次日 03:00 后不开新篇
    python3 scripts/sched_perkins_zh.py --status    # 看还剩多少页、日志在哪
    python3 scripts/sched_perkins_zh.py --stop-now  # 停掉守护（不打断当前页）
    python3 scripts/sched_perkins_zh.py --self-test # 空跑，验排班/锁/收工
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
PAGES = ROOT / 'perkins_raw/galatians/pages_en.json'
ZH_RAW = ROOT / 'perkins_raw/galatians/zh_chapters'
LOGF = ROOT / 'logs/perkins_translate.log'
PIDF = Path('/tmp/sched_perkins_zh.pid')

sys.path.insert(0, str(ROOT / 'scripts'))
import fifo_lock  # noqa: E402


def log(msg):
    with LOGF.open('a', encoding='utf-8') as f:
        f.write(f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n')


def pending():
    """还没译的页，按全书顺序（卷首 → 1:1 … 21:25 → 勘误表）。每夜重数一遍。"""
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    return [p['slug'] for p in json.loads(PAGES.read_text(encoding='utf-8'))
            if p['slug'] not in done]


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
            [sys.executable, '-u', 'scripts/translate_perkins.py',
             '--section', sec, '--resume', '--jobs', '3'],
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
    log('不排 FIFO 锁（与赫奇森守护并行，见文件头说明），直接开工。')
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
    ap.add_argument('--start', type=hhmm, default=(23, 0), help='每夜开工时刻')
    ap.add_argument('--stop', type=hhmm, default=(3, 0), help='此后不再开新页')
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
