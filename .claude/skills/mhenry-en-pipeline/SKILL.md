---
name: mhenry-en-pipeline
description: 马太亨利注释·英文版补全流水线（拆分 → 翻译 → 发布）。处理中文未出版的 14 卷（加拉太、以弗所、腓立比、歌罗西、帖前/帖后、提前/提后、提多、雅各、约一/约二/约三、犹大）。
---

# mhenry-en-pipeline

中文版马太亨利注释长期缺 14 卷（亨利身后续写部分的中段）。本流水线把 CCEL Vol 6（Acts–Revelation，公共领域）英文 PDF 切到这 14 卷、转章节 markdown、用 Qwen3 翻译、最后发布到 `mhenry/<book>/`。

> **当前状态（2026-06）**：phase 1 拆分已完成；phase 2/3 待启动。

---

## 0. 前置依赖

- 源 PDF：`~/Documents/论文/matthew_henry_en/mhc6_acts_revelation.pdf`
  来源：`http://biblestudyguide.org/ebooks/comment/mhc6.pdf`（CCEL 镜像，10.4 MB / 1743 页 / `%PDF` 魔数验证过）
- Python：`pymupdf`、`opencc-python-reimplemented`
- 翻译：本地 Qwen3 API `http://10.192.2.11:8765`（见 `reference_qwen3_api.md`）
- 已有相邻流水线：`pdf-pipeline:04-translate-zh`（calvin 中翻译流程，可直接借用提示词）

---

## 1. 14 卷清单与状态

| book_id | 英文名 | 中文名 | 章数 | 续写者 | 起页@Vol6 | 终页@Vol6 |
|---|---|---|---|---|---|---|
| galatians       | Galatians       | 加拉太书         | 6 | Joshua Bayes             | 934  | 988  |
| ephesians       | Ephesians       | 以弗所书         | 6 | Samuel Rosewell          | 989  | 1042 |
| philippians     | Philippians     | 腓立比书         | 4 | William Harris           | 1043 | 1079 |
| colossians      | Colossians      | 歌罗西书         | 4 | William Harris           | 1080 | 1112 |
| 1thessalonians  | 1 Thessalonians | 帖撒罗尼迦前书   | 5 | Daniel Mayo              | 1113 | 1145 |
| 2thessalonians  | 2 Thessalonians | 帖撒罗尼迦后书   | 3 | Daniel Mayo              | 1146 | 1165 |
| 1timothy        | 1 Timothy       | 提摩太前书       | 6 | Benjamin Andrews Atkinson| 1166 | 1204 |
| 2timothy        | 2 Timothy       | 提摩太后书       | 4 | Benjamin Andrews Atkinson| 1205 | 1233 |
| titus           | Titus           | 提多书           | 3 | Jeremiah Smith           | 1234 | 1269 |
| james           | James           | 雅各书           | 5 | S. Wright                | 1399 | 1448 |
| 1john           | 1 John          | 约翰一书         | 5 | John Reynolds (Shrewsbury)| 1533 | 1588 |
| 2john           | 2 John          | 约翰二书         | 1 | John Reynolds            | 1589 | 1595 |
| 3john           | 3 John          | 约翰三书         | 1 | John Reynolds            | 1596 | 1601 |
| jude            | Jude            | 犹大书           | 1 | John Billingsley         | 1602 | 1617 |

合计 14 卷 / 54 章。所有页码由 `scripts/mhenry_en_locate_books.py`（按"标题页字母间空格"模式扫描）算出，硬编码在 `mhenry_en_split_pdf.py` 的 `BOOKS` 字典里。

---

## 2. Phase 1 — 拆分 PDF（已完成）

### 2.1 切书

```bash
python3 scripts/mhenry_en_split_pdf.py
```

每卷输出到 `~/Documents/论文/matthew_henry_en/<book_id>.pdf`（不进 git 仓库）。

### 2.2 抽章

```bash
python3 scripts/mhenry_en_extract_chapters.py                # 全 14 卷
python3 scripts/mhenry_en_extract_chapters.py galatians      # 单卷
```

