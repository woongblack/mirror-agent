# Mirror Agent 프로젝트 컴팩트 요약

> 이 문서는 여러 세션에 걸친 대화를 압축한 것이다.
> 다음 세션/Claude Code에서 맥락 복원용.

**최종 업데이트:** 2026-04-23

---

## 1. 최종 포지셔닝

**Mirror Agent** = 1인 개발자의 자기 비판 맹점을 해결하는 메타 도구.

- 사용자가 과거 **타인에게 던진 비판**을 현재 **자기 문서**에 기계적으로 재적용
- 핵심 차별점: Historical Agent (일반 LLM 비판 도구에 없는 고유 기능)
- 개발 동기: **카페24 지원용 포트폴리오 + 실제 자기 객관성 상실 문제 해결**

## 2. 세 프로젝트의 관계

```
DEKK (팀, 부트캠프)
  ↓ 집단적 객관성 상실 경험
ALLBLUE (1인, Java/Spring Boot)
  ↓ 개인적 객관성 상실 발견
Mirror Agent (1인, Python + Anthropic API)
  → 자기 비판을 시스템화
```

**서사 핵심:** DEKK에서 당신이 팀에 던진 질문("Snap 클론 아니냐", "셀러 어떻게 구할 건데")을, ALLBLUE에서 자기 자신에겐 못 던졌다는 자각. 그래서 Mirror Agent를 만듦.

## 3. 사용자 핵심 인정 (Historical Agent 학습 데이터)

- "나 스스로의 객관성이 혼자 하다 보니 많이 떨어진 것 같아. 인정할게."
- "좋은 사업 아이디어까지는 아니야. 하나의 프로젝트 정도로 생각하는 거지."
- ALLBLUE 진짜 동기 = "내가 생각한대로 바로 구현할 수 있는 자유"

## 4. 기술 스택 (확정)

- Python 3.11+ / uv
- **Anthropic API** (Claude Sonnet 4.6 + Haiku 4.5)
- Pydantic 2
- CLI: Click + Rich
- 데이터: 로컬 JSON (v0.1) → MySQL (v0.2+)
- HITL: GitHub PR 기반
- 오케스트레이션: Python async (LangGraph 안 씀)

## 5. v0.1 구현 상태 (현재)

✅ **완성된 모듈:**
- `models.py` — 전체 Pydantic 스키마
- `loader.py` — 규칙/패턴 JSON 로더
- `config.py` — 환경변수 기반 설정
- `llm.py` — Anthropic SDK 래퍼
- `analyzer.py` — 문서 → DocumentMetadata
- `matcher.py` — LLM 기반 trigger_conditions 판정 (Evidence 필수)
- `generator.py` — 템플릿 치환 + 질문 생성
- `defender.py` — 방어 예측 (핵심 차별 기능)
- `reporter.py` — Markdown 리포트 렌더링
- `pipeline.py` — 전체 async 파이프라인 조립

🔶 **부분 구현:**
- `cli.py` — main(), rules() 서브커맨드 stub 상태
- `scorer.py` — novelty_score 미구현 (v0.2로 연기 확정)

⏸ **대기:**
- 실제 실행 검증 (ANTHROPIC_API_KEY 필요, **카드 충전 대기 중**)

## 6. 핵심 설계 원칙 (변경 금지)

1. **Harness 95% / Execution 5%**
2. **Evidence 필수** — LLM 출력은 문서 인용 근거 필수, "추측 금지" 프롬프트
3. **방어 모드 유발 회피** — 표시 비판 최대 3개 (Top N)
4. **v0.1 = Historical Agent 단독** — Socratic/Contrarian은 Phase 5로 연기
5. **방어 예측은 v0.1 필수** — Mirror Agent의 진짜 고유 가치

## 7. v0.1 합격 기준

```
[Recall]       ground truth 3건 중 2건 이상 유사 질문 생성
[Precision]    전체 생성 비판 중 50% 이상 사용자 "타당" 판정
[Critical Hit] rule_supplier_first에서 파생된 비판 반드시 포함
[Novelty]      일반 LLM 비판과 구분 가능 (수동 블라인드 평가)
```

## 8. 수동 규칙 8개 (활성)

1. `rule_supplier_first` (high, Critical Hit 대상)
2. `rule_differentiation_explicit` (high)
3. `rule_post_mvp_concreteness` (high)
4. `rule_user_need_evidence` (high)
5. `rule_solo_operability` (medium_high)
6. `rule_hypothetical_language_detector` (medium)
7. `rule_defensive_response_check` (medium)
8. `rule_motivation_honesty` (medium)

+ SEED 2개 대기 중

## 9. 방어 패턴 5개 (Historical Agent 학습용)

- `defense_later_phase` — "Phase 3 얘기니까 나중에"
- `defense_technical_framing` — 사용자 니즈 질문을 기술 난이도로 전환
- `defense_hypothetical_affirmation` — "~라고 생각했어" 같은 가정형 언어
- `defense_attribution_to_others` — 구조 문제를 개인 역량 문제로 환원
- `defense_scope_expansion` — 범위 축소 제안에 "그런데 이것도 필요하고"

## 10. 결정된 정책 4가지

