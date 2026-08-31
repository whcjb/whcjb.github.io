# hodge-pipeline —— 贺智著作专用流水线

从 `pdf-pipeline` 复制而来（2026-08-31），**原 skill 未改动**。
只在本目录内修改，避免波及加尔文那 56 卷已发布内容。

## 与母 skill 的差异（都是做贺智《哥林多前后书》时暴露出来的）

| 差异 | 位置 | 起因 |
|---|---|---|
| **新增 Gate T：字形特征普查** | [refs/audit-gates.md](refs/audit-gates.md) §Gate T | 母 skill 全部 Gate 都只验「产物内部自洽」，无一条验「产物忠于 PDF」 |
| 罗马数字章号 | 03-publish-en | 贺智全书 `CHAPTER I./II./XVI.` |
| 行内上标脚注 | 02a §12 | 脚注号是正文行内 size-9 裸数字 |
| 文末集中 FOOTNOTES 区 | 02a §12 | 全书脚注收在书末 |
| 段首缩进拆段 | 02a §6 补充 | `ages_phil` 路径原本不按缩进拆段 |
| 粗体进管道 | 02a §13 | `_render_spans_with_italic` 原本只抓颜色+斜体 |

## 为什么要有 Gate T（最重要的一条）

做贺智时**严格照母 skill 走完了每一步、每个 Gate 都是 0**，用户仍连续指出
三处错误：

1. **粗体整个丢失** —— `**First,**` / `**Secondly,**` 这些段首提示词全成平文
2. **居中标题偏左** —— `4. DATE. — CONTENTS OF THE EPISTLE.` 落成左缩进
3. **目录层级压平** —— 两级目录都渲染成 `margin-left:2em`

三处的共同点：**PDF 里有、产物里没有**。母 skill 的 Gate 全是标记类检查
（`****`、`<<<END`、脚注配对、`markdown="1"`…），它们能证明产物内部自洽，
证明不了产物忠于 PDF——所以一个都没报。

**结论：凡是「源里有而产物里可能丢」的特征，必须对着源头数一遍。**
毕列志那条线早有先例（`qa_bridges_text.py` 全书字符流逐字比对），
AGES 这条线一直缺，Gate T 补上。
