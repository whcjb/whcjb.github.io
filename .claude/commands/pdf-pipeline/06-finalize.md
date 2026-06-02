# Step 6: index.html + commit + push

发布完所有 chapter 后的收尾。

---

## 起手 checklist

- [ ] 所有章节 md 通过 [refs/audit-gates.md](refs/audit-gates.md) 全 gate
- [ ] raw zh 已 chmod 444
- [ ] `_data/calvin_books.yml` 已 +/- 该书条目
- [ ] index.html 待加 chapter pills 已确认

---

## 1. 更新 `calvin/BOOK/index.html`

加入新章节 pills，更新进度文案：

```html
<p class="text-muted" style="margin-bottom:24px; font-size:14px;">
  中文翻译进行中，目前可阅读第 1–N 章。
</p>

<div class="ch-pills">
  <a href="{{ site.baseurl }}/calvin/BOOK/preface/" class="ch-pill" data-title="Preface">Preface</a>
  <a href="{{ site.baseurl }}/calvin/BOOK/1/" class="ch-pill" data-title="...">第 1 章</a>
  ...
</div>
```

pill 顺序：**Preface → ch1 → ch2 → ... → chN**。

---

## 2. 更新 `_data/calvin_books.yml`

```yaml
new_testament:
  - id: harmony-1
    name: 共观福音（卷一）
    chapters: 10
  - id: harmony-2
    name: 共观福音（卷二）
    chapters: 13
  - id: harmony-3
    name: 共观福音（卷三）
    chapters: 9

english:
  - id: harmony-1-en
    name: Harmony of the Evangelists (Vol. 1)
    chapters: 10
  - id: harmony-2-en
    name: Harmony of the Evangelists (Vol. 2)
    chapters: 13
  - id: harmony-3-en
    name: Harmony of the Evangelists (Vol. 3)
    chapters: 9
```

英文统一为 `Harmony of the Evangelists (Vol. N)`，中文统一为 `共观福音（卷N）`。

---

## 3. git commit message 模板

commit message 必须含 audit 数字（[refs/audit-gates.md](refs/audit-gates.md) §commit-message）：

```
feat: harmony-1 第 N 章中文翻译完成 + 发布

- 译出 N 段，缓存命中 M 段，新翻译 K 段
- raw zh chmod 444 强保留
- index pills + 1–N 章范围

Audit (calvin/harmony-1/N.md):
  ****=0 <<<END=0 split-italic=0
  zh-fm-keys=0 calvin-scripture=0
  long-para=0 hyphen-rem=0
  fn ref/def=N/N
```

**没数字 = 没合格**。

---

## 4. git commit + push 操作

```bash
# 1. 精确 stage（避免误带其他 pending change）
git add calvin/BOOK/*.md calvin/BOOK/index.html \
        calvin_raw/BOOK/zh_chapters/*.md \
        _data/calvin_books.yml

# 2. 确认 staged 列表
git diff --cached --name-only

# 3. commit + push
git commit -m "$(cat <<'EOF'
feat: ...
EOF
)"
git push 2>&1 | tail -3
```

⚠️ **不要用 `git add -A` 或 `git add .`** — 工作树可能有不相关的 pending 修改（最近 john-en 那次踩过，30 个文件被卷入）。

---

## 5. GitHub Pages 部署延迟

push 后 1–2 分钟 GitHub Pages 才会重新部署。用户强刷（⌘+Shift+R）跳过浏览器缓存。

---

## 6. 完成

任务全部结束。如有后续：
- 更多章节翻译 → 回 [04-translate-zh.md](04-translate-zh.md)
- 新书提取 → 回 [01-diagnose.md](01-diagnose.md)
- 修 bug → 查 [refs/anti-patterns.md](refs/anti-patterns.md)
