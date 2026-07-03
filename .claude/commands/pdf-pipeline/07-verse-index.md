# Step 7: 注释经文索引（verse-index）

**Step 7 是每一本中文注释书 publish 后的必做步骤**——不是可选项。
publish-zh 完成后必跑一次；新章节追加翻译后重跑即可。

为 calvin/<book>/ 生成"按章逐节"的索引页，点击节号胶囊跳到对应注释段。

参考实现：
- `scripts/build_romans_verse_index.py`（romans，每节一个胶囊 → `#romans-N-V`）
- `scripts/build_acts_verse_index.py`（acts，按范围锚点展开为单节胶囊；**推荐 clone 模板**）
- `scripts/build_1thess_verse_index.py`（1thess，clone acts 加 anchor 前缀替换）
- `scripts/build_1cor_verse_index.py` / `scripts/build_2cor_verse_index.py` / `scripts/build_john_verse_index.py`

## 已建 verse-index 的书

| 书 | 章数 | pills | 生成脚本 |
|---|---|---|---|
| romans | 16 | ~500 | `build_romans_verse_index.py` |
| acts | 28 | ~700 | `build_acts_verse_index.py` |
| john | 21 | ~700 | `build_john_verse_index.py` |
| 1corinthians | 16 | ~400 | `build_1cor_verse_index.py` |
| 2corinthians | 13 | ~250 | `build_2cor_verse_index.py` |
| 1thessalonians | 5 | 72 | `build_1thess_verse_index.py` |

新增中文注释书（如 1timothy / 2timothy / titus / hebrews / james / 2thess 等）publish-zh
完成后立即建 verse-index：

Checklist:
- [ ] clone `scripts/build_acts_verse_index.py` → `build_<book>_verse_index.py`
- [ ] 全局替换 acts → book_id，anchor 前缀 `id="acts-` → `id="<book_id_flat>-"`
      **注意 `book_id_flat` 是不带连字符的 id**（`1thessalonians-` 不是 `1-thessalonians-`）
- [ ] 更新中文标题、`title=` 属性、返回链接、"未列出的节号"说明文字
- [ ] `python3 scripts/build_<book>_verse_index.py` 生成 `calvin/<book>/verse-index/index.html`
- [ ] `_includes/calvin_intros/<book>.html` 末尾加 📖 经文索引按钮（橙色胶囊，模板见 §5）
- [ ] `bundle exec jekyll build --quiet` 通过
- [ ] Gate: `grep 'scripture-anchor.*id="<book>-' calvin/<book>/*.md` 必须 = 空（id 已 relocate 到 commentary-anchor）

入口：`_includes/calvin_intros/<book>.html`（橙色按钮，与首页风格统一）

---

## 0. 用户底线（写错就被打回）

> "点击胶囊要跳到对应的**注释**，而不是经文块" — 反复强调过
> "要一个胶囊一节注释，不要使用多个" — 不准 `5-8` 这种范围胶囊
> "点击28章14节的胶囊只能跳到7节附近" — 必须节级精度，不准用范围锚点

三条都必须满足。Calvin acts-filibi 译本里**注释段是按节展开的**（`**7.**`、
`**8.**`、`**11.**` 各起一段），所以每段前都要插 per-verse 锚点 `id="acts-CH-V"`，
不能只把 verse-index 链到经节范围锚点 `acts-CH-S-E`（那会跳到范围首节，
后续节都对不齐）。

若 Calvin 未对某节单独作注（如 28:14 没有 `**14.**` 段），verse-index **不显示
该节胶囊**，宁可缺一节也不要错跳。

---

## 1. 经文块 vs 注释段（理解锚点该落哪里）

calvin/<book>/N.md 的经节单元结构：

```html
<h2 class="scripture-anchor" data-ref="ACTS 1:1-2">使徒行传 1:1-2</h2>
  ↑ 隐藏标题（CSS display:hidden + scroll-margin-top:80px）

<div class="scripture-box" markdown="1">
  <p class="scripture-ref">...440101 使徒行传 1:1-2</p>
  <strong>1.</strong> 提阿非罗啊，...
  <strong>2.</strong> 直到他...
</div>
  ↑ 经文块（用户说的"经文"）

<div class="commentary-anchor" id="acts-1-1-2"></div>
  ↑ ★ 跳转目标：注释段开头

<!-- PAGE 24 -->
为要进入基督升天之后...
  ↑ 注释段（用户说的"注释"）
```

**关键事实**：如果 id 留在 `<h2 class="scripture-anchor">` 上（默认 publish 出来就是这样），
点击 verse-index 胶囊会落在**经文块之前**——用户视野里全是经文，看不到注释 → 算作没做对。

---

## 2. publish 脚本必须内联 relocate_anchors_in_body

发布脚本（如 `scripts/publish_acts_filibi_zh.py`）的 `transform()` / 主循环里必须依次跑：

