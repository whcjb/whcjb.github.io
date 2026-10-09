#!/usr/bin/env python3
"""约翰斯通：逐张印面与我们的正文比对，只问「哪里对不上」。

与以赛亚那支（isaiah_page_proofread.py）同一个道理。差别在**锚定**：
以赛亚要拿 PDF 文本层去正文里找锚点（段落常横跨三页），这里我们手上就有
逐页的 OCR 产物，`extract_johnstone.page_text` 能还原「这一页是哪些字」，
拿它的词序列去最终产物里做最长公共子串即可。锚不上就直说，不硬切 ——
锚不上本身就是线索（多半是整段丢失或严重错位）。

为什么非做这一遍不可：检测器只看得见**已知类型**。斜体大写 I 被读成
`7`/`J`/`Z`、`*ever*` 实为 `*never*` 这些，token 本身全合法，非词率、
星号奇偶、页眉判据一条都报不出来；抽三页实读就查出 6 处
（feedback_page_image_is_final_authority / feedback_read_then_sweep）。

    python3 scripts/johnstone_page_proofread.py --leaves 119,367,429
    python3 scripts/johnstone_page_proofread.py --all          # 全书，可断点续
    python3 scripts/johnstone_page_proofread.py --report
"""
import argparse
import base64
import difflib
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import alexander_abbyy as A
import extract_johnstone as E

ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'johnstone', 'philippians')
IMG = os.path.join(ROOT, 'johnstone_raw', 'philippians', 'src', 'images')
LOG = os.path.join(ROOT, 'logs', 'johnstone_pageproof.tsv')
WORD = re.compile(r"[A-Za-zÆæ][A-Za-zÆæ0-9'’-]*")
WIDTH = 1100          # 送图的宽度。1995 原宽太费 token，1100 仍清晰可读

SYSTEM = (
    'You are proof-reading a 19th-century printed book against a transcription '
    '(Robert Johnstone, "Lectures Exegetical and Practical on the Epistle of '
    'Paul to the Philippians", Edinburgh 1875).\n'
    'You get ONE page image and the transcription of that page. Report ONLY the '
    'places where the transcription does not match what is printed.\n'
    'Rules:\n'
    '1. One finding per line, exactly:  MISMATCH: <transcription> ||| <printed>\n'
    '   Quote enough words around it to locate the spot unambiguously.\n'
    '2. IGNORE: the running head line, the page number, printer signature marks, '
    'line-break hyphens, and differences of italic markup (the transcription uses '
    '*asterisks* for italics).\n'
    '3. IGNORE differences in quotation-mark style and in spacing.\n'
    '4. DO report: wrong or missing words, wrong letters inside words, wrong or '
    'missing numbers, words in the wrong order, text present in the image but '
    'absent from the transcription (and vice versa).\n'
    '5. Pay special attention to italic words — the OCR misreads them most.\n'
    '6. The transcription may carry a few words from the previous or the next '
    'page at its very beginning and its very end. IGNORE any mismatch that '
    'falls in the first line or the last line.\n'
    '7. The lecture number and the all-capitals lecture title are moved '
    'elsewhere in our edition; do NOT report them as missing.\n'
    '8. If everything matches, answer exactly:  OK\n'
    'Answer with nothing but the findings (or OK).'
)


def published():
    buf = []
    for f in sorted(os.listdir(OUT)):
        if f.endswith('.md'):
            buf.append(open(os.path.join(OUT, f), encoding='utf-8')
                       .read().split('---', 2)[-1])
    return '\n\n'.join(buf)


def slice_for(raw, whole, w_words, w_pos):
    """这一页在最终产物里的那一段。拿词序列做最长公共块定位。"""
    pw = WORD.findall(raw.replace('*', ''))
    if len(pw) < 25:
        return None
    sm = difflib.SequenceMatcher(None, w_words, pw, autojunk=False)
    m = sm.find_longest_match(0, len(w_words), 0, len(pw))
    if m.size < 12:
        return None
    # 窗口只放宽 2 个词。早先放 8 个，切片两头各带进小半句邻页的话，
    # 模型照实报「这句印面上没有」—— 先导 12 页里 5 页中招，全是我自己
    # 切出来的假阳性。
    lo = max(0, m.a - m.b - 2)
    hi = min(len(w_words) - 1, m.a + (len(pw) - m.b) + 2)
    return strip_markup(whole[w_pos[lo][0]:w_pos[hi][1]])


RE_TAG = re.compile(r'<[^<>]{1,200}>')


def strip_markup(t):
    """发布层的东西不要送进去比对：`<span class="jh-ref">…</span>`、
    `<div class="jh-epigraph">`、markdown 标题。它们印面上当然没有，
    送进去只换来一堆「印面上没有这一行」。"""
    t = RE_TAG.sub('', t)
    t = re.sub(r'^#{1,6} .*$', '', t, flags=re.M)
    return re.sub(r'\n{3,}', '\n\n', t).strip()


