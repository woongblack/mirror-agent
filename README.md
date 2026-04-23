# Mirror Agent

> 1인 개발자가 자기 자신에게 못 던지는 질문을, 대신 던져주는 에이전트 팀.

---

## 현재 상태

| 단계 | 상태 | 비고 |
| --- | --- | --- |
| Phase 0: 문서화 | ✅ 완료 | README, 대화 로그, 파이프라인 설계, 로드맵, 수동 규칙 10개 |
| Phase 1: 레포 초기화 | ✅ 완료 | 프로젝트 구조, Pydantic 모델, 규칙 JSON 분리, Loader 구현 |
| Phase 2: Re-Applicator v0.1 | ✅ 완료 | 전체 파이프라인 구현 + Ground Truth 3/3 재현 검증 |
| Phase 3: 실사용 + 개선 | 🔄 진행 중 | ALLBLUE README 개선 사이클 |
| Phase 4: Extractor 자동화 | ⏸ 대기 | 대화 로그 → 규칙 자동 추출 |
| Phase 5: 다중 에이전트 통합 | ⏸ 대기 | Socratic / Contrarian / Planning Agent |
| Phase 6: 외부 연동 | ⏸ 대기 | Jira / Confluence |

### v0.1 검증 결과 (2026-04-23)

ALLBLUE README + 자율 검수 에이전트 설계서 적용:

- Ground Truth 3건 중 **3/3 전부 재현** ✅
- `rule_supplier_first` Critical Hit 포함 ✅
- 방어 예측 전 비판에 포함, 약점 분석까지 생성 ✅
- 과거 발화(conversation-log.md) 장면 직접 인용 ✅

---

## 왜 만드는가

이 프로젝트는 **좋은 아이디어가 있어서** 시작한 게 아니다.
두 번의 실패에서 **같은 패턴**을 발견했기 때문에 시작했다.

### 첫 번째 실패 — DEKK (팀 프로젝트)

DEKK는 무신사 Snap을 클론한 팀 프로젝트였다. 나는 팀원들에게 물었다.

- "그래서 이 이후에는 어떻게 할 건데?"
- "셀러는 어떻게 구할 건데?"
- "Snap 클론이면, 결국 똑같아지는 거 아니냐?"

팀은 제대로 답하지 않았다. "클론한 게 의미 없다는 거냐"는 식으로 내 질문 자체가 이상한 것으로 몰렸다. 잘하고 있다는 분위기가 팽배했다. 나는 팀을 나왔다.

### 두 번째 실패 — ALLBLUE (1인 프로젝트)

팀의 한계를 벗어나고 싶어서 ALLBLUE를 혼자 시작했다. 파편화된 상품을 AI 이미지 생성으로 엮는 크로스셀러 룩북 플랫폼. Spring Boot 3.5, Redis Streams, Saga 패턴까지 진지하게 구현했다.

몇 달 후, 내가 만든 README를 누군가와 함께 다시 읽어보다가 깨달았다.

**내가 DEKK 팀에게 던졌던 질문을, 나 자신에게는 한 번도 던지지 않았다.**

- "그래서 크로스셀러 상품 모은 다음에 어떻게 할 건데?"
- "카페24 셀러들이 왜 ALLBLUE에 들어올 건데?"
- "AI 합성이 붙은 Snap 클론 아닌가?"

타인에게는 날카롭게 던질 수 있는 질문을, 내 프로젝트에는 던지지 못했다. 혼자서는 객관성이 떨어진다는 걸 인정할 수밖에 없었다.

### 공통된 문제

두 실패에서 공통된 건 "비판이 들어왔을 때 방어 모드로 전환되는" 현상이었다.
DEKK에서는 집단으로, ALLBLUE에서는 혼자서 나 자신을 상대로.

**"더 똑똑한 비판자"가 필요한 게 아니었다. "감정 없이 계속 같은 자리를 찌르는 비판자"가 필요했다.**

Mirror Agent는 그 역할을 하기 위해 만든다.

---

