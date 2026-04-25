# Mirror Agent

> 1인 개발자가 자기 자신에게 못 던지는 질문을, 대신 던져주는 에이전트 팀.

---

## 왜 만들었는가

### 두 번의 실패에서 발견한 공통 패턴

**첫 번째 — DEKK (팀 프로젝트)**

무신사 Snap 클론 프로젝트. 나는 팀원들에게 물었다.

- "그래서 이 이후에는 어떻게 할 건데?"
- "셀러는 어떻게 구할 건데?"
- "Snap 클론이면, 결국 똑같아지는 거 아니냐?"

팀은 답하지 않았다. 내 질문 자체가 이상한 것으로 몰렸다. 나는 팀을 나왔다.

**두 번째 — ALLBLUE (1인 프로젝트)**

팀의 한계를 벗어나고자 혼자 시작한 크로스셀러 룩북 플랫폼. 

몇 달 후, 내가 만든 README를 다시 읽다가 깨달았다.

**내가 DEKK 팀에게 던졌던 질문을, 나 자신에게는 한 번도 던지지 않았다.**

- "그래서 크로스셀러 상품 모은 다음에 어떻게 할 건데?"
- "카페24 셀러들이 왜 ALLBLUE에 들어올 건데?"
- "AI 합성이 붙은 Snap 클론 아닌가?"

**공통된 문제는 "더 똑똑한 비판자"가 아니었다. "감정 없이 계속 같은 자리를 찌르는 비판자"가 필요했다.**

Mirror Agent는 그 역할을 한다.

---

## 무엇을 해결하는가

**해결하는 것**
- 1인 개발자가 자기 기획을 스스로 비판하지 못하는 인지적 맹점
- 과거에 타인에게 던진 비판이 현재 내 문서에는 적용되지 않는 패턴
- 비판이 왔을 때 방어 모드로 전환되는 인간적 반응

**해결하지 않는 것**
- 더 나은 아이디어를 자동으로 생성하는 것
- 사용자를 설득하는 것 (판단은 사용자의 몫)
- 범용 기획 도구 (이건 나를 위해 만드는 도구다)

---

## 에이전트 구성

### 비판 에이전트 팀 (핵심)

| 에이전트 | 역할 | 커맨드 |
|---------|------|--------|
| **Historical** | 과거 내가 타인에게 던진 비판 패턴을 현재 문서에 재적용. 방어 예측 포함. | `mirror review` |
| **Socratic** | 문서의 숨겨진 가정을 드러낸다. 시장/기술/운영/동기/경쟁 5가지 각도. | `mirror socratic` |
| **Contrarian** | 핵심 주장의 반대 전제를 탐색한다. 구체적 시나리오와 함의까지. | `mirror contrarian` |

`mirror review --full` — 3개 에이전트를 병렬 실행하고 severity 기준 통합 리포트 생성.

### Planning Agent (구조화자)

날 아이디어 텍스트를 Ouroboros Loop로 구조화된 기획안으로 변환한다.

```bash
mirror plan <idea_file>
```

---

## 사용자 플로우

### 일상적 사용 (기획 검토)

```
1. 기획 문서 작성 (마크다운)
        ↓
2. mirror review --full <문서>
        ↓
3. Historical 비판 + Socratic 질문 + Contrarian 시나리오 수신
   (severity 기준 상위 3개 우선 표시, 나머지 접힘)
        ↓
4. 각 항목 수용 / 반려 판단
        ↓
5. 문서 수정 → 2번으로 반복
```

### 아이디어 → 기획안 생성

```
1. 아이디어 텍스트 파일 작성
        ↓
2. mirror plan <idea_file>
        ↓
3. Ouroboros Loop 최대 3라운드 — 모호함이 수렴될 때까지 자기 질문 반복
        ↓
4. 구조화된 기획 초안 생성 → data/plans/ 저장
        ↓
5. 생성된 기획안에 mirror review --full 적용
```

### 규칙 DB 확장 (새 대화 로그 생겼을 때)

```
1. mirror extract <conversation_log>
   → 비판 발화 추출 → data/critiques/*.json
        ↓
2. mirror generalize <critiques_json>
   → 추상 규칙 후보 생성 → data/rules/pending/
        ↓
3. pending 규칙 수동 검토 후 data/rules/로 이동
   → 다음 review부터 자동 반영
```

---

## 사용 방법

### 설치

```bash
uv sync
```

`.env` 파일에 API 키 설정:

```
ANTHROPIC_API_KEY=sk-ant-...
```

### 커맨드 레퍼런스

