"""
parse_korean_laws.py

한국 국내법 PDF를 조문 단위 JSON으로 변환.
파싱 로직은 kcs_law_chatbot/pdf_txt_json.py + lawapi.py에서 발췌 (외부 의존 없음).

사용법:
    # 등록된 법령 변환
    python tools/parse_korean_laws.py --law 중재법
    python tools/parse_korean_laws.py --all
    python tools/parse_korean_laws.py --law 중재법 --dump

    # 임의 PDF 직접 변환 (등록 불필요)
    python tools/parse_korean_laws.py --pdf "02_무역실무/40_국내외법령/중재법(...).pdf"
    python tools/parse_korean_laws.py --pdf "path/to/법령.pdf" --dump

    # 미변환 PDF 목록 조회
    python tools/parse_korean_laws.py --list
"""

import re
import json
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from pdfminer.high_level import extract_text

BASE_DIR = Path(__file__).parent.parent

_FOOTER_RE = re.compile(r'법제처\s{2,}[\d]+\s{2,}국가법령정보센터')

# 사전 등록 법령 (--law / --all 용)
LAW_CONFIGS: dict[str, dict] = {
    "중재법": {
        "pdf":       BASE_DIR / "02_무역실무" / "40_국내외법령" / "중재법(법률)(제21065호)(20251001).pdf",
        "json_key":  "중재법",
        "out_file":  BASE_DIR / "02_무역실무" / "40_국내외법령" / "중재법.json",
        "law_title": "중재법",
    },
}

# 법령 PDF가 있는 디렉토리 (--list 스캔 대상)
LAW_DIRS = [
    BASE_DIR / "01_관세평가" / "40_국내외법령",
    BASE_DIR / "02_무역실무" / "40_국내외법령",
]

# ── 파싱 패턴 ─────────────────────────────────────────────────────────────────

_CHAPTER_PATTERN    = re.compile(r"^제\s*[\d가-힣]+\s*장")
_SECTION_PATTERN    = re.compile(r"^제\s*[\d가-힣]+\s*절")
_SUBSECTION_PATTERN = re.compile(r"^제\s*[\d가-힣]+\s*관")
_ARTICLE_PATTERN    = re.compile(
    r"제\s*(?P<number>[\d]+(?:-[\d]+)?(?:의[\d]+)*)\s*조(?:의(?P<sub>[\d]+))?"
    r"\s*\((?P<title>[^)]+)\)(?P<rest>.*)"
)
_ANNEX_PATTERN = re.compile(r"^\s*[【\[]?\s*부\s*칙\s*[】\]]?")


# ── lawapi.py 독립 함수 발췌 ──────────────────────────────────────────────────

def _extract_structure_title(content: str) -> str:
    content_cleaned = re.sub(r'<[^>]*>', '', content).strip()
    for pattern in [
        r'제\d+장(?:의\d+)?\s+(.+)',
        r'제\d+절(?:의\d+)?\s+(.+)',
        r'제\d+관(?:의\d+)?\s+(.+)',
    ]:
        m = re.search(pattern, content_cleaned)
        if m:
            return m.group(1).strip()
    return content_cleaned


def _combine_structure_titles(jang: str, jeol: str, gwan: str, title: str) -> str:
    parts = [p for p in [jang, jeol, gwan, title] if p]
    return ", ".join(parts)


# ── 조문 버퍼 ─────────────────────────────────────────────────────────────────

@dataclass
class _ArticleBuffer:
    number: str
    title:  str
    lines:  List[str] = field(default_factory=list)

    def add(self, text: str) -> None:
        self.lines.append(text)

    def to_dict(self) -> dict:
        return {
            "조번호": self.number,
            "제목":   self.title,
            "내용":   "\n".join(self.lines).strip(),
        }


# ── 파싱 로직 (pdf_txt_json.py 발췌) ─────────────────────────────────────────

def _is_sentence_title(title: str) -> bool:
    endings = [
        '한다', '하여야', '해야', '된다', '받는다', '따른다',
        '의한다', '정한다', '본다', '처리한다', '관리한다',
        '이다', '것이다', '않는다', '같다', '다르다',
    ]
    return any(title.strip().endswith(e) for e in endings)


