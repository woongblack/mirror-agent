# Phase 5-D: Planning Agent 구현 플랜

> 목적: 나머지 3개 에이전트가 "비판자"라면, Planning은 "구조화자".
> 아이디어(러프한 텍스트) → Ouroboros Loop → 구조화된 기획안 생성.
>
> ⚠️ 이 에이전트는 나머지 셋과 진입점이 다름.
> Historical/Socratic/Contrarian: 이미 작성된 문서 → 비판
> Planning: 아이디어 → 기획안 생성

---

## 입출력 계약

- **입력:** 아이디어 메모 (비구조적 텍스트 파일)
- **출력:** `PlanningDraft` (구조화된 기획 초안)

---

## 1. 모델 추가 (`models.py`)

```python
class PlanningRound(BaseModel):
    """Ouroboros Loop 1회 순환 결과."""
    round_number: int
    draft: str                  # 이 라운드의 기획안
    ambiguity_score: float      # 0.0~1.0, 낮을수록 명확
    open_questions: list[str]   # 아직 미해결 질문
    changes_from_prev: str      # 이전 라운드 대비 변경 사항

class PlanningDraft(BaseModel):
    """Planning Agent 최종 출력."""
    idea_input: str             # 원본 아이디어 텍스트
    rounds: list[PlanningRound] # Ouroboros 순환 이력
    final_draft: str            # 최종 기획안 (Markdown)
    final_ambiguity: float      # 최종 ambiguity 점수
    converged: bool             # 기준 이하로 수렴했는가
    generated_at: datetime = Field(default_factory=datetime.utcnow)
```

---

## 2. Ouroboros Loop 설계

### 루프 구조

```
Round 1 — 문제 정의
  입력: 아이디어 원문
  질문: "이 아이디어가 해결하는 문제는 정확히 무엇인가?"
  출력: 문제 정의 초안 + ambiguity_score + open_questions

Round 2 — 전제 명시 (Socratic 활용)
  입력: Round 1 초안
  Socratic Agent가 숨겨진 가정 드러내기
  출력: 전제 명시된 기획안 + 갱신된 ambiguity_score

Round 3 — 반대 검증 (Contrarian 활용)
  입력: Round 2 초안
  Contrarian Agent가 반대 시나리오 탐색
  출력: 반대 시나리오 반영된 기획안 + 최종 ambiguity_score

종료 조건: ambiguity_score ≤ 0.2 OR 최대 3회 순환
```

### ambiguity_score 측정 기준

```
LLM이 다음 항목을 1~5점으로 평가 후 평균:
1. 문제 정의 명확도 (What)
2. 대상 사용자 명확도 (Who)
3. 해결 방식 구체성 (How)
4. 성공 기준 존재 여부 (Measure)
5. 실행 가능성 근거 (Feasibility)

score = (5 - 평균) / 5  → 0.0(완전 명확) ~ 1.0(완전 모호)
종료 기준: score ≤ 0.2
```

---

## 3. 구현 파일 (`src/mirror_agent/planner.py`)

### 클래스 구조

```python
class PlanningAgent:
    MAX_ROUNDS = 3
    AMBIGUITY_THRESHOLD = 0.2

    def __init__(self, settings: Settings) -> None:
        self._llm = LLMClient(settings)
        self._model = settings.model_generator  # sonnet — 기획 품질이 핵심
        self._socratic = SocraticAgent(...)
        self._contrarian = ContrarianAgent(...)

    async def plan(self, idea_text: str) -> PlanningDraft:
        rounds = []
        current_draft = idea_text

        for round_num in range(1, self.MAX_ROUNDS + 1):
            round_result = await self._run_round(round_num, current_draft, idea_text)
            rounds.append(round_result)
            current_draft = round_result.draft

            if round_result.ambiguity_score <= self.AMBIGUITY_THRESHOLD:
                break

        return PlanningDraft(
            idea_input=idea_text,
            rounds=rounds,
            final_draft=rounds[-1].draft,
            final_ambiguity=rounds[-1].ambiguity_score,
            converged=rounds[-1].ambiguity_score <= self.AMBIGUITY_THRESHOLD,
        )

    async def _run_round(self, round_num: int, draft: str, original: str) -> PlanningRound:
        if round_num == 1:
            return await self._define_problem(draft, original)
        elif round_num == 2:
            return await self._surface_assumptions(draft, original)
        else:
            return await self._challenge_premises(draft, original)
```

