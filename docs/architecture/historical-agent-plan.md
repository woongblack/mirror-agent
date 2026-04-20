# Historical Agent — Pipeline Architecture Plan

> Mirror Agent의 핵심 컴포넌트. 사용자가 과거 타인에게 던진 비판을 현재 자기 문서에 기계적으로 재적용하는 3-Stage 파이프라인.

**문서 상태:** v0.1 설계 초안  
**작성일:** 2026-04-19  
**근거 문서:** `/docs/origin/conversation-log.md`

---

## 1. 이 문서의 범위

Mirror Agent를 구성하는 3개 에이전트(Socratic, Contrarian, Historical) 중 **Historical Agent 단독의 내부 파이프라인**을 다룬다. 다른 에이전트와의 오케스트레이션은 별도 문서에서 다룬다.

이 문서는 **v0.1 구현 착수를 위한 설계**이며, 구현 과정에서 발견된 제약은 Git 커밋 히스토리로 추적한다.

---

## 2. 풀려는 문제

### 문제 정의 (한 문장)

사용자가 과거 타인에게 던진 날카로운 비판을, 현재 자기 자신의 문서에 기계적으로 재적용한다.

### 왜 단순 RAG로는 부족한가

단순 벡터 검색 + 프롬프트 주입 방식은 "과거에 이런 말을 했다"는 **회상**만 제공한다. 사용자가 필요로 하는 것은 **"이 비판이 지금 내 문서에도 구조적으로 성립한다"는 재적용**이다.

### 필요한 3단계 추론

| 레벨 | 내용 | 예시 |
| --- | --- | --- |
| L1 (표면) | 과거 발화 그대로 | "셀러는 어떻게 구할 건데?" |
| L2 (일반화) | 사고 패턴 추출 | "플랫폼 프로젝트에서는 공급자 확보 전략이 선행되어야 한다" |
| L3 (재적용) | 현재 문서에 매핑 | "ALLBLUE는 플랫폼이다. 카페24 셀러 확보 전략이 있는가?" |

L1 → L2 → L3 점프가 Historical Agent의 기술적 심장이다.

---

## 3. 3-Stage 파이프라인 개요

