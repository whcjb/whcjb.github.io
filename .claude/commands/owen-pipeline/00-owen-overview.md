# Owen Pipeline —— 约翰·欧文《希伯来书注释》处理总纲

本 skill 由 `pdf-pipeline` 复制而来,**只用于约翰·欧文注释**;原 `pdf-pipeline`(加尔文 Ages / mhenry)保持不动。二者共享 `refs/`(audit-gates / anti-patterns / principles / helpers)方法论,但**提取与重组路径不同**,以本文为准。

---

## 0. 与加尔文 Ages 管线的关键差异(务必先读)

| 维度 | 加尔文(Ages, pdf-pipeline) | 约翰欧文(本 owen-pipeline) |
|---|---|---|
| PDF 来源 | sabda.org 的 Ages Digital Library | **thereformedcatholic.org**(AList 文件站, OneDrive 后端)。下载见 §1 |
| 格式 | 双语双栏 + `<NNNNNN>` 代码 + F/FT 脚注 + 颜色 span | **纯文本单栏英文**(size≈14.4, x≈72),**无代码/无双栏/无 F·FT 脚注/无颜色** |
| 提取 | `calvin_extract.py`(02a-extract-ages) | **`scripts/owen_extract.py`**(按**行间距**切段) |
| 章节结构 | 每书一章一文件 | **Vol1–2=导论(40 篇 EXERCITATION);Vol3–7=逐节注释→重组成希伯来书 1–13 章** |
| 重组 | 无需(已分章) | **`scripts/owen_build.py`**(**TOC 驱动**切章, 见 §3) |
| 站点板块 | `calvin/<book>/` | **`owen/<book>/`**(与 calvin/mhenry 并列),主题色**墨绿**(区别于加尔文白/酒红/藏青、mhenry 暖金) |

> ⚠️ 02a-extract-ages **不适用** Owen(非 Ages)。Owen 走 §2 的纯文本提取。

---

## 1. 下载(AList 文件站)

站点 `thereformedcatholic.org/download/...` 是 **AList V3**(后端 OneDrive)。`/download/<路径>` 返回的是网页 SPA,**不是文件**。取原始文件:

```bash
# 1. 列目录 / 取文件 sign(guest 下载需 sign)
curl -s -X POST 'https://thereformedcatholic.org/download/api/fs/list' \
  -H 'Content-Type: application/json' --data '{"path":"<目录路径>","password":"","page":1,"per_page":0}'
curl -s -X POST 'https://thereformedcatholic.org/download/api/fs/get' \
  -H 'Content-Type: application/json' --data '{"path":"<文件路径>","password":""}'   # 返回 data.sign
# 2. 带 sign 下原始文件
curl -sL 'https://thereformedcatholic.org/download/d/<URL编码路径>?sign=<SIGN>' -o out.pdf
```

Owen 希伯来书注释共 **7 卷**,存 `~/Documents/论文/owen/owen_hebrews_{1..7}.pdf`(不在仓库)。

---

## 2. 提取(纯文本, 非 Ages)

```bash
python3 scripts/owen_extract.py <vol 1-7> --out owen_raw/hebrews/vol{N}_structured.txt
```

`owen_extract.py` 要点:
- **段落边界 = 行间距**(正常 y 间距≈17, 段间≈32; 阈值 `PARA_GAP=25`)。
- ⚠️ **跨页段落分界(踩过大坑)**:不能按页重置 `prev_y`——那样上页末段与下页首段会被错误粘连(如 `The ancients…made by him.` 与 `2. Others…` 本是两段被并成一段)。正确:跨页边界用「**上页末行是否短行**(x1 未达右边距−28 = 段落结束)**或** 下页首行是否分点/章节标记(`starts_marker`)」判定是否分段。
- 去页眉页脚(y<66 / y>724)、页码、running header(`AN EXPOSITION`/`HEBREWS`…)。
- 行末断字合并(`dehyphen`)。
- 标题分类:`EXERCITATION N` / `PART` / 罗马数字节标题 / `Ver. N—经文`(逐节标题)/ `CHAPTER N`(阿拉伯数字!)。
- 输出:段落一行, 非正文段前缀 `[H2]/[VER]/[EXER]/[PART]`。
- ⚠️ 希腊文/叙利亚文/希伯来文原样保留(Owen 的 philology 对照段),grep 需 `-a`(文件含非 ASCII 被当二进制)。

