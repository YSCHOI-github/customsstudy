"""
insert_treaty_articles.py

무역실무 단권화 MD 파일에 국제협약/협정 조문 원문(영어) 및 국내법령 조문 자동 삽입.
insert_law_articles.py 의 무역실무 대응 스크립트.

조문 탐지 방법 (두 가지 병행):
  1. [6] 관련 협약/법령 조문 매핑 테이블 — 가장 정확 (권장)
  2. 본문 스캔 — "CISG 제9조", "대외무역법 제2조" 형식의 명시적 참조 자동 탐지

[6] 관련 협약 조문 매핑 테이블 형식 (국제협약):
    ## [6] 관련 협약 조문 매핑
    | UCP 600 | CISG | 뉴욕협약 |
    |---|---|---|
    | 제2조, 제14조, 제15조 | 제9조 | — |

[6] 관련 법령 조문 매핑 테이블 형식 (국내법령):
    ## [6] 관련 법령 조문 매핑
    | 대외무역법 | 대외무역법 시행령 | 외국환거래법 |
    |---|---|---|
    | 제2조 | 제21조 | — |

사전 조건 (국제협약):
    python tools/parse_treaty_pdfs.py --all  # JSON 생성 먼저 실행

국내법령 JSON (이미 존재):
    02_무역실무/40_국내외법령/foreign_trade.json
    02_무역실무/40_국내외법령/foreign_exchange_investigation.json
    01_관세평가/40_국내외법령/customs_investigation.json

사용법:
    python tools/insert_treaty_articles.py "02_무역실무/10_단권화/03_02_신용장UCP600.md"
    python tools/insert_treaty_articles.py --all
"""

import re
import sys
import json
import argparse
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR   = Path(__file__).parent.parent
MD_DIR     = BASE_DIR / "02_무역실무" / "10_단권화"
PARSED_DIR = BASE_DIR / "02_무역실무" / "40_국내외법령" / "parsed"

APPENDIX_HEADER = "## [부록] 관련 협약 조문 원문"
APPENDIX_NOTE   = "> 이 섹션은 `insert_treaty_articles.py`에 의해 자동 생성되었습니다."

# 본문 스캔용: (탐지 패턴, json_key)
# group(1) = 조문 번호 키 (아라비아 숫자 또는 ISBP 코드)
TREATY_REF_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'UCP\s*600?\s*제(\d+)조'),              "UCP 600"),
    (re.compile(r'CISG\s+제(\d+)조'),                   "CISG"),
    (re.compile(r'뉴욕\s*협약\s+제(\d+)조'),            "뉴욕협약"),
    (re.compile(r'몬트리올\s*협약\s+제(\d+)조'),         "몬트리올협약"),
    (re.compile(r'MIA(?:\s*1906)?\s+제(\d+)조'),         "MIA 1906"),
    (re.compile(r'함부르크\s*규칙\s+제(\d+)조'),         "함부르크규칙"),
    (re.compile(r'URC\s*522\s+제(\d+)조'),              "URC 522"),
    (re.compile(r'ISBP\s*(?:745)?\s+([A-Z]\d+)'),       "ISBP 745"),
    (re.compile(r'ICC\s*A\s+제(\d+)조'),                "ICC A Clauses"),
]

# [6] 매핑 테이블 열 헤더 → json_key
MAPPING_HEADER_MAP = {
    "UCP 600":      "UCP 600",
    "UCP600":       "UCP 600",
    "CISG":         "CISG",
    "뉴욕협약":     "뉴욕협약",
    "뉴욕 협약":    "뉴욕협약",
    "몬트리올협약": "몬트리올협약",
    "몬트리올 협약":"몬트리올협약",
    "MIA 1906":     "MIA 1906",
    "MIA1906":      "MIA 1906",
    "MIA":          "MIA 1906",
    "함부르크규칙": "함부르크규칙",
    "URC 522":      "URC 522",
    "URC522":       "URC 522",
    "ISBP 745":     "ISBP 745",
    "ISBP745":      "ISBP 745",
    "ISBP":         "ISBP 745",
    "ICC A":        "ICC A Clauses",
    "ICC A Clauses":"ICC A Clauses",
}

