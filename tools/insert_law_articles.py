"""
insert_law_articles.py  (v3 — 조의N 지원)

변경 사항:
  1. PDF 파싱 제거 → customs_investigation.json 직접 사용
  2. <a id> 태그 제거 → 헤딩 앵커만 사용 (Obsidian 호환)
  3. 각 조문 끝에 본문 복귀 백링크 추가 (방안 A)
  4. 조의N 지원: 조번호 키를 내용 필드에서 추출, set[str] 사용

사용법:
    python tools/insert_law_articles.py "01_관세평가/10_단권화/04_03_처분사용제한.md"
    python tools/insert_law_articles.py --all
"""

import re
import json
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
JSON_PATH = BASE_DIR / "01_관세평가" / "40_국내외법령" / "customs_investigation.json"
MD_DIR    = BASE_DIR / "01_관세평가" / "10_단권화"

# MD 키워드 → JSON 최상위 키
JSON_KEY_MAP = {
    "관세법":   "관세법",
    "시행령":   "관세법 시행령",
    "시행규칙": "관세법 시행규칙",
    "고시":     "관세평가 운영에 관한 고시",
}

# 매핑 테이블 열 헤더 → 법령 타입
HEADER_TO_LAW = {
    "관세법":   "관세법",
    "시행령":   "시행령",
    "시행규칙": "시행규칙",
    "고시":     "고시",
}

APPENDIX_HEADER = "## [부록] 관련 조문 원문"
APPENDIX_NOTE   = "> 이 섹션은 `insert_law_articles.py`에 의해 자동 생성되었습니다."

# 내용 필드 첫 줄에서 조문 키 추출: "제37조의2(...)" → "제37조의2"
_ART_KEY_RE = re.compile(r'^제(\d+)조(의\d+)?')

_json_articles: dict[str, dict[str, str]] | None = None


# ── 정렬 헬퍼 ────────────────────────────────────────────────────────────────

def art_key_sort(key: str) -> tuple[int, int]:
    """'제10조의2' 같은 키를 숫자 순으로 정렬하기 위한 키 함수."""
    m = re.match(r'제(\d+)조(?:의(\d+))?', key)
    if m:
        return (int(m.group(1)), int(m.group(2) or 0))
    return (0, 0)


# ── JSON 조회 ────────────────────────────────────────────────────────────────

def load_json_articles() -> dict[str, dict[str, str]]:
    """JSON 파일 1회 로드 → {md_law_type: {art_key: 내용}} 캐시.

    art_key 형식: '제37조' 또는 '제37조의2'  (내용 필드 첫 줄에서 추출)
    조번호 필드는 '37'로 중복 저장되므로 사용하지 않음.
    """
    global _json_articles
    if _json_articles is not None:
        return _json_articles

    print(f"  [JSON] 로드: {JSON_PATH.name}")
    with open(JSON_PATH, encoding='utf-8') as f:
        raw = json.load(f)

    result: dict[str, dict[str, str]] = {}
    for md_key, json_key in JSON_KEY_MAP.items():
        if json_key not in raw:
            print(f"  [WARN] JSON에 키 없음: {json_key}")
            result[md_key] = {}
            continue
        lookup: dict[str, str] = {}
        for item in raw[json_key]["data"]:
            content = item["내용"]
            m = _ART_KEY_RE.match(content)
            if m:
                art_key = f"제{m.group(1)}조{m.group(2) or ''}"
            else:
                art_key = item["조번호"]  # fallback
            lookup[art_key] = content
        result[md_key] = lookup
        print(f"         {md_key}: {len(lookup)}개 조문")

    _json_articles = result
    return result


_CIRCLED = '①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚'

# 스크래핑 오염: 조문 끝에 혼입된 장·절·관 제목 (\n제6장 ... 패턴)
_CHAP_CONTAMINATION_RE = re.compile(r'\n제\d+(?:장|절|관)\s[^\n]*')

def format_article_text(text: str) -> str:
    """JSON 조문 텍스트를 Obsidian 마크다운에 맞게 포맷팅.

    관세법·시행령·시행규칙: 이미 \\n이 있으므로 간격만 조정.
    고시: \\n이 없으므로 ①②③, 1. 2. 앞에 \\n 삽입.
    """
    # 스크래핑 오염 제거 (장·절·관 제목이 조문 끝에 혼입된 경우)
    text = _CHAP_CONTAMINATION_RE.sub('', text).rstrip()

    # 원문자 앞 빈 줄: 이미 \n이 있으면 \n\n으로 확장
    text = re.sub(rf'\n([{_CIRCLED}])', r'\n\n\1', text)
    # 원문자 앞 빈 줄: \n 없이 텍스트 중간에 등장하는 경우 (고시 등)
    text = re.sub(rf'(?<=[^\n])([{_CIRCLED}])', r'\n\n\1', text)

    # 번호 목록 분리 (고시 줄글 내 목록 항목 → 개별 줄)
    # 관세법은 이미 \n1.  형식이므로 영향 없음
    # 케이스 A: 이전 항목이 마침표로 끝나는 경우 ". 3. "
    text = re.sub(r'\. (\d{1,2})\. ', r'.\n\1.  ', text)
    # 케이스 B: 이전 항목이 한글로 끝나는 경우 "경우 5. "
    text = re.sub(r'([가-힣]) (\d{1,2})\. ', r'\1\n\2.  ', text)

    # 가나다 목록 앞 빈 줄 (이미 \n이 있는 경우만)
    text = re.sub(r'\n([가나다라마바사아자차카타파하]\.)', r'\n\n\1', text)

    return text


