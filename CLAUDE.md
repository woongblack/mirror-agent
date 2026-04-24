# CLAUDE.md — Mirror Agent 프로젝트 SOP

> 이 파일은 Claude Code 또는 다른 AI 에이전트가 이 프로젝트를 이어받을 때 읽어야 하는 SOP다.
> 
> **맥락을 매번 설명받지 않아도 바로 작업할 수 있게** 하는 것이 이 파일의 목적이다.
> (이게 Mirror Agent 자체의 철학이기도 함.)

---

## 프로젝트 한 줄 요약

**1인 개발자가 자기 자신에게 못 던지는 질문을 대신 던지는 에이전트 팀.**

구체: 사용자가 과거 타인에게 했던 날카로운 비판을, 현재 자기 문서에 기계적으로 재적용하는 도구.

---

## 반드시 먼저 읽을 문서 (순서대로)

1. `README.md` — 프로젝트의 존재 이유와 현재 상태
2. `docs/origin/conversation-log.md` — **가장 중요한 문서.** 이 프로젝트의 기원이 된 전체 대화. Historical Agent의 학습 재료이기도 함.
3. `docs/architecture/historical-agent-plan.md` — 3-Stage 파이프라인 상세 설계
4. `docs/roadmap.md` — 전체 로드맵, 체크포인트 구조
5. `src/mirror_agent/models.py` — 모든 데이터 스키마 (Pydantic)

---

## 핵심 설계 원칙 (변경 시 반드시 의논)

### 1. Harness 95% / Execution 5%
- 에이전트 개수를 늘리거나 로직을 추가하기 전에 **컨텍스트(규칙, 방어 패턴) 품질**을 먼저 점검한다.
- "있어야 할 것 같아서"가 도입 이유면 **도입하지 않는다**.

### 2. Evidence 필수 원칙
- LLM 출력의 모든 판단은 문서에서 직접 인용 가능한 근거를 가져야 한다.
- 근거 인용 불가 시 `matches=False`로 강제한다.
- "추측 금지"를 프롬프트에 명시한다.

### 3. 사용자 방어 모드 유발 회피
- 한 번에 표시되는 비판은 **최대 3개** (Top N).
- 나머지는 접힌 영역(collapsed)으로.
- 이유: 5개 이상 비판은 사용자 방어 모드를 유발한다 (DEKK 실패 패턴).

### 4. v0.1은 Historical Agent 단독
- Socratic/Contrarian Agent는 **Phase 5**로 연기됨.
- v0.1에서는 Historical의 고유 가치를 **단독으로 검증**해야 한다.
- 다른 에이전트를 섞으면 평가가 희석된다.

### 5. 방어 예측은 v0.1 필수
- `defender.py`가 없는 Historical은 그냥 규칙 기반 비판 도구.
- 방어 예측이 있어야 "사용자의 과거 궤적을 아는 비판자"가 됨.
- 이게 Mirror Agent의 **진짜 차별점**.

---

## 현재 구현 상태

### ✅ 완료 (v0.1 구현)
- 프로젝트 구조, pyproject.toml, .env.example
- 전체 Pydantic 모델 (`src/mirror_agent/models.py`)
- 규칙 JSON 8개 + 방어 패턴 5개 (Ground Truth 포함)
- 규칙/패턴 로더 (`src/mirror_agent/loader.py`)
- 설정 (`src/mirror_agent/config.py`)
- 테스트 fixture (ALLBLUE README 스냅샷)
- Evaluation ground truth (`eval/ground_truth.json`)
- `llm.py`: Anthropic AsyncClient, `structured_call` (tool use), `text_call`, 재시도 로직
- `analyzer.py`: 마크다운 섹션 파싱, LLM으로 `DocumentMetadata` 추출, `key_excerpts` 보관
- `matcher.py`: 규칙×문서 LLM 호출, Evidence 없으면 강제 `matches=False`, confidence 필터링
- `generator.py`: 템플릿 변수 치환, `past_evidence` / `document_excerpt` 재사용
- `defender.py`: 비판-방어패턴 의미 유사도 매칭, conversation-log.md 맥락 LLM 추론
- `scorer.py`: confidence_label 기준 정렬, 상위 N개 선택 (novelty 계산은 v0.2 연기)
- `reporter.py`: Markdown 출력, 상위 N개 표시, 나머지 `<details>` 접기, 방어 예측 포함
- `pipeline.py`: Analyzer→Matcher→Generator→Defender→Scorer→Reporter 전체 파이프라인
- `cli.py`: `main()`, `rules list`, `rules show`, `review` 커맨드

### 🔄 일부 구현 (v0.2 연기)
- `scorer.py`: novelty_score / repetition_penalty / 리포트 히스토리 로드 미구현 (현재 confidence_label 정렬만)

### ✅ 검증 완료 (2026-04-23)
- end-to-end 실행 완료 — Ground Truth 3/3 재현
- Phase 3 실사용 사이클 1회 완료 — Precision 60% (합격선 통과)
- 판정 기록: `data/rejections.md` (수용 3 / 반려 2)
- 테스트 6건 모두 통과

### 🔜 다음 세션 작업 (Phase 4-A Extractor)

1. **ALLBLUE README 수정** (수용한 비판 3개 반영)
   ```bash
   # 수용 항목:
   # 1. 차별화 지점을 테스트 가능한 가설로 재작성
   # 2. Phase 1 실패 시 대응 기준 추가
   # 5. 사용자 관심도 검증 계획 추가
   ```

2. **Extractor 구현** (`src/mirror_agent/extractor.py`)
   ```bash
   uv run mirror review tests/fixtures/allblue-readme-snapshot.md
   ```

