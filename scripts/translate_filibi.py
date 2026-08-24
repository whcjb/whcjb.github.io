#!/usr/bin/env python3
"""
translate_filibi.py — Calvin 注释 MD → 中文 MD（支持多书卷）

保留所有格式标记（HTML/Markdown/脚注/页码），只翻译英文内容，
拉丁文保留原文并附中文括注。

用法（从项目根目录）：
    python3 scripts/translate_filibi.py                              # 默认 phil 全量翻译
    python3 scripts/translate_filibi.py --book phil --resume         # 断点续翻
    python3 scripts/translate_filibi.py --book harmony1 --chapter 1  # harmony1 第 1 章
    python3 scripts/translate_filibi.py --book BOOK --dry-run        # 只统计行类型

支持的 --book 配置见下方 BOOKS 字典。harmony1 多文件模式按 --chapter
指定章号；phil 等单文件模式忽略 --chapter。
"""
import sys, re, subprocess, hashlib, argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from claude_usage import CLI_TRIM_FLAGS, call_cli, tracker   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

# 每批翻译段数（每次调用 claude CLI）。translate_batch 用 <<<N>>> 分隔并逐条
# 缓存，解析失败会自动退回逐条翻译，所以 >1 是安全的。设 1 时一章 100+ 段就是
# 100+ 次调用，一章要 20 分钟；设 3 后墙钟时间降到三分之一。
BATCH = 3

# 所有加尔文书卷共用的追加规则(在 main 里 append 到各书 system 之后)
SCRIPTURE_RULE = (
    "\n【经文一律用和合本】被注释或引用的圣经经文句——尤其每段开头所要解释的那节经文、"
    "经文引用块(scripture-ref / 经文表格)、以及正文中整句引用的经文——一律照抄"
    "简体和合本原文，不得自行翻译或改写；唯有加尔文本人的解释性文字才翻译。"
    "书卷名、人名、章节引用亦用和合本(如 腓立比书 1:1)。"
)

