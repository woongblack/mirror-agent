# Mirror Agent — 다음 작업 Step 플랜

> `implementation_plan_remaining.md`의 Phase 3 작업을 **실행 가능한 Step 단위**로 쪼갠 문서.
> 각 Step은 독립적으로 완료 가능하며, 예상 소요 시간을 명시했다.
>
> **작성일:** 2026-04-23
> **기준:** v0.1 구현 완료 직후

---

## 실행 순서 개요

```
Step 1 (reporter 저장)      ─┐
Step 2 (gt_002 규칙 보완)   ─┼─ 코드 최소 수정 (1시간 이내)
Step 3 (rejections 템플릿)  ─┘

Step 4 (실사용 사이클)       ─── 수동 (오늘/내일)
Step 5 (gt_003 fixture)      ─── 문서 작성 (20분)

── 여기까지가 Phase 3 최소 완주 ──

Step 6 (scorer novelty)       ─── 히스토리 쌓인 후
Step 7 (Extractor)            ─── Phase 4 진입
```

---

## Step 1 — 리포트 저장 구조

**목적:** Phase 3 사이클이 Git 히스토리로 남도록 인프라 구축.
**예상 소요:** 30분

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `src/mirror_agent/cli.py` | `review` 커맨드에 `--output` 옵션 추가. 기본값 `data/reports/{doc_slug}/{YYYY-MM-DD}.md` |
| `src/mirror_agent/reporter.py` | 파일 저장 로직 추가 (현재 stdout만 출력) |
| `data/reports/.gitkeep` | 신규 디렉토리 |

### 검증

```bash
uv run mirror review tests/fixtures/allblue-readme-snapshot.md
# → data/reports/allblue-readme-snapshot/2026-04-23.md 자동 저장 확인
```

### 완료 조건

- [ ] 리포트가 지정 경로에 저장됨
- [ ] `--output` 옵션으로 경로 오버라이드 가능
- [ ] 같은 날 재실행 시 덮어쓰기 vs 추가 정책 결정 (권장: 덮어쓰기 + 경고)

---

## Step 2 — gt_002 규칙 보완

**목적:** Ground Truth gap 해소 (Phase 검증 실패 시 시나리오).
**예상 소요:** 10분

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `data/rules/active/rule_post_mvp_concreteness.json` | `evidence_questions`에 1개 추가 |

### 추가할 질문

```
"현재 Phase 검증이 실패했을 때, 다음 Phase의 설계·자원·로드맵은 어떻게 수정되는가?"
```

### 검증

```bash
uv run mirror review tests/fixtures/allblue-readme-snapshot.md
# → 비판 #2에 "실패 시" 각도가 포함되는지 확인
```

### 완료 조건

- [ ] `eval/ground_truth.json`의 `gt_002.pipeline_result`를 `partial` → `matched`로 업데이트

---

## Step 3 — 반려 기록 템플릿

**목적:** Phase 4 Generalizer 튜닝용 데이터 축적 시작.
**예상 소요:** 10분

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `data/rejections.md` | 신규 — 판정 기록 템플릿 |

### 템플릿 구조

```markdown
# Rejection Log

> Mirror Agent 리포트에 대한 사용자 판정 기록.
> 반려 이유가 Phase 4 Generalizer 튜닝의 재료가 된다.

## 2026-04-23 — allblue-readme-snapshot.md

| 비판 # | 규칙 ID | 판정 | 이유 |
|--------|---------|------|------|
| 1 | rule_differentiation_explicit | 수용 / 반려 | ... |
| 2 | rule_post_mvp_concreteness   | 수용 / 반려 | ... |
```

### 완료 조건

- [ ] 템플릿 파일 존재
- [ ] Step 4 실사용 사이클에서 즉시 사용 가능한 구조

---

## Step 4 — 실사용 사이클 1회 (수동)

**목적:** 도구를 실제로 쓰는 증거 확보. **코드 작업 아님.**
**예상 소요:** 1~2시간

### 절차

```
① 오늘 리포트(data/reports/allblue-readme-snapshot/2026-04-23.md) 5개 비판 읽기
② data/rejections.md에 수용/반려 판정 기록
③ ALLBLUE README를 수정 (수용한 비판 반영)
④ mirror review 재실행 → 새 리포트 생성
⑤ 두 리포트 diff 확인 (비판이 줄었는지, 새 비판이 등장했는지)
```

