# Mirror Agent v0.1 — Manual Rules

> 이 파일은 v0.1의 수동 작성 규칙 모음이다.
> 
> Generalizer 자동화 이전 단계에서, 사용자가 직접 자신의 사고 패턴을 언어화한 결과물이다.
> 
> **근거 자료:** `/docs/origin/conversation-log.md`
>
> **작성일:** 2026-04-19
>
> **작성 원칙:**
> - 한 번의 발화만으로 규칙화하지 않는다 (근거 얇음)
> - 확신도를 정직하게 기록한다 (억지로 `high` 붙이지 않는다)
> - 근거가 약한 규칙은 `seed` 상태로 두고, 추가 근거가 쌓이면 활성화한다

---

## 확신도 분류

| 레벨 | 의미 | v0.1 활성화 |
| --- | --- | --- |
| `high` | 대화에서 명시적/반복적으로 드러남 | ✅ 활성 |
| `medium` | 한 번의 발화지만 패턴이 뚜렷함 | ✅ 활성 (주의 표시) |
| `seed` | 근거 부족. 추가 관찰 필요 | ⏸ 대기 |

---

## Rule 1 — 공급자 확보 전략 선행 원칙 ⭐

```json
{
  "rule_id": "rule_supplier_first",
  "rule_name": "공급자 확보 전략 선행 원칙",
  "confidence": "high",
  "trigger_conditions": {
    "target_type_in": ["platform", "marketplace", "two_sided_market", "aggregator"],
    "has_supply_side": true,
    "has_demand_side": true
  },
  "critique_template": "이 플랫폼이 {supply_side}를 어떻게 확보할 것인가?",
  "evidence_questions": [
    "{supply_side}가 이 플랫폼에 참여할 경제적 동기가 있는가?",
    "{supply_side}가 이미 다른 채널(기존 플랫폼)에 참여하고 있다면, 여기에 추가로 참여할 이유가 있는가?",
    "초기 N개의 {supply_side}를 어떻게 확보할 구체적 계획이 있는가?",
    "확보 전략은 문서에 기술되어 있는가, 암묵적 전제로만 있는가?"
  ],
  "source_critiques": [
    "DEKK 팀에게 '셀러는 어떻게 구할 건데?' 질문 (conversation-log.md#phase6)",
    "ALLBLUE 자체 검토에서 카페24 셀러 확보 전략 부재 확인 (conversation-log.md#phase7)"
  ],
  "user_conviction_level": "very_high",
  "notes": "사용자가 DEKK에서 타인에게 한 비판이 ALLBLUE에서 동일 구조로 재현된 사례. 이 프로젝트의 가장 강력한 근거 규칙."
}
```

---

## Rule 2 — 차별화 지점 명시 원칙 ⭐

```json
{
  "rule_id": "rule_differentiation_explicit",
  "rule_name": "클론의 차별화 지점은 명시되어야 한다",
  "confidence": "high",
  "trigger_conditions": {
    "document_mentions_similar_product": true,
    "OR_similarity_to_existing_service_high": true
  },
  "critique_template": "이것이 {existing_service}의 클론이라면, 차별화 지점은 무엇이며 문서에 명시되어 있는가?",
  "evidence_questions": [
    "{existing_service}가 이미 해결한 문제를 재해결하려는 것이 아닌가?",
    "차별화 지점이 사용자 가치인가, 만드는 사람의 기술적 흥미인가?",
    "사용자가 {existing_service} 대신 이것을 선택할 구체적 이유가 있는가?",
    "차별화 지점은 테스트 가능한 가설로 표현되어 있는가?"
  ],
  "source_critiques": [
    "DEKK 팀에게 'Snap 클론이면 똑같아지는 거 아니냐?' 질문 (conversation-log.md#phase7)",
    "ALLBLUE 자체 검토에서 'AI 합성 붙인 Snap 클론 아니냐?' 재적용 가능성 발견"
  ],
  "user_conviction_level": "very_high",
  "notes": "사용자 본인이 명시적으로 '클론 자체는 문제가 아니다, 차별점이 문제다'라고 발화함. 가치 판단이 분명한 규칙."
}
```

