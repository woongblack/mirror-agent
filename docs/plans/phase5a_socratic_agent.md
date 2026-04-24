# Phase 5-A: Socratic Agent 구현 플랜

> 목적: 문서의 숨겨진 가정(hidden assumption)을 드러내어 "왜?"를 묻는다.
> Historical이 "과거에 이런 비판을 했었다"면, Socratic은 "이 주장의 전제가 맞는가?"

---

## 입출력 계약

- **입력:** 문서 텍스트 + `DocumentMetadata`
- **출력:** `list[SocraticQuestion]`

---

## 1. 모델 추가 (`models.py`)

```python
from typing import Literal

class SocraticQuestion(BaseModel):
    assumption: str   # 드러난 숨겨진 가정. 예: "크로스 셀러 룩북이 사용자 수요가 있다"
    question: str     # "왜 ~인가?" 형태의 질문
    angle: Literal["market", "tech", "operation", "motivation", "competition"]
    severity: Literal["high", "medium", "low"]
    evidence_from_document: str  # 이 가정이 문서 어디에 있는지 인용
```

---

## 2. 구현 파일 (`src/mirror_agent/socratic.py`)

### 클래스 구조

```python
class SocraticAgent:
    def __init__(self, llm: LLMClient, model: str) -> None: ...
    async def interrogate(self, document_text: str, metadata: DocumentMetadata) -> list[SocraticQuestion]: ...
```

### 내부 모델 (LLM 출력용)

```python
class _SocraticOutput(BaseModel):
    questions: list[SocraticQuestion]
```

### 시스템 프롬프트 전략

```
당신은 기획 문서에서 암묵적 전제를 드러내는 소크라테스식 질문자입니다.

## 규칙
- 문서에서 "~이다", "~할 것이다", "~가 필요하다" 형태의 주장을 찾는다
- 그 주장이 성립하기 위해 필요한 전제를 명시한다
- "왜 그 전제가 성립하는가?"를 묻는다

## 5가지 각도 (각각 최소 1개 질문 생성)
- market: 시장 수요, 경쟁 환경, 타이밍
- tech: 기술 실행 가능성, 의존성, 병목
- operation: 운영 지속 가능성, 리소스, 유지보수
- motivation: 프로젝트 동기, 목표, 진짜 이유
- competition: 대안 솔루션, 경쟁 제품, 차별점

## 금지
- Historical Agent와 동일한 질문 생성 금지 (규칙 기반 비판과 겹치면 안 됨)
- "~인지 확인이 필요합니다" 식의 추상적 질문 금지
- 문서에서 인용 불가한 가정 생성 금지
```

### 사용자 프롬프트 구조

```python
user_prompt = f"""
다음 문서에서 숨겨진 가정을 드러내는 질문 5개 이상을 생성하세요.
각도별 최소 1개.

문서:
{document_text[:4000]}

메타데이터:
- 프로젝트 유형: {metadata.target_type}
- 1인 프로젝트: {metadata.is_solo_project}
- 사용자 가치 주장: {metadata.claimed_user_values}
"""
```

### 모델 선택

`claude-haiku-4-5-20251001` — 패턴 추출형, 비용 최소화

---

## 3. CLI 추가 (`cli.py`)

```bash
mirror socratic <document_path>
```

옵션:
- `--no-save`: stdout만 출력
- `--output`: 저장 경로 지정

출력 저장 위치: `data/reports/{doc_stem}/socratic_YYYYMMDD.json`

---

## 4. 구현 체크리스트

- [ ] `models.py`에 `SocraticQuestion` 모델 추가
- [ ] `src/mirror_agent/socratic.py` 구현
  - [ ] `SocraticAgent` 클래스
  - [ ] `_SocraticOutput` 내부 모델
  - [ ] `interrogate()` 메서드
- [ ] `cli.py`에 `mirror socratic` 커맨드 추가
- [ ] `tests/test_socratic.py` 작성
  - [ ] 단위 테스트: 5가지 각도 최소 1개씩 생성 확인
  - [ ] 단위 테스트: 빈 문서 처리
  - [ ] 통합 테스트 (`@pytest.mark.integration`)

---

## 5. 테스트 전략

### 단위 테스트 (LLM 없이)
- `SocraticQuestion` 모델 생성 검증
- 각도(angle) 필드 enum 검증

### 통합 테스트 (LLM 호출)
- `tests/fixtures/allblue-readme-snapshot.md` 입력
- 5가지 각도 각각 최소 1개 질문 포함 확인
- `evidence_from_document`가 빈 문자열이 아닌지 확인

---

## 6. 합격 기준

```
[Coverage]   5가지 각도에서 최소 1개씩 질문 생성
[Novelty]    Historical 비판과 겹치지 않는 질문 70% 이상
[Grounded]   모든 질문의 assumption이 문서에서 인용 가능
[Concrete]   "~인지 확인 필요" 식의 추상 질문 0개
```

---

## 7. 의존성

- 기존: `llm.py`, `models.py`, `analyzer.py`
- 신규: 없음
- 선행 조건: 없음 (Historical과 독립)

---

*다음 단계: phase5b_contrarian_agent.md*
