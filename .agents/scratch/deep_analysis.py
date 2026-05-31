# -*- coding: utf-8 -*-
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'01_관세평가\10_단권화\06_03_국내판매가격(4방법).md'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print("=== Checking for potential Obsidian parser-breaking elements ===\n")

# 1. Check for unclosed HTML tags
html_tags = re.findall(r'<([a-zA-Z]+)[^>]*>', content)
close_tags = re.findall(r'</([a-zA-Z]+)>', content)
print(f"Open HTML tags: {html_tags}")
print(f"Close HTML tags: {close_tags}")

# 2. Check for unclosed code blocks (```)
code_block_count = content.count('```')
print(f"\nCode block markers (```): {code_block_count} (should be even: {code_block_count % 2 == 0})")

# 3. Check for YAML frontmatter
if content.startswith('---'):
    print("\nFile starts with --- (could be YAML frontmatter)")
else:
    print("\nNo YAML frontmatter at start")

# 4. Check for any --- that could be misinterpreted
hr_lines = []
for i, line in enumerate(lines):
    stripped = line.strip()
    if stripped == '---':
        hr_lines.append(i + 1)
print(f"\nHorizontal rule (---) lines: {hr_lines}")
print(f"Total: {len(hr_lines)}")

# 5. Check for special Unicode that might break parser
special_chars = set()
for i, line in enumerate(lines):
    for j, c in enumerate(line):
        cp = ord(c)
        if cp > 0x7F and cp < 0xAC00 and cp not in range(0x3000, 0x3100):
            # Not ASCII, not Korean, not CJK symbols
            if c not in 'ㆍ':
                name = f'U+{cp:04X}'
                special_chars.add((c, name, i+1))

if special_chars:
    print(f"\nSpecial/unusual Unicode chars found:")
    for c, name, linenum in sorted(special_chars, key=lambda x: x[2]):
        print(f"  Line {linenum}: '{c}' ({name})")

# 6. Check the file for very long lines (could cause issues)
long_lines = [(i+1, len(line)) for i, line in enumerate(lines) if len(line) > 500]
if long_lines:
    print(f"\nVery long lines (>500 chars):")
    for linenum, length in long_lines:
        print(f"  Line {linenum}: {length} chars")

# 7. Check if heading links work when clicking (not just hovering)
# The [[#heading]] format in Obsidian
print("\n=== All unique heading texts across ALL levels ===")
all_headings = []
for i, line in enumerate(lines):
    m = re.match(r'^(#{1,6})\s+(.+)', line.strip())
    if m:
        level = len(m.group(1))
        text = m.group(2).strip()
        all_headings.append((i+1, level, text))
        print(f"  Line {i+1}: H{level} [{text}]")

# Check for duplicate headings
texts = [h[2] for h in all_headings]
duplicates = [t for t in set(texts) if texts.count(t) > 1]
if duplicates:
    print(f"\n*** DUPLICATE HEADINGS FOUND: {duplicates} ***")
else:
    print(f"\nNo duplicate headings")