```python
body = strip_frontmatter(raw)
body = clean_body(body)                       # 去 <<<END>>>，去 inline display:none
body = relocate_anchors_in_body(body)         # ★ id 从 h2 移到 scripture-box 后
```

`relocate_anchors_in_body` 的语义（参考 `scripts/publish_acts_filibi_zh.py`）：

输入：
```html
<h2 class="scripture-anchor" id="acts-1-1-2" data-ref="ACTS 1:1-2">使徒行传 1:1-2</h2>
<div class="scripture-box" markdown="1">...</div>
```

输出：
```html
<h2 class="scripture-anchor" data-ref="ACTS 1:1-2">使徒行传 1:1-2</h2>
<div class="scripture-box" markdown="1">...</div>
<div class="commentary-anchor" id="acts-1-1-2"></div>
```

**特例**（必须正确处理）：某些 h2 后面**没有** scripture-box（注释紧贴 h2），
比如 `ACTS 1:15-22` 这种长段。这时 `commentary-anchor` 紧贴 h2 之后：

```html
<h2 class="scripture-anchor" data-ref="ACTS 1:15-22">使徒行传 1:15-22</h2>
<div class="commentary-anchor" id="acts-1-15-22"></div>

<!-- 注释段 -->
```

实现要点（行级状态机，**不要写贪婪 regex**）：

```python
h2_re = re.compile(r'^(<h2 class="scripture-anchor")\s+id="(acts-[0-9-]+)"(.*?)>(.*)$')

# 对每行匹配 h2_re：
# 1. 剥 id，重写 h2
# 2. 跳过空行，看下一行是否为 <div class="scripture-box"
#    - 是：找闭合 </div>（计数 depth），在 </div> 之后追加 commentary-anchor
#    - 否：紧贴 h2 之后追加 commentary-anchor
```

**反例（已踩过）**：用一条 DOTALL regex 同时吃 h2 + scripture-box，
对没有 scripture-box 的 h2 会贪婪匹配到**下一段**的 scripture-box，把 id 错放到隔壁段后面。

**为什么必须是 `<div>` 不是 `<span>`**：kramdown 看到独立一行的 `<span>` 会把它当
inline content 包进 `<p>` 里 → 渲染出 `<p><span ...></span></p>`，外层 `<p>` 有
`margin-bottom:14px`，导致 scroll-margin-top 偏移不准、跳转后注释段不能正好贴在
navbar 下。`<div>` 是 block 级元素，kramdown 不包它，渲染出来就是裸 div，scroll 定位精准。

---

## 3. CSS：commentary-anchor 也要 scroll-margin-top

`_layouts/calvin-en.html` 必须有：

```css
.calvin-en-content .commentary-anchor {
  display: block;
  height: 0;
  line-height: 0;
  margin: 0;
  padding: 0;
  overflow: hidden;
  visibility: hidden;
  scroll-margin-top: 80px;   /* 避开 navbar */
}
```

没有 `scroll-margin-top`，跳转后注释段被 navbar 盖住——用户体感"还是没跳对"。

---

## 4. 胶囊：每节一个 + 精确跳到该节

acts-filibi 译本注释段按节展开（`**7.**`、`**8.**`、`**11.**` 各起一段），
胶囊必须节级精度——单节胶囊 + 该节专属锚点，不能用经节范围锚点（会跳到首节）。

```html
<!-- ✓ 正确：每节专属锚点 -->
<a href="/calvin/acts/28/#acts-28-7">7</a>
<a href="/calvin/acts/28/#acts-28-8">8</a>
<a href="/calvin/acts/28/#acts-28-11">11</a>
<a href="/calvin/acts/28/#acts-28-12">12</a>

<!-- ✗ 错：所有节都指向范围锚点 -->
<a href="/calvin/acts/28/#acts-28-7-14">7</a>
<a href="/calvin/acts/28/#acts-28-7-14">8</a>   ← 跳到 7
<a href="/calvin/acts/28/#acts-28-7-14">14</a>  ← 跳到 7，用户骂"无法跳到 14"
```

### 4.1 在 `**N.**` 段前插 per-verse 锚点（publish 阶段做）

publish 脚本中 `add_verse_anchors_in_body(body, ch)`：

```python
VERSE_MARK_RE = re.compile(r'^\*\*(\d{1,3})\.\*\*[\s<]')  # 段首 **N.** + 空格/<

def add_verse_anchors_in_body(body, ch):
    out, in_box, seen = [], False, {}
    for raw in body.split('\n'):
        s = raw.strip()
        # 跳过 scripture-box 内（经文用 <strong>N.</strong> HTML，不会被 RE 命中
        # 但保险起见做状态机）
        if s.startswith('<div class="scripture-box"'):
            in_box = True
            out.append(raw); continue
        if in_box:
            if s == '</div>': in_box = False
            out.append(raw); continue
        m = VERSE_MARK_RE.match(raw)
        if m:
            v = int(m.group(1))
            seen[v] = seen.get(v, 0) + 1
            # Calvin 偶尔同一节再起新段评论 → 第二次起加 -2/-3 后缀，verse-index 只用首次
            suffix = '' if seen[v] == 1 else f'-{seen[v]}'
            out.append(f'<div class="commentary-anchor" id="acts-{ch}-{v}{suffix}"></div>')
        out.append(raw)
    return '\n'.join(out)
```

