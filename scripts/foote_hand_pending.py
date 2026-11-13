#!/usr/bin/env python3
"""福特《路加福音讲义》一页一图待核条目·用户同意后逐条定（2026-11-12 用户令「照建议处理」）。

foote_page_check 的待核 65 条（模型一次看图读法、无第二来源）按用户同意的建议处理：
  1 上下文明显的英文词——照模型读法落（PLAIN）；
  2 正文里读花的注号、整条卷进正文的页脚注——从正文删出，该页注区没有的按转录补，转录 [?] 处用模型同位读法
    （已与转录通配相合，见 page_check 的 W 闸）；
  3 数字——第 113 讲 `5;` 与转录注文相合，第 25 讲 Juvenal iii. 296 引文相合，第 111 讲 `9-73.` 看图（首位有墨点，可辨 9）；
  4 希腊词——与转录通配相合的照落；
  5 夹斜体/注号的——逐条按页图与转录拼。
未处理的（第 17 讲 `countries^ un^ per`、第 30 讲读崩的希腊注两行、第 114 讲 Εὐθ[?]ως 一条）留待看图。

    python3 scripts/foote_hand_pending.py --rules   # 链条位置：foote_page_check --apply 之后 → hand_pending_fixes.tsv
    python3 scripts/foote_hand_pending.py --apply
"""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adjudicate_foote_ocr as A  # noqa: E402
import foote_image_check as I  # noqa: E402
import foote_notes_missing as M  # noqa: E402

RULES = A.RAW / 'hand_pending_fixes.tsv'
FN = A.FN_MARK

