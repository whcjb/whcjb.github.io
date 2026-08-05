# 马太亨利注释（mhenry）处理指南

处理 `mhenry/` 目录下马太亨利圣经注释（中文版）的统一规范、脚本接口和错误防御手册。每一次接到 mhenry 相关任务（新书卷上传、前言修复、章节修订、样式调整、批处理脚本等）前必须读完本文，按里面的规则执行；以下规则均由真实事故反推得出，违规会重蹈覆辙。

---

## 0. 项目位置和文件清单

- 站点根：`/Users/yanpeifa/Documents/whcjb.github.io`
- 注释目录：`mhenry/<book_id>/`
  - `preface.md` — 书卷前言（layout: `mhenry-preface`）
  - `1.md`、`2.md` … — 各章（layout: `mhenry-chapter`）
  - `index.html` — 章节列表入口
- 新约统一钻石风 CSS：`_includes/mhenry-diamond.html`（§1.7）
- 书目元数据：`_data/mhenry_books.yml`（id、Chinese name、chapters 数）
- 布局：`_layouts/mhenry-preface.html`、`_layouts/mhenry-chapter.html`、`_layouts/mhenry-book.html`
- PDF 源（**不在仓库内**）：`~/Documents/论文/matthew_henry/`，文件名形如 `18马太亨利完整圣经注释 约伯记01-21.pdf`
- 常用脚本（全在 `scripts/`）：
  - `mhenry_pdf_to_md.py` — PDF→md 全量转换
  - `optimize_preface.py` — 把旧版 preface.md 升级为哈该书样式
  - `fix_contaminated_prefaces.py` — 修复前言里混入章节正文的污染
  - `audit_mhenry_overview.py` — 体检章节综述质量
  - `qa_mhenry.py` — 章节内容/经文/截断质检
  - `fix_mhenry_verse_leak.py` — 修复经文泄漏到注释体
  - `inject_date_headings.py` — 注入日期大标题
  - `propagate_verse_style.py` — 经文块字体/配色推广
  - `fix_henry_footnotes.py` — 章末脚注编号重排/双向跳转链接（只改链接不碰内容）
  - `fix_nt_footnotes.py` — 对照 PDF 字号重建脚注内容、修脚注↔正文双向错乱（全 66 卷，§4.12）
  - `theme_book_index.py` — 书卷目录页 `index.html` 主题色注入（§4.8）
  - `bootstrap_ezra_preface.py` — 缺 `preface.md` 的单卷修复参考（§4.9）
  - `assign_nt_headers.py` — 新约 27 卷页头风景图分配（§1.8）
  - `realign_john.py` — 约翰福音章节结构对齐 Matthew 风的一次性修复（§4.9）

---

## 1. 最高原则（违反会被立刻打回）

### 1.1 一切格式问题必须先对照 PDF 原文

来源：`feedback_pdf_verify_before_change.md`。

- 用户指出格式有误时，**先读对应 PDF 页**确认正确格式，再动手。
- **禁止猜测**：用户否定 A 方案不等于 B 方案正确；B 方案同样需要 PDF 核实。
- 不知道 PDF 路径时直接问用户，不要自己假设。

PDF 抽取使用 PyMuPDF：
```python
import fitz
doc = fitz.open(pdf_path)
text = doc[page_index].get_text()  # 0-indexed
```

### 1.2 禁止编造

来源：`feedback_no_fabrication.md`。

- 不得随意编造人名、日期、英文名、生卒年。
- 前言里的人物（如"哈蒙德博士1605-1660"）来自 PDF 脚注，必须原文回查。

### 1.3 每本书独立配色，禁止串色

来源：`feedback_book_style_isolation.md`。

- 字体、小标题、经文格式、emblem/title-block 配色等样式按书隔离。
- 复制 1.md 的 `<style>` 块到 preface.md 时，**保留该书自己的色板**——绝不能把哈该书的色板套到创世记上。
- 例外只在用户明确说"共用"时才成立。

### 1.4 中文翻译产物强制保留

来源：`feedback_translation_raw_preserve.md`。

- `zh_chapters/`、`zh_cache/`、`calvin_*_zh.md` 等翻译产物绝不可删除或无备份覆盖。
- 这条对 mhenry 本身也成立：mhenry 章节本身就是翻译产物，重跑成本极高，**任何批处理脚本必须先 dry-run，且对单个文件做 diff 验证后再批跑**。

### 1.5 编辑后自检 HTML

来源：`feedback_mhenry_self_check.md`。

- 编辑 mhenry 文件后必须自检：HTML 标签是否闭合、是否有弯引号（"" '' 写成 `&ldquo;`、`&rdquo;` 或直接 `"`）、`<p>`/`<div>` 是否成对。
- 不要让用户先发现错误。

### 1.6 日期字段必须精确到分钟且为真实时间

来源：根 `CLAUDE.md`。

- 所有 mhenry 章节/前言的 front matter `date` 字段为 `YYYY-MM-DD HH:MM`，**不能只写日期**。
- 新建文件用 `date '+%Y-%m-%d %H:%M'` 取当前真实时间；已有文件的 date **不要改**。

---

## 1.7 主题风格：旧约水晶 / 新约钻石（不要混用）

mhenry 的视觉风格按约分两套：

| | 旧约 (39 卷) | 新约 (27 卷) |
|---|---|---|
| 风格名 | 水晶透明风 (`水晶`) | 钻石风 (`diamond`) |
| 调色板 | **每书独立**，PDF 提取的暖色系（金/绿/橙/紫…）| **新约统一**，银蓝白冷色系 |
| 圆角 | 12-16px（柔和）| 3-6px（棱角） |
| emblem 字符 | `◆` 实心方块 | `◇` 菱形 |
| 实现 | 每书 `1.md`/`preface.md` 顶部内联 `<style>` + `index.html` 的 `custom_style:` | `_includes/mhenry-diamond.html`，三个 layout 用 Liquid 条件加载 |
| 字体强调 | "Ma Shan Zheng" 楷草 | "Cormorant Garamond" 欧文衬线 + "Klee One" |

