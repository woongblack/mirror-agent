# Mirror Agent — 잔여 구현 플랜

> v0.1 구현 완료 (2026-04-23) 이후 남은 작업.
> 각 단계는 독립 가치를 가지며, 어디서 멈춰도 그 시점까지 완성된 상태다.

---

## 현재 위치

```
Phase 2 (v0.1)  ✅ 완료 — Historical Agent Re-Applicator 동작 확인
Phase 3         🔄 진행 중 — 실사용 + 개선 사이클
Phase 4         ⏸ 대기 — Extractor + Generalizer 자동화
Phase 5         ⏸ 대기 — Socratic / Contrarian 통합
Phase 6         ⏸ 대기 — Jira / Confluence 연동
```

**현재 한계:** 규칙 8개가 전부 수동 작성 + 플랫폼/마켓플레이스 맥락 특화.
다른 유형의 기획 문서에는 트리거되는 규칙이 적거나 없을 수 있음.

---

## Phase 3 — 실사용 + 개선 (지금 해야 할 것)

코드 작업보다 **도구를 실제로 쓰는 것**이 이 단계의 핵심.

### 3-1. 리포트 저장 구조 구축

`data/reports/`에 날짜별 리포트를 저장하는 구조를 잡는다.

```
data/reports/
└── allblue-readme/
    ├── 2026-04-23.md   ← 오늘 생성된 리포트
    ├── 2026-04-30.md   ← 개선 후 재실행
    └── ...
```

**코드 변경:** `reporter.py`에 `--output` 옵션 또는 자동 저장 경로 지정.
이 히스토리가 쌓여야 v0.2 scorer.py novelty 계산이 의미를 가진다.

### 3-2. 비판 수용/반려 사이클

오늘 나온 비판 5개를 직접 판정하고 ALLBLUE README를 수정한다.

```
① 비판 읽기
② 수용 / 반려 판정 (반려 이유 data/rejections.md에 기록)
③ ALLBLUE README 수정
④ mirror review 재실행
⑤ 새 비판과 이전 비판 비교
```

**반려 이유 기록이 중요하다.** 이게 Phase 4 Generalizer 튜닝 재료가 된다.

### 3-3. ground_truth 보완

| 항목 | 작업 |
|------|------|
| gt_002 gap | `rule_post_mvp_concreteness`의 `evidence_questions`에 "현재 Phase 검증 실패 시 다음 Phase 설계는 어떻게 되는가?" 추가 |
| gt_003 | 자율 검수 에이전트 설계서 fixture 파일 추가 후 재실행 |

```bash
# gt_002 보완 후 확인
uv run mirror review tests/fixtures/allblue-readme-snapshot.md

# gt_003 재현 (fixture 추가 후)
uv run mirror review tests/fixtures/inspection-agent-design.md
```

### 3-4. Rule 10 빈 슬롯 채우기

실사용 사이클에서 "이런 패턴도 있었네"를 발견하는 순간 채운다.
플랫폼이 아닌 유형의 기획에서 반복되는 본인의 비판 패턴이 후보.

---

## v0.2 — Scorer Novelty 구현

Phase 3에서 리포트 히스토리가 2~3회 쌓인 후 구현한다.

### 변경 파일: `src/mirror_agent/scorer.py`

```python
final_score = confidence × (1 + novelty_bonus - repetition_penalty)
```

| 항목 | 구현 내용 |
|------|-----------|
| `_load_history()` | `data/reports/{document_slug}/` 탐색, 이전 리포트 파싱 |
| `novelty_bonus` | 이번에 새로 등장한 규칙 ID면 +0.2 |
| `repetition_penalty` | 직전 3회 리포트에 이미 있던 규칙 ID면 -0.3 |
| 사용자 답변 감점 | 사용자가 수용 판정한 규칙이 또 나오면 추가 감점 (data/rejections.md 참조) |

---

## Phase 4-A — Extractor 구현

**목적:** 과거 대화 로그에서 Critique Unit을 자동 추출한다.
Generalizer의 입력 재료를 만드는 단계.

### 입력
- `docs/origin/conversation-log.md`
- 추후 추가될 회의록, 코드 리뷰 코멘트 등

### 출력: `data/critiques/*.json`

```json
{
  "id": "critique_001",
  "source": "conversation-log.md#phase7",
  "raw_text": "셀러는 어떻게 구할 건데?",
  "target_project": "DEKK",
  "domain": "platform/marketplace",
  "critique_category": "supplier_acquisition",
  "context": "클론 제품의 차별화 부재 지적 중"
}
```

### 구현 위치: `src/mirror_agent/extractor.py`