# ── 各书卷配置 ────────────────────────────────────────────────────────────────
# 每项要么是 (src_path, cache_dir, out_path, system) 单文件配置，
# 要么是按章号生成路径的回调（dict 含 src_fn / cache_dir / out_fn / system）。
BOOKS = {
    'phil': {
        'mode':   'single',
        'src':    ROOT / 'calvin_raw/phil/calvin_filibi.md',
        'cache':  ROOT / 'calvin_raw/phil/zh_cache',
        'out':    ROOT / 'calvin_raw/phil/calvin_filibi_zh.md',
        'system': (
            "你是一位精通加尔文神学的中文译者，专门翻译16世纪加尔文的圣经注释。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明、不重复原文\n"
            "2. 保留所有脚注引用标记不变：[^f1] [^ft35] 等\n"
            "3. 保留所有行内 HTML 标签不变：<span style=\"color:#800000\">*...*</span>\n"
            "4. 拉丁文/法文/希腊文保留原文，括号后附中文，如 fides（信心）\n"
            "5. 圣经书卷名和人名使用和合本标准译名：\n"
            "   PHILIPPIANS→腓立比书，COLOSSIANS→歌罗西书，GALATIANS→加拉太书\n"
            "   CORINTHIANS→哥林多书，THESSALONIANS→帖撒罗尼迦书，EPHESIANS→以弗所书\n"
            "   ROMANS→罗马书，TIMOTHY→提摩太书，HEBREWS→希伯来书\n"
            "   Paul→保罗，Timothy→提摩太，Philippi→腓立比，Epaphroditus→以巴弗提\n"
            "6. 章节引用格式保持：腓立比书 1:1，歌罗西书 2:6\n"
            "7. 脚注中的法文引文格式：保留原法文 —\"中文译文\"（保留破折号和引号格式）"
        ),
    },
    'harmony1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-1-en',          # 目录，按 {ch}.md 取
        'cache':  ROOT / 'calvin_raw/matthew1/zh_cache',
        'out':    ROOT / 'calvin_raw/matthew1/zh_chapters', # 目录，按 {ch}.md 输出
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《福音书和谐》（共观福音注释）卷一。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^123] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> 等\n"
            "5. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   πεπληροφορημένα（充分确信）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "6. 圣经书卷/人名用和合本标准译名：\n"
            "   Luke→路加福音，Matthew→马太福音，Mark→马可福音，John→约翰福音\n"
            "   Acts→使徒行传，Romans→罗马书，Corinthians→哥林多书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书\n"
            "   Hebrews→希伯来书，Peter→彼得，James→雅各书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Malachi→玛拉基书\n"
            "   Zechariah→撒迦利亚书，Daniel→但以理书，Micah→弥迦书\n"
            "   Zacharias→撒迦利亚（路加福音中施洗约翰之父），Elisabeth→以利沙伯\n"
            "   Mary→马利亚，Joseph→约瑟，Jesus→耶稣，Christ→基督，John the Baptist→施洗约翰\n"
            "   Gabriel→加百列，David→大卫，Abraham→亚伯拉罕，Sarah→撒拉，Joshua→约书亚\n"
            "   Paul→保罗，Luke→路加，Theophilus→提阿非罗\n"
            "7. 章节引用格式：路加福音 1:1，马太福音 2:23（书卷名 章:节）\n"
            "8. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "9. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "   sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "   regeneration→重生，election→拣选，predestination→预定，\n"
            "   sovereignty→主权，providence→护理，redemption→救赎"
        ),
    },
    'harmony3': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-3-en',
        'cache':  ROOT / 'calvin_raw/harmony3/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony3/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《福音书和谐》（共观福音注释）卷三。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^123] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> 等\n"
            "5. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   πεπληροφορημένα（充分确信）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "6. 圣经书卷/人名用和合本标准译名：\n"
            "   Luke→路加福音，Matthew→马太福音，Mark→马可福音,John→约翰福音\n"
            "   Acts→使徒行传，Romans→罗马书，Corinthians→哥林多书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书\n"
            "   Hebrews→希伯来书，Peter→彼得，James→雅各书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Malachi→玛拉基书\n"
            "   Zechariah→撒迦利亚书，Daniel→但以理书，Micah→弥迦书\n"
            "   Mary→马利亚，Joseph→约瑟，Jesus→耶稣，Christ→基督，John the Baptist→施洗约翰\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Scribes→文士，disciples→门徒\n"
            "   Herod→希律，Pilate→彼拉多，David→大卫，Abraham→亚伯拉罕，Moses→摩西\n"
            "   Paul→保罗，Peter→彼得，James→雅各，Andrew→安得烈，Philip→腓力\n"
            "   Judas→犹大（Iscariot 加略人犹大），Caiaphas→该亚法\n"
            "7. 章节引用格式：路加福音 1:1，马太福音 2:23（书卷名 章:节）\n"
            "8. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "9. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "   sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "   regeneration→重生，election→拣选，predestination→预定，\n"
            "   sovereignty→主权，providence→护理，redemption→救赎，\n"
            "   passion→受难，crucifixion→十字架/钉十字架，resurrection→复活，\n"
            "   ascension→升天，tribulation→患难，judgment→审判"
        ),
    },
    'harmony2': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-2-en',           # 目录，按 {ch}.md 取
        'cache':  ROOT / 'calvin_raw/harmony2/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony2/zh_chapters', # 目录，按 {ch}.md 输出
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《福音书和谐》（共观福音注释）卷二。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^123] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> 等\n"
            "5. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   πεπληροφορημένα（充分确信）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "6. 圣经书卷/人名用和合本标准译名：\n"
            "   Luke→路加福音，Matthew→马太福音，Mark→马可福音，John→约翰福音\n"
            "   Acts→使徒行传，Romans→罗马书，Corinthians→哥林多书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书\n"
            "   Hebrews→希伯来书，Peter→彼得，James→雅各书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Malachi→玛拉基书\n"
            "   Zechariah→撒迦利亚书，Daniel→但以理书，Micah→弥迦书\n"
            "   Mary→马利亚，Joseph→约瑟，Jesus→耶稣，Christ→基督，John the Baptist→施洗约翰\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Scribes→文士，disciples→门徒\n"
            "   Herod→希律，Pilate→彼拉多，David→大卫，Abraham→亚伯拉罕，Moses→摩西\n"
            "   Paul→保罗，Peter→彼得，James→雅各，Andrew→安得烈，Philip→腓力\n"
            "7. 章节引用格式：路加福音 1:1，马太福音 2:23（书卷名 章:节）\n"
            "8. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "9. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "   sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "   regeneration→重生，election→拣选，predestination→预定，\n"
            "   sovereignty→主权，providence→护理，redemption→救赎"
        ),
    },
    'acts': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/acts-en',                # 目录，按 {ch}.md 取
        'cache':  ROOT / 'calvin_raw/acts-filibi/zh_cache',
        'out':    ROOT / 'calvin_raw/acts-filibi/zh_chapters',  # 目录
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《使徒行传注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   ἐκκλησία（教会）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Corinthians→哥林多书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书，Philemon→腓利门书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Joel→约珥书\n"
            "   Daniel→但以理书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Theophilus→提阿非罗，Peter→彼得，Paul→保罗，Stephen→司提反，Philip→腓利\n"
            "   James→雅各，John→约翰，Andrew→安得烈，Thomas→多马，Bartholomew→巴多罗买\n"
            "   Matthew→马太，Thaddaeus→达太，Simon the Zealot→奋锐党的西门，\n"
            "   Judas Iscariot→加略人犹大，Matthias→马提亚\n"
            "   Barnabas→巴拿巴，Silas→西拉，Timothy→提摩太，Mark→马可，Luke→路加\n"
            "   Mary→马利亚，David→大卫，Abraham→亚伯拉罕，Moses→摩西，Joshua→约书亚\n"
            "   Cornelius→哥尼流，Ananias→亚拿尼亚，Sapphira→撒非喇，Gamaliel→迦玛列\n"
            "   Aquila→亚居拉，Priscilla→百基拉，Apollos→亚波罗，Lydia→吕底亚\n"
            "   Felix→腓力斯，Festus→非斯都，Agrippa→亚基帕，Drusilla→土西拉\n"
            "   Bernice→百尼基，Lysias→吕西亚，Tertullus→帖土罗\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷，Antioch→安提阿，Damascus→大马士革，Athens→雅典\n"
            "   Corinth→哥林多，Ephesus→以弗所，Philippi→腓立比，Caesarea→该撒利亚\n"
            "   Macedonia→马其顿，Asia→亚西亚，Galatia→加拉太\n"
            "8. 章节引用格式：使徒行传 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵"
        ),
    },
    '1cor': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/1corinthians-en',
        'cache':  ROOT / 'calvin_raw/1cor/zh_cache',
        'out':    ROOT / 'calvin_raw/1cor/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《哥林多前书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   ἐκκλησία（教会）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书，Philemon→腓利门书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Joel→约珥书\n"
            "   Daniel→但以理书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，Sosthenes→所提尼，Apollos→亚波罗，Cephas→矶法\n"
            "   Stephanas→司提反家，Fortunatus→福徒拿都，Achaicus→亚该古\n"
            "   Crispus→基利司布，Gaius→该犹，Chloe→革来氏，Aquila→亚居拉，Priscilla→百基拉\n"
            "   Timothy→提摩太，Barnabas→巴拿巴，Silvanus/Silas→西拉\n"
            "   Mary→马利亚，David→大卫，Abraham→亚伯拉罕，Moses→摩西，Adam→亚当，Eve→夏娃\n"
            "   Israel→以色列，Pharaoh→法老，Egypt→埃及，Sinai→西乃，Sodom→所多玛\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷，Corinth→哥林多，Ephesus→以弗所，Athens→雅典\n"
            "   Macedonia→马其顿，Achaia→亚该亚，Asia→亚西亚，Galatia→加拉太\n"
            "   Antioch→安提阿，Damascus→大马士革\n"
            "8. 章节引用格式：哥林多前书 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    Lord's Supper→主餐，charity/love→爱，spiritual gifts→属灵恩赐，\n"
            "    resurrection→复活，flesh→肉体，circumcision→割礼"
        ),
    },
    '2cor': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/2corinthians-en',
        'cache':  ROOT / 'calvin_raw/2cor/zh_cache',
        'out':    ROOT / 'calvin_raw/2cor/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《哥林多后书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   ἐκκλησία（教会）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   2 Corinthians→哥林多后书，1 Corinthians→哥林多前书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Thessalonians→帖撒罗尼迦书，Timothy→提摩太书，Titus→提多书，Philemon→腓利门书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Joel→约珥书\n"
            "   Daniel→但以理书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，Timothy→提摩太，Titus→提多，Silvanus/Silas→西拉\n"
            "   Apollos→亚波罗，Cephas→矶法，Barnabas→巴拿巴\n"
            "   Mary→马利亚，David→大卫，Abraham→亚伯拉罕，Moses→摩西，Adam→亚当，Eve→夏娃\n"
            "   Israel→以色列，Pharaoh→法老，Egypt→埃及，Sinai→西乃，Sodom→所多玛\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷，Corinth→哥林多，Ephesus→以弗所，Athens→雅典\n"
            "   Macedonia→马其顿，Achaia→亚该亚，Asia→亚西亚，Galatia→加拉太\n"
            "   Antioch→安提阿，Damascus→大马士革\n"
            "8. 章节引用格式：哥林多后书 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    Lord's Supper→主餐，consolation/comfort→安慰，affliction→患难/苦难，\n"
            "    resurrection→复活，flesh→肉体，circumcision→割礼，\n"
            "    new creature→新造的人，ambassador→大使/使者"
        ),
    },
    '2thess': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/2thessalonians-en',
        'cache':  ROOT / 'calvin_raw/2thessalonians/zh_cache',
        'out':    ROOT / 'calvin_raw/2thessalonians/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《帖撒罗尼迦后书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   2 Thessalonians→帖撒罗尼迦后书，1 Thessalonians→帖撒罗尼迦前书\n"
            "   1/2 Corinthians→哥林多前/后书，Acts→使徒行传\n"
            "   Matthew→马太福音，Luke→路加福音，Romans→罗马书\n"
            "   Ephesians→以弗所书，Colossians→歌罗西书\n"
            "   Paul→保罗，Silvanus/Silas→西拉，Timothy→提摩太\n"
            "   Thessalonica→帖撒罗尼迦，Corinth→哥林多\n"
            "8. 章节引用格式：帖撒罗尼迦后书 2:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    election→拣选，antichrist→敌基督，apostasy→背道/离道反教，\n"
            "    man of sin→大罪人/不法之人，son of perdition→沉沦之子，\n"
            "    coming/parousia→降临，wrath→忿怒，perdition→沉沦，\n"
            "    lawless→不法，restrainer→拦阻者，delusion→迷惑"
        ),
    },
    '2timothy': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/2timothy-en',
        'cache':  ROOT / 'calvin_raw/2timothy/zh_cache',
        'out':    ROOT / 'calvin_raw/2timothy/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《提摩太后书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   2 Timothy→提摩太后书，1 Timothy→提摩太前书，Titus→提多书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Paul→保罗，Timothy→提摩太，Titus→提多，Onesiphorus→阿尼色弗，Demas→底马\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Egypt→埃及\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Ephesus→以弗所，Rome→罗马\n"
            "8. 章节引用格式：提摩太后书 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临，\n"
            "    wrath to come→将来的忿怒，idols→偶像，conversion→归主/悔改归正"
        ),
    },
    '1timothy': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/1timothy-en',
        'cache':  ROOT / 'calvin_raw/1timothy/zh_cache',
        'out':    ROOT / 'calvin_raw/1timothy/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《提摩太前书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Joel→约珥书\n"
            "   Daniel→但以理书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，Timothy→提摩太，Titus→提多，Philemon→腓利门\n"
            "   Aquila→亚居拉，Priscilla→百基拉，Barnabas→巴拿巴，Silas→西拉\n"
            "   Mary→马利亚，David→大卫，Abraham→亚伯拉罕，Moses→摩西，Adam→亚当，Eve→夏娃\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Wiclif→威克里夫\n"
            "   Vulgate→武加大, Epicurus→伊壁鸠鲁，Diogenes→第欧根尼\n"
            "   Israel→以色列，Pharaoh→法老，Egypt→埃及，Sinai→西乃，Sodom→所多玛\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷，Ephesus→以弗所，Crete→革哩底\n"
            "   Macedonia→马其顿，Achaia→亚该亚，Asia→亚西亚，Galatia→加拉太\n"
            "8. 章节引用格式：提摩太前书 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临，\n"
            "    wrath to come→将来的忿怒，idols→偶像，conversion→归主/悔改归正"
        ),
    },
    'hebrews': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/hebrews-en',
        'cache':  ROOT / 'calvin_raw/hebrews/zh_cache',
        'out':    ROOT / 'calvin_raw/hebrews/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《希伯来书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Joshua→约书亚记，Judges→士师记，Ruth→路得记\n"
            "   1 Samuel→撒母耳记上，2 Samuel→撒母耳记下，1 Kings→列王纪上，2 Kings→列王纪下\n"
            "   1 Chronicles→历代志上，2 Chronicles→历代志下\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Ecclesiastes→传道书，Song of Solomon→雅歌\n"
            "   Isaiah→以赛亚书，Jeremiah→耶利米书，Lamentations→耶利米哀歌\n"
            "   Ezekiel→以西结书，Daniel→但以理书\n"
            "   Hosea→何西阿书，Joel→约珥书，Amos→阿摩司书，Obadiah→俄巴底亚书\n"
            "   Jonah→约拿书，Micah→弥迦书，Nahum→那鸿书，Habakkuk→哈巴谷书\n"
            "   Zephaniah→西番雅书，Haggai→哈该书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，Timothy→提摩太，Titus→提多\n"
            "   Abraham→亚伯拉罕，Isaac→以撒，Jacob→雅各，Moses→摩西，Aaron→亚伦\n"
            "   Melchizedek/Melchisedek→麦基洗德，Levi→利未\n"
            "   David→大卫，Solomon→所罗门，Enoch→以诺，Noah→挪亚\n"
            "   Sarah→撒拉，Rahab→喇合，Gideon→基甸，Barak→巴拉，Samson→参孙\n"
            "   Jephthah→耶弗他，Samuel→撒母耳\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Egypt→埃及，Sinai→西乃山\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷\n"
            "8. 章节引用格式：希伯来书 1:3，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 希伯来书专属术语：\n"
            "    high priest→大祭司，priest/priesthood→祭司/祭司职分\n"
            "    tabernacle→帐幕，sanctuary→圣所，holy of holies→至圣所\n"
            "    sacrifice→祭/献祭，offering→供物/祭物，burnt offering→燔祭\n"
            "    sin offering→赎罪祭，propitiation→挽回祭，expiation→赎罪\n"
            "    Melchizedek/Melchisedec→麦基洗德，Levitical→利未\n"
            "    ark of the covenant→约柜，mercy-seat→施恩座\n"
            "    Old Testament/covenant→旧约，New Testament/covenant→新约\n"
            "    Mediator→中保，intercession→代求，Redeemer→救赎主\n"
            "    firstborn→长子，heir→后嗣，inheritance→产业/基业\n"
            "    Word (of God)→（神的）道/话语"
        ),
    },
    'james': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/james-en',
        'cache':  ROOT / 'calvin_raw/james/zh_cache',
        'out':    ROOT / 'calvin_raw/james/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《雅各书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   James→雅各书，Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Peter→彼得前书，2 Peter→彼得后书，Jude→犹大书，Revelation→启示录\n"
            "   1 John→约翰一书，2 John→约翰二书，3 John→约翰三书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Joshua→约书亚记，Judges→士师记，Ruth→路得记\n"
            "   1 Samuel→撒母耳记上，2 Samuel→撒母耳记下，1 Kings→列王纪上，2 Kings→列王纪下\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Ecclesiastes→传道书，Song of Solomon→雅歌\n"
            "   Isaiah→以赛亚书，Jeremiah→耶利米书，Lamentations→耶利米哀歌\n"
            "   Ezekiel→以西结书，Daniel→但以理书\n"
            "   Hosea→何西阿书，Joel→约珥书，Amos→阿摩司书，Obadiah→俄巴底亚书\n"
            "   Jonah→约拿书，Micah→弥迦书，Nahum→那鸿书，Habakkuk→哈巴谷书\n"
            "   Zephaniah→西番雅书，Haggai→哈该书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，James→雅各，Peter→彼得，John→约翰\n"
            "   Abraham→亚伯拉罕，Isaac→以撒，Jacob→雅各，Moses→摩西\n"
            "   David→大卫，Solomon→所罗门，Job→约伯，Elijah/Elias→以利亚\n"
            "   Rahab→喇合，Isaac→以撒\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Gentiles→外邦人，Jews→犹太人，Jerusalem→耶路撒冷\n"
            "8. 章节引用格式：雅各书 1:3，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 雅各书专属术语：\n"
            "    works→行为，faith and works→信心与行为，justified by works→因行为称义\n"
            "    trial/temptation→试炼/试探，to try/prove→试验，tempt→引诱\n"
            "    wisdom→智慧，double-minded→心怀二意，unstable→摇摆不定\n"
            "    the tongue→舌头，bridle→勒住/约束\n"
            "    doer of the word→行道者，hearer→听道者\n"
            "    the perfect law of liberty→使人得自由的完全律法\n"
            "    respect of persons/partiality→按外貌待人/偏心\n"
            "    firstfruits→初熟的果子，pure religion→纯正的虔诚/敬虔\n"
            "    elders→长老，anointing (with oil)→（用油）抹\n"
            "    the prayer of faith→出于信心的祈祷，patience→忍耐/恒忍\n"
            "    the husbandman→农夫，the early and latter rain→秋雨和春雨\n"
            "    brother→弟兄，Lord of Sabaoth→万军之主\n"
            "    Word (of God)→（神的）道/话语"
        ),
    },
    '1peter': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/1peter-en',
        'cache':  ROOT / 'calvin_raw/1peter/zh_cache',
        'out':    ROOT / 'calvin_raw/1peter/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《彼得前书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   1 Peter→彼得前书，2 Peter→彼得后书，James→雅各书，Jude→犹大书\n"
            "   1 John→约翰一书，2 John→约翰二书，3 John→约翰三书，Revelation→启示录\n"
            "   Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Ezekiel→以西结书，Daniel→但以理书，Hosea→何西阿书\n"
            "   Paul→保罗，Peter→彼得，Silvanus→西拉，Mark→马可\n"
            "   Abraham→亚伯拉罕，Isaac→以撒，Sarah→撒拉，Noah→挪亚，Moses→摩西\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Gentiles→外邦人，Jews→犹太人，Babylon→巴比伦\n"
            "   Pontus→本都，Galatia→加拉太，Cappadocia→加帕多家，Asia→亚细亚，Bithynia→庇推尼\n"
            "8. 章节引用格式：彼得前书 1:3，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 彼得前书专属术语：\n"
            "    suffering(s)→苦难/受苦，persecution→逼迫，trial→试炼\n"
            "    submission/be subject→顺服，obedience→顺从\n"
            "    elders→长老，flock→羊群，feed/shepherd→牧养，\n"
            "    chief Shepherd→牧长，Bishop of souls→灵魂的监督\n"
            "    living stone→活石，chief corner-stone→房角的头块石头\n"
            "    royal priesthood→君尊的祭司，holy nation→圣洁的国度\n"
            "    peculiar people→属神的子民，spiritual sacrifices→属灵的祭\n"
            "    precious blood→宝血，lively/living hope→活泼的盼望\n"
            "    the last time→末世，inheritance→基业\n"
            "    conversation/conduct→品行/为人，sojourners/strangers→客旅/寄居的\n"
            "    the spirits in prison→在监狱里的灵，baptism→洗礼\n"
            "    Word (of God)→（神的）道/话语"
        ),
    },
    '2peter': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/2peter-en',
        'cache':  ROOT / 'calvin_raw/2peter/zh_cache',
        'out':    ROOT / 'calvin_raw/2peter/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《彼得后书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   2 Peter→彼得后书，1 Peter→彼得前书，James→雅各书，Jude→犹大书\n"
            "   1 John→约翰一书，2 John→约翰二书，3 John→约翰三书，Revelation→启示录\n"
            "   Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Ezekiel→以西结书，Daniel→但以理书\n"
            "   Paul→保罗，Peter→彼得，Simon→西门，Balaam→巴兰，Noah→挪亚，Lot→罗得\n"
            "   Abraham→亚伯拉罕，Sodom→所多玛，Gomorrah→蛾摩拉\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Gentiles→外邦人，Jews→犹太人\n"
            "8. 章节引用格式：彼得后书 1:3，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 彼得后书专属术语：\n"
            "    knowledge/acknowledging→知识/认识，godliness→敬虔\n"
            "    divine nature→神的性情，virtue→德行，calling and election→呼召与拣选\n"
            "    false teachers→假师傅，false prophets→假先知，heresies→异端\n"
            "    the day of the Lord→主的日子，the day of God→神的日子\n"
            "    destruction/perdition→灭亡/沉沦，damnable→使人沉沦的\n"
            "    the last days→末世，scoffers→好讥诮的人\n"
            "    the holy mount→圣山，transfiguration→变像\n"
            "    prophecy of the Scripture→经上的预言\n"
            "    new heavens and new earth→新天新地\n"
            "    Word (of God)→（神的）道/话语"
        ),
    },
    '1john': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/1john-en',
        'cache':  ROOT / 'calvin_raw/1john/zh_cache',
        'out':    ROOT / 'calvin_raw/1john/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《约翰一书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   1 John→约翰一书，2 John→约翰二书，3 John→约翰三书\n"
            "   1 Peter→彼得前书，2 Peter→彼得后书，James→雅各书，Jude→犹大书，Revelation→启示录\n"
            "   Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Ezekiel→以西结书，Daniel→但以理书\n"
            "   Paul→保罗，John→约翰，Peter→彼得，James→雅各\n"
            "   Abraham→亚伯拉罕，Moses→摩西，Cain→该隐，Abel→亚伯\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Gentiles→外邦人，Jews→犹太人\n"
            "8. 章节引用格式：约翰一书 1:3，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 约翰一书专属术语：\n"
            "    fellowship→相交/团契，light→光，darkness→黑暗\n"
            "    propitiation→挽回祭，advocate→中保/代求者\n"
            "    to abide/dwell→住/常在，to walk→行\n"
            "    the world→世界，lust→私欲，the lust of the flesh→肉体的私欲\n"
            "    antichrist→敌基督，the last time→末时\n"
            "    the anointing/unction→恩膏，born of God→从神生/由神而生\n"
            "    the children of God→神的儿女，the seed of God→神的种\n"
            "    eternal life→永生，the Son of God→神的儿子\n"
            "    love→爱，perfect love→完全的爱，fear→惧怕\n"
            "    to know/knowledge→认识/知道，assurance→确据\n"
            "    the witness/testimony→见证，the Spirit of truth→真理的灵\n"
            "    the spirit of error→谬妄的灵，to try the spirits→试验诸灵\n"
            "    Word of life→生命之道，manifested→显现\n"
            "    Word (of God)→（神的）道/话语"
        ),
    },
    'jude': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/jude-en',
        'cache':  ROOT / 'calvin_raw/jude/zh_cache',
        'out':    ROOT / 'calvin_raw/jude/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《犹大书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Jude→犹大书，1 John→约翰一书，2 John→约翰二书，3 John→约翰三书\n"
            "   1 Peter→彼得前书，2 Peter→彼得后书，James→雅各书，Revelation→启示录\n"
            "   Hebrews→希伯来书，Romans→罗马书，Galatians→加拉太书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   1 Timothy→提摩太前书，2 Timothy→提摩太后书，Titus→提多书，Philemon→腓利门书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Proverbs→箴言，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Ezekiel→以西结书，Daniel→但以理书\n"
            "   Paul→保罗，John→约翰，Peter→彼得，James→雅各，Jude→犹大\n"
            "   Abraham→亚伯拉罕，Moses→摩西，Cain→该隐，Abel→亚伯\n"
            "   Enoch→以诺，Korah→可拉，Balaam→巴兰，Sodom→所多玛，Gomorrah→蛾摩拉\n"
            "   Michael→米迦勒，Adam→亚当，Israel→以色列，Egypt→埃及\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Eusebius→优西比乌，Jerome→耶柔米，Vulgate→武加大\n"
            "   Gentiles→外邦人，Jews→犹太人\n"
            "8. 章节引用格式：犹大书 1:3，彼得后书 2:1（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心/信仰，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临\n"
            "11. 犹大书专属术语：\n"
            "    the faith once delivered unto the saints→一次交付圣徒的真道\n"
            "    to contend earnestly for the faith→为真道竭力争辩\n"
            "    ungodly/ungodliness→不敬虔（的人）/不虔，godliness→敬虔\n"
            "    to creep in unawares→偷着进来，crept in→潜入\n"
            "    to turn grace into lasciviousness→将神的恩变作放纵情欲的机会\n"
            "    to deny the Lord→不认主，reprobate→被弃绝的\n"
            "    the archangel→天使长，to keep/preserve→保守/持守\n"
            "    to build up yourselves→建立自己（在真道上）\n"
            "    murmurers/complainers→私下议论的人/发怨言的人\n"
            "    mockers/scoffers→好讥诮的人，spots→污点/礁石\n"
            "    feasts of charity/love-feasts→爱席，wandering stars→流荡的星\n"
            "    sensual/natural (ψυχικοί)→属血气的，to condemn→定罪，judgment→审判"
        ),
    },
    'genesis': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/genesis-en',
        'cache':  ROOT / 'calvin_raw/genesis/zh_cache',
        'out':    ROOT / 'calvin_raw/genesis/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《创世记注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <span style=\"...\"> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO GENESIS X:Y</span> 中的 GO TO 可译为「前往」，书卷章节照和合本\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Genesis→创世记，Exodus→出埃及记，Leviticus→利未记，Numbers→民数记\n"
            "   Deuteronomy→申命记，Psalm(s)→诗篇，Isaiah→以赛亚书，Romans→罗马书\n"
            "   Matthew→马太福音，John→约翰福音，Hebrews→希伯来书，Galatians→加拉太书\n"
            "   Acts→使徒行传，Ephesians→以弗所书，1 Corinthians→哥林多前书\n"
            "   人名：Adam→亚当，Eve→夏娃，Cain→该隐，Abel→亚伯，Seth→塞特\n"
            "   Enoch→以诺，Noah→挪亚，Shem→闪，Ham→含，Japheth→雅弗\n"
            "   Abraham/Abram→亚伯拉罕/亚伯兰，Sarah/Sarai→撒拉/撒莱，Hagar→夏甲\n"
            "   Ishmael→以实玛利，Isaac→以撒，Rebekah→利百加，Esau→以扫\n"
            "   Jacob→雅各，Leah→利亚，Rachel→拉结，Laban→拉班，Joseph→约瑟\n"
            "   Lot→罗得，Melchizedek→麦基洗德，Pharaoh→法老，Moses→摩西\n"
            "   Sodom→所多玛，Gomorrah→蛾摩拉，Canaan→迦南，Egypt→埃及\n"
            "   Eden→伊甸，Babel→巴别，Ararat→亚拉腊，Israel→以色列\n"
            "   神名：Elohim→以罗欣（神），Jehovah→耶和华，El Shaddai→全能的神\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Augustine→奥古斯丁\n"
            "   Jerome→耶柔米，Servetus→塞尔维特，Vulgate→武加大\n"
            "8. 章节引用格式：创世记 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    faith→信心，grace→恩典，promise→应许，flesh→肉体\n"
            "11. 创世记专属术语：\n"
            "    the beginning→起初，creation→创造，to create→创造\n"
            "    chaos→混沌，without form and void→空虚混沌，the deep/abyss→深渊\n"
            "    firmament→穹苍，the waters→水，the image of God→神的形象\n"
            "    the fall→堕落，the flood/deluge→洪水，the ark→方舟\n"
            "    the serpent→蛇，the tree of life→生命树，the tree of knowledge→分别善恶树\n"
            "    the seed→后裔/种子，blessing→祝福，birthright→长子名分\n"
            "    the patriarchs→列祖，the covenant→约，circumcision→割礼\n"
            "    the firstborn→长子，altar→祭坛，sacrifice→祭物/献祭\n"
            "    the Sabbath→安息日，to bless→赐福，to curse→咒诅\n"
            "    dominion→治理/管辖，the Word→道，the Spirit→（圣）灵"
        ),
    },
    'harmony-law-1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-law-1-en',
        'cache':  ROOT / 'calvin_raw/harmony-law-1/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony-law-1/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《律法合参》"
            "（又称《摩西五经合参》，Harmony of the Law，即出埃及记至申命记"
            "四卷按主题合参编排的注释）第一卷。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO EXODUS X:Y</span> 的 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 双栏经文表 calvin-parallel：左栏英文经文→照抄简体和合本原文，右栏"
            "拉丁文原样保留（不翻译）；表结构 <tr><td>...</td><td>...</td></tr> 不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 标题块：THE FIRST/SECOND... COMMANDMENT→第一/第二…诫，"
            "EXPOSITION OF...→…的阐释，PREFACE TO THE LAW→律法序言，"
            "THE SUM/USE/SANCTIONS OF THE LAW→律法的总义/功用/赏罚，"
            "SUPPLEMENTS→补充律例，TABLES OF SCRIPTURE→经文汇编，"
            "THE SONG OF MOSES→摩西之歌，RETURN TO THE HISTORY→回到历史叙事\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Genesis→创世记，Psalm(s)→诗篇，Isaiah→以赛亚书，Matthew→马太福音\n"
            "   Romans→罗马书，Hebrews→希伯来书，Acts→使徒行传，Galatians→加拉太书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    Moses→摩西，Aaron→亚伦，Pharaoh→法老，Israel→以色列，Egypt→埃及\n"
            "    Jacob→雅各，Joseph→约瑟，Abraham→亚伯拉罕，Levi→利未，Judah→犹大\n"
            "    Miriam→米利暗，Joshua→约书亚，Sinai→西奈，Horeb→何烈，Canaan→迦南\n"
            "    the Red Sea→红海，Zipporah→西坡拉，Jethro→叶忒罗，Amalek→亚玛力\n"
            "11. 章节引用格式：出埃及记 20:3，申命记 5:7（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选\n"
            "14. 律法合参专属术语：\n"
            "    the Law→律法，the Ten Commandments/the Decalogue→十诫\n"
            "    the moral law→道德律，the ceremonial law→礼仪律，\n"
            "    the judicial/political law→司法律/政治律，\n"
            "    the First/Second Table→第一版/第二版（律法），\n"
            "    commandment→诫命，precept→诫命/训诲，statute→律例，\n"
            "    ordinance→典章/条例，the tabernacle→帐幕，the sanctuary→圣所，\n"
            "    the ark (of the covenant)→约柜，the priesthood→祭司职分，\n"
            "    the high priest→大祭司，sacrifice→祭物/献祭，burnt offering→燔祭，\n"
            "    sin offering→赎罪祭，the Sabbath→安息日，circumcision→割礼，\n"
            "    the Passover→逾越节，to worship→敬拜，idolatry→拜偶像，\n"
            "    graven image→雕刻的偶像，the Lawgiver→立法者，Israelites→以色列人"
        ),
    },
    'harmony-law-2': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-law-2-en',
        'cache':  ROOT / 'calvin_raw/harmony-law-2/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony-law-2/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《律法合参》"
            "（又称《摩西五经合参》，Harmony of the Law，即出埃及记至申命记"
            "四卷按主题合参编排的注释）第二卷。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO EXODUS X:Y</span> 的 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 双栏经文表 calvin-parallel：左栏英文经文→照抄简体和合本原文，右栏"
            "拉丁文原样保留（不翻译）；表结构 <tr><td>...</td><td>...</td></tr> 不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 标题块：THE FIRST/SECOND... COMMANDMENT→第一/第二…诫，"
            "EXPOSITION OF...→…的阐释，PREFACE TO THE LAW→律法序言，"
            "THE SUM/USE/SANCTIONS OF THE LAW→律法的总义/功用/赏罚，"
            "SUPPLEMENTS→补充律例，TABLES OF SCRIPTURE→经文汇编，"
            "THE SONG OF MOSES→摩西之歌，RETURN TO THE HISTORY→回到历史叙事\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Genesis→创世记，Psalm(s)→诗篇，Isaiah→以赛亚书，Matthew→马太福音\n"
            "   Romans→罗马书，Hebrews→希伯来书，Acts→使徒行传，Galatians→加拉太书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    Moses→摩西，Aaron→亚伦，Pharaoh→法老，Israel→以色列，Egypt→埃及\n"
            "    Jacob→雅各，Joseph→约瑟，Abraham→亚伯拉罕，Levi→利未，Judah→犹大\n"
            "    Miriam→米利暗，Joshua→约书亚，Sinai→西奈，Horeb→何烈，Canaan→迦南\n"
            "    the Red Sea→红海，Zipporah→西坡拉，Jethro→叶忒罗，Amalek→亚玛力\n"
            "11. 章节引用格式：出埃及记 20:3，申命记 5:7（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选\n"
            "14. 律法合参专属术语：\n"
            "    the Law→律法，the Ten Commandments/the Decalogue→十诫\n"
            "    the moral law→道德律，the ceremonial law→礼仪律，\n"
            "    the judicial/political law→司法律/政治律，\n"
            "    the First/Second Table→第一版/第二版（律法），\n"
            "    commandment→诫命，precept→诫命/训诲，statute→律例，\n"
            "    ordinance→典章/条例，the tabernacle→帐幕，the sanctuary→圣所，\n"
            "    the ark (of the covenant)→约柜，the priesthood→祭司职分，\n"
            "    the high priest→大祭司，sacrifice→祭物/献祭，burnt offering→燔祭，\n"
            "    sin offering→赎罪祭，the Sabbath→安息日，circumcision→割礼，\n"
            "    the Passover→逾越节，to worship→敬拜，idolatry→拜偶像，\n"
            "    graven image→雕刻的偶像，the Lawgiver→立法者，Israelites→以色列人"
        ),
    },
    'harmony-law-3': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-law-3-en',
        'cache':  ROOT / 'calvin_raw/harmony-law-3/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony-law-3/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《律法合参》"
            "（又称《摩西五经合参》，Harmony of the Law，即出埃及记至申命记"
            "四卷按主题合参编排的注释）第三卷。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO EXODUS X:Y</span> 的 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 双栏经文表 calvin-parallel：左栏英文经文→照抄简体和合本原文，右栏"
            "拉丁文原样保留（不翻译）；表结构 <tr><td>...</td><td>...</td></tr> 不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 标题块：THE FIRST/SECOND... COMMANDMENT→第一/第二…诫，"
            "EXPOSITION OF...→…的阐释，PREFACE TO THE LAW→律法序言，"
            "THE SUM/USE/SANCTIONS OF THE LAW→律法的总义/功用/赏罚，"
            "SUPPLEMENTS→补充律例，TABLES OF SCRIPTURE→经文汇编，"
            "THE SONG OF MOSES→摩西之歌，RETURN TO THE HISTORY→回到历史叙事\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Genesis→创世记，Psalm(s)→诗篇，Isaiah→以赛亚书，Matthew→马太福音\n"
            "   Romans→罗马书，Hebrews→希伯来书，Acts→使徒行传，Galatians→加拉太书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    Moses→摩西，Aaron→亚伦，Pharaoh→法老，Israel→以色列，Egypt→埃及\n"
            "    Jacob→雅各，Joseph→约瑟，Abraham→亚伯拉罕，Levi→利未，Judah→犹大\n"
            "    Miriam→米利暗，Joshua→约书亚，Sinai→西奈，Horeb→何烈，Canaan→迦南\n"
            "    the Red Sea→红海，Zipporah→西坡拉，Jethro→叶忒罗，Amalek→亚玛力\n"
            "11. 章节引用格式：出埃及记 20:3，申命记 5:7（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选\n"
            "14. 律法合参专属术语：\n"
            "    the Law→律法，the Ten Commandments/the Decalogue→十诫\n"
            "    the moral law→道德律，the ceremonial law→礼仪律，\n"
            "    the judicial/political law→司法律/政治律，\n"
            "    the First/Second Table→第一版/第二版（律法），\n"
            "    commandment→诫命，precept→诫命/训诲，statute→律例，\n"
            "    ordinance→典章/条例，the tabernacle→帐幕，the sanctuary→圣所，\n"
            "    the ark (of the covenant)→约柜，the priesthood→祭司职分，\n"
            "    the high priest→大祭司，sacrifice→祭物/献祭，burnt offering→燔祭，\n"
            "    sin offering→赎罪祭，the Sabbath→安息日，circumcision→割礼，\n"
            "    the Passover→逾越节，to worship→敬拜，idolatry→拜偶像，\n"
            "    graven image→雕刻的偶像，the Lawgiver→立法者，Israelites→以色列人"
        ),
    },
    'harmony-law-4': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/harmony-law-4-en',
        'cache':  ROOT / 'calvin_raw/harmony-law-4/zh_cache',
        'out':    ROOT / 'calvin_raw/harmony-law-4/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《律法合参》"
            "（又称《摩西五经合参》，Harmony of the Law，即出埃及记至申命记"
            "四卷按主题合参编排的注释）第四卷。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO EXODUS X:Y</span> 的 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 双栏经文表 calvin-parallel：左栏英文经文→照抄简体和合本原文，右栏"
            "拉丁文原样保留（不翻译）；表结构 <tr><td>...</td><td>...</td></tr> 不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 标题块：THE FIRST/SECOND... COMMANDMENT→第一/第二…诫，"
            "EXPOSITION OF...→…的阐释，PREFACE TO THE LAW→律法序言，"
            "THE SUM/USE/SANCTIONS OF THE LAW→律法的总义/功用/赏罚，"
            "SUPPLEMENTS→补充律例，TABLES OF SCRIPTURE→经文汇编，"
            "THE SONG OF MOSES→摩西之歌，RETURN TO THE HISTORY→回到历史叙事\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Genesis→创世记，Psalm(s)→诗篇，Isaiah→以赛亚书，Matthew→马太福音\n"
            "   Romans→罗马书，Hebrews→希伯来书，Acts→使徒行传，Galatians→加拉太书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    Moses→摩西，Aaron→亚伦，Pharaoh→法老，Israel→以色列，Egypt→埃及\n"
            "    Jacob→雅各，Joseph→约瑟，Abraham→亚伯拉罕，Levi→利未，Judah→犹大\n"
            "    Miriam→米利暗，Joshua→约书亚，Sinai→西奈，Horeb→何烈，Canaan→迦南\n"
            "    the Red Sea→红海，Zipporah→西坡拉，Jethro→叶忒罗，Amalek→亚玛力\n"
            "11. 章节引用格式：出埃及记 20:3，申命记 5:7（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选\n"
            "14. 律法合参专属术语：\n"
            "    the Law→律法，the Ten Commandments/the Decalogue→十诫\n"
            "    the moral law→道德律，the ceremonial law→礼仪律，\n"
            "    the judicial/political law→司法律/政治律，\n"
            "    the First/Second Table→第一版/第二版（律法），\n"
            "    commandment→诫命，precept→诫命/训诲，statute→律例，\n"
            "    ordinance→典章/条例，the tabernacle→帐幕，the sanctuary→圣所，\n"
            "    the ark (of the covenant)→约柜，the priesthood→祭司职分，\n"
            "    the high priest→大祭司，sacrifice→祭物/献祭，burnt offering→燔祭，\n"
            "    sin offering→赎罪祭，the Sabbath→安息日，circumcision→割礼，\n"
            "    the Passover→逾越节，to worship→敬拜，idolatry→拜偶像，\n"
            "    graven image→雕刻的偶像，the Lawgiver→立法者，Israelites→以色列人"
        ),
    },
    'isaiah-1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/isaiah-1-en',
        'cache':  ROOT / 'calvin_raw/isaiah-1/zh_cache',
        'out':    ROOT / 'calvin_raw/isaiah-1/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《以赛亚书注释》（即 Calvin on Isaiah）。以赛亚书是先知书，兼有审判的宣告、悔改的呼召、对余民的安慰，以及关乎弥赛亚的预言。\n将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n严格规则：\n1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n2. 保留所有脚注引用标记不变：[^17] [^123] 等\n3. 保留所有 Markdown 标记不变：**bold** *italic*\n4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <span> <p class=\"title-block-h1\">/<h2> 等\n5. 居中经文导航 GO TO ISAIAH 1:1-31 译为「前往 以赛亚书 1:1-31」\n6. 引用的圣经经文照简体和合本原文；先知书的经文务必核对和合本措辞\n7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n8. 圣经书卷用和合本标准译名：\n   Isaiah→以赛亚书，Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Jeremiah→耶利米书，Ezekiel→以西结书，Daniel→但以理书，Hosea→何西阿书，Matthew→马太福音，John→约翰福音，Romans→罗马书，Hebrews→希伯来书\n9. 人名/地名用和合本标准译名：\n   Isaiah→以赛亚，Uzziah→乌西雅，Jotham→约坦，Ahaz→亚哈斯，Hezekiah→希西家，Sennacherib→西拿基立，Cyrus→古列，Nebuchadnezzar→尼布甲尼撒，Moses→摩西，David→大卫，Abraham→亚伯拉罕，Jacob→雅各\n   Zion→锡安，Jerusalem→耶路撒冷，Judah→犹大，Samaria→撒玛利亚，Assyria→亚述，Babylon→巴比伦，Egypt→埃及，Ephraim→以法莲，Chaldeans→迦勒底人\n10. 章节引用格式：以赛亚书 6:9，诗篇 1:1（书卷名 章:节）\n11. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n12. 加尔文术语保留学术性：righteousness→义，justification→称义，sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，the wicked→恶人，the ungodly→不敬虔的人，providence→护理，chastisement→管教，deliverance→拯救，remnant→余民，prophecy→预言\n"
        ),
    },
    'isaiah-2': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/isaiah-2-en',
        'cache':  ROOT / 'calvin_raw/isaiah-2/zh_cache',
        'out':    ROOT / 'calvin_raw/isaiah-2/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《以赛亚书注释》（即 Calvin on Isaiah）。以赛亚书是先知书，兼有审判的宣告、悔改的呼召、对余民的安慰，以及关乎弥赛亚的预言。\n将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n严格规则：\n1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n2. 保留所有脚注引用标记不变：[^17] [^123] 等\n3. 保留所有 Markdown 标记不变：**bold** *italic*\n4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <span> <p class=\"title-block-h1\">/<h2> 等\n5. 居中经文导航 GO TO ISAIAH 1:1-31 译为「前往 以赛亚书 1:1-31」\n6. 引用的圣经经文照简体和合本原文；先知书的经文务必核对和合本措辞\n7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n8. 圣经书卷用和合本标准译名：\n   Isaiah→以赛亚书，Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Jeremiah→耶利米书，Ezekiel→以西结书，Daniel→但以理书，Hosea→何西阿书，Matthew→马太福音，John→约翰福音，Romans→罗马书，Hebrews→希伯来书\n9. 人名/地名用和合本标准译名：\n   Isaiah→以赛亚，Uzziah→乌西雅，Jotham→约坦，Ahaz→亚哈斯，Hezekiah→希西家，Sennacherib→西拿基立，Cyrus→古列，Nebuchadnezzar→尼布甲尼撒，Moses→摩西，David→大卫，Abraham→亚伯拉罕，Jacob→雅各\n   Zion→锡安，Jerusalem→耶路撒冷，Judah→犹大，Samaria→撒玛利亚，Assyria→亚述，Babylon→巴比伦，Egypt→埃及，Ephraim→以法莲，Chaldeans→迦勒底人\n10. 章节引用格式：以赛亚书 6:9，诗篇 1:1（书卷名 章:节）\n11. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n12. 加尔文术语保留学术性：righteousness→义，justification→称义，sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，the wicked→恶人，the ungodly→不敬虔的人，providence→护理，chastisement→管教，deliverance→拯救，remnant→余民，prophecy→预言\n"
        ),
    },
    'jeremiah-1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/jeremiah-1-en',
        'cache':  ROOT / 'calvin_raw/jeremiah-1/zh_cache',
        'out':    ROOT / 'calvin_raw/jeremiah-1/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《耶利米书注释》（即 Calvin on Jeremiah）。耶利米书是先知书，充满对犹大的审判宣告、对悔改的恳切呼召、先知本人的哀恸与代祷，以及新约的应许。\n将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n严格规则：\n1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n2. 保留所有脚注引用标记不变：[^17] [^123] 等\n3. 保留所有 Markdown 标记不变：**bold** *italic*\n4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <span> <p class=\"title-block-h1\">/<h2> 等\n5. 居中经文导航 GO TO JEREMIAH 1:1-19 译为「前往 耶利米书 1:1-19」\n6. 引用的圣经经文照简体和合本原文；先知书的经文务必核对和合本措辞\n7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n8. 圣经书卷用和合本标准译名：\n   Jeremiah→耶利米书，Lamentations→耶利米哀歌，Isaiah→以赛亚书，Ezekiel→以西结书，Daniel→但以理书，Hosea→何西阿书，Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Deuteronomy→申命记，Kings→列王纪，Matthew→马太福音，John→约翰福音，Romans→罗马书，Hebrews→希伯来书\n9. 人名/地名用和合本标准译名：\n   Jeremiah→耶利米，Baruch→巴录，Josiah→约西亚，Jehoiakim→约雅敬，Jehoiachin→约雅斤，Zedekiah→西底家，Nebuchadnezzar→尼布甲尼撒，Nebuzaradan→尼布撒拉旦，Gedaliah→基大利，Hananiah→哈拿尼雅，Ishmael→以实玛利，Moses→摩西，David→大卫，Abraham→亚伯拉罕\n   Jerusalem→耶路撒冷，Judah→犹大，Zion→锡安，Babylon→巴比伦，Chaldeans→迦勒底人，Egypt→埃及，Assyria→亚述，Anathoth→亚拿突，Tophet→陀斐特，Euphrates→伯拉大河，Moab→摩押，Ammon→亚扪，Edom→以东，Elam→以拦\n10. 章节引用格式：耶利米书 31:31，诗篇 1:1（书卷名 章:节）\n11. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n12. 加尔文术语保留学术性：righteousness→义，justification→称义，sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，the wicked→恶人，the ungodly→不敬虔的人，providence→护理，chastisement→管教，deliverance→拯救，remnant→余民，prophecy→预言，captivity→被掳\n"
        ),
    },
    'jeremiah-2': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/jeremiah-2-en',
        'cache':  ROOT / 'calvin_raw/jeremiah-2/zh_cache',
        'out':    ROOT / 'calvin_raw/jeremiah-2/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《耶利米书注释》（即 Calvin on Jeremiah）。耶利米书是先知书，充满对犹大的审判宣告、对悔改的恳切呼召、先知本人的哀恸与代祷，以及新约的应许。\n将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n严格规则：\n1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n2. 保留所有脚注引用标记不变：[^17] [^123] 等\n3. 保留所有 Markdown 标记不变：**bold** *italic*\n4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <span> <p class=\"title-block-h1\">/<h2> 等\n5. 居中经文导航 GO TO JEREMIAH 1:1-19 译为「前往 耶利米书 1:1-19」\n6. 引用的圣经经文照简体和合本原文；先知书的经文务必核对和合本措辞\n7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n8. 圣经书卷用和合本标准译名：\n   Jeremiah→耶利米书，Lamentations→耶利米哀歌，Isaiah→以赛亚书，Ezekiel→以西结书，Daniel→但以理书，Hosea→何西阿书，Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Deuteronomy→申命记，Kings→列王纪，Matthew→马太福音，John→约翰福音，Romans→罗马书，Hebrews→希伯来书\n9. 人名/地名用和合本标准译名：\n   Jeremiah→耶利米，Baruch→巴录，Josiah→约西亚，Jehoiakim→约雅敬，Jehoiachin→约雅斤，Zedekiah→西底家，Nebuchadnezzar→尼布甲尼撒，Nebuzaradan→尼布撒拉旦，Gedaliah→基大利，Hananiah→哈拿尼雅，Ishmael→以实玛利，Moses→摩西，David→大卫，Abraham→亚伯拉罕\n   Jerusalem→耶路撒冷，Judah→犹大，Zion→锡安，Babylon→巴比伦，Chaldeans→迦勒底人，Egypt→埃及，Assyria→亚述，Anathoth→亚拿突，Tophet→陀斐特，Euphrates→伯拉大河，Moab→摩押，Ammon→亚扪，Edom→以东，Elam→以拦\n10. 章节引用格式：耶利米书 31:31，诗篇 1:1（书卷名 章:节）\n11. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n12. 加尔文术语保留学术性：righteousness→义，justification→称义，sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，the wicked→恶人，the ungodly→不敬虔的人，providence→护理，chastisement→管教，deliverance→拯救，remnant→余民，prophecy→预言，captivity→被掳\n"
        ),
    },
    'hosea': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/hosea-en',
        'cache':  ROOT / 'calvin_raw/hosea/zh_cache',
        'out':    ROOT / 'calvin_raw/hosea/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《何西阿书注释》（即 Calvin on Hosea）。何西阿书是小先知书，以婚姻的比喻揭露以色列的属灵淫乱，宣告审判，也满有神不离不弃的慈爱与呼召归回。\n将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n严格规则：\n1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n2. 保留所有脚注引用标记不变：[^17] [^123] 等\n3. 保留所有 Markdown 标记不变：**bold** *italic*\n4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <span> <p class=\"title-block-h1\">/<h2> 等\n5. 居中经文导航 GO TO HOSEA 1:1-11 译为「前往 何西阿书 1:1-11」\n6. 引用的圣经经文照简体和合本原文；先知书的经文务必核对和合本措辞\n7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n8. 圣经书卷用和合本标准译名：\n   Hosea→何西阿书，Joel→约珥书，Amos→阿摩司书，Micah→弥迦书，Isaiah→以赛亚书，Jeremiah→耶利米书，Ezekiel→以西结书，Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Deuteronomy→申命记，Kings→列王纪，Matthew→马太福音，Romans→罗马书，Hebrews→希伯来书\n9. 人名/地名用和合本标准译名：\n   Hosea→何西阿，Gomer→歌篾，Jezreel→耶斯列，Jeroboam→耶罗波安，Uzziah→乌西雅，Jotham→约坦，Ahaz→亚哈斯，Hezekiah→希西家，Moses→摩西，David→大卫，Jacob→雅各，Ephraim→以法莲\n   Israel→以色列，Judah→犹大，Samaria→撒玛利亚，Bethel→伯特利，Gilgal→吉甲，Gilead→基列，Assyria→亚述，Egypt→埃及，Baal→巴力，Baalim→众巴力\n10. 章节引用格式：何西阿书 6:6，诗篇 1:1（书卷名 章:节）\n11. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n12. 加尔文术语保留学术性：righteousness→义，justification→称义，sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，the wicked→恶人，the ungodly→不敬虔的人，providence→护理，chastisement→管教，repentance→悔改，harlotry→淫乱，idolatry→拜偶像，prophecy→预言\n"
        ),
    },
    'psalms-1': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/psalms-1-en',
        'cache':  ROOT / 'calvin_raw/psalms-1/zh_cache',
        'out':    ROOT / 'calvin_raw/psalms-1/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《诗篇注释》"
            "（即 Calvin on the Psalms），诗篇是希伯来诗歌，记录大卫等圣徒的祷告、"
            "哀歌、赞美与预言。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] [^fa1] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"scripture-ref\"> "
            "<p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；"
            "居中经文导航 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 经文框：英文经文→照抄简体和合本原文（诗篇按和合本），"
            "拉丁文原样保留（不翻译）；`<span class=\"book-name\">Psalm</span>`→诗篇，"
            "`<span class=\"verse-range\">` 内的章节数字不变；表结构不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 诗篇标题(superscription/题注)照和合本译；Selah→细拉；"
            "PSALM N→诗篇 N；篇题如 THE ARGUMENT→题旨/引言\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Isaiah→以赛亚书，"
            "Jeremiah→耶利米书，Matthew→马太福音，Romans→罗马书，Hebrews→希伯来书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    David→大卫，Saul→扫罗，Absalom→押沙龙，Solomon→所罗门，"
            "Moses→摩西，Aaron→亚伦，Abraham→亚伯拉罕，Jacob→雅各，Israel→以色列\n"
            "    Zion→锡安，Jerusalem→耶路撒冷，Judah→犹大，Philistines→非利士人\n"
            "11. 章节引用格式：诗篇 1:1，以赛亚书 6:9（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，"
            "sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，"
            "promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，"
            "the wicked→恶人，the ungodly→不敬虔的人，providence→护理，"
            "chastisement→管教，deliverance→拯救\n"
        ),
    },
    'psalms-2': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/psalms-2-en',
        'cache':  ROOT / 'calvin_raw/psalms-2/zh_cache',
        'out':    ROOT / 'calvin_raw/psalms-2/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《诗篇注释》"
            "（即 Calvin on the Psalms），诗篇是希伯来诗歌，记录大卫等圣徒的祷告、"
            "哀歌、赞美与预言。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] [^fa1] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"scripture-ref\"> "
            "<p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；"
            "居中经文导航 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 经文框：英文经文→照抄简体和合本原文（诗篇按和合本），"
            "拉丁文原样保留（不翻译）；`<span class=\"book-name\">Psalm</span>`→诗篇，"
            "`<span class=\"verse-range\">` 内的章节数字不变；表结构不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 诗篇标题(superscription/题注)照和合本译；Selah→细拉；"
            "PSALM N→诗篇 N；篇题如 THE ARGUMENT→题旨/引言\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Psalm(s)→诗篇，Genesis→创世记，Exodus→出埃及记，Isaiah→以赛亚书，"
            "Jeremiah→耶利米书，Matthew→马太福音，Romans→罗马书，Hebrews→希伯来书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    David→大卫，Saul→扫罗，Absalom→押沙龙，Solomon→所罗门，"
            "Moses→摩西，Aaron→亚伦，Abraham→亚伯拉罕，Jacob→雅各，Israel→以色列\n"
            "    Zion→锡安，Jerusalem→耶路撒冷，Judah→犹大，Philistines→非利士人\n"
            "11. 章节引用格式：诗篇 1:1，以赛亚书 6:9（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，"
            "sanctification→成圣，covenant→约/盟约，grace→恩典，faith→信心，"
            "promise→应许，flesh→肉体，election→拣选，the godly→敬虔人，"
            "the wicked→恶人，the ungodly→不敬虔的人，providence→护理，"
            "chastisement→管教，deliverance→拯救\n"
        ),
    },
    'joshua': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/joshua-en',
        'cache':  ROOT / 'calvin_raw/joshua/zh_cache',
        'out':    ROOT / 'calvin_raw/joshua/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《约书亚记注释》"
            "（即 Calvin on Joshua"
            "，记载以色列人进迦南、分地的历史。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签与结构不变：<p style=\"...\"> <strong> <div> <span> "
            "<table class=\"scripture-table calvin-parallel\"> <tr> <td> "
            "<h2 class=\"scripture-anchor\"...> <p class=\"title-block-h1\">/<h2> 等\n"
            "5. 保留 AGES code 不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）；\n"
            "   居中经文导航 <span style=\"color:#000080\">GO TO EXODUS X:Y</span> 的 GO TO 译为「前往」，书卷章节照和合本\n"
            "6. 双栏经文表 calvin-parallel：左栏英文经文→照抄简体和合本原文，右栏"
            "拉丁文原样保留（不翻译）；表结构 <tr><td>...</td><td>...</td></tr> 不变\n"
            "7. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "8. 标题块：THE FIRST/SECOND... COMMANDMENT→第一/第二…诫，"
            "EXPOSITION OF...→…的阐释，PREFACE TO THE LAW→律法序言，"
            "THE SUM/USE/SANCTIONS OF THE LAW→律法的总义/功用/赏罚，"
            "SUPPLEMENTS→补充律例，TABLES OF SCRIPTURE→经文汇编，"
            "THE SONG OF MOSES→摩西之歌，RETURN TO THE HISTORY→回到历史叙事\n"
            "9. 圣经书卷用和合本标准译名：\n"
            "   Exodus→出埃及记，Leviticus→利未记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Genesis→创世记，Psalm(s)→诗篇，Isaiah→以赛亚书，Matthew→马太福音\n"
            "   Romans→罗马书，Hebrews→希伯来书，Acts→使徒行传，Galatians→加拉太书\n"
            "10. 人名/地名用和合本标准译名：\n"
            "    Moses→摩西，Aaron→亚伦，Pharaoh→法老，Israel→以色列，Egypt→埃及\n"
            "    Jacob→雅各，Joseph→约瑟，Abraham→亚伯拉罕，Levi→利未，Judah→犹大\n"
            "    Joshua→约书亚，Caleb→迦勒，Rahab→喇合，Achan→亚干，Eleazar→以利亚撒，Jericho→耶利哥，Ai→艾城，Gibeon→基遍，Gilgal→吉甲，Shiloh→示罗，Jordan→约旦河，Canaan→迦南\n"
            "    the Red Sea→红海，Zipporah→西坡拉，Jethro→叶忒罗，Amalek→亚玛力\n"
            "11. 章节引用格式：约书亚记 1:9，申命记 5:7（书卷名 章:节）\n"
            "12. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "13. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    grace→恩典，faith→信心，promise→应许，flesh→肉体，election→拣选\n"
            "14. 律法合参专属术语：\n"
            "    the Law→律法，the Ten Commandments/the Decalogue→十诫\n"
            "    the moral law→道德律，the ceremonial law→礼仪律，\n"
            "    the judicial/political law→司法律/政治律，\n"
            "    the First/Second Table→第一版/第二版（律法），\n"
            "    commandment→诫命，precept→诫命/训诲，statute→律例，\n"
            "    ordinance→典章/条例，the tabernacle→帐幕，the sanctuary→圣所，\n"
            "    the ark (of the covenant)→约柜，the priesthood→祭司职分，\n"
            "    the high priest→大祭司，sacrifice→祭物/献祭，burnt offering→燔祭，\n"
            "    sin offering→赎罪祭，the Sabbath→安息日，circumcision→割礼，\n"
            "    the Passover→逾越节，to worship→敬拜，idolatry→拜偶像，\n"
            "    graven image→雕刻的偶像，the Lawgiver→立法者，Israelites→以色列人"
        ),
    },
    'philemon': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/philemon-en',
        'cache':  ROOT / 'calvin_raw/philemon/zh_cache',
        'out':    ROOT / 'calvin_raw/philemon/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《腓利门书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Philemon→腓利门书，Titus→提多书，1 Timothy→提摩太前书，2 Timothy→提摩太后书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Paul→保罗，Philemon→腓利门，Onesimus→阿尼西母，Apphia→亚腓亚，\n"
            "   Archippus→亚基布，Epaphras→以巴弗，Mark→马可，Aristarchus→亚里达古，\n"
            "   Demas→底马，Luke→路加，Timothy→提摩太\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Egypt→埃及\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Ephesus→以弗所，Rome→罗马，Colosse→歌罗西\n"
            "8. 章节引用格式：腓利门书 1:5，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临，\n"
            "    servant/bondman/slave→仆人/奴仆，master/lord→主人，manumission→释放/自由\n"
        ),
    },
    'titus': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/titus-en',
        'cache':  ROOT / 'calvin_raw/titus/zh_cache',
        'out':    ROOT / 'calvin_raw/titus/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《提多书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   Titus→提多书，1 Timothy→提摩太前书，2 Timothy→提摩太后书\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书\n"
            "   Paul→保罗，Titus→提多，Timothy→提摩太，Artemas→亚提马，Tychicus→推基古\n"
            "   Zenas→西纳，Apollos→亚波罗\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模\n"
            "   Vulgate→武加大\n"
            "   Israel→以色列，Egypt→埃及\n"
            "   Cretans/Cretians→革哩底人，Crete→革哩底\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Ephesus→以弗所，Rome→罗马，Nicopolis→尼哥波立\n"
            "8. 章节引用格式：提多书 1:5，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临，\n"
            "    wrath to come→将来的忿怒，idols→偶像，conversion→归主/悔改归正，\n"
            "    bishop/elder→监督/长老，presbyter→长老，deacon→执事，\n"
            "    heretic→异端，schism→分裂，heresy→异端邪说"
        ),
    },
    '1thess': {
        'mode':   'multi_chapter',
        'src':    ROOT / 'calvin/1thessalonians-en',
        'cache':  ROOT / 'calvin_raw/1thessalonians/zh_cache',
        'out':    ROOT / 'calvin_raw/1thessalonians/zh_chapters',
        'system': (
            "你是一位精通加尔文神学的中文译者，正在翻译加尔文《帖撒罗尼迦前书注释》。\n"
            "将英文翻译成简体中文，忠实原文，保持加尔文神学深度与文体风格。\n"
            "严格规则：\n"
            "1. 只输出译文，不加任何说明，不重复原文，不要前言或解释\n"
            "2. 保留所有脚注引用标记不变：[^17] [^f23] [^ft35] 等\n"
            "3. 保留所有 Markdown 标记不变：**bold** *italic*\n"
            "4. 保留所有 HTML 标签不变：<p style=\"...\"> <strong> <div> <h2 class=\"scripture-anchor\"...> 等\n"
            "5. 保留 AGES code 与 scripture-box 结构不变（<span class=\"ages-code\">&lt;NNNNNN&gt;</span>）\n"
            "6. 拉丁文/法文/希腊文/希伯来文保留原文，括号附中文译音/译义，如：\n"
            "   ἐκκλησία（教会）、Inter nos（在我们中间）、שלום（shalom，平安）\n"
            "7. 圣经书卷/人名用和合本标准译名：\n"
            "   1 Thessalonians→帖撒罗尼迦前书，2 Thessalonians→帖撒罗尼迦后书\n"
            "   1 Corinthians→哥林多前书，2 Corinthians→哥林多后书\n"
            "   Acts→使徒行传，Matthew→马太福音，Mark→马可福音，Luke→路加福音，John→约翰福音\n"
            "   Romans→罗马书，Galatians→加拉太书\n"
            "   Ephesians→以弗所书，Philippians→腓立比书，Colossians→歌罗西书\n"
            "   Timothy→提摩太书，Titus→提多书，Philemon→腓利门书\n"
            "   Hebrews→希伯来书，James→雅各书，Peter→彼得书，Jude→犹大书，Revelation→启示录\n"
            "   Genesis→创世记，Exodus→出埃及记，Numbers→民数记，Deuteronomy→申命记\n"
            "   Psalm(s)→诗篇，Isaiah→以赛亚书，Jeremiah→耶利米书，Joel→约珥书\n"
            "   Daniel→但以理书，Zechariah→撒迦利亚书，Malachi→玛拉基书\n"
            "   Paul→保罗，Silvanus/Silas→西拉，Timothy→提摩太\n"
            "   Aquila→亚居拉，Priscilla→百基拉，Barnabas→巴拿巴\n"
            "   Mary→马利亚，David→大卫，Abraham→亚伯拉罕，Moses→摩西，Adam→亚当，Eve→夏娃\n"
            "   Erasmus→伊拉斯谟，Chrysostom→屈梭多模，Wiclif→威克里夫，Cranmer→克兰麦\n"
            "   Vulgate→武加大, Epicurus→伊壁鸠鲁，Diogenes→第欧根尼\n"
            "   Corderius/Cordier→科尔德里乌斯（加尔文的拉丁文老师）\n"
            "   Israel→以色列，Pharaoh→法老，Egypt→埃及，Sinai→西乃，Sodom→所多玛\n"
            "   Pharisees→法利赛人，Sadducees→撒都该人，Gentiles→外邦人，Jews→犹太人\n"
            "   Jerusalem→耶路撒冷，Thessalonica→帖撒罗尼迦，Berea→庇哩亚\n"
            "   Philippi→腓立比，Athens→雅典，Corinth→哥林多，Ephesus→以弗所\n"
            "   Macedonia→马其顿，Achaia→亚该亚，Asia→亚西亚，Galatia→加拉太\n"
            "8. 章节引用格式：帖撒罗尼迦前书 1:1，罗马书 2:23（书卷名 章:节）\n"
            "9. 脚注中的法文/拉丁文原文保留，破折号后附中文译文\n"
            "10. 加尔文术语保留学术性：righteousness→义，justification→称义，\n"
            "    sanctification→成圣，covenant→约/盟约，atonement→赎罪/挽回祭，\n"
            "    regeneration→重生，election→拣选，predestination→预定，\n"
            "    sovereignty→主权，providence→护理，redemption→救赎，\n"
            "    apostle→使徒，ministry→事奉/职事，doctrine→教义/教训，\n"
            "    gospel→福音，kingdom of God→神的国，Holy Ghost/Spirit→圣灵，\n"
            "    hope→盼望，faith→信心，charity/love→爱心/爱，patience→忍耐，\n"
            "    resurrection→复活，flesh→肉体，Coming (of Christ)→（基督的）降临，\n"
            "    wrath to come→将来的忿怒，idols→偶像，conversion→归主/悔改归正"
        ),
    },
}