**新约的实现关键文件**：
- `_includes/mhenry-diamond.html` — 钻石风全套 CSS（章节页 + 前言页 + 书卷目录页 三套选择器都在一个文件里）
- `_layouts/mhenry-chapter.html` / `mhenry-preface.html` / `mhenry-book.html` 末尾各有一段 Liquid：
  ```liquid
  {% assign nt_books = "matthew,mark,luke,john,acts,romans,1corinthians,2corinthians,galatians,ephesians,philippians,colossians,1thessalonians,2thessalonians,1timothy,2timothy,titus,philemon,hebrews,james,1peter,2peter,1john,2john,3john,jude,revelation" | split: "," %}
  {% if nt_books contains page.book_id %}{% include mhenry-diamond.html %}{% endif %}
  ```

**改动方式**：
- 改新约统一配色 → 编辑 `_includes/mhenry-diamond.html`（一处即生效全部 27 卷）。
- 改某卷旧约配色 → 改该书 `1.md`（章节）/ `preface.md`（前言）顶部的内联 `<style>`，再用 `theme_book_index.py` 同步 `index.html`（§4.8）。

**禁忌**：
- 不要在 NT 书的 `1.md`/`preface.md` 里塞自定义 `<style>`——会与 `mhenry-diamond.html` 重复 / 冲突。
- 不要往 `_includes/mhenry-diamond.html` 里加 `#xxx-col` 之类 OT 专属选择器——NT 用同一套，加了变成"两套都套"的混乱。
- 新增书卷时如果它属于 NT，**不需要**做 §4.8 的 `theme_book_index.py`；只需保证它在上面那段 Liquid 的 `nt_books` 列表里。

## 1.8 页头背景图（header-img）

每个 mhenry 页面（章节/前言/书卷目录）的 front matter `header-img:` 字段决定顶部横幅图。**新约 27 卷已要求每一章都用风景图**（2026-06 起），具体由 `scripts/assign_nt_headers.py` 按确定算法分配，**不要手工乱改**。

**新约图库（NT 专属，132 张，全部从 Unsplash 下载）**：
- `nt-bg-001.jpg` … `nt-bg-132.jpg`
- 来源：`scripts/auto-commit.sh` 里用过的 Unsplash 直链 CDN（`https://images.unsplash.com/photo-{id}?w=1200&q=80`，**不需要 API key**）
- 搜索关键词：landscape / mountain / forest / sea / lake / sunset-landscape / valley / river / desert / sky / hills-meadow（避开人物、不洁净动物）
- 每张图 ↔ Unsplash photo ID 的映射记录在 `_data/nt_image_provenance.yml`，万一图被删可凭 ID 重抓

**旧约图库（OT 专属，60 张，原仓库已有）**：
- `mhenry-land-21.jpg` … `mhenry-land-55.jpg`（35 张）
- `psalm-bg-36.jpg` … `psalm-bg-54.jpg`（19 张）
- `psalm-bg-mountain.jpg` / `valley` / `forest` / `cattle` / `sheep1` / `sheep2`（6 张）

**OT 和 NT 图池严格分离**，不混用——免得新旧约视觉串味。

**分配规则**（脚本固化的算法，幂等）：
```
book_offset = sha1(book_id) % 60       # 每卷起点
slot:    preface→0, index.html→1, k.md→k+1
image  = pool[(book_offset + slot) % 60]
```
- 每卷从池里某个偏移开始，按 preface → index → 1.md → 2.md → … 顺序循环取图。
- 不同卷起点不同，相邻卷之间不会撞图；同卷的相邻章节图按池序排列，视觉上有"逐渐过渡"的感觉。
- 因为 27 卷 × 平均 ~10 章 > 60 张，全站会有图片重复使用，**但同一卷内不会重复**（除非该卷超过 60 章——目前 max 是 matthew 28 章）。

**踩坑**：
- **图必须真存在**：原本 `revelation` / `2peter` 等用了 `mhenry-land-56..61` 这些**不存在的图片**，前端是默认色块。`assign_nt_headers.py` 会把每张图都路径校验后放进池子。新加图片直接放 `img/`，命名遵循上面 3 类前缀即可被脚本自动捡到。
- **stub 前言里有「孤立 header-img」行**：早期 14 卷 NT 书的 `preface.md` 前言体里有一行 `header-img: …` 字面输出在正文（不在 front matter）。已批量清理；以后任何写 mhenry 文件的脚本都要避免把 yml 字段误塞进 body。
- **不要在 OT 文件上跑这个脚本**：脚本里硬编码了 `NT_BOOKS` 白名单，但任何"图片重新分配"的需求都该明确分约划分。
- **"使用风景图"的真实含义是「下载新风景图」**：用户曾要求"NT 每章用风景图"，第一反应是从现有 60 张 OT 池里循环，结果被骂"我让你去下载新图，不是让你使用旧图"。**正确做法**：去 Unsplash 搜（landscape / mountain / sea …），WebFetch 抓 `<img src="https://images.unsplash.com/photo-{id}?..." />` 里的 ID，过滤格式 `\d{13}-[a-f0-9]{12}`，HEAD 验证 200，再 curl 下载。整条流水线写在了 `_data/nt_image_provenance.yml`（132 张 ID 映射）。

**新增 / 补充图片的流程**：
1. WebFetch `https://unsplash.com/s/photos/<keyword>` 拉 photo ID。
2. 过滤格式 + curl HEAD 验证 200。
3. 与 `_data/nt_image_provenance.yml` 已记录的去重，避免同图重抓。
4. `curl -sL --max-time 60 'https://images.unsplash.com/photo-{id}?w=1200&q=80' -o img/nt-bg-{NNN}.jpg`，编号续上当前最大。
5. 追加映射到 `_data/nt_image_provenance.yml`。
6. 重跑 `assign_nt_headers.py`（脚本会自动捡到新加的 `nt-bg-*.jpg`）。

**用法**：
```bash
python3 scripts/assign_nt_headers.py --dry-run   # 预览 260 个文件的分配
python3 scripts/assign_nt_headers.py             # 实际写入
```
跑完跑 §7 体检 + `bundle exec jekyll build`。

## 2. 文件结构契约

### 2.1 章节 md 的标准框架（1.md / 2.md / …）

