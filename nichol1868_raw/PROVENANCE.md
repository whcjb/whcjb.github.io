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
