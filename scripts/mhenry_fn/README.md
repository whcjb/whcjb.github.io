# mhenry 正文脚注标记修复（2026-11-06）

正文里脚注标记原是普通数字，靠 `_layouts/mhenry-chapter.html` 的 JS 猜（前一字须是汉字），
紧跟「）」「”」的标记认不出、后续编号整体错位；页底定义还有大量跨章重复/挂错章。

做法：以中文 PDF（/Users/yanpeifa/Documents/论文/matthew_henry/）为证人——
1. `pdffn.py`  逐页抽「正文上标 + 前文上下文」与页底定义（脚注区=最后一行正文以下，区内行首数字为编号）
2. `witness.py` 按书名映射到 mhenry/<book>/，存 witness.pkl
3. `align.py` / `plan.py` 用上标前的汉字串在站内正文唯一定位；定义优先沿用站内文字（相似度≥0.6）
4. `apply.py --write` 标记写成 `<sup>N</sup>`、按位置重排页底；与已落位定义重复(>0.8)的跨章副本删除
   有未定位证人/非重复孤儿定义的文件不自动改，列入 manual 人工处理

JS 已改为：正文有 `<sup>N</sup>` 时按顺序挂链接，不再走数字猜测。