```
┌─────────────────────────────────────────────────────────┐
│  입력: 과거 대화 로그, 프로젝트 문서, 회의록                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Stage 1: Extractor                                      │
│  - 비판 발화 식별 및 구조화                                │
│  - 출력: Critique Unit (JSON)                            │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Stage 2: Generalizer                                    │
│  - 비판 유닛 → 재사용 가능한 규칙으로 추상화               │
│  - 출력: Critique Rule (JSON)                            │
│  - HITL 검증: GitHub PR 승인 방식                          │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  Stage 3: Re-Applicator                                  │
│  - 현재 문서에 규칙 매칭 및 질문 생성                      │
│  - 방어 예측 포함                                         │
│  - 출력: Critique Report (Markdown)                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│  출력: 사용자에게 제시되는 비판 리포트                     │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Stage 1 — Extractor 설계

### 역할
과거 텍스트(대화 로그, 회의록, 프로젝트 문서)에서 "비판 발화"를 식별하고 구조화한다.

### 입력
- 마크다운 형식의 과거 텍스트
- 예: `conversation-log.md`, `meeting-notes/*.md`

### 출력 스키마 (Critique Unit)

```json
{
  "id": "critique_001",
  "source": "conversation-log.md#phase7",
  "raw_text": "셀러는 어떻게 구할 건데?",
  "target_project": "DEKK",
  "target_type": "team_project",
  "domain": "platform/marketplace",
  "critique_category": "supplier_acquisition",
  "emotional_marker": "neutral_skeptical",
  "context": "클론 제품의 차별화 부재 지적 중",
  "extracted_at": "2026-04-19T14:30:00Z"
}
```

### 필드 정의

| 필드 | 용도 |
| --- | --- |
| `target_type` | 비판 대상의 성격. `team_project` / `personal_project` / `tech_decision` / `market_judgment` 중 하나 |
| `domain` | 도메인 태깅. Generalizer의 클러스터링 기준 |
| `critique_category` | 비판 유형. `supplier_acquisition` / `differentiation` / `scaling` / `validation_absence` 등 |
| `emotional_marker` | 발화의 감정 톤. 동일 패턴이라도 강도가 다를 수 있음 |
| `context` | 이 비판이 왜 나왔는지의 주변 맥락 |

### 구현 방식
- LLM + 구조화 출력 (JSON schema 강제)
- 모델: 비용 저렴 버전 사용 (Claude Haiku / GPT-4o-mini)
- 배치: 문서 통째로 1회 호출

### 실패 모드 & 대응
- **오탐**: 비판 아닌 발화를 비판으로 추출 → HITL 검증에서 걸러냄
- **누락**: 중요한 비판 놓침 → Ground truth 셋 기반 재현율 측정

---

## 5. Stage 2 — Generalizer 설계

### 역할
여러 Critique Unit을 군집화하여 재사용 가능한 추상 규칙으로 추출한다.

### 입력
- Stage 1의 Critique Unit 리스트
- (옵션) 기존 규칙 DB (점진적 업데이트용)

### 출력 스키마 (Critique Rule)

```json
{
  "rule_id": "rule_supplier_first",
  "rule_name": "공급자 확보 전략 선행 원칙",
  "trigger_conditions": {
    "target_type_in": ["platform", "marketplace", "two_sided_market"],
    "has_supply_side": true,
    "has_demand_side": true
  },
  "critique_template": "이 플랫폼이 {supply_side}를 어떻게 확보할 것인가?",
  "evidence_questions": [
    "{supply_side}가 이 플랫폼에 참여할 경제적 동기가 있는가?",
    "경쟁 플랫폼 대신 이곳을 선택할 이유가 있는가?",
    "초기 N개의 {supply_side}를 어떻게 확보할 것인가?"
  ],
  "source_critique_ids": ["critique_001", "critique_003"],
  "user_conviction_level": "high",
  "created_at": "2026-04-19T14:35:00Z",
  "validated_by_user": false
}
```

### 필드 정의

| 필드 | 용도 |
| --- | --- |
| `trigger_conditions` | 어떤 문서에 이 규칙을 적용할지 결정. Re-Applicator가 매칭에 사용 |
| `critique_template` | 변수 슬롯 포함. 현재 문서 내용으로 치환되어 질문 생성 |
| `evidence_questions` | 파생 질문. 하나의 핵심 비판에 뒤따르는 검증 질문들 |
| `user_conviction_level` | 사용자가 이 비판을 얼마나 반복적으로 강하게 했는가. 우선순위 결정 |
| `validated_by_user` | HITL 검증 통과 여부. false면 자동 적용 안 함 |

### 구현 방식
- LLM 기반 클러스터링 + 추상화
- 모델: 고급 모델 필요 (Claude Sonnet/Opus) — 추상화 품질이 핵심
- 점진적 업데이트: 새 Critique Unit이 들어오면 기존 규칙과의 유사도 체크 후 병합 or 신규 생성

### HITL 검증 — GitHub PR 방식 (결정사항 반영)

1. Generalizer가 규칙 생성 → `rules/pending/` 폴더에 JSON 파일로 저장
2. GitHub Action이 자동 PR 생성 (PR 템플릿 포함)
3. 사용자가 PR 리뷰에서 승인/반려/수정
4. 머지되면 `rules/active/`로 이동

**PR 템플릿 예시:**
```markdown
## 신규 규칙 제안: {rule_name}

### 근거 비판 유닛
- {critique_id_1}: "{raw_text_1}"
- {critique_id_2}: "{raw_text_2}"

### 추출된 규칙
[JSON 내용]

### 질문
- 이 일반화가 과도하거나 부족하지 않은가?
- trigger_conditions가 적절한가?
```

### 실패 모드 & 대응
- **과잉 추상화**: "모든 프로젝트는 사용자 검증이 필요하다" 같은 공허한 규칙 → HITL 반려
- **과소 추상화**: 재사용 불가능한 너무 구체적인 규칙 → `user_conviction_level` 낮게 기록, 후순위 처리

### ⚠️ v0.1에서는 Generalizer 자동화 스킵

**솔직한 판단:** Generalizer는 기술적으로 가장 어렵고, v0.1에서 자동화해도 HITL 거부율이 높을 가능성이 크다. 

따라서 **v0.1에서는 사용자가 수동으로 규칙 10개를 작성**하여 시작한다. 수동 규칙으로 Re-Applicator가 동작함을 검증한 뒤, v0.2에서 Generalizer 자동화를 추가한다.

수동 규칙 초안은 `rules/active/` 아래에 바로 커밋한다. 해당 파일은 `rules/manual-v0.1/` 으로 별도 관리하여 이후 자동 생성된 규칙과 구분한다.

---

## 6. Stage 3 — Re-Applicator 설계

### 역할
현재 검토 대상 문서에 규칙을 매칭하여 구체적 비판 질문을 생성한다. 사용자의 방어를 예측한다.

### 입력
- 현재 문서 (예: ALLBLUE README.md)
- 활성 규칙 집합 (`rules/active/*.json`)
- (옵션) 사용자의 과거 방어 패턴 (`defense-patterns.json`)

### 처리 단계

**단계 1: 문서 분석**
- 현재 문서에서 메타 정보 추출: 프로젝트 유형, 도메인, 구성 요소
- 예: ALLBLUE README → `{type: "platform", has_supply: true, has_demand: true, domain: "fashion-commerce"}`

**단계 2: 규칙 매칭**
- 활성 규칙 중 `trigger_conditions`를 만족하는 것들 필터링
- 매칭 스코어링 (복수 조건 만족 시 우선순위)

**단계 3: 질문 생성**
- 매칭된 규칙의 `critique_template`에 문서 메타 정보 치환
- 예: `{supply_side}` → "카페24 셀러"

**단계 4: 문서 내 근거 구절 추출**
- 해당 비판과 관련된 문서 내 구절 인용
- 없으면 "문서에 해당 내용 없음"으로 명시

**단계 5: 방어 예측** ⭐ 이게 Mirror Agent의 고유 가치
- 사용자가 이 비판을 받았을 때 어떻게 방어할지 예측
- 그 방어의 약점 지적

### 출력 예시

```markdown
## Historical Agent Report — ALLBLUE README

### 🔴 비판 #1 — 공급자 확보 전략 부재

**적용된 규칙:** rule_supplier_first (확신도: high)

**과거 발화 근거:** 
DEKK 팀 회의에서 "셀러는 어떻게 구할 건데?"라는 비판을 하셨습니다. 
(출처: conversation-log.md#phase7)

**현재 문서에 적용된 질문:**
1. ALLBLUE가 카페24 셀러를 어떻게 확보할 것인가?
2. 카페24 셀러가 이미 자사몰/네이버/쿠팡/29CM에 입점해 있는데, 
   ALLBLUE에 추가로 입점할 경제적 동기가 있는가?
3. 초기 10~30개 셀러를 어떻게 확보할 계획인가?

**문서 내 관련 구절:**
> "Phase 3: 카페24 연동 + PortOne 통합 결제 + Saga"

이 로드맵은 "카페24 셀러가 있다"를 전제하고 있지만, 
확보 전략이 문서에 기술되지 않았습니다.

**당신의 예상 방어:**
- 예상 발화: "이건 Phase 3 얘기니까 나중에 생각하면 돼"
- 이 방어의 문제점: 
  DEKK에서 동일한 "나중에 생각하자" 논리가 프로젝트 실패의 원인이었습니다.
  공급자 확보는 후행 과제가 아니라 선행 검증 대상입니다.
```

### 구현 방식
- 문서 분석: LLM + 구조화 출력
- 매칭: 규칙 기반 필터링 (JSON 필드 매칭)
- 질문 생성: 템플릿 치환 + LLM 정제
- 방어 예측: 과거 방어 패턴 DB 기반 (없으면 LLM 추론)

### 실패 모드 & 대응
- **무관한 비판 생성**: 매칭 조건이 느슨 → `trigger_conditions` 엄격화
- **방어 예측 빗나감**: 사용자가 피드백 제공 → `defense-patterns.json` 업데이트
- **근거 구절 없음**: 문서에 해당 내용 자체가 없는 경우 → 오히려 강력한 비판 시그널

---

## 7. 데이터 저장 구조 (결정사항 반영)

### 결정: 로컬 JSON 파일 + Git 버전 관리

```
mirror-agent/
├── docs/
│   ├── origin/
│   │   └── conversation-log.md           # Extractor 입력
│   └── architecture/
│       └── historical-agent-plan.md      # 이 문서
│
├── data/
│   ├── critiques/                        # Stage 1 출력
│   │   ├── dekk-conversations.json
│   │   └── allblue-self-review.json
│   │
│   ├── rules/
│   │   ├── active/                       # 승인된 규칙
│   │   │   ├── rule_supplier_first.json
│   │   │   └── rule_differentiation.json
│   │   ├── pending/                      # 자동 생성 대기 (v0.2+)
│   │   │   └── rule_candidate_*.json
│   │   └── manual-v0.1/                  # v0.1 수동 작성
│   │       └── [수동 규칙 10개]
│   │
│   ├── defense-patterns.json             # 방어 예측용
│   │
│   └── reports/                          # Stage 3 출력 아카이브
│       ├── 2026-04-19_allblue-readme.md
│       └── ...
│
├── src/
│   ├── extractor/
│   ├── generalizer/                      # v0.2에서 구현
│   ├── reapplicator/
│   └── main.py
│
└── .github/
    └── workflows/
        └── rule-review.yml               # HITL PR 자동화
```

### Git 워크플로우
- 모든 규칙 생성/수정은 브랜치에서 시작
- PR 머지 == 규칙 활성화
- 커밋 메시지로 규칙 진화 과정 추적
- 목표: 3개월 후 `git log rules/` 으로 "나의 사고 패턴 진화사"를 볼 수 있음

---

## 8. 오케스트레이션 (결정사항 반영)

### 결정: Python async

```python
async def historical_agent_pipeline(document_path: str) -> CritiqueReport:
    # Stage 3만 수행 (Stage 1, 2는 별도 파이프라인에서 사전 완료)
    
    # 1. 문서 분석
    doc_meta = await analyze_document(document_path)
    
    # 2. 활성 규칙 로드
    rules = load_rules("data/rules/active/")
    
    # 3. 매칭
    matched_rules = match_rules(doc_meta, rules)
    
    # 4. 병렬 질문 생성
    tasks = [
        generate_critique(rule, doc_meta, document_path)
        for rule in matched_rules
    ]
    critiques = await asyncio.gather(*tasks)
    
    # 5. 방어 예측 (병렬)
    defense_tasks = [
        predict_defense(c, defense_patterns)
        for c in critiques
    ]
    critiques_with_defense = await asyncio.gather(*defense_tasks)
    
    # 6. 리포트 조립
    return assemble_report(critiques_with_defense)
```

**왜 LangGraph를 안 쓰는가:**
- Historical Agent는 상태가 복잡하지 않음 (선형 파이프라인)
- 프레임워크 학습 곡선 > 얻는 가치
- v0.5에서 Socratic/Contrarian과 결합할 때 필요하면 도입

---

## 9. HITL — GitHub PR 워크플로우 (결정사항 반영)

### 결정: GitHub PR 기반 승인

### v0.2 자동 PR 생성 흐름

```yaml
# .github/workflows/rule-review.yml (개념)
on:
  push:
    paths: ['data/rules/pending/**']

jobs:
  create-review-pr:
    steps:
      - name: Parse new rule
      - name: Create branch
      - name: Move file to rules/active/
      - name: Create PR with template
      - name: Request review from owner
```

### PR 리뷰 체크리스트 (사용자 본인이 체크)

- [ ] 이 규칙이 실제 내 사고 패턴을 반영하는가?
- [ ] trigger_conditions가 너무 넓거나 좁지 않은가?
- [ ] evidence_questions가 단순 반복이 아닌 유효한 검증 질문인가?
- [ ] user_conviction_level이 적절한가?

### 이 방식의 이점
- **규칙 진화사가 커밋 로그로 남음** → 포트폴리오 자산
- **리뷰 코멘트가 곧 추가 학습 데이터** → "왜 이 규칙을 반려했는가"가 다음 Generalizer 튜닝 재료
- **UI 구축 비용 제로**

---

## 10. v0.1 성공 기준

### 정량 기준

**Ground Truth:** `conversation-log.md`의 "반사실적 데이터" 섹션에 있는 3개 비판

1. ALLBLUE README → "Snap 클론에 AI 붙인 것 아닌가?" 질문
2. Phase 3 로드맵 → "Phase 1 검증 실패 시 이 설계는?" 질문
3. 자율 검수 에이전트 설계서 → "에이전트 5개가 정말 필요한가?" 질문

**합격선:** Re-Applicator가 위 3개 중 **최소 2개를 자동 생성**

### 정성 기준

- 사용자(본인)가 리포트를 읽고 "아 이건 내가 타인에게 했을 법한 질문이다"라고 느끼는가?
- 리포트의 질문이 일반 LLM 비판("사용자 검증이 필요합니다")과 구분되는가?

### 실패 시 대응

- 수동 규칙의 질을 먼저 의심 (Generalizer 문제 아님)
- Re-Applicator의 템플릿 치환 로직 점검
- 방어 예측이 피상적이면 `defense-patterns.json`에 수동 패턴 추가

---

## 11. 로드맵

| 단계 | 내용 | 상태 |
| --- | --- | --- |
| v0.1 | 수동 규칙 10개 + Re-Applicator 구현 + ALLBLUE 테스트 | **착수 예정** |
| v0.2 | Extractor 자동화 | 계획 |
| v0.3 | Generalizer 자동화 + GitHub PR 워크플로우 | 계획 |
| v0.4 | 방어 예측 고도화 (사용자 피드백 루프) | 계획 |
| v0.5 | Socratic / Contrarian Agent와 통합 | 계획 |

---

## 12. 미해결 이슈 (구현 중 결정)

- [ ] `user_conviction_level` 기준을 어떻게 정할 것인가? (빈도? 강도? 시간?)
- [ ] 규칙 충돌 시 우선순위 (높은 conviction 우선? 최근 규칙 우선?)
- [ ] 방어 패턴 DB를 수동 vs 자동 학습 중 무엇으로 갈 것인가
- [ ] Stage 1 Extractor의 False Positive 허용 수준

---

*"타인에게 할 수 있는 비판을 자신에게도 할 수 있을 때, 비로소 혼자 개발이 가능하다."*