写到 `mhenry/<book_id>-en/`：
- `preface.md` — "AN EXPOSITION, …" 标题块 + 整书 introduction（`CHAP. I.` 之前的全部正文）
- `1.md` … `N.md` — 每章原文（含 chapter 综述、verses 块、注释正文，目前未做内部结构识别）

每个 md 文件的 front matter：
```yaml
layout: mhenry-en-chapter
book_id: <book_id>-en        # 注意尾巴的 -en
book_name_en: "Galatians"
book_name_zh: "加拉太书"
chapter: 1
total_chapters: 6
date: YYYY-MM-DD HH:MM        # 必须分钟精度
```

### 2.3 关键模式（脚本里固化的解析点）

CCEL Vol 6 的 PDF 文本结构：

1. **书首识别**：标题页有 `T H E   G A L A T I A N S .` 这种字母间空格的形式。`scripts/mhenry_en_split_pdf.py` 的 BOOKS 字典是手工核对过的页码。
2. **章首识别**：单独一行 `CHAP. I.` / `CHAP. II.` ...（注意是 `CHAP.` 不是 `CHAPTER`）。罗马数字必须用 `[IVX]+`。
3. **续写者识别**：preface 末尾有 `Completed by <Name>.` 行，正则要锚定到 `\.\s*$` 否则会被名字里的 `S.` 截断（James 卷的事故）。
4. **页脚剥离**：每页结尾有  
   ```
   <页码>
   Matthew Henry
   Commentary on the Whole Bible Volume VI (Acts to Revelation)
   ```
   被 `FOOTER_RE` 替换为单空行。

### 2.4 建索引页

```bash
python3 scripts/mhenry_en_build_indexes.py
```

为每个 `mhenry/<book>-en/` 生成 `index.html`（layout: `mhenry-en-book`），列出 preface + 所有章节按钮。

### 2.5 入口

`mhenry/index.html` 底部已加 **❧ 英文版（English）** 一栏，自动列出所有 `layout: mhenry-en-book` 的页面，按 NT 书序排列。色板为冷调蓝（`#1F3A52` / `#EEF4F9` / `#4A6D8C`），与暖色的中文段落明显区分。

---

## 3. Phase 2 — 翻译

### 3.1 翻译模式（两种，按需选）

| 模式 | 工具 | 何时用 |
|---|---|---|
| **A. CLI 翻译**（默认） | Claude Code 直接读英文 raw、生成中文输出 | 用户明确说"用 CLI 翻译"、或要质量更高/章节短的卷 |
| **B. Qwen3 翻译** | 本地 Qwen3 `http://10.192.2.11:8765` | 章节多、要批量跑、对质量要求中等的情况 |

**Jude 是模式 A 的首例**（2026-06 完成）：用 Claude Code 在对话中直接翻译，没有跑任何脚本，没有调 Qwen3。

### 3.2 通用规则（两种模式都遵守）

- 经文用**简体和合本**现成译文（OT 也已经统一过见 [[feedback_no_self_translation_from_en]]）。**绝不从英文回译经文**——直接照抄和合本简体。
- 字体已是 LXGW WenKai 楷体（NT 全卷由 `_includes/mhenry-diamond.html` 接管，无需在 md 里设字体）。
- 圣经引用就用纯文本格式（"罗马书 8:9"等），前端 popup 由 `mhenry-chapter.html` 的 `.scripture-ref` JS 注入；不需要手工写 span。
- 保留每个 `mh-date-heading`（英文 PDF 里"<Section Title>. (a. d. 66.)"形式的小标题）。
- 不要编造（[[feedback_no_fabrication]]）：人名、年份、引文找不到原文就**不写**或保留 "Dr. Manton" 这样的英文姓，不要随口编中文译名。

### 3.2a 罗马数字大纲必须包 mh-l1 div（**强制**）

**事故来源**：jude/1.md 首次翻译时把 I/II/III 段落写成裸文本（`I. 关于本卷书信执笔人...\n\nII. 这里说明...`），渲染出来是一堵墙——没有 border-left、没有 margin、没有视觉上的层级。用户在 review 时立刻指出 "罗马数字 I II III 分开的内容，没有分段"。

