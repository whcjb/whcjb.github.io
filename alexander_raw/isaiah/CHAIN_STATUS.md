# 以赛亚链条现状：**可以重跑了**（2026-09-28）

`bash scripts/chain_alexander_isaiah.sh` 现在跑完退出 0，连跑两次逐字节不变，
逐词回退闸干净。下面是这一轮怎么从「跑不动 → 跑了更差 → 可以跑」一步步收的，
以及每一条的判据落在哪。

## 验收口径

```bash
bash scripts/chain_alexander_isaiah.sh          # 跑第一遍
cp -r alexander/isaiah /tmp/run1
bash scripts/chain_alexander_isaiah.sh          # 跑第二遍
diff -rq /tmp/run1 alexander/isaiah             # 必须无输出（幂等）
python3 scripts/alexander_regress_check.py isaiah <上一个好提交>   # 必须 ✓
```

2026-09-28 实测：幂等 ✓；逐词回退「改动 26 块，没有真词改成非词」✓。

## 三个坑，怎么修的

### ① 发布脚本拿诗篇的表去匹配以赛亚（链条从 09-23 起跑不动）

```
✗ raw_fixes 第 2 章命中 0 次（应为 1）：'impart to this whole psalm a highly dramatic character'
```

`publish_alexander_en.py` 的 `RAW_FIXES` 写死成 `alexander_raw/psalms/raw_fixes.tsv`。
**以赛亚从 2026-09-23 起就发布不了**，没人发现是因为没人重跑过。
改成 `raw_fixes_path(book_id)` 按书取表，并新建了
`alexander_raw/isaiah/raw_fixes.tsv`。

### ② 诗篇的「删多余撇号」规则把以赛亚的收引号一个个删掉

`repair_alexander_ocr.drop_stray_apostrophe` 删的是「真词 + 撇号 + 空格」。
这在诗篇上是对的（那是墨点），在以赛亚上是**灾难**：Alexander 满篇用单引号引
短语，收引号正好长这样。

全书量过：规则命中 **68 处，其中至少 64 处是收引号**——20 处前面的开引号还在
（`'is spiritually called Sodom' (Rev. 11: 8)`），另外几十处的开引号被 OCR 读成
`c` / `<` / `(` / `*l*`（`Umbreit (c new moon…I cannot bear')`、
`Henderson < all the vessels…appearance')`、`the creproach of widowhood'`），
**所以「前面没有开引号」根本不能当放行判据**。
开着它换来的只有三四处真正多余的撇号，代价是引号配对全毁。

已改成按书开关：`BOOKS['isaiah']['stray_apostrophe'] = False`。
以赛亚那几处真正多余的撇号，要修得连开引号一起补（manual_fixes 里
`instead ofc the whole of the idols` → `instead of ' the whole` 就是这么修的）。

### ③ 有些改正**只存在于已发布正文里**，重跑就没了

和诗篇踩的是同一个坑（「判读只改产物＝没落盘」）。这一轮逐条反推成数据，
落进 `manual_fixes.tsv`：

| 处 | raw 里是什么 | 为什么判据看不见 |
|---|---|---|
| `be`→`le` 五处 | en_chapters 本来就是 `le` | 判词典把 `le` 当真词放行 |
| `praeteritum prophetic.um` | raw 是 `praettritum prophetic.um` | 句点把 token 劈两半，前半修好后半没修 |

## 这一轮被判定为「不是回归」的两类（上一版写错了，更正）

- **第 42 章不是整段丢失**。raw 是 `V..2.`（多一个句点），节号正则认不出，
  `transform` 把它劈成孤立的 `V..` 一行 + 没有锚点的 `2.` 段。正文一个字没少，
  是行级 diff 把长段与 `V..` 对齐了才看着像丢了 2000 字符。
  修法落 `raw_fixes.tsv`（全书仅此一处），修完 42:2 **第一次有了锚点**。
- **`i.e.`→`i. e.` 不是拿诗篇的结论硬套**。以赛亚自己的语料也这么说：
  `i. e.` 带空格 976 处 / 不带 17 处，`e. g.` 41 / 2。归一是对的。
  （按 [[feedback_measure_before_applying_rule]] 先量后用，不是照搬。）

## 重跑相对上一个提交的 26 处改动，全部是改好

17 处 `i.e.`/`e.g.` 空格归一 · `bepaid`→`be paid` ×2 · `bar boured`→`harboured` ·
`Hor ace`→`Horace` · `Epipbanes`→`Epiphanes` · `he still`→`be still` ·
第 42 章 v.2 补上锚点。逐词回退闸确认没有「真词改成非词」。

## 还开着的

1. **逐页实读**：1153 个书页只抽了卷二 6 页（`isaiah_page_proofread.py`，
   $0.05/页），捞到 8 处。实测约 1.3 处/页。
2. **星号奇偶**：70 个文件里 36 个是奇数，页面上至少有一个落单的字面 `*`。
   这项检查以赛亚从没做过。
3. **中译、verse-index、账上 86 处待判**（其中 60 处只能翻影像）。
