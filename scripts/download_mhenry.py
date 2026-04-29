#!/usr/bin/env python3
"""Download all Matthew Henry OT PDFs from AList and extract chapters to mhenry/ directory."""
import json, subprocess, os, re, sys, time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALIST_BASE = 'https://thereformedcatholic.org/download'
ALIST_PATH = ('/長老宗 Presbyterianism/EPCEW英格蘭和威爾士福音長老會The\xa0Evangelical '
              'Presbyterian Church in England and Wales/馬太亨利 Matthew Henry/'
              '馬太亨利聖經注釋/古舊福音林弟兄譯/馬亨舊約')
DATE = '2026-04-29'
TMPDIR = '/tmp/mhenry_pdfs'
os.makedirs(TMPDIR, exist_ok=True)

# ── Chinese number → int ────────────────────────────────────────
CN = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,
      '十':10,'百':100}

def cn_to_int(s):
    s = s.strip()
    result = 0
    tmp = 0
    for ch in s:
        v = CN.get(ch)
        if v is None: return None
        if v >= 10:
            if tmp == 0: tmp = 1
            result += tmp * v
            tmp = 0
        else:
            tmp = v
    return result + tmp

# ── PDF filename → (book_id, book_name, total_chapters, uses_pian) ──
BOOK_MAP = {
    '创世记':    ('genesis',       '创世记',     50,  False),
    '出埃及记':  ('exodus',        '出埃及记',   40,  False),
    '利未记':    ('leviticus',     '利未记',     27,  False),
    '民数记':    ('numbers',       '民数记',     36,  False),
    '申命记':    ('deuteronomy',   '申命记',     34,  False),
    '约书亚记':  ('joshua',        '约书亚记',   24,  False),
    '士师记':    ('judges',        '士师记',     21,  False),
    '路得记':    ('ruth',          '路得记',     4,   False),
    '撒母耳记上':('1samuel',       '撒母耳记上', 31,  False),
    '撒母耳记下':('2samuel',       '撒母耳记下', 24,  False),
    '列王纪上':  ('1kings',        '列王记上',   22,  False),
    '列王纪下':  ('2kings',        '列王记下',   25,  False),
    '历代志上':  ('1chronicles',   '历代志上',   29,  False),
    '历代志下':  ('2chronicles',   '历代志下',   36,  False),
    '以斯拉记':  ('ezra',          '以斯拉记',   10,  False),
    '尼希米记':  ('nehemiah',      '尼希米记',   13,  False),
    '以斯帖记':  ('esther',        '以斯帖记',   10,  False),
    '约伯记':    ('job',           '约伯记',     42,  False),
    '诗篇':      ('psalms',        '诗篇',       150, True),
    '箴言':      ('proverbs',      '箴言',       31,  False),
    '传道书':    ('ecclesiastes',  '传道书',     12,  False),
    '雅歌':      ('songofsolomon', '雅歌',       8,   False),
    '以赛亚书':  ('isaiah',        '以赛亚书',   66,  False),
    '耶利米书':  ('jeremiah',      '耶利米书',   52,  False),
    '耶利米哀歌':('lamentations',  '耶利米哀歌', 5,   False),
    '以西结书':  ('ezekiel',       '以西结书',   48,  False),
    '但以理书':  ('daniel',        '但以理书',   12,  False),
    '何西阿书':  ('hosea',         '何西阿书',   14,  False),
    '约珥书':    ('joel',          '约珥书',     3,   False),
    '阿摩司书':  ('amos',          '阿摩司书',   9,   False),
    '俄巴底亚书':('obadiah',       '俄巴底亚书', 1,   False),
    '约拿书':    ('jonah',         '约拿书',     4,   False),
    '弥迦书':    ('micah',         '弥迦书',     7,   False),
    '那鸿书':    ('nahum',         '那鸿书',     3,   False),
    '哈巴谷书':  ('habakkuk',      '哈巴谷书',   3,   False),
    '西番雅书':  ('zephaniah',     '西番雅书',   3,   False),
    '哈该书':    ('haggai',        '哈该书',     2,   False),
    '撒迦利亚书':('zechariah',     '撒迦利亚书', 14,  False),
    '玛拉基书':  ('malachi',       '玛拉基书',   4,   False),
}

def identify_book(filename):
    for key, val in BOOK_MAP.items():
        if key in filename:
            return val
    return None

def alist_get(filename):
    path = ALIST_PATH + '/' + filename
    body = json.dumps({'path': path, 'password': ''})
    r = subprocess.run([
        'curl', '-s', '-X', 'POST', f'{ALIST_BASE}/api/fs/get',
        '-H', 'Content-Type: application/json', '--data-raw', body
    ], capture_output=True, text=True)
    d = json.loads(r.stdout)
    if d.get('code') != 200:
        print(f'  AList error for {filename}: {d.get("message")}')
        return None
    return d['data']