# 运行时由 main() 注入下面三个全局变量
SRC = CACHE_DIR = OUT = SYSTEM = None


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def md5key(text: str) -> str:
    return hashlib.md5(text.encode('utf-8')).hexdigest()[:16]


# CLI_TRIM_FLAGS 见 claude_usage.py：不发工具定义 / MCP / CLAUDE.md / skills /
# hooks，默认 29,142 token/次 → 287。这里 re-export 供老调用方（translate_owen
# 等）继续 `tf.CLI_TRIM_FLAGS` 引用。


def call_claude(prompt: str, timeout: int = 300, max_retries: int = 3,
                label: str = '') -> str:
    """调用 claude CLI；遇到失败重试 max_retries 次（指数退避 5/15/30s）。

    每次调用会打印 token 用量（见 claude_usage.tracker），脚本结束打印汇总。
    """
    import time
    last_err = ''
    for attempt in range(max_retries):
        if attempt:
            wait = 5 * (3 ** (attempt - 1))
            print(f'    [retry {attempt}] {last_err[:120]} | wait {wait}s', flush=True)
            time.sleep(wait)
        try:
            out = call_cli(['--system-prompt', SYSTEM], prompt,
                           timeout=timeout, label=label)
        except subprocess.TimeoutExpired:
            last_err = f'TimeoutExpired({timeout}s)'
            continue
        except RuntimeError as e:
            last_err = str(e)
            continue
        if out:
            return out
        last_err = 'CLI 返回空响应'
    raise RuntimeError(f'claude CLI failed after {max_retries} retries: {last_err}')


