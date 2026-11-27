# 巴罗夫《何西阿书讲解》抽章实读校勘记录

底本是 EEBO-TCP 人工双录入本（不是 OCR），对照杜克藏本实物扫描（第 2–4 卷同版；第 1 卷证人是 1643 初版、他版，只作旁证）。
随机抽一段（站上一页），逐页对影像读（每叶只读一次，读过的叶与结论记 `read_pages.tsv`，抽样自动跳过、再用到时照账本结论），错处落 `tcp_fixes.tsv`（词句）、`gap_review.tsv`（缺字），整类的在抽取层改判据。

| 轮 | 日期 | 抽中 | 印本页 | 页数 | 本段错处 | 每页 |
|---|---|---|---|---|---|---|
| 1 | 2026-11-26 | 第 3 卷 10:12 | pp. 442–487（456 后原书页码跳到 467） | 36 | 约 30（正文词句 11、斜体 5、缺字 6、旁注正斜整条颠倒 4 条） | ≈ 0.8 |
| 2 | 2026-11-26 | 第 2 卷 7:9–12 | pp. 677–684 | 8 | 2（词句 1、希伯来旁注 1）＋段首首字一类 | ≈ 0.25 |
| 3 | 2026-11-26 | 第 2 卷 5:15 | pp. 510–527 | 18 | 12（词句 3、漏页边标记 1、缺字 8——其中希伯来／希腊旁注 6）＋页边纯序号一类 | ≈ 0.7 |
| 4 | 2026-11-26 | 第 3 卷 9:9 | pp. 203–210 | 8 | 3（词句 2、斜体边界 1）＋第 3 卷英文旁注底子一类 | ≈ 0.4 |
| 5 | 2026-11-26 | 第 4 卷 11:2–3 | pp. 23–41（p.42 只两行，叶留给 11:4） | 19 | 11（词句 7、标点 3、录入本擅补 1）＋段尾小标题一类 | ≈ 0.6 |
| 6 | 2026-11-26 | 第 3 卷 10:6（及 10:7 首） | pp. 392–402 | 11 | 2（标点 1、斜体边界 1）＋四类整类 | ≈ 0.2 |
| 7 | 2026-11-26 | 第 2 卷 5:6（及 5:7 首） | pp. 404–417 | 14 | 2（希伯来旁注 2）＋两类整类 | ≈ 0.15 |
| 8 | 2026-11-27 | 第 2 卷 6:7–8（及 6:9 首） | pp. 622–629 | 8 | 1（标点 1）＋两类整类 | ≈ 0.13 |
| 9 | 2026-11-27 | 第 3 卷 9:10（及 9:11 首） | pp. 211–220 | 10 | 6（词 1、标点 1、缺字 3、旁注正斜 1）＋两类整类 | ≈ 0.6 |
| 10 | 2026-11-27 | 第 4 卷 12:5（及 12:6 首） | pp. 270–274、285–289（原书页码跳 275–284） | 10 | 2（词 2）＋上标一类 | ≈ 0.2 |

## 第 1 轮（10:12）

整类（抽取层 `extract_burroughs.py`）：
- **拉丁旁注正斜颠倒**：原书拉丁旁注底子是斜体、出处人名与英文连接词正体，录入本只给正体部分标 `<hi>`，抽出来恰好反了
  （本段 Hierom、Arias Mont.、Paratus sum、Ipsa gratiarum actio 四条；另在第 1、2、4 卷各抽一条看图核实：
  1643 初版 p.95 Cujus faciem、第 2 卷 p.376 Septuag./Calv.、第 4 卷 p.510 Pareus，印法相同）。
  格林希尔那条整条正斜互换规则接进来，但它的外文判据（英文虚词 < 15%）在本书把英文短旁注（Use to Ministers.、Fair Skins foul Souls…）也判成外文，
  改为：三字母以上小写词 ≥ 2 个、其中本书正文常用词（≥ 20 次）不到三分之一，且有拉丁虚词或多数词带拉丁词尾。全书 229 条旁注翻转（四卷 104／32／50／43）。
  旁注改动后缺字组原串有 66 组带上／去掉斜体号，判读表 1930 条仍全部对上落盘。