---

## Rule 3 — 이후 단계 구체성 원칙 ⭐

```json
{
  "rule_id": "rule_post_mvp_concreteness",
  "rule_name": "첫 단계 이후의 구체적 계획 원칙",
  "confidence": "high",
  "trigger_conditions": {
    "document_has_phased_roadmap": true,
    "OR_document_describes_mvp_only": true
  },
  "critique_template": "이 {current_phase}가 완료된 이후, 다음 단계는 무엇이며 구체적으로 기술되어 있는가?",
  "evidence_questions": [
    "현재 Phase가 성공했을 때 다음 Phase로의 전환 조건은 무엇인가?",
    "현재 Phase가 실패했을 때 다음 Phase는 어떻게 되는가?",
    "다음 Phase의 자원/전제조건이 현재 Phase에서 확보되는가?",
    "'나중에 생각하자'의 '나중에'가 언제인지 정의되어 있는가?"
  ],
  "source_critiques": [
    "DEKK 팀에게 '그래서 이 이후에는 어떻게 할 건데?' 질문 (conversation-log.md#phase6)",
    "ALLBLUE Phase 3(통합결제) 설계가 Phase 1 검증 전에 이미 전제됨"
  ],
  "user_conviction_level": "very_high",
  "notes": "DEKK에서 던진 질문이 ALLBLUE 로드맵에도 그대로 재적용됨."
}
```

---

## Rule 4 — 사용자 니즈 증거 원칙 ⭐

```json
{
  "rule_id": "rule_user_need_evidence",
  "rule_name": "사용자 니즈는 추측이 아닌 증거를 요구한다",
  "confidence": "high",
  "trigger_conditions": {
    "document_claims_user_value": true,
    "OR_document_describes_user_problem": true
  },
  "critique_template": "사용자가 '{claimed_need}'를 원한다는 증거가 문서에 있는가, 아니면 작성자의 추측인가?",
  "evidence_questions": [
    "사용자 인터뷰, 설문, 기존 서비스의 불만 데이터 중 어떤 근거가 있는가?",
    "이 니즈가 기존에 해결되지 않은 이유는 무엇인가?",
    "경쟁 서비스가 이 기능을 제공하지 않는 이유가 '기술 부족'인가 '니즈 부재'인가?",
    "'~라고 생각했어', '~라면', '~할 수 있을 거라고' 같은 가정형 언어로만 표현되어 있지 않은가?"
  ],
  "source_critiques": [
    "ALLBLUE 자체 검토에서 '다양한 코디'가 실제 사용자 니즈인지 검증 없음 (conversation-log.md#phase7)",
    "사용자 본인의 가정형 언어 사용 다수 관찰"
  ],
  "user_conviction_level": "high",
  "notes": "이 규칙은 사용자가 타인에게 직접 발화한 근거는 약하지만, 대화에서 외부 지적을 수용한 사례가 강력함. '가정형 언어'를 실제 탐지 기준으로 포함."
}
```

---

## Rule 5 — 1인 운영 가능성 원칙 ⭐

```json
{
  "rule_id": "rule_solo_operability",
  "rule_name": "1인 운영 가능성 검증 원칙",
  "confidence": "high",
  "trigger_conditions": {
    "project_is_solo": true,
    "AND_tech_stack_complexity_high": true
  },
  "critique_template": "1인이 이 {stack_component_list}를 운영 중에 디버깅/유지보수할 수 있는가?",
  "evidence_questions": [
    "장애 발생 시 1인이 대응 가능한 범위를 벗어나지 않는가?",
    "각 컴포넌트가 MVP 단계에서 진짜 필요한가, '있어야 할 것 같아서' 넣었는가?",
    "관측성/분산 시스템 패턴이 premature optimization 아닌가?",
    "기술 부채 누적 시 1인이 감당할 수 있는 규모인가?"
  ],
  "source_critiques": [
    "ALLBLUE 자체 검토에서 Spring Boot + Redis Streams + Saga + Prometheus + Loki 등 1인 운영 적합성 의문 (conversation-log.md#phase6)"
  ],
  "user_conviction_level": "medium_high",
  "notes": "대화 중반에 외부 지적으로 확인된 규칙. 사용자가 직접 발화하지는 않았으나 수용함."
}
```

