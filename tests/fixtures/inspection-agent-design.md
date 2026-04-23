# ALLBLUE 자율 검수 에이전트 팀 — 아키텍처 설계서

> **목적:** AI 이미지 검수 자동화를 위한 Multi-Agent Debate 기반 5-에이전트 시스템
>
> **설계 철학:** Ouroboros — 문제를 반복적으로 재정의하여 최적 명세에 수렴
>
> **개발 인원:** 1인 (기획 · 설계 · 구현 · 운영)

---

## 시스템 개요

```
[이미지 입력]
    ↓
Sisyphus Orchestrator (총괄)
    ├── Prometheus Specifier (명세화)
    ├── Metis Critic (비판/검토)
    ├── Atlas Worker (실행)
    └── Heracles Tester (검증)
    ↓
[검수 결과 출력]
```

**핵심 차별점:** Multi-Agent Debate 패턴 — 에이전트들이 서로 반박하며 합의에 도달

---

## 에이전트 역할 상세

### Sisyphus Orchestrator

- 전체 파이프라인 조율
- Phase 간 전환 조건 판단
- 최종 승인/반려 결정
- Ouroboros 루프 종료 조건 관리

### Prometheus Specifier

- 요구사항 → 구체적 명세로 변환
- 검수 기준 JSON 생성 (`rules.json`)
- Metis Critic의 반박을 수용하여 명세 재정의
- Phase 1 루프에서 무한 반복 가능

### Metis Critic

- Prometheus가 생성한 명세에 반박
- 누락된 엣지 케이스 탐지
- "이 명세로 실제 검수가 가능한가?" 반복 질문
- 승인 기준: Ambiguity Score ≤ 0.2

### Atlas Worker

- 확정된 `rules.json`으로 실제 이미지 검수 실행
- VLM(Vision Language Model) API 호출
- 검수 결과를 구조화된 JSON으로 반환
- 처리 실패 시 Sisyphus에 에스컬레이션

### Heracles Tester

- Atlas Worker 결과를 독립 검증
- Ground truth 셋 대비 정확도 측정
- "90% 이상 공수 절감" 수치 검증 담당
- Phase 3 최종 승인 게이트

---

## 3-Phase 파이프라인

| Phase | 단계 | 에이전트 | 종료 조건 |
|-------|------|---------|----------|
| Phase 1 | 요구사항 → 명세화 (Ouroboros Loop) | Prometheus ↔ Metis | Ambiguity ≤ 0.2 |
| Phase 2 | 자율 PoC 검증 | Atlas + Heracles | 정확도 ≥ 90% |
| Phase 3 | 최종 승인 및 배포 | Sisyphus | Human 승인 |

---

## 기술 스택

- **오케스트레이션:** Claude Agent SDK (MCP 기반 에이전트 간 통신)
- **VLM:** GPT-4o Vision / Gemini Pro Vision (교차 검증)
- **명세 저장:** JSON Schema + Git 버전 관리
- **메시지 큐:** Redis Streams (에이전트 간 비동기 통신)
- **모니터링:** Prometheus + Grafana (에이전트별 처리량/오류율)
- **배포:** Docker Compose (각 에이전트 컨테이너 분리)
- **로깅:** Loki (에이전트 간 대화 추적)

---

## 기대 효과

- 이미지 검수 공수 **90% 이상 절감** (수동 → 자동)
- 검수 기준의 일관성 보장 (사람마다 다르던 기준을 명세화)
- Ouroboros 루프로 요구사항 모호성 자동 해소

---

## 현재 상태

| 항목 | 상태 |
|------|------|
| 아키텍처 설계 | ✅ 완료 |
| Sisyphus Orchestrator | 🔄 구현 중 |
| Prometheus Specifier | 🔄 구현 중 |
| Metis Critic | ⏸ 대기 |
| Atlas Worker | ⏸ 대기 |
| Heracles Tester | ⏸ 대기 |

---

*[스냅샷 수집일: 2026-04-19 — Mirror Agent gt_003 테스트 fixture]*
*[출처: conversation-log.md Phase 1 — ALLBLUE 자율 검수 에이전트 설계 원본]*
