#!/usr/bin/env python3
"""夜里把霍尔丹《罗马书释义》（haldane/romans）第 1–16 章译成中文，白天不占额度。

时段：每晚 02:00 开工，05:00 准点收工（2026-11-10 用户指定「定时 02:00 - 05:00 翻译」）。
与亚当斯守护不同：霍尔丹一章约 13 万字符、上百次调用，跑一章要一个多小时，「05:00 后不开新章」
会拖到天亮。所以到点就停掉正在跑的那章（缓存按段落盘，停下只丢在途的那一段），次夜 --resume 接着译。
范围：只译录入本里有的第 1–16 章。序言、导论、专论、结语、附录、七条脚注正文录入本没有，用户说先不补。

每夜做的事
----------
1. 睡到 `--start`；
2. 逐章跑 `translate_haldane.py --section <章> --resume`——它自己发布、提交、推送；
   有段落重试后仍不合格的章不写出不发布（退出码非零），跳过，次夜重数到它再试；
3. 到 `--stop` 准点停掉在跑的章（SIGTERM 整个进程组，含 claude CLI 子进程）；
4. 全部译完 → 记一笔然后退出。

用法
----
    python3 scripts/sched_haldane_zh.py             # 每晚 02:00–05:00
    python3 scripts/sched_haldane_zh.py --status
    python3 scripts/sched_haldane_zh.py --stop-now
    python3 scripts/sched_haldane_zh.py --self-test
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
ZH_RAW = ROOT / 'haldane_raw/romans/zh_chapters'
LOGF = ROOT / 'logs/haldane_translate_night.log'
PIDF = Path('/tmp/sched_haldane_zh.pid')

sys.path.insert(0, str(ROOT / 'scripts'))


def log(msg):
    with LOGF.open('a', encoding='utf-8') as f:
        f.write(f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n')


def pending():
    """还没译的章，按章序。每夜重数一遍。"""
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    return [str(c) for c in range(1, 17) if str(c) not in done]


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


def _descendants(pid):
    out = []
    for c in subprocess.run(['pgrep', '-P', str(pid)], capture_output=True, text=True).stdout.split():
        out += [int(c)] + _descendants(int(c))
    return out


def translate(sec, deadline):
    """跑一章，到 deadline 准点停。返回退出码（42 = 撞会话额度；-15 = 到点被停）。"""
    if DRY:
        log(f'[self-test] 假装译第 {sec} 章（不调 CLI）')
        time.sleep(2)
        return 0
    with LOGF.open('a', encoding='utf-8') as out:
        p = subprocess.Popen(
            [sys.executable, '-u', 'scripts/translate_haldane.py', '--section', sec, '--resume'],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        while p.poll() is None:
            if dt.datetime.now() >= deadline:
                log(f'到点，停掉第 {sec} 章（pid={p.pid}，已译段落都在缓存里）')
                tree = _descendants(p.pid) + [p.pid]
                os.killpg(p.pid, signal.SIGTERM)
                time.sleep(5)
                for pid in tree:          # claude CLI 收到 SIGTERM 不一定马上退（实测在途调用拖了几秒）
                    if _alive(pid):
                        os.kill(pid, signal.SIGKILL)
                p.wait()
                return -15
            time.sleep(10)
        return p.returncode


def run_night(stop_h, stop_m):
    """一夜的班。返回 False 表示该收工（章译完了）。"""
    todo = pending()
    if not todo:
        log('全部章都已译完，守护退出。')
        return False
    deadline = next_at(stop_h, stop_m)
    log(f'开工：还剩 {len(todo)} 章 {todo[:8]}{"…" if len(todo) > 8 else ""}；'
        f'{deadline:%m-%d %H:%M} 之后不再开新章')
    for sec in todo:
        if dt.datetime.now() >= deadline:
            log(f'到 {stop_h:02d}:{stop_m:02d} 了，今夜收工，第 {sec} 章留到明晚。')
            break
        t0 = time.time()
        rc = translate(sec, deadline)
        dur = int(time.time() - t0)
        log(f'{sec} rc={rc} 用时 {dur // 60}分{dur % 60}秒')
        if rc == -15:
            log('今夜收工。')
            break
        if rc == 42:
            log('撞会话额度（退出码 42），今夜收工。')
            break
        if rc != 0:
            log(f'{sec} 非零退出，跳过，继续下一章。')
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


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def status():
    todo = pending()
    print(f'还没译的章：{len(todo)} 章 {todo[:12]}{"…" if len(todo) > 12 else ""}')
    if PIDF.exists():
        pid = int(PIDF.read_text().strip() or 0)
        alive = _alive(pid) if pid else False
        print(f'守护进程 pid={pid} {"在跑" if alive else "已不在"}')
    else:
        print('没有守护进程在跑')
    print(f'日志：{LOGF}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--start', type=hhmm, default=(2, 0), help='每夜开工时刻')
    ap.add_argument('--stop', type=hhmm, default=(5, 0), help='到点准点收工')
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
        print('所有章都已译完，不用起守护。')
        return 0

    daemonize()
    PIDF.write_text(f'{os.getpid()}\n')
    log(f'daemon 启动 pid={os.getpid()} ppid={os.getppid()}（PPID=1 才算脱离会话）'
        f'；每夜 {a.start[0]:02d}:{a.start[1]:02d} 开工，'
        f'{a.stop[0]:02d}:{a.stop[1]:02d} 准点收工')
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
