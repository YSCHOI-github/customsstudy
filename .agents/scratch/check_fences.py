# -*- coding: utf-8 -*-
"""
Simulate Obsidian's code fence parsing to find unclosed blocks.
Obsidian code fence rules:
- Opening: line starts with 3+ backticks, optionally followed by language info
- Closing: line starts with 3+ backticks (at least as many as opening), no other content
- Content between fences is treated as code (headings not recognized)
"""
import sys, re
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'01_관세평가\10_단권화\06_03_국내판매가격(4방법).md'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

in_code = False
open_line = None
open_backticks = 0

for i, line in enumerate(lines):
    stripped = line.rstrip('\r\n')
    
    # Count leading backticks
    leading_backticks = 0
    for c in stripped:
        if c == '`':
            leading_backticks += 1
        else:
            break
    
    if leading_backticks >= 3:
        rest = stripped[leading_backticks:].strip()
        
        if in_code:
            # Closing fence: must have >= open_backticks and NO other content
            if leading_backticks >= open_backticks and rest == '':
                print(f"Line {i+1}: CLOSE fence (```x{leading_backticks}), was opened at line {open_line}")
                in_code = False
                open_line = None
            else:
                # Not a valid close, still in code
                pass
        else:
            # Opening fence: can have language info after backticks, but NOT closing backticks
            # A line like ``` is an opening fence
            # A line like ```python is an opening fence
            # A line like `some text` is inline code (but has only 1 backtick)
            # But ```...``` on same line is tricky
            
            # In CommonMark/Obsidian: opening code fence line cannot contain closing backticks
            # If the rest doesn't contain any backtick, it's a valid opening
            if '`' not in rest:
                print(f"Line {i+1}: OPEN fence (```x{leading_backticks}) info=[{rest}]")
                in_code = True
                open_line = i + 1
                open_backticks = leading_backticks
            else:
                print(f"Line {i+1}: SKIP (backtick in rest): [{stripped[:80]}]")

if in_code:
    print(f"\n*** UNCLOSED CODE BLOCK from line {open_line} ***")
    print(f"*** Everything after line {open_line} is inside a code block! ***")
    print(f"*** Obsidian won't recognize headings from line {open_line} to end of file ***")
else:
    print(f"\nAll code blocks properly closed")
