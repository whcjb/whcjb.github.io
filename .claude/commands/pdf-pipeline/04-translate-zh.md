# Step 4: 中文翻译执行

英文版发布完成后，可启动中文翻译。

---

## ⚠️ 最高优先级：中文翻译产物必须强制保留

中文翻译耗时极高（单段 30–60s × 100–300 段 = 1–3 小时/章），且 Claude CLI 有会话额度限制。**绝不可以删除或无备份覆盖以下文件**：

- `calvin_raw/BOOK/zh_chapters/*.md`（中文 raw 翻译产物）
- `calvin_raw/BOOK/zh_cache/*.txt`（按 md5 缓存的逐段翻译）
- `calvin_raw/BOOK/calvin_BOOK_zh.md`（单文件模式产物）

**操作规则**：
1. 翻译完成后**立刻 `chmod 444`** 让 raw 文件只读
2. 重跑翻译前先 `chmod 644` 解锁，跑完后再 chmod 444
3. cache 目录绝不能删，**重跑全量翻译成本极高**

详见 [refs/anti-patterns.md](refs/anti-patterns.md) §M。

---

## 起手 checklist

- [ ] 英文版 raw 已稳定（grep [audit-gates.md](refs/audit-gates.md) Gate 1 全 0）
- [ ] **英文版已过 Gate 5g 跨页断句检查**：`python3 scripts/fix_page_split_paragraphs.py --dry-run calvin/BOOK-en` 必须 0 处。
      不先修就开译 = 照着断句拆译，事后修英文要把受影响章节全部 `--resume` 重跑
- [ ] `translate_filibi.py` BOOKS dict 中已有该书的 entry
- [ ] 当前 Claude CLI 会话有额度（如撞 limit 会等待重置）
- [ ] 计划是单章还是全书？全书需多次重启 + cache 复用

---

## 1. 主入口

```bash
# 全量翻译（耗时较长）
python3 -u scripts/translate_filibi.py --book BOOK

# 断点续翻（已缓存段直接读，不重新调 Claude）
python3 -u scripts/translate_filibi.py --book BOOK --chapter N --resume

# 只统计各类型行数，不翻译
python3 scripts/translate_filibi.py --book BOOK --chapter N --dry-run

# 多章模式：harmony1 / harmony2 等用 --chapter N 指定章号
```

---

## 2. 后台运行 + 5% 进度监控（推荐做法）

```bash
python3 -u scripts/translate_filibi.py --book BOOK --chapter N --resume \
  > /tmp/chN_translate.log 2>&1 &
```

然后用 Monitor 工具挂 5% 进度报告：

```bash
tail -F /tmp/chN_translate.log | python3 -u -c "
import sys, re
total = 0; uncached = 0; last = 0
for line in sys.stdin:
    m = re.search(r'共\s+(\d+)\s+段需要翻译', line)
    if m: total = int(m.group(1))
    m = re.search(r'翻译第\s+(\d+)[–-]\d+\s+段（共\s+(\d+)\s+段未缓存', line)
    if m and total:
        n = int(m.group(1))
        uncached = int(m.group(2))
        cached = total - uncached
        overall = cached + n
        pct = overall * 100 // total
        bucket = (pct // 5) * 5
        if bucket > last and bucket > 0:
            last = bucket
            print(f'[{bucket}%] chN 进度 {overall}/{total} 段', flush=True)
    if 'retry' in line.lower() or 'session limit' in line.lower():
        print('⚠ ' + line.rstrip(), flush=True)
    if '✓ 写入' in line:
        print(line.rstrip(), flush=True)
        sys.exit(0)
"
```

---

## 3. Claude CLI 会话额度处理

```
You've hit your session limit · resets 2pm (Asia/Shanghai)
```

- 脚本内置 3 次重试（5/15/30s 指数退避）——会话超限重试无效，会失败退出
- **不要轻易 kill**：cache 已保存进度，下次 `--resume` 会从 cache 继续
- **会话重置后**：`pkill -f translate_filibi`（如有残留）+ 重新启动 `--resume`

定时启动（如 19:02 重置）参考 scripts pattern（不在本 skill 范围）。

---

## 4. 翻译 system prompt 关键规则

translate_filibi.py BOOKS dict 中每个 book 都定义了 system prompt。必含：

- 「只输出译文，不加任何说明，不重复原文」
- 「保留所有脚注引用标记不变：`[^17]` `[^123]` 等」
- 「保留所有 Markdown 标记不变：`**bold**` `*italic*`」
- 「保留所有 HTML 标签不变：`<p style="...">` `<strong>` `<div>` 等」
- 「拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义」
- 「圣经书卷/人名用和合本标准译名（一长表）」
- 「章节引用格式：路加福音 1:1，马太福音 2:23（书卷名 章:节）」
- 「加尔文术语保留学术性：righteousness→义，justification→称义，...」

新书加 entry 时复制现有 entry 改本书相关词汇。

---

## 5. cache 机制

- key：每个英文段落的 md5 hash
- value：Claude 翻译结果
- 路径：`calvin_raw/BOOK/zh_cache/<md5>.txt`

**英文 raw 改动后**：MD5 变 → 该段新译。所以**重新提取英文版会 invalidate 缓存**——非必要不要重抽。

---

## 6. 完成后操作

```bash
# 1. 验证输出
ls -l calvin_raw/BOOK/zh_chapters/N.md
# 期望：size > 10KB，含完整翻译

# 2. chmod 444 强保留（关键！）
chmod 444 calvin_raw/BOOK/zh_chapters/N.md

# 3. 抽查若干段
head -50 calvin_raw/BOOK/zh_chapters/N.md
tail -30 calvin_raw/BOOK/zh_chapters/N.md
```

---

## 7. 已知翻译 bug 及修复

Claude 翻译偶尔会产生：

### 7.1 Front-matter 键名被翻译

- `chapter: N` → `章：N` 或 `章节：N`
- `prev_section: N` → `上一节：N`
- `next_label: "X"` → `下一节标签: "X"`

由 publish-zh transform 修正（见 [05-publish-zh.md](05-publish-zh.md) §1）。

### 7.2 `<<<END1>>>` 分段标记

Claude BATCH=1 偶尔吐出。由 publish-zh transform 剥除。

### 7.3 `****` abut-bold

Claude 偶尔把 `**A** **B**` 之间空格吃掉变 `**A****B**`。由 transform 中 `.replace('****', '')` 收尾。

### 7.4 `<th>` 卷名未翻译

Claude 经常保留 `<th>Matthew X:Y</th>` 原样。由 transform 改为 `<th>马太福音 X:Y</th>`。

---

## 8. 必读引用

- [refs/anti-patterns.md](refs/anti-patterns.md) §C/§D/§B/§M
- [refs/audit-gates.md](refs/audit-gates.md) Gate 2

---

## 9. 进入下一步

raw zh 完成 → [05-publish-zh.md](05-publish-zh.md)