# 부록 출력 순서
TREATY_ORDER = [
    "UCP 600", "CISG", "뉴욕협약", "몬트리올협약",
    "MIA 1906", "ICC A Clauses", "함부르크규칙", "URC 522", "ISBP 745",
]

_treaty_articles: dict[str, dict[str, str]] | None = None


# ── 국내법령 상수 ─────────────────────────────────────────────────────────────

DOMESTIC_LAW_JSON_FILES = [
    BASE_DIR / "02_무역실무" / "40_국내외법령" / "foreign_trade.json",
    BASE_DIR / "02_무역실무" / "40_국내외법령" / "foreign_exchange_investigation.json",
    BASE_DIR / "01_관세평가" / "40_국내외법령" / "customs_investigation.json",
]

DOMESTIC_SKIP_KEYS = {
    "대외무역법 (3단비교)", "외국환거래법 (3단비교)",
    "관세조사 운영에 관한 훈령", "관세법 (3단비교)",
}

DOMESTIC_LAW_ORDER = [
    "관세법", "관세법 시행령", "관세법 시행규칙", "관세평가 운영에 관한 고시",
    "대외무역법", "대외무역법 시행령", "대외무역관리규정",
    "외국환거래법", "외국환거래법 시행령", "외국환거래규정",
]

# [6] 관련 법령 조문 매핑 테이블 열 헤더 → law_key
DOMESTIC_MAPPING_HEADER_MAP: dict[str, str] = {
    "관세법":              "관세법",
    "관세법시행령":        "관세법 시행령",
    "관세법 시행령":       "관세법 시행령",
    "관세법시행규칙":      "관세법 시행규칙",
    "관세법 시행규칙":     "관세법 시행규칙",
    "고시":                "관세평가 운영에 관한 고시",
    "관세평가고시":        "관세평가 운영에 관한 고시",
    "대외무역법":          "대외무역법",
    "대외무역법시행령":    "대외무역법 시행령",
    "대외무역법 시행령":   "대외무역법 시행령",
    "대외무역관리규정":    "대외무역관리규정",
    "외국환거래법":        "외국환거래법",
    "외국환거래법시행령":  "외국환거래법 시행령",
    "외국환거래법 시행령": "외국환거래법 시행령",
    "외국환거래규정":      "외국환거래규정",
}

# 본문 스캔용 국내법령 패턴 (더 구체적인 패턴을 먼저 배치)
DOMESTIC_REF_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'관세법\s+시행규칙\s+(제\d+조(?:의\d+)?)'),       "관세법 시행규칙"),
    (re.compile(r'관세법\s+시행령\s+(제\d+조(?:의\d+)?)'),         "관세법 시행령"),
    (re.compile(r'관세법\s+(제\d+조(?:의\d+)?)'),                  "관세법"),
    (re.compile(r'대외무역법\s+시행령\s+(제\d+조(?:의\d+)?)'),     "대외무역법 시행령"),
    (re.compile(r'대외무역법\s+(제\d+조(?:의\d+)?)'),              "대외무역법"),
    (re.compile(r'대외무역관리규정\s+(제\d+조(?:의\d+)?)'),        "대외무역관리규정"),
    (re.compile(r'외국환거래법\s+시행령\s+(제\d+조(?:의\d+)?)'),   "외국환거래법 시행령"),
    (re.compile(r'외국환거래법\s+(제\d+조(?:의\d+)?)'),            "외국환거래법"),
    (re.compile(r'외국환거래규정\s+(제\d+-\d+조|제\d+조(?:의\d+)?)'), "외국환거래규정"),
]

DOMESTIC_APPENDIX_HEADER = "## [부록] 관련 법령 조문 원문"
DOMESTIC_APPENDIX_NOTE   = "> 이 섹션은 `insert_treaty_articles.py`에 의해 자동 생성되었습니다."

_domestic_articles: dict[str, dict[str, str]] | None = None

_ART_KEY_RE = re.compile(r'^제(\d+)조(의\d+)?')
_CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚'
_CHAP_CONTAMINATION_RE = re.compile(r'\n제\d+(?:장|절|관)\s[^\n]*')


# ── JSON 로드 ────────────────────────────────────────────────────────────────

