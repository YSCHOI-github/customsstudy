# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

# Compare appendix structure between working file and broken file
files = [
    (r'01_관세평가\10_단권화\02_01_과세가격결정기본원칙.md', 'WORKING'),
    (r'01_관세평가\10_단권화\06_03_국내판매가격(4방법).md', 'BROKEN'),
]

for filepath, label in files:
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_bytes = sum(len(l.encode('utf-8')) for l in lines)
    print(f'=== {label}: {filepath} ===')
    print(f'Total lines: {len(lines)}')
    print(f'File size: {total_bytes} bytes')
    
    # Find [부록] section
    appendix_start = None
    for i, line in enumerate(lines):
        if '[부록]' in line:
            appendix_start = i
            break
    
    if appendix_start:
        print(f'Appendix starts at line: {appendix_start + 1}')
        # Show context around appendix start
        start = max(0, appendix_start - 3)
        end = min(len(lines), appendix_start + 30)
        print(f'Context (lines {start+1}-{end}):')
        for j in range(start, end):
            line_content = lines[j].rstrip('\r\n')
            print(f'  {j+1}: {line_content[:120]}')
    
    # Find first ### heading in appendix
    if appendix_start:
        for i in range(appendix_start, min(len(lines), appendix_start + 20)):
            if lines[i].strip().startswith('### '):
                heading = lines[i].rstrip('\r\n')
                print(f'\nFirst appendix heading at line {i+1}: [{heading}]')
                for k in range(max(0, i-2), i):
                    prev = lines[k].rstrip('\r\n')
                    print(f'  prev {k+1}: {repr(prev)}')
                print(f'  head {i+1}: {repr(heading)}')
                if i+1 < len(lines):
                    nxt = lines[i+1].rstrip('\r\n')
                    print(f'  next {i+2}: {repr(nxt)}')
                break

    # Check for any BOM or special chars at file start
    first_bytes = lines[0].encode('utf-8')[:10]
    hex_start = ' '.join(f'{b:02X}' for b in first_bytes)
    print(f'\nFirst bytes: {hex_start}')
    
    # Check number of headings at each level
    h1 = len(re.findall(r'^# [^#]', ''.join(lines), re.MULTILINE))
    h2 = len(re.findall(r'^## [^#]', ''.join(lines), re.MULTILINE))
    h3 = len(re.findall(r'^### [^#]', ''.join(lines), re.MULTILINE))
    h4 = len(re.findall(r'^#### [^#]', ''.join(lines), re.MULTILINE))
    print(f'Heading counts: H1={h1}, H2={h2}, H3={h3}, H4={h4}')
    
    print('\n' + '='*60 + '\n')