## 이 프로젝트가 해결하려는 것 (그리고 해결하지 않는 것)

### 해결하려는 것
- 1인 개발자가 자기 기획을 스스로 비판하지 못하는 인지적 맹점
- 과거에 내가 타인에게 던진 비판이 현재의 내 문서에 적용되지 않는 패턴
- 비판이 왔을 때 방어 모드로 전환되는 인간적 반응

### 해결하지 않는 것
- 더 나은 아이디어를 자동으로 생성하는 것
- 사용자를 설득하는 것 (판단은 사용자의 몫)
- 범용 기획 도구 (이건 나를 위해 만드는 도구다)

---

## 핵심 원칙

**1. 맥락을 사용자가 매번 설명하지 않아도 된다**

사용자가 "내가 예전에 이런 프로젝트를 했는데, 이런 비판을 했고, 이런 동기로 새 프로젝트를 시작했다"를 매번 설명해야 한다면, 이 도구는 실패다. Mirror Agent는 사용자의 과거 궤적(이전 프로젝트, 과거 비판, 인정한 맹점)을 학습해 **현재 문서에 기계적으로 재적용한다.**

**2. 비판은 감정 없는 존재에게서 와야 한다**

인간 비판자는 관계, 체면, 분위기에 휘둘린다. 에이전트는 그런 변수가 없다. 5번 물어도 똑같이 묻는다. 사용자가 "얘네가 뭘 모르네"로 방어하면 더 파고든다.

**3. 타인에게 할 수 있는 비판을 자신에게도 적용한다**

이게 이 도구의 고유 기능이다. 범용 LLM은 "일반적 비판"을 한다. Mirror Agent는 **"당신이 과거에 타인에게 던진 바로 그 질문"을 현재 문서에 적용한다.**

**4. 당신(사용자)이 답할 때까지 끝나지 않는다**

에이전트가 만족할 때가 아니라, **사용자가 "이 질문에 답할 수 있다"고 증명할 때까지** 루프를 돈다. 종료 조건은 수치화된다 (Ambiguity 지표 ≤ 0.2).

---

## 최종 시스템 워크플로우

```
① 패턴화 (Patternization)
   과거 대화 로그 → Extractor → Critique Unit
                 → Generalizer → 비판 규칙 DB
                                 (사용자의 사고 궤적 학습)
        │
        ▼
② 초안 기획 (Extraction & Planning)          ← Phase 5
   Confluence 문서 / 날 아이디어
        → Planning Agent (우로보로스 문답)
        → 1차 기획안 생성
        │
        ▼
③ 기획 구체화 (Refinement via Critique)      ← 현재 동작
   1차 기획안
        → Historical Agent: 패턴 규칙 적용
        → Defense Prediction: 방어 예측 + 약점 찌르기
        → 사용자 수용/반려 → 기획 보완
        → Ambiguity ≤ 0.2 될 때까지 반복
        │
        ▼
④ 구현 계획 (Implementation & Jira)          ← Phase 6
   검증된 기획안
        → 작업 단위 분해
        → Jira 티켓 자동 발행
        → Confluence 저장
```

---

## 에이전트 구성

| 에이전트 | 역할 | 상태 |
| --- | --- | --- |
| **Historical Agent** | 과거 비판 패턴을 현재 문서에 재적용. 이 프로젝트의 진짜 차별점. | ✅ 구현됨 |
| **Socratic Agent** | "왜?"를 5번 다른 각도로 물어 가정을 드러냄 | ⏸ Phase 5 |
| **Contrarian Agent** | 반대 전제 탐색, 당연한 가정에 회의 제기 | ⏸ Phase 5 |
| **Planning Agent** | 우로보로스 문답으로 날 아이디어 → 1차 기획안 공동 생성 | ⏸ Phase 5 |

### Historical Agent 내부 파이프라인