### 시스템 프롬프트 (Round 1 — 문제 정의)

```
당신은 기획 구조화 전문가입니다.

주어진 아이디어에서 다음을 추출하세요:
1. 핵심 문제 (What problem does this solve?)
2. 대상 사용자 (Who has this problem?)
3. 해결 방식 (How does this solve it?)
4. 성공 지표 (How do we know it worked?)
5. 핵심 전제 (What must be true for this to work?)

출력 형식: Markdown 기획 초안
모호한 부분은 [?] 태그로 표시하세요.
```

### 내부 모델 (LLM 출력용)

```python
class _RoundOutput(BaseModel):
    draft: str
    ambiguity_score: float  # 0.0~1.0
    open_questions: list[str]
    changes_from_prev: str
```

---

## 4. CLI 추가 (`cli.py`)

```bash
mirror plan <idea_file>
```

옵션:
- `--max-rounds N`: 최대 순환 횟수 (기본 3)
- `--threshold F`: ambiguity 종료 기준 (기본 0.2)
- `--no-save`: stdout만 출력

출력 저장 위치: `data/plans/{idea_stem}_YYYYMMDD.md`

---

## 5. 구현 체크리스트

- [ ] `models.py`에 `PlanningRound`, `PlanningDraft` 모델 추가
- [ ] `src/mirror_agent/planner.py` 구현
  - [ ] `PlanningAgent` 클래스
  - [ ] `plan()` 메서드 (Ouroboros Loop)
  - [ ] `_define_problem()` (Round 1)
  - [ ] `_surface_assumptions()` (Round 2, Socratic 활용)
  - [ ] `_challenge_premises()` (Round 3, Contrarian 활용)
  - [ ] `_measure_ambiguity()` (ambiguity_score 계산)
- [ ] `cli.py`에 `mirror plan` 커맨드 추가
- [ ] `data/plans/` 디렉토리 생성
- [ ] `tests/test_planner.py` 작성
  - [ ] 단위 테스트: ambiguity_score 0.2 이하 시 조기 종료
  - [ ] 단위 테스트: 최대 3라운드 초과 안 함
  - [ ] 통합 테스트 (`@pytest.mark.integration`)

---

## 6. 테스트 전략

### 단위 테스트 (LLM 없이)
- `MAX_ROUNDS` 초과 방지 로직
- `ambiguity_score ≤ AMBIGUITY_THRESHOLD` 시 조기 종료
- `PlanningDraft.converged` 필드 정확성

### 통합 테스트 (LLM 호출)
- 입력: Mirror Agent 아이디어 메모 (간단한 텍스트)
- 최소 2 라운드 실행 확인
- 최종 `final_draft`가 원본보다 구조화됐는지 확인 (섹션 수 증가)
- `open_questions`가 라운드마다 감소하는 추세 확인

### 실제 사용 시나리오 테스트
- `docs/origin/conversation-log.md` 요약 → 아이디어 입력
- Mirror Agent 자기 자신의 기획안 생성 테스트

---

## 7. 합격 기준

```
[Convergence]  3회 이내 ambiguity_score ≤ 0.2 달성 (또는 3회 후 명확히 감소 추세)
[Structure]    최종 기획안에 문제/사용자/해결방식/성공지표 4개 섹션 포함
[Integration]  Round 2에서 Socratic, Round 3에서 Contrarian 실제 활용
[Traceability] 각 라운드의 changes_from_prev가 구체적으로 작성됨
```

---

## 8. 의존성

- **선행 조건: 5-A, 5-B 완료 필수** (Socratic/Contrarian 내부에서 사용)
- 기존: `llm.py`, `models.py`, `socratic.py`, `contrarian.py`
- 신규: `planner.py`, `data/plans/` 디렉토리

---

## 9. 포트폴리오 가치

이 에이전트가 완성되면 Mirror Agent의 전체 워크플로우가 완성된다:

```
[아이디어] → Planning Agent → [기획 초안]
                ↓
[기획 초안] → Historical + Socratic + Contrarian → [비판 리포트]
                ↓
[비판 수용] → 기획 수정 → 반복
```

---

*Phase 5 완료 후: 포트폴리오 정리 → Phase 6 (입사 후 Jira/Confluence)*