**关键**：判定段首不要用 `prev_blank`——`<!-- PAGE NN -->` 紧贴 `**N.**` 之前
没有空行，会把 prev_blank 弄成 False。直接信任 "scripture-box 外的 `^**N.**[\s<]`
就是注释段起首"。

### 4.2 verse-index 只用 per-verse 锚点

build 脚本 regex：`<div class="commentary-anchor" id="acts-(\d+)-(\d+)"></div>`，
**不要**匹配 range 锚点（`acts-N-S-E` 三段式）。

```python
PER_VERSE_RE = re.compile(r'<div class="commentary-anchor" id="acts-(\d+)-(\d+)"></div>')
# 关键：尾部 \" 之前不能再有 -，否则就是 range；\d+ 不吃 -，自然只匹 per-verse
```

未单独作注的节（如 acts 28:14）→ 不进 verse-index pills 列表。
索引页 intro 里用一行小字说明 "未列出的节号表示 Calvin 未对该节单独作注"。

---

## 5. 入口按钮放书卷首页（不放全局导航）

verse-index 页面不进 `_data/calvin_books.yml`（不挤书卷列表），
仅在书卷的 intro include 里加按钮：

`_includes/calvin_intros/<book>.html` 末尾追加：

```html
<a href="{{ site.baseurl }}/calvin/<book>/verse-index/" class="<book>-verse-index-link">
  📖 经文索引 <span>按章逐节检索 Calvin 注释</span>
</a>

<style>
.<book>-verse-index-link {
  display: inline-flex;
  align-items: baseline;
  gap: 8px;
  padding: 8px 14px;
  margin-bottom: 24px;
  background: #fff3e0;
  border: 1px solid #ffb74d;
  border-radius: 4px;
  color: #e65100;
  font-size: 14px;
  text-decoration: none !important;
}
.<book>-verse-index-link:hover {
  background: #ffe0b2; border-color: #f57c00; color: #bf360c;
}
.<book>-verse-index-link span { font-size: 12px; color: #8a4a1a; opacity: 0.8; }
</style>
```

---

## 6. 校验流程

```bash
# 1. 重新发布（publish 已内联 relocate）
python3 scripts/publish_<book>_zh.py

# 2. 生成 verse-index
python3 scripts/build_<book>_verse_index.py

# 3. 校验：无残留 id="<book>-..." 在 h2 上
grep 'scripture-anchor.*id="<book>-' calvin/<book>/*.md   # 必须 = 空

# 4. 校验：commentary-anchor 数等于胶囊范围数
grep -c 'commentary-anchor' calvin/<book>/*.md

# 5. 校验：verse-index 胶囊 label 全是单节
grep 'vi-pill"' calvin/<book>/verse-index/index.html | grep -E '>[0-9]+-[0-9]+<'
# 必须 = 空（不能有 "3-5" 这种范围标签）

# 6. Jekyll 构建
bundle exec jekyll build --quiet
```

---

## 7. 反例 / 已踩过的坑

| 现象 | 根因 | Fix |
|---|---|---|
| 点击胶囊只看到经文，看不到注释 | id 还在 `<h2 class="scripture-anchor">` 上 | publish 内联 `relocate_anchors_in_body` |
| 点击 `1:23-26` 跳到 `1:15-22` 的注释 | 贪婪 regex 跨段匹配 scripture-box | 用行级状态机，遇空行才看下一行是否 scripture-box |
| 胶囊显示 `3-5` / `15-22` 范围 | 直接照搬 anchor range 当胶囊 label | 展开 `verse_to_aid` 映射，每节单独生成 pill |
| 点击 28:14 跳到 28:7 附近 | verse-index 链到范围锚点 `acts-28-7-14` | 在每个 `**N.**` 段前插 `acts-CH-V` per-verse 锚点，verse-index 只用 per-verse |
| `**N.**` 前没插 anchor，但段首明明匹配 | `<!-- PAGE NN -->` 紧贴段首破坏 prev_blank | 别用 prev_blank；scripture-box 外直接信 `^**N.**[\s<]` |
| 跳转后注释被 navbar 盖住 | `.commentary-anchor` 缺 `scroll-margin-top` | 给新 class 加 80px margin |
| scripture-anchor 上 inline `style="display:none"` | 翻译源 calvin/<book>-en/N.md 自带 | `clean_body` 用 regex 剥掉 inline style |
| 入口按钮塞进全局 calvin 列表页 | 把 verse-index 加进 `_data/calvin_books.yml` | 仅放书卷 intro include；不影响列表页 |
| 锚点 `<span>` 被 kramdown 包进 `<p>` | span 是 inline，markdown 当 inline content 处理 | 用 `<div>`：block-level，kramdown 不包 |