```yaml
---
layout: mhenry-chapter
book_id: haggai
book_name: 哈该书
chapter: 1
total_chapters: 2
header-img: mhenry-land-37.jpg
date: 2026-05-20 17:14
---

<style>
@import url('https://fonts.googleapis.com/css2?family=Klee+One:wght@400;600&family=Ma+Shan+Zheng&display=swap');

/* ── <book_id> 水晶透明风 ──────────────────────────── */
#mhenry-col { background: linear-gradient(160deg, ...) !important; ... }
.mh-nav-bar { ... }
/* （此处约 370 行，每本书有自己的色板） */
</style>

## 第一章

<div class="mh-overview">
本章在前言以后：1. ……。2. ……。
</div>

<div class="mh-date-heading">日期大标题（主前 520 年）</div>

<div class="mh-unit">
<div class="mh-verse">
1 经文…… 2 经文……
</div>
<div class="mh-unit-body">

注释正文，第一段……

I. 第一大点……

II. 第二大点……

</div>
</div>

<!-- 后续 mh-unit ……  -->
```

关键 class（**所有章节都用同一套，别自己造**）：

| class | 用途 |
|---|---|
| `mh-overview` | 本章综述（顶部摘要） |
| `mh-date-heading` | 段落级日期标题 |
| `mh-unit` | 经文+注释一组 |
| `mh-verse` | 经文块（繁体和合本，毛笔楷书字体） |
| `mh-unit-body` | 注释正文容器 |
| `mh-l1` / `mh-l2` / `mh-l3` | 罗马数字 / 阿拉伯数字 / 圆括号数字的多级大纲 |
| `mh-label` | 大纲标签（"I."、"1."、"（1）"） |

### 2.2 前言 md 的标准框架（preface.md，"哈该书样式"）

**这是 2026-06 已统一的标准格式**。30 卷未优化的旧约前言已经一键升级到这套结构。

```yaml
---
layout: mhenry-preface
book_id: haggai
book_name: 哈该书
header-img: mhenry-land-37.jpg
date: 2026-05-20 17:14
---

<style>
/* 章节级水晶风样式：直接复制自该书 1.md 的 <style>（含 #mhenry-col、.mh-nav-bar、.mh-unit 等） */
/* 这个 <style> 用来让前言页跟章节页底色一致 */
@import url('https://fonts.googleapis.com/css2?...');
...约 370 行...
</style>

<div class="preface-wrap">

<div class="preface-emblem">✦</div>

<div class="preface-title-block">
  <div class="preface-label">先知简介</div>         <!-- 见 §2.3 分类 -->
  <div class="preface-book-name">哈该书</div>
  <div class="preface-sub">马太亨利注释 · 书卷导言</div>
</div>

<div class="preface-divider"><span>◆</span></div>

<div class="preface-body">
<p>前言正文……</p>
</div>

<div class="preface-closing">✦ &ensp; ✦ &ensp; ✦</div>

</div>

<style>
/* 前言专属装饰：.preface-emblem、.preface-title-block、.preface-label、
   .preface-divider、.preface-body、.preface-closing 等 */
/* padding 关键值：.preface-title-block 和 .preface-body 必须是 padding: 0
   （包裹结构已自带间距，不归零会双重内边距） */
</style>
```

**易错点**：
- 第二个 `<style>` 里的 `.preface-title-block` 与 `.preface-body` 必须 `padding: 0`；旧版用 `padding: 20px 24px 22px` / `padding: 24px 26px`，加上新版包裹后会出现双重内边距。
- 标签（`<div class="preface-label">`）按书卷类型分类，见下表。

### 2.3 preface-label 按书卷类型分类

| 类别 | 标签 | 书卷 |
|---|---|---|
| 律法书（摩西五经） | `律法简介` | genesis, exodus, leviticus, numbers, deuteronomy |
| 历史书 | `历史简介` | joshua, judges, ruth, 1samuel, 2samuel, 1kings, 2kings, 1chronicles, 2chronicles, ezra, nehemiah, esther |
| 智慧/诗歌书 | `智慧简介` | job, psalms, proverbs, ecclesiastes, songofsolomon |
| 大先知 + 小先知 | `先知简介` | isaiah, jeremiah, lamentations, ezekiel, daniel, hosea, joel, amos, obadiah, jonah, micah, nahum, habakkuk, zephaniah, haggai, zechariah, malachi |
| 福音书 | `福音简介` | matthew, mark, luke, john |
| 历史 | `历史简介` | acts |
| 书信 | `书信简介` | romans … jude |
| 启示 | `启示简介` | revelation |

> **耶利米哀歌**虽属诗歌，因紧随耶利米书且常与先知书合并讨论，归 `先知简介`。

---

## 3. 上传新书卷的标准流程

```bash
python3 scripts/mhenry_pdf_to_md.py <pdf_path> <book_id> <book_name_zh> <header_img> \
    <preface_pages> <chapter1_pages> <chapter2_pages> ...
```

参数格式：
- `preface_pages`：`<preface>:<start_page>:<end_page>`，或单页 `<preface>:<single_page>`
- `chapter_n_pages`：`<chapter_num>:<start_page>:<end_page>`，单页同上
- 页码 **1-indexed**

例（哈该书）：
```bash
python3 scripts/mhenry_pdf_to_md.py \
    ~/Documents/论文/matthew_henry/马太亨利完整圣经注释-哈该书.pdf \
    haggai 哈该书 mhenry-land-37.jpg \
    2:2 1:3:5 2:6:11
```

脚本会：
1. 用 PyMuPDF 抽文字；扫描件回退 OCR（http://10.192.2.11:8765/ocr，见 `reference_qwen3_api.md`）。
2. 识别日期、经文块、罗马数字大纲、脚注。
3. 输出符合 §2.1 模板的 md 文件。

跑完之后必须：
1. `python3 scripts/qa_mhenry.py <book_id> <pdf_path> <chapter_pages>` 跑质检。
2. `python3 scripts/audit_mhenry_overview.py` 检查 `mh-overview` 质量。
3. 手工对照 PDF 抽样 1～2 章。
4. 在 `_data/mhenry_books.yml` 增加书目条目（id、name、chapters）。

---

## 4. 历史踩过的坑（按优先级）

### 4.1 前言被章节正文污染（job/psalms/proverbs/ecclesiastes/songofsolomon）

**症状**：前言末尾出现 "在这里注定要" 之类断在第 3 章中间的怪句。前言的 `<p>...</p>` 里塞进了 1-3 章正文。

**根因**：早期批处理脚本没识别 "约伯记第一章" 等章节标题，把所有页面文本灌进了前言体。

**修复方案**：`scripts/fix_contaminated_prefaces.py` 已经写好，思路是从 PDF 重抽 → 用首尾锚点切片：

