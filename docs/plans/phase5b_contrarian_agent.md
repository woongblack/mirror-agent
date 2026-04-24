# Phase 5-B: Contrarian Agent 구현 플랜

> 목적: 문서가 "당연히" 전제하는 것에 반대 시나리오를 구성한다.
> "크로스 셀러 룩북이 전환율이 높다"는 주장에 → "낮을 수도 있다면 어떻게 되는가?"

---

## 입출력 계약

- **입력:** 문서 텍스트 + `DocumentMetadata`
- **출력:** `list[ContrarianChallenge]`

---

## 1. 모델 추가 (`models.py`)

```python
class ContrarianChallenge(BaseModel):
    claim: str               # 문서의 핵심 주장. 예: "크로스 셀러 룩북이 전환율을 높인다"
    counter_premise: str     # 반대 전제. 예: "오히려 낮출 수도 있다"
    counter_scenario: str    # 반대 전제가 성립하는 구체적 시나리오
    challenge_question: str  # 이 시나리오에서 나오는 질문
    implication: str         # 반대 전제가 맞다면 어떤 결과가 오는가
    severity: Literal["high", "medium", "low"]
    evidence_from_document: str  # claim이 문서 어디에 있는지 인용
```

---

## 2. 구현 파일 (`src/mirror_agent/contrarian.py`)

### 클래스 구조

```python
class ContrarianAgent:
    def __init__(self, llm: LLMClient, model: str) -> None: ...
    async def challenge(self, document_text: str, metadata: DocumentMetadata) -> list[ContrarianChallenge]: ...
```

### 내부 모델 (LLM 출력용)

```python
class _ContrarianOutput(BaseModel):
    challenges: list[ContrarianChallenge]
```

### 시스템 프롬프트 전략

```
당신은 기획 문서의 핵심 주장에 반대 시나리오를 구성하는 비판자입니다.

## 역할
- 문서가 "당연히" 전제하는 것에 "정말 당연한가?"를 묻습니다
- 단순 부정("아닐 수도 있다")이 아니라 반대 전제가 성립하는 구체적 시나리오를 만듭니다
- 반대 시나리오가 맞다면 기획이 어떻게 바뀌어야 하는지까지 제시합니다

## 핵심 주장 유형 (아래 유형에서 찾아라)
- 사용자 수요 주장: "사용자가 X를 원한다"
- 차별화 주장: "우리가 더 낫다"
- 실행 가능성 주장: "기술적으로 가능하다"
- 수익 주장: "이렇게 수익이 난다"
- 타이밍 주장: "지금이 적기다"

## 반대 시나리오 작성 원칙
- "~이 아닐 수도 있다"에서 그치지 말 것
- 반대 전제가 성립하는 구체적 조건과 메커니즘을 설명할 것
- 반대 시나리오가 사실이면 어떤 결정을 다르게 해야 하는지까지 제시할 것

## 금지
- 단순 부정("이게 안 될 수도 있어요") 금지
- Historical/Socratic과 겹치는 질문 금지
- 문서 근거 없이 주장 생성 금지
```

### 사용자 프롬프트 구조

```python
user_prompt = f"""
다음 문서의 핵심 주장에 반대 시나리오를 구성하세요. 최소 3개.

문서:
{document_text[:4000]}

메타데이터:
- 프로젝트 유형: {metadata.target_type}
- 사용자 가치 주장: {metadata.claimed_user_values}
- 공급자 존재: {metadata.has_supply_side}
"""
```

### 모델 선택

`claude-sonnet-4-6` — 반대 시나리오 구성은 추론 깊이 필요, haiku로 부족

---

## 3. CLI 추가 (`cli.py`)

```bash
mirror contrarian <document_path>
```

옵션:
- `--no-save`: stdout만 출력
- `--output`: 저장 경로 지정

출력 저장 위치: `data/reports/{doc_stem}/contrarian_YYYYMMDD.json`

---

## 4. 구현 체크리스트

- [ ] `models.py`에 `ContrarianChallenge` 모델 추가
- [ ] `src/mirror_agent/contrarian.py` 구현
  - [ ] `ContrarianAgent` 클래스
  - [ ] `_ContrarianOutput` 내부 모델
  - [ ] `challenge()` 메서드
- [ ] `cli.py`에 `mirror contrarian` 커맨드 추가
- [ ] `tests/test_contrarian.py` 작성
  - [ ] 단위 테스트: `ContrarianChallenge` 모델 검증
  - [ ] 단위 테스트: counter_scenario 빈 값 방지
  - [ ] 통합 테스트 (`@pytest.mark.integration`)

---

## 5. 테스트 전략

### 단위 테스트 (LLM 없이)
- `ContrarianChallenge` 모델 생성 검증
- severity 필드 enum 검증

### 통합 테스트 (LLM 호출)
- `tests/fixtures/allblue-readme-snapshot.md` 입력
- 최소 3개 challenge 생성 확인
- 각 challenge의 `counter_scenario`가 단순 부정이 아닌지 확인
  - 길이 50자 이상 (최소 구체성 기준)
- `claim`이 문서에서 인용 가능한지 확인

---

## 6. 합격 기준

```
[Coverage]   핵심 주장(value proposition) 당 최소 1개 반대 시나리오
[Concrete]   counter_scenario가 구체적 조건과 메커니즘 포함 (50자 이상)
[Novelty]    Historical + Socratic과 겹치지 않는 각도 60% 이상
[Grounded]   모든 claim이 문서에서 직접 인용 가능
```

---

## 7. 의존성

- 기존: `llm.py`, `models.py`, `analyzer.py`
- 신규: 없음
- 선행 조건: 5-A 완료 (독립 가능하지만 겹침 방지를 위해 순서 권장)

---

*다음 단계: phase5c_orchestrator.md*