逐条（`tcp_fixes.tsv`）：Prophe→Prophet、God making→Gods making、Jesu→Jesus、Minister/Ministers 互误两处、they fruit→thy fruit、
take it is it is→as it is、Righteousnes→Righteousness、Graviora eras→cras、Well, [but what seed?] It is not every seed（录入本漏 3 词）；
斜体边界：「You will say,」原书正体、问句斜体（本段与 9:6 p.187 两处，全书只此两处这样标）、like a large field…（原书正体）、It is time.（原书斜体）；
terrarñ 后多出的缩写横（缺字判读后 TCP 的 cmbAbbrStroke 留成孤立附加符）。

缺字（`gap_review.tsv`）：希伯来旁注 לפי חסד（p.448）、יורה à ירה（p.478）；meâ、colli、dispairing、Obs.。p.453 希伯来字仍判不了（已有 `?`）。

全书同类查过、不改：
- 重复词（the the、in in、as as…）70 处：证人 OCR 同页也重复的 51 处；其余 19 处裁图看了 7 处，都是原书行末重排时多印一词（find in / in Matth.、must must、as as），原书误植照录。
- 英文旁注 p.467「Subjection is either passive…」原书底子斜体、人名正体，录入本反标；只此一条英文长注，未改。
- 旁注序号（p.477–478 页边的 1. 2. 3. 4.）录入本未录，不补。
- 段末 `▪`（录入者没认出的标点）本段 17 处未判，留着。

## 第 2 轮（7:9–12）

- 逐条：p.682「as the Doves but」→「as the Dove; but」（tcp_fixes）；p.680 页边希伯来 פותה（gid 2073）。
  该旁注原先只剩〈Greek〉、按约定不出脚注，补字后出脚注。
- 整类（`burroughs_common.dropcaps`）：原书段首花饰首字后余字小型大写（THE word、GOD hath、THEY are），录入本没标 decorInit、
  旧规则只认两字母首词（IN、WE）和 WEe 式，三字母以上的全大写首词漏认；段首先有旁注的（`[^5] THE word`）也漏。规则放宽后全书补认 33 处，逐条看过都在经文框或标题后的段首。
- 查过不改：p.677「one one night」、p.679「Mini-/nisters」原书行末重印；页边序号（1. 2. 3.）录入本不录，照旧。
- 已知未做：全书只剩〈Greek〉的希伯来旁注（站上不出脚注）尚有若干，需逐条看图，未在本轮处理。

## 第 3 轮（5:15）

- 逐条（tcp_fixes）：p.510「I will not, not leave you; there it two」→「not, not, not … there is two」（来 13:5 五重否定，录入本漏一个 not）；
  p.511「desturbs He even and Earth」→「Heaven」；p.515 页边「Obs. 3.」录入本漏。
- 缺字（gap_review）：希腊／希伯来旁注 6 条照影像补（来 13:5 οὐ μή σε ἀνῶ…、יאשמו、ישחרנני שחר、ὀρθρίσουσι、צקון לחש、ζέοντες）；Damned.、consciance（原书拼法）。
- 整类（`extract_burroughs.prep`）：页边只印一个序号（2、3、4…）的，录入本记作空 `<milestone type="tcpmilestone" n="…"/>`，抽取时整类丢掉。
  段内的改排成页边纲目标记，全书恢复 521 处（四卷 145／221／125／0；p.678「2 3 4」、p.522「2」看图核过）。块级的（章节间）不动。
  新标记不计入分页词数（否则 9:2 段跨过阈值多切出 9-4 页、改动网址）；缺字组编号与判读表全部仍对上。
- 查过不改：页边「Answ. 2」「Answ. 3」类——原书多半只印数字（p.522、p.526），单位是录入者补的，但录入本里补的和原书印出的（Obs. 1–5 各条都印）写法完全相同，规则分不开，照录入本。
  原书误植照录：Sainss、Remakable（录入本已正作 Remarkable，不动）、Isa. 16.14（应作 26.14）、how much better it it。

## 第 4 轮（9:9）

- 逐条（tcp_fixes）：p.203「superstition take, in」→「takes in」；p.208「greatest cause of evil」→「causes」；
  p.209「Sixtly,」段正斜颠倒（原书 Sixtly 正体、论点斜体、「even the men of Gibeah…」正体）。
