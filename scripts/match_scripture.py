#!/usr/bin/env python3
"""Match scripture quotes using Simplified Chinese Union Version Bible (SQLite)."""
import sqlite3, re
from pathlib import Path

conn = sqlite3.connect('/tmp/bible_cuvs.db')
cursor = conn.cursor()

# Build book name -> VolumeSN mapping
cursor.execute('SELECT SN, FullName FROM BibleID')
BOOK_MAP = {}
for sn, name in cursor.fetchall():
    BOOK_MAP[name] = sn

def get_verse_kw(book_name, chapter, verse, length=6):
    if book_name not in BOOK_MAP: return None
    vol = BOOK_MAP[book_name]
    cursor.execute('SELECT Lection FROM Bible WHERE VolumeSN=? AND ChapterSN=? AND VerseSN=?',
                   (vol, chapter, verse))
    row = cursor.fetchone()
    if not row: return None
    text = row[0].replace('\u3000', '').replace('"', '').replace('"', '').strip()
    return text[:length]

CN_NUMS = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,
    '十一':11,'十二':12,'十三':13,'十四':14,'十五':15,'十六':16,'十七':17,
    '十八':18,'十九':19,'二十':20,'二十一':21,'二十二':22,'二十三':23,
    '二十四':24,'二十五':25,'二十六':26,'二十七':27,'二十八':28,'二十九':29,
    '三十':30,'三十一':31,'三十二':32,'三十三':33,'三十四':34,'三十七':37,
    '四十':40,'四十二':42,'四十四':44,'五十':50,'五十五':55,'六十':60,
    '一百':100,'一百一十九':119,'一百五十':150}

def parse_cn(s):
    s = s.strip()
    if s.isdigit(): return int(s)
    return CN_NUMS.get(s)

def normalize(s):
    return s.replace('\u3000', '').replace('"', '').replace('"', '').replace('"', '').replace('"', '').strip()

ref_re = re.compile(r'《([^》]+)》\s*([一二三四五六七八九十百\d]+)\s*章\s*(\d+)\s*[至～~\-]*\s*(\d*)\s*节')

out_dir = Path('/Users/yanpeifa/Documents/whcjb.github.io/reading/tripp/quest/')
total = 0

for ch_num in range(1, 19):
    f = out_dir / f'{ch_num}.md'
    text = f.read_text('utf-8')
    lines = text.split('\n')
    
    # Collect refs with verse keywords
    refs_by_line = {}
    for i, line in enumerate(lines):
        for m in ref_re.finditer(line):
            book = m.group(1)
            ch = parse_cn(m.group(2))
            vs = int(m.group(3))
            ve = int(m.group(4)) if m.group(4) else vs
            if ch:
                kw = get_verse_kw(book, ch, vs)
                if kw:
                    ref_str = f'《{book}》{m.group(2)}章{m.group(3)}'
                    if m.group(4): ref_str += f'～{m.group(4)}'
                    ref_str += '节'
                    refs_by_line.setdefault(i, []).append((normalize(kw), ref_str))
    
    new_lines = []
    added = 0
    i = 0
    while i < len(lines):
        line = lines[i]
        if 'scripture-block' in line:
            new_lines.append(line); i += 1; continue
        
        m_p = re.match(r'^<p>(.+)</p>$', line)
        if m_p:
            para_text = m_p.group(1)
            para_clean = normalize(re.sub(r'<[^>]+>', '', para_text))
            
            matched_ref = None
            for back in range(1, 8):
                cl = i - back
                if cl < 0: break
                if cl in refs_by_line:
                    for kw, ref_str in refs_by_line[cl]:
                        if kw[:3] in para_clean[:12]:
                            matched_ref = ref_str
                            break
                if matched_ref: break
            
            if matched_ref:
                new_lines.append(f'<div class="scripture-block">{para_text}<span class="scripture-ref">——{matched_ref}</span></div>')
                added += 1; i += 1; continue
        
        new_lines.append(line); i += 1
    
    if added:
        f.write_text('\n'.join(new_lines), 'utf-8')
        total += added
        print(f'ch{ch_num}: +{added}')

print(f'\nTotal new: {total}')
conn.close()
