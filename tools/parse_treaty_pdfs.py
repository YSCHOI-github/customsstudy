"""
parse_treaty_pdfs.py

무역실무 국제협약/협정 PDF에서 조문을 추출하여 협약별 JSON 파일로 저장.
일회성 변환 도구.

사용법:
    python tools/parse_treaty_pdfs.py --treaty ucp600
    python tools/parse_treaty_pdfs.py --all
    python tools/parse_treaty_pdfs.py --treaty ucp600 --dump
"""

import re
import json
import sys
import argparse
from pathlib import Path
from collections import Counter

import pdfplumber

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ('utf-8', 'utf8'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent.parent
PDF_DIR  = BASE_DIR / "02_무역실무" / "40_국내외법령"
OUT_DIR  = PDF_DIR / "parsed"

# 한국어 문자 범위 (제거용)
_KO_RE = re.compile(r'[가-힣ㄱ-ㅎㅏ-ㅣ　-〿一-鿿【】]+\s*')


def roman_to_int(s: str) -> int:
    vals = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}
    result, prev = 0, 0
    for ch in reversed(s.upper()):
        v = vals.get(ch, 0)
        result += v if v >= prev else -v
        prev = v
    return result


# ── 협약 설정 ────────────────────────────────────────────────────────────────
# bilingual=True: 영한 혼합 PDF → 한국어 문자 제거 후 영어 라인만 추출
# skip=True: PDF에 조문 없음 → 변환 건너뜀

TREATY_CONFIGS: dict[str, dict] = {
    "ucp600": {
        "pdf":             "UCP 600 Text.pdf",
        "json_key":        "UCP 600",
        "article_pattern": re.compile(r"^UCP 600 - Article\s+(\d+)\b"),
        "roman":           False,
        "min_content_len": 80,
    },
    "cisg": {
        "pdf":             "CISG.pdf",
        "json_key":        "CISG",
        "article_pattern": re.compile(r"^Article\s+(\d+)\b"),
        "roman":           False,
        "min_content_len": 80,
    },
    "newyork": {
        "pdf":             "new-york-convention-e.pdf",
        "json_key":        "뉴욕협약",
        "article_pattern": re.compile(r"^Article\s+([IVX]+)\b"),
        "roman":           True,
        "min_content_len": 80,
    },
    "montreal": {
        # PDF(Mtl99_EN.pdf)는 비준현황 표 파일 → 한국어 TXT로 대체
        "txt":             "몬트리올협약.txt",
        "json_key":        "몬트리올협약",
        # 한국어 조문 헤더: "제 1 조", "제17조" 등
        "article_pattern": re.compile(r"^제\s*(\d+)\s*조"),
        "roman":           False,
        "min_content_len": 30,
    },
    "mia": {
        "pdf":             "MIA1906.pdf",
        "json_key":        "MIA 1906",
        # UK 법률 형식: "55. Included losses." → 번호+공백+제목(마침표 종결)
        "article_pattern": re.compile(r"^(\d{1,2})\s+[A-Z][a-z].*\.\s*$"),
        "roman":           False,
        "min_content_len": 40,
    },
    "hamburg": {
        "pdf":             "hamburg_rules_e.pdf",
        "json_key":        "함부르크규칙",
        "article_pattern": re.compile(r"^Article\s+(\d+)\b"),
        "roman":           False,
        "min_content_len": 80,
    },
    "urc522": {
        "pdf":             "URC522.pdf",
        "json_key":        "URC 522",
        # URC 522 형식: "ARTICLE 1 APPLICATION OF URC 522" (모두 대문자)
        "article_pattern": re.compile(r"^ARTICLE\s+(\d+)\b"),
        "roman":           False,
        "min_content_len": 80,
    },
    "isbp": {
        "pdf":             "isbp-745.pdf",
        "json_key":        "ISBP 745",
        # ISBP 745 형식: "A1) Generally accepted..." (문자+숫자+닫기괄호)
        "article_pattern": re.compile(r"^([A-Z]\d+)\)"),
        "roman":           False,
        "min_content_len": 60,
    },
    "icc": {
        "md":              "ICC.md",
        "json_key":        "ICC",
        "article_pattern": re.compile(r"^(\d{1,2})\.\s"),
        "roman":           False,
        "min_content_len": 40,
        "multi_section":   True,
        "section_pattern": re.compile(r"^# Institute Cargo Clauses \(([ABC])\)"),
    },
    "hague": {
        "html":            "Hague Rules.html",
        "json_key":        "헤이그규칙",
        "article_pattern": re.compile(r"^Article\s+(\d+)\s*$"),
        "stop_pattern":    re.compile(r"^PROTOCOL OF SIGNATURE", re.IGNORECASE),
        "roman":           False,
        "min_content_len": 50,
    },
}