# 1、3、4、5：(讲, 原串, 改作)
PLAIN = [
    ('005', '<!-- NOTE p.66 --> • Gen. xvii.', '<!-- NOTE p.66 --> ♦ Gen. xvii.'),
    ('019', 'shore ; I>€', None),          # 占位：第 19 讲 I>€ 在注区读花行内，下面整行换
    ('021', 'said t<^ the apostles', 'said to the apostles'),
    ('021', 'make c^" their sickness', 'make on their sickness'),
    ('021', 'paralytic' + FN + '^ sins', "paralytic's sins"),
    ('023', 'keep a £i8t,', 'keep a fast,'),
    ('024', 'the ears qfcorn^ and', 'the ears of corn, and'),
    ('024', "said: ''{But if", 'said: "But if'),
    ('033', 'save us fh>m', 'save us from'),
    ('054', 'U8<|ue', 'usque'),
    ('079', 'the *S3d* verse', 'the 33d verse'),
    ('086', 'and not to indi • viduals', 'and not to individuals'),
    ('089', 'xiv. l3;', 'xiv. 13;'),
    ('100', '\\.q^', 'to'),
    ('101', 'promis<»', 'promise'),
    ('103', 'epclesiastics^l', 'ecclesiastical'),
    ('103', ' qi^ ', ' on '),
    ('111', 'Eumenid. >^73w', 'Eumenid. 9-73.'),
    ('113', '*1>t*', 'Dr'),
    ('127', 'W^fil', 'Wolfii'),
    ('128', 'Exj^ed,', 'Exped.'),
    ('128', 'sieptua^nt,', 'Septuagint,'),
    ('130', 't|iJ', 'the'),
    ('133', 'Sa^V^^^t^kv', 'Sabbath'),
    ('135', ' <m ', ' on '),
    # 页缝重问后多出的页首英文词（用户同意的第 1 类）
    ('011', 'their con<\\* elusion.', 'their conclusion.'),
    ('013', 'abandoned. «\\* Therefore', 'abandoned. "Therefore'),
    ('043', 'into the home^ he', 'into the house, he'),
    ('085', 'in that* tr/^icA *is', 'in that* which *is'),
    ('086', 'are exeecdm^ iadiffeRat', 'are exceedingly iadiffeRat'),
    ('109', 'fills jo\\|pbeart8 with', 'fills your hearts with'),
    ('132', 'that is, ^hen the women', 'that is, when the women'),
    # 第 24 讲 p.348 读崩的一句：看页图整句读定（2026-11-12）
    ('024', 'willingly and cWcifnHr,', 'willingly and cheerfully.'),
    ('024', '*Lei m ns^ee ttn ir ikrm mmihmtmig stm/^titi* ly *tke ^fpiieatum \\*if tioM mirmdAt* to*tpirifmiJ iku^tj^td* '
     'then have done.', '*Let us notice two or three sentiments suggested by the application of this miracle, to spiritual '
     'things,* and then have done.'),
    ('024', 'restoring die dead to life, andthehlind toaght—to tnmthe attention',
     'restoring the dead to life, and the blind to sight—to turn the attention'),
    # 经文引文里墨渍盖住/读花的字：按钦定本（eBible KJV2006）同节补，用户 2026-11-12 同意「补」。
    # 雅 5:20；路 13:5、17:21、17:25、17:28、17:37、16:31、9:56、4:16；林前 8:13；诗 38:4–6；拿 2:8
    ('021', 'the error a^^ his way', 'the error of his way'),
    ('021', 'a multitud -^ of sins', 'a multitude of sins'),
    ('071', 'Nay: *hut^ except', 'Nay: *but, except'),
    ('091', "and he r^'ected of", 'and be rejected of'),
    ('091', 'of Lot; the^ did eat', 'of Lot; they did eat'),
    ('091', 'unto them, W^heresoever', 'unto them, Wheresoever'),
    ('091', 'gathered together.' + FN + '^\n', 'gathered together."' + FN + '\n'),
    ('091', 'they na^^ Lo^ here I oVy Lo^ therer*', 'they say, Lo here! or, lo there!*'),
    ('087', 'from the dead.^\n', 'from the dead."\n'),
    ('089', 'brother to offend«"\n', 'brother to offend."\n'),
    ('090', 'too heavy for me."-^" I am', 'too heavy for me."—"I am'),
    ('121', 'own n^ercy."', 'own mercy."'),
    ('050', 'and he and *^^they went"* forward "^0 *another village"*', 'and he and "*they went*" forward "*to another village*"'),
    ('016', 'of Nazareth *^^ on the Sabbath-day', 'of Nazareth "*on the Sabbath-day'),
    # 收尾一批（转录同位相合，或看页图）：2026-11-12
    ('001', "says one, '^ for their", 'says one, "for their'),
    ('001', 'com« manding', 'commanding'),
    ('041', 'curiosity, aii<|.the exciting', 'curiosity, and the exciting'),
    ('041', 'is wheii t^erthings which', 'is when the things which'),
    ('084', '"an *hundred measures^\\* or corg^\\* ^^ (^ reheat,"* he', '"*an hundred measures*," or *cors*,' + FN + ' "*of wheat*," he'),
    ('090', 'be •omplete.', 'be complete.'),
    ('128', 'of bea¥en«\n', 'of heaven.\n'),
    ('131', 'a^trisxistis.', 'adstrinxistis.'),
    ('111', 'praelium"—^"', 'prælium"—"'),
    ('094', "palmis.''—4S^«7tMj *Italicus,* lib. zii.", 'palmis."—*Silius Italicus*, lib. xii.'),
    ('016', "*% 'Αναπτυξας ra fisfikuv, »tu lifiktytfiifAes l^tiy* &C.—*Herodotus,* lib. i.",
     '‡ Ἀναπτυξας το βιβλιον, και ἐπιλεγομενος ἐφη, &c.—*Herodotus,* lib. i.'),
    ('030', '*^Evivg xtfiuw fMyav^ m* »«Xir«f\n\n<!-- NOTE p.428 --> flToByrA *^XriffafAivos x^vffau.*',
     'Ἐνδυς κιθωνα μεγαν,—τον κολπον παντα πλησαμενος χρυσου.'),
    ('101', '4lir«rriAA.«', 'ἀποστελλει'),
    # 第 7 讲 p.94：第 2 版扫描页左下缺损一块（几行行首丢失，OCR 乱补），按第 3 版同句补（第 3 版 ABBYY 第 82 叶）
    ('007', 'the cure is not to be I. found in contemplating', 'the cure is not to be found in contemplating'),
    ('007', 'On the contrary, re should keep', 'On the contrary, we should keep'),
    ('007', '<!-- PAGE 94 -->\nad at the same time', '<!-- PAGE 94 -->\nand at the same time'),
    ('007', 'and i the^aring which', 'and into the bearing which'),
    ('007', 'individual hope\n\n<!-- PAGE 94 -->\nGod grant', 'individual hope and destiny.\n\n<!-- PAGE 94 -->\nGod grant'),
    ('007', 'may be accompany the evangelist Luke, in his resting account',
     'may be promoted, as we accompany the evangelist Luke, in his beautiful and interesting account'),
    ('007', "<!-- PAGE 94 -->\nI of the Saviour's birth.", "<!-- PAGE 94 -->\nother circumstances of the Saviour's birth."),
    # 第 17 讲：印面 `un-` 转行接 `per`，原书排错，照录
    ('017', 'other countries^ un^ per the', 'other countries, un-per the'),
    # 第 24 讲 p.349 末行 `service.` 被抽进了注区（该页无脚注），挪回正文末
    ('024', 'strength you have in his\n\n---\n', 'strength you have in his service.\n\n---\n'),
    ('024', '\n\n<!-- NOTE p.349 --> •€mc6\\*\n', '\n'),
    # 第 1 讲 p.13：段首 `3d` 左边的墨点读成了句点（看页图）；其前的分段是原书排版（`in the` 末行、`3d place` 缩进另起），照录
    ('001', '<!-- PAGE 13 -->\n.3d place,', '<!-- PAGE 13 -->\n3d place,'),
    # 5：注区读花的希腊行
    ('019', "ζωγρῶν vivos capieni. *T»9* K^Mrav i^«y(iir«v. *'Arrvmynf litty^n^n" + FN + '* Horodotuf.',
     '♦ ζωγρῶν vivos capiens. Τον Κροισον ἐζωγρησαν. Ἀστυαγης ἐζωγρηθη. Herodotus.'),
    ('054', 'him/^ *^ty^* dt «ra^t^tX^«iy r^v ', 'him." Σιγῇ δε παρεξελθειν τον '),
    ('075', 'o' + FN + '»u ', 'ὁκου '),
    ('081', 'fu^*— TMf *$bTtifdMrM9 T» ', 'μερος— των κτηματων το '),
    ('101', "f Matt. zxi. 7. *\\*Ein»mft0'»9 Waw avv09,* thai is,", '† Matt. xxi. 7. Ἐπεκαθισαν ἐπανω αὐτων, that is,'),
    ('106', '*^\\** Chi ti fa carezze piik che non suole, O t' + FN + ' ha ingannato, o ingannar ti Tuole."\'\n\n'
     '<!-- NOTE p.213 --> *Italian proverb, quoted by J)r A. Clarke,*',
     '♦ "Chi ti fa carezze più che non suole, O t\' ha ingannato, o ingannar ti vuole." *Italian proverb, quoted by Dr A. Clarke.*'),
    ('114', "*X \\*Aito'\\pvx«fr«at M^etvtcn kvto ^oSov,* &c.", "‡ 'Αποψυχοντων ἀνθρωπων ἀπο φοβου, &c."),
    ('128', '\\6tXti.*—*Xen,', 'ἐθελει.*—*Xen.'),
    ('131', 'r»s ^myovas* «iri<r^/y$«r», «', 'τας σιαγονας* ἀπεσφιγξατε, "'),
    ('131', "Ἐπιφωσκε was lighting up. See criticisms by Dr Campbell, Clarke, &0' t John xix. 41. ^ Isa. liii. 9.",
     '♦ Ἐπιφωσκε, was lighting up. See criticisms by Dr Campbell, Clarke, &c.\n\n<!-- NOTE p.579 --> † John xix. 41.'
     '\n\n<!-- NOTE p.579 --> ‡ Isa. liii. 9.'),
    ('133', '♦ MaU. V. *"SI. \\* ^Q\\. it' + FN + "»^w Wt «t#sH'«i.",
     '♦ Matt. v. 22.\n\n<!-- NOTE p.610 --> † Not μωροι but ἀνοητοι.'),
]

