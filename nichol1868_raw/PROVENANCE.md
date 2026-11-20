# 1868 年 Nichol 合订本（史密斯诗 1 / 皮尔森诗 27、84、85、87 / 古治诗 116）OCR 工作目录

- 底本：Internet Archive `davidsblessedman00smit`（Princeton 神学院藏本；Nichol's Series of Commentaries，Edinburgh: James Nichol, 1868），452 叶，400dpi。
- 源文件放 `~/Documents/论文/nichol1868/`（abbyy.xml、scandata.xml、page_numbers.json、img/），不入库。
- 影像编号：ABBYY 第 idx 页 = 扫描第 idx-1 叶；IA 可访问影像剔掉了第 0–2 叶（scandata 标 Delete），故 `page/n{idx-4}.jpg`。
- 第一证人 ABBYY（IA 自带）；IA 的 `_hocr.html` 是 ABBYY 的另一种导出，**不是**独立证人。第二证人是本地 tesseract 5.5（psm 4，eng），
  按正文栏裁图，左右各留 40px（留 8px 时每行丢尾字母），结果缓存在 `tess/<页>_<块>.txt`（入库备查）。
- 清理链见 `scripts/nichol1868_ocr.py`：第 ② 层 tesseract 按位置对证 → 第 ① 层符号形与字形规则（候选唯一、且在全书出现 ≥2 次才改）
  → 各书的看图判读表（如 `smith_raw/psalm1/fill_fixes.tsv`）。
- 用法：史密斯诗 1 只取补 TCP 缺页的五段（`scripts/smith_psalm1_fill.py`）。
- 古治诗 116（`scripts/publish_gouge_psalm116.py`，2026-11-19 首发）：影像第 297–442 页整本取用；TCP A01981 残存部分作第三证人（左右 3 词定位投票）。
  首发时正文 104,696 词，正文残余非词约 1.25%（含专名、拉丁文），真词互换未决 206 处（`gouge_raw/psalm116/disagree_left.tsv`）；
  斜体（经文框、小节标题）错得最多，待逐页看图校正，判读结果落 `gouge_raw/psalm116/fixes.tsv`。
- 皮尔森诗 84、85、87（`scripts/publish_pierson_ocr.py`，2026-11-19 首发）：影像第 189–296 页；无 TCP 证人（1647 年版 TCP 只录诗 27）。
  首发时残余非词：诗 84 1.19%、诗 85 0.85%、诗 87 0.89%；斜体待逐页看图校正。诗 27 用 TCP A54870（publish_tcp_psalm.py）。
- 共用整理（publish_gouge_psalm116.md）：斜体在哨兵层面处理（合并相邻段、空白挪到标记外、配平），OCR 原有的 * 删除；
  希伯来／希腊文乱码在斜体转换之前标〈Hebrew〉。验收：渲染后正文无字面星号、无 <table>。

## 2026-11-20 第二轮清理：合流换主字流 + 看图校读

- **字流换主**：量过两条流的原始非词率（皮尔森 ABBYY 3.02% / tesseract 1.09%，古治 5.39% / 3.14%，含拉丁文），
  tesseract 明显更准，于是正文改为「字取 tesseract、斜体与分段取 ABBYY」（`nichol1868_ocr.merge_block`，old-book-ocr §3.2d）：
  块级整体对齐后逐词定夺；罗马数字取 ABBYY（tesseract 常丢一个 i）；两边都是真词时古治先问 TCP，再用清教徒语料
  （Owen／Manton／Matthew Henry 英文版，非 OCR）二元词频定夺，否则取 tesseract；tesseract 吞的词从 ABBYY 补回。
- 成类规则（`publish_gouge_psalm116.md()`，古治、皮尔森共用）：`&e.`→`&c.`、`Alls.`→`Ans.`、`wy./y.`→`v.`（抽查全是 v.）、
  罗马数字 `L/I/b` 起头→`l`、`vill`→`viii`、粘句末的脚注号、书帖签名、`he-was` 类假连字符、问号读成斜体 *I*、
  ABBYY 误判的单词假斜体（*with*／*will*／*own*，讨论词本身时保留）、段落被栏底切开的接合等。
- 修正表：`gouge_raw/psalm116/fixes.tsv`、`pierson_raw/psalms/psalmNN/fixes.tsv`（`@H`／`@G` 希伯来／希腊缺口，
  `@NOTE 注 @@ 留文` 把混进正文的栏底脚注挪到页末）。命中不为 1 次的条目，发布时报警。
- 古治小节标题：tesseract 把 `Sec.` 读成 `See.`/`Sect.`，原来漏认 16 个；且原发布版小节号全部多了前缀 5（把 `Sec` 的 S 当数字），
  已修，128 节齐全、连续。皮尔森诗 84:1–2、85:3–4、85:8–9 原是因「Ver. N.」读坏而并页，现按节分开。
- 看图实读：皮尔森诗 85 献辞、85:2（pp.107–109）、诗 84 pp.68–87。合流与规则之后仍约 2–4 处/页（引号、出处节号、
  希伯来／希腊文、混入正文的脚注），未收敛，继续逐页。