def md_inline_to_html(s: str) -> str:
    """<td> 里 kramdown 不解析 markdown，模型偶尔输出的 **x** / *x* 会显示成
    字面星号（1cor 1/15 曾留下 3 处）。html_td_row / html_th 重组前转回标签。
    注意 md_table_row 走的是 markdown 表格，那里 ** 是对的，不要套用。"""
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    return re.sub(r'(?<![\*\w])\*([^*\n]+?)\*(?![\*\w])', r'<em>\1</em>', s)


def translate_batch(texts: list) -> list:
    """
    一次 claude CLI 调用翻译多段文本。
    用 <<<N>>> 分隔符标记每段，解析响应时按编号提取。
    """
    parts = [f'<<<{i+1}>>>\n{t}' for i, t in enumerate(texts)]
    prompt = '请按编号顺序翻译以下各段（加尔文腓立比书注释），保持 <<<N>>> 格式输出：\n\n' + '\n\n'.join(parts)

    raw = call_claude(prompt)

    # 解析 <<<N>>> 格式响应
    result = [None] * len(texts)
    for m in re.finditer(r'<<<(\d+)>>>\s*\n(.*?)(?=<<<\d+>>>|\Z)', raw, re.DOTALL):
        idx = int(m.group(1)) - 1
        if 0 <= idx < len(texts):
            result[idx] = m.group(2).strip()

    # fallback：解析失败的逐条翻译
    for i, t in enumerate(result):
        if t is None:
            try:
                result[i] = call_claude(texts[i], timeout=120)
            except Exception:
                result[i] = texts[i]  # 保留原文

    return result