| 영역 | 결정 |
|---|---|
| trigger_conditions 판정 | LLM + Evidence 필수 + "추측 금지" |
| 규칙 동시 발동 | 전부 발동, 상위 3개만 표시, 나머지는 collapsed |
| v0.1 범위 | Historical Agent 단독 + 방어 예측 필수 |
| 합격 기준 | Recall/Precision/Critical Hit/Novelty 4조건 |

## 11. 카페24 지원 관련 현재 계획

- **1순위 지원처, 상시 채용 중**
- **타이밍:** 빨리 지원 목표 (1주 이내)
- **자산:**
  - ALLBLUE BE (602 commits, Spring Boot, 카페24 OAuth 중심 재구성 완료)
  - Mirror Agent (스캐폴드 + 핵심 코드 완료, 실행 검증 대기)
  - ALLBLUE FE (org 정책으로 README 재작성 불가 → 이력서에서 제외)

## 12. 남은 액션 (우선순위)

### 단기 (이번 주)
1. **카드 충전 후 ANTHROPIC_API_KEY 발급** (사용자가 집에서)
   - 체크카드/가상카드도 가능 (토스, 카카오뱅크 등)
   - $5 충전으로 v0.1 검증 충분
2. **CLI 완성** — Claude Code로 main(), rules() 서브커맨드
3. **실제 실행** — `uv run mirror review tests/fixtures/allblue-readme-snapshot.md`
4. **리포트 검증** — ground_truth.json 대비 측정
5. **ALLBLUE BE README에 "Mirror Agent 자체 검토" 섹션 추가**
6. **이력서/자기소개서 작성**
7. **카페24 지원**

### 중기 (면접 대응 병행)
- `scorer.py` novelty 구현
- FastAPI 관리 API + MySQL (JD 요건 추가 증명)
- n8n 실제 워크플로우 연결
- 사용 대시보드 (Streamlit)

### 연기 (Phase 5+)
- Socratic/Contrarian Agent
- Generalizer 자동화
- Jira/Confluence MCP 연동

## 13. 주의사항 (의사결정 시 체크)

### 하지 말 것
- ❌ 에이전트 개수 늘리기 (Phase 5까지 금지)
- ❌ LiteLLM 같은 추상화 레이어 도입 (YAGNI)
- ❌ 상위 표시 3개 초과로 늘리기
- ❌ "더 친절한" 프롬프트로 바꾸기

### 의심하고 재확인할 것
- 🔍 새 기능 제안 → Rule 5 (1인 운영 가능성) 자기 적용
- 🔍 "있어야 할 것 같아서" → 즉시 중단
- 🔍 합리화 언어 ("나중에 필요할 것 같아서") → Defense Pattern 자기 적용

## 14. 파일 구조 (레포: woongblack/mirror-agent)

```
mirror-agent/ (Public on GitHub)
├── README.md                          ✅ 완성
├── CLAUDE.md                          ✅ 프로젝트 SOP
├── pyproject.toml                     ✅ uv 기반
│
├── src/mirror_agent/
│   ├── models.py                      ✅
│   ├── loader.py                      ✅
│   ├── config.py                      ✅
│   ├── llm.py                         ✅ (Anthropic SDK)
│   ├── analyzer.py                    ✅
│   ├── matcher.py                     ✅
│   ├── generator.py                   ✅
│   ├── defender.py                    ✅ (핵심 차별 기능)
│   ├── reporter.py                    ✅
│   ├── pipeline.py                    ✅
│   ├── cli.py                         🔶 부분 구현
│   └── scorer.py                      🔶 stub (v0.2 연기)
│
├── data/
│   ├── rules/manual-v0.1/             ✅ 8개 규칙 JSON
│   └── defense-patterns/patterns.json ✅ 5개 패턴
│
├── docs/
│   ├── origin/conversation-log.md     ✅ 프로젝트 기원 대화
│   ├── architecture/
│   │   └── historical-agent-plan.md   ✅ 파이프라인 설계
│   └── roadmap.md                     ✅
│
├── eval/
│   └── ground_truth.json              ✅ 3건 + 보너스 2건
│
└── tests/
    ├── test_loader.py
    └── fixtures/
        └── allblue-readme-snapshot.md ✅ 재현성 고정
```

## 15. 다음 세션 시작할 때 할 말

Claude Code든 새 Claude 세션이든, 이 문서(compact-summary.md) + CLAUDE.md + conversation-log.md 이 세 개 읽게 하고 시작하면 맥락 완전 복원됨.

**다음 첫 행동:**
1. `uv run mirror rules list` 동작 확인
2. `.env`에 ANTHROPIC_API_KEY 설정
3. `uv run mirror review tests/fixtures/allblue-readme-snapshot.md` 실행
4. 리포트 결과 검토
5. 결과에 따라 다음 단계 결정

---

## 16. 메타 — 이 대화에서 검증된 것

Mirror Agent의 철학이 **이 대화 자체에서 이미 증명됨**:

- 사용자가 초기에 "자율 검수 에이전트 팀" 아키텍처 가져옴
- 대화 진행하며 여러 차례 방향 수정 + 자기 인정
- 최종적으로 "자기 객관성 상실 도구"로 수렴
- 이 과정 자체가 Mirror Agent가 해야 할 일의 수동 시뮬레이션

**이 대화 로그 = Historical Agent의 첫 학습 데이터.**

---

*"타인에게 할 수 있는 비판을 자신에게도 할 수 있을 때, 비로소 혼자 개발이 가능하다."*