```python
specs = [
    ('job',           pdf_path, '约伯记这卷书自成一体',         '约伯记第一章'),
    ('psalms',        pdf_path, '摆在我们面前的是整卷旧约',     '这是一首关于善恶'),
    ('proverbs',      pdf_path, '摆在我们面前的是，I. 一位新作者', '箴言第一章'),
    ('ecclesiastes',  pdf_path, '我们仍与那些快乐的臣子',       '传道书第一章'),
    ('songofsolomon', pdf_path, '我们坚信圣经都是神所默示',     '雅歌第一章'),
]
```

`start_phrase` 取**前言正文第一句的前 10～15 字**（避开 "简介" 这种会出现在 TOC 里的标题词）；`end_phrase` 取**章节标题**（"约伯记第一章" 之类的整行）。

**清洗步骤**（已内置）：
- 去掉每页页眉 `马太亨利完整圣经注释[^\n]*\n` 和页脚 `第\s*\d+\s*页\s*\n`
- 去掉脚注定义行 `^\d+[^\n]+（\d{4}-\d{4}）`
- 去掉跨页的孤立章节标记 `\n第一篇\s*\n`
- 把 PDF 硬换行（句内未结束就被换行）合并为单行：上一行末尾不是 `。！？.!?` 时，下一行直接拼接

**预防**：
- 写 PDF 转 md 脚本时，**必须显式找章节标题作为边界**，不能用页码硬切。
- 转完之后跑：
  ```bash
  for book in mhenry/*/; do
    book=$(basename "$book")
    [ -f "mhenry/$book/preface.md" ] || continue
    size=$(wc -c < "mhenry/$book/preface.md")
    ch1=$(grep -cE '记第一章|书第一章|福音第一章' "mhenry/$book/preface.md")
    if [ "$ch1" -gt 0 ] || [ "$size" -gt 30000 ]; then
      echo "[SUSPECT] $book size=$size ch1=$ch1"
    fi
  done
  ```
  `[SUSPECT]` 出现就要重抽。

### 4.2 双重迁移导致样式块重复 / 装饰 CSS 丢失

**症状**：跑 `optimize_preface.py` 后某卷字符数突然翻倍，搜不到 `.preface-emblem` 等 CSS。

**根因**：脚本对已经迁移过的文件再跑一次，会把"已迁移文件里 §2.2 第一个 `<style>`（章节风）"当成"原装饰风格"读出来，结果输出里章节风出现两次，装饰风丢失。

**预防与修复**：
- 跑批处理前先检查："如果文件已有 `class="preface-wrap"`，跳过"。
- 已损坏的卷：`git checkout HEAD -- mhenry/<book>/preface.md` 还原，再单跑：
  ```bash
  python3 scripts/optimize_preface.py <book>
  grep -cE '^\.preface-(emblem|title-block|label|divider|closing|body|sub|book-name)' mhenry/<book>/preface.md
  # 必须输出 13
  ```
- 永远不要在 stash/pop 期间跑迁移脚本。`git stash` + 脚本运行 + `git stash pop` 的组合极易把"清白"和"已迁移"两个状态搅在一起。

### 4.3 经文跨页截断，经文节号泄漏到注释体

**症状**：`mh-unit-body` 开头直接是 "1 那日……" 这种经文，而不是注释文字。`mh-verse` 末尾不是句号也不是 `」`，而是句中停止。

**修复**：`scripts/fix_mhenry_verse_leak.py`；质检用 `scripts/qa_mhenry.py` 的 `[A]`、`[B]` 项目。

**预防**：PDF 抽取时按"卷名头"+"`;`-分隔引用串"分组（详见 `pdf-to-structured-txt` skill §0.1）。经文识别要识别整个跨页段而不是单页。

**另一种反向截断（注释体开头被吞，质检 `[G]`）**：`mh-unit-body` 开头**缺失**——引言句 + 首个大纲点（含 `I.` 标签）整段丢失，只剩一段以经文引用**右括号**起头的残尾，如 `书33：11）。` / `翰福音11：50）；` / `节）：`。根因：PDF 抽取/OCR 在**页首·分栏边界**漏掉注释开头，跨边界的经文引用 `（书N：M）` 只留下 `）`（那个孤立右括号就是残尾特征）。**检出**：`qa_mhenry.py [G]`（读每个 body 起始正文，先遇 `）` 而其前无 `（` = 括号失衡 = 截断）。**修复**：必须对照**中文 PDF**（`/Users/yanpeifa/Documents/论文/matthew_henry/`）回填丢失段落，按 PDF 原文补上引言 + `<div class="mh-l1"><span class="mh-label">I.</span>` 结构，**禁止**从英文版翻译或编造（见 `feedback_pdf_verify_before_change` / `feedback_no_self_translation_from_en`）。已知案例：`1peter/1`、`acts/12`、`deuteronomy/17·26·32`、`genesis/4`、`isaiah/30`、`judges/3·13`、`mark/14`、`psalms/89`、`romans/4` 共 12 处**已全部对照 PDF 修复**（2026-08，全卷 `[G]` 扫描=0）。其中 `deuteronomy/17` 是重度损坏（8-13 经文与注释被拆入一个伪 `mh-unit`、经文 14-15 泄漏、脚注碎片），修法=合并经文 8-13 + 注释 A/B/C、删伪单元、把 14-15 还给「拣选君王」单元；`psalms/89`/`romans/4` 是孤立括号 + 页边界拆段/经文缺闭括号漏入正文。

### 4.4 字数/标点级 OCR 噪音

历史出现过的批修脚本：
- `cc2f5f8d` / `a18a916e` — 删除中文字符内的多余空格、全角空格 U+3000
- `ae595c0b` — 删除中文与数字之间的空格
- `ee53401c` — 修补 OCR 把圣经引用切到不同行的问题
- `2b6d8ec5` — 合并 OCR 切到不同行的中文段落

**预防**：转换完跑一遍 `format_mhenry.py` / `format_mhenry2.py` 做后处理。

### 4.5 章节文件的"上一章孤立内容泄漏"

**症状**：第 N 章开头出现第 N-1 章的尾巴。

**修复**：`b8d414d5`（2026-05）已写脚本批修。

**预防**：抽取章节时按 PDF 页范围精确切分，章首必须出现 "## 第N章" 或类似 heading。

### 4.6 多列经文与跨页列续接

**症状**：经文 OCR 后多列乱序、跨页时尾段被丢。