```python
class Extractor:
    async def extract(self, document_path: Path) -> list[CritiqueUnit]:
        # LLM + structured_call로 비판 발화 식별
        # 모델: claude-haiku-4-5-20251001 (배치 처리, 비용 최소화)
        pass
```

### 검증 기준
- `conversation-log.md` 입력 시 수동 규칙 8개의 원본 비판 3개 이상 재현
- False Positive(비판 아닌 발화를 비판으로 추출) 20% 미만

---

## Phase 4-B — Generalizer 구현

**목적:** Critique Unit → 추상 규칙 자동 생성.
이 단계가 완성되면 "어떤 유형의 기획이든 패턴 적용"이 가능해진다.

### 핵심 과제

L1 → L2 점프:
```
L1: "셀러는 어떻게 구할 건데?" (DEKK 맥락 특화)
L2: trigger_conditions: { target_type_in: ["platform", "marketplace"] }
    critique_template: "{supply_side}를 어떻게 확보할 것인가?"
```

### 구현 위치: `src/mirror_agent/generalizer.py`

```python
class Generalizer:
    async def generalize(self, units: list[CritiqueUnit]) -> list[Rule]:
        # 유사 CritiqueUnit 클러스터링
        # 클러스터 → 추상 규칙 생성 (claude-sonnet-4-6, 추상화 품질이 핵심)
        # 기존 규칙과 유사도 체크 → 병합 or 신규
        pass
```

### HITL 검증: GitHub PR 방식

```
자동 생성 규칙
    → data/rules/pending/rule_candidate_*.json 저장
    → GitHub Action이 PR 자동 생성
    → 사용자 승인/반려/수정
    → 머지되면 data/rules/active/로 이동
```

PR 체크리스트:
- [ ] 이 규칙이 실제 내 사고 패턴을 반영하는가?
- [ ] trigger_conditions가 너무 넓거나 좁지 않은가?
- [ ] 수동 규칙과 중복되지 않는가?

### 검증 기준
- 자동 생성 규칙 PR 승인율 50% 이상
- 수동 규칙 8개 중 6개 이상을 자동으로 재현

### ⚠️ 실패 시 대응
historical-agent-plan.md의 경고 그대로:
> "이 플랜대로 가면 Generalizer 단계에서 무조건 벽에 부딪힐 거예요."

실패해도 괜찮다. "LLM의 일반화 한계 실증 케이스" 자체가 포트폴리오 가치를 가진다.

---

## Phase 5 — Socratic + Contrarian 통합

**전제:** Phase 4 완료 + Historical Agent 단독 가치 충분히 검증된 후.
(CLAUDE.md 원칙: v0.1에서는 Historical 단독 검증. 섞으면 평가가 희석됨.)

### Socratic Agent

"왜?"를 5번 다른 각도로 묻는다.

```python
class SocraticAgent:
    async def interrogate(self, document: str) -> list[SocraticQuestion]:
        # 가정 드러내기 패턴
        # 각 주장의 전제를 명시하게 함
        pass
```

### Contrarian Agent

반대 전제가 성립할 가능성 탐색.

```python
class ContrarianAgent:
    async def challenge(self, document: str) -> list[ContrarianChallenge]:
        # "당연한 것"에 회의 제기
        # 반대 시나리오 구성
        pass
```

### 오케스트레이션

뽀짝이/뽀야 구조 참고 (conversation-log.md):
- Historical Agent가 다른 두 에이전트 출력을 "과거 궤적 기준으로 재검증"
- 세 에이전트 병렬 실행 → 결과 통합 → 우선순위 결정

---

## Phase 6 — Jira / Confluence 연동

취업 이후 실제 업무 환경에서 자연스럽게.

- Confluence 페이지 → 비판 리포트 입력 소스
- 확정된 리포트 → Confluence 자동 저장
- 비판 → Jira 티켓 자동 생성

---

## 구현 우선순위 요약

```
지금    Phase 3 실사용 사이클 (코드 최소, 사용이 핵심)
        data/reports/ 저장 구조 (소수정)
        gt_002 규칙 보완

히스토리 2~3회 후   v0.2 scorer.py novelty

Phase 3 완주 후   Phase 4-A Extractor
                 Phase 4-B Generalizer

검증 후          Phase 5 Socratic/Contrarian
취업 후          Phase 6 Jira/Confluence
```

---

## 각 단계 진입 전 셀프 체크

- 이전 단계의 실사용 피드백을 반영했는가?
- 새 단계가 "있어야 할 것 같아서"가 아닌 실제 필요 때문에 시작하는가?
- 중간에 멈춰도 이 단계까지의 산출물이 독립적 가치를 가지는가?

---

*작성일: 2026-04-23*
*기준 문서: roadmap.md, historical-agent-plan.md, CLAUDE.md*
