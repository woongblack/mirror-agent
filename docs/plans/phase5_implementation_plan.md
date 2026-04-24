# Phase 5 구현 플랜 — Socratic + Contrarian + Planning Agent

> 작성일: 2026-04-24
> 전제: Phase 4 완료 (Historical Agent + Extractor + Generalizer 검증됨)
> 목표: 에이전트 팀 완성 → 포트폴리오 서사 완결

---

## 전체 구조 (완성 후)

```
사용자 문서 입력
    ├── Historical Agent  (과거 비판 패턴 재적용)  ← 기존
    ├── Socratic Agent    (숨겨진 가정 드러내기)    ← Phase 5-A
    └── Contrarian Agent  (반대 전제 탐색)          ← Phase 5-B
            ↓ 병렬 실행
    Orchestrator (결과 통합 + 우선순위 결정)        ← Phase 5-C
            ↓
    Reporter (통합 리포트 출력)

Planning Agent (별도 진입점)                       ← Phase 5-D
    — 기획 초안 → 구조화 → 문제 정의 Ouroboros Loop
```

---

## Phase 5-A: Socratic Agent

**목적:** 문서의 숨겨진 가정(hidden assumption)을 드러내어 "왜?"를 묻는다.
Historical이 "과거에 이런 비판을 했었다"면, Socratic은 "이 주장의 전제가 맞는가?"

### 입출력

- **입력:** 문서 텍스트 + `DocumentMetadata`
- **출력:** `list[SocraticQuestion]`

### 새 모델 (`models.py`에 추가)

```python
class SocraticQuestion(BaseModel):
    assumption: str          # 드러난 숨겨진 가정
    question: str            # "왜 ~인가?" 형태의 질문
    angle: str               # 어떤 각도에서 묻는가 (시장/기술/운영/동기/경쟁)
    severity: Literal["high", "medium", "low"]
```

### 구현 파일

- `src/mirror_agent/socratic.py`

### 프롬프트 전략

```
시스템: 당신은 기획 문서의 암묵적 전제를 드러내는 소크라테스식 질문자입니다.
        "~이다" 형태의 주장에서 전제를 추출하고, 그 전제가 성립하는지 묻습니다.
        각도: 시장 / 기술 / 운영 / 동기 / 경쟁 — 각각 최소 1개

사용자: [문서 텍스트]
```

### 모델

`claude-haiku-4-5-20251001` — 단순 패턴 추출, 비용 최소화

### 합격 기준

- 5가지 각도(시장/기술/운영/동기/경쟁)에서 최소 1개씩 질문 생성
- Historical과 겹치지 않는 새 질문 비율 70% 이상
- False Positive(질문이 문서 내용과 무관) 20% 미만

---

## Phase 5-B: Contrarian Agent

**목적:** 문서가 "당연히" 전제하는 것에 반대 시나리오를 구성한다.
"크로스 셀러 룩북이 전환율이 높다"는 주장에 → "낮을 수도 있다면?"을 탐색.

### 입출력

- **입력:** 문서 텍스트 + `DocumentMetadata`
- **출력:** `list[ContrarianChallenge]`

### 새 모델 (`models.py`에 추가)

```python
class ContrarianChallenge(BaseModel):
    claim: str               # 문서의 주장
    counter_premise: str     # 반대 전제
    challenge_question: str  # 이 반대 전제에서 나오는 질문
    implication: str         # 반대 전제가 맞다면 어떤 결과가 오는가
    severity: Literal["high", "medium", "low"]
```

### 구현 파일

- `src/mirror_agent/contrarian.py`

### 프롬프트 전략

```
시스템: 당신은 기획 문서의 핵심 주장에 반대 시나리오를 구성하는 비판자입니다.
        "~이다"라는 주장에 "~이 아닐 수도 있다"를 탐색합니다.
        단순 부정이 아닌, 반대 전제가 성립할 구체적 시나리오를 제시합니다.
```

### 모델

`claude-sonnet-4-6` — 반대 시나리오 구성은 추론 깊이가 필요

### 합격 기준

- 핵심 주장(value proposition) 당 최소 1개 반대 시나리오
- 반대 시나리오가 구체적 (단순 "아닐 수도 있다"는 제외)
- Historical + Socratic과 비교해 새로운 각도 60% 이상

---

## Phase 5-C: Orchestrator