# ── 텍스트 추출 (PDF / TXT / MD) ────────────────────────────────────────────

def extract_raw_lines_from_txt(txt_path: Path) -> list[str]:
    """일반 텍스트 파일에서 줄 목록 반환 (빈 줄 제외)."""
    with open(txt_path, encoding='utf-8', errors='replace') as f:
        return [ln.strip() for ln in f if ln.strip()]


def extract_sections_from_md(md_path: Path, section_pat: re.Pattern) -> dict[str, list[str]]:
    """MD 파일에서 '---' 구분자로 섹션을 분리하여 {레이블: 라인목록} 반환.

    섹션 헤더 예: '# Institute Cargo Clauses (A)' → 레이블 'A'
    헤더 이후 빈 줄은 제외하고 조문 텍스트만 수집한다.
    """
    sections: dict[str, list[str]] = {}
    current_label: str | None = None
    current_lines: list[str] = []

    with open(md_path, encoding='utf-8') as f:
        for raw_line in f:
            line = raw_line.strip()
            if line == "---":
                if current_label:
                    sections[current_label] = current_lines
                current_label = None
                current_lines = []
                continue
            m = section_pat.match(line)
            if m:
                current_label = m.group(1)   # "A", "B", "C"
                current_lines = []
                continue
            if current_label and line:
                current_lines.append(line)

    # 마지막 섹션 저장
    if current_label and current_lines:
        sections[current_label] = current_lines

    return sections


def extract_raw_lines(pdf_path: Path) -> list[str]:
    lines: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped:
                        lines.append(stripped)
    return lines


def extract_bilingual_full_text(pdf_path: Path) -> str:
    """영한 혼합 PDF에서 한국어 문자를 제거한 전체 텍스트 반환.

    라인 단위가 아닌 전체 텍스트로 반환하여, 조문 헤더가 라인 중간에
    있어도 re.finditer()로 경계를 탐지할 수 있게 한다.
    """
    chunks: list[str] = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                chunks.append(text)
    full = "\n".join(chunks)
    # 한국어 문자 제거
    full = _KO_RE.sub(' ', full)
    # 연속 공백/줄바꿈 정리
    full = re.sub(r'[ \t]{2,}', ' ', full)
    full = re.sub(r'\n{3,}', '\n\n', full)
    return full


