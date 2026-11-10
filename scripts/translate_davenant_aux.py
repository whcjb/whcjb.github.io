#!/usr/bin/env python3
"""达文南特《歌罗西书》辅助页中译：卷一补遗（addenda）与原书索引（indexes/*）→ <页>/zh/index.md。

2026-11-10 用户令补齐各书辅助页。正文与两部附卷走 translate_davenant.py；这几页结构不同（补遗是零散的注补，
索引一条一行），单写此脚本：
  - 索引条目（<p class="dv-idx">…</p>）每 SIZE 条打包一次调用，按 [编号] 逐行对应；补遗按段落一段一次；
  - 每条/每段过 translate_davenant.check_block（达文南特那套闸），不合格的单条重译一次，仍不合格即停（不发布）；
  - 缓存 davenant_raw/colossians/zh_cache_aux/<md5>.txt（命名空间 DAVENANT_AUX::，不碰正文缓存）。
CLI 走 translate_filibi.call_claude（--safe-mode --strict-mcp-config --disallowedTools '*' + --system-prompt）。

英文底本还有 OCR 乱码的页（传略索引、目次、问题索引的引导点行，经文索引大半行）先不译——先看原书页图修干净。

用法：python3 -u scripts/translate_davenant_aux.py --page addenda --page indexes/general [--dry-run]
发布：publish_davenant_appx.py / publish_davenant_index.py 在中文页存在时自动给英文页挂 zh_url。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import translate_filibi as tf     # noqa: E402
import translate_davenant as D    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PUB = ROOT / 'davenant' / 'colossians'
CACHE = ROOT / 'davenant_raw' / 'colossians' / 'zh_cache_aux'
NS = 'DAVENANT_AUX::'
SIZE = 40
TITLE_ZH = {'addenda': '卷一补遗', 'indexes/biographical': '传略索引', 'indexes/contents': '《论基督之死》目次',
            'indexes/errata': '勘误', 'indexes/general': '总索引', 'indexes/notes': '注中人事索引',
            'indexes/questions': '问题索引', 'indexes/scripture': '经文索引'}
RE_TAG = re.compile(r'<[^<>]{1,300}>')
RE_PH = re.compile(r'⟦(\d+)⟧')
RE_IDX = re.compile(r'^(<p class="dv-idx">)(.*)(</p>)$')

AUX_SYSTEM = D.SYSTEM + (
    "\n补充（书末索引与补遗）：索引条目译成简洁的中文名词短语，人名首次出现括注原名；"
    "卷次 I. / II. 与页码数字照抄（I. 212 → 卷一 212；II. 90, 211 → 卷二 90、211）；"
    "see / see also → 见 / 另见；ibid. → 同上。")


def mask(t):
    tags = []

    def put(m):
        tags.append(m.group(0))
        return f'⟦{len(tags)}⟧'
    return RE_TAG.sub(put, t), tags


def unmask(t, tags):
    return RE_PH.sub(lambda m: tags[int(m.group(1)) - 1] if 0 < int(m.group(1)) <= len(tags) else m.group(0), t)


def cache_get(t):
    f = CACHE / f'{tf.md5key(NS + t)}.txt'
    return f.read_text(encoding='utf-8') if f.exists() else None


def cache_put(t, zh):
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / f'{tf.md5key(NS + t)}.txt').write_text(zh, encoding='utf-8')


def ok(en_masked, zh):
    if len(RE_PH.findall(en_masked)) != len(RE_PH.findall(zh)):
        return '占位符不符'
    return D.check_block(en_masked, zh)


ONE_RULES = (
    "把下面这段（达文南特《歌罗西书注释》1831 年英译本卷一的「补遗」或书末索引）译成简体中文。规则：\n"
    "1. 人名、地名、书名一律先写中文译名，紧跟全角括号注原名：克雷格（Craig）、居普良（Cyprian）、"
    "鲍尔（Bower）《教皇史》（History of the Popes）；同一人前后用同一译名，罗马主教 Stephen 译「斯德望」\n"
    "2. 列举的序数前后一致：First / Second / Third → 第一 / 第二 / 第三\n"
    "3. 补遗小标题「For Note *, p. 14.」意为「第 14 页注 * 之补遗」，「Note at the end of … p. 16」意为「第 16 页……之注」\n"
    "4. ⟦N⟧ 占位符原样保留，`*` 斜体成对照留；不加任何说明\n"
    "5. 译文放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃\n")


def one(t, label, ctx=''):
    """单段翻译（补遗段落、批量里不合格的条目、小标题）。重译一次仍不合格 → 抛错停下。"""
    c = cache_get(t)
    if c is not None and not ok(t, c):
        return c
    base = ONE_RULES + (f"\n【前一段英文，只供理解上下文，不要翻译、不要输出】\n{ctx}\n" if ctx else '') + "\n【要翻译的段落】\n"
    for n in range(2):
        raw = tf.call_claude(base + t, timeout=900, label=f'{label}' + (f'·retry{n}' if n else ''))
        m = re.findall(r'<译文>(.*?)</译文>', raw, re.S)
        zh = (m[-1] if m else raw).strip()
        why = ok(t, zh)
        if not why:
            cache_put(t, zh)
            return zh
        print(f'    [retry] {label}: {why}', flush=True)
    raise SystemExit(f'⛔ {label} 重译后仍不合格：{why}')


def batch(items, label):
    todo = [t for t in dict.fromkeys(items) if cache_get(t) is None or ok(t, cache_get(t))]
    for bi in range(0, len(todo), SIZE):
        chunk = todo[bi:bi + SIZE]
        body = '\n'.join(f'[{i}] {t}' for i, t in enumerate(chunk, 1))
        prompt = ("下面是十七世纪神学著作英译本（1831）书末索引的若干条目，每行以 [编号] 开头。逐行译成简体中文："
                  "**行数、编号一一对应，不并行、不拆行、不漏行**；每行保留行首 [编号]；⟦N⟧ 占位符原样保留。"
                  "人名、书名、术语一律先写中文，紧跟全角括号注原名（鲍尔（Bower）、换称法（Antonomasia））；"
                  "教派名照本站定译：Arians 阿里乌派、Pelagians 柏拉糾派、Arminians 阿民念派、Socinians 苏西尼派、"
                  "Donatists 多纳徒派、Jesuits 耶稣会士；卷次 I. / II. 写作卷一 / 卷二，页码照抄。"
                  "译文放在 <译文> 与 </译文> 之间，标签外的文字一律丢弃。\n\n" + body)
        raw = tf.call_claude(prompt, timeout=900, label=f'{label}·batch{bi // SIZE + 1}')
        m = re.findall(r'<译文>(.*?)</译文>', raw, re.S)
        got = {int(x.group(1)): x.group(2).strip() for x in
               (re.match(r'^\s*\[(\d+)\]\s?(.*)$', ln) for ln in (m[-1] if m else raw).strip().split('\n')) if x}
        for i, t in enumerate(chunk, 1):
            zh = got.get(i, '')
            if zh and not ok(t, zh):
                cache_put(t, zh)
        print(f'  [{label}] 批 {bi // SIZE + 1}/{(len(todo) + SIZE - 1) // SIZE}', flush=True)
    return {t: (cache_get(t) if cache_get(t) is not None and not ok(t, cache_get(t)) else one(t, label))
            for t in dict.fromkeys(items)}


def translate_page(page, dry):
    src = PUB / f'{page}.md'
    fm, body = src.read_text(encoding='utf-8').split('\n---\n', 1)
    lines = body.strip().split('\n')
    idx = [(i, RE_IDX.match(ln)) for i, ln in enumerate(lines)]
    entries = [mask(m.group(2))[0] for i, m in idx if m]
    paras = [b for b in body.strip().split('\n\n') if b.strip() and not b.startswith('<p class="dv-idx')
             and re.search(r'[A-Za-z]{3}', RE_TAG.sub('', b))]
    print(f'[{page}] 索引条目 {len(entries)}、段落 {len(paras)}', flush=True)
    if dry:
        return
    if entries:
        zh = batch(entries, page)
        for i, m in idx:
            if m:
                t, tags = mask(m.group(2))
                lines[i] = m.group(1) + unmask(zh[t], tags) + m.group(3)
        # 小标题（IN VOL. I.、PAGE、VOL. PAGE. 之类）：单字母分节头（A、B…）照留，其余译出
        for i, ln in enumerate(lines):
            h = re.match(r'^(<h\d[^>]*>|<p class="dv-idx-caption">)(.*)(</h\d>|</p>)$', ln)
            if h and re.search(r'[A-Za-z]{2}', RE_TAG.sub('', h.group(2))):
                t, tags = mask(h.group(2))
                lines[i] = h.group(1) + unmask(one(t, page + '·head'), tags) + h.group(3)
        out_body = '\n'.join(lines)
    else:
        out_body = body.strip()
        prev = ''
        for b in paras:
            t, tags = mask(b)
            out_body = out_body.replace(b, unmask(one(t, page, prev[-600:]), tags), 1)
            prev = RE_TAG.sub('', b)
    # 达文南特正文中文页同一套落盘处理：省略号规范、教派名补原名、原名括注转 dv-orig 灰字方括号
    out_body = D.bracket_glosses(D.annotate_sects(D.normalize_etc(out_body), body))
    # 中文页 front matter：照英文，换标题、加 en_url，去掉翻页链（中文页之间不串）
    keep = [ln for ln in fm.split('\n') if ln and not ln.startswith(('title:', 'prev_', 'next_', 'zh_url:', '---'))]
    date = subprocess.run(['date', '+%Y-%m-%d %H:%M'], capture_output=True, text=True).stdout.strip()
    keep = [ln for ln in keep if not ln.startswith('date:')] + [f'date: {date}']
    out = ['---', f'title: "{TITLE_ZH[page]}"', *keep, f'en_url: "/davenant/colossians/{page}/"', '---', '', out_body, '']
    dst = PUB / page / 'zh' / 'index.md'
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text('\n'.join(out), encoding='utf-8')
    print(f'✓ 写入 {dst.relative_to(ROOT)}', flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', action='append', default=[], choices=list(TITLE_ZH))
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()
    tf.SYSTEM = AUX_SYSTEM
    for p in a.page:
        translate_page(p, a.dry_run)


if __name__ == '__main__':
    main()