- 整类（`extract_burroughs.GR.italic_base`）：**第 3 卷 pp. 1–441 的英文旁注原书是斜体底子**（人名、Use／Obs. 等标签正体），
  录入本照例只给正体部分标 `<hi>`，抽出来恰好反了——第 1 轮看的 pp. 442–487 恰在分界之后（正体底子），所以当时只翻了拉丁旁注。
  做法：逐叶用证人词框找出页边旁注、量笔画倾斜（逐行平移求列投影方差最大），第 3 卷全卷画出分布：叶 38–约 430 几乎全斜，此后以正体为主；
  再按卷分段裁图核（第 3 卷 p.10/13/68/110/114/203/204/206/271/420/430/431 斜、p.501/504 正；第 4 卷 6 条、第 2 卷前三轮所见全正体）。
  斜体底子页上英文旁注整条正斜互换；纲目标签（Obs. 2、Use.、Expos. 1. …，含带缺字记号的）与条首序号保持正体。全书改动约 1090 条旁注（含先前拉丁规则的重算）。
  p.467 那条长注落在分界之后仍是斜体，单列。9:6「Use To those that say…」翻转后正合原书，改正表原串同步。
  缺字组编号与判读表全部仍对上。

## 第 5 轮（11:2–3）

- 逐条（tcp_fixes）：wrenched→wretched、good I and→good Land（申 9:6）、delign→design（旁注）、befides→besides、opes→ones；
  标点 maze;→maze,、weak;→weak,、Canaan 后补句点；p.30「went out of their their Country」——原书印作「went out their their」（误植），录入本擅补 of，照原书。
- 整类（`extract_burroughs.prep`）：原书居中的逐句小标题（「But they knew not that I healed them.」）录入本录成上一段段尾的 `<q>`，
  站上并进了上段。段尾 `<q>`（前为句末标点、段落随即结束、无子元素、≤160 字）挪出段落，与其他段外 `<q>` 一样排 jb-quote。
  全书 35 处（第 4 卷 34、第 2 卷 1）；分页、缺字组编号不变。
- 查过不改：经文框站上整框斜体、内部 em 转正体，与原书斜体经文、正体人名一致；Fifhly、thm、healteh、aud、Chap. 44. 86、Psal. 10. 3 原书误植照录；p.24 页眉误作 Chap. 10。

## 第 6 轮（10:6）

逐条：p.397「go on; at length」→「go on, at length」；p.402（10:7 首）「Your King (saith the Prophet) he shall be…」正斜颠倒。

整类（本轮正文几乎无错，收获都在版式）：
1. **段首花饰首字**（`burroughs_common.RE_DROP`）：首词全大写后接大写起头的词（WHAT King、THE Lord、GODS Works、MY Brethren）也认；JESUS CHRIST 这类连串全大写不认。全书 +18。
2. **单词旁注不翻**（`extract_burroughs.RE_LABEL`）：上轮第 3 卷斜体底子规则把只有一个词的旁注（Jareb.、Hierom.、Bethel.）也翻成斜体；
   看图 Jareb./Hierom./Author./England./Calvin. 正体，仅 London. 斜体——按多数，单词旁注保持录入本原样。
3. **「First, 论点」正斜颠倒**（`burroughs_common.RE_ORDINAL`）：段首序数词斜体、旁注、整句论点正体的，原书是序数词正体、论点斜体
   （p.396 First/Secondly、p.67 Secondly、p.11 Fourthly 看图），全书 7 处翻正；同类其余几十处录入本本来就对。
4. **经文框专名**（`extract_burroughs.mark_names`）：原书经文框「经文斜体、专名正体」，第 2、3 卷录入本框内专名多半没标
   （第 3 卷 20 处全未标、第 2 卷 22/29 未标；p.392 Assyria/Jareb、p.402 Samaria 看图），按专名表补标，站上框内 em 转正体后与原书一致。全书 59 处。

查过不改：p.399「Divers other things…」录入本录作 `<q><p>` 块，原书确是缩进块，照排。

## 第 7 轮（5:6）

正文无录入错；页边希伯来 חלץ（p.412）、בגדו（p.417，5:7 首）补字。

