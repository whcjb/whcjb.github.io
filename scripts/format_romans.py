#!/usr/bin/env python3
"""Format Romans v4: handle verse text embedded in paragraphs."""
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
    body = re.sub(r'\d+---第.+章\n?', '', body)
    body = re.sub(r'^第.+章\s*$', '', body, flags=re.MULTILINE)
    
    lines = body.strip().split('\n')
    new_lines = []
    i = 0
    current_verse_lines = []
    current_verse_start = None
    current_verse_end = None
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Detect verse line: starts with "N." (half-width) at line beginning
        # e.g., "1.耶稣基督的仆人保罗..."
        verse_start_match = re.match(r'^(\d+)\.(?!．)(.+)', stripped)
        
        # Detect commentary line: starts with "N．" (full-width)
        commentary_match = re.match(r'^(\d+)．', stripped)
        
        if verse_start_match and not commentary_match:
            num = int(verse_start_match.group(1))
            if current_verse_start is None:
                current_verse_start = num
            current_verse_end = num
            
            # Also find inline verse numbers: "...7.我写信给..."
            inline_nums = [int(m.group(1)) for m in re.finditer(r'(\d+)\.(?!．)', stripped)]
            if inline_nums:
                current_verse_end = max(current_verse_end, max(inline_nums))
            
            current_verse_lines.append(stripped)
            i += 1
            continue
        
        # If we were collecting verse lines and hit a non-verse line
        if current_verse_lines:
            # Check if this is a continuation of verse (no number prefix, short, follows verse)
            if stripped and not commentary_match and not stripped.startswith('#') and not stripped.startswith('---'):
                # Check for inline verse numbers
                inline_nums = [int(m.group(1)) for m in re.finditer(r'(\d+)\.(?!．)', stripped)]
                if inline_nums:
                    current_verse_end = max(current_verse_end, max(inline_nums))
                    current_verse_lines.append(stripped)
                    i += 1
                    continue
                # No verse number but could be continuation of verse text
                # If the line is relatively short and the next line starts with N．, it's verse continuation
                if len(stripped) < 80:
                    current_verse_lines.append(stripped)
                    i += 1
                    continue
            
            # Flush verse block
            verse_text = ' '.join(' '.join(current_verse_lines).split())
            vs, ve = current_verse_start, current_verse_end
            
            new_lines.append('')
            new_lines.append('---')
            new_lines.append('')
            new_lines.append(f'## {ch_num}:{vs}-{ve}')
            new_lines.append('')
            new_lines.append(f'**{verse_text}**')
            new_lines.append('')
            
            current_verse_lines = []
            current_verse_start = None
            current_verse_end = None
            # Don't increment i - reprocess this line
            continue
        
        new_lines.append(line)
        i += 1
    
    # Flush any remaining verse
    if current_verse_lines:
        verse_text = ' '.join(' '.join(current_verse_lines).split())
        vs, ve = current_verse_start, current_verse_end
        new_lines.append('')
        new_lines.append('---')
        new_lines.append('')
        new_lines.append(f'## {ch_num}:{vs}-{ve}')
        new_lines.append('')
        new_lines.append(f'**{verse_text}**')
        new_lines.append('')
    
    result = front_matter + '\n\n' + '\n'.join(new_lines)
    # Remove duplicate --- at the very start
    result = re.sub(r'(---\n\n)\n*---\n\n---', r'\1---', result)
    
    f.write_text(result, 'utf-8')
    
    # Count
    h2_count = len(re.findall(r'^## ', '\n'.join(new_lines), re.MULTILINE))
    bold_count = len(re.findall(r'^\*\*', '\n'.join(new_lines), re.MULTILINE))
    print(f'ch{ch_num}: {h2_count} sections, {bold_count} verse blocks')

print('Done!')