**修复经验**：见提交 `6776eae0` / `1b954c68` / `547b98b9` / `8efdff95` / `d5252b4e`，方法是：
- outlier `x0` 过滤（异常列被剔除）
- `cx` 回退兜底跨页列续接
- 跨 block 合并：相邻 block 在视觉上是同一段时合并
- 已存的 `<p>...</p>` 经文块原样输出，不要再嵌套

具体规则记在 `pdf-to-structured-txt` skill §4.5e。

### 4.7 注释中的圣经引用样式

**约定（2026-06 起）**：注释正文里的圣经引用（如 `耶利米哀歌3：33`、`马太福音 1:17`）**视觉上要与普通文字完全一致**——无颜色、无下划线、无悬停背景、无 `cursor: pointer`。

**功能仍需保留**：点击引用要弹出经文 popup。

**实现位置**：`_layouts/mhenry-chapter.html` 的 `.scripture-ref` 规则。当前正确写法：

```css
.scripture-ref {
    color: inherit;
    border-bottom: none;
    background: transparent;
    cursor: inherit;
    white-space: inherit;
    text-decoration: none;
}
```

注意要把整个 `.scripture-ref:hover` 块删掉；任何 `:hover` 残留都会暴露引用位置。

**架构说明**——为什么删 CSS 不影响点击：
1. 引用 span 是 JS 在 `mhenry-col` 容器内动态生成的（搜 "scripture-ref" 看 `_layouts/mhenry-chapter.html`）。
2. 点击通过事件委托绑定在 `#mhenry-col` 上：
   ```js
   col.addEventListener('click', function(e) {
       if (!e.target.classList.contains('scripture-ref')) return;
       // ……弹 popup
   });
   ```
3. 只要 `class="scripture-ref"` 不变、`data-vol/data-ch/data-v1/data-v2/data-label` 不变，点击就能 work；CSS 只控制外观。

**易错**：
- 不要删 class 本身——会破坏点击。
- 不要删 span 元素——会破坏 popup 锚点。
- preface 布局 (`_layouts/mhenry-preface.html`) 没单独定义 `.scripture-ref` CSS，所以前言里引用本就跟正文同色；不需要改。**新章节布局派生时也别再加 `.scripture-ref` 颜色样式**。
- 如果以后要让引用可发现（比如 hover 时有提示），优先用 `title` 属性，不要再加颜色/下划线。

### 4.8 书卷目录页（index.html）需要套用各书自己的主题

**约定（2026-06 起）**：`mhenry/<book>/index.html` 的章节按钮、章节标题分隔线、页面背景渐变、navbar、footer 都要用**这卷书自己的水晶配色**——和它的章节页（`1.md` 内联 `<style>`）保持视觉一致。

**实现方式**：`_layouts/mhenry-book.html` 文末有这行（不要改）：
```liquid
{% if page.custom_style %}<style>{{ page.custom_style }}</style>{% endif %}
```
每本书的 `index.html` 在 front matter 里塞一个 `custom_style:` 块，里面是该书专属的 CSS 覆盖。

**模板**（参考 `mhenry/haggai/index.html`），13 行 CSS，必须覆盖：
- `body` 渐变 — 4 个 hex（与该书 1.md 的 `#mhenry-col { background: linear-gradient(160deg, …) }` 完全相同）
- `.navbar-default` / `.navbar-default .navbar-nav > li > a` / `.navbar-default .navbar-brand` — navbar 玻璃化 + 文字色
- `.intro-header { opacity: 0.85 }` — 顶图变暗
- `.mhenry-chapter-btn--has-content` + `:hover` — 已有章节的按钮（含 4 色：背景/边框/文字/悬停）
- `.mhenry-chapter-btn--preface` + `:hover` — 前言按钮（颜色更深的变体）
- `.mh-section-title` — "❧ 书名 · 章节目录" 标题的下边线 + 文字色
- `.mh-book-chapters-col` — 整个章节列容器的玻璃化背景
- `footer` / `footer .copyright, footer a` — 页脚配色

**调色板从 1.md 抽取**——脚本 `scripts/theme_book_index.py` 已经把这套规则固化：

| custom_style 字段 | 1.md 源 selector |
|---|---|
| body 渐变 4 色 | `#mhenry-col { background: linear-gradient(160deg, X 0%, Y 30%, Z 60%, W 100%) }` |
| `text_dark` | `.mh-nav-bar a { color: ... }` |
| `text_light` | `.mh-expand-tab { color: ... }` |
| `mid_strong`（章节标题下边线） | `.mh-l1 { border-left: 3px solid rgba(...) }` |
| `strong`（hover 背景） | `.mh-l1 > .mh-label { background: rgba(...) }` |
| `mid_acc`（按钮边框） | `.mh-l1 > .mh-label { border: 1px solid rgba(...) }` |
| `dark_acc`（按钮阴影） | `.mh-l1 > .mh-label { box-shadow: 0 1px 6px rgba(...) }` |
| `strong2`（hover 边框） | `.mh-footer ... color: rgba(...)` |
| `light_acc`（navbar/footer 边线） | `.tts-bar { border: 1px solid rgba(...) }` |
| `overview_text`（footer 文字） | `.mh-overview { color: ... }` |
| `h2_text`（section 标题文字） | `#mhenry-col > h2 { color: ... }` |

**两个派生色**（1.md 里没有直接对应，脚本里写公式合成）：
- `very_dark`（前言按钮文字）= 把 `text_dark` 每通道 × 0.6 取整
- `pale_bg`（前言按钮背景）= `.tts-bar { background: rgba(...) }` 的 RGB 各加 `(0, 10, 20)` 并 clamp 到 255

**用法**：
```bash
python3 scripts/theme_book_index.py                    # 跑所有未注入的卷
python3 scripts/theme_book_index.py genesis exodus     # 单跑
python3 scripts/theme_book_index.py --dry-run          # 只打印不写
```

**幂等保证**：脚本检测 front matter 已有 `custom_style:` 就 skip。哈该书等已经手工调过的 8 卷小先知（haggai / habakkuk / jonah / malachi / micah / nahum / zechariah / zephaniah）**不会被覆盖**——它们的配色是手工精调的，更贴近视觉直觉，自动合成的版本略有偏差。

**新增书卷流程**：
1. 跑完 `mhenry_pdf_to_md.py`（已经在 1.md 注入水晶 `<style>`）。
2. `python3 scripts/theme_book_index.py <book_id>` 一键注入 index.html 主题。
3. `bundle exec jekyll build`、抽 `_site/mhenry/<book>/index.html` 验证 `linear-gradient(160deg, #XXXXXX` 与 1.md 的渐变首色一致。

