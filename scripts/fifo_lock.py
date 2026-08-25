#!/usr/bin/env python3
"""先到先得的排队锁，替换 translate_serial.sh 原来的 mkdir 自旋锁。

为什么换掉 mkdir 锁
-------------------
原来是这样：

    while ! mkdir "$LOCK" 2>/dev/null; do sleep 30; done
    trap 'rmdir "$LOCK"' EXIT

它只保证互斥，不保证顺序。每个等待者都在盲抢，锁一空谁的 sleep 恰好先醒谁
就拿走，排最久的那个可能永远抢不到。这个坑咬过两次：

  - 耶利米书 jeremiah-1 排队 33 小时（1,445 次轮询）没轮上；
  - 但以理书 2026-08-24 22:23 排到次日 09:06，10 小时 42 分一章没跑——
    哀歌和以西结轮流插队，它每次都慢半拍。

两次都是同一个原因，所以这次改成真正的 FIFO，而不是再调一次 sleep 间隔。

怎么保证 FIFO
-------------
每个等待者先取号：在队列目录里建一个名为 `<纳秒时间戳>.<pid>` 的文件。
纳秒时间戳在同一台机器上单调递增，所以文件名的字典序 == 到达顺序。
之后只轮询一件事：「比我早的号里还有活着的吗」——没有了就轮到我。

排队者崩溃不会堵死队列：号里写着 PID，轮询时用 kill(pid, 0) 探活，
进程没了就把它的号清掉。所以不需要超时兜底，也不会留下陈旧锁。

用法（在 shell 里）
-------------------
    TICKET=$(python3 scripts/fifo_lock.py take my-job $$)   # $$ 不能省
    trap 'rm -f "$TICKET"' EXIT
    python3 scripts/fifo_lock.py wait "$TICKET"
    ... 干活 ...

take 只取号立刻返回；wait 阻塞到轮到自己。分成两步是因为号必须在
trap 装好之前就拿到，否则中途被 Ctrl-C 会留下没人清的号。

    python3 scripts/fifo_lock.py queue     # 看当前队列（调试用）
"""
import errno
import subprocess
import os
import sys
import time
from pathlib import Path

QUEUE_DIR = Path('/tmp/translate_queue')
POLL_SEC = 5          # 只是探活间隔，跟公平性无关，FIFO 由号码顺序保证


def alive(pid: int) -> bool:
    """进程是否还在。EPERM 说明进程存在但不属于本用户，也算活着。

    僵尸要单独排掉：进程被杀但父进程还没 wait 时会留成 Z 状态，此时
    os.kill(pid, 0) 照样成功，光看它会把死号当活号，队列就被堵死了
    （崩溃自测里正是这样卡住 30 秒没人顶上）。所以再问一次 ps 的状态。
    """
    try:
        os.kill(pid, 0)
    except OSError as e:
        return e.errno == errno.EPERM
    try:
        st = subprocess.run(['ps', '-o', 'state=', '-p', str(pid)],
                            capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return True          # ps 不可用就宁可当它活着，不误清别人的号
    if not st:
        return False
    return not st.startswith('Z')


def parse(name: str):
    """`<ns>.<pid>[.<label>]` → (ns, pid)，解析不了的返回 None。"""
    parts = name.split('.')
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def tickets():
    """队列里所有活着的号，按到达顺序排好；顺手清掉主人已经死了的号。"""
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    out = []
    for p in QUEUE_DIR.iterdir():
        info = parse(p.name)
        if info is None:
            continue
        ns, pid = info
        if not alive(pid):
            p.unlink(missing_ok=True)      # 排队者已崩溃，别让它堵住后面的人
            continue
        out.append((ns, pid, p))
    out.sort(key=lambda t: (t[0], t[1]))
    return out


def take(label: str, pid: int = None) -> Path:
    """取号。纳秒时间戳保证单调，撞号了就往后挪一格。

    pid 必须由调用方显式传进来（shell 里就是 `$$`）。不能用 os.getppid()：
    take 通常写成 `TICKET=$(python3 fifo_lock.py take foo $$)`，命令替换会起
    一个子 shell，getppid() 拿到的是那个子 shell——它在命令替换结束的瞬间就
    没了，于是下一个排队者探活时认定此号主人已死，顺手清号直接插队，互斥当场
    失效。自测里 JOB1 还持锁 JOB2 就进来了，就是这个原因。
    """
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    if pid is None:
        pid = os.getppid()
    ns = time.time_ns()
    while True:
        p = QUEUE_DIR / f'{ns}.{pid}.{label}'
        try:
            fd = os.open(str(p), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            ns += 1
            continue
        os.write(fd, f'{label} pid={pid} at={time.strftime("%F %T")}\n'.encode())
        os.close(fd)
        return p


def wait(ticket: Path, verbose=True):
    """轮到自己才返回。判据只有一条：比我早的号都不在了。"""
    info = parse(ticket.name)
    if info is None:
        print(f'fifo_lock: 号码无法解析 {ticket.name}', file=sys.stderr)
        sys.exit(2)
    my_ns, my_pid = info
    waited = 0
    while True:
        if not ticket.exists():
            # 号被人清了（多半是本进程被判定死亡），重新取一个排到队尾。
            # 沿用原来的 pid——新号的主人还是那个 shell，不是本进程。
            print('fifo_lock: 号码丢失，重新取号', file=sys.stderr)
            ticket = take('requeue', my_pid)
            my_ns, my_pid = parse(ticket.name)
        ahead = [t for t in tickets() if (t[0], t[1]) < (my_ns, my_pid)]
        if not ahead:
            if verbose and waited:
                print(f'fifo_lock: 轮到我了，等了 {waited//60} 分 {waited%60} 秒',
                      file=sys.stderr)
            return ticket
        if verbose and waited % 300 == 0:      # 每 5 分钟报一次，别刷屏
            head = ahead[0][2].name.split('.', 2)[-1]
            print(f'fifo_lock: 前面还有 {len(ahead)} 个（队首 {head}），已等 '
                  f'{waited//60} 分', file=sys.stderr)
        time.sleep(POLL_SEC)
        waited += POLL_SEC


def show_queue():
    q = tickets()
    if not q:
        print('队列为空')
        return
    for i, (ns, pid, p) in enumerate(q):
        label = p.name.split('.', 2)[-1] if p.name.count('.') >= 2 else '?'
        age = (time.time_ns() - ns) / 1e9
        mark = '← 持锁中' if i == 0 else f'  第 {i} 位'
        print(f'{mark}  {label:<20} pid={pid:<8} 已等 {age/60:.0f} 分')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'take':
        label = sys.argv[2] if len(sys.argv) > 2 else 'job'
        pid = int(sys.argv[3]) if len(sys.argv) > 3 else None
        print(take(label, pid))
    elif cmd == 'wait':
        wait(Path(sys.argv[2]))
    elif cmd == 'queue':
        show_queue()
    else:
        print(f'未知命令 {cmd!r}', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
