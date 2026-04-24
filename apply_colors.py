import re

file_path = '01_관세평가/50_핵심요약/00_관세평가마인드맵초안.md'

RED    = 'color:#e74c3c;font-weight:bold'
ORANGE = 'color:#e67e22;font-weight:bold'
YELLOW = 'color:#d4ac0d'

def span(content, style):
    return f'<span style="{style}">{content}</span>'

rules = [
    # ── Section headers (## level) ──────────────────────────────
    ('## 1. ', ORANGE),
    ('## 2. ', RED),
    ('## 3. ', RED),
    ('## 4. ', YELLOW),
    ('## 5. ', YELLOW),
    ('## 6. ', ORANGE),
    ('## 7. ', YELLOW),
    ('## 8. ', ORANGE),
    # ── Section 1 ───────────────────────────────────────────────
    ('- 1.4. ', RED),
    # ── Section 2 ───────────────────────────────────────────────
    ('- 2.1. ', RED),
    ('- 2.2. ', RED),
    ('- 2.3. ', RED),
    ('- 2.4. ', RED),
    ('- 2.5. ', ORANGE),
    ('  - 2.4.1. ', RED),
    ('    - 2.4.2.1. ', RED),
    ('    - 2.4.2.2. ', RED),
    ('  - 2.4.3. ', ORANGE),
    # ── Section 3 ───────────────────────────────────────────────
    ('- 3.1. ', ORANGE),
    ('- 3.2. ', RED),
    ('- 3.3. ', YELLOW),
    ('  - 3.1.2. ', RED),
    ('  - 3.2.1. ', RED),
    ('  - 3.2.2. ', ORANGE),
    ('  - 3.2.3. ', RED),
    ('  - 3.2.4. ', RED),
    ('  - 3.2.5. ', RED),
    ('  - 3.2.6. ', ORANGE),
    ('    - 3.2.1.3. ', RED),
    ('    - 3.2.1.4. ', RED),
    ('    - 3.2.3.2. ', RED),
    ('    - 3.2.3.4. ', RED),
    ('    - 3.2.3.5. ', ORANGE),
    ('    - 3.2.4.2. ', RED),
    ('    - 3.2.4.3. ', RED),
    ('    - 3.2.4.4. ', RED),
    ('    - 3.2.5.4. ', RED),
    ('    - 3.2.6.4. ', ORANGE),
    ('      - 3.2.4.6.1. ', ORANGE),
    # ── Section 5 ───────────────────────────────────────────────
    ('- 5.6. ', ORANGE),
    # ── Section 6 ───────────────────────────────────────────────
    ('  - 6.2.3. ', RED),
    ('  - 6.4.1. ', RED),
    # ── Section 8 ───────────────────────────────────────────────
    ('- 8.2. ', RED),
    ('- 8.3. ', YELLOW),
]

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Step 1: 기존 span 태그 제거 (중복 적용 방지)
content = re.sub(r'<span style="[^"]*">', '', content)
content = content.replace('</span>', '')

lines = content.splitlines(keepends=True)

# Step 2: 색상 태그 적용
new_lines = []
count = 0
for line in lines:
    matched = False
    for prefix, style in rules:
        if line.startswith(prefix):
            body = line[len(prefix):].rstrip('\n')
            new_lines.append(prefix + span(body, style) + '\n')
            matched = True
            count += 1
            break
    if not matched:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Done: {count} lines tagged")
