"""
docx → md 변환 스크립트
30_기출문제_모범답안 폴더의 모든 .docx 파일을 .md로 변환한다.

Korean exam docx files often wrap all content inside <w:sdt> (Structured Document
Tags), making top-level paragraph iteration miss most text. This script uses XPath
to find ALL paragraph elements at any nesting depth.
"""

import sys
from pathlib import Path
from docx import Document
from docx.oxml.ns import qn
from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W}


def get_runs_text(para_elem) -> str:
    """단락 요소에서 볼드/이탤릭 포함 텍스트를 추출한다."""
    parts = []
    for r_elem in para_elem.findall(".//w:r", NS):
        t_nodes = r_elem.findall("w:t", NS)
        text = "".join((t.text or "") for t in t_nodes)
        if not text:
            continue
        rpr = r_elem.find("w:rPr", NS)
        bold = rpr is not None and rpr.find("w:b", NS) is not None
        italic = rpr is not None and rpr.find("w:i", NS) is not None
        if bold and italic:
            parts.append(f"***{text}***")
        elif bold:
            parts.append(f"**{text}**")
        elif italic:
            parts.append(f"*{text}*")
        else:
            parts.append(text)
    return "".join(parts)


def get_heading_level(para_elem) -> int:
    """단락이 제목 스타일이면 레벨(1~6)을 반환, 아니면 0."""
    ppr = para_elem.find("w:pPr", NS)
    if ppr is None:
        return 0
    pstyle = ppr.find("w:pStyle", NS)
    if pstyle is None:
        return 0
    val = pstyle.get(f"{{{W}}}val", "")
    val_lower = val.lower()
    if val_lower.startswith("heading"):
        suffix = val[len("heading"):].strip()
        try:
            return min(int(suffix), 6)
        except ValueError:
            return 1
    return 0


def is_list_para(para_elem) -> bool:
    """글머리 목록 단락이면 True."""
    ppr = para_elem.find("w:pPr", NS)
    if ppr is None:
        return False
    return ppr.find("w:numPr", NS) is not None


def table_elem_to_md(tbl_elem) -> str:
    """w:tbl 요소를 마크다운 테이블로 변환한다."""
    rows = tbl_elem.findall(".//w:tr", NS)
    if not rows:
        return ""

    md_rows = []
    for i, tr in enumerate(rows):
        cells = []
        for tc in tr.findall("w:tc", NS):
            # 셀 안의 모든 텍스트를 추출
            cell_text = " ".join(
                get_runs_text(p).strip()
                for p in tc.findall(".//w:p", NS)
                if get_runs_text(p).strip()
            )
            cells.append(cell_text.replace("|", "\\|"))
        if cells:
            md_rows.append("| " + " | ".join(cells) + " |")
            if i == 0:
                md_rows.append("| " + " | ".join("---" for _ in cells) + " |")

    return "\n".join(md_rows)


def docx_to_md(docx_path: Path) -> str:
    """docx를 마크다운 문자열로 변환한다."""
    doc = Document(str(docx_path))
    body = doc.element.body

    lines = []

    # body 전체를 순회하되 w:p와 w:tbl을 문서 순서대로 처리
    # - w:tbl 안의 w:p는 table_elem_to_md에서 처리하므로 별도 skip 필요
    processed_in_table = set()

    def collect(elem, depth=0):
        tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

        if tag == "tbl":
            md = table_elem_to_md(elem)
            if md:
                lines.append("")
                lines.append(md)
                lines.append("")
            # 테이블 내부 paragraph는 이미 처리됐으므로 skip
            return

        if tag == "p":
            text = get_runs_text(elem).strip()
            if text:
                level = get_heading_level(elem)
                if level:
                    lines.append("#" * level + " " + text)
                elif is_list_para(elem):
                    lines.append("- " + text)
                else:
                    lines.append(text)
            else:
                lines.append("")
            return  # 단락 내부를 다시 순회하지 않음

        # sdt, sdtContent, body, sectPr 등: 자식 요소를 재귀 탐색
        for child in elem:
            child_tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            # sectPr(섹션 속성)은 건너뜀
            if child_tag == "sectPr":
                continue
            collect(child, depth + 1)

    collect(body)

    # 연속 빈 줄 최대 1개로 압축
    result = []
    prev_blank = False
    for line in lines:
        is_blank = (line == "")
        if is_blank and prev_blank:
            continue
        result.append(line)
        prev_blank = is_blank

    return "\n".join(result).strip() + "\n"


def convert_folder(folder: Path) -> tuple[int, int]:
    """폴더 내 모든 docx를 md로 변환. (성공, 실패) 반환."""
    docx_files = sorted(folder.glob("*.docx"))
    success, fail = 0, 0

    for docx_path in docx_files:
        md_path = docx_path.with_suffix(".md")
        try:
            md_content = docx_to_md(docx_path)
            md_path.write_text(md_content, encoding="utf-8")
            line_count = md_content.count("\n")
            print(f"  [OK] {docx_path.name}  ({line_count}줄)")
            success += 1
        except Exception as e:
            print(f"  [FAIL] {docx_path.name}: {e}")
            fail += 1

    return success, fail


def main():
    base = Path(r"c:\Users\haja1\Documents\customsstudy")
    targets = {
        "관세평가": base / "01_관세평가" / "30_기출문제_모범답안",
        "무역실무": base / "02_무역실무" / "30_기출문제_모범답안",
    }

    subject_filter = sys.argv[1] if len(sys.argv) > 1 else None
    if subject_filter:
        targets = {k: v for k, v in targets.items() if k == subject_filter}
        if not targets:
            print(f"알 수 없는 과목: {subject_filter}. '관세평가' 또는 '무역실무'를 입력하세요.")
            sys.exit(1)

    total_ok, total_fail = 0, 0
    for label, folder in targets.items():
        print(f"\n[{label}]")
        ok, fail = convert_folder(folder)
        total_ok += ok
        total_fail += fail

    print(f"\n완료 — 성공: {total_ok}건 / 실패: {total_fail}건")


if __name__ == "__main__":
    main()