---

## Rule 6 — 가정형 언어 탐지 (자기 합리화 마커)

```json
{
  "rule_id": "rule_hypothetical_language_detector",
  "rule_name": "가정형 언어 패턴 탐지",
  "confidence": "medium",
  "trigger_conditions": {
    "document_type_in": ["readme", "prd", "planning_doc", "chat_log"],
    "author_is_user": true
  },
  "critique_template": "이 문서에 다음 가정형 언어 패턴이 N회 이상 등장하는가?",
  "evidence_questions": [
    "'~라고 생각했어' 패턴이 등장하는 맥락에서 증거가 제시되는가?",
    "'~라면' 패턴 뒤에 검증 계획이 따라오는가, 단순 낙관인가?",
    "'기술적으로 어려울 수는 있지만' 같은 한계 인정 후 구체적 해결 방안이 있는가?",
    "가정형 언어가 핵심 가치 주장에 사용되고 있는가, 부수적 설명에 사용되는가?"
  ],
  "source_critiques": [
    "conversation-log.md#phase7의 ALLBLUE 차별화 답변에서 가정형 언어 집중 사용"
  ],
  "user_conviction_level": "medium",
  "notes": "언어 패턴 탐지는 NLP 태스크로 자동화 가능. v0.2에서 정규식 + 의미 분류로 구현 예정. v0.1에서는 LLM 프롬프트로 탐지."
}
```

---

## Rule 7 — 방어 모드 전환 회피 원칙

```json
{
  "rule_id": "rule_defensive_response_check",
  "rule_name": "비판에 대한 방어 패턴 자기 점검",
  "confidence": "medium",
  "trigger_conditions": {
    "context": "user_received_critique_recently",
    "OR_document_responds_to_prior_critique": true
  },
  "critique_template": "이 문서/응답이 비판에 대한 방어 모드로 작성되지 않았는가?",
  "evidence_questions": [
    "비판의 핵심을 재진술한 뒤 답변하고 있는가, 우회하고 있는가?",
    "'그건 이미 고려했어' 톤이 등장하는가?",
    "비판의 전제를 문제 삼고 있는가, 비판 자체에 답하고 있는가?",
    "DEKK 팀이 사용자 비판에 방어했던 패턴과 구조적으로 유사하지 않은가?"
  ],
  "source_critiques": [
    "DEKK 팀이 사용자의 비판에 '클론한 게 의미 없다는 거냐'로 되받은 사례 (conversation-log.md#phase7)",
    "사용자 본인이 '지금 나도 같은 함정에 빠질 수 있다'는 자기 인식을 드러냄"
  ],
  "user_conviction_level": "medium",
  "notes": "이 규칙은 Mirror Agent 자체에 대한 방어도 포함. 사용자가 에이전트 출력에 방어할 때 트리거 가능."
}
```

---

## Rule 8 — 동기의 정직성 원칙

```json
{
  "rule_id": "rule_motivation_honesty",
  "rule_name": "프로젝트 동기의 정직성 원칙",
  "confidence": "medium",
  "trigger_conditions": {
    "document_type": "readme_or_pitch",
    "claims_commercial_value": true
  },
  "critique_template": "이 프로젝트를 하는 진짜 이유가 {stated_reason}인가, 아니면 다른 이유인가?",
  "evidence_questions": [
    "'좋은 사업 아이디어'라고 주장하는 근거가 있는가?",
    "개인적 동기(실행 자유, 학습, 포트폴리오)를 숨기고 상업성을 앞세우고 있지 않은가?",
    "솔직한 동기를 문서화했을 때 프로젝트 설계가 달라질 수 있는가?",
    "목표와 메트릭이 진짜 동기와 일치하는가?"
  ],
  "source_critiques": [
    "ALLBLUE의 진짜 동기가 '실행 자유'였음을 사용자가 인정 (conversation-log.md#phase8)"
  ],
  "user_conviction_level": "medium",
  "notes": "이 규칙은 사용자가 한 번 인정한 것에 기반. 추후 비슷한 인정이 쌓이면 high로 승격."
}
```