def ask(png, text):
    msg = {'type': 'user', 'message': {'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/png',
                                     'data': base64.b64encode(png).decode()}},
        {'type': 'text', 'text': 'Transcription of this page:\n\n' + text}]}}
    # 砍 CLI 前缀：不带这几个开关，每次调用会先灌进两万多 token 的工具定义
    # 与 MCP 清单（feedback_trim_claude_cli_for_translation）。
    #   --mcp-config '{}'      一个 MCP server 都不挂
    #   --strict-mcp-config    不去读用户/项目的 .mcp.json
    #   --disallowedTools '*'  工具定义一条不发
    #   --safe-mode            不跑任何钩子
    #   --system-prompt        换掉默认那段长系统提示
    cmd = ['claude', '-p', '--safe-mode',
           '--mcp-config', '{"mcpServers":{}}', '--strict-mcp-config',
           '--disallowedTools', '*', '--input-format', 'stream-json',
           '--output-format', 'stream-json', '--verbose', '--system-prompt', SYSTEM]
    r = subprocess.run(cmd, input=json.dumps(msg) + '\n', capture_output=True,
                       text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError(f'rc={r.returncode} {r.stderr[:160]}')
    for line in r.stdout.splitlines():
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get('type') == 'result':
            if o.get('is_error'):
                raise RuntimeError(str(o.get('result'))[:200])
            return str(o.get('result') or ''), float(o.get('total_cost_usd') or 0)
    raise RuntimeError('no result')


def done_leaves():
    if not os.path.exists(LOG):
        return set()
    out = set()
    for line in open(LOG, encoding='utf-8'):
        p = line.split('\t')
        if p and p[0].isdigit():
            out.add(int(p[0]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--leaves', default='')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()

    if a.report:
        rows = [l.rstrip('\n').split('\t') for l in open(LOG, encoding='utf-8')]
        hit = [r for r in rows if len(r) > 3 and r[2] == 'MISMATCH']
        pages = {r[0] for r in rows if r and r[0].isdigit()}
        cost = sum(float(r[1]) for r in rows if len(r) > 1 and r[0].isdigit()
                   and re.fullmatch(r'[\d.]+', r[1] or ''))
        print(f'已比对 {len(pages)} 页，报出 {len(hit)} 处，累计 ${cost:.2f}')
        for r in hit[:80]:
            print(f'  leaf {r[0]}  {r[3]}')
        return

    from PIL import Image
    ab = A.parse_pages(E.load_xml())
    ocr = E.ocr_pages()
    for lf in E.drop_duplicate_leaves(ocr):
        del ocr[lf]
    first, shapes = E.learn_heads(ocr)
    sec = E.assign_leaves(ocr)
    whole = published()
    w_words, w_pos = [], []
    for m in WORD.finditer(whole):
        w_words.append(m.group(0)); w_pos.append((m.start(), m.end()))

    body = [l for l in sorted(ocr)
            if sec.get(l) not in (None, 'front') and len(ocr[l]) > 20]
    if a.leaves:
        leaves = [int(x) for x in a.leaves.split(',')]
    else:
        leaves = [l for l in body if l not in done_leaves()]
    if a.limit:
        leaves = leaves[:a.limit]

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    fh = open(LOG, 'a', encoding='utf-8')
    total = 0.0
    for n, leaf in enumerate(leaves, 1):
        raw = E.page_text([p['text'] for p in ab[leaf]['pars']], ocr[leaf],
                          first.get(leaf, ''), shapes)
        text = slice_for(raw, whole, w_words, w_pos)
        if not text:
            fh.write(f'{leaf}\t0\tANCHOR-FAIL\t\n'); fh.flush()
            print(f'{leaf:4d} 锚不上', file=sys.stderr)
            continue
        im = Image.open(os.path.join(IMG, f'{leaf:04d}.jp2'))
        im = im.resize((WIDTH, int(im.height * WIDTH / im.width)))
        buf = io.BytesIO(); im.save(buf, 'PNG')
        try:
            res, cost = ask(buf.getvalue(), text)
        except Exception as e:
            print(f'{leaf:4d} 失败 {e}', file=sys.stderr)
            time.sleep(5)
            continue
        total += cost
        hits = [l for l in res.splitlines() if l.strip().startswith('MISMATCH')]
        fh.write(f'{leaf}\t{cost:.4f}\t{"MISMATCH" if hits else "OK"}\t'
                 + ' ⟂ '.join(h.strip() for h in hits) + '\n')
        fh.flush()
        print(f'{leaf:4d} {len(hits):2d} 处  ${cost:.4f}  累计 ${total:.2f}'
              f'  ({n}/{len(leaves)})', file=sys.stderr)
    fh.close()


if __name__ == '__main__':
    main()