**正确做法**：每一个顶级罗马字段落（`I.`/`II.`/`III.`/`IV.`/`V.`…）必须包成

```html
<div class="mh-l1"><span class="mh-label">I.</span>

关于本卷书信执笔人的说明……（这一段对应"I."的全部内容）
</div>

<div class="mh-l1"><span class="mh-label">II.</span>

这里说明本信所致的对象……
</div>
```

参照 `mhenry/hebrews/1.md`、`mhenry/romans/8.md`——这是 NT/OT 所有已发布卷一致采用的格式。NT 由 `_includes/mhenry-diamond.html` 的 `#mhenry-col .mh-l1`、`#mhenry-col .mh-l1 > .mh-label` 规则负责样式，给每个 I/II/III 加：

- 左侧 3px 蓝色竖线（钻石冷色）
- 圆角玻璃背景
- `margin: 26px 0 12px` 自带块间距
- label 是圆角胶囊，对比明显

只要包对了，渲染就自动是带卡片感的多段；包错（或不包）就是一堵字墙。

### 3.2b mh-l1 内部的分级嵌套

- **I./II./III.**（顶级罗马字）：**始终**包 `<div class="mh-l1">`。
- **1./2./3.**（第二级阿拉伯数字）：
  - 默认沿用 hebrews 风格——内嵌在 mh-l1 内文的中文段落里（"……请留意：1. xxx；2. xxx；3. xxx"），不再额外包 div。
  - 仅当该小点本身很长（>500 字）且自成一节时，才包 `<div class="mh-l2"><span class="mh-label">1.</span>...</div>`，参考 `mhenry/romans/8.md` III 段下的 1./2./3.。
- **（1）（2）/ [1.] [2.]**（第三级及以下）：永远内嵌为段中文本，不包 div（CSS 里 `.mh-l3` 选择器虽存在但全站没有 md 使用它）。

### 3.2c 包 mh-l1 的实现

每章翻译完成时执行：

```python
import re
ROMAN = re.compile(r"^(I{1,3}|IV|V|VI{0,3}|IX|X)\. ", re.M)

def wrap_unit_body(body: str) -> str:
    starts = [m.start() for m in ROMAN.finditer(body)]
    if not starts:
        return body
    out = [body[:starts[0]].rstrip() + ("\n\n" if body[:starts[0]].strip() else "")]
    for i, s in enumerate(starts):
        e = starts[i + 1] if i + 1 < len(starts) else len(body)
        m = ROMAN.match(body[s:e])
        out.append(
            f'<div class="mh-l1"><span class="mh-label">{m.group(1)}.</span>\n\n'
            f'{body[s:e][m.end():].lstrip().rstrip()}\n</div>\n\n'
        )
    return "".join(out)

text = open(path).read()
new = re.sub(
    r'(<div class="mh-unit-body">\n\n)(.*?)(\n</div>)',
    lambda m: m.group(1) + wrap_unit_body(m.group(2)) + m.group(3),
    text, flags=re.DOTALL,
)
open(path, "w").write(new)
```

CLI 翻译时可以在初稿就直接写 `<div class="mh-l1">` 包好；如果忘了写，跑一遍上面这段就能补救。也可放到 `scripts/mhenry_wrap_outline.py` 作为正式工具（待写）。

### 3.2d 自检 grep

```bash
# 每章 mh-l1 数应 ≥ mh-date-heading 数（每个段标题至少一个 Roman 段）
grep -cE 'class="mh-l1"|class="mh-date-heading"' mhenry/<book>/<n>.md
# 也不应在 mh-unit-body 之外出现裸的 "^I\. " "^II\. " 段（漏包检测）
grep -nE '^(I{1,3}|IV|V|VI{0,3}|IX|X)\. ' mhenry/<book>/<n>.md
```

### 3.3 流程（两种模式共用）

