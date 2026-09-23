# 恢复指引（2026-09-23 暂停点）

> 这份是**下次接着做**用的。完整的判据与踩坑记录在 `HANDOFF.md`；
> 这里只写「停在哪、下一步做什么、怎么做」。

## 状态：干净

工作区已提交并 push 到 `4ec74dd13`，产物与规则同步，连跑两次 publish 逐字节相同。
英文与中文四章都是最新的，可以直接从这里往下做。

## 正在做的事：第 ③ 层（页面影像）逐处判读

`old-book-ocr` skill 的四层证据里，①字形规则 ②第二证人 已经走到头，
剩下的只能裁图看影像。做法与工具如下。

### 工单从哪来

```bash
python3 scripts/qa_davenant_nonword.py            # Gate N：不依赖已知类型的非词普查
```

当前 **2,885 种 / 3,211 处**。⚠️ 这个数**不是**剩余错误数——里面混着大量拉丁引文、
只出现一两次的人名地名、以及 web2 词典没收的真词（`Tacitus` `carcases` `recognise`）。
实测真错约占三成。**它的用法是看趋势**：修掉一类之后应当降，涨上去就说明引入了新错。

工单排序用的脚本（scratchpad 里，换个位置重建即可）：把候选按「与本书出现 ≥5 次的
某个词只差 1 个字符」排序，命中率从 ~10% 提到 ~55%。**语料只排序，判定一律以影像为准。**

### 裁图工具

`/private/tmp/.../scratchpad/batchcrop.py`（临时目录，下次要重写；逻辑记在这里）：

1. **先从产物取 `<!--vNpM-->` 页码标记，再回到那一页找原始行**。
   ⚠️ 不能拿词形直接去原始行里搜——跨行断词拼起来的词（`Scrip-`+`tures`）在原始行里
   根本不存在，按前缀回退会找到别处一个正好同样开头的行，**实测读了四张不相干的图**。
2. 连字符断词时连下一行一起裁（`lines2=True`）。
3. 8–10 条竖着拼成一张图，一次判一批。看不清就单独放大到 3–4 倍
   （`Pellarmin` 的 P/B、`autnority` 的 n/h 都是这样定的案）。

### 判完怎么落盘

- **要改**：写进 `davenant_raw/colossians/manual_votes.json`，键是 `卷|扫描页号|词形`，
  同页同词形出现两次时用后词限定 `卷|页|词形>后一个词`。落票前**必须**数一遍
  该词形在该页出现几次。
- **判定不改**：写进同一份文件的 `_round_*` 说明里，下次普查不必再看。
- **原始 OCR 本来就对、被某条规则改坏**：票值**等于词形本身**＝原样登记，
  `fix_line` 会跳过后面所有规则（v2p78 `clude` 就是这么钉住的）。

### 每一轮的收尾（一步都不能省）

```bash
python3 scripts/extract_davenant.py          # ~12 分钟，迭代到不动点
python3 scripts/extract_davenant_appx.py
python3 scripts/extract_davenant_index.py
python3 scripts/publish_davenant_en.py
python3 scripts/publish_davenant_appx.py
python3 scripts/publish_davenant_index.py
# 逐条读词级 diff（不是只看「diff 是不是这一类」——两次翻车都藏在这一步）
python3 scripts/qa_davenant_regress.py
# 中文：凡英文改过的段落都要重译重发，并逐块比长度差
for n in 1 2 3 4; do python3 -u scripts/translate_davenant.py --chapter $n --resume --publish; done
python3 scripts/davenant_zh_check.py && python3 scripts/davenant_zh_leakscan.py
bash scripts/davenant_verify.sh && python3 scripts/qa_davenant_nonword.py
# 幂等：再跑一次 publish，逐字节相同
```

## 硬约束（违反过的，别再犯）

1. **原书排字错默认「照印不改」。** 已批准的 9 处是**逐条个案**，
   见 `manual_votes._compositor_policy`。再发现新的，**报给用户等批准**，不得套用。
2. **新规则插进链条早段会截掉后面更好的解**（犯过三次：`Jaity→Laity`、`TAere→THere`、
   `OxsecTion→OxsæcTion`）。加规则时要查它会不会抢掉后面规则已经修对的东西。
3. **守卫别把证据本身当否决理由**（`era.`→`æra.` 差点被自己的守卫挡掉）。
4. **产物侧改了词形，所有按词对齐的旁路数据都要过同一张表**
   （倾角 slant / 希腊文 grc / 词级 w3）。否则「修对一个词」会让它掉出斜体。
5. **闸子自己会误报**：`qa_davenant_regress` 对 `æ` 特判过；加新字符时先想想闸认不认。
6. **验收要逐条读词级 diff**，不能只看「diff 是不是这一类」。

## 下一步的候选方向

- 继续按工单裁图判读（还剩约 270 条，两卷都有）。
- 加一道**中英长度比**闸：`[^dv40]` 那条长注的中译曾经从中间截断（423 → 应有 1075 字符），
  旧缓存里可能还有别的截断块，靠长度比能扫出来。
- `davenant_zh_leakscan` 只认成串的英文词，夹在中文里的**单个**英文词漏得掉
  （`「now 已成了。」` 实测），可以收紧。
- 花括号分析表目前画成「缩进子列表 + 左侧竖线」，用户问过要不要画**真的 `{`**，
  未决。
