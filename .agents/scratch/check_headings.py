# -*- coding: utf-8 -*-
import re, sys

sys.stdout.reconfigure(encoding='utf-8')

filepath = r'01_관세평가\10_단권화\06_03_국내판매가격(4방법).md'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print("=== HEADINGS (### level) ===")
for i, line in enumerate(lines):
    stripped = line.rstrip('\r\n')
    if stripped.startswith('### '):
        linenum = i + 1
        heading_text = stripped[4:]
        special = []
        for j, c in enumerate(heading_text):
            if c == '\u3000':
                special.append(f"  pos {j}: FULLWIDTH SPACE U+3000")
            elif c == '\u00a0':
                special.append(f"  pos {j}: NO-BREAK SPACE U+00A0")
            elif c == '\u200b':
                special.append(f"  pos {j}: ZERO-WIDTH SPACE U+200B")
            elif c == '\ufeff':
                special.append(f"  pos {j}: BOM U+FEFF")
        
        has_trailing = stripped != stripped.rstrip()
        print(f"Line {linenum}: [{heading_text}] len={len(heading_text)} trailing_space={has_trailing}")
        if special:
            for s in special:
                print(s)
        hex_repr = ' '.join(f'{b:02X}' for b in heading_text.encode('utf-8'))
        print(f"  UTF-8 hex: {hex_repr}")
        print()

print("\n=== LINK TARGETS (unique [[#...]] patterns) ===")
content = ''.join(lines)
link_pattern = re.compile(r'\[\[#([^|\]]+?)(?:\|[^\]]+?)?\]\]')
targets = set()
for m in link_pattern.finditer(content):
    targets.add(m.group(1))

for t in sorted(targets):
    hex_repr = ' '.join(f'{b:02X}' for b in t.encode('utf-8'))
    print(f"Link target: [{t}] len={len(t)}")
    print(f"  UTF-8 hex: {hex_repr}")
    print()

print("\n=== MATCH CHECK ===")
headings = {}
for i, line in enumerate(lines):
    stripped = line.rstrip('\r\n')
    m = re.match(r'^(#{1,6})\s+(.*)', stripped)
    if m:
        h_text = m.group(2).strip()
        headings[h_text] = i + 1

for t in sorted(targets):
    if t in headings:
        print(f"OK  : [{t}] -> Line {headings[t]}")
    else:
        print(f"MISS: [{t}] - NO MATCHING HEADING FOUND")
        for h in headings:
            if t in h or h in t:
                print(f"      near match: [{h}] at Line {headings[h]}")
