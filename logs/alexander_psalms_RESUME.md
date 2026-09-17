# 亚历山大《诗篇注释》——续跑说明（2026-09-16 更新）

## 一、当前状态

### 英文底本：残留 3 处，都是同一处希伯来文
全书判读收尾。`python3 scripts/psalms_backlog.py` 随时重算，现在报：

```
非词 9 处：已落过判读 3，待判 3，已核实原样 3
```

**待判的 3 处就是诗篇 69:22 那三个派生词**（见第三节 B）。其余全部清完：

| 检查 | 结果 |
|---|---|
| 复扫非词残留 | 165 → 3 |
| 双标点（`arm,,` `Solomon,;at`） | 47 → 0 |
| 斜体星号未配对的段落 | 9 → 0 |
| HTML 标签异常（坏标签 / `<span>` 不配对） | 1 → 0 |

### 中译
- **已发布 11 篇**：著者序 + 诗篇 1–10，落在 `alexander/psalms/zh/`
- 余 140 篇未译。流程：`scripts/translate_alexander_psalms.py --range N-M --resume`
  → 自动 `publish_alexander_psalms_zh.py` + commit + push
- 页面 date 取 `alexander_raw/psalms/zh_meta.json` 里**该篇实际译完的时刻**

## 一之二、2026-09-16 傍晚：实读三页，又捞出四类

上面那张表全绿之后，实读了诗 117、131、134 三页（共约 5 页影像），立刻撞出
四类检测器看不见的错。**这条经验第三次被验证：检测器只找它认得的错。**

| 类 | 处数 | 怎么才查得出来 |
|---|---|---|
| 节号错（`3.`读成`8.`、`31.`→`81.`） | 40 | 按**锚点序列单调性**算账：`id="psalms-N-M"` 不递增就是错 |
| 呼格 O 读成数字 0 | 207 | `0` 里没有字母，token 正则不切它，判词典永远轮不到 |
| 引号多一个/少一个 | 146 | 按**段内引号配对**算账 |
| 行末连字断在第一个字母（`u-ill`=will） | 6 | `_legit_compound` 把单字母半截当真词放行了 |

前三类的检测器都已写成脚本（`psalms_backlog.py` 之外另有
`psalms_quote_marks.py`，节号那道在提交说明里）。另修 publish 的一个设计缺陷：
希伯来题注与真正的第 1 节拿同一个 id，六十来篇如此。

**还没查过的类**（想到但没做）：
- **斜体括号**：原书里 `(是)` `(男人们)` 这类补词是**正体**、斜体在括号处断开，
  我们全书 1350 处把括号包在斜体里了。这是抽取时的系统性取舍，不是随机错，
  要不要改是个取舍问题（括号本身已经传达了「这是补的词」）。
- 引号还剩 58 段配对不上，多是真引语丢了另一半，得翻影像。
- **只实读了 5 页 / 480 页**。按这个出错密度，剩下 475 页里还有东西。

## 二、整条链可以重跑（验收口径就是这个）

```bash
bash scripts/chain_alexander_psalms.sh
```

```
publish → adjudicate(第二证人/MANUAL_TEXT/希伯来规则) → hebrew → image(--replay) → manual
```

跑完 `alexander/psalms/*.md` 与跑之前**逐字节相同**。任何一处对不上，都说明有一轮
改动只落在了正文里、没落进脚本或数据——那正是这条链要防的事。

人工判读全部固化在 `alexander_raw/psalms/manual_fixes.tsv`（487 条，
chapter / old / new / src），由 `scripts/apply_alexander_manual.py` **按表中顺序
逐条**落回（每条看到的是前面几条改完之后的正文，且要求 old 在该篇唯一）。
src 记来源：`crop2*` 裁图互证、`witness1850` 1850 三卷本按位置读、
`image1864` 1864 影像判读、`hand-*` 逐张读影像手工落定。

## 三、这一轮怎么把 165 处清到 3 处的

**先用不要钱的证人，再用影像。** 两层的闸是同一条：**只接受标点级的改动**——
读数与残串剥掉标点、数字之外的字符后必须逐字相同，否则一律不采信。
证人是 1850 三卷本、影像是 1864 印面，两边都不可能借这道闸把词改掉。