# 2：卷进正文的页脚注：(讲, 正文原串, 正文改作, 页, [注条]) —— 注条空表＝该页注区已有，只删正文
LEAKS = [
    ('019', 'either Numb, xxxiv. 11; Josh. xii. 3. f I>€ Bello, iu. 10. see', 'either see', '266', []),
    ('113', 'massacres. Wars, VI., viii 6} IX., it 3. A very', 'massacres. A very', '309', []),
    ('070', " \\*Ai«'r«y, their smallest coin« about the third part of our farthing. a thing", ' a thing', '437',
     ['♦ Λεπτον, their smallest coin, about the third part of our farthing.']),
    ('078', ' *\\*Afairti^ovf,* the disabled in any way. f Grotius. be profitable', ' be profitable', '523',
     ["♦ 'Αναπηρους, the disabled in any way.", '† Grotius.']),
    ('025', 'in\n\n<!-- PAGE 351 -->\n " Ede ubi consistas, in qua te qusero proseucha."\n\n<!-- PAGE 351 -->\n*Juvenal,* iii. 29(>.'
     '\n\n<!-- PAGE 351 -->\nPhilo (against Flaccus) complains that αἱ προσευχαι were demolished: and Josephus says the '
     'people were gathered *us m' + FN + '* describing', 'in\n\n<!-- PAGE 351 -->\ndescribing', '351',
     ['♦ "Ede ubi consistas, in qua te quæro proseucha." *Juvenal*, iii. 296. Philo (against Flaccus) complains that '
      'αἱ προσευχαι were demolished: and Josephus says the people were gathered εἰς την προσευχην.']),
    ('023', ' *\'^.ym^ov,* t Josh. ix. 4. of wine', ' of wine', '330', ["♦ 'Αγναφου.", '† Josh. ix. 4.']),
    ('066', ' *lAtrtu^tX,t9$u* -j- Doddridge. privileges', ' privileges', '382', ['♦ Μετεωριζεσθε.', '† Doddridge.']),
    ('070', " • 'Arf»XX«;c^ft/. f Prov. vi. 1-5. J Gen. xxxii.; 1 Sam. xxv. 18. of their time", ' of their time', '436',
     ["♦ 'Απηλλαχθαι.", '† Prov. vi. 1-5.', '‡ Gen. xxxii.; 1 Sam. xxv. 18.']),
    ('089', ' *iMtvhatXm,* \\*|\\* Lev. xix. 14. fall into sin', ' fall into sin', '664', ['♦ Σκανδαλα.', '† Lev. xix. 14.']),
    ('105', " *'Ax^aymuMf,* Eph. u. 20; and κεφαλη γωνιας, as here. death.", ' death.', '205',
     ["♦ 'Ακρογωνιαιος, Eph. ii. 20; and κεφαλη γωνιας, as here."]),
    ('115', ' ^ See also Mark xiv. I. here,', ' here,', '341', ['♦ See also Mark xiv. 1.']),
    ('118', '"The\n\n<!-- PAGE 393 -->\n 2 Cor. i. 24; 1 Pet v. 2.\n\n<!-- PAGE 393 -->\nf Mfi^Afy, *nuTi06s,* Dr Campbell '
     'makes them correspond in the other way thus: " Let the greatest become among you as the smallest." great apostle',
     '"The\n\n<!-- PAGE 393 -->\ngreat apostle', '393',
     ['♦ 2 Cor. i. 24; 1 Pet. v. 2.', '† Μειζων, νεωτερος. Dr Campbell makes them correspond in the other way thus: '
      '"Let the greatest become among you as the smallest."']),
    ('118', "as we\n\n<!-- PAGE 395 -->\n• Henry. *X ^^'* \\*»!• J^«, t *Διατίθεμαι.* I 2 Sam. ix. 10; 1 Kings ii. 7. read",
     'as we\n\n<!-- PAGE 395 -->\nread', '395',
     ['♦ Henry.', '† Διατιθεμαι.', '‡ Rev. xxi. 14.', '§ 2 Sam. ix. 10; 1 Kings ii. 7.']),
    ('123', ' i^«»rir. t Micah y. 1. of the word', ' of the word', '458', ['♦ Δεροντες.', '† Micah v. 1.']),
    ('123', 'as putting\n\n<!-- PAGE 466 -->\n• Lev. xxi. 10. t Joseph. Ware, II. 15. 1 Mac. xl. 7L Jesus',
     'as putting\n\n<!-- PAGE 466 -->\nJesus', '466', []),
    ('124', ' *"EfSnret ka/Av^v' + FN + '* "f' + FN + ' Luke xiii, 1. and jealous', ' and jealous', '482',
     ["♦ 'Εσθητα λαμπραν.", '† Luke xiii. 1.']),
    ('103', '\n\n<!-- PAGE 179 -->\n• Campbell.\n\n<!-- PAGE 179 -->\nt " Penditque itenun narrantis ab ore"—She again hung '
     'on the mouth of the narrator.—*JBneid,* iv. 79. desire', '\n\n<!-- PAGE 179 -->\ndesire', '179', []),
]


