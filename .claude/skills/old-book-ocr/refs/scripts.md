# 脚本与换书清单

本仓库的实现都在 `scripts/`，以 alexander 两卷（psalms / isaiah）为例。
换一本新书时按下面的顺序做。

---

## 前置

- `tesseract` + 语言包 `eng`、`heb`、`grc`（第 ④ 层用）
- Python：`pymupdf`（裁图）、`Pillow`（合批图）
- 判词典依赖 `/usr/share/dict/web2`

**底本要用带坐标的 ABBYY XML，不要用 `_djvu.txt` 或 PDF 文本层。**
纯文本把斜体丢干净了，而 19 世纪注释书靠斜体区分「作者自己的译文」与
「解说」——丢了斜体读者分不清哪句是经文。坐标也是第 ③ ④ 层的前提。

---

## 一、页序标定（先做，且必须实测）

**PDF 页序与 XML 页序几乎一定错位**，不许拿页序号互相套。
诗篇：PDF 584 页 / XML 590 页，实测 `pdf_index = xml_index - 2`。

标定办法：取 XML 第 100/200/500 页的页眉文字，在 PDF 里找印着同一个书页
页码的那页。至少核三对。

正文里的 `<!-- PAGE n -->` 标的是**书上印的页码**，不是扫描页序号。
第 ③ 层按它定位，`pdf_index = 书页 + 常数`（诗篇是 +3）。

---

## 二、脚本清单

| 脚本 | 层 | 换书要改 |
|---|---|---|
| `alexander_abbyy.py` | — | XML 命名空间（一般不变） |
| `alexander_common.py` | — | 分段／页眉／连字符判据（按书的版式调） |
| `extract_<book>.py` | — | 页范围、章题正则、节号正则 |
| `alexander_lexicon.py` | ① | `EXTRA` 补充词表路径 |
| `repair_alexander_ocr.py` | ① | `BOOKS` 表加一项：`src`/`log`/`manual`/`real`/`pre`/`short_len` |
| `adjudicate_alexander_ocr.py` | ② | `SRC`、证人 pickle 路径、`HEBREW_RULES` |
| `crop_alexander_page.py` | ③ | `PDF` 路径、`OFFSET` |
| `<book>_hebrew_ocr.py` | ④ | `PDF`/`XML`/`BODY`/`OFFSET` |
| `<book>_hebrew_filter.py` | ④ | `MIN_CONF`（按书量） |
| `<book>_hebrew_apply.py` | ④ | 路径 |

`repair` 已经是多书卷的（`python3 scripts/repair_alexander_ocr.py <book>`）；
`adjudicate` 的 `SRC` 目前写死，要多书卷得按 `BOOKS` 表参数化。

---

## 三、跑的顺序

```bash
# ① 抽取 → 规则修复 → 发布
python3 scripts/extract_<book>.py
python3 scripts/repair_alexander_ocr.py <book>
python3 scripts/publish_alexander_en.py <book>

# ② 第二证人判读，跑到收敛（一般 3–4 轮）
for i in 1 2 3 4; do python3 scripts/adjudicate_alexander_ocr.py --apply; done
python3 scripts/adjudicate_alexander_ocr.py          # 干跑，确认 fix 为 0

# ④ 非拉丁活字重扫（可选，先小范围试）
python3 scripts/<book>_hebrew_ocr.py --pages 100-130
python3 scripts/<book>_hebrew_filter.py -v           # 看弃掉的对不对
python3 scripts/<book>_hebrew_ocr.py                 # 全书
python3 scripts/<book>_hebrew_filter.py
python3 scripts/<book>_hebrew_apply.py --apply
```

**重跑 `publish` 会冲掉 ②④ 的结果**（它们只存在于已发布正文里）。
重跑之后补一句 `adjudicate --apply` 即可全量恢复——前提是 ④ 的结果已经
落成 `hebrew_ocr_rules.tsv` 并由 `adjudicate` 一并应用。

---

## 四、第 ③ 层怎么用

裁图定位有两招，**优先用第一招**：

1. **拿残串本身去 PDF 文本层里搜**。文本层与我们手上的抽取产物同出一份
   ABBYY OCR，同一个残串一模一样，命中最准。
2. 退回上下文锚（残串前的几个干净词）。

定位到之后裁出该行及上下各一行，600dpi 渲染。**合批读图**：每 7–8 张竖排
拼成一张、加上红色标签，一次读一批。实测 156 处分 20 批读完。

> 正文里的 `<!-- PAGE n -->` 是**段落起始页**，长段跨两三页时按它翻会翻错页。
> 段落短的书（诗篇）问题不大，段落长的书要按句子定位。

---

## 五、验收脚本（每轮都跑）

```python
# 1. 逐词比对 + 自动回退判据（对着自己上一个已知良好的提交）
old_words 全是真词 and new_words 出现非词  →  回退

# 2. 幂等：再跑一次 --apply，判决里不应再有 fix
# 3. 规则自检：原文与修复后的形态都找不到 → 该规则已失效
# 4. 渲染层（见 SKILL.md §3.4）：
#    kramdown 丢词 / <em> 首尾空白 / 锚点总数 / 重复 id / 星号奇偶
```

---

## 六、分账口径

每轮结束报这张表，**不要只报一个非词率**：

| | 含义 |
|---|---|
| 已核实原样 | 两版一致、英美拼写之差、两份 OCR 都崩但已查过 |
| 外文与活字残渣 | 希伯来／希腊／拉丁，**页面上印的就是这些字母** |
| 待判·证人还有话说 | 形状接近，只是没过闸 |
| 待判·证人对不上 | 锚撞车，只剩影像 |
| 待判·无证据 | 锚找不到落点，只剩影像 |

**非词率不可比。** 以赛亚 1.61% 对诗篇 0.28%，差距的大头在「外文与残渣」
那一栏（4599 对 623），不是处理质量。报数时要带上这一栏的数字。

---

## 七、实测成本（供排期）

| 步骤 | 诗篇（34.3 万词 / 590 扫描页） |
|---|---|
| extract + repair + publish | 约 3 分钟 |
| adjudicate 跑到收敛 | 约 2 分钟 |
| 第 ③ 层影像判读 | 156 处 ≈ 20 批 ≈ 20 次读图 |
| 第 ④ 层重扫（白名单） | 全书 36 分钟（8 线程 tesseract） |
| 第 ④ 层重扫（现推候选） | 约一个量级更久 |

最终：非词率 0.78% → **0.28%**，待判 0，还原希伯来／希腊字符 562 个，
全程 20 余轮改动、**回退 0 处**。
