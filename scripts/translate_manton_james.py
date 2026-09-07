#!/usr/bin/env python3
"""translate_manton_james.py —— 曼顿《雅各书注释》英文 raw → 中文 raw。

复用 translate_filibi 的 call_claude / md5 缓存；CLI 调用统一走
claude_usage.call_cli，**自动带 CLI_TRIM_FLAGS**
（--safe-mode / --strict-mcp-config / --disallowedTools "*" / --system-prompt），
不发工具定义、MCP、CLAUDE.md、skills、hooks —— 29,142 → 287 token/次。
绝不要在本脚本里自己拼 subprocess 调 claude，那样会把整套上下文又带回去。

输入  manton_raw/james/{dedicatory,advertisement,preface,1..5}.md
缓存  manton_raw/james/zh_cache/<md5>.txt      ← 必须保留，重跑成本极高
输出  manton_raw/james/zh_chapters/<name>.md   ← 翻完 chmod 444

只翻正文。以下原样保留，不进模型：
  <!-- PAGE N -->        页码标记
  <!--VERSE N-->         释经单元标记（publish 靠它插经节锚点）
  [^fN] 行内脚注引用      （脚注**定义**的正文部分要翻）
  <em> </em> 等 HTML 标签

用法（项目根目录）：
    python3 -u scripts/translate_manton_james.py --dry-run
    python3 -u scripts/translate_manton_james.py --section 1 --resume
    python3 -u scripts/translate_manton_james.py --all --resume
"""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf   # noqa: E402  复用 CLI/缓存

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'manton_raw' / 'james'
OUT_DIR = RAW / 'zh_chapters'
CACHE = RAW / 'zh_cache'

SECTIONS = ['dedicatory', 'advertisement', 'preface', '1', '2', '3', '4', '5']

SYSTEM = (
    "你是一位精通清教神学与改革宗传统的中文译者，正在翻译托马斯·曼顿"
    "（Thomas Manton, 1620-1677）《雅各书注释》（1657）。\n"
    "此书底本是他在伦敦近郊每周所讲的讲章，逐节讲解，走清教徒"
    "「立教义—陈理由—落应用」的平实讲道法。译文要庄重、恳切、可诵读，"
    "既是解经也是讲道，不可译成干巴巴的学术论文，也不可油滑口语。\n"
    "严格规则：\n"
    "1. 只输出译文，不加任何说明，不重复原文，不要前言、解释或译注\n"
    "2. 保留所有 HTML 标签不变：<em> </em> <p> <strong> 等，位置对应原文\n"
    "3. 保留所有脚注引用标记不变：[^f24] [^f151] 等，位置对应原文\n"
    "4. 保留所有 Markdown 标记与 HTML 注释不变\n"
    "5. 希腊文/希伯来文/拉丁文一律保留原文，其后用圆括号附中文译义，"
    "如 δοῦλος（仆人）、Sola Fide（唯独因信）；整句拉丁引文保留原文，括注中文大意\n"
    "6. 圣经书卷名、人名一律用和合本标准译名：James→雅各书，Paul→保罗，"
    "Abraham→亚伯拉罕，Rahab→喇合，Job→约伯，Elias→以利亚，"
    "Moses→摩西，Christ→基督，the Lord→主\n"
    "7. 章节引用格式：雅各书 2:14，罗马书 3:28（书卷名 章:节）。"
    "原文的罗马数字章号（Gal. iii. 28）要转成阿拉伯数字（加拉太书 3:28）\n"
    "8. 神学术语务必精确、互不撞词：\n"
    "   justification→称义　justify→称……为义　righteousness→义　"
    "   imputed righteousness→归算的义\n"
    "   faith→信心　works→行为　grace→恩典　mercy→怜悯　\n"
    "   sanctification→成圣　regeneration→重生　repentance→悔改\n"
    "   temptation→试探（引诱犯罪）／试炼（患难考验），按上下文分用，勿混\n"
    "   trial→试炼　affliction→苦难　patience→忍耐　\n"
    "   profession→口称信主／表白　hypocrite→假冒为善的人\n"
    "   the law of liberty→使人自由的律法　respect of persons→按外貌待人\n"
    "9. 「Obs.」是曼顿标注「观察／教义」的体例词，译作「观察」并保留序号，"
    "如 Obs. 1. → 观察一。「Ver. 2.」译作「第2节」。"
    "「Object.」→「诘难」，「Solut.」→「解答」，「Use 1.」→「应用一」\n"
    "10. 教父/古典作者姓名首次出现保留原文并括注中文音译，"
    "如 Chrysostom（屈梭多模）、Augustine（奥古斯丁）、Jerome（耶柔米）\n"
    "11. 曼顿常引经文而不标出处，引文按和合本语感译，不要自造译法\n"
    "12. 原文若有未闭合的引号（底本转写缺陷），照原样保留，不要自行补全"
)

