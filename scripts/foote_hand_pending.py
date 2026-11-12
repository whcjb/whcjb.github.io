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
    a = ap.parse_args()
    if a.rules:
        rules()
    elif a.apply and RULES.exists():
        I.apply_multiline(RULES)


if __name__ == '__main__':
    main()
