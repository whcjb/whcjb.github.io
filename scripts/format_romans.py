#!/usr/bin/env python3
"""Format Romans: merge lines into paragraphs, add ## headers and **bold**."""
import re
from pathlib import Path

romans_dir = Path('/Users/yanpeifa/Documents/whcjb.github.io/calvin/romans/')

for ch_num in range(1, 17):
    f = romans_dir / f'{ch_num}.md'
    text = f.read_text('utf-8')
    
    parts = text.split('---', 2)
    if len(parts) < 3: continue
    front_matter = parts[0] + '---' + parts[1] + '---'
    body = parts[2]
    
    # Clean artifacts
    body = re.sub(r'\d+---第.+章\s*\n?', '', body)
    body = re.sub(r'^第.+章\s*$', '', body, flags=re.MULTILINE)
    
    # Step 1: Merge single-newline lines into paragraphs (blank line = paragraph break)
    lines = body.split('\n')
    paragraphs = []
    current = []
    for line in lines:
        if not line.strip():
            if current:
                paragraphs.append(' '.join(current))
                current = []
        else:
            current.append(line.strip())
    if current:
        paragraphs.append(' '.join(current))
    
    # Step 2: Identify verse blocks vs commentary
    # Verse: starts with "N." (half-width)
    # Commentary: starts with "N．" (full-width)
    new_paras = []
    verse_buffer = []
    
    for para in paragraphs:
        verse_match = re.match(r'^(\d+)\.(?!．)', para)
        commentary_match = re.match(r'^(\d+)．', para)
        
        if verse_match and not commentary_match:
            # Find all verse numbers in this paragraph
            all_nums = [int(m.group(1)) for m in re.finditer(r'(\d+)\.(?!．)', para)]
            vs = min(all_nums) if all_nums else int(verse_match.group(1))
            ve = max(all_nums) if all_nums else vs
            
            # Output as ## header + **bold**
            new_paras.append('')
            new_paras.append('---')
            new_paras.append('')
            new_paras.append(f'## {ch_num}:{vs}-{ve}')
            new_paras.append('')
            new_paras.append(f'**{para}**')
            new_paras.append('')
        else:
            new_paras.append(para)
            new_paras.append('')
    
    result_body = '\n'.join(new_paras)
    # Clean up excessive blank lines and leading ---
    result_body = re.sub(r'\n{3,}', '\n\n', result_body)
    result_body = result_body.lstrip('\n- ')
    
    result = front_matter + '\n\n' + result_body
    f.write_text(result, 'utf-8')
    
    h2_count = len(re.findall(r'^## ', result_body, re.MULTILINE))
    print(f'ch{ch_num}: {h2_count} sections')

print('Done!')