def get_article_text(law_type: str, art_key: str) -> str:
    """법령 타입·조문 키로 조문 텍스트 반환. art_key: '제37조' 또는 '제37조의2'."""
    articles = load_json_articles()
    lookup = articles.get(law_type, {})
    raw = lookup.get(art_key, f"*{art_key}를 찾을 수 없습니다*")
    return format_article_text(raw)


# ── 매핑 테이블 파싱 ─────────────────────────────────────────────────────────

def parse_mapping_table(md_text: str) -> dict[str, set[str]]:
    """[6] 관련 법령 조문 매핑 테이블 → {법령타입: {art_key}} (열 헤더 기반)."""
    result: dict[str, set[str]] = {}

    m = re.search(r'##\s+\[6\]\s+관련 법령 조문 매핑', md_text, re.IGNORECASE)
    if not m:
        return result

    sec_start = m.start()
    nxt = re.search(r'\n##\s', md_text[sec_start + 1:])
    sec_end = sec_start + 1 + nxt.start() if nxt else len(md_text)
    section = md_text[sec_start:sec_end]

    # 조의N 포함 패턴
    art_num_pat = re.compile(r'제(\d+)조(의\d+)?')
    rows = [ln for ln in section.splitlines() if ln.startswith('|')]

    if len(rows) < 2:
        return result

    header_cells = [c.strip() for c in rows[0].split('|') if c.strip()]
    col_to_law: dict[int, str] = {}
    for col_i, cell in enumerate(header_cells):
        for header_key, law_type in HEADER_TO_LAW.items():
            if header_key in cell:
                col_to_law[col_i] = law_type
                break

    for row in rows[2:]:
        cells = [c for c in (c.strip() for c in row.split('|')) if c != '']
        for col_i, law_type in col_to_law.items():
            if col_i == 0 or col_i >= len(cells):
                continue
            cell = cells[col_i]
            if cell in ('—', '-', ''):
                continue
            for am in art_num_pat.finditer(cell):
                art_key = f"제{am.group(1)}조{am.group(2) or ''}"
                result.setdefault(law_type, set()).add(art_key)

    return result


# ── 본문 직접 스캔 ──────────────────────────────────────────────────────────

