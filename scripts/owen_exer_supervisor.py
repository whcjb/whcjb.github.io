#!/usr/bin/env python3
"""看守欧文批量中译：撞会话额度就等到额度重置，然后自动续跑。

    python3 scripts/daemonize.py /tmp/owen_batch_sup.log \
        python3 scripts/owen_exer_supervisor.py

任务清单在 scripts/owen_tasks.txt（一行一个英文页），看守与批处理读同一份。

为什么要单独一个文件
--------------------
不能把这段逻辑加进 translate_owen_batch.sh —— bash 是按字节偏移边读边执行的，
改一个正在跑的脚本会让它读到错位的位置，直接语法错误（改 translate_serial.sh
时踩过，报 `line 70: syntax error`，何西阿那批白跑）。所以看守单独成文件，
只在外面观察和拉起，绝不碰运行中的批处理。

工作方式
--------
1. 若批处理还在跑，就等它结束（不重复拉起）。
2. 结束后看它做到哪儿：4–40 里哪些还没有 zh/index.md，取最小的那个当续跑点。
   用产物判断而不是记录进度，进程被 kill / 断电都不会丢。
3. 判断该不该续：
   · 全部有 zh   → 完成，退出。
   · 退出码 42 或日志里有额度用尽字样 → 从 /tmp/cli_errors.jsonl 里读
     "resets 10:20pm (Asia/Shanghai)"，睡到那个点后 +3 分钟再拉起；
     读不到就退一步睡 30 分钟。
   · 其他非零退出 → 真故障，停下留话给人看，不自动重试（免得一个 bug
     被无限重放）。
4. 拉起后回到 1。最多连拉 MAX_RESTARTS 次，防呆。
"""
import json, os, re, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = Path('/tmp/owen_batch.log')
ERRS = Path('/tmp/cli_errors.jsonl')
TASKS = ROOT / 'scripts/owen_tasks.txt'
MAX_RESTARTS = 40
POLL = 60
LIMIT_RE = re.compile(r'额度用尽|session limit|usage limit|rate limit', re.I)
RESET_RE = re.compile(r'resets?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)', re.I)


def log(msg):
    print(f'[{datetime.now():%F %T}] {msg}', flush=True)


def batch_running():
    r = subprocess.run(['pgrep', '-f', 'translate_owen_batch.sh'],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def next_todo():
    """清单里第一个还没有中文页的条目；全有则 None。

    用产物（<页目录>/zh/index.md 是否存在）判断，不记进度文件——进程被 kill、
    断电、人为中途插一篇，状态都不会错乱。
    """
    for line in TASKS.read_text(encoding='utf-8').split('\n'):
        src = line.strip()
        if not src or not (ROOT / src).exists():
            continue
        if not (ROOT / src.replace('/index.md', '/zh/index.md')).exists():
            return src
    return None


def hit_limit():
    """日志尾部是否是撞额度停的。"""
    if not LOG.exists():
        return False
    tail = LOG.read_text(encoding='utf-8', errors='replace')[-4000:]
    return bool(LIMIT_RE.search(tail))


def reset_wait_sec():
    """从 cli_errors.jsonl 末尾找额度重置时间，返回该睡多少秒。"""
    if not ERRS.exists():
        return None
    try:
        lines = ERRS.read_text(encoding='utf-8', errors='replace').splitlines()[-40:]
    except OSError:
        return None
    for ln in reversed(lines):
        try:
            txt = str(json.loads(ln).get('resp', {}).get('result', ''))
        except Exception:
            continue
        m = RESET_RE.search(txt)
        if not m:
            continue
        h = int(m.group(1)) % 12
        if m.group(3).lower() == 'pm':
            h += 12
        mi = int(m.group(2) or 0)
        now = datetime.now()
        t = now.replace(hour=h, minute=mi, second=0, microsecond=0)
        if t <= now:                      # 已过点 → 是明天那个
            t += timedelta(days=1)
        return max(60, int((t - now).total_seconds()) + 180)   # 多等 3 分钟
    return None


def launch(nxt):
    # 不必传起始点：批处理自己会跳过已有中文页的条目
    log(f'拉起批处理，下一个未完成：{nxt}')
    subprocess.Popen(['bash', str(ROOT / 'scripts/translate_owen_batch.sh')],
                     stdout=open(LOG, 'a'), stderr=subprocess.STDOUT,
                     stdin=subprocess.DEVNULL, start_new_session=True)


def main():
    restarts = 0
    log('看守启动')
    while True:
        if batch_running():
            time.sleep(POLL)
            continue
        todo = next_todo()
        if todo is None:
            log('清单全部已有中文页，看守退出')
            return
        if not hit_limit():
            # 批处理不在跑、活儿没干完、又不是撞额度 —— 多半是真故障或被人为停掉。
            # 不自动重试：一个 bug 被无限重放比停下更糟。
            log(f'批处理已停，{todo} 尚未完成，但日志末尾不是额度用尽。'
                f'不自动续跑，请查 {LOG}')
            return
        if restarts >= MAX_RESTARTS:
            log(f'已自动续跑 {restarts} 次，达上限，停。')
            return
        wait = reset_wait_sec()
        if wait is None:
            wait = 1800
            log('未能从 cli_errors.jsonl 解出重置时间，退一步等 30 分钟')
        else:
            log(f'撞额度。等 {wait // 60} 分 {wait % 60} 秒到额度重置后续跑')
        time.sleep(wait)
        restarts += 1
        launch(todo)
        time.sleep(30)          # 给它起来的时间，免得下一轮误判成「没在跑」


if __name__ == '__main__':
    sys.exit(main())
