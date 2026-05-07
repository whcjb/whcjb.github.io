#!/usr/bin/env python3
"""Handle scripture blocks where reference comes AFTER the quote."""
import sqlite3, re
from pathlib import Path

conn = sqlite3.connect('/tmp/bible_cuvs.db')
cursor = conn.cursor()
cursor.execute('SELECT SN, FullName FROM BibleID')
BOOK_MAP = {name: sn for sn, name in cursor.fetchall()}

def get_verse_kw(book, ch, vs):
    if book not in BOOK_MAP: return None
    cursor.execute('SELECT Lection FROM Bible WHERE VolumeSN=? AND ChapterSN=? AND VerseSN=?',
                   (BOOK_MAP[book], ch, vs))
    r = cursor.fetchone()
    if not r: return None
    return r[0].replace('\u3000','').replace('"','').replace('"','').strip()[:6]

CN_NUMS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
    '十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,'十七':17,
    '十八':18,'十九':19,'二十':20,'二十一':21,'二十二':22,'二十三':23,
    '二十四':24,'二十五':25,'二十六':26,'二十七':27,'二十八':28,'二十九':29,
    '三十':30,'三十一':31,'三十二':32,'三十三':33,'三十四':34,'三十七':37,
    '四十':40,'四十二':42,'五十五':55,'一百五十':150}

def parse_cn(s):
    s = s.strip()
    if s.isdigit(): return int(s)
    return CN_NUMS.get(s)

ref_re = re.compile(r'[（(]《([^》]+)》\s*([一二三四五六七八九十百\d]+)\s*章\s*(\d+)\s*[至～~\-]*\s*(\d*)\s*节[）)]')

out_dir = Path('/Users/yanpeifa/Documents/whcjb.github.io/reading/tripp/quest/')
total = 0

for ch_num in range(1, 19):
    f = out_dir / f'{ch_num}.md'
    text = f.read_text('utf-8')
    lines = text.split('\n')
    
    new_lines = []
    added = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check if this is a standalone reference line like （《路加福音》十四章 28～33 节）
        ref_match = re.match(r'^<p>\s*[（(]《([^》]+)》\s*([一二三四五六七八九十百\d]+)\s*章\s*(\d+)\s*[至～~\-]*\s*(\d*)\s*节[）)]\s*</p>$', line)
        if ref_match:
            book = ref_match.group(1)
            ch = parse_cn(ref_match.group(2))
            vs = int(ref_match.group(3))
            ve = int(ref_match.group(4)) if ref_match.group(4) else vs
            ref_str = f'《{book}》{ref_match.group(2)}章{ref_match.group(3)}'
            if ref_match.group(4): ref_str += f'～{ref_match.group(4)}'
            ref_str += '节'
            
            kw = get_verse_kw(book, ch, vs) if ch else None
            
            # Look backwards for the verse paragraph(s)
            # Find the previous <p> that isn't already a scripture-block
            verse_lines = []
            j = len(new_lines) - 1
            while j >= 0 and not new_lines[j].strip():
                j -= 1
            
            # Check if previous paragraph matches verse text
            if j >= 0 and new_lines[j].startswith('<p>') and 'scripture-block' not in new_lines[j]:
                para = re.sub(r'<[^>]+>', '', new_lines[j]).strip()
                if kw and kw[:3] in para[:12]:
                    # Convert this paragraph to scripture-block
                    content = re.sub(r'^<p>|</p>$', '', new_lines[j])
                    new_lines[j] = f'<div class="scripture-block">{content}<span class="scripture-ref">——{ref_str}</span></div>'
                    added += 1
                    i += 1  # skip the reference line
                    continue
            
            new_lines.append(line)
            i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    if added:
        f.write_text('\n'.join(new_lines), 'utf-8')
        total += added
        print(f'ch{ch_num}: +{added}')

print(f'\nTotal: {total}')
conn.close()
