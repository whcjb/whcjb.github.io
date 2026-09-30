#!/usr/bin/env python3
"""夜里把亚历山大《以赛亚书注释》剩下的章一章一章译完，白天不占额度。

实测一章 **$2、21 分钟、34 次 CLI 调用**（第 1 章 6.0 万字符）。剩 63 章
折下来约 $125、22 小时——所以分几夜跑，而不是一口气占满白天。

每夜做的事
----------
1. 睡到 `--start`；
2. 取 FIFO 号排队（`scripts/fifo_lock.py`），轮到自己才开工——别的翻译任务
   可能也在跑，**并发调 claude CLI 会一起撞会话额度**；
   用 FIFO 不用 mkdir 自旋锁：后者只保证互斥不保证顺序，排最久的可能永远
   抢不到（耶利米书饿死过 33 小时，[[feedback_recurring_bug_change_mechanism]]）；
3. 逐章跑 `translate_alexander_isaiah.py --section N --resume`——那个脚本自己
   会发布、提交、推送（[[feedback_translate_autopublish]]），这里只管排班；
4. 过了 `--stop` 就**不再开新章**（正在跑的那章跑完），放锁，睡到明夜；
5. 章全译完 → 记一笔然后退出，不再空转。

每夜开工前重新数一遍还剩哪些章，所以中途手工插译几章、或某夜撞额度中断，
下一夜自己会对上，不需要改参数。

撞额度（退出码 42）当夜立即收工：额度是会话级的，接着跑只会一章一章白撞。

CLI 上下文
----------
翻译走 `translate_filibi.call_claude → claude_usage.call_cli`，**自动带四个
开关**（`--safe-mode --strict-mcp-config --disallowedTools '*' --system-prompt`），
不发工具定义 / MCP / CLAUDE.md / skills / hooks。实测对照：

    带开关：  输入 264 token
    不带：    输入 33,675 token（新建缓存 17,303 + 读缓存 16,370）

本脚本不自己拼 claude 命令，就是为了不把那 3 万 token 的上下文带回去。

用法
----
    python3 scripts/sched_alexander_isaiah_zh.py            # 今晚 23:00 起，07:00 收
    python3 scripts/sched_alexander_isaiah_zh.py --start 22:30 --stop 06:30
    python3 scripts/sched_alexander_isaiah_zh.py --status   # 看还剩多少章、日志在哪
    python3 scripts/sched_alexander_isaiah_zh.py --stop-now # 停掉守护（不打断当前章）
    python3 scripts/sched_alexander_isaiah_zh.py --self-test # 空跑一夜，验排班/锁/收工
"""
import argparse
import datetime as dt
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/Users/yanpeifa/Documents/whcjb.github.io')
SRC = ROOT / 'alexander/isaiah'
ZH_RAW = ROOT / 'alexander_raw/isaiah/zh_chapters'
LOGF = Path('/tmp/sched_alexander_isaiah_zh.log')
PIDF = Path('/tmp/sched_alexander_isaiah_zh.pid')

sys.path.insert(0, str(ROOT / 'scripts'))
import fifo_lock  # noqa: E402


def log(msg):
    with LOGF.open('a', encoding='utf-8') as f:
        f.write(f'{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}\n')


def pending():
    """还没译的章，按章号顺序。每夜重数一遍，手工插译过的自动跳过。"""
    done = {p.stem for p in ZH_RAW.glob('*.md')}
    return [p.stem for p in sorted(SRC.glob('[0-9]*.md'), key=lambda x: int(x.stem))
            if p.stem not in done]


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
        log(f'[self-test] 假装译第 {sec} 章（不调 CLI）')
        time.sleep(2)
        return 0
    with LOGF.open('a', encoding='utf-8') as out:
        return subprocess.run(
            [sys.executable, '-u', 'scripts/translate_alexander_isaiah.py',
             '--section', sec, '--resume'],
            cwd=ROOT, stdout=out, stderr=subprocess.STDOUT).returncode


def run_night(stop_h, stop_m):
    """一夜的班。返回 False 表示该收工（章译完了）。"""
    todo = pending()
    if not todo:
        log('全部章节都已译完，守护退出。')
        return False
    deadline = next_at(stop_h, stop_m)
    log(f'开工：还剩 {len(todo)} 章 {todo[:8]}{"…" if len(todo) > 8 else ""}；'
        f'{deadline:%m-%d %H:%M} 之后不再开新章')
    ticket = fifo_lock.take('alexander-isaiah-zh', os.getpid())
    try:
        fifo_lock.wait(ticket, verbose=False)
        log('已轮到，开始翻译。')
        for sec in todo:
            if dt.datetime.now() >= deadline:
                log(f'到 {stop_h:02d}:{stop_m:02d} 了，今夜收工，第 {sec} 章留到明夜。')
                break
            t0 = time.time()
            rc = translate(sec)
            dur = int(time.time() - t0)
            log(f'第 {sec} 章 rc={rc} 用时 {dur // 60}分{dur % 60}秒')
            if rc == 42:
                log('撞会话额度（退出码 42），今夜收工。')
                break
            if rc != 0:
                log(f'第 {sec} 章非零退出，跳过，继续下一章。')
    finally:
        try:
            ticket.unlink()
        except OSError:
            pass
        log('已放锁。')
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
    print(f'还没译的章：{len(todo)} 章 {todo[:12]}{"…" if len(todo) > 12 else ""}')
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
    ap.add_argument('--stop', type=hhmm, default=(7, 0), help='此后不再开新章')
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
        fifo_lock.show_queue()
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
        print('所有章节都已译完，不用起守护。')
        return 0

    daemonize()
    PIDF.write_text(f'{os.getpid()}\n')
    log(f'daemon 启动 pid={os.getpid()} ppid={os.getppid()}（PPID=1 才算脱离会话）'
        f'；每夜 {a.start[0]:02d}:{a.start[1]:02d} 开工，'
        f'{a.stop[0]:02d}:{a.stop[1]:02d} 后不再开新章')
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