整类：
1. **论点块并进上段**（`extract_burroughs.prep`，第 5 轮段尾 `<q>` 规则放宽）：原书逐条论点（Obs.）居中排成斜体缩进块，
   录入本录成上段段尾的 `<q>`；第 5 轮只认「前文句末标点、`<q>` 内无子元素」的。本段 p.404「the Note is this, That ⟨论点⟩」、
   p.408「Thence this Note likewise, ⟨论点⟩」两种都漏：`<q>` 内只有旁注 `<note>` 或 `<hi>` 的也收，前文以 That/this/thus 或「Note…,」「observe,」收尾的也收。
   全书再拆 48 处（含原 35 处之外的 13 处）。p.261「He found him in Bethel…」（带页边 Text.）看图核过。
2. **「引语, 论点」正斜颠倒扩充**（`burroughs_common.RE_ORDINAL`）：上轮只认序数词起头的整段；本段 p.407「Again observe,」、p.410「Further,」
   同样是引语正体、论点斜体被反标。扩到 Again/Further/But secondly/That 等一两个词的引语，允许段首或块首先有旁注、页码锚点，句末带旁注或页边序号。
   全书共 23 处翻正（含上轮 7 处）。

查过不改：p.412 页边「Obs. 1」录入本插在句中（与原书页边位置对应），站上排成行内标记，不挪；Tea（原书斜体 Y 误作 T）录入本已正作 Yea；
au、commeth our、Isa. 29.16 原书误植照录。

## 希伯来文／希腊文全书补字（2026-11-27）

录入本凡希伯来、希腊字一律记作「〈in non-Latin alphabet〉」缺字，此前只在抽章时顺带补了几十条，全书仍有 280 余组标红或判「?」。本轮全书逐组看图：
新判读表现成的整页裁图（整行宽、近原分辨率，`witness/sheets/gk{1-4}_*.jpg`）定位不准的，再按旁注所对正文找到前后叶整条页边看（多数是旁注排在前一叶页脚）。

- **新补**：第 2 卷 113、第 3 卷 53（含西弗吉尼亚本补杜克本页边残缺的 2 条）、第 4 卷 6、第 1 卷 103（初版影像，方括号）。
- **旧判读改正**：先前判「?」、这次看清的 30 余条（如 1332 לבט、1335 אשם、2107 לא יוכלו נקין、2596–2598、2845–2849）；
  先前读错或只录一半的：1273 ῥαβδομαντεία→βελομαντεία（原书第二词是以箭占卜）、2168 דבר→רבו、2167 ירה→תורה ירה、2398 עוה→עוה עון עין ענה、
  785 原推作旁注的 ὑπερεπερίσσευσεν，实为正文「a second ὑπὲρ.」。
- 体例：原书末字 ם 常印成方框（铅字缺），照经文补 ם，备注注明；原书拼法与经文不同的照原书（186 שמחתו、1214 ואמאסאך），不改；
  希腊合字（ȣ、ϗ、缩写 θεοῦ）照通行写法展开。
- **仍未补的 19 组**：字形判不定的 6 组（793、1208、1821、2566、2567、2619，备注写了可见字形）；原书同处没有外文字的 3 组（35、829、2532）；第 1 卷初版页边不见该注（多为 1652 新增）的 10 组。
- **另记、未改**（录入本漏了外文字之外的字，涉及缺字组编号，不在本轮动）：p.68 旁注 ab 前原书有 ויחלו；p.384 旁注原书作「אסר pro איסר à יסר」，录入本漏首尾两词；
  第 1 卷「idem ו cum אחרי」漏 ו；p.198 旁注 officere 原书作 afficere。

## 第 8 轮（6:7–8）

8 页逐页整页读一次（这几叶上一轮补希伯来字时只看过页边外文字，正文没读）。正文只有一处：p.626「take care, for him」→「take care for him」（tcp_fixes）。

整类：
1. **花饰首字 VV**（`burroughs_common.RE_DROP`）：原书无 W 铅字，段首花饰 W 是一整块 VV，录入本照录作 VV；
   旧规则只放大第一个 V，站上成了「V + VEE reade」。改成 VV 整块放大，全书 25 处（VVEE、VVhat、VVe、VVhen…）。