1. `scripts/psalms_residue_witness.py`
   拿 1850 三卷本按位置读出那一处的**原文切片连标点**，收掉 94 处
   （`declare^`→`declare,`、`w^ord`→`word`、`Deut.^xxv.`→`Deut. xxv.`）。
   两条边界归一必须做，否则会写出静默的双标点：
   - 右边：正文里这串后面本来就有标点的，读数尾巴上的标点要剥掉
   - 左边：正文里前面已有的破折号/括号，读数里再带一个就重了
   **两版排印可能本来就不同的地方不听证人的**（串里带 `-`、读数里凭空多出引号）
   ——1864 的引语用单引号、OCR 一半读成 `'` 一半读成 `-`，而 1850 那版根本不加引号。

2. `scripts/psalms_residue_crop.py`
   证人给不出 / 字母对不上 / 两版可能不同的那批，裁出该行影像，
   跑两遍独立判读，两遍一致 + 标点级才落盘（35 处，约 $2.7）。

3. `scripts/psalms_double_punct.py`
   `,,` `;;` `,;` 这类连着两个标点的地方——`psalms_backlog.py` 一个也看不见
   （它按空白分段找非词，标点自己不成段）。**只准删标点**：
   两个一模一样就直接并成一个（印刷上不存在连着两个逗号，不用问证人）；
   两个不一样才问证人留哪个，而证人给的必须**就是我们这两个里的一个**。
   `.,` 要特判：`Ps. xcvii., but`、`i. e., of its wilful continuance` 都是正经的。

4. 剩下的逐张读影像手工落定（约 50 处），包括几类只有看影像才发现的：
   - **页眉串进正文**：诗 115 `worship- *Psalm 115:]-7 All* pers,` 其实是
     「worship-」「下一页页眉」「pers,」三截，应作 `worshippers,`；诗 139 同类
   - **跨行词被拼了两遍**：诗 119 `the con- conservative`、诗 13 `common;;common`
   - **希伯来词被切反了序**：诗 36 `*(יהוה** נְאֻם)` 应作 `(נְאֻם יהוה)`；诗 62 两处对调
   - **判读落到了标签里**：诗 83 `</span>` 正好含 `/s`，上一轮把 `/s` 的读数
     `(is)` 落了进去，`</span>` 整个坏成 `<(is)pan>`（HTML 自检才抓得到）
   - **罗马数字连字误读**：`Ps. ex.`=`cx.`（6 处）、`hi.`=`lii.`、`h.`=`li.`、
     `six.`=`xix.`、`lui.`=`liii.`——按所引经文内容逐条核定

判词典（`alexander_raw/lexicon_extra.txt`）补了约 290 个专名、拉丁引文、
19 世纪拼法；底本印错而我们照留的三处（`darknees` / `Notwitstanding` /
`phropheticum`）单列 `alexander_raw/psalms/printed_as_is.txt`。

### B. 唯一没做完的：诗篇 69:22 的三个希伯来派生词
`(D7li^, *u>^,* D^li^,` —— 印面是 `(שלם, שלם, שלם)` 三个**只靠元音点区分**的词。
1400–2000 dpi 裁图读过，最右那个能定成 `שִׁלֵּם`，另外两个的点判不准；
两遍机判也不一致（`שִׁלֻּם` / `שלם` / `שִׁלֵּם`）。1850 三卷本这一句的希伯来文
OCR 同样是乱码（`tibiD fclblp to]bll5`），帮不上忙。

去点写出来就是三个一模一样的词，等于把这句话的意思抹掉，所以**先不动**。
要收的话得另找一份带点清楚的本子。裁图脚本：
```python
p = fitz.open(PDF)[306]; r = p.search_for('derivatives')[0]
p.get_pixmap(dpi=2000, clip=fitz.Rect(r.x1+2, r.y0-7, r.x1+95, r.y1+9))
```

## 四、不要踩的坑
- **修正必须落 `manual_fixes.tsv`，不能只改已发布正文**：重跑链条会冲掉。
  落完跑一遍 `chain_alexander_psalms.sh`，diff 为空才算数。
