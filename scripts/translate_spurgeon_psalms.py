#!/usr/bin/env python3
"""translate_spurgeon_psalms.py —— 司布真《大卫的宝库》(The Treasury of David, 1869–1885) 英文页 → 中文 raw。

引擎整套借 translate_alexander_matthew（质检闸、<译文> 标签、占位符遮盖、restore_greek、斜体对位、
严重问题不入缓存、--jobs、--max-minutes、⛔ 即停）；本脚本只换输入输出、系统提示与分块。
CLI 调用走 translate_filibi.call_claude → claude_usage.call_cli，自动带
--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt（不发工具定义、MCP、CLAUDE.md、skills）。

输入  spurgeon/psalms/<N>.md、preface.md、119/<a-b>.md（已发布的英文页，一块一段）
缓存  spurgeon_raw/psalms/zh_cache/<md5>.txt   ← 必须保留
输出  spurgeon_raw/psalms/zh_chapters/<页>.md   ← 翻完 chmod 444（发布脚本另写）
时刻  spurgeon_raw/psalms/zh_meta.json

  - `<h2 class="td-sec">` 四类节标题按表译，不送模型；
  - 其余每块（释经、解经札记、乡村传道人提示、题解）送模型，标签遮成占位符。

用法（项目根目录）：
    python3 -u scripts/translate_spurgeon_psalms.py --dry-run --all
    python3 -u scripts/translate_spurgeon_psalms.py --section 23 --resume --no-publish
    python3 -u scripts/translate_spurgeon_psalms.py --all --resume --jobs 6 --max-minutes 6 --no-publish
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_alexander_matthew as A   # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'spurgeon' / 'psalms'
RAW = ROOT / 'spurgeon_raw' / 'psalms'

A.SRC = SRC
A.RAW = RAW
A.OUT_DIR = RAW / 'zh_chapters'
A.CACHE = RAW / 'zh_cache'
A.BAD_LOG = RAW / 'zh_translate_issues.log'
A.ITALIC_LOG = RAW / 'zh_italic_notes.log'
A.META = RAW / 'zh_meta.json'
A.ACCEPTED = RAW / 'zh_accepted.txt'
A.KEY_NS = 'SPURGEON_PSALMS::'
A.ANNOTATE = {}

A.SYSTEM = (
    "你是改革宗神学文献的专业译者，正在翻译司布真（C. H. Spurgeon, 1834-1892，伦敦大都会会幕牧师）"
    "的《大卫的宝库》（The Treasury of David，1869–1885，七卷诗篇注释）。只输出译文，不要任何说明。\n"
    "\n"
    "★优先级（冲突时一律按此让步）：①意思正确 ②中文读者读得懂 ③文风。为求典雅而让读者读不懂，是错译不是好译。\n"
    "\n"
    "【本书体裁】每篇分几部分：题解；「释经」（司布真本人逐节讲解，讲道口吻，比喻多、句子短、常直接呼告，"
    "译文要保住这股恳切亲切的口气）；「解经札记与警句」（摘录清教徒、教父、改教家等数百位作者，文风各异，"
    "十七世纪的就译得庄重些，不要一律抹成司布真腔）；「给乡村传道人的提示」（讲章提纲，简短，照条目译）。\n"
    "\n"
    "【经文】段首或句中引的诗篇与其他经文（多在 *\"…\"* 里），一律照和合本原文，不要自己另译；"
    "原作者另有译法（如 thus it may be rendered…）时，按他的意思译出，不硬套和合本。"
    "书卷名、人名、地名照和合本。\n"
    "【诗句】引的英文诗歌、赞美诗译成通顺的中文，可不押韵，但分行照原样（<br> 占位符不得丢）。\n"
    "【作者署名】札记段末括号里的作者名与书名，人名音译后括注英文原名（加尔文、路德、奥古斯丁这类定译不注），"
    "书名译出并保留原文书名。\n"
    "【必须原样保留】⟦N⟧ 占位符（个数与先后都要对上）；*斜体* 星号；希腊文、希伯来文逐字照抄，"
    "原文里没有的希腊文、希伯来文一个字母也不许添。\n"
    "· 引文后的 &c. 译成省略号……。\n"
    "· 引号一律用弯引号“”（嵌套时内层用‘’）。\n"
)

_N = {'FIRST': 1, 'SECOND': 2, 'THIRD': 3, 'FOURTH': 4, 'FIFTH': 5, 'SIXTH': 6, 'SEVENTH': 7, 'EIGHTH': 8,
      'NINTH': 9, 'TENTH': 10, 'ELEVENTH': 11, 'TWELFTH': 12, 'THIRTEENTH': 13, 'FOURTEENTH': 14,
      'FIFTEENTH': 15, 'SIXTEENTH': 16, 'SEVENTEENTH': 17, 'EIGHTEENTH': 18, 'NINETEENTH': 19}
SEC = {'EXPOSITION': '释经', 'EXPLANATORY NOTES AND QUAINT SAYINGS': '解经札记与警句',
       'HINTS TO THE VILLAGE PREACHER': '给乡村传道人的提示',
       'NOTES RELATING TO THE PSALM AS A WHOLE': '关于全篇的札记'}
RE_SEC = re.compile(r'^(<h2 class="td-sec"[^>]*>)([^<]*)(</h2>)$')


def sec_zh(slug: str, title: str) -> str:
    t = title.strip()
    if t in SEC:
        return SEC[t]
    if re.match(r'^WORKS? UPON THE .*PSALM$', t):
        n = slug.split('/')[0]
        return f'论诗篇第 {n} 篇的著作' if n.isdigit() else '相关著作'
    return ''


def body_of(slug: str) -> str:
    t = (SRC / f'{slug}.md').read_text(encoding='utf-8')
    t = t.split('\n---\n', 1)[1].strip() if t.startswith('---\n') else t.strip()
    return re.sub(r'<em>([^<>]*)</em>', r'*\1*', t)            # 斜体转星号，模型按星号对位


def units_of(slug: str):
    out = []
    for block in body_of(slug).split('\n\n'):
        b = block.strip()
        if not b:
            continue
        m = RE_SEC.match(b)
        if m and sec_zh(slug, m.group(2)):
            out.append(('keep', m.group(1) + sec_zh(slug, m.group(2)) + m.group(3)))
        else:
            out.append(('keep' if A.is_keep_block(b) else 'text', b))
    return out


def all_slugs():
    nums = [str(n) for n in range(1, 151)]
    parts = sorted((p.stem for p in (SRC / '119').glob('*.md')), key=lambda s: int(s.split('-')[0]))
    i = nums.index('119') + 1
    return ['preface'] + nums[:i] + [f'119/{p}' for p in parts] + nums[i:]


A.body_of = body_of
A.units_of = units_of
A.all_slugs = all_slugs


def _no_autopublish(slug):
    print(f'    [publish] {slug}：中文发布脚本未接，暂不发布', flush=True)


A.autopublish = _no_autopublish

if __name__ == '__main__':
    A.main()