# 原样保留、不进模型的整块。
# `---` 是脚注区分隔线，务必列进来：送进模型会得到「您似乎没有附上需要翻译的
# 英文段落」这类**对话式回复**，直接写进正文（踩过，advertisement 块3）。
# 凡是「没有实义文字」的块都不该进模型。
SKIP_BLOCK_RE = re.compile(
    r'^(?:<!-- PAGE \d+ -->|<!--VERSE [^>]*-->|-{3,}|\*{3,}|_{3,})$')

# 模型没在翻译、而是在跟你说话的迹象。命中即判失败重试。
CHATTY_RE = re.compile(
    r'(您似乎|你似乎|请把原文|请提供|没有附上|未提供|无法翻译|'
    r'as an ai|i (?:cannot|can\'t|don\'t see)|please provide)', re.I)


def structural_diff(en: str, zh: str):
    """返回结构性差异说明；空字符串表示通过。

    只查**可机验**的硬结构：脚注标签集合、<em> 数量、HTML 注释。
    这三样错了下游一定出问题，且模型确实会丢（advertisement 块1 丢了 <em>）。
    """
    problems = []
    en_fn = sorted(re.findall(r'\[\^f\d+\]', en))
    zh_fn = sorted(re.findall(r'\[\^f\d+\]', zh))
    if en_fn != zh_fn:
        problems.append(f'脚注标记不符 {en_fn} → {zh_fn}')
    if en.count('<em>') != zh.count('<em>') or en.count('</em>') != zh.count('</em>'):
        problems.append(f'<em> 数量不符 {en.count("<em>")} → {zh.count("<em>")}')
    en_c = re.findall(r'<!--.*?-->', en, re.S)
    zh_c = re.findall(r'<!--.*?-->', zh, re.S)
    if en_c != zh_c:
        problems.append(f'HTML 注释不符 {en_c} → {zh_c}')
    if CHATTY_RE.search(zh):
        problems.append('模型在对话而非翻译')
    if re.search(r'[A-Za-z]', en) and not re.search(r'[一-鿿]', zh) and len(en) > 40:
        problems.append('译文无汉字')
    return '；'.join(problems)
HEADING_RE = re.compile(r'^(#{1,6})\s+(.*)$', re.S)
FNDEF_RE = re.compile(r'^(\[\^f\d+\]:\s*)(.*)$', re.S)
CENTER_RE = re.compile(r'^(<p style="text-align:center" markdown="1">)(.*?)(</p>)$', re.S)


BAD_LOG = RAW / 'zh_translate_issues.log'


def translate_one(text: str, resume: bool, label: str = '') -> str:
    """带缓存 + 结构校验的单段翻译。key = 段落 md5。

    校验不过就重译一次（把问题点明写进 prompt）。仍不过则**保留译文但记账**到
    zh_translate_issues.log —— 不静默吞掉，也不因一段卡死整章。
    缓存命中的旧译文同样过校验：早先跑出来的坏译文（丢 <em>、对话式回复）
    会因此自动重译，不必手工清缓存。
    """
    key = tf.md5key('MANTON_JAS::' + text)
    f = CACHE / f'{key}.txt'
    if resume and f.exists() and f.stat().st_size > 0:
        cached = f.read_text(encoding='utf-8')
        if not structural_diff(text, cached):
            return cached
        print(f'    [cache-reject] {label}: {structural_diff(text, cached)[:90]}',
              flush=True)

    base = ("把下面这段托马斯·曼顿《雅各书注释》的英文译成简体中文。"
            "整段通读后再译，保证上下文连贯；只输出译文。\n\n")
    out = re.sub(r'<<<[^>]*>>>', '', tf.call_claude(base + text, label=label)).strip()

    diff = structural_diff(text, out)
    if diff:
        print(f'    [retry-struct] {label}: {diff[:90]}', flush=True)
        fix = (f"上一版译文有结构问题：{diff}。\n"
               "重译下面这段。**必须逐一保留**原文中的 <em></em> 标签、"
               "[^fN] 脚注标记、<!-- --> 注释，位置与原文对应；只输出译文。\n\n")
        out2 = re.sub(r'<<<[^>]*>>>', '',
                      tf.call_claude(fix + text, label=label + '·retry')).strip()
        if not structural_diff(text, out2):
            out = out2
        else:
            out = out2 or out
            BAD_LOG.parent.mkdir(parents=True, exist_ok=True)
            with BAD_LOG.open('a', encoding='utf-8') as fh:
                fh.write(f'[{label}] {structural_diff(text, out)}\n'
                         f'  EN: {text[:160]!r}\n  ZH: {out[:160]!r}\n')

    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_text(out, encoding='utf-8')
    return out


