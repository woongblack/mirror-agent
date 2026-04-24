# Mirror Agent

> 1인 개발자가 자기 자신에게 못 던지는 질문을, 대신 던져주는 에이전트 팀.

---

## 현재 상태

| 단계 | 상태 | 비고 |
| --- | --- | --- |
| Phase 0: 문서화 | ✅ 완료 | README, 대화 로그, 파이프라인 설계, 로드맵 |
| Phase 1: 레포 초기화 | ✅ 완료 | 프로젝트 구조, Pydantic 모델, 규칙 JSON, Loader |
| Phase 2: Re-Applicator v0.1 | ✅ 완료 | 전체 파이프라인 + Ground Truth 3/3 재현 |
| Phase 3: 실사용 + 개선 | ✅ 완료 | Precision 100% (9/9 수용) |
| Phase 4: 규칙 자동화 | ✅ 완료 | Extractor + Generalizer + HITL (auto 규칙 5개) |
| Phase 5: 다중 에이전트 통합 | ✅ 완료 | Socratic + Contrarian + Planning Agent |
| Phase 6: 외부 연동 | ⏸ 입사 후 | Jira / Confluence |

### 검증 결과 (2026-04-24 기준)

- Ground Truth 3/3 전부 재현 ✅
- Precision 100% (9개 비판 전체 수용) ✅
- auto 규칙 3개 신규 각도 발동 확인 ✅
- `mirror review --full`: Historical + Socratic + Contrarian 병렬 실행, **총 20개 질문** 생성 ✅

---

## 왜 만드는가

이 프로젝트는 **좋은 아이디어가 있어서** 시작한 게 아니다.
두 번의 실패에서 **같은 패턴**을 발견했기 때문에 시작했다.

### 첫 번째 실패 — DEKK (팀 프로젝트)

DEKK는 무신사 Snap을 클론한 팀 프로젝트였다. 나는 팀원들에게 물었다.

- "그래서 이 이후에는 어떻게 할 건데?"
- "셀러는 어떻게 구할 건데?"
- "Snap 클론이면, 결국 똑같아지는 거 아니냐?"

팀은 제대로 답하지 않았다. "클론한 게 의미 없다는 거냐"는 식으로 내 질문 자체가 이상한 것으로 몰렸다. 나는 팀을 나왔다.

### 두 번째 실패 — ALLBLUE (1인 프로젝트)

팀의 한계를 벗어나고 싶어서 ALLBLUE를 혼자 시작했다. 파편화된 상품을 AI로 엮는 크로스셀러 룩북 플랫폼. Spring Boot 3.5, Redis Streams, Saga 패턴까지 진지하게 구현했다.

몇 달 후, 내가 만든 README를 다시 읽어보다가 깨달았다.

**내가 DEKK 팀에게 던졌던 질문을, 나 자신에게는 한 번도 던지지 않았다.**

- "그래서 크로스셀러 상품 모은 다음에 어떻게 할 건데?"
- "카페24 셀러들이 왜 ALLBLUE에 들어올 건데?"
- "AI 합성이 붙은 Snap 클론 아닌가?"

타인에게는 날카롭게 던질 수 있는 질문을, 내 프로젝트에는 던지지 못했다.

### 공통된 문제

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

사용자의 과거 궤적(이전 프로젝트, 과거 비판, 인정한 맹점)을 학습해 **현재 문서에 기계적으로 재적용한다.**

**2. 비판은 감정 없는 존재에게서 와야 한다**

인간 비판자는 관계, 체면, 분위기에 휘둘린다. 에이전트는 그런 변수가 없다. 5번 물어도 똑같이 묻는다.

**3. 타인에게 할 수 있는 비판을 자신에게도 적용한다**

범용 LLM은 "일반적 비판"을 한다. Mirror Agent는 **"당신이 과거에 타인에게 던진 바로 그 질문"을 현재 문서에 적용한다.**

---

## 최종 시스템 워크플로우

```
① 패턴화 (Patternization)
   과거 대화 로그
        → Extractor   → Critique Unit 추출     ✅ 완료
        → Generalizer → 비판 규칙 DB 자동 생성  ✅ 완료 (HITL 승인)

        ↓

② 초안 기획 (Planning)
   날 아이디어
        → Planning Agent (Ouroboros 3라운드)    ✅ 완료
        → 구조화된 1차 기획안

        ↓

③ 기획 구체화 (Critique)
   기획안
        → Historical Agent: 과거 비판 패턴 재적용  ✅ 완료
        → Socratic Agent:   숨겨진 가정 드러내기   ✅ 완료
        → Contrarian Agent: 반대 시나리오 탐색      ✅ 완료
        → 사용자 수용/반려 → 기획 보완 → 반복

        ↓

④ 구현 계획 (Jira/Confluence)                    ⏸ 입사 후
   검증된 기획안 → Jira 티켓 자동 발행
```

