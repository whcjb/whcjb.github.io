#!/usr/bin/env python3
"""
owen_extract.py — 约翰·欧文《希伯来书注释》(7 卷, thereformedcatholic AList 下载的
CCEL 系纯文本 PDF, 单栏, size≈14.4, x≈72) → 结构化文本。

非 Ages 格式: 无 <NNNNNN> 代码/无双栏/无 F·FT 脚注。段落边界靠行间距(正常≈17,
段间≈32)。标题: EXERCITATION N / 罗马数字节标题 / "Ver. N—经文" / CHAPTER。

用法:
    python3 scripts/owen_extract.py <vol 1-7> [--out FILE]
输出结构化文本(段落一行, 标题前缀 [H1]/[H2]/[VER]/[EXER]), 供后续切分成 md。
"""
import fitz, re, sys, os

PDF_DIR = os.path.expanduser('~/Documents/论文/owen')
BODY_SIZE = 14.4
PARA_GAP = 25          # y 间距 > 此值视为新段
HEAD_Y = 66            # y < 此值 = 页眉区
FOOT_Y = 724           # y > 此值 = 页脚区

RE_EXER   = re.compile(r'^EXERCITATION\s+([IVXLC]+)\.?\s*$')
RE_VER    = re.compile(r'^Vers?e?s?\.?\s+\d')
RE_CHAP   = re.compile(r'^CHAPTER\s+([IVXLC]+)\.?\s*$')
RE_PARTHD = re.compile(r'^PART\s+[IVXLC]+\b')
RE_ROMANHD= re.compile(r'^([IVXLC]{1,6})\.\s*[—\-–]')   # 节标题 "III.—TO..."
RE_PAGENUM= re.compile(r'^\d{1,4}$')
RE_RUNHEAD= re.compile(r'^(AN EXPOSITION|EXPOSITION|HEBREWS|OWEN)', re.I)


def page_lines(page):
    out = []
    for b in page.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            spans = l.get('spans', [])
            txt = ''.join(s['text'] for s in spans).rstrip()
            if not txt.strip():
                continue
            y = l['bbox'][1]; x = l['bbox'][0]; x1 = l['bbox'][2]
            sz = spans[0]['size'] if spans else 0
            out.append({'y': y, 'x': x, 'x1': x1, 'sz': sz, 't': txt})
    out.sort(key=lambda r: r['y'])
    return out

def starts_marker(t):
    """段首分点/章节标记 → 新段"""
    s = t.strip()
    return bool(re.match(r'^(\d{1,3}\.|\(\d{1,3}\.?\)|\[\d{1,3}\.?\]|CHAPTER\s|EXERCITATION\s|Vers?e?s?\.\s|PART\s|[IVXLC]{1,5}\.\s)', s))


def is_chrome(r):
    """页眉页脚 / 页码 / running header"""
    if r['y'] < HEAD_Y or r['y'] > FOOT_Y:
        return True
    s = r['t'].strip()
    if RE_PAGENUM.match(s):
        return True
    if RE_RUNHEAD.match(s) and len(s) < 45:
        return True
    return False


def dehyphen(a, b):
    """行尾断字合并: a 以字母+连字符结尾, b 以小写字母开头 → 直接拼"""
    if re.search(r'[A-Za-z]-$', a) and re.match(r'[a-z]', b):
        return a[:-1] + b
    return a + ' ' + b


def classify(line):
    s = line.strip()
    if RE_EXER.match(s):   return 'EXER'
    if RE_CHAP.match(s):   return 'CHAP'
    if RE_PARTHD.match(s): return 'PART'
    if RE_VER.match(s):    return 'VER'
    if RE_ROMANHD.match(s) and len(s) < 80: return 'H2'
    # 短全大写行 = 小标题
    if len(s) < 55 and s == s.upper() and re.search(r'[A-Z]', s) and not RE_PAGENUM.match(s):
        return 'H2'
    return 'BODY'


def extract(vol):
    d = fitz.open(os.path.join(PDF_DIR, f'owen_hebrews_{vol}.pdf'))
    paras = []          # (kind, text)
    cur = []            # current paragraph display-lines
    prev_y = None
    def flush():
        if not cur:
            return
        text = cur[0]
        for nx in cur[1:]:
            text = dehyphen(text, nx)
        paras.append(text.strip())
        cur.clear()
    prev_y = None; prev_x1 = None; prev_right = None
    for i in range(d.page_count):
        lines = [r for r in page_lines(d[i]) if not is_chrome(r)]
        if not lines:
            continue
        page_right = max(r['x1'] for r in lines)   # 本页正文右边距
        for j, r in enumerate(lines):
            if j == 0:
                # 跨页边界: 上页末行"短"(段落结束) 或 本行是分点标记 → 分段; 否则续接
                if cur and (prev_x1 is None
                            or prev_x1 < (prev_right or page_right) - 28
                            or starts_marker(r['t'])):
                    flush()
            else:
                if r['y'] - prev_y > PARA_GAP:
                    flush()
            cur.append(r['t'])
            prev_y = r['y']; prev_x1 = r['x1']
        prev_right = page_right
    flush()
    # 分类每段
    return [(classify(p), p) for p in paras if p.strip()]


def main():
    if len(sys.argv) < 2:
        print('用法: owen_extract.py <vol 1-7> [--out FILE]'); return
    vol = int(sys.argv[1])
    rows = extract(vol)
    out = None
    if '--out' in sys.argv:
        out = sys.argv[sys.argv.index('--out') + 1]
    lines = []
    from collections import Counter
    c = Counter(k for k, _ in rows)
    for kind, text in rows:
        lines.append(f'[{kind}] {text}' if kind != 'BODY' else text)
    data = '\n\n'.join(lines)
    if out:
        open(out, 'w', encoding='utf-8').write(data)
        print(f'Vol{vol}: {len(rows)} 段 → {out}  分类 {dict(c)}')
    else:
        print(f'Vol{vol}: {len(rows)} 段  分类 {dict(c)}')
        for kind, text in rows[:40]:
            print(f'[{kind}] {text[:90]}')


if __name__ == '__main__':
    main()