def extract_articles_from_html(html_path: Path, config: dict) -> list[dict]:
    """HTML 파일에서 조문 추출 (헤이그규칙 등 HTML 소스용)."""
    html = html_path.read_text(encoding='utf-8')

    for ent, ch in [('&quot;', '"'), ('&amp;', '&'), ('&nbsp;', ' '),
                    ('&gt;', '>'), ('&lt;', '<')]:
        html = html.replace(ent, ch)

    html = re.sub(r'</p>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    html = re.sub(r'<[^>]+>', '', html)

    lines = []
    for raw_line in html.splitlines():
        line = re.sub(r'[ \t]+', ' ', raw_line).strip()
        if line:
            lines.append(line)

    stop_pat = config.get("stop_pattern")
    if stop_pat:
        try:
            stop_idx = next(i for i, ln in enumerate(lines) if stop_pat.match(ln))
            lines = lines[:stop_idx]
        except StopIteration:
            pass

    return extract_articles(lines, config)


def remove_repeated_lines(lines: list[str], threshold: int = 5) -> list[str]:
    counts = Counter(lines)
    noise = {ln for ln, cnt in counts.items()
             if cnt >= threshold and len(ln) < 100}
    return [ln for ln in lines if ln not in noise]


# ── 조문 파싱 ────────────────────────────────────────────────────────────────

def extract_articles(lines: list[str], config: dict) -> list[dict]:
    """조문 경계 탐지 → [{"key": str, "content": str}] 리스트.

    목차 항목(연속 점 5개 이상)을 제거하고, 중복 key는 긴 쪽을 유지.
    """
    pat: re.Pattern = config["article_pattern"]
    roman: bool = config.get("roman", False)
    min_len: int = config.get("min_content_len", 80)

    raw: list[dict] = []
    current_key: str | None = None
    current_lines: list[str] = []

    for line in lines:
        m = pat.match(line)
        if m:
            if current_key is not None and current_lines:
                content = "\n".join(current_lines).strip()
                if len(content) >= min_len:
                    raw.append({"key": current_key, "content": content})
            art_num = m.group(1)
            current_key = str(roman_to_int(art_num)) if roman else art_num
            current_lines = [line]
        elif current_key is not None:
            current_lines.append(line)

    if current_key is not None and current_lines:
        content = "\n".join(current_lines).strip()
        if len(content) >= min_len:
            raw.append({"key": current_key, "content": content})

    # 목차 항목 제거 (연속 점 5개 이상)
    raw = [a for a in raw if not re.search(r'\.{5,}', a["content"])]

    # 중복 key: 내용이 긴 것 유지 (목차 vs 본문 중 본문 선택)
    by_key: dict[str, dict] = {}
    for art in raw:
        key = art["key"]
        if key not in by_key or len(art["content"]) > len(by_key[key]["content"]):
            by_key[key] = art

    def sort_key(a: dict) -> tuple:
        k = a["key"]
        m2 = re.match(r'^(\d+)', k)
        return (int(m2.group(1)), k) if m2 else (0, k)

    return sorted(by_key.values(), key=sort_key)


def extract_articles_from_fulltext(full_text: str, config: dict) -> list[dict]:
    """전체 텍스트에서 조문 경계 탐지 (영한 혼합 PDF용).

    라인 시작 앵커(^)를 제거하고 re.finditer()로 전체 텍스트를 스캔하여
    조문 헤더가 줄 중간에 있어도 올바르게 분리.
    """
    # bilingual config는 article_pattern이 ^ 앵커를 가지므로 제거
    raw_pat: re.Pattern = config["article_pattern"]
    pattern_str = raw_pat.pattern.lstrip('^')
    pat = re.compile(pattern_str)
    roman: bool = config.get("roman", False)
    min_len: int = config.get("min_content_len", 80)

    matches = list(pat.finditer(full_text))
    if not matches:
        return []

    raw: list[dict] = []
    for i, m in enumerate(matches):
        art_num = m.group(1)
        key = str(roman_to_int(art_num)) if roman else art_num
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        content = full_text[start:end].strip()
        content = re.sub(r'\n{3,}', '\n\n', content)
        if len(content) >= min_len:
            raw.append({"key": key, "content": content})

    # 목차 항목 제거 (연속 점 5개 이상)
    raw = [a for a in raw if not re.search(r'\.{5,}', a["content"][:200])]

    # 중복 key: 내용이 긴 것 유지
    by_key: dict[str, dict] = {}
    for art in raw:
        k = art["key"]
        if k not in by_key or len(art["content"]) > len(by_key[k]["content"]):
            by_key[k] = art

    def sort_key(a: dict) -> tuple:
        m2 = re.match(r'^(\d+)', a["key"])
        return (int(m2.group(1)), a["key"]) if m2 else (0, a["key"])

    return sorted(by_key.values(), key=sort_key)


# ── 메인 변환 ────────────────────────────────────────────────────────────────

def parse_treaty(name: str, dump: bool = False) -> None:
    if name not in TREATY_CONFIGS:
        print(f"[ERROR] 알 수 없는 협약: {name}")
        print(f"  지원: {', '.join(TREATY_CONFIGS)}")
        return

    cfg = TREATY_CONFIGS[name]

    if cfg.get("skip"):
        print(f"\n[{name}] SKIP: {cfg.get('skip_reason', '')}")
        return

    # ── MD 멀티섹션 소스 분기 (ICC A/B/C) ────────────────────────────────────
    if cfg.get("md") and cfg.get("multi_section"):
        md_path = PDF_DIR / cfg["md"]
        if not md_path.exists():
            print(f"\n[{name}] SKIP: MD 없음 ({md_path.name})")
            return

        print(f"\n[{name}] {cfg['md']} (마크다운 파일, 멀티섹션)")
        sections = extract_sections_from_md(md_path, cfg["section_pattern"])
        print(f"  섹션 수: {len(sections)} ({', '.join(sections.keys())})")

        if dump:
            for label, lines in sections.items():
                print(f"\n--- 섹션 ({label}) 처음 30줄 ---")
                for i, ln in enumerate(lines[:30], 1):
                    print(f"{i:4d}: {ln}")
            return

        out_data: dict = {cfg["json_key"]: {}}
        for label, lines in sections.items():
            articles = extract_articles(lines, cfg)
            print(f"  [ICC ({label})] 조문 수: {len(articles)}")
            if not articles:
                print(f"  [WARN] 섹션 {label}: 조문을 찾지 못했습니다.")
            out_data[cfg["json_key"]][f"ICC ({label})"] = {
                "type":      "treaty",
                "source_md": cfg["md"],
                "data":      articles,
            }

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"{name}.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
        print(f"  저장: {out_path.relative_to(BASE_DIR)}")
        return

    # ── HTML 소스 분기 ─────────────────────────────────────────────────────────
    if cfg.get("html"):
        html_path = PDF_DIR / cfg["html"]
        if not html_path.exists():
            print(f"\n[{name}] SKIP: HTML 없음 ({html_path.name})")
            return

        print(f"\n[{name}] {cfg['html']} (HTML 파일)")

        if dump:
            import html as _html_mod
            tmp = html_path.read_text(encoding='utf-8')
            for ent, ch in [('&quot;', '"'), ('&amp;', '&'), ('&nbsp;', ' '),
                             ('&gt;', '>'), ('&lt;', '<')]:
                tmp = tmp.replace(ent, ch)
            tmp = re.sub(r'</p>', '\n', tmp, flags=re.IGNORECASE)
            tmp = re.sub(r'<[^>]+>', '', tmp)
            preview = [re.sub(r'[ \t]+', ' ', ln).strip()
                       for ln in tmp.splitlines() if ln.strip()][:200]
            print(f"\n--- 추출 텍스트 (처음 200줄) ---")
            for i, ln in enumerate(preview, 1):
                print(f"{i:4d}: {ln}")
            return

        articles = extract_articles_from_html(html_path, cfg)
        print(f"  조문 수: {len(articles)}")

        if not articles:
            print("  [WARN] 조문을 찾지 못했습니다. --dump 로 원문 구조를 확인하세요.")
            return

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"{name}.json"
        out_data = {
            cfg["json_key"]: {
                "type":        "treaty",
                "source_html": cfg["html"],
                "data":        articles,
            }
        }
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
        print(f"  저장: {out_path.relative_to(BASE_DIR)}")
        s = articles[0]
        print(f"  샘플: [{s['key']}] {s['content'][:70]}...")
        return

    # ── TXT 소스 분기 ──────────────────────────────────────────────────────────
    if cfg.get("txt"):
        txt_path = PDF_DIR / cfg["txt"]
        if not txt_path.exists():
            print(f"\n[{name}] SKIP: TXT 없음 ({txt_path.name})")
            return

        print(f"\n[{name}] {cfg['txt']} (텍스트 파일)")
        lines = extract_raw_lines_from_txt(txt_path)
        print(f"  추출 라인: {len(lines)}줄")

        if dump:
            print(f"\n--- 추출 텍스트 (처음 200줄) ---")
            for i, ln in enumerate(lines[:200], 1):
                print(f"{i:4d}: {ln}")
            return

        articles = extract_articles(lines, cfg)
        print(f"  조문 수: {len(articles)}")

        if not articles:
            print("  [WARN] 조문을 찾지 못했습니다. --dump 로 원문 구조를 확인하세요.")
            return

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_path = OUT_DIR / f"{name}.json"
        out_data = {
            cfg["json_key"]: {
                "type":       "treaty",
                "source_txt": cfg["txt"],
                "data":       articles,
            }
        }
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(out_data, f, ensure_ascii=False, indent=2)
        print(f"  저장: {out_path.relative_to(BASE_DIR)}")
        s = articles[0]
        print(f"  샘플: [{s['key']}] {s['content'][:70]}...")
        return

    # ── PDF 소스 분기 ──────────────────────────────────────────────────────────
    pdf_path = PDF_DIR / cfg["pdf"]
    if not pdf_path.exists():
        print(f"\n[{name}] SKIP: PDF 없음 ({pdf_path.name})")
        return

    print(f"\n[{name}] {cfg['pdf']}")

    if cfg.get("bilingual"):
        # 영한 혼합 PDF: 전체 텍스트에서 패턴 검색 (라인 시작 무관)
        full_text = extract_bilingual_full_text(pdf_path)
        if dump:
            lines_preview = [ln for ln in full_text.splitlines() if ln.strip()][:200]
            print(f"\n--- 추출 텍스트 (처음 200줄) ---")
            for i, ln in enumerate(lines_preview, 1):
                print(f"{i:4d}: {ln[:100]}")
            return
        articles = extract_articles_from_fulltext(full_text, cfg)
    else:
        lines = extract_raw_lines(pdf_path)
        print(f"  추출 라인: {len(lines)}줄")
        lines = remove_repeated_lines(lines)
        print(f"  노이즈 제거 후: {len(lines)}줄")

        if dump:
            print(f"\n--- 추출 텍스트 (처음 200줄) ---")
            for i, ln in enumerate(lines[:200], 1):
                print(f"{i:4d}: {ln}")
            return

        articles = extract_articles(lines, cfg)
    print(f"  조문 수: {len(articles)}")

    if not articles:
        print("  [WARN] 조문을 찾지 못했습니다. --dump 로 원문 구조를 확인하세요.")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{name}.json"

    out_data = {
        cfg["json_key"]: {
            "type":       "treaty",
            "source_pdf": cfg["pdf"],
            "data":       articles,
        }
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(out_data, f, ensure_ascii=False, indent=2)

    print(f"  저장: {out_path.relative_to(BASE_DIR)}")
    s = articles[0]
    print(f"  샘플: [{s['key']}] {s['content'][:70]}...")


def main() -> None:
    parser = argparse.ArgumentParser(description='무역실무 협약 PDF → JSON 변환')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--treaty', metavar='NAME',
                       help=f'협약명 ({", ".join(TREATY_CONFIGS)})')
    group.add_argument('--all', action='store_true', help='전체 협약 변환')
    parser.add_argument('--dump', action='store_true',
                        help='JSON 미저장, 추출 텍스트 확인 (--treaty 전용)')
    args = parser.parse_args()

    if args.all:
        for name in TREATY_CONFIGS:
            parse_treaty(name)
    else:
        parse_treaty(args.treaty, dump=args.dump)


if __name__ == '__main__':
    main()