2. **短拉丁旁注没翻斜体**（`extract_burroughs.short_latin`）：拉丁旁注原书斜体底子、录入本只标正体部分，第 1 轮的判据要求至少两个三字母以上小写词，
   夹在希伯来／希腊字旁的一两个拉丁词（p.627「און Vanitas.」、p.623「Psa. 14.5, ibi tinuerunt; i. e. tunc」）漏掉。
   放宽为：旁注带外文字缺字、余下的词（出处缩写、人名、纲目标签除外）英文常用词不到一半、有拉丁虚词或词尾，即整条正斜互换；LATIN_MARK 补 ibi/tunc/nunc/ita 等。
   全书 21 条翻正，其中 11-4「Erupisset … Beza」、12-2「supplantavit / operatus est」、6-9「Nunquid desolatio … Mont.」原先拉丁正体、人名斜体，恰好反了；
   试跑时把 11-10「Vatablus in notis」「Vulgat.」当成拉丁翻反，出处人名表补上后复原。3-1、6-3、6-9 三条上一轮补字时看过图，与翻后一致。
3. 顺带改正上一轮补字笔误：535 Mendatcs → Mendaces（录入本 Mendat•s 的 t 是误录，整组照初版）。

查过不改：monnt Sinai、Paeadise、geference 录入本已正，不动；tinuerunt、corruted、Devil is is、thns 原书如此照录（thns 录入本已正）。

## 第 9 轮（9:10）

抽段时先查账本，整段一叶都没看过的才抽（上一轮 6:7 有 4 叶补字时看过页边，又整页读了一遍，不再这样）。10 页各整页读一次。

逐条：p.216「and Apostate that leaves」→「an Apostate」；p.218「Moab; and」→「Moab, and」（tcp_fixes）；
缺字 p.215 nec、ill，p.217「Perit judicium, & quum…」的 &（gap_review，看图）；
p.217 旁注「Perit judicium, & quum res transit in affectum.」原书正体，同页其余拉丁旁注都斜体，排字不一，规则判不出，列入 `extract_burroughs.LATIN_ROMAN` 单条保持正体。

整类：
1. **段首斜体时花饰首字没认**（`burroughs_common.RE_DROP_IT`）：段落以经文引语起头、录入本整段首词连同首字标斜体（`*AS for* Ephraim.]`、`*THey make the King glad.]`），
   旧规则要求行首就是大写字母，前面有 `*` 就漏了。花饰首字本身正体，提到 `*` 前。全书 19 处（p.220 看图：A 花饰、S for 斜体）。
2. **斜体底子页条首纲目标签**（`extract_burroughs.GR.note`）：第 3 卷 pp. 1–441 英文旁注斜体底子，录入本整条无 `<hi>` 的整条翻成斜体，
   但条首「Expos. 4」「Use」「Caution」「Applic.」原书正体（p.218「Expos. 4 *prefer'd.*」看图）。只动录入本整条无 `<hi>` 的，标签移出斜体，全书 12 条。
   录入本有 `<hi>` 的（Answ, 1. *of others*、Obs. 1. *Of Persons*）标法各异，不动。

查过不改：小标题「They went to BAAL-PEOR」原书 Baal-Peor 小型大写，录入本全大写，站上照显；Chap. 7. 12 首字母原书切边（缺字照留）。

## 第 10 轮（12:5）

账本里一叶都没看过的段才抽。原书页码 274 后跳到 285（印刷时页码错排，叶是连续的）。10 页各整页读一次。

逐条（tcp_fixes）：p.271「the wholeworks of Creation」→「whol works」；p.285 旁注「Iebovah」→「Iehovah」（h 误认作 b，全书只此一处）。

整类：**上标缩写当斜体出**（`extract_burroughs.prep` + `burroughs_common.load`）：原书 wᶜʰ、wᵗʰ、9ᵗʰ、13ˡʸ、Mʳ 等上标缩写，录入本标 `<hi rend="sup">`，
抽取时跟普通 `<hi>` 一样出成斜体（站上「w*ch*」「13*ly*」）。改出 `<sup>`，全书 58 处（p.272「in wᶜʰ much」看图）。

查过不改：p.273 旁注条末页边序号「1」并进上一条旁注（录入本如此，与第 2 轮页边序号同例）；p.285 旁注「[* Alwaies …]」原书带星号与方括号对应正文 Lord*，录入本未录，不补；
St Paul 原书 Sᵗ 上标，录入本作 St，不改。