**覆盖率自检(必做)**:提取后按词数比对 PDF,应 ≈100%(差几十词 = 剥掉的页眉页脚页码):
```
fitz PDF 全文词数 vs owen_raw 词数 → we/wp ≈ 1.00
```

产物 `owen_raw/hebrews/vol{N}_structured.txt` 是**贵重产物**,勿删(见 refs/anti-patterns §M 同理)。

**⚠️ 排版原则(用户明确要求, 血泪教训)**:**先严格照 PDF 忠实还原(段落原顺序原样、不折叠/不重排/不分级/不切分/不加结构), 优化留后**。`owen_build.py --emit`(`emit_faithful`)按章一页 `owen/hebrews/N/`, 段落照 PDF 顺序原样输出。曾反复用折叠考据/嵌套缩进/经节组分页等"优化"惹恼用户——**没有明确"优化"指令前, 保持忠实版**。

**⚠️ 层级不可自动还原(已跨 7 卷实证, 别再试栈解析)**:Owen 的编号层级**无法**从标记字形机械推断——已验证:
- 标记字形 ≠ 深度:`I.`(罗马)能是 `3.`(阿拉伯)的**子**层;阿拉伯 `1.` 既在顶层又在两层深处。任何 `I.>1.>(1.)>[1.]` 的"字形排序表"都是伪规律。
- 引出信号(破折号 `,—`/冒号 `:` 结尾)真实但不足:序列起始标记 64% 前有引出、续号仅 6%(10 倍差),然而只覆盖 64%。
- **完整上下文栈解析(引出压栈+续号弹栈+同族平级重开)仍失控**:Vol1/2/7 深度 5–9(合理),但 **Vol3/4/5/6 冲到 20–40 层**(不可能),因跨页漏号无法弹栈、单条父列表永不闭合、引文数字(`2 Pet. 3:3`)混入。
- **结论**:忠实平铺是**正确工程判断**,非权宜;自动缩进优化版会在半数卷里自信缩错。用户 2026-07 明确「保持忠实版」。若日后要做,**只允许给 `(N.)`/`[N.]`(圆/方括号,从不顶层、永远子项)加悬挂缩进,`1./I./First` 一律不动**。

---

## 3. 重组成章(TOC 驱动 —— Owen 独有难点)

**坑**:PDF 里的 `CHAPTER N` 章标记提取时**时而独立、时而并入正文/经文文本**(如 `CHAPTER 4 CHAPTER 5 HAVING…`),按正文里的章标记切章**不可靠**(会漏 CHAPTER 9/11/13、相邻章被吞并)。

**解法**:用**每卷目录(TOC)**——TOC 干净列出 `CHAPTER N` + `Hebrews N:V` 顺序。`owen_build.py`:
- `toc_chapters(vol)`:从 PDF 目录页(p2-7)解析该卷含哪些 Heb 章(顺序)。
- body 按**英文 `Ver.` 首节号重置到 1**(章总是从第 1 节起)切段, 按 TOC 章号顺序编号。
- 先 `--map` 打印章映射核对再 `--emit`。

```bash
python3 scripts/owen_build.py --map    # 核对: Heb 1-13 各归一卷
```

**卷→章覆盖**:Vol3=Heb1–3、Vol4=Heb3(:7)–5、Vol5=Heb6–7、Vol6=Heb8–10、Vol7=Heb11–13。
**已知边界瑕疵**:Vol3/Vol4 之间 Heb 3:7–19 归属略偏(Vol4 无 `CHAPTER 3` 标记, 3:7 起接在 ch4 段前),需人工核对该边界。

---

## 4. 建站板块 owen/

- `owen/<book>/N.md`(章)+ 导论页;`owen/<book>/index.html`;`_data/owen_books.yml`;`_layouts/owen-*.html`。
- 主题色**墨绿**(paper 暖白 `#fbfaf6`, accent 松墨绿 `#1f5a4b`),与 calvin/mhenry 区分。
- 发布/审计沿用 refs/audit-gates(脚注/`markdown="1"`/etc 等适配后按需)。

---

## 5. 翻译(等命令)

英文版结构立好后,用 CLI(`translate_filibi` 系)翻中文,**等用户命令**再启动。参考 pdf-pipeline:04-translate-zh 的提示词与守护化机制([[reference_scheduled_translate]])。
