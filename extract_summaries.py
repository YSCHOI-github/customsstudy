"""
핵심 요약 추출기 (관세평가 · 무역실무)

사용법:
  python extract_summaries.py              # 두 과목 모두 실행
  python extract_summaries.py 관세평가     # 관세평가만
  python extract_summaries.py 무역실무     # 무역실무만

각 과목의 10_단권화/ 에서 숫자로 시작하는 MD 파일의
'## ... 핵심 요약 ...' 섹션을 다음 '---' 직전까지 추출하여
50_핵심요약/핵심요약.md 에 이어 쓴다.
"""

import re
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

SUBJECTS: dict[str, dict] = {
    "관세평가": {
        "source": BASE_DIR / "01_관세평가" / "10_단권화",
        "output": BASE_DIR / "01_관세평가" / "50_핵심요약" / "핵심요약.md",
        "title": "filename",   # H1이 모두 동일하므로 파일명 사용
    },
    "무역실무": {
        "source": BASE_DIR / "02_무역실무" / "10_단권화",
        "output": BASE_DIR / "02_무역실무" / "50_핵심요약" / "핵심요약.md",
        "title": "h1",
    },
}

SUMMARY_HEADER_RE = re.compile(r"^##\s+.*핵심\s*요약")
DIVIDER_RE = re.compile(r"^-{3,}\s*$")


def get_numbered_md_files(source_dir: Path) -> list[Path]:
    files = [f for f in source_dir.glob("*.md") if f.name[0].isdigit()]
    return sorted(files, key=lambda f: f.name)


def extract_h1_title(lines: list[str]) -> str:
    for line in lines:
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def extract_summary_section(lines: list[str]) -> str | None:
    section_lines: list[str] = []
    in_section = False

    for line in lines:
        if not in_section:
            if SUMMARY_HEADER_RE.match(line):
                in_section = True
                section_lines.append(line)
        else:
            if DIVIDER_RE.match(line):
                break
            section_lines.append(line)

    if not section_lines:
        return None

    while section_lines and not section_lines[-1].strip():
        section_lines.pop()

    return "\n".join(section_lines)


def run_subject(subject: str) -> None:
    paths = SUBJECTS[subject]
    source_dir: Path = paths["source"]
    output_file: Path = paths["output"]

    output_file.parent.mkdir(parents=True, exist_ok=True)
    md_files = get_numbered_md_files(source_dir)

    found, skipped = 0, 0

    use_filename = paths.get("title") == "filename"

    print(f"\n=== {subject} ===")
    with open(output_file, "w", encoding="utf-8") as out:
        for file_path in md_files:
            lines = file_path.read_text(encoding="utf-8").splitlines()
            title = file_path.stem if use_filename else (extract_h1_title(lines) or file_path.stem)
            section = extract_summary_section(lines)

            if section:
                found += 1
                print(f"  [O] {file_path.name}")
                out.write(f"# {title}\n\n")
                out.write(section)
                out.write("\n\n---\n\n")
            else:
                skipped += 1
                print(f"  [-] {file_path.name}  (핵심 요약 없음)")

    print(f"  완료: {found}개 추출, {skipped}개 건너뜀")
    print(f"  출력: {output_file}")


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
        run_subject(subject)


if __name__ == "__main__":
    main()
