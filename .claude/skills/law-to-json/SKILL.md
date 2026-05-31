---
name: law-to-json
description: 프로젝트 내 한국 법령 PDF를 조문 단위 JSON으로 변환한다. /law-to-json <PDF경로> 형식으로 호출. 인수 없으면 변환 현황을 조회한다.
---

# law-to-json — 법령 PDF → JSON 변환

`tools/parse_korean_laws.py`를 사용해 한국 국내법 PDF를 `{"조번호", "제목", "내용"}` 형식의 JSON으로 변환한다.
변환 결과는 PDF와 동일한 디렉토리에 `법령명.json`으로 저장된다.

## 사용법

```
/law-to-json                                            # 변환 현황 조회
/law-to-json 02_무역실무/40_국내외법령/중재법(...).pdf  # 특정 PDF 변환
/law-to-json --all                                      # 등록된 법령 전체 재변환
/law-to-json --dump 경로                                # 저장 없이 조문 미리보기
```

## 파싱 도구

- 스크립트: `tools/parse_korean_laws.py`
- PDF 라이브러리: `pdfminer.six`
- 장/절/관 헤더 자동 추적 → 제목 필드에 `"총칙, 목적"` 형식으로 조합
- 부칙 이후 자동 중단, 중복 조번호 탈중복(더 긴 내용 유지), 법제처 페이지 헤더·푸터 노이즈 제거

## 출력 JSON 포맷

```json
{
  "법령명": {
    "type": "law",
    "data": [
      { "조번호": "1", "제목": "총칙, 목적", "내용": "제1조(목적) ..." },
      { "조번호": "2의1", "제목": "총칙, 정의", "내용": "..." }
    ]
  }
}
```

---

## 실행 지시문

사용자 확인을 기다리지 말고 STEP 0~4를 끝까지 자동 실행하라.

---

### STEP 0 — 인수 파싱

인수에 따라 실행 모드를 결정한다.

| 인수 패턴 | 모드 |
|---|---|
| 인수 없음 | **list** — 현황 조회 후 종료 |
| `--all` | **all** — 등록된 전체 법령 재변환 |
| `--dump <경로>` | **dump** — 저장 없이 조문 미리보기 |
| PDF 경로 (`.pdf`로 끝남) | **convert** — 해당 PDF 변환 |

PDF 경로는 절대경로 또는 프로젝트 루트 기준 상대경로 모두 허용한다.

---

### STEP 1 — 현황 조회 (list 모드)

list 모드인 경우 아래 명령을 실행하고 결과를 사용자에게 표시한 뒤 종료한다.

```powershell
$env:PYTHONIOENCODING="utf-8"
cd "C:\Users\haja1\Documents\customsstudy"
python tools/parse_korean_laws.py --list 2>&1
```

출력 결과를 그대로 사용자에게 보여주고 STEP 2 이후는 실행하지 않는다.

---

### STEP 2 — PDF 경로 확인 (convert / dump 모드)

PDF 경로가 존재하는지 확인한다.

```powershell
Test-Path "<PDF경로>"
```

- 파일 없으면: 오류 메시지 출력 후 종료
- 파일 있으면: STEP 3 진행

---

### STEP 3 — 변환 실행

모드에 따라 아래 명령을 실행한다.

#### convert 모드 (저장)

```powershell
$env:PYTHONIOENCODING="utf-8"
cd "C:\Users\haja1\Documents\customsstudy"
python tools/parse_korean_laws.py --pdf "<PDF경로>" 2>&1
```

#### dump 모드 (미리보기)

```powershell
$env:PYTHONIOENCODING="utf-8"
cd "C:\Users\haja1\Documents\customsstudy"
python tools/parse_korean_laws.py --pdf "<PDF경로>" --dump 2>&1
```

#### all 모드 (전체 재변환)

```powershell
$env:PYTHONIOENCODING="utf-8"
cd "C:\Users\haja1\Documents\customsstudy"
python tools/parse_korean_laws.py --all 2>&1
```

---

### STEP 4 — 결과 검증 및 보고

convert 모드에서 저장이 완료된 경우, 생성된 JSON 파일을 읽어 검증한다.

```python
import json
with open("<출력 JSON 경로>", encoding="utf-8") as f:
    data = json.load(f)

key = list(data.keys())[0]
arts = data[key]["data"]

# 확인 항목
article_count = len(arts)
has_dup = len(arts) != len({a["조번호"] for a in arts})
sample_first = arts[0]
sample_last  = arts[-1]
```

아래 형식으로 결과를 출력한다.

```
## 변환 완료: <법령명>.json

| 항목 | 결과 |
|---|---|
| 총 조문 수 | N개 |
| 중복 조번호 | 없음 / 있음 (경고) |
| 첫 조문 | [1] 총칙, 목적 |
| 마지막 조문 | [N] ... |
| 저장 경로 | 02_무역실무/40_국내외법령/법령명.json |
```

dump 모드와 all 모드는 스크립트 출력 내용을 그대로 표시한다.

---

## 신규 법령 등록 (선택)

자주 사용하는 법령은 `tools/parse_korean_laws.py`의 `LAW_CONFIGS`에 등록해두면 `--law <id>` 또는 `--all`로 빠르게 재변환할 수 있다.

```python
LAW_CONFIGS: dict[str, dict] = {
    "중재법": { ... },               # 기존 등록
    "무역보험법": {                   # 신규 추가 예시
        "pdf":       BASE_DIR / "02_무역실무" / "40_국내외법령" / "무역보험법(...).pdf",
        "json_key":  "무역보험법",
        "out_file":  BASE_DIR / "02_무역실무" / "40_국내외법령" / "무역보험법.json",
        "law_title": "무역보험법",
    },
}
```

사용자가 등록을 요청하면 해당 PDF의 `infer_config()` 결과를 확인한 뒤 `LAW_CONFIGS`에 추가하고 저장한다.
