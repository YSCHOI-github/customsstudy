import re

file_path = '02_무역실무/50_핵심요약/00_무역실무마인드맵초안.md'

RED    = 'color:#e74c3c;font-weight:bold'
ORANGE = 'color:#e67e22;font-weight:bold'
YELLOW = 'color:#d4ac0d'

def span(content, style):
    return f'<span style="{style}">{content}</span>'

# 무역실무 MD 형식: - **1.1.** 텍스트 (bold 포함)
rules = [
    # ── Section headers (## level) ──────────────────────────────
    ('## 1. ', RED),
    ('## 2. ', RED),
    ('## 3. ', ORANGE),
    ('## 4. ', ORANGE),
    ('## 5. ', YELLOW),

    # ── Section 1: CISG + Incoterms ──────────────────────────────
    ('- **1.1.** ', RED),        # 계약 성립 절차
    ('- **1.2.** ', RED),        # 물품 계약적합성
    ('- **1.3.** ', RED),        # Incoterms 2020
    ('  - **1.1.1.** ', RED),    # 청약 요건 (CISG 제14조)
    ('  - **1.1.2.** ', RED),    # 승낙 (CISG 제18-22조)
    ('  - **1.2.1.** ', RED),    # 수량·품질·포장 적합성 (제35조)
    ('  - **1.2.2.** ', RED),    # 검사·부적합 통지 (제38·39조)
    ('  - **1.3.1.** ', RED),    # 인도·위험 이전
    ('  - **1.3.2.** ', RED),    # 운송·보험 계약 의무 (CIP↔CIF)
    ('  - **1.3.3.** ', ORANGE), # 통관 의무
    ('    - **1.1.2.2.** ', RED),  # 부가조건부 승낙 제19조
    ('    - **1.1.2.3.** ', RED),  # 지연된 승낙 제21조
    ('    - **1.3.2.2.** ', RED),  # CIP→ICC(A) vs CIF→ICC(C)

    # ── Section 2: UCP 600 ────────────────────────────────────────
    ('- **2.1.** ', RED),        # 신용장 기본원칙
    ('- **2.2.** ', ORANGE),     # 결제방식·은행 확약
    ('- **2.3.** ', RED),        # 서류심사 기준
    ('- **2.4.** ', RED),        # 불일치 서류 처리
    ('- **2.5.** ', ORANGE),     # 추심 (URC 522)
    ('  - **2.1.1.** ', RED),    # 독립성·추상성 (사기 예외 병기)
    ('  - **2.3.1.** ', RED),    # 5 banking days
    ('  - **2.3.2.** ', RED),    # 과부족 용인 10%·5%
    ('  - **2.3.3.** ', ORANGE), # 원본성·발행 요건
    ('  - **2.4.1.** ', RED),    # 불일치 통지 단일통지 원칙
    ('  - **2.4.2.** ', RED),    # 서류 처분 상태 4가지

    # ── Section 3: 운송 ────────────────────────────────────────────
    ('- **3.1.** ', ORANGE),     # 운송서류 수리 요건
    ('- **3.2.** ', RED),        # 운송인 책임 원칙
    ('- **3.3.** ', ORANGE),     # 클레임·제소 기한
    ('- **3.4.** ', ORANGE),     # Incoterms 운송 의무
    ('  - **3.1.1.** ', RED),    # B/L 심사
    ('  - **3.1.2.** ', ORANGE), # 복합운송서류
    ('  - **3.1.3.** ', ORANGE), # 항공운송서류
    ('  - **3.2.1.** ', RED),    # 몬트리올협약 (2021 50점 출제)
    ('  - **3.2.2.** ', ORANGE), # 함부르크 규칙

    # ── Section 4: 보험 ────────────────────────────────────────────
    ('- **4.1.** ', RED),        # MIA 기본 법리
    ('- **4.2.** ', RED),        # ICC 담보 범위·면책
    ('- **4.3.** ', YELLOW),     # 보험 책임 기간
    ('- **4.4.** ', YELLOW),     # 손해 유형·권리구제
    ('- **4.5.** ', ORANGE),     # 신용장 보험서류 (UCP 제28조)
    ('  - **4.1.1.** ', RED),    # 최대선의·고지의무
    ('  - **4.1.2.** ', ORANGE), # 피보험이익
    ('  - **4.1.3.** ', ORANGE), # 보험담보(Warranty)
    ('  - **4.2.1.** ', RED),    # ICC(A)/(B)/(C) 비교
    ('  - **4.2.2.** ', ORANGE), # 면책 위험

    # ── Section 5: 분쟁해결 ────────────────────────────────────────
    ('- **5.1.** ', ORANGE),     # 계약위반 구제 (CISG)
    ('- **5.2.** ', YELLOW),     # 뉴욕협약 중재
    ('  - **5.1.1.** ', RED),    # 본질적 계약위반 (제25조)
    ('  - **5.1.2.** ', ORANGE), # 매수인 구제수단
    ('  - **5.1.3.** ', ORANGE), # 매도인 구제수단
    ('  - **5.1.4.** ', ORANGE), # 손해배상·이행 정지
]

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 기존 span 제거
content = re.sub(r'<span style="[^"]*">', '', content)
content = content.replace('</span>', '')

lines = content.splitlines(keepends=True)

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
