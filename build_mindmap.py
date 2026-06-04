"""
build_mindmap.py  —  핵심요약.md → 마인드맵초안.md 변환기

변환 규칙:
  1. markmap frontmatter 추가
  2. 단일 H1(루트) 추가
  3. 각 단원의 # (H1) → ## (H2)
  4. ## ... 핵심 요약 ... 중간 헤더 제거
  5. 단원 내 하위 헤딩 → H3 기준으로 자동 표준화
  6. 탭 → 2스페이스
  7. * bullet → - bullet

사용법:
  python build_mindmap.py              # 두 과목 모두
  python build_mindmap.py 관세평가
  python build_mindmap.py 무역실무
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

SUBJECTS: dict[str, dict] = {
    "관세평가": {
        "source": BASE_DIR / "01_관세평가" / "50_핵심요약" / "핵심요약.md",
        "output": BASE_DIR / "01_관세평가" / "50_핵심요약" / "00_관세평가마인드맵초안.md",
        "title":  "관세평가 핵심 요약",
    },
    "무역실무": {
        "source": BASE_DIR / "02_무역실무" / "50_핵심요약" / "핵심요약.md",
        "output": BASE_DIR / "02_무역실무" / "50_핵심요약" / "00_무역실무마인드맵초안.md",
        "title":  "무역실무 핵심 요약",
    },
}

MARKMAP_FRONTMATTER = "---\nmarkmap:\n  initialExpandLevel: 1\n---\n"
SUMMARY_HEADER_RE = re.compile(r"^#{1,6}\s+.*핵심\s*요약")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


def normalize_subheadings(lines: list[str]) -> list[str]:
    """단원 내 H3 미만 헤딩(H4~H6)을 H3으로 끌어올린다.
    H2(단원 제목)는 건드리지 않는다."""
    levels = [
        len(m.group(1))
        for line in lines
        if (m := HEADING_RE.match(line)) and len(m.group(1)) > 2
    ]
    if not levels:
        return lines

    shift = min(levels) - 3  # 최소 레벨이 H3이 되도록 이동량 계산
    if shift == 0:
        return lines

    result = []
    for line in lines:
        m = HEADING_RE.match(line)
        if m and len(m.group(1)) > 2:
            new_level = max(3, len(m.group(1)) - shift)
            line = "#" * new_level + " " + m.group(2)
        result.append(line)
    return result


def split_into_units(lines: list[str]) -> list[list[str]]:
    """H1(# )을 기준으로 단원을 분리한다."""
    units: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^# ", line):
            if current:
                units.append(current)
            current = [line]
        else:
            current.append(line)
    if current:
        units.append(current)
    return units


def transform_unit(unit: list[str]) -> list[str]:
    """단원 하나에 변환 규칙을 적용한다."""
    result: list[str] = []
    skip_next_blank = False

    for line in unit:
        # H1 → H2
        if re.match(r"^# ", line):
            result.append("#" + line)
            continue

        # ## ... 핵심 요약 ... 헤더 삭제 (다음 빈 줄도 하나 제거)
        if SUMMARY_HEADER_RE.match(line):
            skip_next_blank = True
            continue

        if skip_next_blank:
            skip_next_blank = False
            if line.strip() == "":
                continue

        result.append(line)

    return normalize_subheadings(result)


def convert(source: Path, title: str) -> str:
    raw = source.read_text(encoding="utf-8")

    # 탭 → 2스페이스, * bullet → - bullet
    normalized = raw.replace("\t", "  ")
    normalized = re.sub(r"^(\s*)\* ", r"\1- ", normalized, flags=re.MULTILINE)

    lines = normalized.splitlines()
    units = split_into_units(lines)

    out: list[str] = [MARKMAP_FRONTMATTER, f"# {title}", ""]
    for unit in units:
        out.extend(transform_unit(unit))
        out.append("")  # 단원 사이 빈 줄

    return "\n".join(out)


def run(subject: str) -> None:
    cfg = SUBJECTS[subject]
    src: Path = cfg["source"]
    dst: Path = cfg["output"]

    if not src.exists():
        print(f"[{subject}] 핵심요약.md 없음: {src}")
        return

    dst.write_text(convert(src, cfg["title"]), encoding="utf-8")
    print(f"[{subject}] 완료 → {dst}")


def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else None

    if arg is None:
        targets = list(SUBJECTS.keys())
    elif arg in SUBJECTS:
        targets = [arg]
    else:
        print(f"오류: 알 수 없는 과목 '{arg}'. 사용 가능: {', '.join(SUBJECTS)}")
        sys.exit(1)

    for subject in targets:
        run(subject)


if __name__ == "__main__":
    main()