def cached_translate(texts: list, resume: bool) -> list:
    """批量翻译，已有缓存的直接读取。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    results = [None] * len(texts)
    pending_idx = []

    for i, t in enumerate(texts):
        f = CACHE_DIR / f'{md5key(t)}.txt'
        if resume and f.exists() and f.stat().st_size > 2:
            results[i] = f.read_text(encoding='utf-8')
        else:
            pending_idx.append(i)

    # 分批翻译未命中缓存的
    for batch_start in range(0, len(pending_idx), BATCH):
        batch_pos = pending_idx[batch_start:batch_start + BATCH]
        batch_texts = [texts[i] for i in batch_pos]
        print(f'  翻译第 {batch_start+1}–{batch_start+len(batch_pos)} 段（共 {len(pending_idx)} 段未缓存）...', flush=True)
        zh_list = translate_batch(batch_texts)
        for i, zh in zip(batch_pos, zh_list):
            results[i] = zh
            f = CACHE_DIR / f'{md5key(texts[i])}.txt'
            f.write_text(zh, encoding='utf-8')

    return results


# ── 行分类 ────────────────────────────────────────────────────────────────────

def classify(line: str):
    """
    返回 (kind, data)：
      'pass'            → data = line（原样输出）
      'h1'              → data = heading text
      'h2'              → data = heading text
      'bq'              → data = blockquote content
      'fn'              → data = (key, footnote_text)
      'md_table_header' → data = (bold_ref_text, full_line)  # | **PHIL 1:1** | |
      'md_table_sep'    → data = line  # |---|---|
      'md_table_row'    → data = (left_en, right_lat, full_line)
      'body'            → data = paragraph text
    """
    # 空行 / 页码 / 水平线 / HTML结构标签
    stripped = line.strip()
    if not stripped:
        return ('pass', line)
    if re.match(r'^<!-- PAGE \d+ -->', line):
        return ('pass', line)
    if stripped == '---':
        return ('pass', line)
    if re.match(r'^</?(?:table|tbody|thead|tr)[\s>]', line) and '<td' not in line:
        return ('pass', line)
    # HTML 结构包装标签（独立成行的开/闭 div、p class、span class 等无文本内容）
    # 这类纯标签行不含可翻译英文，须 pass，否则被孤立发给 Claude，
    # Claude 看不到正文会拒绝并产出 "未收到需要翻译的英文正文" meta-message
    if re.match(r'^<div\b[^>]*>\s*$', stripped):
        return ('pass', line)
    if stripped == '</div>':
        return ('pass', line)
    if re.match(r'^<p\s+class="scripture-ref">[^<]+</p>\s*$', stripped):
        # 形如 <p class="scripture-ref">马太福音 23:16</p> — 含书卷引用，
        # 但格式固定，Claude 翻译时可能误抹格式；pass 让发布脚本另做处理
        return ('pass', line)

    # H1 / H2
    m = re.match(r'^(#{1,2}) (.+)', line)
    if m:
        prefix = m.group(1)
        return ('h1' if prefix == '#' else 'h2', m.group(2))

    # Blockquote
    m = re.match(r'^> (.+)', line)
    if m:
        return ('bq', m.group(1))

    # Footnote definition  ([^17]: ...  or  [^f17]: ...  or  [^ft17]: ...)
    m = re.match(r'^\[\^(f?t?\d+)\]: (.+)', line, re.DOTALL)
    if m:
        return ('fn', (m.group(1), m.group(2)))

    # Markdown table separator  |---|---|
    if re.match(r'^\|[-| :]+\|$', stripped):
        return ('md_table_sep', line)

    # Markdown table row  | cell1 | cell2 |
    if stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 3:
        # 去掉首尾 |，再按 | 分割，保留空单元格
        cells = [c.strip() for c in stripped[1:-1].split('|')]
        if len(cells) >= 2:
            left, right = cells[0], cells[1]
            # 表格标题行：左列是粗体引用（如 **PHILIPPIANS 1:1-6**），右列为空
            if re.match(r'^\*\*.+\*\*$', left) and right == '':
                inner = left[2:-2]  # 去掉 **
                return ('md_table_header', (inner, line))
            # 内容行
            return ('md_table_row', (left, right, line))
        return ('pass', line)

    # HTML table row with two td columns (with optional class attributes)
    m_tr = re.match(
        # ⚠️ 两列都用 (.*?) 而非 (.+?)：拉丁列为空的行
        # `<tr><td class="scripture-en">…</td><td class="scripture-la"></td></tr>`
        # 曾因 (.+?) 要求至少一字符而整行漏判成 body，裸 HTML 被当正文送进模型，
        # CLI 直接返回 is_error（jeremiah-1 ch1 卡在这里）。全库 32 处。
        r'^<tr>(<td[^>]*>)(.*?)</td>(<td[^>]*>)(.*?)</td></tr>\s*$',
        line,
    )
    if m_tr:
        left_open  = m_tr.group(1)
        left_body  = m_tr.group(2)
        right_open = m_tr.group(3)
        right_body = m_tr.group(4)
        return ('html_td_row', (left_open, left_body, right_open, right_body))

    # HTML table header th
    if '<th' in line and '<td>' not in line:
        m_th = re.search(r'(<th[^>]*>)([^<]+)(</th>)', line)
        if m_th:
            return ('html_th', (m_th.group(1), m_th.group(2), m_th.group(3), line))

    # 普通段落
    return ('body', line)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def translate_file(src_path: Path, out_path: Path, resume: bool, dry_run: bool):
    if not src_path.exists():
        print(f'错误：找不到源文件 {src_path}')
        return False

    print(f'读取 {src_path}', flush=True)
    lines = src_path.read_text(encoding='utf-8').split('\n')

    print('分类行类型...', flush=True)
    # YAML front matter 整块 pass（元数据不翻译，由 publish 本地化）。
    # classify 是逐行无状态的，无法识别 --- 之间的字段行（如 chapter: 1 /
    # title: / prev_label:），会误当 body 送翻——既费 token，遇纯 key:数字
    # (如 chapter: 1) 还会让 LLM 回聊天/报错文本污染成品。此处显式跳过。
    segments = []
    in_fm = fm_closed = False
    for idx, l in enumerate(lines):
        if not fm_closed and l.strip() == '---':
            if not in_fm and idx == 0:
                in_fm = True
            elif in_fm:
                in_fm = False
                fm_closed = True
            segments.append(('pass', l))
            continue
        if in_fm:
            segments.append(('pass', l))
            continue
        segments.append(classify(l))

    # 统计
    from collections import Counter
    cnt = Counter(k for k, _ in segments)
    print('各类型行数：', dict(cnt))

    if dry_run:
        return True

    # 收集需要翻译的文本（按 seg index）
    # kind → text to translate
    to_translate = []  # [(seg_index, text_to_translate)]

    for i, (kind, data) in enumerate(segments):
        if kind in ('h1', 'h2', 'body', 'bq'):
            to_translate.append((i, data))
        elif kind == 'fn':
            to_translate.append((i, data[1]))
        elif kind == 'md_table_header':
            to_translate.append((i, data[0]))  # 翻译引用文字（如 PHILIPPIANS 1:1-6）
        elif kind == 'md_table_row':
            if data[0].strip():
                to_translate.append((i, data[0]))  # 翻译左列（英文）
        elif kind == 'html_td_row':
            # data = (left_open, left_body, right_open, right_body)
            # 只翻译左列（英文）
            if data[1].strip():
                to_translate.append((i, data[1]))
        elif kind == 'html_th':
            to_translate.append((i, data[1]))

    print(f'\n共 {len(to_translate)} 段需要翻译，缓存目录: {CACHE_DIR}', flush=True)

    # 批量翻译
    texts = [t for _, t in to_translate]
    zh_list = cached_translate(texts, resume)

    # 建立 seg_index → 中文 的映射
    translations = {seg_i: zh for (seg_i, _), zh in zip(to_translate, zh_list)}

    # 重建输出行
    print('\n重建 MD...', flush=True)
    out_lines = []
    for i, (kind, data) in enumerate(segments):
        zh = translations.get(i, '')

        if kind == 'pass':
            out_lines.append(data)
        elif kind == 'h1':
            out_lines.append(f'# {zh}')
        elif kind == 'h2':
            out_lines.append(f'## {zh}')
        elif kind == 'bq':
            out_lines.append(f'> {zh}')
        elif kind == 'fn':
            key = data[0]
            out_lines.append(f'[^{key}]: {zh}')
        elif kind == 'body':
            out_lines.append(zh if zh else data)
        elif kind == 'md_table_header':
            # | **PHILIPPIANS 1:1-6** | |  →  | **腓立比书 1:1-6** | |
            out_lines.append(f'| **{zh}** | |')
        elif kind == 'md_table_sep':
            out_lines.append(data)
        elif kind == 'md_table_row':
            left_en, right_lat, _ = data
            zh_left = zh if zh else left_en
            out_lines.append(f'| {zh_left} | {right_lat} |')
        elif kind == 'html_td_row':
            left_open, left_body, right_open, right_body = data
            zh_left = md_inline_to_html(zh) if zh else left_body
            out_lines.append(
                f'<tr>{left_open}{zh_left}</td>{right_open}{right_body}</td></tr>'
            )
        elif kind == 'html_th':
            prefix, text_en, suffix, original = data
            out_lines.append(original.replace(text_en, md_inline_to_html(zh), 1)
                             if zh else original)
        else:
            out_lines.append(data if isinstance(data, str) else str(data))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    output = '\n'.join(out_lines)
    out_path.write_text(output, encoding='utf-8')
    print(f'\n✓ 写入 {out_path}  ({out_path.stat().st_size:,} bytes)')
    print(f'  段落翻译：{len(to_translate)} 段')
    hit = sum(1 for (i, t) in to_translate
              if (CACHE_DIR / f'{md5key(t)}.txt').exists())
    print(f'  缓存命中：{hit}，新翻译：{len(to_translate)-hit}')
    return True


def main():
    global SRC, CACHE_DIR, OUT, SYSTEM

    ap = argparse.ArgumentParser(description='Calvin MD → 中文 MD 翻译')
    ap.add_argument('--book', default='phil', choices=list(BOOKS.keys()),
                    help='选择书卷预设配置（默认 phil）')
    ap.add_argument('--chapter', type=str, default=None,
                    help='多章模式下指定章号（或 all），单文件模式忽略')
    ap.add_argument('--resume',  action='store_true', help='断点续翻')
    ap.add_argument('--dry-run', action='store_true', help='只统计行类型不翻译')
    args = ap.parse_args()

    cfg = BOOKS[args.book]
    CACHE_DIR = cfg['cache']
    SYSTEM    = cfg['system'] + SCRIPTURE_RULE

    if cfg['mode'] == 'single':
        SRC = cfg['src']
        OUT = cfg['out']
        translate_file(SRC, OUT, args.resume, args.dry_run)
    elif cfg['mode'] == 'multi_chapter':
        if not args.chapter:
            print(f'书卷 {args.book} 是多章模式，请用 --chapter N (或 all)')
            sys.exit(1)
        src_dir = cfg['src']
        out_dir = cfg['out']
        if args.chapter == 'all':
            chapters = sorted(int(p.stem) for p in src_dir.glob('*.md') if p.stem.isdigit())
        elif args.chapter == 'preface':
            chapters = ['preface']
        else:
            chapters = [int(args.chapter)]
        for ch in chapters:
            src = src_dir / f'{ch}.md'
            out = out_dir / f'{ch}.md'
            label = '前言' if ch == 'preface' else f'第 {ch} 章'
            print(f'\n=== {label} ===')
            translate_file(src, out, args.resume, args.dry_run)


if __name__ == '__main__':
    main()