def split_units(raw: str):
    """raw md → [(kind, payload)]。kind='keep' 原样；'text' 需翻译。"""
    units = []
    for block in raw.split('\n\n'):
        b = block.strip()
        if not b:
            continue
        if SKIP_BLOCK_RE.match(b):
            units.append(('keep', b))
            continue
        units.append(('text', b))
    return units


def translate_block(b: str, resume: bool, label: str) -> str:
    """按块型拆出真正要翻的文字，翻完套回原结构。"""
    m = HEADING_RE.match(b)
    if m:
        return f'{m.group(1)} {translate_one(m.group(2), resume, label)}'
    m = FNDEF_RE.match(b)
    if m:
        return m.group(1) + translate_one(m.group(2), resume, label)
    m = CENTER_RE.match(b)
    if m:
        return m.group(1) + translate_one(m.group(2), resume, label) + m.group(3)
    return translate_one(b, resume, label)


def run_section(name: str, resume: bool, dry: bool) -> None:
    src = RAW / f'{name}.md'
    if not src.exists():
        sys.exit(f'找不到 {src}')
    units = split_units(src.read_text(encoding='utf-8'))
    todo = [u for k, u in units if k == 'text']
    hit = sum(1 for t in todo
              if (CACHE / f'{tf.md5key("MANTON_JAS::" + _payload(t))}.txt').exists())
    print(f'[{name}] 共 {len(units)} 块，其中需翻译 {len(todo)} 段，'
          f'已缓存 {hit}，待调用 {len(todo) - hit}', flush=True)
    if dry:
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = OUT_DIR / f'{name}.md'
    # 翻译产物受 chmod 444 保护，重跑前先解锁（anti-pattern M）
    if dst.exists():
        os.chmod(dst, 0o644)

    out, n = [], 0
    for kind, payload in units:
        if kind == 'keep':
            out.append(payload)
            continue
        n += 1
        out.append(translate_block(payload, resume, label=f'{name}#{n}'))
        if n % 20 == 0:
            print(f'  [{name}] {n}/{len(todo)} 段', flush=True)

    dst.write_text('\n\n'.join(out) + '\n', encoding='utf-8')
    os.chmod(dst, 0o444)          # 强保留
    print(f'✓ 写入 {dst}（{dst.stat().st_size:,} bytes，已 chmod 444）', flush=True)


def _payload(b: str) -> str:
    """与 translate_block 一致地取出真正送模型的那段文字，用于缓存命中统计。"""
    for rx, g in ((HEADING_RE, 2), (FNDEF_RE, 2), (CENTER_RE, 2)):
        m = rx.match(b)
        if m:
            return m.group(g)
    return b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--section', help='dedicatory/advertisement/preface/1..5')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--resume', action='store_true', help='命中缓存则不重调模型')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    tf.CACHE_DIR = CACHE
    tf.SYSTEM = SYSTEM
    CACHE.mkdir(parents=True, exist_ok=True)

    targets = [a.section] if a.section else SECTIONS
    for name in targets:
        try:
            run_section(name, a.resume, a.dry_run)
        except tf.SessionLimitError as e:
            # 额度用尽时重试毫无意义，还照样计费。逐段缓存已落盘，
            # 额度恢复后 --resume 从缓存续跑即可。退出码 42 = 整批中止信号。
            print(f'\n✗ 会话额度用尽，于 [{name}] 中止：{str(e)[:160]}\n'
                  f'  已翻译的段落都在 {CACHE}，额度恢复后加 --resume 续跑。',
                  flush=True)
            sys.exit(42)


if __name__ == '__main__':
    main()
