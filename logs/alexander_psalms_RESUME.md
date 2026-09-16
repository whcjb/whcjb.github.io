# 亚历山大《诗篇注释》——续跑说明（2026-09-16 更新）

## 一、当前状态

### 中译
- **已发布 11 篇**：著者序 + 诗篇 1–10，落在 `alexander/psalms/zh/`
- 余 140 篇未译
- 流程：`scripts/translate_alexander_psalms.py --range N-M --resume`
  → 自动 `publish_alexander_psalms_zh.py` + commit + push
- 页面 date 取 `alexander_raw/psalms/zh_meta.json` 里**该篇实际译完的时刻**

### 英文底本 OCR 清理
全书扫出 1456 处待判 / 480 书页，经第二证人（1850 三卷本）、整页影像两遍、
裁图两遍、逐张读影像四道判读，已落盘约 940 处。**这一轮的判读已经全部固化，
整条链可以重跑**（见下）。真实残留 165 处，按类分好了，见第三节。

## 二、整条链现在可以重跑了（2026-09-16 最重要的一件事）

以前 image / 裁图 / 手工判读改的都是**已发布正文** `alexander/psalms/*.md`，
而 `publish_alexander_en.py` 是从 `en_chapters/` 全量重写这些文件的——
重跑一次 publish，九百多处判读全没。裁图那一轮的落盘脚本当时写在会话里，
连复现都做不到。

现在：

```bash
bash scripts/chain_alexander_psalms.sh
```

```
publish → adjudicate(第二证人/MANUAL_TEXT/希伯来规则) → hebrew → image(--replay) → manual
```

跑完 `alexander/psalms/*.md` 与跑之前**逐字节相同**（已验证两遍）。
任何一处对不上，都说明有一轮改动只落在正文里、没落进脚本或数据。

固化的办法是**拿产物反推数据**：把链条跑到 image 判读为止的结果与已发布正文
逐词 diff，每处差异连同刚好唯一的上下文写进
`alexander_raw/psalms/manual_fixes.tsv`（chapter / old / new / src，257 条），
由 `scripts/apply_alexander_manual.py` 按篇锚定落回（要求 old 在该篇唯一）。

顺手修掉的三个地雷（都会静默毁掉产物）：
- `psalms_hebrew_apply.py` 把整篇正文 unent→reent，把我们自己写的
  `<span class="ax-anchor">` 一起转义成 `&lt;span…`，诗篇 119 的节号锚点全毁。
  改成**只转义规则串**。
- 同一个脚本每次都按「正文里还找得到这串乱码」重出 `hebrew_ocr_rules.tsv`，
  而这批规则自己就是把乱码改掉的那批——落过一次盘表就塌成 5 条，
  下一轮读这张表的 adjudicate 什么都不修了。改成默认不重写，加 `--rebuild-rules`。
- `adjudicate_alexander_image.py` 落盘时对希伯来读数做 `unpoint()`，
  把 שָׁלֵם / שִׁלֵּם 这种只靠元音点区分的词抹成同一个。去点只留在 `norm()`
  里（那是比对两遍读数用的）。

## 三、还剩的活儿

### A. 真实残留 165 处，`python3 scripts/psalms_backlog.py` 随时重算

以前报「约 560 处残留」，其中约 530 是判词典收不到的正经专名，本来就没错。
这一轮把 277 个纯拉丁串逐个看过上下文，正经词补进了
`alexander_raw/lexicon_extra.txt`；底本印错、我们照印面保留的三处
（darknees / Notwitstanding / phropheticum）收进
`alexander_raw/psalms/printed_as_is.txt`。清单 → `logs/alexander_psalms_backlog.tsv`。

| 类 | 处数 | 样子 | 怎么收 |
|---|---|---|---|
| 残留 `^` | 76 | `declare^` `Jehovah^` `^of` | 词本身是对的，只是粘了个 `^`；要翻影像确认那位置印的是什么（多半是元音点/脚注记号的碎屑） |
| 其他杂质 | 60 | `\will` `Exod.xix` `the~` `ver..1-3` | 多是标点/词距，逐条看 |
| 纯拉丁 | 28 | `are-` `three-` `faith-` `-he` | 跨行连字没接上，`dignity-` 这类要看下一行 |
| 方块/圆点 | 1 | `■^writer's` | 同类的另外 20 处已清（行首扫描噪点，诗 8/10 核过影像）|

### B. 诗篇 69:22 的三个希伯来派生词读不出来
`(D7li^, *u>^,* D^li^,` —— 印面是 `(שלם, שלם, שלם)` 三个只靠元音点区分的词，
1400 dpi 裁图（`scripts/crop_alexander_page.py`）仍判不准是哪三个。
去点写出来就是三个一模一样的词，等于把这句话的意思抹掉，所以**先不动**。
要收的话得另找一份带点清楚的本子。

### C. 中译
诗篇 11–150 未译。英文改过的篇若涉及 1–10，`translate_alexander_psalms.py
--resume` 会自己重译受影响的段（缓存键就是英文段落本身）。
本轮改到的篇里 **8、10 在 1–10 之内**，下次开中译前先 `--resume` 跑一遍。

## 四、不要踩的坑
- **修正必须落 `manual_fixes.tsv`，不能只改已发布正文**：重跑链条会冲掉。
  落完跑一遍 `chain_alexander_psalms.sh`，diff 为空才算数。
- **判词典是全书共用的**：这一轮往 `lexicon_extra.txt` 加了 270 来个词，
  以赛亚书那条链下次重跑会跟着变（多半是好事——诗篇 28 的 `immoveable`
  以前被"改正"成 immovable，加了词之后才保住）。但真词错要小心：
  `whoso` 收进词典之后，诗篇 75 那处本该改成 `whose` 的就不再被改，
  只能补一条 manual_fixes。以赛亚那边重跑后要对一遍 diff。
- **希伯来相邻词会倒序**：ABBYY 按视觉左右切词，希伯来文右起横书。
- **上下文快照是修复前取的**：同一轮里邻近坏字先被改掉，快照前文就失效。
- **印面上的错字不等于要改**：`pruise`(诗 66) 因为 1850 三卷本作 praise 才改；
  `darknees`(诗 107) `Notwitstanding`(诗 78) 没有第二证人给出不同读数，不动。

## 五、下次开工第一步
```bash
cd /Users/yanpeifa/Documents/whcjb.github.io
bash scripts/chain_alexander_psalms.sh && git diff --stat alexander/psalms   # 应为空
python3 scripts/psalms_backlog.py                                           # 看残留分布
```