def load_treaty_articles() -> dict[str, dict[str, str]]:
    """parsed/ 폴더의 모든 JSON 로드 → {json_key: {art_key: content}}."""
    global _treaty_articles
    if _treaty_articles is not None:
        return _treaty_articles

    result: dict[str, dict[str, str]] = {}

    if not PARSED_DIR.exists():
        print(f"  [WARN] parsed/ 폴더 없음: parse_treaty_pdfs.py --all 먼저 실행하세요")
        _treaty_articles = result
        return result

    for json_file in sorted(PARSED_DIR.glob("*.json")):
        with open(json_file, encoding='utf-8') as f:
            raw = json.load(f)
        for json_key, treaty_data in raw.items():
            if "data" in treaty_data:
                lookup = {item["key"]: item["content"] for item in treaty_data["data"]}
                result[json_key] = lookup
                print(f"  [JSON] {json_file.name}: {json_key} — {len(lookup)}개 조문")
            else:
                # Multi-section treaty (e.g., ICC A/B/C)
                for sub_key, sub_data in treaty_data.items():
                    if not isinstance(sub_data, dict) or "data" not in sub_data:
                        continue
                    m = re.match(r'^(.+?)\s*\(([A-Z])\)$', sub_key)
                    norm_key = f"{m.group(1)} {m.group(2)} Clauses" if m else sub_key
                    lookup = {item["key"]: item["content"] for item in sub_data["data"]}
                    result[norm_key] = lookup
                    print(f"  [JSON] {json_file.name}: {norm_key} — {len(lookup)}개 조문")

    _treaty_articles = result
    return result


def load_domestic_articles() -> dict[str, dict[str, str]]:
    """국내법령 JSON 로드 → {law_key: {art_key: 내용}}.

    조번호 형식별 art_key 추출:
      - 숫자형 ("1", "37"): 내용 첫 줄 ^제N조(의N)? 패턴
      - 문자형 ("제1조", "제1-1조"): 조번호 그대로 사용
    """
    global _domestic_articles
    if _domestic_articles is not None:
        return _domestic_articles

    result: dict[str, dict[str, str]] = {}

    for json_path in DOMESTIC_LAW_JSON_FILES:
        if not json_path.exists():
            print(f"  [WARN] 파일 없음: {json_path.name}")
            continue
        with open(json_path, encoding='utf-8') as f:
            raw = json.load(f)
        for law_key, law_data in raw.items():
            if law_key in DOMESTIC_SKIP_KEYS:
                continue
            if not isinstance(law_data, dict) or "data" not in law_data:
                continue
            lookup: dict[str, str] = {}
            for item in law_data["data"]:
                조번호 = str(item.get("조번호", "")).strip()
                내용   = item.get("내용", "")
                if 조번호.startswith("제"):
                    art_key = 조번호
                else:
                    m = _ART_KEY_RE.match(내용)
                    if m:
                        art_key = f"제{m.group(1)}조{m.group(2) or ''}"
                    else:
                        continue
                lookup[art_key] = 내용
            result[law_key] = lookup
            print(f"  [JSON] {json_path.name}: {law_key} — {len(lookup)}개 조문")

    _domestic_articles = result
    return result


# ── [6] 매핑 테이블 파싱 ─────────────────────────────────────────────────────

def parse_mapping_table(md_text: str) -> dict[str, set[str]]:
    """[6] 관련 협약 조문 매핑 테이블 → {json_key: {art_key}}.

    테이블 형식 (열 헤더 = 협약명):
        | UCP 600 | CISG |
        |---|---|
        | 제2조, 제14조 | 제9조 |
    """
    result: dict[str, set[str]] = {}

    m = re.search(r'##\s+\[6\]\s+관련 협약 조문 매핑', md_text, re.IGNORECASE)
    if not m:
        return result

    sec_start = m.start()
    nxt = re.search(r'\n##\s', md_text[sec_start + 1:])
    sec_end = sec_start + 1 + nxt.start() if nxt else len(md_text)
    section = md_text[sec_start:sec_end]

    art_pat = re.compile(r'제(\d+)조')
    isbp_pat = re.compile(r'([A-Z]\d+)')
    rows = [ln for ln in section.splitlines() if ln.strip().startswith('|')]

    if len(rows) < 2:
        return result

    header_cells = [c.strip() for c in rows[0].split('|') if c.strip()]
    col_to_key: dict[int, str] = {}
    for col_i, cell in enumerate(header_cells):
        for header_text, json_key in MAPPING_HEADER_MAP.items():
            if header_text in cell:
                col_to_key[col_i] = json_key
                break

    for row in rows[2:]:
        cells = [c.strip() for c in row.split('|') if c.strip() != '']
        for col_i, json_key in col_to_key.items():
            if col_i >= len(cells):
                continue
            cell = cells[col_i]
            if cell in ('—', '-', ''):
                continue
            if json_key == "ISBP 745":
                for code in isbp_pat.findall(cell):
                    result.setdefault(json_key, set()).add(code)
            else:
                for art_m in art_pat.finditer(cell):
                    result.setdefault(json_key, set()).add(art_m.group(1))

    return result