1. 读 `mhenry/<book>-en/preface.md` 和 `mhenry/<book>-en/<n>.md`（英文 raw）
2. 翻译成中文，直接按 §2.1 of mhenry skill 模板的结构写出（`## 第N章`、`<div class="mh-overview">`、`<div class="mh-date-heading">`、`<div class="mh-unit">`/`<div class="mh-verse">`/`<div class="mh-unit-body">`）
3. 写入 `mhenry/<book>/preface.md` 和 `mhenry/<book>/<n>.md`（这就是发布稿）
4. **同步复制**到 `mhenry/<book>-en/zh_chapters/preface.md` 和 `…/<n>.md`（这就是 raw 备份）—— §3.4 详述
5. 跑 §4.2 体检 + jekyll build

### 3.4 翻译 raw 必须保存（强制）

按 [[feedback_translation_raw_preserve]] 规则：每翻译完一卷书的一章，立即把成稿复制一份到 raw 目录：

```bash
mkdir -p mhenry/<book>-en/zh_chapters
cp mhenry/<book>/preface.md mhenry/<book>-en/zh_chapters/preface.md
cp mhenry/<book>/1.md       mhenry/<book>-en/zh_chapters/1.md
# ……
```

**为什么不能跳过这步**：

- 发布稿（`mhenry/<book>/<n>.md`）后续会被各种修复脚本、风格脚本、HTML 检查脚本反复改写（参考 mhenry skill §4 的事故清单）；任何一次脚本 bug 都可能破坏译文。
- raw 副本是回滚的最后一道防线。即便发布稿被脚本覆写或被 git 误操作丢失，raw 还在。
- 重新翻译同一章的成本极高（CLI 模式要再花一次 Claude 的对话上下文；Qwen3 模式要再跑一次 API + 人工修订），所以"备份一份"比"重译一份"便宜得多。

raw 目录约定：

| 路径 | 内容 |
|---|---|
| `mhenry/<book>-en/<n>.md` | 英文 raw（PDF 抽出的原文，phase 1 已生成） |
| `mhenry/<book>-en/zh_chapters/<n>.md` | 中文翻译 raw（phase 2 必须落地） |
| `mhenry/<book>-en/zh_cache/` | Qwen3 模式才有：分片缓存，断点续传用 |
| `mhenry/<book>/<n>.md` | 发布稿（最终上站点） |

四类路径都受 [[feedback_translation_raw_preserve]] 保护，**任何脚本、任何手工操作都不可删除或无备份覆盖**。新写的批处理脚本必须在 `LOCKED_PATHS` 白名单里跳过 `mhenry/*-en/zh_chapters/`。

---

## 4. Phase 3 — 发布（待启动）

### 4.1 流程

每卷一次：
1. 把 `mhenry/<book>-en/zh_chapters/<n>.md` 整合成符合 §2.1 mhenry skill 模板的 `mhenry/<book>/<n>.md`：
   - 加 `layout: mhenry-chapter`、`book_id: <book>`、`book_name: <中文名>`、`chapter`、`total_chapters` front matter
   - `<div class="mh-overview">`、`<div class="mh-unit"><div class="mh-verse">…</div><div class="mh-unit-body">…</div></div>`
   - 经文用简体和合本 + KaiTi 字体（NT 已经全 OK，diamond 风格自动套用）
2. 生成 `mhenry/<book>/preface.md`（layout: `mhenry-preface`），译稿同上
3. `mhenry/<book>/index.html` 用 `_layouts/mhenry-book.html`；NT 书不需要 `theme_book_index.py`（§1.7 of mhenry skill：钻石风全 NT 共用）
4. `_data/mhenry_books.yml` 不需要改（这 14 卷在 yml 里早就有条目，只是没章节内容）

### 4.2 体检

- 跑主 mhenry skill §7 体检脚本
- 跑 `scripts/qa_mhenry.py <book> <pdf_path>`（注意 pdf_path 给英文 PDF，质检脚本会做经文/截断检测）
- `bundle exec jekyll build --quiet` 通过
- 抽 `_site/mhenry/galatians/1/index.html` 检查渲染、字体、链接

### 4.3 完成后

把 `mhenry/<book>-en/` 目录**保留**（英文原文不删，可作交叉参考）；mhenry 主页 `index.html` 里的"❧ 新约"网格会自动检测到这本书已有章节内容，按钮从灰色变金色；"❧ 英文版"那一栏可以保留作为对照入口，或者按需把已发布的卷从 `en_order` 列表里移除（约 4.4 的偏好）。