---

## 에이전트 구성

### 비판 에이전트 팀 (핵심)

| 에이전트 | 역할 | 커맨드 |
| --- | --- | --- |
| **Historical Agent** | 과거 비판 패턴을 현재 문서에 재적용. 이 프로젝트의 핵심 차별점. | `mirror review` |
| **Socratic Agent** | 문서의 숨겨진 가정을 드러낸다. 5가지 각도(시장/기술/운영/동기/경쟁). | `mirror socratic` |
| **Contrarian Agent** | 핵심 주장의 반대 전제를 탐색한다. 구체적 시나리오와 함의까지. | `mirror contrarian` |

**Orchestrator** (`mirror review --full`): 3개 에이전트를 병렬 실행하고 severity 기준으로 통합 리포트 생성.

### Planning Agent (구조화자)

날 아이디어 텍스트를 Ouroboros Loop로 구조화된 기획안으로 변환한다.
Socratic/Contrarian을 내부에서 활용해 라운드마다 기획을 정제한다.

```bash
mirror plan <idea_file>
```

### Historical Agent 내부 파이프라인

```
[과거 대화 로그]
      ↓
  Stage 1: Extractor      → Critique Unit 추출          ✅ 완료
      ↓
  Stage 2: Generalizer    → 추상 규칙 자동 생성 (HITL)   ✅ 완료
      ↓
  Stage 3: Re-Applicator  → 현재 문서에 적용 + 리포트     ✅ 완료
```

현재 규칙: 수동 8개 + 자동 생성 5개 = **총 13개**

---

## 첫 번째 테스트 케이스 — ALLBLUE README

이 도구의 첫 번째 적용 대상은 **내 다른 프로젝트인 ALLBLUE**였다.

- 입력: ALLBLUE README
- Historical 비판 9개, Socratic 질문 8개, Contrarian 시나리오 3개 = **총 20개**
- Critical Hit: `rule_supplier_first` — "카페24 셀러를 어떻게 확보할 것인가?"
- Precision 100% (전체 수용)

이 결과를 반영해 ALLBLUE의 상업적 방향을 보류하고 **기술 탐구 + Mirror Agent 테스트베드**로 포지션을 재정의했다.

---

## 기술 스택

| 항목 | 기술 |
| --- | --- |
| 언어 | Python 3.12 |
| LLM | Anthropic Claude (Haiku: Extractor/Matcher, Sonnet: Generator/Defender/Agents) |
| SDK | `anthropic` Python SDK (structured output via tool use) |
| CLI | Click + Rich |
| 데이터 모델 | Pydantic v2 |
| 패키지 관리 | uv |
| 규칙 저장 | 로컬 JSON + Git 버전 관리 |
| 외부 연동 (예정) | Atlassian MCP (Jira / Confluence) |

기술 선택의 원칙: **Harness에 95% 시간, Execution에 5%.** 에이전트 개수를 늘리기보다 컨텍스트 주입에 투자한다.

---

## 자주 쓰는 커맨드

```bash
# 설치
uv sync

# 테스트
uv run pytest -m "not integration"

# Historical Agent (13개 규칙 적용)
uv run mirror review <document>

# 3개 에이전트 통합 실행
uv run mirror review --full <document>

# 개별 에이전트
uv run mirror socratic <document>
uv run mirror contrarian <document>

# Planning Agent (아이디어 → 기획안)
uv run mirror plan <idea_file>

# 규칙 자동화 파이프라인
uv run mirror extract <conversation_log>
uv run mirror generalize <critiques_json>
```

---

## 이 프로젝트가 실패할 조건

정직하게 적는다.

1. 내가 만든 에이전트의 비판을 내가 받아들이지 않으면 실패다. DEKK 팀이 내 비판을 방어했던 것처럼, 내가 에이전트를 방어하기 시작하면.
2. 내가 이 도구를 실제로 매주 쓰지 않으면 실패다. "만들어놓고 안 쓰는 도구"가 되면.
3. Historical Agent가 단순 RAG 이상의 가치를 못 내면 실패다. 과거 비판을 현재에 적용하는 메타 추론이 동작하지 않으면.

---

## 참고한 자료

- [Q00/ouroboros](https://github.com/Q00/ouroboros) — Ambiguity 수치화, Double Diamond, Persona Rotation 개념
- [razzant/ouroboros](https://github.com/razzant/ouroboros) — 자기 수정과 Multi-Model Review 개념
- 지피터스 사례 (뽀짝이-뽀야 2단 멘토 구조) — 에이전트 간 검토 패턴
- 빌더 조쉬 Claude Code 영상 — "Harness에 95% 시간" 원칙

---

*"타인에게 할 수 있는 비판을 자신에게도 할 수 있을 때, 비로소 혼자 개발이 가능하다."*
