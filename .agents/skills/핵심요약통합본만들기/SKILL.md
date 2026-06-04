---
name: 핵심요약통합본만들기
description: /핵심요약통합본만들기 [관세평가|무역실무] — 단권화 MD에서 핵심 요약을 추출해 핵심요약.md를 생성하고, 마인드맵 소스(마인드맵초안.md)까지 연속 생성한다. 인수 없으면 두 과목 모두 실행.
---

# 핵심요약통합본만들기

두 스크립트를 순서대로 실행해 최종 산출물 2종을 생성한다.

1. `extract_summaries.py` → `50_핵심요약/핵심요약.md`
2. `build_mindmap.py` → `50_핵심요약/00_관세평가마인드맵초안.md` 또는 `00_무역실무마인드맵초안.md`

## 사용법

```
/핵심요약통합본만들기              # 두 과목 모두
/핵심요약통합본만들기 관세평가     # 관세평가만
/핵심요약통합본만들기 무역실무     # 무역실무만
```

## 실행 지시문

아래 STEP 0~1을 자동 실행하라.

---

### STEP 0 — 명령 결정

인수에 따라 실행할 명령 쌍을 결정한다.

- 인수 없음:
  ```
  python extract_summaries.py
  python build_mindmap.py
  ```
- `관세평가`:
  ```
  python extract_summaries.py 관세평가
  python build_mindmap.py 관세평가
  ```
- `무역실무`:
  ```
  python extract_summaries.py 무역실무
  python build_mindmap.py 무역실무
  ```
- 그 외 → "오류: 인수는 '관세평가' 또는 '무역실무'만 허용됩니다." 출력 후 종료

---

### STEP 1 — 순서대로 실행 및 결과 보고

프로젝트 루트 `C:\Users\haja1\Documents\customsstudy`에서 두 명령을 순서대로 실행한다.
`extract_summaries.py`가 성공한 경우에만 `build_mindmap.py`를 실행한다.

실행 후 과목별로 아래 형식으로 결과를 보고한다.

```
[관세평가]
  핵심요약.md      → 01_관세평가/50_핵심요약/핵심요약.md (추출 N개)
  마인드맵초안.md  → 01_관세평가/50_핵심요약/00_관세평가마인드맵초안.md
```