### 4.4 主页"英文版"栏的去留策略

两种策略，都可行：

| 方案 A：保留 | 方案 B：只剩未译的 |
|---|---|
| 全 14 卷一直显示在英文栏 | 已译完的从英文栏 `en_order` 移除 |
| 用户可中英对照阅读 | 列表只显示还在 phase 1 状态的卷 |
| 默认选这个 | 翻译全部完成后整个英文栏可彻底删除 |

---

## 5. 脚本清单

| 脚本 | 用途 |
|---|---|
| `scripts/mhenry_en_split_pdf.py` | Vol 6 PDF → 14 个 per-book PDF（输出到 `~/Documents/论文/matthew_henry_en/`） |
| `scripts/mhenry_en_extract_chapters.py` | per-book PDF → `mhenry/<book>-en/<n>.md` |
| `scripts/mhenry_en_build_indexes.py` | 给每个 `-en/` 目录生成 `index.html` |
| _待写_ `scripts/mhenry_en_translate.py` | phase 2：调 Qwen3 把英文章节翻成中文，写入 `zh_chapters/` |
| _待写_ `scripts/mhenry_en_publish.py` | phase 3：把翻译稿 + 结构化拼装到 `mhenry/<book>/` |

---

## 6. 反例 / 陷阱

### 6.1 章节标记是 `CHAP.` 不是 `CHAPTER`
首次试错的正则用了 `^CHAPTER\s+([IVX]+)\.?\s*$`，0 匹配。CCEL Vol 6 用 `CHAP. I.`、`CHAP. II.`。后续脚本统一用 `\bCHAP\.\s+([IVX]+)\.`。

### 6.2 "Completed by S. Wright." 这种姓名里有句点
正则 `Completed by ([^.\n]+)\.` 会被姓里的 `S.` 截断。改用 `Completed by ([^\n]+?)\.\s*$` 锚定行尾。

### 6.3 PDF 没有 chapter 0
某些短书（2 John、3 John、Jude）只有 1 章，但仍然有 `CHAP. I.` 标记，按统一流程处理即可。preface 部分依旧从首章 marker 之前抽。

### 6.4 字母间空格的标题不能用 `re.search('GALATIANS')` 直接匹配
PDF 抽出的标题文本是 `G A L A T I A N S .`。规则化方法：把所有"单字母+空格+单字母"的 pattern 折叠为单字符，或者用 `' '.join('GALATIANS') + r'\.'` 这种生成 regex。

### 6.5 Vol 6 全本一次性切完比"一卷一搜"稳
脚本 BOOKS 字典里所有 14 卷的 start/end 都是同次扫描算出来的；不要单卷重算页码，因为 1/2/3 John、1/2 Tim 的标题区分非常脆弱（都靠 `FIRST/SECOND/THIRD` 前缀和文本顺序去重）。

### 6.6 英文 raw 与中文翻译产物都要保留
phase 2 启动时不能覆盖 `mhenry/<book>-en/<n>.md`；翻译输出走 `mhenry/<book>-en/zh_chapters/<n>.md` 这个**并列**目录。同 [[feedback_translation_raw_preserve]]。

### 6.7 主页英文栏自动发现的前提
`mhenry/index.html` 用 `site.pages | where: "layout", "mhenry-en-book"` 过滤。新加书卷只要：
1. 创建 `mhenry/<book>-en/index.html` 且 layout 是 `mhenry-en-book`
2. 在 `en_order` 列表里加 `book_id`（按 NT 经典顺序）

不需要改任何 `_data/*.yml`。

---

## 7. 一句话总结

> Phase 1 拆分已落地；当年漏 PDF 的 14 卷有了**英文章节版站点**作占位。Phase 2 翻译只是把 calvin 04-translate-zh 的提示词换个目录跑一遍；Phase 3 发布只是把翻译稿按 mhenry skill §2.1 模板拼装到 `mhenry/<book>/`。两个 phase 都用 Qwen3 跑，启动前先在单卷（建议从 2/3 John 或 Jude，体量最小）跑一遍校对，再批量。