def parse_body_articles(body: str) -> dict[str, set[str]]:
    """본문 텍스트에서 직접 법령 조문 참조 탐색 → {법령타입: {art_key}}."""
    result: dict[str, set[str]] = {}
    code_blocks = find_code_blocks(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    patterns = [
        (re.compile(r'관세법\s+(제\d+조(?:의\d+)?)'),   "관세법"),
        (re.compile(r'시행령\s+(제\d+조(?:의\d+)?)'),    "시행령"),
        (re.compile(r'시행규칙\s+(제\d+조(?:의\d+)?)'),  "시행규칙"),
        (re.compile(r'고시\s+(제\d+조(?:의\d+)?)'),      "고시"),
    ]
    for pat, law_type in patterns:
        for m in pat.finditer(body):
            if not in_code(m.start()):
                result.setdefault(law_type, set()).add(m.group(1))
    return result


# ── Obsidian 위키링크 생성 ───────────────────────────────────────────────────

def get_body_back_wikilink(body: str) -> str:
    """문서 # 제목 헤딩의 Obsidian 위키링크 반환 (백링크용)."""
    m = re.search(r'^# (.+)$', body, re.MULTILINE)
    if not m:
        return ""
    heading = m.group(1).strip()
    return f"[[#{heading}|↩ 본문으로 돌아가기]]"


# ── 부록 섹션 생성 ───────────────────────────────────────────────────────────

def build_appendix(needed: dict[str, set[str]], back_wikilink: str) -> str:
    """부록 텍스트 생성 (Obsidian 위키링크 방식)."""
    lines = ["\n\n---\n\n", f"{APPENDIX_HEADER}\n\n", f"{APPENDIX_NOTE}\n"]
    law_order = ["관세법", "시행령", "시행규칙", "고시"]
    back_link = f"\n> {back_wikilink}\n" if back_wikilink else ""

    for law_type in law_order:
        if law_type not in needed:
            continue
        for art_key in sorted(needed[law_type], key=art_key_sort):
            text = get_article_text(law_type, art_key)
            lines.append(f"\n---\n\n")
            lines.append(f"### {law_type} {art_key}\n\n")  # e.g. "### 관세법 제37조의2"
            lines.append(f"{text}\n")
            lines.append(back_link)

    return "".join(lines)


# ── 본문 링크 교체 ───────────────────────────────────────────────────────────

def find_code_blocks(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in re.finditer(r'```[\s\S]*?```', text)]


def find_table_rows(text: str) -> list[tuple[int, int]]:
    """마크다운 테이블 행 위치 반환. 테이블 내 wikilink | 가 컬럼 구분자로 파싱되는 문제 방지용."""
    return [(m.start(), m.end()) for m in re.finditer(r'^[ \t]*\|.+\|[ \t]*$', text, re.MULTILINE)]


def is_already_linked(body: str, pos: int) -> bool:
    before = body[max(0, pos - 200):pos]
    return before.rfind('[') > before.rfind(']')


def insert_links(body: str, needed: dict[str, set[str]]) -> str:
    """조문 참조에 내부 앵커 링크 삽입 (조의N 포함).
    테이블 행 내부는 제외: wikilink의 | 가 테이블 컬럼 구분자로 파싱되는 문제 방지.
    """
    code_blocks = find_code_blocks(body)
    table_rows  = find_table_rows(body)

    def in_code(pos: int) -> bool:
        return any(s <= pos < e for s, e in code_blocks)

    def in_table(pos: int) -> bool:
        return any(s <= pos < e for s, e in table_rows)

    law_patterns = [
        (re.compile(r'(관세법)\s+(제\d+조(?:의\d+)?)'),   "관세법"),
        (re.compile(r'(시행령)\s+(제\d+조(?:의\d+)?)'),   "시행령"),
        (re.compile(r'(시행규칙)\s+(제\d+조(?:의\d+)?)'), "시행규칙"),
        (re.compile(r'(고시)\s+(제\d+조(?:의\d+)?)'),     "고시"),
    ]

    replacements: list[tuple[int, int, str]] = []
    for pat, law_type in law_patterns:
        if law_type not in needed:
            continue
        for m in pat.finditer(body):
            art_key = m.group(2)  # "제37조" 또는 "제37조의2"
            if art_key not in needed[law_type]:
                continue
            if in_code(m.start()) or is_already_linked(body, m.start()):
                continue
            heading = f"{law_type} {art_key}"  # "관세법 제37조의2"
            if in_table(m.start()):
                # 테이블 행: | 없는 단축 형식 (Obsidian은 heading 텍스트로 표시)
                linked = f"[[#{heading}]]"
            else:
                linked = f"[[#{heading}|{m.group(0)}]]"
            replacements.append((m.start(), m.end(), linked))

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

def process_file(md_path: Path) -> None:
    print(f"\n처리 중: {md_path.name}")
    original = md_path.read_text(encoding='utf-8')

    # 기존 부록 제거
    for marker in [f"\n{APPENDIX_HEADER}", APPENDIX_HEADER]:
        idx = original.find(marker)
        if idx != -1:
            original = original[:idx].rstrip()
            break

    # 기존 내부 링크 제거 (markdown 형식 + wikilink 형식 모두)
    original = re.sub(
        r'\[((관세법|시행령|시행규칙|고시)\s+제\d+조[^\]]*)\]\(#[^)]+\)',
        r'\1', original
    )
    original = re.sub(
        r'\[\[#[^\|]+\|((관세법|시행령|시행규칙|고시)\s+제\d+조[^\]]*)\]\]',
        r'\1', original
    )
    # 테이블 행에 삽입된 단축 형식 [[#관세법 제31조]] 제거
    original = re.sub(
        r'\[\[#((관세법|시행령|시행규칙|고시)\s+제\d+조(?:의\d+)?)\]\]',
        r'\1', original
    )

    # Step 1: 조문 탐색 — 매핑 테이블 + 본문 직접 스캔 (union)
    needed_table = parse_mapping_table(original)
    needed_body  = parse_body_articles(original)
    needed: dict[str, set[str]] = {}
    for law_type in set(needed_table) | set(needed_body):
        needed[law_type] = needed_table.get(law_type, set()) | needed_body.get(law_type, set())
    if not needed:
        print("  [SKIP] 본문에 법령 조문 참조 없음")
        return
    print(f"  [조문] {{{', '.join(f'{k}: {sorted(v, key=art_key_sort)}' for k, v in needed.items())}}}")

    # Step 2: 백링크 위키링크 생성
    back_wikilink = get_body_back_wikilink(original)
    print("  [backlink] ok" if back_wikilink else "  [backlink] none")

    # Step 3: 부록 생성
    appendix = build_appendix(needed, back_wikilink)

    # Step 4: 본문 링크 삽입
    body_linked = insert_links(original, needed)

    # Step 5: 저장
    md_path.write_text(body_linked + appendix, encoding='utf-8')
    print(f"  [완료] {md_path.name}")


def main():
    parser = argparse.ArgumentParser(description='MD 파일에 관세법 조문 원문 삽입 (Obsidian 최적화)')
    parser.add_argument('file', nargs='?', help='처리할 MD 파일 경로')
    parser.add_argument('--all', action='store_true', help='단권화 폴더 전체 처리')
    args = parser.parse_args()

    if args.all:
        md_files = sorted(MD_DIR.glob('*.md'))
        print(f"전체 처리: {len(md_files)}개 파일")
        for f in md_files:
            process_file(f)
    elif args.file:
        process_file(Path(args.file).resolve())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