def _is_article_reference(m, _line: str) -> bool:
    rest = m.group("rest").strip()
    list_pats = [r'^\s*및\s*', r'^\s*,\s*', r'^\s*또는\s*', r'^\s*내지\s*',
                 r'^\s*부터\s*', r'^\s*까지\s*', r'^\s*ㆍ\s*', r'^\s*~\s*']
    conn_pats = [r'^\s*의\s*규정', r'^\s*에\s*따라', r'^\s*에\s*의하여',
                 r'^\s*을\s*준용', r'^\s*를\s*준용', r'^\s*에\s*의한',
                 r'^\s*에\s*규정', r'^\s*의\s*개정', r'^\s*에\s*해당',
                 r'^\s*에\s*따른', r'^\s*을\s*적용', r'^\s*를\s*적용',
                 r'^\s*의\s*적용', r'^\s*에서\s*정한',
                 r'^\s*의\s+', r'^\s*을\s+', r'^\s*를\s+',
                 r'^\s*에\s+', r'^\s*에서\s+']
    for p in list_pats + conn_pats:
        if re.search(p, rest):
            return True
    if re.search(r'^\s*제\s*\d+\s*[항호]', rest):
        return True
    return False


def _normalize_number(raw: str) -> str:
    return raw.replace(" ", "").lstrip("0") or "0"


def _is_noise_line(line: str, law_title: str = "") -> bool:
    """PDF 헤더/푸터 및 단독 법령명 줄 필터링."""
    if _FOOTER_RE.search(line):
        return True
    if law_title and line == law_title:
        return True
    return False


def parse_text(text: str, law_title: str = "") -> List[dict]:
    jang = jeol = gwan = ""
    articles: List[dict] = []
    cur: Optional[_ArticleBuffer] = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            if cur:
                cur.add("")
            continue

        if _is_noise_line(line, law_title):
            continue

        if _ANNEX_PATTERN.match(line):
            if cur:
                articles.append(cur.to_dict())
            break

        if _CHAPTER_PATTERN.match(line):
            if cur:
                articles.append(cur.to_dict())
                cur = None
            jang = _extract_structure_title(line)
            jeol = gwan = ""
            continue

        if _SECTION_PATTERN.match(line):
            if cur:
                articles.append(cur.to_dict())
                cur = None
            jeol = _extract_structure_title(line)
            gwan = ""
            continue

        if _SUBSECTION_PATTERN.match(line):
            if cur:
                articles.append(cur.to_dict())
                cur = None
            gwan = _extract_structure_title(line)
            continue

        am = _ARTICLE_PATTERN.match(line)
        if am:
            rest = am.group("rest").strip()
            prefix = rest.split("(", 1)[0].strip()
            if prefix.startswith("제") and any(mk in prefix for mk in ("항", "호", "목")):
                if cur:
                    cur.add(line)
                continue

            title = am.group("title").strip()
            if _is_sentence_title(title) or _is_article_reference(am, line):
                if cur:
                    cur.add(line)
                continue

            number = _normalize_number(am.group("number"))
            sub    = am.group("sub")
            if sub:
                number = f"{number}의{sub}"

            combined = _combine_structure_titles(jang, jeol, gwan, title)
            parts    = [p.strip() for p in combined.split(",") if p.strip()]
            seen_parts: list[str] = []
            for p in parts:
                if p not in seen_parts:
                    seen_parts.append(p)
            combined = ", ".join(seen_parts)

            if cur:
                articles.append(cur.to_dict())
            cur = _ArticleBuffer(number=number, title=" ".join(combined.split()))
            if rest:
                cur.add(rest)
            continue

        if cur:
            cur.add(line)

    if cur:
        articles.append(cur.to_dict())

    # 중복 조번호 탈중복: 동일 조번호가 여러 번 나오면 내용이 가장 긴 것만 유지
    seen: dict[str, dict] = {}
    for a in articles:
        key = a["조번호"]
        if key not in seen or len(a["내용"]) > len(seen[key]["내용"]):
            seen[key] = a
    return list(seen.values())


# ── 설정 자동 추론 (--pdf 모드) ───────────────────────────────────────────────