**목적:** 3개 에이전트를 병렬 실행하고 결과를 통합한다.
Historical Agent가 Socratic/Contrarian 출력을 "과거 궤적 기준으로 재검증"하는 역할.

### 실행 구조

```python
# pipeline.py 확장
async def run_full_review(document_path: Path) -> FullReport:
    # 1. 공통 분석
    metadata = await analyzer.analyze(document_path)

    # 2. 3개 에이전트 병렬 실행
    historical, socratic, contrarian = await asyncio.gather(
        run_historical(document_text, metadata),
        run_socratic(document_text, metadata),
        run_contrarian(document_text, metadata),
    )

    # 3. Historical이 타 에이전트 결과를 과거 궤적 기준으로 재검증
    validated = await historical_revalidate(socratic + contrarian, historical_context)

    # 4. 통합 스코어링 + 상위 N개 선택
    return scorer.score_full(historical + validated)
```

### 새 모델 (`models.py`에 추가)

```python
class FullReport(BaseModel):
    document_path: str
    generated_at: datetime
    historical_critiques: list[Critique]     # 기존
    socratic_questions: list[SocraticQuestion]
    contrarian_challenges: list[ContrarianChallenge]
    top_items: list[...]                     # 통합 우선순위 상위 N개
    document_metadata: DocumentMetadata
```

### Reporter 업데이트

- 섹션 분리: "Historical 비판 / Socratic 질문 / Contrarian 도전"
- 또는 통합 우선순위 리스트 (severity 기준)
- 상위 3개는 에이전트 출처 표시

### CLI

```bash
mirror review --full <document>   # 3개 에이전트 통합
mirror review <document>          # 기존 (Historical만)
```

---

## Phase 5-D: Planning Agent

**목적:** Historical/Socratic/Contrarian이 "비판자"라면, Planning은 "구조화자".
기획 아이디어 → Ouroboros Loop → 구조화된 기획안.

**이 에이전트는 나머지 셋과 진입점이 다름:**
- 나머지: 이미 작성된 문서 → 비판
- Planning: 아이디어(러프한 텍스트) → 기획안 생성

### 입출력

- **입력:** 아이디어 메모 (비구조적 텍스트)
- **출력:** 구조화된 기획 초안 (`PlanningDraft`)

### 구현 파일

- `src/mirror_agent/planner.py`

### Ouroboros Loop 설계

```
Round 1: 문제 정의 — "이 아이디어가 해결하는 문제는 무엇인가?"
Round 2: 전제 명시 — Socratic Agent로 전제 드러내기
Round 3: 반대 검증 — Contrarian Agent로 반대 시나리오 탐색
Round 4: 정제 — Round 2~3 피드백 반영해 기획안 수정
종료 조건: Ambiguity 점수 ≤ 0.2 또는 최대 3회
```

### CLI

```bash
mirror plan <idea_file>    # 아이디어 → 기획안
```

---

## 구현 순서 및 의존성

```
Phase 5-A (Socratic)    ─┐
                          ├→ Phase 5-C (Orchestrator)
Phase 5-B (Contrarian)  ─┘

Phase 5-D (Planning)   → 독립적, 마지막에 구현
```

**권장 순서:** 5-A → 5-B → 5-C → 5-D

---

## 각 단계 합격 기준 요약

| 단계 | 기준 |
|------|------|
| 5-A Socratic | 5개 각도 × 최소 1개, Historical과 비중복 70% |
| 5-B Contrarian | 핵심 주장당 1개 반대 시나리오, 구체성 확인 |
| 5-C Orchestrator | 3개 에이전트 병렬 실행, 통합 리포트 생성 |
| 5-D Planning | Ouroboros 3회 이내 Ambiguity 수렴 확인 |

---

## 주의사항 (CLAUDE.md 원칙 상기)

- ❌ Planning Agent 없이 Socratic/Contrarian만 구현해도 포트폴리오 완성
- ❌ 에이전트 추가가 목적이 되어선 안 됨 — 각 에이전트는 독립적 가치를 가져야 함
- ✅ 5-A, 5-B 단독으로 검증 완료 후 5-C 통합
- ✅ Historical 결과가 희석되지 않는지 매 단계 확인

---

*기준 문서: implementation_plan_remaining.md, CLAUDE.md, conversation-log.md*