2. **합격 기준 측정**
   - `eval/ground_truth.json`의 3건 중 2건 이상 유사 질문 생성 확인
   - `rule_supplier_first` Critical Hit 포함 여부 확인
   - 수동 블라인드 평가 (Precision/Novelty)

3. **v0.2 scorer.py novelty 구현** (검증 통과 후)
   - `data/reports/` 히스토리 로드
   - `final_score = confidence × (1 + novelty_bonus - repetition_penalty)`

---

## v0.1 합격 기준 (자주 확인할 것)

```
[Recall]       ground truth 3건 중 2건 이상 유사 질문 생성
[Precision]    전체 생성 비판 중 50% 이상이 사용자 본인 "타당" 판정
[Critical Hit] rule_supplier_first에서 파생된 비판 반드시 포함
[Novelty]      일반 LLM 비판("사용자 검증이 필요합니다")과 구분 가능
```

**Precision/Novelty는 수동 블라인드 평가**로 측정. 자동화 시도하지 말 것.

---

## 주의사항

### 하지 말아야 할 것

- ❌ 에이전트 개수 늘리기 (Socratic/Contrarian은 Phase 5까지 **추가 금지**)
- ❌ Generalizer 자동화 시도 (v0.2 영역)
- ❌ Jira/Confluence 연동 (Phase 6 영역)
- ❌ 상위 표시 N개를 3개 초과로 늘리기
- ❌ "더 친절한" 프롬프트로 바꾸기 (LLM이 "예"를 과도하게 답하게 됨)

### 의심하고 재확인할 것

- 🔍 새 규칙 추가 제안 → "이게 DEKK/ALLBLUE 맥락에 근거가 있는가?"
- 🔍 아키텍처 변경 제안 → "Harness 95% 원칙에 부합하는가?"
- 🔍 평가 기준 완화 제안 → "이게 방어 모드의 산물은 아닌가?"

---

## 환경 변수

```
ANTHROPIC_API_KEY                    필수
MIRROR_MODEL_MATCHER                 기본: claude-haiku-4-5-20251001
MIRROR_MODEL_GENERATOR               기본: claude-sonnet-4-6
MIRROR_MODEL_DEFENDER                기본: claude-sonnet-4-6
MIRROR_MATCH_CONFIDENCE_THRESHOLD    기본: 0.7
MIRROR_DISPLAY_TOP_N                 기본: 3
```

---

## 세션 마무리 규칙

**세션 종료 시 반드시 수행한다. 순서대로.**

### 1. 커밋 단위 결정

변경된 파일을 보고 의미 단위로 커밋을 나눈다.

**커밋 단위 원칙:**
- 문서 변경 (CLAUDE.md, README, docs/) → 별도 커밋
- 비판 반영 (fixture 수정) → 별도 커밋
- 기능 구현 (새 파이썬 파일 + 테스트 + CLI) → 하나의 커밋
- 설정 변경 (pyproject.toml 등) → 관련 기능 커밋에 포함

**커밋 메시지 형식:** `{type}: {한 줄 요약}`
- `feat:` 새 기능
- `fix:` 버그 수정 또는 비판 반영
- `docs:` 문서만 변경
- `test:` 테스트만 추가

**커밋은 사용자에게 단위를 제안하고, 사용자가 직접 실행하거나 명시적으로 요청 시 대신 실행한다.**

### 2. 세션 메모리 저장

1. `memory/memory_YYYYMMDD.md` 파일에 세션 요약 작성
2. `memory/MEMORY.md` 인덱스에 한 줄 링크 추가

**세션 요약 파일 포함 항목:**
- 세션 시작 시점 상태
- 오늘 완료한 것 (코드 변경, 검증 결과, 결정 사항)
- 오늘 커밋 이력
- 다음 세션 시작점 (구체적 작업 + 참고 파일)

**규칙:**
- 사용자가 요청하지 않아도 세션 마무리 시 **자동으로 저장**한다.
- 메모리 파일은 다음 세션에서 CLAUDE.md와 함께 읽으면 맥락이 완전히 복원되어야 한다.
- 진행 중인 작업은 "다음 세션 시작점"에 Step 단위로 명시한다.

---

## 자주 쓰는 명령

```bash
# 설치
uv sync

# 테스트
uv run pytest

# 규칙 목록
uv run mirror rules list

# 특정 규칙 상세
uv run mirror rules show rule_supplier_first

# 문서 검토 (v0.2 구현 후 동작)
uv run mirror review tests/fixtures/allblue-readme-snapshot.md
```

---

## 메타 주의 — 이 프로젝트가 자기 자신에게 적용되는가

이 프로젝트의 철학은 "자기 비판"이다. 따라서 **이 프로젝트 자체의 설계도 자기 비판 대상이어야 한다.**

작업 중 다음 순간이 오면 **반드시 멈추고 재검토**:

- "이 기능이 필요한 것 같아" → Rule 5 (1인 운영 가능성) 자기 적용
- "일단 넣어두자" → Rule 3 (이후 단계 구체성) 자기 적용
- "사용자가 원할 거야" → Rule 4 (사용자 니즈 증거) 자기 적용
- "기술적으로 가능해" → Defense Pattern `defense_technical_framing` 자기 적용

**자기 규칙에 자기가 걸리는 순간이 이 프로젝트가 동작한다는 증거다.**

---

*"맥락을 매번 설명하지 않아도 된다"가 이 프로젝트의 핵심 원칙이다. 이 CLAUDE.md가 그 첫 적용이다.*
