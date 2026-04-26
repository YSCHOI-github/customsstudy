"""
convert_box_to_table.py
단권화 MD 파일 상단의 ASCII 박스(``` 코드블록)를 Markdown 표로 변환합니다.

사용법:
    python tools/convert_box_to_table.py "01_관세평가/10_단권화/04_05.md"
    python tools/convert_box_to_table.py --all
"""

import re
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
MD_DIR = BASE_DIR / "01_관세평가" / "10_단권화"

# KEY: VALUE 패턴 — 콜론 앞에 화살표 없이 1~20자
_FIELD_RE = re.compile(r'^([^:→←]{1,20}):\s*(.*)?$')


def _strip_box_line(line: str) -> str:
    """'│ content │' 또는 '│ content' 에서 content만 추출."""
    s = line.strip()
    if s.startswith('│'):
        s = s[1:]
    if s.endswith('│'):
        s = s[:-1]
    return s.strip()


def _parse_box(box_lines: list[str]) -> list[tuple[str, str]]:
    """
    박스 줄 목록을 (key, value) 쌍으로 파싱.
    첫 번째 내용 줄(절 제목) → ('__title__', ...) 로 표시해 표에서 제외.
    연속 줄(→ 로 시작)은 이전 값에 <br>로 이어붙임.
    """
    fields: list[tuple[str, str]] = []
    current_key: str | None = None
    current_val: str = ''
    is_first = True

    for raw in box_lines:
        s = raw.strip()
        if s.startswith('┌') or s.startswith('└') or s == '':
            continue
        if not s.startswith('│'):
            continue

        content = _strip_box_line(raw)
        if not content:
            continue

        if is_first:
            fields.append(('__title__', content))
            is_first = False
            continue

        m = _FIELD_RE.match(content)
        if m:
            if current_key is not None:
                fields.append((current_key, current_val))
            current_key = m.group(1).strip()
            current_val = (m.group(2) or '').strip()
        else:
            # 연속 줄 (→ 등으로 시작)
            if current_key is not None:
                current_val = (current_val + '<br>' + content) if current_val else content

    if current_key is not None:
        fields.append((current_key, current_val))

    return fields


def _to_table(fields: list[tuple[str, str]]) -> str:
    """필드 리스트 → Markdown 2열 표 (제목 행 제외)."""
    rows = [(k, v) for k, v in fields if k != '__title__']
    if not rows:
        return ''
    lines = ['| 항목 | 내용 |', '|------|------|']
    for key, val in rows:
        lines.append(f'| **{key}** | {val} |')
    return '\n'.join(lines)


def convert_file(path: Path) -> bool:
    """파일 내 첫 번째 ASCII 박스 ``` 블록을 표로 교체. 변경 시 True 반환."""
    text = path.read_text(encoding='utf-8')
    lines = text.split('\n')

    # 첫 번째 ``` 펜스 탐색
    fence_start = None
    for i, line in enumerate(lines):
        if line.strip() == '```':
            fence_start = i
            break

    if fence_start is None:
        return False

    # 닫힘 펜스 탐색 + 박스 문자 확인
    fence_end = None
    has_box = False
    for i in range(fence_start + 1, len(lines)):
        if lines[i].strip() == '```':
            fence_end = i
            break
        if any(c in lines[i] for c in ('┌', '└', '│')):
            has_box = True

    if fence_end is None or not has_box:
        return False

    # 박스 파싱 → 표 생성
    box_lines = lines[fence_start + 1:fence_end]
    fields = _parse_box(box_lines)
    table = _to_table(fields)
    if not table:
        return False

    # 교체: fence 블록(시작~끝 포함) → 표
    new_lines = lines[:fence_start] + table.split('\n') + lines[fence_end + 1:]
    new_text = '\n'.join(new_lines)

    if new_text == text:
        return False

    path.write_text(new_text, encoding='utf-8')
    return True


def main():
    parser = argparse.ArgumentParser(description='ASCII 박스를 Markdown 표로 변환')
    parser.add_argument('target', nargs='?', help='변환할 파일 경로')
    parser.add_argument('--all', action='store_true', help='10_단권화 전체 처리')
    args = parser.parse_args()

    if args.all:
        files = sorted(MD_DIR.glob('*.md'))
    elif args.target:
        files = [BASE_DIR / args.target]
    else:
        parser.print_help()
        return

    converted, skipped = 0, 0
    for f in files:
        if not f.exists():
            print(f'  [없음] {f.name}')
            continue
        if convert_file(f):
            print(f'  [변환] {f.name}')
            converted += 1
        else:
            print(f'  [스킵] {f.name}')
            skipped += 1

    print(f'\n완료: {converted}개 변환, {skipped}개 스킵')


if __name__ == '__main__':
    main()