**易错**：
- 不要直接编辑 `_layouts/mhenry-book.html` 的默认 CSS 来改某一本书——会污染所有书；必须走 `custom_style` per-book。
- 不要把 NT 书或没经过水晶风改造的书丢进 `theme_book_index.py`——脚本会 fail，因为 1.md 没有所需 selector。
- 修改 `custom_style` 模板时，必须同步更新 `_layouts/mhenry-book.html` 默认样式里相同 selector 的定义；否则新书和旧书不一致。

### 4.9 同卷书 21 章用了三套不同的格式（约翰福音事故）

**症状**：`mhenry/john/` 21 个章节里 3 种结构并存——
- ch 1, 2, 5, 7, 12, 19：`<div class="mh-verse">第N-N节</div>` 范围标签 + 经文塞在 `<div class="mh-unit-body">` 的第一个 `<p>` 里 + 全篇用 `<p>...</p>` 包裹（约翰独有的"伪结构"）。
- ch 3, 4, 6, 8-11, 13-18, 20, 21（15 章）：整章全部内容（综述、约N:M-K 标记、经文、注释）压成一个超长 `<div class="mh-overview">`，整个 `.md` 文件只有 16 行（每行一个段落 blob）。
- preface：把 PDF 封面 + TOC（"目录、第1章 ----- 3"）当成前言体抄进去，根本不是真前言。

跟 matthew/mark/luke/acts 等其它 NT 卷的 Matthew 风（`mh-unit > mh-verse[真经文] / mh-unit-body[注释]`）完全不一致。

**根因**：早期写约翰章节时漏了正确的 PDF 抽取步骤（在 commit `1f4e92dc feat: 撒迦利亚书/哈该书/约翰福音版面与创世记保持一致` 时只补了一半），结果约翰一直保留着半成品结构。

**关键陷阱：约翰有两份 PDF，互补**：
- `马太亨利圣经注释-约翰福音.pdf`（385 页清洁版，"梁弟兄/小溪" 译）— 章节排版干净，**没有书卷前言**，TOC 直接跳到 ch1。
- `43马太亨利圣经注释：约翰福音.pdf`（1121 页早期版，"古旧福音" 译）— 章节排版乱，**但 p7–p8 有真正的书卷前言**（"探求这卷福音书写于何时何地…"）。

**两份 PDF 内容对照**（已验证）：
- 章节数、verse-range 段数完全一致（96 段 vs 96 段，无差异）。
- 章节字数小版本比大版本小 ~3%（翻译用词差异，非内容缺失）。
- **小版本有 1 处用全角冒号** `约17：24-26`（其他 95 段都用半角 `:`）——`realign_john.py` 的旧版只匹配半角，**漏过 ch17 这一段**，导致 ch17 只生成 5 个 mh-unit 而不是 6 个。已修，所有 verse-range regex 用 `[:：]` 同时匹配两种。
- 两份是不同译者，翻译用词不同。如果以后要"再次重抽 ch17 看看是否丢内容"，用 `[:：]` 而不只是 `:`。

**修复策略**：
- 章节用 385 页版（`scripts/realign_john.py`，verse-range regex 必须 `[:：]`）。
- 前言从 1121 页版的 p7–p8 抽（`介绍` 锚点切到 p9 末），合并 PDF 硬换行后写入 `mhenry/john/preface.md`，格式跟 `mhenry/matthew/preface.md` 一致——单个 `<p>...</p>`，文字直接拼接。

`scripts/realign_john.py` 处理章节按下面流程：

1. 用 `第N章` 标题在每页扫描，自动算出每章的 PDF 页区间（TOC 里的页号不一定准——约翰这本 PDF 的 ch3 等多章 heading 在前一页底部）。
2. `squash_lines`：把 PDF 硬换行的段落重连，识别结构性标记（章标题 / `约N:M-K` 经节标识 / 罗马数字 / `1.` / `(1)` 等）作为段落锚点。**关键规则**：只有"章标题"和"`约N:M-K`"是 *standalone* 锚点（后面接的行不应再被回拼），其它结构性标记后面如果不带句末标点，仍要继续向下拼接。
3. `split_chapter_overview`：从含 ch N-1 尾段的本页里，**先**找 `第N章` 把它**之前**的内容全丢掉，再把它和第一个 `约N:M-K` 之间的内容当 overview。
4. `split_into_sections`：以 `约N:M-K`（**半角冒号**，跟 overview 里的全角 `约N：M-K` 文中引用区分开）切 sections。
5. `split_scripture_commentary`：找经文最后一节 hi 的位置，再找下一个 `。\n`，前为经文（拼进 `mh-verse`）、后为注释（写入 `mh-unit-body`）。

**用法**：
```bash
python3 scripts/realign_john.py --dry-run          # 看每章预计单元数
python3 scripts/realign_john.py 1 3 14             # 跑指定章
python3 scripts/realign_john.py                    # 全 21 章
```

**预防**：写 PDF→md 的脚本时，**比较与第一卷的最终 HTML 输出结构**，不只看自己脚本的中间结果。`scripts/qa_mhenry.py` 现在能查"经文泄漏进 unit-body"，但当年没人对约翰跑过 QA。新书卷上传后必须跑 §3 流程的 §3.4「手工对照 PDF 抽样 1-2 章」+ `qa_mhenry.py`。

### 4.10 PDF 下载失败被无声落盘（HTML 错误页伪装成 PDF）

**症状**：某卷书有章节但没有 `preface.md`；查 PDF 文件看似存在但小得离谱（< 10KB）。`fitz.open` 报错或只返回 1 页（一段 SharePoint / Cloudflare / Bing 等服务的错误文案）。

**已知案例**：`15马太亨利完整圣经注释-以斯拉记.pdf` 当年下载时 SharePoint 返回了错误页 HTML，被 `download_mhenry.py` 当成 PDF 落盘了 8070 字节。此后所有把 PDF 当真 PDF 用的脚本对它都 fail；以斯拉记因此一直缺前言。

**侦测方法**：
```bash
# 健康 PDF 必以 %PDF 起始
for f in ~/Documents/论文/matthew_henry/*.pdf; do
  head -c 4 "$f" | grep -q '^%PDF' || echo "[BAD] $f ($(wc -c < "$f") bytes)"
done
```
配合 `file`：
```bash
file ~/Documents/论文/matthew_henry/*.pdf | grep -v 'PDF document'
```

