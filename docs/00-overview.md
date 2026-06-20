---
title: Happy Our Planning — 개요/비전
status: draft
owner: planning
okf_type: ProjectBrief
updated: 2026-06-20
---

# Happy Our Planning (행사 검색·신청·추천 인프라)

## 1. 한 줄 정의
대한민국 지도 기반으로 **전국의 행사(공연·축제·전시·교육·공모·정부지원 등)** 를
지역·기간·나이대·테마·키워드로 검색하고, **신청 매크로**로 신청기간 내 신청을 보조하며,
**결과 알람**으로 통지하고, **AI 추천 플래닝**으로 개인 일정을 설계하는 경량 웹 인프라.

## 2. 설계 원칙 (제약 조건의 번역)
| 사용자 요구 | 설계 규칙 |
|---|---|
| 가급적 무료 API | 한국 공공데이터(KOPIS·TourAPI·data.go.kr) + OSS만 사용. 유료 의존 0 목표 |
| 아주 적은 파일 관리 시스템 = 지식 DB | **flat-file 지식 DB**: git repo 안의 Markdown+YAML frontmatter 파일. 별도 DBMS 없음 |
| 적재·업데이트 가능 | GitHub Actions cron으로 주기 수집 → 정규화 → 파일 upsert → 인덱스 재생성 |
| Open Knowledge Format (Google) 준수 | 각 행사 레코드는 **schema.org/Event** 어휘를 따르는 JSON-LD를 frontmatter로 보관 (Google이 인식하는 구조화 데이터 = OKF의 실용적 구현) |
| llm-wiki 시스템 적용 | `knowledge/` 디렉터리를 llm-wiki 패턴(index.md + 페이지 + sources/queries/reports)으로 구성, graphify로 그래프화 |
| 스크립트가 주요 | 수집·정규화·매크로·알람·인덱싱 전부 작은 Python/Node 스크립트. UI는 정적 자산 |
| 가볍지만 데이터가 축적·개선되는 인프라 | 파일 = 단일 진실원천(SSOT). 매 실행마다 신규/변경분만 diff 적재, 출처·신선도 메타 유지 |
| SaaS·무료 사용 | Cloudflare Pages/Workers/KV/D1 free tier + GitHub Actions free + 무료 LLM(Gemini/Groq) free tier |

## 3. 핵심 기능 (사용자가 명시)
1. **지역 검색** — Korea map(시/도·시군구) 클릭 또는 선택으로 필터
2. **기간 검색** — 진행중/예정/신청가능 + 날짜 범위
3. **키워드 검색** — 제목·설명·태그 풀텍스트(클라이언트 인덱스)
4. **신청 매크로** — 신청기간 내 폼 자동/반자동 신청 (Playwright 스크립트)
5. **결과 알람** — 신청결과·마감 임박·신규 행사 알림 (Web Push / Telegram / Email)
6. **AI 추천 플래닝** — 사용자 프로필(지역·나이대·관심테마·가용일)로 행사 큐레이션 + 일정 플랜

## 4. 추가 검색 축 (사용자가 명시)
- 지역별 / 시간대(기간)별 / 나이대별 / 테마별 — 모두 데이터 모델의 정규 속성으로 1급 필터.

## 5. 비범위(Non-goals) — 1차
- 결제·티켓팅 직접 처리(외부 신청사이트로 위임).
- 로그인 SSO 풀스택(1차는 익명 + 로컬 프로필, 알람만 식별자 연결).
- 모바일 네이티브 앱(반응형 웹 우선).

## 6. 성공 기준 (측정 가능)
- 전국 행사 ≥ 3개 무료 소스에서 수집되어 파일 DB에 적재 (일 1회 갱신).
- 5개 필터 축(지역/기간/나이/테마/키워드) 모두 동작.
- 1개 이상 신청 대상에 대해 매크로 자동입력 데모 성공.
- 마감 임박 + 신규 행사 알람 채널 1개 동작.
- AI 추천이 프로필 입력 → 주간 플랜(JSON) 출력.
- 전 인프라 월 비용 = 0원 (free tier 한도 내).

## 7. 문서 맵
- [01 아키텍처](01-architecture.md)
- [02 데이터 모델 / OKF](02-data-model-okf.md)
- [03 데이터 소스 & 무료 API](03-data-sources-apis.md)
- [04 수집 파이프라인 & 지식 DB(llm-wiki)](04-ingestion-pipeline.md)
- [05 검색 & 지도 UI](05-search-and-map.md)
- [06 신청 매크로](06-application-macro.md)
- [07 결과 알람](07-notifications.md)
- [08 AI 추천 플래닝](08-ai-planning.md)
- [09 무료 SaaS 스택](09-saas-free-stack.md)
- [10 로드맵 & 마일스톤](10-roadmap-milestones.md)
- [11 웹검색 발견·SQLite·Gemini (2026 개선)](11-discovery-sqlite-ai.md)