---

## Rule 9 — [SEED] 타인/자기 비판 비대칭 탐지

```json
{
  "rule_id": "rule_critique_asymmetry_SEED",
  "rule_name": "타인에게 한 비판을 자신에게도 하는가 (시드)",
  "confidence": "seed",
  "trigger_conditions": {
    "placeholder": "근거 축적 필요"
  },
  "critique_template": "[SEED] 사용자가 과거 {target_type}에 대해 한 비판 {critique_A}가, 현재 자기 프로젝트에도 구조적으로 성립하는가?",
  "evidence_questions": [
    "[SEED] 과거 비판 대상과 현재 프로젝트의 구조적 유사성이 있는가?",
    "[SEED] 사용자가 이 대응 관계를 이미 자각하고 있는가?"
  ],
  "source_critiques": [
    "이 규칙은 Mirror Agent 전체의 메타 규칙. 개별 사례가 아닌 구조에 대한 규칙."
  ],
  "user_conviction_level": "very_high (concept) / low (instances)",
  "notes": "⏸ SEED 상태. 이 규칙은 Historical Agent의 존재 이유 그 자체라서 자동 적용되어야 하지만, 개별 적용 사례가 아직 1~2개뿐이라 템플릿화가 이르다. 사례 5개 이상 쌓이면 활성화."
}
```

---

## Rule 10 — [SEED] 빈 슬롯 (사용자 추가 예정)

```json
{
  "rule_id": "rule_10_EMPTY",
  "rule_name": "빈 슬롯 — 사용자가 직접 관찰한 자기 패턴으로 채울 것",
  "confidence": "seed",
  "trigger_conditions": {},
  "critique_template": "",
  "evidence_questions": [],
  "source_critiques": [],
  "user_conviction_level": "TBD",
  "notes": "이 슬롯은 의도적으로 비워둠. 사용자가 Mirror Agent를 사용하면서 '이런 패턴도 있었네'를 발견할 때 채우는 공간."
}
```

---

## 요약

| # | Rule | Confidence | Status |
| --- | --- | --- | --- |
| 1 | 공급자 확보 전략 선행 | high | ✅ 활성 |
| 2 | 차별화 지점 명시 | high | ✅ 활성 |
| 3 | 이후 단계 구체성 | high | ✅ 활성 |
| 4 | 사용자 니즈 증거 | high | ✅ 활성 |
| 5 | 1인 운영 가능성 | medium-high | ✅ 활성 |
| 6 | 가정형 언어 탐지 | medium | ✅ 활성 |
| 7 | 방어 모드 전환 회피 | medium | ✅ 활성 |
| 8 | 동기의 정직성 | medium | ✅ 활성 |
| 9 | 타인/자기 비판 비대칭 | seed | ⏸ 대기 |
| 10 | 빈 슬롯 | seed | ⏸ 대기 |

**활성 규칙:** 8개  
**대기 규칙:** 2개

---

## v0.1 테스트 예상

이 8개 활성 규칙을 ALLBLUE README에 적용했을 때 최소 다음 비판은 생성되어야 한다:

1. **Rule 1 → 카페24 셀러 확보 전략 부재** ✓ (기대)
2. **Rule 2 → AI 합성 Snap 클론과의 차별화 불명확** ✓ (기대)
3. **Rule 3 → Phase 3가 Phase 1 검증 실패 시나리오 부재** ✓ (기대)
4. **Rule 4 → 크로스셀러 코디 니즈의 사용자 증거 부재** ✓ (기대)
5. **Rule 5 → 1인 Spring Boot + Redis Streams + Saga 운영 가능성 의문** ✓ (기대)

**v0.1 합격선:** 위 5개 중 최소 3개 생성.

---

*"규칙이 늘어날수록 내 맹점이 줄어드는 게 아니라, 내가 내 맹점을 볼 수 있는 각도가 늘어난다."*