- **manual_fixes 是按顺序逐条落的**：后加的条目往往冲着前一条的结果去
  （`one\`→`one)` 之后才轮到那个 `{`）。但**互换型**的两条要小心：
  诗 62 两个希伯来词对调，逐条落会让第二条撞上第一条造出来的同形串，
  锚必须带上各自的上下文（`first word זו)` / `pronoun (אַךְ) in ver. 12`）。
- **判词典是全书共用的**：这一轮加了约 290 个词，以赛亚那条链下次重跑会跟着变
  （多半是好事——诗 28 的 `immoveable` 以前被"改正"成 immovable）。但真词错要小心：
  `whoso` 收进词典之后，诗 75 那处本该改成 `whose` 的就不再被改，只能补 manual_fixes。
  **以赛亚那边重跑后要对一遍 diff。**
- **印面上的错字不等于要改**：`pruise`(诗 66) 因为 1850 三卷本作 praise 才改；
  `darknees`(诗 107) `Notwitstanding`(诗 78) 没有第二证人给出不同读数，不动。
- **希伯来相邻词会倒序**：ABBYY 按视觉左右切词，希伯来文右起横书。

## 五、下次开工第一步
```bash
cd /Users/yanpeifa/Documents/whcjb.github.io
bash scripts/chain_alexander_psalms.sh && git diff --stat alexander/psalms   # 应为空
python3 scripts/psalms_backlog.py            # 应报「待判 3」（诗 69 那三个词）
python3 scripts/psalms_double_punct.py       # 应报「可疑双标点 0 处」
```
剩下的活儿是**中译 11–150**（140 篇）。英文改过的篇若涉及 1–10，
`translate_alexander_psalms.py --resume` 会自己重译受影响的段；
本轮改到的篇里 **8、10 在 1–10 之内**，开中译前先 `--resume` 跑一遍。

---

## 六、2026-09-17 暂停点（整页比对做到一半）

### 停在哪
- **第一遍跑完**：558 页全判，$34.70，报了 1441 处 → `logs/alexander_psalms_page_round1.tsv`
- **第二遍跑到 270/475 页**（$17.40）就按要求停了 → `logs/alexander_psalms_page_round2.tsv`
  续跑：`python3 scripts/psalms_page_proofread.py --round 2 --only-hits`（会跳过已判的页）
- 两遍都跑完之后：`python3 scripts/psalms_page_proofread.py --report` 出待落清单，
  `--report --apply-fixes` 把「能在 raw 里唯一定位 + 改动够小 + 改完是真词」的直接落进
  `en_chapters`，其余进 `logs/alexander_psalms_page_manual.tsv` 等人看。
  **落完必须跑一遍 `chain_alexander_psalms.sh`**，再核幂等。

### 这一轮已经落地的（都已提交推送）
| 类 | 处数 | 查法 |
|---|---|---|
| 节号被读错（`3.`→`8.`、`31.`→`81.`；英文与希伯来两套） | 48 | 锚点序列单调性，已并进 `psalms_backlog.py` |
| 呼格 O 读成数字 0 | 207 | repair 的 PRE 规则 |
| 大写 I 读成数字 1 | 61 | 同上，要排除经卷号 `1 Sam.` |
| `/` 是 f 或大写 I | 140 | 同上 |
| 真词错（`hut`→`but`、`hone`→`bone`…） | 61 | `psalms_realword_witness.py`（证人 + 语料二元组闸） |
| `}` 是 y（`bod}"`=body） | 19 | repair 的 PRE，y/u 都试、落词典才算 |
| 词尾多余撇号、`j'`=y | 29 | repair 的 PRE |
| 句末 `!` 读成 I/1/l | 33 | 全书扫，排除经卷号/代词/希伯来音译 |
| 引号配对不上 | 42 | `psalms_quote_marks.py` + 裁图两遍 |

### 还没做的
1. **第二遍剩 205 页**（约 $13、1 小时）
2. 第一遍那 1441 处里，两遍都报的才算数；目前中间统计约可落 98 处、要人看 53 处
3. `logs/alexander_psalms_page_manual.tsv` 要人逐条看（模型抄引文会抄短、会打错字，
   已有三道闸拦掉大半，剩下的得看影像）
4. **整页覆盖率自查已做**：我们的字数 / PDF 文本层字数，全书合计 1.011，
   五页滑窗最低 0.85——没有整段漏抽。单页比值低的（如书页 121 的 0.24）都是
   `<!-- PAGE n -->` 标记差一段，相邻页会补回来，不是丢内容
5. 斜体括号（1350 处，原书补词是正体）这个取舍仍未定
6. 诗 69:22 三个希伯来派生词仍判不出