# 疑似词模式（foote_page_check --words）待核 6 条：转录同位读法＋模型看图读法，斜体/连字符按我们的口径拼（链条：words 之后）
LATE = [
    ('033', 'save us from *mit* nns.', 'save us from our sins.'),
    ('036', '" *Wisdom ujiMtifiedafaU her* Mt/*dren"*', '" *Wisdom is justified of all her children."*'),
    ('103', '"*it wrkten, My house', '"*It is written, My house'),
    ('118', 'those *vrhose* hearU are', 'those whose hearts are'),
    ('127', 'into extcn-\\* tion,', 'into execution,'),
    ('131', 'civil magisstrate.', 'civil magistrate.'),
]
LATEF = A.RAW / 'hand_words_fixes.tsv'

# 疑似词第 2 轮（foote_page_check --words2）之后：待核逐条定（转录/钦定本/上下文明显的行末断词），印张签名删去，
# 卷进正文的页脚注删出（注区缺的补）。用户 2026-11-12「继续」。链条：words2 之后（--late2）
LATE2 = [
    ('004', 'Jer. zxxL 20.', 'Jer. xxxi. 20.'),
    ('012', 'no matiy neither', 'no man, neither'),                       # 路 3:14
    ('015', 'in parti-\\* cular,', 'in particular,'),
    ('016', 'the synagogue- service', 'the synagogue-service'),
    ('016', 'the prison- house."', 'the prison-house."'),
    ('019', 'peculiarly *ilbisr* trious.', 'peculiarly illustrious.'),
    ('021', 'goodness anctf truth', 'goodness and truth'),                  # 出 34:6–7
    ('021', 'iniquity, anctf transgression', 'iniquity, and transgression'),
    ('023', 'to van-\n\n<!-- PAGE 331 -->\nSuish their', 'to vanquish their'),
    ('024', 'and indepen- dentlj on', 'and independently on'),
    ('027', 'Matt. xiii. *bbi* "', 'Matt. xiii. 55: "'),
    ('030', 'condemn nhtt and', 'condemn not, and'),                        # 路 6:37
    ('031', "of which au ipi'ho are", 'of which all who are'),
    ('032', 'as oer- tainly', 'as certainly'),
    ('036', 'not be ngnt for', 'not be right for'),
    ('038', 'important deli- Terance', 'important deliverance'),
    ('044', 'one of* VOL. n. D *the old', 'one of the old'),                # 印张签名 VOL. II. D
    ('046', 'sajiDgunto them', 'saying unto them'),
    ('052', 'in hea' + FN + ' ven, then', 'in heaven,' + FN + ' then'),
    ('071', 'treacherously Antiquities, ztUL 1. f Luke xxiii. 12. on certain', 'treacherously on certain'),
    ('072', 'his vineyardJ' + FN + '*', 'his vineyard."' + FN + '*'),
    ('089', 'to the Co- *\\** 1 Sam. 11.17; MfOtUtSi rinthians,', 'to the Corinthians,'),
    ('098', 'all repects most', 'all respects most'),
    ('099', "Zaccheus' con- Tersion", "Zaccheus' conversion"),
    ('103', 'nature men- Mark xi 17. t 1 Kings viil 28. tioned by', 'nature mentioned by'),
    ('103', 'any uu- seemly', 'any unseemly'),
    ('106', 'is mar- yelled at', 'is marvelled at'),
    ('112', 'the *iSmah* historian', 'the Jewish historian'),
    ('114', 'coming of *\\* RoBU* ziy. 4. f Luke xix. 47\\* Matt, zxu 17. Christ', 'coming of Christ'),
    ('119', 'to /tave t/oUy that he may sift you 08 wheat', 'to have you, that he may sift you as wheat'),   # 路 22:31
    ('119', 'the ear- / nest of', 'the earnest of'),
    ('121', 'He volun' + FN + ' tarily', 'He voluntarily' + FN),
    ('123', 'They might\n\n<!-- PAGE 465 -->\nVOL. III. 2 G disbelieve him', 'They might disbelieve him'),   # 印张签名
    ('126', 'green fir- tree.', 'green fir-tree.'),
    ('127', 'parts, *ffXh* nishing', 'parts, furnishing'),
    ('127', 'Campbell, fcc, may', 'Campbell, &c., may'),
    ('135', 'fr(ym on highJ' + FN + '*', 'from on high."' + FN + '*'),      # 路 24:49
    ('136', 'among Rev. v. 6. fRey. Tiii. 3. the blessings', 'among the blessings'),
    # 第 3 批（疑似词余下的真错，转录/钦定本/上下文逐条定）
    ('001', 'understanding of sJl things', 'understanding of all things'),          # 路 1:3
    ('001', 'which the i¥ord is used', 'which the word is used'),
    ('001', 'these fovr historians', 'these four historians'),
    ('006', 'the immuta- bility of', 'the immutability of'),                       # 来 6:17
    ('009', 'after the cusof the law', 'after the custom of the law'),             # 路 2:27
    ('010', 'declaring that- God', 'declaring that God'),
    ('013', 'of Aris' + FN + ' tobulus', 'of Aristobulus' + FN),
    ('015', 'would pro- Tide, in', 'would provide, in'),
    ('018', 'the sjrna\\*gogue', 'the synagogue'),
    ('018', 'the won-\\* ders which', 'the wonders which'),
    ('019', 'has prospered- us', 'has prospered us'),
    ('019', 'higher na— ture', 'higher nature'),
    ('019', 'been alto- gethen or', 'been altogether, or'),
    ('024', 'notgreatlysurprise,andespecially', 'not greatly surprise, and especially'),
    ('025', 'was putamongtheapostles,', 'was put among the apostles,'),
    ('025', 'noble- minded', 'noble-minded'),
    ('026', 'to in- Tite them', 'to invite them'),
    ('027', 'occasional oc-*\n\n<!-- PAGE 393 -->\n*currence of', 'occasional occurrence of'),
    ('028', 'same evangelisr,', 'same evangelist,'),
    ('028', 'more con- cisely', 'more concisely'),
    ('030', 'all- sufficiency', 'all-sufficiency'),
    ('032', 'the hiding- place', 'the hiding-place'),
    ('033', 'acknowledg-\\* ment', 'acknowledgment'),
    ('034', 'accomplish this-\n', 'accomplish this.\n'),
    ('035', '**LtTKE Til. 18-23.**', '**LUKE VII. 18-23.**'),
    ('037', 'himself frcm guilt', 'himself from guilt'),
    ('037', 'more heart- affecting', 'more heart-affecting'),
    ('042', 'This terri- tory', 'This territory'),
    ('047', 'our floiilfl may live', 'our souls may live'),
    ('049', '*yriW* say', 'will say'),
    ('049', 'for pre- eminence', 'for pre-eminence'),
    ('053', "perfected praisef'", 'perfected praise?"'),                          # 太 21:16
    ('061', 'the yoke of bond-\n', 'the yoke of bondage."\n'),                   # 加 5:1，下页页首 age." 丢失
    ('066', 'than the fowlsf"*', 'than the fowls?"*'),
    ('068', 'guests, aud when', 'guests, and when'),
    ('070', '"sincereand without', '"sincere and without'),                       # 腓 1:10
    ("071", "were en- ' gaged", 'were engaged'),
    ('071', 'the childrenof men', 'the children of men'),
    ('072', 'and inpre- Tailing for', 'and in prevailing for'),
    ('074', 'kingdom overthown.', 'kingdom overthrown.'),
    ('074', 'the testimon of', 'the testimony of'),
    ('078', 'shalt be blesssd;', 'shalt be blessed;'),                            # 路 14:14
    ('080', 'to annouce the', 'to announce the'),
    ('084', 'to fradulent practices', 'to fraudulent practices'),
    ('084', 'the chil' + FN + ' dren of light', 'the children' + FN + ' of light'),
    ('084', 'the pro' + FN + ' secution of', 'the prosecution' + FN + ' of'),
    ('086', '*ihejpressed* into it', 'they *pressed* into it'),
    ('089', 'this *dntjfrom a regard', 'this *duty from a regard'),
    ('090', 'and deadily diseases', 'and deadly diseases'),
    ('091', 'I tell vou, in', 'I tell you, in'),                                   # 路 17:34
    ('093', 'asso-\\* ciated', 'associated'),
    ('094', 'of iiis own', 'of his own'),
    ('094', 'not withstand- ing', 'notwithstanding'),
    ('099', 'without gruding."', 'without grudging."'),                            # 彼前 4:9
    ('104', 'Christian mini- Btrj of', 'Christian ministry of'),
    ('105', 'as havin been', 'as having been'),
    ('110', 'gold all- over,', 'gold all over,'),
    ('110', 'run- Ding about', 'running about'),
    ('111', 'perseverance, pre- serve, or', 'perseverance, preserve, or'),
    ('115', 'the feast- day,"', 'the feast-day,"'),
    ('116', 'administered, aud then', 'administered, and then'),
    ('118', 'not yet consumated.', 'not yet consummated.'),
    ('118', 'or oppressive- authority', 'or oppressive authority'),
    ('123', 'the abjectsgathered', 'the abjects gathered'),                        # 诗 35:15
    ('123', 'have en-\\* couraged', 'have encouraged'),
    ('124', 'effectual instruetion.', 'effectual instruction.'),
    ('124', 'Herod Anti-\\* pas,', 'Herod Antipas,'),
    ('125', 'Awful impre- cation!', 'Awful imprecation!'),
    ('126', 'senate enact- ing', 'senate enacting'),
    ('127', '**LtJKE XXIII. 32-34.**', '**LUKE XXIII. 32-34.**'),
    ('127', 'in in-\\* ward anguish', 'in inward anguish'),
    ('128', 'as *ockmflh* ledged him', 'as acknowledged him'),
    ('128', 'for repen' + FN + ' tance?', 'for repentance' + FN + '?'),
    ('131', 'which eame with', 'which came with'),                                 # 路 23:55
    ('131', 'simple- hearted', 'simple-hearted'),
    ('132', 'had pre-* g *pared,', 'had prepared,'),
    ('133', 'in ge-\n\n<!-- PAGE 610 -->\nI neral, were', 'in general, were'),
]
LATE2_LEAKS = [   # (讲, 正文原串, 改作, 页, 注条)
    ('101', 'Lord." 2 Sam. xiv. 4; and 2 Kings vL 26, in,Hebrew. f Matt. xzi. 9.', 'Lord."', '152',
     ['♦ 2 Sam. xiv. 4; and 2 Kings vi. 26, in Hebrew.', '† Matt. xxi. 9.']),
    ('096', 'in Rom. xiii. 9. + Ἀπο *nornroi' + FN + '* any degree', 'in any degree', '77', ['♦ Rom. xiii. 9.', '† Ἀπο νεοτητος.']),
]
LATE2F = A.RAW / 'hand_words2_fixes.tsv'