def parse_mapping_table_domestic(md_text: str) -> dict[str, set[str]]:
    """[6] 관련 법령 조문 매핑 테이블 → {law_key: {art_key}}.

    테이블 형식 (열 헤더 = 법령명):
        | 대외무역법 | 대외무역법 시행령 |
        |---|---|
        | 제2조 | 제21조 |
    """
    result: dict[str, set[str]] = {}

    m = re.search(r'##\s+\[6\]\s+관련 법령 조문 매핑', md_text, re.IGNORECASE)
    if not m:
        return result

    sec_start = m.start()
    nxt = re.search(r'\n##\s', md_text[sec_start + 1:])
    sec_end = sec_start + 1 + nxt.start() if nxt else len(md_text)
    section = md_text[sec_start:sec_end]

    art_pat    = re.compile(r'제(\d+)조(의\d+)?')
    fxreg_pat  = re.compile(r'제(\d+)-(\d+)조')
    rows = [ln for ln in section.splitlines() if ln.strip().startswith('|')]

    if len(rows) < 2:
        return result

    header_cells = [c.strip() for c in rows[0].split('|') if c.strip()]
    col_to_key: dict[int, str] = {}
    for col_i, cell in enumerate(header_cells):
        for header_text, law_key in DOMESTIC_MAPPING_HEADER_MAP.items():
            if header_text in cell:
                col_to_key[col_i] = law_key
                break

    for row in rows[2:]:
        cells = [c.strip() for c in row.split('|') if c.strip() != '']
        for col_i, law_key in col_to_key.items():
            if col_i >= len(cells):
                continue
            cell = cells[col_i]
            if cell in ('—', '-', ''):
                continue
            if law_key == "외국환거래규정":
                for fx_m in fxreg_pat.finditer(cell):
                    result.setdefault(law_key, set()).add(f"제{fx_m.group(1)}-{fx_m.group(2)}조")
                for art_m in art_pat.finditer(cell):
                    result.setdefault(law_key, set()).add(f"제{art_m.group(1)}조{art_m.group(2) or ''}")
            else:
                for art_m in art_pat.finditer(cell):
                    result.setdefault(law_key, set()).add(f"제{art_m.group(1)}조{art_m.group(2) or ''}")

    return result


# ── 조문 헤딩 & 정렬 ────────────────────────────────────────────────────────

def art_heading(json_key: str, art_key: str) -> str:
    if json_key == "MIA 1906":
        return f"{json_key} Section {art_key}"
    if json_key == "ISBP 745":
        return f"{json_key} {art_key}"
    return f"{json_key} Article {art_key}"


def art_sort_key(json_key: str, key: str) -> tuple:
    if json_key == "ISBP 745":
        m = re.match(r'([A-Z])(\d+)', key)
        return (m.group(1), int(m.group(2))) if m else (key, 0)
    try:
        return (int(key),)
    except ValueError:
        return (0,)


def dom_art_key_sort(key: str) -> tuple:
    """'제10조', '제10조의2', '제1-1조' 형태 정렬 키."""
    m = re.match(r'제(\d+)-(\d+)조', key)
    if m:
        return (int(m.group(1)), int(m.group(2)), 0)
    m = re.match(r'제(\d+)조(?:의(\d+))?', key)
    if m:
        return (int(m.group(1)), 0, int(m.group(2) or 0))
    return (0, 0, 0)


