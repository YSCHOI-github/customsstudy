---
name: docx-to-md
description: 기출문제 모범답안 폴더의 .docx 파일을 .md로 변환한다. 사용자가 docx를 업데이트한 뒤 이 스킬을 실행하면 md 파일이 최신화된다. /docx-to-md [관세평가|무역실무] 형식으로 호출. 인수 없으면 두 과목 모두 변환.
---

# 기출문제 모범답안 docx → md 변환 스킬

`30_기출문제_모범답안` 폴더의 `.docx` 파일을 `.md`로 변환한다.
사용자가 docx를 업데이트할 때마다 이 스킬을 실행해 md 파일을 최신화한다.

## 사용법

```
/docx-to-md              # 두 과목 모두 변환
/docx-to-md 관세평가      # 관세평가만 변환
/docx-to-md 무역실무      # 무역실무만 변환
```

---

## 변환 대상 폴더

| 과목 | 폴더 경로 |
|------|---------|
| 관세평가 | `c:\Users\haja1\Documents\customsstudy\01_관세평가\30_기출문제_모범답안\` |
| 무역실무 | `c:\Users\haja1\Documents\customsstudy\02_무역실무\30_기출문제_모범답안\` |

---

## 실행 지시문

사용자 확인을 기다리지 말고 STEP 1~4를 끝까지 자동 실행하라.

---

### STEP 1 — 대상 파일 목록 조회

인수에 따라 변환 대상 폴더를 결정한다.
- 인수 없음: 관세평가·무역실무 두 폴더 모두
- `관세평가`: 관세평가 폴더만
- `무역실무`: 무역실무 폴더만

각 대상 폴더에서 `list_dir` 도구로 `.docx` 파일 목록을 조회한다.
조회된 파일 목록을 내부적으로 기록한다.

---

### STEP 2 — 변환 도구 확인

아래 Bash 명령으로 pandoc 설치 여부를 확인한다.

```bash
pandoc --version 2>&1 | head -1
```

- **pandoc 있음**: pandoc으로 변환 (주 방법)
- **pandoc 없음**: python-docx로 변환 (fallback)

---

### STEP 3 — docx → md 변환

각 `.docx` 파일에 대해 동일 폴더에 동일 이름의 `.md` 파일로 변환한다.
(예: `2024-관세평가.docx` → `2024-관세평가.md`)

#### pandoc 사용 시

```bash
pandoc "입력경로.docx" -f docx -t markdown -o "출력경로.md" --wrap=none
```

#### python-docx fallback 사용 시

프로젝트 루트의 `docx_to_md.py` 스크립트를 사용한다.
이 스크립트는 `<w:sdt>` 등 중첩 구조를 포함한 한국어 시험 docx를 정확히 변환한다.

```bash
$env:PYTHONIOENCODING="utf-8"
python "c:\Users\haja1\Documents\customsstudy\docx_to_md.py" [과목]
```

각 파일 변환 결과(성공/실패)를 내부적으로 기록한다.

---

### STEP 4 — 결과 리포트 출력

아래 형식으로 결과를 출력한다.

```
## ✅ docx → md 변환 완료

| 파일 | 결과 |
|------|------|
| 2024-관세평가.docx | ✅ 변환됨 |
| 2023-관세평가.docx | ✅ 변환됨 |
| 2022-관세평가.docx | ⚠️ 실패: [사유] |

**성공**: N건 / **실패**: M건

[실패 건이 있는 경우]
실패 파일은 pandoc 또는 python-docx 설치 여부를 확인하세요.
- pandoc 설치: https://pandoc.org/installing.html
- python-docx 설치: pip install python-docx
```