### 완료 조건

- [x] 최소 1회 리포트 → 수정 → 재실행 사이클 완주 (2026-04-23)
- [x] 수용/반려 판정 5건 기록 (수용 3 / 반려 2, Precision 60%)
- [ ] ALLBLUE README commit 1회 ← 수용한 비판 3개 반영 필요

### ⚠️ 이 Step이 Phase 3의 핵심

roadmap.md에 이미 명시됨:
> "내가 이 도구를 실제로 매주 쓰지 않으면 실패다."

---

## Step 5 — gt_003 fixture 추가

**목적:** Ground Truth 3/3 완전 재현.
**예상 소요:** 20분

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `tests/fixtures/inspection-agent-design.md` | 신규 — 자율 검수 에이전트 설계서 |

### 내용

conversation-log.md Phase 1에 나온 5-에이전트 설계 (Sisyphus / Prometheus / Metis / Atlas / Heracles) 기반으로 작성.

### 검증

```bash
uv run mirror review tests/fixtures/inspection-agent-design.md
# → rule_solo_operability 또는 rule_user_need_evidence 트리거 확인
# → "에이전트 5개가 정말 필요한가?" 유사 질문 생성 확인
```

### 완료 조건

- [ ] fixture 파일 생성
- [ ] `eval/ground_truth.json`의 `gt_003.pipeline_result` → `matched` 업데이트

---

## Step 6 — v0.2 scorer.py novelty 구현

**전제:** `data/reports/` 히스토리 2회 이상 쌓인 후.
**예상 소요:** 2~3시간

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `src/mirror_agent/scorer.py` | `_load_history()` 실구현, `novelty_bonus` / `repetition_penalty` 계산 |
| `src/mirror_agent/models.py` | `Critique` 필드 확인 (`final_score`, `novelty_score` 있는지) |

### 스코어링 공식

```python
final_score = confidence × (1 + novelty_bonus - repetition_penalty)
```

| 항목 | 계산 |
|------|------|
| `novelty_bonus` | 이번에 새로 등장한 규칙 ID면 +0.2 |
| `repetition_penalty` | 직전 3회 리포트에 있던 규칙 ID면 -0.3 |
| 추가 감점 | 사용자가 `data/rejections.md`에서 수용 판정한 규칙이 또 나오면 -0.2 |

### 완료 조건

- [ ] 2회 이상 실행 시 상위 3개 순서가 달라지는 케이스 존재
- [ ] 반복 비판이 하위로 밀림

---

## Step 7 — Phase 4-A Extractor 착수

**전제:** Phase 3 사이클 2~3회 완주 후.
**예상 소요:** 1~2주

### 변경 대상

| 파일 | 변경 내용 |
|------|----------|
| `src/mirror_agent/extractor.py` | 신규 |
| `src/mirror_agent/models.py` | `CritiqueUnit` 모델 추가 |
| `data/critiques/.gitkeep` | 신규 디렉토리 |

### 입출력

- 입력: `docs/origin/conversation-log.md` (및 추후 회의록, 코드 리뷰)
- 출력: `data/critiques/*.json`

### 검증 기준

- [ ] `conversation-log.md` 입력 시 수동 규칙 8개의 원본 비판 3개 이상 재현
- [ ] False Positive 20% 미만

---

## 진행 상황 체크리스트

완료한 Step 옆에 날짜 기록:

- [x] Step 1 — 리포트 저장 구조 (2026-04-23)
- [x] Step 2 — gt_002 규칙 보완 (2026-04-23)
- [x] Step 3 — 반려 기록 템플릿 (2026-04-23)
- [x] Step 4 — 실사용 사이클 1회 (2026-04-23)
- [x] Step 5 — gt_003 fixture (2026-04-23)
- [ ] Step 6 — scorer novelty (v0.2)
- [ ] Step 7 — Extractor (Phase 4-A)

---

## 각 Step 착수 전 셀프 체크

1. 이전 Step의 실사용 피드백이 이 Step에 반영되는가?
2. "있어야 할 것 같아서"가 아닌 실제 필요 때문에 시작하는가? (Rule 5 자기 적용)
3. 중간에 멈춰도 이 Step까지의 산출물이 독립적 가치를 가지는가?

---

*다음 단계: ALLBLUE README 수정 (Step 4 마무리) → Extractor 구현 (Step 7)*