# 单字母（foote_page_check --marks）之后：问号/注号读成字母的待核、又一批卷进正文的页脚注（13 处）。2026-11-12「继续」
LATE3 = [
    ('010', 'Mount Zion." t\n', 'Mount Zion."' + FN + '\n'),
    ('016', 'to death.' + FN + ' "t Not so', 'to death."' + FN + ' Not so'),
    ('024', 'unleavened bread." J This', 'unleavened bread."' + FN + ' This'),
    ('026', 'alluded to t as having', 'alluded to' + FN + ' as having'),
    ('056', 'its very words. J\n', 'its very words.' + FN + '\n'),
    ('106', '\nRomans." t\n', '\nRomans."' + FN + '\n'),
    ('130', 'wrought salvation, t\n', 'wrought salvation,' + FN + '\n'),
    ('135', 'had been slain." t\n', 'had been slain."' + FN + '\n'),
    ('037', 'love him most f Simon', 'love him most? Simon'),                     # 路 7:42
    ('047', 'he was H in the form', 'he was "in the form'),
    ('049', 'in the J 1th chapter', 'in the 11th chapter'),
    ('050', 'naturally v adapted', 'naturally adapted'),
    ('057', 'a serpent f or,', 'a serpent? or,'),                                 # 路 11:11
    ('070', '*S. We are here', '3. *We are here'),
    ('079', 'endless peace. f t\n\n<!-- PAGE 549 -->\nI *i*\n', 'endless peace.\n'),     # 讲末残码
    ('101', 'personified X \'\'Behold', 'personified), "Behold'),
    ('115', 'my disciples f Avulhe shall', 'my disciples? And he shall'),             # 路 22:11–12
    ('116', 'body of Christ *V* Communion', 'body of Christ?" Communion'),         # 林前 10:16
    ('072', 'but let us M improve', 'but let us all improve'),                    # 卷二 p.461 末行看图：斜体 all
    ('072', 'judgment of God *V' + FN + '* Neither', 'judgment of God?" Neither'),        # 罗 2:5，p.462 看图
    ('034', 'name of the Lord *V* Have', 'name of the Lord?" Have'),              # 伯 1:21，卷一 p.489 看图
    ('083', 'to go in to Aare* m *the feast.*', 'to go in to share in the feast.*'),  # 卷二 p.595 看图：斜体 share in
    # 第 60 讲逐页实读（卷二 pp.286–302 全部看图，2026-11-13）
    ('060', 'evil generation:' + FN + ' they seek', 'evil generation: they seek'),   # p.286 是墨点，不是注号
    ('060', 'Sun, Stand thou still', 'Sun, stand thou still'),                     # p.287 页首 stand
    ('060', 'greater than Jonas is here ."*', 'greater than Jonas is here."*'),
    ('060', 'from the.5th verse', 'from the 5th verse'),
    ('060', "greater than Solomon is here''*", 'greater than Solomon is here."*'),  # p.293 页首 here."
    ('060', "former rain unto the earth.''", 'former rain unto the earth."'),
    ('060', 'on a candlestick that they who', 'on a candlestick, that they who'),   # p.296 candle-stick,
    ('060', 'full of darkness— is in', 'full of darkness—is in'),
    ('136', 'carried up into beaTen.', 'carried up into heaven.'),                # 路 24:51；按词典会误成 beaten
    ('126', 'from *fooL"* hardiness,', 'from fool-hardiness,'),                  # 卷三 p.507 看图：行末断词 fool-／hardiness
    # 第 5 讲（卷一 pp.63–76）、第 95 讲（卷三 pp.57–70）逐页实读，2026-11-13
    ('005', 'have him called' + FN + ' 63.', 'have him called. 63.'),
    ('005', 'shall this be I And', 'shall this be! And'),
    ('005', 'the Lord was with him,"\n', 'the Lord was with him."\n'),
    ('005', 'Judea. *66.* And', 'Judea. 66. And'),
    ('005', 'make it good *?"*', 'make it good?"'),
    ('005', 'daughter- in-law', 'daughter-in-law'),
    ('005', 'he shall be called John ."*', 'he shall be called John."*'),
    ('005', 'were calling " him, *Zacharias,', 'were calling " *him, Zacharias,'),
    ('005', 'heart."( Prov. iii. 3.)', 'heart." (Prov. iii. 3.)'),
    ('005', 'epistle of Christ— written', 'epistle of Christ—written'),
    ('005', 'T)er- haps', 'perhaps'),
    ('005', '"When once heard', 'When once heard'),
    ('005', 'shall trust in the Lord,"\n', 'shall trust in the Lord."\n'),
    ('005', 'reminds its 0/ the', 'reminds us of the'),                          # us 读成 its：读成真词的一例
    ('095', '**LUKE XVIII 1&-17.**', '**LUKE XVIII. 15-17.**'),
    ('095', 'beyond Jordan.""  Great', 'beyond Jordan." " Great'),
    ('095', 'also infants"* says Luke', 'also infants,"* says Luke'),
    ('095', 'appears, In its strongest', 'appears, in its strongest'),
    ('095', 'on £Ephraim', 'on Ephraim'),
    ('095', 'rebuked them,"*— they', 'rebuked them,"*—they'),
    ('095', 'be bom again, he cannot', 'be born again, he cannot'),
    ('095', 'but now are they holy."t', 'but now are they holy."' + FN),
    ('095', 'do evil," The earlier', 'do evil." The earlier'),
    ('095', 'forbid them not"— nay', 'forbid them not"—nay'),
    ('095', 'Verily 1 say unto you', 'Verily I say unto you'),
    ('095', 'he said," Verily I say', 'he said, " Verily I say'),
    ('095', 'asks our Lord," who', 'asks our Lord, " who'),
    ('095', 'not depart from it/\\*', 'not depart from it."'),
    ('095', 'Feed my lambs/\\*', 'Feed my lambs."'),
    ('095', 'because ye were dear unto us."\n', 'because ye were dear unto us."' + FN + '\n'),
    ('095', '9, 11,13, 14, 20, 21', '9, 11, 13, 14, 20, 21'),
    ('095', 'xviii. 2, 3,4, 5', 'xviii. 2, 3, 4, 5'),
    ('095', 'm Mark y. 39, 40. 41, 42', 'in Mark v. 39, 40, 41, 42'),
    ('095', 'new-bom child in Luke iL 12,16', 'new-born child in Luke ii. 12, 16'),
    ('095', '<!-- NOTE p.59 --> ♦ Cren. xlviii. 14. f Ley. ix. 22;', '<!-- NOTE p.59 --> ♦ Gen. xlviii. 14.\n\n<!-- NOTE p.59 --> † Lev. ix. 22;'),
    ('095', '<!-- NOTE p.63 --> 2 Kings', '<!-- NOTE p.63 --> ♦ 2 Kings'),
    ('095', '<!-- NOTE p.66 --> Nicephorus', '<!-- NOTE p.66 --> ♦ Nicephorus'),
    ('095', '<!-- NOTE p.68 --> 1 Thess', '<!-- NOTE p.68 --> ♦ 1 Thess'),
    ('095', '<!-- NOTE p.69 --> Ps. cxxxi', '<!-- NOTE p.69 --> ♦ Ps. cxxxi'),
    # 印张签名混入（VOL. II. P 一类）
    ('056', 'Shorter Catechism. VOL. II. P', 'Shorter Catechism.'),
    ('087', 'article Byssus. VOL. II. 2 s', 'article Byssus.'),
    ('099', "'Αρχιτελωνης. VOL. III. H", "'Αρχιτελωνης."),
    ('111', 'the very name."—TertwWiaTi. VOL. III. T', 'the very name."—TertwWiaTi.'),
    ('085', 'nor steaL" VOL. H. *2* R', 'nor steal"'),
]
# 词中混大写（souL、gospeL、seLf）：只改大小写，改后须是真词；以下是改后虽成词但不对的，不动或另行处理
CASE_SKIP = {'mX', 'lO', 'PhiL', 'voL', 'beaTen'}
LATE3_LEAKS = [   # (讲, 正文原串, 改作, 页, 注条——空表＝注区已有)
    ('004', '<!-- PAGE 59 -->\n παιδα Acts iv. 25. *"* £o die pueri tui mihi a te literas reddiderunt." —*Cicero ad AUicum.* '
     'f Jer. xxxi. 20. This he did', '<!-- PAGE 59 -->\nThis he did', '59',
     ['♦ παιδα, Acts iv. 25. "Eo die pueri tui mihi a te literas reddiderunt." —*Cicero ad Atticum.*', '† Jer. xxxi. 20.']),
    ('034', 'imply that\n\n<!-- PAGE 484 -->\n 1 Kings xvii. 21. f 2 Kings It. SS. *t* Aotf ix. 34, 40, Si 6. he took',
     'imply that he took', '484', ['♦ 1 Kings xvii. 21.', '† 2 Kings iv. 33.', '‡ Acts ix. 34, 40, iii. 6.']),
    ('038', 'of Matt. XXvii 55. f Lake xxiii. 65. *X* Mark xvi. 9. Dorcas', 'of Dorcas', '546', []),
    ('076', "prophets. John Xvii. 4. f Heb. iL 10, v. 9, vii. 28. *X Olx ἐνδέχεται.*\n", 'prophets.\n', '503', []),
    ('079', 'without Jolm xU. 25. f Rev. xii, 11.:(: See Lecture on, God,', 'without God,', '539',
     ['♦ John xii. 25.', '† Rev. xii. 11.', '‡ See Lecture on,']),
    ('089', 'stumbled hy \\** 1 Cor. viii. t Rom. xiv. 13; 1 Cor. x. 3l *such offences', 'stumbled by such offences', '668', []),
    ('101', 'however John xi. 18. f Numb. xix. 2; Dent. ui. 3; 1 Sam. vi. 7. fabulous', 'however fabulous', '145', []),
    ('103', 'or the Maseillon, f Τὸ ἱερόν. house of God', 'or the house of God', '174', ['♦ Massillon.', '† Το ἱερον.']),
    ('107', 'traditions,\n\n<!-- PAGE 227 -->\n Acts xxiii. 6.\n\n<!-- PAGE 227 -->\nt Antiq. XIII. t. 9, x. 6, xvii. 1, 5; '
     'and XX. ix. I. Though', 'traditions,\n\n<!-- PAGE 227 -->\nThough', '227', []),
    ('108', 'by Matthew, f 2 Sam. vii. 12-16; Pg. lxxxix. 4, 29, 36; Isa. xi. 1. Isaiah,', 'by Isaiah,', '240', []),
    ('112', 'the holy Tertullian, Ap. xvi. f Wan, VI. tL I place,"', 'the holy place,"', '296', []),
    ('114', 'their Isa. 11. 6; 1 Pet. L 25; Matt. v. 18. guard', 'their guard', '333', []),
    ('132', 'opportunities 1 Cor. XT. *5-8.*, t Acts i. 3, 21, x. 40. of knowing', 'opportunities of knowing', '594', []),
]
LATE3F = A.RAW / 'hand_marks_fixes.tsv'


