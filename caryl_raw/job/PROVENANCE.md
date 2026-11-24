# 卡里尔《约伯记讲解》——底本与处理链

## 著者与著作

Joseph Caryl（约瑟·卡里尔，1602–1673；DNB、Wikipedia）。*An Exposition with Practical Observations upon … the Book of Job*，
伦敦圣马格努斯堂（St Magnus the Martyr）讲章，四开本分 12 部出版（1643–1666），1676–77 年合为对开两卷。

卒日：DNB 作 1672/3-03-10，Wikipedia 前后作 2 月 25 日与 3 月；EEBO-TCP A43792（*The mock-elogie on the funeral of Mr. Caryl;
gloriously solemnized, February 25th. 1672/3*）记葬礼在 2 月 25 日，故 3 月 10 日不成立。站内只写「1673 年 2 月」。

## 是否有中译本

2026-11-24 未检索。

## 底本：EEBO-TCP 8 部（人工录入 TEI，CC0）

| 部 | 章 | TCP | 扉页年份 | 扉页讲数 | 缺字（读不出） |
|---|---|---|---|---|---|
| 1 | 1–3 | A35389 | 1643 | XXI | 311 |
| 2 | 4–7 | A35438 | 1656（再版） | XXXV | 951 |
| 3 | 8–10 | A35439 | 1647 | thirty two | 622 |
| 5 | 15–17 | A35473 | 1650 | twenty three | 224 |
| 7 | 22–26 | A81199 | 1655 | Thirty-seven | 436 |
| 10 | 32–34 | A35535 | 1661 | Forty-nine | 323 |
| 11 | 35–37 | A35537 | 1664 | Thirty-five | 2966（胶片差） |
| 12 | 38–42 | A35538 | 1666 | Fifty-two | 1242 |

`src/<TCP>.xml` 取自 github `textcreationpartnership/<TCP>`（TCP.csv 里这几部标 Restricted 是 Phase 2 旧状态，2020 年已公开）。
TCP 编目把第 12 部年份记作 1653，扉页印的是 1666，以扉页为准。

**AGES 无此书**（2026-11-24 查 docs/SABDA_AGES_书目.md 与 media.sabda.org 镜像 COMMENT／PURITAN／LIBRARY3 目录）。

## 缺的 4 部（无任何录入本）

| 部 | 章 |
|---|---|
| 4 | 11–14 |
| 6 | 18–21 |
| 8 | 27–29 |
| 9 | 30–31 |

TCP 未录，1676–77 对开合订本也不在 TCP。只有影像：archive.org（如 `ExpositionOnJob3234`）、Regent College
Houston-Packer 藏本（ebooks.regent-college.edu/Caryl-Exposition-Job-Vol-N/）、Google Books（Digital Puritan 列有链接）。
待选底本走 old-book-ocr。站上这 13 章各出一页占位说明（对比抽屉按章号区间 1–42 列本书，不出占位就 404）。

## 结构（`scripts/extract_caryl.py`）

各部 TEI 分 div 的方式不一（part／chapter>verses>verse／每段一个重复的 chapter div），统一规则：
**直接带 `<epigraph>` 的最外层 div 即一段**，一段一页 `<章>-<首节>`，共 226 段。经节取段首经文框的出处行。

录入本的怪处：

- 第 2 部 4:1–6 段出处行没印节号（「JOB Chap. 4. Verse」），按 div n。
- 第 2 部 4:12–13 段出处行照抄上一段「Vers. 9, 10, 11」，框内经文是 12–13 节，按 div n。
- 第 3 部 8:4–7 段出处行作「Cap.」（非 Chap.）。
- 出处行只引头几节、讲解一路讲到下一段之前的：1:13（讲到 22）、3:14（19）、5:19（22–23）、7:5（9–10）、39:26（30）、40:6（9），
  正文里有「Verse 20.」之类小标题为证，段尾延到下一段首节之前。
- 两段都标的节（1:5、1:11、2:5–6、6:22、33:25–26、34:7–9、34:21–22）：锚点只挂在前一段。
- 卷首：书名页、出版许可、致读者、勘误各一页 `p<部>-<类>`；第 3、5、10 部勘误印在卷末，一并归卷首。第 1 部正文前的全书引论 `p1-intro`。
- 卷末主题索引、经文索引不出；第 10 部卷末书商广告不出。

## 发布（`scripts/publish_caryl_job_en.py`）

共用 `tcp_publish.Book`：页序按部交错（各部卷首在该部各段之前）；段内小经文框处已挂的 commentary-anchor 不重挂，其余挂段首；
书首页 1–42 章格子，缺的 4 部标灰。缺字记号标红，未做第二证人判读。