def download_pdf(filename, local_path):
    if os.path.exists(local_path) and os.path.getsize(local_path) > 10000:
        print(f'  Already downloaded: {filename}')
        return True
    info = alist_get(filename)
    if not info:
        return False
    raw_url = info.get('raw_url', '')
    if not raw_url:
        print(f'  No raw_url for {filename}')
        return False
    r = subprocess.run(['curl', '-s', '-L', raw_url, '-o', local_path], capture_output=True)
    if r.returncode != 0 or not os.path.exists(local_path):
        print(f'  Download failed for {filename}')
        return False
    print(f'  Downloaded {filename} ({os.path.getsize(local_path)//1024}KB)')
    return True

def strip_header_lines(page_text):
    lines = page_text.splitlines()
    return '\n'.join(l for l in lines if not ('马太亨利' in l and len(l.strip()) < 100))

def extract_chapters(text, uses_pian):
    suffix = '篇' if uses_pian else '章'
    cn_nums = sorted(CN.keys(), key=len, reverse=True)
    cn_pat = '|'.join(re.escape(c) for c in cn_nums)
    header_re = re.compile(
        r'^第((?:' + cn_pat + r')+)' + re.escape(suffix) + r'\s*$',
        re.MULTILINE
    )
    pages = text.split('\x0c')
    full_text = '\n'.join(strip_header_lines(p) for p in pages)

    matches = list(header_re.finditer(full_text))
    if not matches:
        print('  WARNING: no chapter headings found')
        return {}

    chapters = {}
    for i, m in enumerate(matches):
        ch_num = cn_to_int(m.group(1))
        if ch_num is None:
            continue
        start = m.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(full_text)
        content = re.sub(r'\n{3,}', '\n\n', full_text[start:end].strip())
        chapters[ch_num] = content
    return chapters

def write_chapter(book_id, book_name, total_chapters, ch_num, content):
    book_dir = os.path.join(REPO, 'mhenry', book_id)
    os.makedirs(book_dir, exist_ok=True)
    out_path = os.path.join(book_dir, f'{ch_num}.md')
    if os.path.exists(out_path):
        return False
    fm = (f'---\nlayout: mhenry-chapter\nbook_id: {book_id}\nbook_name: {book_name}\n'
          f'chapter: {ch_num}\ntotal_chapters: {total_chapters}\n'
          f'header-img: img/post-bg-2015.jpg\ndate: {DATE}\n---\n\n')
    with open(out_path, 'w') as f:
        f.write(fm + content + '\n')
    return True

def ensure_book_index(book_id, book_name, chapters):
    idx = os.path.join(REPO, 'mhenry', book_id, 'index.html')
    if os.path.exists(idx):
        return
    os.makedirs(os.path.dirname(idx), exist_ok=True)
    with open(idx, 'w') as f:
        f.write(f'---\nlayout: mhenry-book\nbook_id: {book_id}\nbook_name: {book_name}\nchapters: {chapters}\n---\n')

def process_pdf(filename):
    info = identify_book(filename)
    if not info:
        print(f'  SKIP (unknown book): {filename}')
        return 0
    book_id, book_name, total_chapters, uses_pian = info

    local_pdf = os.path.join(TMPDIR, filename.replace('/', '_'))
    local_txt = local_pdf.replace('.pdf', '.txt')

    if not download_pdf(filename, local_pdf):
        return 0

    if not os.path.exists(local_txt):
        r = subprocess.run(['pdftotext', '-layout', local_pdf, local_txt], capture_output=True)
        if r.returncode != 0:
            print(f'  pdftotext failed for {filename}')
            return 0

    text = open(local_txt).read()
    chapters = extract_chapters(text, uses_pian)
    if not chapters:
        return 0

    written = sum(write_chapter(book_id, book_name, total_chapters, n, c)
                  for n, c in sorted(chapters.items()))
    ensure_book_index(book_id, book_name, total_chapters)
    print(f'  Wrote {written} new chapters for {book_name}')
    return written

def main():
    body = json.dumps({'path': ALIST_PATH, 'password': '', 'page': 1, 'per_page': 100, 'refresh': False})
    r = subprocess.run([
        'curl', '-s', '-X', 'POST', f'{ALIST_BASE}/api/fs/list',
        '-H', 'Content-Type: application/json', '--data-raw', body
    ], capture_output=True, text=True)
    d = json.loads(r.stdout)
    files = [x['name'] for x in (d.get('data') or {}).get('content', [])
             if x['name'].endswith('.pdf')]
    print(f'Found {len(files)} PDFs')

    skip = {'19马太亨利完整圣经注释-诗篇（卷1）001-041.pdf',
            '19马太亨利完整圣经注释-诗篇（卷2）042-072.pdf'}

    total = 0
    for filename in files:
        if filename in skip:
            print(f'Skipping (already done): {filename}')
            continue
        print(f'\nProcessing: {filename}')
        total += process_pdf(filename)
        time.sleep(0.3)

    print(f'\nDone. Total new chapters written: {total}')
    print('Regenerating pagination...')
    subprocess.run(['python3', os.path.join(REPO, 'scripts', 'update-recent.py')])
    print('Pagination updated.')

if __name__ == '__main__':
    main()
