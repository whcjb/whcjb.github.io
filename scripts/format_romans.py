#!/usr/bin/env python3
"""Format Romans v2: force paragraph break before N．commentary lines."""
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
    
    body = re.sub(r'\d+---第.+章\s*\n?', '', body)
    body = re.sub(r'^第.+章\s*$', '', body, flags=re.MULTILINE)
    
    # Step 1: Merge lines into paragraphs
    # Blank line = paragraph break
    # Line starting with N．(full-width) = also paragraph break (commentary start)
    lines = body.split('\n')
    paragraphs = []
    current = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            # Blank line = paragraph break
            if current:
                paragraphs.append(' '.join(current))
                current = []
        elif re.match(r'^\d+．', stripped) and current:
            # Commentary start = force break before it
            paragraphs.append(' '.join(current))
            current = [stripped]
        else:
            current.append(stripped)
    if current:
        paragraphs.append(' '.join(current))
    
    # Step 2: Identify verse blocks and add formatting
    new_paras = []
    for para in paragraphs:
        verse_match = re.match(r'^(\d+)\.(?!．)', para)
        commentary_match = re.match(r'^(\d+)．', para)
        
        if verse_match and not commentary_match:
            all_nums = [int(m.group(1)) for m in re.finditer(r'(\d+)\.(?!．)', para)]
            vs = min(all_nums) if all_nums else int(verse_match.group(1))
            ve = max(all_nums) if all_nums else vs
            
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
    result_body = re.sub(r'\n{3,}', '\n\n', result_body)
    result_body = result_body.lstrip('\n- ')
    
    result = front_matter + '\n\n' + result_body
    f.write_text(result, 'utf-8')
    
    h2_count = len(re.findall(r'^## ', result_body, re.MULTILINE))
    print(f'ch{ch_num}: {h2_count} sections')

print('Done!')