```
[과거 대화 로그]
      ↓
  Stage 1: Extractor      → Critique Unit 추출       (⏸ Phase 4-A)
      ↓
  Stage 2: Generalizer    → 추상 규칙 자동 생성       (⏸ Phase 4-B)
      ↓                     (GitHub PR HITL 승인)
  Stage 3: Re-Applicator  → 현재 문서에 적용 + 리포트  (✅ 구현됨)
```

**현재:** 수동 작성 규칙 8개로 Stage 3만 동작 중.
**Phase 4 이후:** 새 대화 로그를 넣을 때마다 규칙 자동 추가.

---

## 첫 번째 테스트 케이스 — 완료

이 도구의 첫 번째 적용 대상은 **내 다른 프로젝트인 ALLBLUE**였다.

- 입력: ALLBLUE README + 자율 검수 에이전트 설계서
- 결과: Ground Truth 3건 중 **3/3 재현**
- Critical Hit: `rule_supplier_first` — "카페24 셀러를 어떻게 확보할 것인가?"

이 결과를 ALLBLUE 프로젝트에 반영해 상업적 방향을 보류하고 **기술 탐구 + Mirror Agent 테스트베드**로 포지션을 재정의했다.

---

## 기술 스택

| 항목 | 기술 |
| --- | --- |
| 언어 | Python 3.12 |
| LLM | Anthropic Claude (Haiku: matcher, Sonnet: generator/defender) |
| SDK | `anthropic` Python SDK (structured output via tool use) |
| CLI | Click + Rich |
| 데이터 모델 | Pydantic v2 |
| 패키지 관리 | uv |
| 규칙 저장 | 로컬 JSON + Git 버전 관리 |
| 외부 연동 (예정) | Atlassian MCP (Jira / Confluence) |

기술 선택의 원칙: **Harness에 95% 시간, Execution에 5%.** 에이전트 개수를 늘리기보다 컨텍스트 주입에 투자한다.

---

## 이 프로젝트가 실패할 조건

정직하게 적는다.

1. 내가 만든 에이전트의 비판을 내가 받아들이지 않으면 실패다. DEKK 팀이 내 비판을 방어했던 것처럼, 내가 에이전트를 방어하기 시작하면.
2. 내가 이 도구를 실제로 매주 쓰지 않으면 실패다. "만들어놓고 안 쓰는 도구"가 되면.
3. Historical Agent가 단순 RAG 이상의 가치를 못 내면 실패다. 과거 비판을 현재에 적용하는 메타 추론이 동작하지 않으면.

---

## 이 프로젝트가 아닌 것

- 범용 코딩 에이전트가 아니다. 그건 Claude Code가 이미 한다.
- 사업 아이디어가 아니다. 개인 도구다.
- 팀 도구가 아니다. 1인 개발자의 메타 도구다.

---

## 로드맵

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| Phase 0~2 | 문서화 + 레포 초기화 + Re-Applicator v0.1 구현 | ✅ 완료 |
| Phase 3 | 실사용 + 개선 사이클 (ALLBLUE README 적용) | 🔄 진행 중 |
| Phase 4 | Extractor + Generalizer 자동화 (규칙 자동 추출/생성) | ⏸ 대기 |
| Phase 5 | Socratic / Contrarian / Planning Agent 통합 | ⏸ 대기 |
| Phase 6 | Jira / Confluence 연동 | ⏸ 대기 |

각 Phase에서 멈춰도 그 시점까지의 산출물은 독립적 가치를 가진다.

---

## 참고한 자료

- [Q00/ouroboros](https://github.com/Q00/ouroboros) — Ambiguity 수치화, Double Diamond, Persona Rotation 개념
- [razzant/ouroboros](https://github.com/razzant/ouroboros) — 자기 수정과 Multi-Model Review 개념
- 지피터스 사례 (뽀짝이-뽀야 2단 멘토 구조) — 에이전트 간 검토 패턴
- 빌더 조쉬 Claude Code 영상 — "Harness에 95% 시간" 원칙

---

*"타인에게 할 수 있는 비판을 자신에게도 할 수 있을 때, 비로소 혼자 개발이 가능하다."*