# ── 텍스트 포맷팅 ────────────────────────────────────────────────────────────

def format_treaty_text(text: str) -> str:
    # PDF 인코딩 오류 수정: 공백 대신 점(.)으로 인코딩된 경우
    # "Recognition.and.enforcement" → "Recognition and enforcement"
    text = re.sub(r'(?<=[a-zA-Z,;])\.(?=[a-zA-Z(])', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def format_domestic_law_text(text: str) -> str:
    """국내법령 조문 텍스트 포맷팅 (원문자·번호목록·장절 오염 처리)."""
    text = _CHAP_CONTAMINATION_RE.sub('', text).rstrip()
    text = re.sub(rf'\n([{_CIRCLED}])', r'\n\n\1', text)
    text = re.sub(rf'(?<=[^\n])([{_CIRCLED}])', r'\n\n\1', text)
    text = re.sub(r'\. (\d{1,2})\. ', r'.\n\1.  ', text)
    text = re.sub(r'([가-힣]) (\d{1,2})\. ', r'\1\n\2.  ', text)
    text = re.sub(r'\n([가나다라마바사아자차카타파하]\.)', r'\n\n\1', text)
    return text


# ── 본문 스캔 ────────────────────────────────────────────────────────────────

def find_code_blocks(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r'```[\s\S]*?```', text)]


def find_table_rows(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end())
            for m in re.finditer(r'^[ \t]*(?:>[ \t]*)*\|.+\|[ \t]*$', text, re.MULTILINE)]


def is_already_linked(body: str, pos: int) -> bool:
    before = body[max(0, pos - 200):pos]
    return before.rfind('[[') > before.rfind(']]')


