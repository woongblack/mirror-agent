# Phase 5-C: Orchestrator 구현 플랜

> 목적: Historical + Socratic + Contrarian을 병렬 실행하고 결과를 통합한다.
> Historical Agent가 다른 에이전트 출력을 "과거 궤적 기준으로 재검증"하는 역할.

---

## 입출력 계약

- **입력:** 문서 경로
- **출력:** `FullReport` (3개 에이전트 통합 결과)

---

## 1. 모델 추가 (`models.py`)

```python
class UnifiedItem(BaseModel):
    """통합 우선순위 리스트의 단일 항목."""
    source_agent: Literal["historical", "socratic", "contrarian"]
    severity: Literal["high", "medium", "low"]
    question: str           # 사용자에게 보여줄 핵심 질문
    evidence: str           # 문서 인용
    historical_link: str | None = None  # Historical이 연결한 과거 궤적 (있을 때만)
    final_score: float = 0.0

class FullReport(BaseModel):
    document_path: str
    generated_at: datetime
    # 에이전트별 원본 출력
    historical_critiques: list[Critique]
    socratic_questions: list[SocraticQuestion]
    contrarian_challenges: list[ContrarianChallenge]
    # 통합 우선순위 리스트
    top_items: list[UnifiedItem]        # 상위 3개 표시
    collapsed_items: list[UnifiedItem]  # 나머지 접힘
    document_metadata: DocumentMetadata
```

---

## 2. Orchestrator 설계

### 실행 구조

```
Phase 1 — 공통 분석 (순차)
    analyzer.analyze(document) → DocumentMetadata

Phase 2 — 3개 에이전트 병렬 실행
    historical_task = run_historical(doc, metadata)
    socratic_task   = socratic_agent.interrogate(doc, metadata)
    contrarian_task = contrarian_agent.challenge(doc, metadata)
    results = await asyncio.gather(historical_task, socratic_task, contrarian_task)

Phase 3 — Historical 재검증 (선택적)
    Historical이 Socratic/Contrarian 결과를 과거 궤적 기준으로 재검증
    → "이 질문은 내가 DEKK에 했던 것과 같다" 연결 추가

Phase 4 — 통합 스코어링
    UnifiedItem 변환 → severity + historical_link 기준 정렬
    → top_items (3개) + collapsed_items
```

### Historical 재검증 프롬프트

```
시스템: 당신은 Socratic/Contrarian 에이전트의 출력을 검토합니다.
        각 질문이 사용자(정재웅)의 과거 궤적과 연결되는지 확인하세요.
        연결되는 것만 historical_link를 채우고, 없으면 null로 두세요.

사용자: [과거 궤적 컨텍스트]
        [Socratic/Contrarian 질문 목록]
```

### 파일 구조

```python
# src/mirror_agent/orchestrator.py

class Orchestrator:
    def __init__(self, settings: Settings) -> None: ...

    async def run(self, document_path: Path) -> FullReport:
        # Phase 1: 분석
        metadata = await self._analyzer.analyze(document_path)

        # Phase 2: 병렬 실행
        historical, socratic, contrarian = await asyncio.gather(
            self._run_historical(document_text, metadata),
            self._socratic.interrogate(document_text, metadata),
            self._contrarian.challenge(document_text, metadata),
        )

        # Phase 3: Historical 재검증
        unified = await self._revalidate(historical, socratic, contrarian)

        # Phase 4: 스코어링 + 리포트 생성
        return self._build_full_report(document_path, metadata, historical, socratic, contrarian, unified)
```

---

## 3. Reporter 업데이트 (`reporter.py`)

### 출력 형식 옵션 A (섹션 분리)

```markdown
# Mirror Agent Full Report

## Historical 비판 (과거 궤적 재적용)
### 1. 차별화 지점 명시 원칙 🔴 HIGH
...

## Socratic 질문 (숨겨진 가정)
### 1. [market] 왜 크로스 셀러 룩북이 단일 셀러보다 전환율이 높다고 가정하는가?
...

## Contrarian 도전 (반대 시나리오)
### 1. 크로스 셀러 룩북이 오히려 선택 장애를 유발한다면?
...
```

### 출력 형식 옵션 B (통합 우선순위)

```markdown
# Mirror Agent Full Report

## 핵심 질문 (통합 우선순위)

### 1. [Historical] 차별화 지점 명시 원칙 🔴
### 2. [Socratic/market] 왜 수요가 있다고 가정하는가? 🔴
### 3. [Contrarian] 룩북이 선택 장애를 유발한다면? 🔴

<details>추가 질문 N개</details>
```

**권장: 옵션 B** — 에이전트 출처보다 우선순위가 더 중요

### 구현 파일

```python
# reporter.py에 render_full() 메서드 추가
class Reporter:
    def render(self, report: Report) -> str: ...          # 기존 (Historical만)
    def render_full(self, report: FullReport) -> str: ... # 신규 (통합)
```

---

## 4. CLI 업데이트 (`cli.py`)

```bash
# 기존 (Historical만)
mirror review <document>

# 신규 (3개 에이전트 통합)
mirror review --full <document>
```

---

## 5. 구현 체크리스트

- [ ] `models.py`에 `UnifiedItem`, `FullReport` 모델 추가
- [ ] `src/mirror_agent/orchestrator.py` 구현
  - [ ] `Orchestrator` 클래스
  - [ ] `run()` 메서드 (병렬 실행)
  - [ ] `_revalidate()` 메서드 (Historical 재검증)
  - [ ] `_build_full_report()` 메서드
- [ ] `reporter.py`에 `render_full()` 추가
- [ ] `cli.py`에 `--full` 옵션 추가
- [ ] `tests/test_orchestrator.py` 작성
  - [ ] 단위 테스트: UnifiedItem 정렬 로직
  - [ ] 단위 테스트: 에이전트 실패 시 graceful degradation
  - [ ] 통합 테스트 (`@pytest.mark.integration`)

---

## 6. 테스트 전략

### 단위 테스트 (LLM 없이)
- `UnifiedItem` severity 기준 정렬 확인
- 에이전트 하나가 실패해도 나머지 결과로 리포트 생성 확인

### 통합 테스트 (LLM 호출)
- `tests/fixtures/allblue-readme-snapshot.md` 입력
- 3개 에이전트 모두 결과 반환 확인
- `top_items` 3개 포함 확인
- 총 실행 시간 120초 이내 (병렬 실행 검증)

---

## 7. 합격 기준

```
[Parallel]    3개 에이전트 병렬 실행, 총 시간 단일 실행보다 짧음
[Coverage]    top_items에 최소 2개 에이전트 출처 포함
[Historical]  Socratic/Contrarian 결과 중 과거 궤적 연결 가능한 것에 historical_link 추가
[Graceful]    에이전트 하나 실패해도 나머지로 리포트 생성
```

---

## 8. 의존성

- 선행 조건: **5-A, 5-B 완료 필수**
- 기존: `pipeline.py` (Historical 실행 로직 재사용)
- 신규: `orchestrator.py`, `reporter.py` 업데이트

---

*다음 단계: phase5d_planning_agent.md*