**预防（写下载脚本时）**：
- 下载完立刻校验前 4 字节是 `%PDF`（不是就 raise）。
- 文件大小阈值（章节卷常见在几百 KB 以上；不到 50 KB 几乎肯定是错误页）。
- `download_mhenry.py` 应当返回非 0 退出码而不是默默落盘。

**侦测前缺失前言的卷**：
```bash
for d in mhenry/*/; do
  [ -d "$d" ] || continue
  [ -f "$d/preface.md" ] || echo "[MISSING preface] $(basename "$d")"
done
```

**修复案例**：`scripts/bootstrap_ezra_preface.py` 演示了"无 preface.md，从真 PDF 单独抽前言"的完整流程：
1. PDF 抽 `犹太会众在本书` → `第一章` 区间为 body
2. 拿同类书（`nehemiah/preface.md`，都是历史书 + 同色系）当模板
3. 用 §4.8 的同一套 PALETTE_PATTERNS 抽出两本书的调色板做 1-to-1 替换
4. 写 `mhenry/<book>/preface.md`、跑 §7 体检

新书卷如果遇到同样的"PDF 当年下载坏掉"事故，照这个套路改 BOOKS list / 锚点短语 / 模板书即可。

### 4.11 字体串到别的书

**症状**：A 书的字体出现在 B 书的页面。

**根因**：写新书 CSS 时不小心套用全局选择器，或忘了在每个 `<style>` 块开头放 `/* ── <book_id> 水晶透明风 ──*/` 标记。

**预防**：CSS 必须用 `#mhenry-col` 等顶层 scope 限定；每书的 `<style>` 都是 inline，互相独立。

### 4.12 章末脚注与正文在页断处双向错乱（全书 66 卷普遍）

**症状**：`<aside class="mhenry-footnotes">` 里混入正文片段（甚至整条真脚注前面挂着一段正文），或真脚注整条丢失；同时正文里嵌着脚注文字（如「钦定本将…译为…」突兀插在叙述中间），正文相应位置缺字。腓利门书更极端：整个 aside 全是被顶掉的正文碎片（另见早期「古旧福音」页眉水印事故）。

**根因**：PDF 每页正文在**页脚注区上方**结束，PyMuPDF 抽取时把页底最后一行正文与其下的脚注块粘在一起，早期 `mhenry_pdf_to_md.py` 的脚注分类器（`FOOTNOTE_RE` / `INLINE_FN_RE`）在页断缝处误判，导致正文↔脚注双向串位、且个别脚注被丢。**新旧约全部受影响**（NT 109 章 / OT 768 章，2026-07 已全量修复）。

**权威依据 = PDF 字号**（所有卷一致，已验证）：
- **正文 = 12 号**，**脚注 = 10 号**，**章标题 = 14 号**（诗篇用「第N篇」；弥迦/哈巴谷/西番雅无 14 号标题，改用页眉「第N章」归属）。
- 脚注按**左边距（x<60）小字号（≤8.5）纯数字**的引导编号切分成单条。
- 运行头 `马太亨利…第N页 第N章` 在 y<40，抽正文时按 y 丢弃；章边界页按 14 号标题的 y 坐标切分（正文和脚注都要 y 感知，否则会漏掉本章在下一章标题页顶部的尾巴）。

**修复工具**：`scripts/fix_nt_footnotes.py`（见 §6，`analyze` / `apply` 双模）。它重建 aside、把被顶掉的正文按 PDF 局部锚点桥接回原位，每处改动都要 `前文+桥接+后文` 是 PDF 连续子串才落地，**跨 HTML 标签一律跳过**（保护经文框/结构），不确定就标 residual 让人工处理。

**人工修 residual 的判型**（工具跨标签跳过的少数）：
- 脚注**追加在完整句后**、其后就是 `</div>` 或标题 → 直接删脚注（正文已完整）。
- 脚注**前置在综述开头** → 删前缀。
- 脚注**卡在句中**（前文未结句）→ 用 PDF 桥接缺失正文；注意 PDF gap 常延伸进已存在的标题/经文，只补「到下一结构元素之前」那截，别把已有 heading 重复插进去。

**顺带发现的历史遗留**：撒迦利亚 1、7 章正文在页断处**整段截断**（各缺约 2900 / 1500 字，与脚注无关），已对照 PDF 逐字补回。修脚注时若发现某章 `md 正文字数 ≪ PDF 12 号正文字数`（比值 <0.85，注意先剥掉内联 `<style>` 再比），多半是这种预存截断。

**勿混淆**：`fix_henry_footnotes.py`（§0 老脚本）只做**编号重排/双向跳转链接**，不碰内容；本条的内容重建用 `fix_nt_footnotes.py`。

---

## 5. 修改/批改流程模板

无论是手动改一卷，还是写脚本批改 N 卷，按以下顺序执行：

### 5.1 改前

1. **明确范围**：是改前言、章节还是 yml？是改样式还是改正文？
2. **先看 PDF**（§1.1）：用 PyMuPDF 抽对应页面文本，确认要改的目标。
3. **看一卷参考样本**：`mhenry/haggai/preface.md` 是 preface 黄金参考；`mhenry/genesis/1.md` 是章节参考（注意已被 `25dd8d1d`、`6a261f50` 升级过）。
4. **dry-run**：脚本必须支持 `--dry-run`，先打印要改的文件数和字符差异。

### 5.2 改时

1. **单卷验证**：选 1～2 个有代表性的卷先跑一次，肉眼对比 diff。
2. **再大规模批跑**：确认单卷无误，再 `python3 scripts/xxx.py` 全量。
3. **保留可回滚**：批跑前 `git status`；跑完 `git diff --stat mhenry/*/preface.md` 看变更范围。

### 5.3 改后

1. **HTML 自检**（§1.5）：
   ```bash
   for f in $(git diff --name-only mhenry/); do
     # 标签平衡
     opens=$(grep -c '<div ' "$f")
     closes=$(grep -c '</div>' "$f")
     [ "$opens" -ne "$closes" ] && echo "DIV mismatch: $f ($opens/$closes)"
     # 弯引号
     grep -l '[""'']' "$f"  # 应为空
   done
   ```
2. **Jekyll 构建**：
   ```bash
   bundle exec jekyll build --quiet 2>&1 | tail -20
   ```
   有 Liquid 错误或 YAML 错误必须立刻修。
