---
title: 로드맵 & 마일스톤
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 10. 로드맵 & 마일스톤

각 마일스톤은 독립 배포 가능하고 검증 기준(DoD)을 가진다.

## M0 — 골격 & 데이터 모델 (1주)
- 레포 스켈레톤, `config/*.yaml`, `event.schema.json`, 샘플 레코드.
- DoD: 샘플 레코드가 JSON Schema 검증 통과, `build_index`가 `events.json` 생성.

## M1 — 1소스 수집 적재 (1주)
- KOPIS 어댑터 fetch→normalize→upsert→validate→build, GitHub Actions cron.
- DoD: 실 공연 ≥ 500건이 파일 DB에 적재·일1회 갱신, 신선도 노출.

## M2 — 멀티소스 + 지오코딩 (1주)
- TourAPI(축제) + data.go.kr 추가, VWorld 지오코딩, dedupe(`same_as`).
- DoD: 3소스 통합, 좌표 결측률 < 15%, 시/도 17개 모두 데이터 존재.

## M3 — 검색 & 지도 UI (1.5주)
- Leaflet 코로플레스 + 5축 필터 + Fuse.js 검색, Cloudflare Pages 배포.
- DoD: 5필터 조합 동작, URL 복원, 모바일 반응형.

## M4 — 알람 (1주)
- Telegram 1차 + 구독(KV) + 디스패처(신규/오픈/마감임박) + 중복억제.
- DoD: 마감 D-1 알람 정확 도달, 중복 0.

## M5 — AI 추천 플래닝 (1주)
- 규칙 랭킹 + LLM 플랜(ai-proxy Worker) + 폴백 + 결과 캐시.
- DoD: 프로필→유효 JSON 주간 플랜, free_only 준수, LLM 실패 폴백.

## M6 — 신청 매크로 (1.5주)
- Playwright 러너 + 사이트 프로필 + 잡 큐 + 반자동/자동 분기 + 결과 캡처→알람.
- DoD: mock 자동제출 E2E + 실사이트 반자동 데모 + 약관금지 사이트 비자동 보장.

## M7 — 지식 루프 & 운영 (지속)
- graphify 그래프, 주간 큐레이션 리포트, dedupe 리포트, usage 모니터.
- DoD: `knowledge/reports/*` 주간 자동 생성, 그래프 갱신.

## 우선순위 근거
- 데이터(M0–M2)가 모든 기능의 전제 → 최우선.
- UI(M3) 후 알람(M4)·AI(M5)로 가치 확장, 매크로(M6)는 약관 리스크가 커 후순위.

## 리스크 레지스터
| 리스크 | 영향 | 완화 |
|---|---|---|
| 소스 약관/자동화 금지 | 매크로 축소 | 반자동 강등, 사이트별 플래그 |
| 무료 한도 초과 | 서비스 중단 | 캐시·증분·degrade, limits.yaml |
| 좌표/스키마 결측 | 지도/필터 품질 | geocache, 검증 CI, archived 정책 |
| 공공API 스키마 변경 | 수집 실패 | profile 분리, 소스별 격리 skip |
| PII/보안 | 법적 리스크 | 로컬·암호화 저장, 최소수집 |