def infer_config(pdf_path: Path) -> dict:
    """파일명에서 법령 이름을 추출해 변환 설정을 자동 생성한다.

    예) 중재법(법률)(제21065호)(20251001).pdf → json_key="중재법"
    """
    stem = pdf_path.stem
    # 첫 번째 '(' 이전의 한글+공백 전체를 법령명으로 추출 (공백 trim)
    # 예) "무역보험법 시행령(대통령령)(...)" → "무역보험법 시행령"
    m    = re.match(r'^([가-힣\s]+?)(?:\s*\(|$)', stem)
    name = m.group(1).strip() if m else stem
    return {
        "pdf":       pdf_path,
        "json_key":  name,
        "out_file":  pdf_path.parent / f"{name}.json",
        "law_title": name,
    }


# ── 변환 실행 ─────────────────────────────────────────────────────────────────

def convert_cfg(cfg: dict, dump: bool = False) -> dict | None:
    """설정 dict로 변환 실행. dump=True면 저장 없이 조문 목록만 출력."""
    pdf_path = Path(cfg["pdf"])
    out_path = Path(cfg["out_file"])

    if not pdf_path.exists():
        print(f"  [ERROR] PDF 없음: {pdf_path}")
        return None

    print(f"  [파싱] {pdf_path.name} ...", end=" ", flush=True)
    text     = extract_text(str(pdf_path))
    articles = parse_text(text, law_title=cfg.get("law_title", ""))
    print(f"{len(articles)}개 조문 추출")

    if dump:
        for a in articles:
            preview = a['내용'][:80].replace('\n', ' ')
            print(f"  [{a['조번호']}] {a['제목']}")
            print(f"    {preview}...")
        return None

    out = {cfg["json_key"]: {"type": "law", "data": articles}}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  [저장] {out_path.relative_to(BASE_DIR)}")
    return {"json_path": out_path, "count": len(articles), "json_key": cfg["json_key"]}


def convert(law_id: str, dump: bool = False) -> dict | None:
    """등록된 법령 ID로 변환."""
    return convert_cfg(LAW_CONFIGS[law_id], dump=dump)


def convert_pdf(pdf_path: Path, dump: bool = False) -> dict | None:
    """임의 PDF 경로로 변환 (자동 설정 추론)."""
    return convert_cfg(infer_config(pdf_path), dump=dump)


# ── 미변환 PDF 목록 ───────────────────────────────────────────────────────────

def list_unregistered() -> None:
    """LAW_DIRS에서 JSON 없는 법령 PDF 목록을 출력한다."""
    registered_pdfs = {Path(c["pdf"]).resolve() for c in LAW_CONFIGS.values()}

    print("법령 PDF 스캔 결과:\n")
    found_any = False
    for law_dir in LAW_DIRS:
        if not law_dir.exists():
            continue
        pdfs = sorted(law_dir.glob("*.pdf"))
        for pdf in pdfs:
            json_path = pdf.parent / f"{re.match(r'^([가-힣]+)', pdf.stem).group(1)}.json" \
                        if re.match(r'^([가-힣]+)', pdf.stem) else None
            status = "[done]" if (json_path and json_path.exists()) else "[ -- ]"
            reg    = " [등록]" if pdf.resolve() in registered_pdfs else ""
            print(f"  {status}{reg}  {pdf.relative_to(BASE_DIR)}")
            found_any = True

    if not found_any:
        print("  (PDF 파일 없음)")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="한국 국내법 PDF → JSON 변환")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--law",
        choices=list(LAW_CONFIGS),
        metavar="LAW_ID",
        help=f"등록된 법령 변환: {list(LAW_CONFIGS)}",
    )
    group.add_argument(
        "--pdf",
        metavar="PDF_PATH",
        help="임의 PDF 직접 변환 (프로젝트 루트 기준 상대경로 또는 절대경로)",
    )
    group.add_argument("--all",  action="store_true", help="등록된 법령 전체 변환")
    group.add_argument("--list", action="store_true", help="법령 PDF 변환 현황 조회")
    parser.add_argument("--dump", action="store_true", help="조문 목록만 출력 (저장 안 함)")
    args = parser.parse_args()

    if args.list:
        list_unregistered()
        return

    if args.all:
        for law_id in LAW_CONFIGS:
            convert(law_id, dump=args.dump)
        return

    if args.law:
        convert(args.law, dump=args.dump)
        return

    if args.pdf:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_absolute():
            pdf_path = BASE_DIR / pdf_path
        convert_pdf(pdf_path, dump=args.dump)


if __name__ == "__main__":
    main()