3. **关键页面渲染检查**：
   ```bash
   # 例：检查前言是否有完整 wrap 结构
   for book in genesis haggai job psalms; do
     cnt=$(grep -c 'preface-wrap\|preface-emblem\|preface-title-block\|preface-divider\|preface-closing' \
           _site/mhenry/$book/preface/index.html)
     # 应为 13（5 个 class × wrap/inline，外加重复出现）
     echo "$book: $cnt"
   done
   ```
4. **可选**：对手机端/桌面端表现做差异化处理。见 `feedback_mobile_commit.md`：手机端改动每次立即 commit+push；桌面端需用户确认。

---

## 6. 关键脚本接口速查

### `mhenry_pdf_to_md.py`
PDF → md 全量转换。见 §3。

### `optimize_preface.py`
把"旧版 preface.md（只有简化 CSS+裸 `<p>`）" 升级为 §2.2 的哈该书结构。

```bash
python3 scripts/optimize_preface.py <book_id>             # 单卷
python3 scripts/optimize_preface.py                       # 全量 30 卷
python3 scripts/optimize_preface.py --dry-run <book_id>   # 预览
```

每书的 label 在 `BOOKS` dict 里硬编码（§2.3）。新书要扩展 `BOOKS`。

### `fix_contaminated_prefaces.py`
重抽 PDF 修复 §4.1 的污染前言。

```bash
python3 scripts/fix_contaminated_prefaces.py
```

只动 `BOOKS = ["job", "psalms", "proverbs", "ecclesiastes", "songofsolomon"]`。若新发现污染卷：
1. 在 `BOOKS` 加入 book_id。
2. 在脚本里加 `specs` 项（pdf_path、start_phrase、end_phrase）。
3. 先 `--dry-run`，对比新旧字符数，再 commit。

### `qa_mhenry.py`
内容/结构质检。见脚本头部注释，覆盖项目 A-E。

```bash
python3 scripts/qa_mhenry.py <book_id> [pdf_path] [chapter_pages...]
```

### `audit_mhenry_overview.py`
专测 `mh-overview` 综述是否缺失/过短/异常。

### `fix_mhenry_verse_leak.py`
修 §4.3 经文泄漏到注释体。

### `theme_book_index.py`
为 `mhenry/<book>/index.html` 注入与该书章节页同色系的 `custom_style`。详见 §4.8。

```bash
python3 scripts/theme_book_index.py                  # 全量
python3 scripts/theme_book_index.py <book_id>        # 单卷
python3 scripts/theme_book_index.py --dry-run        # 预览
```

幂等：已有 `custom_style:` 的 8 卷小先知会跳过，不被覆盖。

### `fix_nt_footnotes.py`
对照中文 PDF 重建章末脚注、修复脚注↔正文在页断处的双向错乱（详见 §4.12）。名字虽叫 nt，`BOOKS` dict 已含**全 66 卷**（新旧约）。

```bash
python3 scripts/fix_nt_footnotes.py analyze [book...]   # 只诊断，打印每章 PDF_fn/old_fn/body_edits/residual
python3 scripts/fix_nt_footnotes.py apply   [book...]    # 落地：重建 aside + 桥接正文
# 省略 book 则处理 BOOKS 里全部
```

- 靠 PDF 字号分层（正文 12 / 脚注 10 / 标题 14），见 §4.12。加新卷改 `BOOKS`（book_id → PDF 文件名列表，多卷按章顺序）。
- `apply` 落地前断言 `aside == PDF 脚注`；跨 HTML 标签的桥接一律跳过并标 `⚠RESIDUAL`，**residual 必须人工对照 PDF 修**（判型见 §4.12）。
- **改后校验**（务必跑）：残留嵌入脚注归零、`<div>` 平衡、标签内无弯引号、`git show HEAD:<f>` 与新版做 difflib 确认「删除的都是脚注文字」（正文零丢失）、`jekyll build`。
- 已知**误报**：difflib 把「正文句末。+ 脚注」这种边界窗口报成删除——核对该文字是否已在 aside 即可排除。

---

## 7. 体检清单（提交前必跑）

```bash
cd /Users/yanpeifa/Documents/whcjb.github.io

# 1. 所有 OT 前言结构齐全
for book in genesis exodus leviticus numbers deuteronomy joshua judges ruth \
            1samuel 2samuel 1kings 2kings 1chronicles 2chronicles ezra nehemiah esther \
            job psalms proverbs ecclesiastes songofsolomon \
            isaiah jeremiah lamentations ezekiel daniel \
            hosea joel amos obadiah jonah micah nahum habakkuk zephaniah haggai zechariah malachi; do
  [ -f mhenry/$book/preface.md ] || { echo "MISSING $book"; continue; }
  wrap=$(grep -c 'class="preface-wrap"' mhenry/$book/preface.md)
  body=$(grep -c 'class="preface-body"' mhenry/$book/preface.md)
  closing=$(grep -c 'class="preface-closing"' mhenry/$book/preface.md)
  css=$(grep -cE '^\.preface-(emblem|title-block|label|divider|closing|body|sub|book-name)' mhenry/$book/preface.md)
  chap=$(grep -c '#mhenry-col' mhenry/$book/preface.md)
  [ "$wrap" -ge 1 ] && [ "$body" -ge 1 ] && [ "$closing" -ge 1 ] && [ "$css" -ge 13 ] && [ "$chap" -ge 1 ] \
    || echo "FAIL $book wrap=$wrap body=$body closing=$closing css=$css chap=$chap"
done

# 2. 前言没被章节污染
for book in mhenry/*/; do
  book=$(basename "$book")
  [ -f "mhenry/$book/preface.md" ] || continue
  ch1=$(grep -cE '记第一章|书第一章|福音第一章' mhenry/$book/preface.md)
  [ "$ch1" -gt 0 ] && echo "[CONTAMINATED] $book"
done

# 3. Jekyll 能构建
bundle exec jekyll build --quiet 2>&1 | tail -10
```

---

## 8. 一句话总结

> mhenry 改动的失败模式只有两种：**抄错色板** 和 **PDF 没看准**。
>
> 前者靠 §1.3 的"每书独立"防线；后者靠 §1.1 的"先读 PDF 再动手" 防线。
>
> 任何批跑都要 dry-run，跑完都要跑 §7 体检，提交前都要 `jekyll build`。