def late3_rules():
    out, texts = [], {}
    for lec, o, n in LATE3:
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        texts[lec] = t.replace(o, n)
        out.append((lec, o, n))
    for lec, o, n, pg, notes in LATE3_LEAKS:
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        t = t.replace(o, n)
        out.append((lec, o, n))
        if notes and pg not in M.NOTE.findall(t):
            o2, n2 = M.insert_row(t, pg, '\n\n'.join(f'<!-- NOTE p.{pg} --> {x}' for x in notes))
            t = t.replace(o2, n2)
            out.append((lec, o2, n2))
        texts[lec] = t
    # 第 101 讲注区 p.145 那行 `vol. III. K` 是印张签名，换成该页两条注
    t = texts.setdefault('101', (A.SRC / '101.md').read_text(encoding='utf-8'))
    o = '<!-- NOTE p.145 --> vol. III. K'
    if t.count(o) == 1:
        n = '<!-- NOTE p.145 --> ♦ John xi. 18.\n\n<!-- NOTE p.145 --> † Numb. xix. 2; Deut. xxi. 3; 1 Sam. vi. 7.'
        texts['101'] = t.replace(o, n)
        out.append(('101', o, n))
    # 词中混大写：小写化后是真词才改（beaTen 那种已在上表手定）；`''` 当作收引号
    for lec in sorted(p.stem for p in A.SRC.glob('*.md')):
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        for m in list(re.finditer(r"(?<![\w'])([a-zA-Z]*[a-z][A-Z][a-zA-Z]*)(?!\w)", t)):
            w = m.group(1)
            fix = w[0] + w[1:].lower() if w[0].isupper() else w.lower()
            if w in CASE_SKIP or not A._isword(fix.lower()) \
                    or re.search(r'[Ͱ-Ͽἀ-῿]', t[max(0, m.start() - 40):m.end() + 40]):
                continue
            k = 0
            while t.count(t[m.start() - k:m.end() + 1]) != 1:
                k += 5
            o = t[m.start() - k:m.end() + 1]
            out.append((lec, o, o[:k] + fix + o[-1]))
        for m in re.finditer(r"[a-z.,;:!?]''", t):
            if t[m.end():m.end() + 6] == ' *saw ':      # 第 22 讲 `he'' *saw`：不是收引号
                continue
            k = 0
            while t.count(t[m.start() - k:m.end() + 1]) != 1:
                k += 5
            o = t[m.start() - k:m.end() + 1]
            n = o[:k + 1] + '"' + o[-1]
            if o[-1].isalpha():
                n = o[:k + 1] + '" ' + o[-1]
            out.append((lec, o, n))
    LATE3F.write_text('# lecture\t原串\t改作 —— foote_hand_pending.py LATE3（单字母待核、卷入注第 3 批）；\\n 表换行\n'
                      + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {LATE3F}', file=sys.stderr)


def late2_rules():
    out, texts = [], {}
    for lec, o, n in LATE2:
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        texts[lec] = t.replace(o, n)
        out.append((lec, o, n))
    for lec, o, n, pg, notes in LATE2_LEAKS:
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        t = t.replace(o, n)
        out.append((lec, o, n))
        if pg not in M.NOTE.findall(t):
            o2, n2 = M.insert_row(t, pg, '\n\n'.join(f'<!-- NOTE p.{pg} --> {x}' for x in notes))
            t = t.replace(o2, n2)
            out.append((lec, o2, n2))
        texts[lec] = t
    LATE2F.write_text('# lecture\t原串\t改作 —— foote_hand_pending.py LATE2（疑似词第 2 轮待核逐条定）；\\n 表换行\n'
                      + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {LATE2F}', file=sys.stderr)


def late_rules():
    out = []
    for lec, o, n in LATE:
        t = (A.SRC / f'{lec}.md').read_text(encoding='utf-8')
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        out.append((lec, o, n))
    LATEF.write_text('# lecture\t原串\t改作 —— foote_hand_pending.py LATE（疑似词待核逐条定）\n'
                     + ''.join('\t'.join(r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {LATEF}', file=sys.stderr)


def rules():
    texts, out = {}, []
    for lec, o, n in PLAIN:
        if n is None:
            continue
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        texts[lec] = t.replace(o, n)
        out.append((lec, o, n))
    for lec, o, n, pg, notes in LEAKS:
        t = texts.setdefault(lec, (A.SRC / f'{lec}.md').read_text(encoding='utf-8'))
        if t.count(o) != 1:
            raise SystemExit(f'{lec}: 命中 {t.count(o)} 次 {o!r}')
        t = t.replace(o, n)
        out.append((lec, o, n))
        if notes and pg not in M.NOTE.findall(t):
            ent = '\n\n'.join(f'<!-- NOTE p.{pg} --> {x}' for x in notes)
            o2, n2 = M.insert_row(t, pg, ent)
            if t.count(o2) != 1:
                raise SystemExit(f'{lec}: 插注定位失败')
            t = t.replace(o2, n2)
            out.append((lec, o2, n2))
        texts[lec] = t
    RULES.write_text('# lecture\t原串\t改作 —— foote_hand_pending.py（一页一图待核，用户同意的建议逐条定）；\\n 表换行\n'
                     + ''.join('\t'.join(x.replace('\n', '\\n') for x in r) + '\n' for r in out), encoding='utf-8')
    print(f'规则 {len(out)} → {RULES}', file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rules', action='store_true')
    ap.add_argument('--apply', action='store_true')
    ap.add_argument('--late', action='store_true', help='疑似词待核表（链条在 foote_page_check --words 之后）')
    ap.add_argument('--late2', action='store_true', help='疑似词第 2 轮待核表（链条在 --words2 之后）')
    ap.add_argument('--late3', action='store_true', help='单字母待核表（链条在 --marks 之后）')
    a = ap.parse_args()
    if a.rules and a.late3:
        late3_rules()
    elif a.apply and a.late3:
        if LATE3F.exists():
            I.apply_multiline(LATE3F)
    elif a.rules and a.late2:
        late2_rules()
    elif a.apply and a.late2:
        if LATE2F.exists():
            I.apply_multiline(LATE2F)
    elif a.rules and a.late:
        late_rules()
    elif a.rules:
        rules()
    elif a.apply and a.late:
        if LATEF.exists():
            I.apply_multiline(LATEF)
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
