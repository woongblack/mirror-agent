# 🌊 ALLBLUE — AI Fashion Orchestration Platform

> **파편화된 쇼핑을 단 하나의 룩으로 엮다.**
>
> 여러 쇼핑몰의 단품 데이터를 수집하여 AI가 크로스 셀러 코디 조합(룩북)을 자동 생성하고,
> 유저에게 통합된 쇼핑 경험을 제공하는 패션 오케스트레이션 플랫폼의 **백엔드 서버**입니다.

## 📌 프로젝트 핵심 요약

| 항목 | 내용 |
| --- | --- |
| **서비스 포지션** | 크로스 셀러 AI 룩북 오케스트레이터 (단순 애그리게이터 ✕) |
| **핵심 차별점** | A셀러 상의 + B셀러 하의 + C셀러 신발 → AI가 하나의 룩북으로 합성 |
| **개발 인원** | 1인 (기획 · 설계 · 백엔드 · 인프라) |
| **개발 기간** | 2026.03 ~ (진행 중) |
| **운영 환경** | AWS EC2 · Docker Compose · GitHub Actions CI/CD |

## 🏗️ 시스템 아키텍처

Next.js (Frontend) → Spring Boot API (이 레포) → PostgreSQL / Redis
→ Python Crawler (단품 수집) → AWS S3 (이미지 저장)
→ n8n Worker (Gemini API, 룩북 합성) → Redis Streams (Message Queue)

## ⚙️ 기술 스택

### Core
- Java 21 (LTS) — Virtual Thread 지원, 비동기 처리 최적화
- Spring Boot 3.5 — 최신 LTS 기반, Native Image 지원
- Gradle 8.x — 빌드 캐싱 활용한 빠른 빌드

### Data & Cache
- PostgreSQL — 상품·룩북·유저·주문 비즈니스 데이터
- Redis — 세션/토큰 관리, API 응답 캐싱, 분산 락(Redisson), 랭킹
- Redis Streams — AI 워커 부하 제어용 메시지 큐 (Rate Limiting, 우선순위 큐)
- AWS S3 — 상품 이미지, AI 합성 룩북 이미지 저장

### Infra & Observability
- Docker Compose — 로컬·운영 환경 컨테이너 오케스트레이션
- GitHub Actions — CI 파이프라인
- AWS CodeDeploy — CD 파이프라인 (무중단 배포)
- Prometheus + Grafana — 메트릭 수집 및 시각화 대시보드
- Loki — 중앙 집중식 로깅 및 에러 트래킹

## 🔥 기술적 도전 과제 & 해결

### 1. AI 룩북 생성 — 비동기 파이프라인 + 부하 제어

**문제**: Gemini API 호출은 평균 2초 소요 + Rate Limit 존재 → 동기 처리 시 UX 붕괴 + 비용 폭탄

**해결**: Redis Streams 기반 메시지 큐 + 상태 머신 + 우선순위 분리

- @Async 콜백: n8n 워커 완료 시 Webhook으로 비동기 수신, 블로킹 없음
- 우선순위 큐: 유저가 직접 요청한 커스텀 룩북은 HIGH, 배치 자동 생성은 LOW
- Dead Letter Queue: 3회 실패 시 DLQ 격리, 관리자 수동 확인

### 2. 통합 결제 — 하이브리드 전략 + Saga 패턴

**문제**: 무신사/네이버는 외부 주문 API 미제공 → 전체 통합 결제 불가능

**해결**: 셀러 유형에 따라 결제 방식을 이분화하는 하이브리드 전략

- 딥링크 결제 (무신사/네이버 등): 룩북 내 상품 클릭 → 원본 쇼핑몰 리다이렉트 → 어필리에이트 수수료
- 통합 결제 (카페24 셀러): PortOne 결제 → Saga Orchestrator → 셀러별 주문 분산 라우팅
- 카페24 API 연동: OAuth 2.0 → 실시간 재고/사이즈 조회 + 주문 생성
- Saga/TCC 패턴: 멀티 셀러 주문의 분산 트랜잭션, 부분 실패 시 보상 로직
- Redisson 분산 락: 동시 결제 시 재고 차감 동시성 제어

### 3. 동시성 제어 — Redisson 분산 락

**문제**: 인기 상품에 동시 결제 요청이 몰리면 재고 초과 판매 위험

**해결**: Redis 기반 분산 락으로 재고 차감 원자성 보장

### 4. API 응답 최적화 — Redis 캐싱 전략

**문제**: 룩북 갤러리 피드는 동일한 데이터를 반복 조회 → DB 부하 증가

**해결**: 읽기 빈도 높은 데이터에 Redis 캐싱 적용

## 🗓️ 개발 로드맵

| Phase | 기간 | 내용 | 상태 |
| --- | --- | --- | --- |
| **Phase 1** | 4주 | 단품 크롤링 수신 + AI 룩북 PoC + SNS 검증 | 🔄 진행 중 |
| **Phase 2** | 4주 | 웹 MVP (갤러리 + 커스텀 룩북 + FitProfile) | 📋 예정 |
| **Phase 3** | 4주 | 카페24 연동 + PortOne 통합 결제 + Saga | 📋 예정 |
| **Phase 4** | 지속 | 크롤링 소스 확장 + 수익화 + 모니터링 고도화 | 📋 예정 |

## 🧑‍💻 개발자

**1인 개발** — 기획 · 설계 · 백엔드 · 인프라

이전 프로젝트 DEKK에서의 경험(크롤링 파이프라인, Batch API 설계, 모니터링 구축)을 기반으로,
방향을 전환하여 AI 오케스트레이션 플랫폼으로 독립 개발하고 있습니다.

---

**ALLBLUE** — The Ultimate Fashion Universe 🌊

---

*[스냅샷 수집일: 2026-04-19 — Mirror Agent v0.1 테스트 fixture]*