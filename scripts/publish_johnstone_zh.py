#!/usr/bin/env python3
"""johnstone_raw/philippians/zh_chapters/*.md → johnstone/philippians/zh/*.md（中文版）。

    python3 scripts/publish_johnstone_zh.py          # 发布全部已翻译的
    python3 scripts/publish_johnstone_zh.py 1 3      # 只发布指定篇

与英文版共用 johnstone-chapter / johnstone-book 两个 layout，靠 `zh: true` 切换
（亚历山大那边的既定写法）。「每本书独立样式」说的是不与别家共用，不是中英文
各造一份。

上下篇导航**只在已翻译的篇之间串**：翻译逐篇推进，把导航指到还没译的篇等于
送读者去 404。每次重跑按当前已译清单重新串。

页面 date 取 `zh_meta.json` 里**该篇实际译完的时刻**，不是发布这一刻（一次
发布 N 篇会写出 N 个相同时间戳，等于没有信息）。取不到才沿用已发布文件的原值，
再取不到才用当前时间。

讲章的经文出处（英文页的 subtitle `Philippians i. 1, 2`）在这里转成和合本格式
`腓立比书 1:1-2`：中文页挂了经文弹层，它认的是中文书卷名。

英文页的 `zh_url` 由 publish_johnstone_en.py 按 zh 目录是否存在自行补上，
本脚本跑完顺手调它一次，两边幂等。
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'johnstone_raw/philippians/zh_chapters'
META = ROOT / 'johnstone_raw/philippians/zh_meta.json'
EN = ROOT / 'johnstone/philippians'
OUT = EN / 'zh'

BOOK_NAME_ZH = '约翰斯通《腓立比书讲章》'
FM_DATE = re.compile(r'^date:\s*(.+)$', re.M)
FM_SUB = re.compile(r'^subtitle:\s*"(.*)"$', re.M)
FM_TITLE = re.compile(r'^title:\s*"(.*)"$', re.M)
TITLE_LINE = re.compile(r'^<!-- title: (.*?) -->\n+', re.S)

ORDER = (['preface', 'introduction'] + [str(i) for i in range(1, 31)]
         + ['translation', 'notes-1', 'notes-2', 'notes-3', 'notes-4', 'polycarp'])

LABELS = {
    'preface': '序言',
    'introduction': '导论',
    'translation': '腓立比书修订译文',
    'notes-1': '希腊文经文注释 · 第一章',
    'notes-2': '希腊文经文注释 · 第二章',
    'notes-3': '希腊文经文注释 · 第三章',
    'notes-4': '希腊文经文注释 · 第四章',
    'polycarp': '附录 · 坡旅甲致腓立比人书',
}
CN_NUM = '一二三四五六七八九十'
ROMAN = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4}


def cn(n: int) -> str:
    if n <= 10:
        return CN_NUM[n - 1]
    if n < 20:
        return '十' + (CN_NUM[n - 11] if n > 10 else '')
    t, u = divmod(n, 10)
    return CN_NUM[t - 1] + '十' + (CN_NUM[u - 1] if u else '')


def zh_ref(en: str):
    """`Philippians i. 1, 2` → `腓立比书 1:1-2`；`i. 21, 1st clause` → `1:21 上半节`。"""
    m = re.match(r'Philippians ([ivx]+)\. (.+)$', en or '')
    if not m:
        return None
    ch, rest = ROMAN[m.group(1)], m.group(2).strip()
    half = ''
    mm = re.search(r',\s*(1st|2d|2nd) clause$', rest)
    if mm:
        half = ' 上半节' if mm.group(1) == '1st' else ' 下半节'
        rest = rest[:mm.start()]
    nums = re.findall(r'\d+', rest)
    if not nums:
        return None
    vs = nums[0] if len(nums) == 1 else f'{nums[0]}-{nums[-1]}'
    return f'腓立比书 {ch}:{vs}{half}'


def en_fm(sec: str) -> str:
    p = EN / f'{sec}.md'
    return p.read_text(encoding='utf-8').split('\n---\n', 1)[0] if p.exists() else ''


def label(sec: str, title_zh: str) -> str:
    if sec.isdigit():
        name = re.sub(r'^.*?[·：:]\s*', '', title_zh) if re.search(r'[·：:]', title_zh) else title_zh
        name = re.sub(r'^第[一二三四五六七八九十\d]+讲\s*', '', name).strip() or title_zh
        return f'第{cn(int(sec))}讲 · {name}'
    return LABELS.get(sec, title_zh)


# 「第 1 章 13 节」——作者说 chap. i. 13 指的就是腓立比书本身，译文照规矩写成
# 「第 N 章 M 节」，经文弹层不认（它要书卷名）。发布时改写成和合本格式。
# 两道闸：前面紧挨书卷名的不动（「罗马书第 8 章」是别的书），章号只认 1–4
# （腓立比书只有四章）。
REL_REF = re.compile(r'(?<![书记传篇言歌音录])第\s?([1-4])\s?章\s?(\d{1,2})'
                     r'(?:\s?[-–至]\s?(\d{1,2}))?\s?节')


# 书末两块原样保留、没送翻译的英文（translate_johnstone.IMPRINT）：卷终语与印刷所落款。
IMPRINT_ZH = [
    ('\nTHE END.\n', '\n（全书完）\n'),
    ('<span class="jh-verse">MURRAY AND GIBB, EDINBURGH,<br>PRINTERS TO HER MAJESTY’S STATIONERY OFFICE.</span>',
     '<span class="jh-verse">爱丁堡 Murray and Gibb 印行<br>（女王陛下文书局印刷商）</span>'),
]


def absolutize_refs(body: str) -> str:
    def sub(m):
        vs = m.group(2) + (f'-{m.group(3)}' if m.group(3) else '')
        return f'腓立比书 {m.group(1)}:{vs}'
    return REL_REF.sub(sub, body)


# 音译专名后的原名括注「（Brutus）」→ 小一号灰字方括号。只认括号里全是西文
# 字母的（人名、地名）；夹了中文的（「Alford，见于他的一部著作」）、希腊文、
# 拉丁词释义「fides（信心）」都不动。zh_chapters 仍存圆括号，只在发布时换。
# 2026-10-19 用户：「用圆括号有点丑陋，改成方括号并且字体小一号，灰色字体」。
ORIG_NAME = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ .,'’&-]*)）")


# 「（presbyter，即「长老」一词的希腊文）」这种「原词，即……」的原文括注也同样处理，
# 连同后面的中文说明一起放进灰字方括号（2026-10-22 用户指定）。
ORIG_GLOSS = re.compile(r"（([A-Za-zÀ-ÿÆæŒœ][A-Za-zÀ-ÿÆæŒœ'’-]*，即[^（）]*)）")


# 纯经文出处括注「（彼得前书 5:1、2）」「（见提摩太前书 6:18，并参哥林多前书 1:5）」
# 同样换成灰字方括号（2026-10-22 用户指定）。括号里夹了别的话（「见该节第一分句的
# 讲解」「中 εἴ πως 便是……」「自夸，」）的不动。
_REF = r"(?:[\u4e00-\u9fff]{2,7} )?\d+:\d[\d:\-、, ]*"
_PRE = r"(?:另参|并参|见|参|如)?"
# 首个出处必须带书卷名：裸「（3:20）」是弹层按「本卷」识别的格式、靠圆括号认，
# 换成方括号弹层就认不出了，留原样。
_REF1 = r"[\u4e00-\u9fff]{2,7} \d+:\d[\d:\-、, ]*"
SCRIPTURE_PAREN = re.compile(rf"（({_PRE}{_REF1}(?:[；，]{_PRE}{_REF})*)）")


def orig_names(body: str) -> str:
    body = SCRIPTURE_PAREN.sub(r'<span class="jh-orig jh-orig-wrap">[\1]</span>', body)
    body = ORIG_GLOSS.sub(r'<span class="jh-orig jh-orig-wrap">[\1]</span>', body)
    return ORIG_NAME.sub(r'<span class="jh-orig">[\1]</span>', body)


def existing_date(path: Path):
    if not path.exists():
        return None
    m = FM_DATE.search(path.read_text(encoding='utf-8')[:600])
    return m.group(1).strip() if m else None


def main(only=None):
    if not RAW.exists():
        sys.exit(f'找不到 {RAW}，先跑 translate_johnstone.py')
    done = {p.stem for p in RAW.glob('*.md')}
    names = [s for s in ORDER if s in done]
    if not names:
        sys.exit('zh_chapters 里没有任何已翻译的篇')

    now = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True,
                         text=True, check=True).stdout.strip()
    meta = json.loads(META.read_text(encoding='utf-8')) if META.exists() else {}
    OUT.mkdir(parents=True, exist_ok=True)

    info = {}
    for sec in names:
        raw = (RAW / f'{sec}.md').read_text(encoding='utf-8')
        m = TITLE_LINE.match(raw)
        title_zh = m.group(1).strip() if m else sec
        body = raw[m.end():] if m else raw
        for a, b in IMPRINT_ZH:
            body = body.replace(a, b)
        sub = FM_SUB.search(en_fm(sec))
        info[sec] = dict(label=label(sec, title_zh), body=orig_names(absolutize_refs(body.strip())),
                         ref=zh_ref(sub.group(1)) if sub else None)

    written = kept = 0
    for k, sec in enumerate(names):
        if only and sec not in only:
            continue
        pg = info[sec]
        path = OUT / f'{sec}.md'
        date = meta.get(sec) or existing_date(path)
        kept += date is not None
        fm = ['---', 'layout: johnstone-chapter', 'book_id: philippians',
              f'book_name: "{BOOK_NAME_ZH}"', f'title: "{pg["label"]}"']
        if pg['ref']:
            fm.append(f'subtitle: "{pg["ref"]}"')
        fm.append(f'date: {date or now}')
        if k > 0:
            fm += [f'prev_url: "/johnstone/philippians/zh/{names[k - 1]}/"',
                   f'prev_label: "{info[names[k - 1]]["label"]}"']
        if k + 1 < len(names):
            fm += [f'next_url: "/johnstone/philippians/zh/{names[k + 1]}/"',
                   f'next_label: "{info[names[k + 1]]["label"]}"']
        # 章节页不放英文入口：英文版只从首页进（用户 2026-10-16 定）
        fm += ['zh: true', '---']
        path.write_text('\n'.join(fm) + '\n\n' + pg['body'] + '\n', encoding='utf-8')
        written += 1

    # 中文目录就是这本书的首页 /johnstone/philippians/；英文目录在 /en/。
    (EN / 'index.html').write_text(build_index(names, info), encoding='utf-8')
    old_idx = OUT / 'index.html'
    if old_idx.exists():
        old_idx.unlink()
    print(f'发布中文 {written} 篇（已译共 {len(names)}/{len(ORDER)}），'
          f'date 取自译完时刻 {kept} 篇 → {OUT}')


GROUPS = [
    ('卷首', ['preface', 'introduction']),
    ('讲章 · 三十篇', [str(i) for i in range(1, 31)]),
    ('修订译文与希腊文注释', ['translation', 'notes-1', 'notes-2', 'notes-3', 'notes-4']),
    ('附录', ['polycarp']),
]


def build_index(names, info):
    out = ['---', 'layout: johnstone-book', 'book_id: philippians',
           f'book_name: "{BOOK_NAME_ZH}"',
           'author: "罗伯特·约翰斯通（Robert Johnstone），1875"',
           'edition: "《腓立比书讲章：释经与实践》· 爱丁堡 William Oliphant，1875"',
           f'title: "{BOOK_NAME_ZH}"', 'en_url: "/johnstone/philippians/en/"',
           'zh: true', '---', '']
    for group, slugs in GROUPS:
        slugs = [s for s in slugs if s in names]
        if not slugs:
            continue
        out.append(f'<h2 class="jh-group">{group} <small>（{len(slugs)} 篇）</small></h2>')
        out.append('<ul class="jh-toc">')
        for s in slugs:
            p = info[s]
            if s.isdigit():
                no, name = p['label'].split(' · ', 1)
                inner = f'<span class="jh-no">{no}</span>{name}'
            else:
                inner = p['label']
            ref = f'<br><span class="jh-ref">{p["ref"]}</span>' if p['ref'] else ''
            out.append(f'  <li><a href="{{{{ site.baseurl }}}}/johnstone/philippians/zh/{s}/">'
                       f'{inner}{ref}</a></li>')
        out.append('</ul>')
    out.append(f'<p class="jh-note">已译 {len(names)} / {len(ORDER)} 篇，逐篇上线。'
               '译文据英文底本（1875 年爱丁堡初版，多伦多大学藏本重新 OCR 校订）译出，'
               '经文引用照和合本；作者自己的直译与修订译文按其英文字面译出。</p>')
    return '\n'.join(out) + '\n'


if __name__ == '__main__':
    main(set(sys.argv[1:]) or None)
    # 英文页回填 zh_url（英文发布脚本按 zh 目录是否存在自行决定，幂等）
    subprocess.run([sys.executable, str(ROOT / 'scripts/publish_johnstone_en.py'), '--apply'],
                   cwd=ROOT, capture_output=True)