```bash
# 3개 에이전트 통합 검토 (권장)
uv run mirror review --full <document.md>

# Historical Agent만 (빠름)
uv run mirror review <document.md>

# 개별 에이전트
uv run mirror socratic <document.md>
uv run mirror contrarian <document.md>

# 아이디어 → 기획안
uv run mirror plan <idea.txt>

# 규칙 자동화
uv run mirror extract <conversation_log.md>
uv run mirror generalize <critiques.json>

# 규칙 관리
uv run mirror rules list
uv run mirror rules show <rule_id>

# 테스트
uv run pytest -m "not integration"
```

### 옵션

```bash
# 리포트 저장 없이 stdout만 출력
uv run mirror review --full <document.md> --no-save

# 저장 경로 지정
uv run mirror review <document.md> -o ./my-reports/

# Planning Agent 라운드 수 조정 (기본 3)
uv run mirror plan <idea.txt> --max-rounds 5
```

---

## 현재 상태

| 단계 | 상태 | 비고 |
|------|------|------|
| Phase 0: 문서화 | ✅ 완료 | README, 대화 로그, 파이프라인 설계, 로드맵 |
| Phase 1: 레포 초기화 | ✅ 완료 | 프로젝트 구조, Pydantic 모델, 규칙 JSON, Loader |
| Phase 2: Re-Applicator v0.1 | ✅ 완료 | 전체 파이프라인 + Ground Truth 3/3 재현 |
| Phase 3: 실사용 + 개선 | ✅ 완료 | Precision 82% (11개 생성 → 9개 수용, 본인 직접 평가) |
| Phase 4: 규칙 자동화 | ✅ 완료 | Extractor + Generalizer + HITL (auto 규칙 5개) |
| Phase 5: 다중 에이전트 통합 | ⚠️ 구현 완료 | Socratic + Contrarian + Planning Agent — 반복 실사용 검증 추가 필요 |
| Phase 6: 외부 연동 | ⏸ 입사 후 | Jira / Confluence |

**검증 결과 (2026-04-24 기준)**
- Ground Truth 3/3 재현 ✅
- Precision 82% (11개 생성 → 9개 수용, 본인 직접 평가) ✅ — [실제 리포트 확인](data/reports/allblue-readme-snapshot/20260425_040815_allblue-readme-snapshot.md)
- auto 규칙 3개 신규 각도 발동 확인 ✅
- `mirror review --full`: 총 20개 질문 생성 ✅ (ALLBLUE README 1회 실행 기준)

**검증 한계**
- Phase 3(Historical)은 실사용 2회 사이클 완료
- Phase 4~5(Extractor/Socratic/Contrarian/Planning)는 코드 구현 + 1회 통합 실행 완료, 반복 실사용 검증은 추가 필요
- 실제 리포트 파일(`data/reports/`)은 로컬 생성 후 커밋 미포함

현재 규칙: 수동 8개 + 자동 생성 5개 = **총 13개**

---

## 기술 스택

| 항목 | 기술 |
|------|------|
| 언어 | Python 3.12 |
| LLM | Anthropic Claude (Haiku: Matcher/Extractor, Sonnet: Generator/Defender/Agents) |
| SDK | `anthropic` Python SDK (structured output via tool use) |
| CLI | Click + Rich |
| 데이터 모델 | Pydantic v2 |
| 패키지 관리 | uv |
| 규칙 저장 | 로컬 JSON + Git 버전 관리 |

기술 선택 원칙: **Harness에 95% 시간, Execution에 5%.** 에이전트 개수를 늘리기보다 컨텍스트 주입에 투자한다.

---

## 이 프로젝트가 실패할 조건

1. 내가 에이전트의 비판을 방어하기 시작하면. DEKK 팀이 내 비판을 방어했던 것처럼.
2. 이 도구를 실제로 매주 쓰지 않으면. "만들어놓고 안 쓰는 도구"가 되면.
3. Historical Agent가 단순 RAG 이상의 가치를 못 내면. 과거 비판을 현재에 적용하는 메타 추론이 동작하지 않으면.

---

## 참고

- [Q00/ouroboros](https://github.com/Q00/ouroboros) — Ambiguity 수치화, Double Diamond, Persona Rotation 개념
- [razzant/ouroboros](https://github.com/razzant/ouroboros) — 자기 수정과 Multi-Model Review 개념
- 지피터스 사례 (뽀짝이-뽀야 2단 멘토 구조) — 에이전트 간 검토 패턴
- 빌더 조쉬 Claude Code 영상 — "Harness에 95% 시간" 원칙

---

*"타인에게 할 수 있는 비판을 자신에게도 할 수 있을 때, 비로소 혼자 개발이 가능하다."*