def parse_body_treaties(body: str) -> dict[str, set[str]]:
    """본문에서 협약 조문 참조 탐지 → {json_key: {art_key}}."""
    result: dict[str, set[str]] = {}
    code_blocks = find_code_blocks(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    for pat, json_key in TREATY_REF_PATTERNS:
        for m in pat.finditer(body):
            if not in_code(m.start()):
                result.setdefault(json_key, set()).add(m.group(1))

    return result


def parse_body_domestic(body: str) -> dict[str, set[str]]:
    """본문에서 국내법령 조문 참조 탐지 → {law_key: {art_key}}."""
    result: dict[str, set[str]] = {}
    code_blocks = find_code_blocks(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    for pat, law_key in DOMESTIC_REF_PATTERNS:
        for m in pat.finditer(body):
            if not in_code(m.start()):
                result.setdefault(law_key, set()).add(m.group(1))

    return result


# ── 백링크 ──────────────────────────────────────────────────────────────────

def get_body_back_wikilink(body: str) -> str:
    m = re.search(r'^# (.+)$', body, re.MULTILINE)
    if not m:
        return ""
    return f"[[#{m.group(1).strip()}|↩ 본문으로 돌아가기]]"


# ── 부록 생성 ────────────────────────────────────────────────────────────────

def build_appendix(needed: dict[str, set[str]], back_wikilink: str) -> str:
    lines = ["\n\n---\n\n", f"{APPENDIX_HEADER}\n\n", f"{APPENDIX_NOTE}\n"]
    back_link = f"\n> {back_wikilink}\n" if back_wikilink else ""
    articles = load_treaty_articles()

    ordered = [k for k in TREATY_ORDER if k in needed] + \
              [k for k in needed if k not in TREATY_ORDER]

    for json_key in ordered:
        lookup = articles.get(json_key, {})
        sorted_keys = sorted(needed[json_key],
                             key=lambda k: art_sort_key(json_key, k))
        for art_key in sorted_keys:
            heading  = art_heading(json_key, art_key)
            raw      = lookup.get(art_key,
                                  f"*{heading}: 조문 없음 — `parse_treaty_pdfs.py`를 먼저 실행하세요.*")
            content  = format_treaty_text(raw)

            lines.append("\n---\n\n")
            lines.append(f"### {heading}\n\n")
            lines.append(f"{content}\n")
            lines.append(back_link)

    return "".join(lines)


def build_domestic_appendix(needed: dict[str, set[str]], back_wikilink: str) -> str:
    """국내법령 부록 섹션 생성."""
    if not needed:
        return ""
    lines = ["\n\n---\n\n", f"{DOMESTIC_APPENDIX_HEADER}\n\n", f"{DOMESTIC_APPENDIX_NOTE}\n"]
    back_link = f"\n> {back_wikilink}\n" if back_wikilink else ""
    articles = load_domestic_articles()

    ordered = [k for k in DOMESTIC_LAW_ORDER if k in needed] + \
              [k for k in needed if k not in DOMESTIC_LAW_ORDER]

    for law_key in ordered:
        lookup = articles.get(law_key, {})
        sorted_keys = sorted(needed[law_key], key=dom_art_key_sort)
        for art_key in sorted_keys:
            heading = f"{law_key} {art_key}"
            raw     = lookup.get(art_key, f"*{heading}: 조문 없음*")
            content = format_domestic_law_text(raw)
            lines.append("\n---\n\n")
            lines.append(f"### {heading}\n\n")
            lines.append(f"{content}\n")
            lines.append(back_link)

    return "".join(lines)


# ── 본문 링크 삽입 ───────────────────────────────────────────────────────────

def insert_links(body: str, needed: dict[str, set[str]]) -> str:
    code_blocks = find_code_blocks(body)
    table_rows  = find_table_rows(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    def in_table(pos: int) -> bool:
        return any(s <= pos < e for s, e in table_rows)

    replacements: list[tuple[int, int, str]] = []

    for pat, json_key in TREATY_REF_PATTERNS:
        if json_key not in needed:
            continue
        for m in pat.finditer(body):
            art_key = m.group(1)
            if art_key not in needed[json_key]:
                continue
            start, end = m.start(), m.end()
            # Absorb surrounding annotation brackets [text] to avoid [[[...]]]
            if start > 0 and body[start - 1] == '[' and end < len(body) and body[end] == ']':
                start -= 1
                end += 1
            if in_code(start) or is_already_linked(body, start):
                continue
            heading = art_heading(json_key, art_key)
            if in_table(start):
                linked = f"[[#{heading}\\|{m.group(0)}]]"
            else:
                linked = f"[[#{heading}|{m.group(0)}]]"
            replacements.append((start, end, linked))

    replacements.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, linked in replacements:
        if start >= last_end:
            deduped.append((start, end, linked))
            last_end = end

    result = body
    for start, end, linked in sorted(deduped, key=lambda x: -x[0]):
        result = result[:start] + linked + result[end:]

    return result


def insert_domestic_links(body: str, needed: dict[str, set[str]]) -> str:
    """국내법령 조문 참조에 Obsidian 위키링크 삽입."""
    if not needed:
        return body

    code_blocks = find_code_blocks(body)
    table_rows  = find_table_rows(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    def in_table(pos: int) -> bool:
        return any(s <= pos < e for s, e in table_rows)

    replacements: list[tuple[int, int, str]] = []

    for pat, law_key in DOMESTIC_REF_PATTERNS:
        if law_key not in needed:
            continue
        for m in pat.finditer(body):
            art_key = m.group(1)
            if art_key not in needed[law_key]:
                continue
            start, end = m.start(), m.end()
            if in_code(start) or is_already_linked(body, start):
                continue
            heading = f"{law_key} {art_key}"
            if in_table(start):
                linked = f"[[#{heading}]]"
            else:
                linked = f"[[#{heading}|{m.group(0)}]]"
            replacements.append((start, end, linked))

    replacements.sort(key=lambda x: x[0])
    deduped: list[tuple[int, int, str]] = []
    last_end = -1
    for start, end, linked in replacements:
        if start >= last_end:
            deduped.append((start, end, linked))
            last_end = end

    result = body
    for start, end, linked in sorted(deduped, key=lambda x: -x[0]):
        result = result[:start] + linked + result[end:]

    return result


# ── 메인 처리 ────────────────────────────────────────────────────────────────

_LINK_CLEANUP_RE = re.compile(
    r'\[\[#[^\|\]]+\|((?:UCP|CISG|뉴욕|몬트리올|MIA|함부르크|URC|ISBP|ICC\s*A)[^\]]*)\]\]'
)
_DOMESTIC_LINK_CLEANUP_RE = re.compile(
    r'\[\[#[^\|\]]+\|((?:관세법|대외무역법|대외무역관리규정|외국환거래법|외국환거래규정)[^\]]*)\]\]'
)
_DOMESTIC_LINK_SHORT_RE = re.compile(
    r'\[\[#((?:관세법|대외무역법|대외무역관리규정|외국환거래법|외국환거래규정)\s+제[^\]]*)\]\]'
)


def process_file(md_path: Path) -> None:
    print(f"\n처리 중: {md_path.name}")
    original = md_path.read_text(encoding='utf-8')

    # 기존 부록 제거 (협약 부록이 법령 부록보다 앞에 위치하므로 먼저 체크)
    stripped = False
    for marker in [f"\n{APPENDIX_HEADER}", APPENDIX_HEADER]:
        idx = original.find(marker)
        if idx != -1:
            original = original[:idx].rstrip()
            stripped = True
            break
    if not stripped:
        for marker in [f"\n{DOMESTIC_APPENDIX_HEADER}", DOMESTIC_APPENDIX_HEADER]:
            idx = original.find(marker)
            if idx != -1:
                original = original[:idx].rstrip()
                break

    # 기존 위키링크 제거 (재처리 지원)
    original = _LINK_CLEANUP_RE.sub(r'\1', original)
    original = _DOMESTIC_LINK_CLEANUP_RE.sub(r'\1', original)
    original = _DOMESTIC_LINK_SHORT_RE.sub(r'\1', original)

    # ── 국제협약 파이프라인 ──
    needed_table = parse_mapping_table(original)
    needed_body  = parse_body_treaties(original)
    needed: dict[str, set[str]] = {}
    for key in set(needed_table) | set(needed_body):
        needed[key] = needed_table.get(key, set()) | needed_body.get(key, set())

    if needed:
        src = []
        if needed_table:
            src.append(f"매핑테이블({', '.join(needed_table)})")
        if needed_body:
            src.append(f"본문스캔({', '.join(needed_body)})")
        print(f"  [협약] {src}")
        for k, v in needed.items():
            print(f"         {k}: {sorted(v)}")
    else:
        print("  [협약] 참조 없음")

    # ── 국내법령 파이프라인 ──
    needed_dom_table = parse_mapping_table_domestic(original)
    needed_dom_body  = parse_body_domestic(original)
    needed_dom: dict[str, set[str]] = {}
    for key in set(needed_dom_table) | set(needed_dom_body):
        needed_dom[key] = needed_dom_table.get(key, set()) | needed_dom_body.get(key, set())

    if needed_dom:
        src_dom = []
        if needed_dom_table:
            src_dom.append(f"매핑테이블({', '.join(needed_dom_table)})")
        if needed_dom_body:
            src_dom.append(f"본문스캔({', '.join(needed_dom_body)})")
        print(f"  [법령] {src_dom}")
        for k, v in needed_dom.items():
            print(f"         {k}: {sorted(v, key=dom_art_key_sort)}")
    else:
        print("  [법령] 참조 없음")

    if not needed and not needed_dom:
        print("  [SKIP] 협약·법령 조문 참조 없음")
        return

    back_wikilink = get_body_back_wikilink(original)

    appendix     = build_appendix(needed, back_wikilink) if needed else ""
    dom_appendix = build_domestic_appendix(needed_dom, back_wikilink)

    body_linked = insert_links(original, needed)
    body_linked = insert_domestic_links(body_linked, needed_dom)

    md_path.write_text(body_linked + appendix + dom_appendix, encoding='utf-8')
    print(f"  [완료] {md_path.name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description='무역실무 단권화 MD 파일에 협약·법령 조문 원문 삽입')
    parser.add_argument('file', nargs='?', help='처리할 MD 파일 경로')
    parser.add_argument('--all', action='store_true', help='단권화 폴더 전체 처리')
    args = parser.parse_args()

    if args.all:
        md_files = sorted(f for f in MD_DIR.glob('*.md')
                          if not f.name.startswith('00_'))
        print(f"전체 처리: {len(md_files)}개 파일")
        for f in md_files:
            process_file(f)
    elif args.file:
        process_file(Path(args.file).resolve())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
