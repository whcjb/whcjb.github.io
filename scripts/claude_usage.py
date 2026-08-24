#!/usr/bin/env python3
"""claude CLI 调用 + token 用量计量。

所有翻译脚本都走这里调 `claude -p`，好处有二：
1. 统一带上 CLI_TRIM_FLAGS（不发工具定义 / MCP / CLAUDE.md / skills / hooks）；
2. 每次调用打印 token 用量，脚本结束时打印汇总——人工跑脚本时能直接看到花了多少。

用法：
    from claude_usage import call_cli, CLI_TRIM_FLAGS, tracker
    text = call_cli(['--model', 'opus', '--system-prompt', SYSTEM], prompt)
"""
import atexit, json, subprocess, sys, time

# 翻译是纯文本任务，用不着工具、MCP、CLAUDE.md、skills、hooks。默认调用把这些
# 全塞进每次请求的前缀——2026-08-19 实测（CLI 2.1.235）：默认 29,142 token/次，
# 加下面四个开关后 287。
#   --disallowedTools "*"   去掉全部工具定义（最大头，约 18,700 token）
#   --strict-mcp-config     不加载任何 MCP server
#   --safe-mode             不加载 CLAUDE.md / auto-memory / skills / plugins /
#                           hooks（约 5,540 token；auth、模型选择不受影响）
#   --system-prompt         由调用方传入，**替换**默认 agent 提示词（而非追加）
# 注意：prompt 必须走 stdin —— --disallowedTools 是可变参数，会把跟在后面的
# 位置参数当成工具名吞掉。
CLI_TRIM_FLAGS = ['--safe-mode', '--strict-mcp-config', '--disallowedTools', '*']


def _fmt(n):
    return f'{n:,}'


class UsageTracker:
    """累计 claude CLI 的 token 用量，脚本退出时打印汇总。"""

    def __init__(self):
        self.calls = 0
        self.failed = 0
        self.input = 0          # 未缓存的输入
        self.cache_write = 0    # cache_creation_input_tokens
        self.cache_read = 0     # cache_read_input_tokens
        self.output = 0
        self.cost = 0.0
        self.t0 = time.time()
        self._registered = False

    # ── 记账 ──────────────────────────────────────────────────────────
    def record(self, usage: dict, cost: float, label: str = '', quiet=False):
        self.calls += 1
        self.input       += usage.get('input_tokens') or 0
        self.cache_write += usage.get('cache_creation_input_tokens') or 0
        self.cache_read  += usage.get('cache_read_input_tokens') or 0
        self.output      += usage.get('output_tokens') or 0
        self.cost        += cost or 0.0
        self._register()
        if quiet:
            return
        cur_in = ((usage.get('input_tokens') or 0)
                  + (usage.get('cache_creation_input_tokens') or 0)
                  + (usage.get('cache_read_input_tokens') or 0))
        cur_out = usage.get('output_tokens') or 0
        tag = f' {label}' if label else ''
        print(f'    [tok]{tag} #{self.calls} 入 {_fmt(cur_in)}'
              f'（新缓存 {_fmt(usage.get("cache_creation_input_tokens") or 0)}'
              f' / 读缓存 {_fmt(usage.get("cache_read_input_tokens") or 0)}）'
              f' 出 {_fmt(cur_out)} = {_fmt(cur_in + cur_out)}'
              f' | 累计 {_fmt(self.total)} tok ${self.cost:.3f}', flush=True)

    def record_failure(self):
        self.failed += 1
        self._register()

    @property
    def total(self):
        return self.input + self.cache_write + self.cache_read + self.output

    # ── 汇总 ──────────────────────────────────────────────────────────
    def _register(self):
        if not self._registered:
            atexit.register(self.summary)
            self._registered = True

    def summary(self):
        if not self.calls and not self.failed:
            return
        dt = time.time() - self.t0
        m, s = divmod(int(dt), 60)
        total_in = self.input + self.cache_write + self.cache_read
        print('\n──────── claude CLI 用量汇总 ────────', flush=True)
        print(f'  调用      {self.calls} 次'
              + (f'（另有 {self.failed} 次失败重试）' if self.failed else ''))
        print(f'  输入      {_fmt(total_in)}'
              f'（未缓存 {_fmt(self.input)} / 新建缓存 {_fmt(self.cache_write)}'
              f' / 读缓存 {_fmt(self.cache_read)}）')
        print(f'  输出      {_fmt(self.output)}')
        print(f'  合计      {_fmt(self.total)} tok')
        if self.calls:
            print(f'  均次      {_fmt(self.total // self.calls)} tok')
        print(f'  费用      ${self.cost:.4f}')
        print(f'  用时      {m}m{s:02d}s')
        print('────────────────────────────────────', flush=True)


tracker = UsageTracker()


# ── 调用 ──────────────────────────────────────────────────────────────
def call_cli(extra_flags, prompt: str, timeout: int = 300, label: str = '',
             quiet: bool = False, trim: bool = True):
    """调 claude CLI，返回响应文本；顺带把 token 用量记进 tracker。

    失败（rc≠0 / 输出非 JSON / is_error）抛 RuntimeError，重试策略由调用方决定。
    """
    cmd = ['claude', '-p']
    if trim:
        cmd += CLI_TRIM_FLAGS
    cmd += list(extra_flags) + ['--output-format', 'json']
    r = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                       timeout=timeout)
    if r.returncode != 0 or not r.stdout.strip():
        tracker.record_failure()
        # rc≠0 时 stdout 往往仍是合法 JSON，里面的 result/subtype 才说明原因。
        # 早先只截 120 字符原样抛出，把「is_error + stop_reason=stop_sequence」
        # 的真实报错文本挡在了外面，白查了一轮。落盘完整 JSON 供事后翻。
        detail = ''
        try:
            d = json.loads(r.stdout)
            detail = (f' subtype={d.get("subtype")!r}'
                      f' stop_reason={d.get("stop_reason")!r}'
                      f' result={str(d.get("result"))[:300]!r}')
            dump = Path('/tmp/cli_errors.jsonl')
            with dump.open('a', encoding='utf-8') as fh:
                fh.write(json.dumps({'ts': time.strftime('%F %T'),
                                     'label': label, 'resp': d},
                                    ensure_ascii=False) + '\n')
        except Exception:
            pass
        raise RuntimeError(f'rc={r.returncode} stderr={r.stderr[:200]!r}'
                           f'{detail or " stdout=" + repr(r.stdout[:120])}')
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        # --output-format json 理应总是 JSON；真出意外就按纯文本用，不丢译文
        tracker.record_failure()
        raise RuntimeError(f'响应不是 JSON: {r.stdout[:200]!r}')
    tracker.record(d.get('usage') or {}, d.get('total_cost_usd') or 0.0,
                   label=label, quiet=quiet)
    if d.get('is_error') or d.get('subtype') not in (None, 'success'):
        raise RuntimeError(f'CLI 报错: subtype={d.get("subtype")} '
                           f'result={str(d.get("result"))[:200]!r}')
    return (d.get('result') or '').strip()
