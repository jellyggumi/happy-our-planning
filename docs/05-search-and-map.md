---
title: 검색 & 지도 UI
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 05. 검색 & 지도 UI (정적, 무료)

## 1. 프런트엔드 스택
- 빌드: **Vite** (정적 산출) → Cloudflare Pages 배포.
- UI: Vanilla JS + 가벼운 컴포넌트(또는 Preact). 무거운 프레임워크 회피(경량 원칙).
- 지도: **Leaflet** + OSM/VWorld 타일. 시/도 경계 GeoJSON 오버레이.
- 검색: **Fuse.js**(퍼지 풀텍스트) — 사전 빌드 `events.json` 클라이언트 로드.
- 상태/URL: 필터를 URL 쿼리에 직렬화(`?sido=서울&theme=공연&from=...`) → 공유/딥링크.

## 2. 데이터 계약 (빌드 산출물)
- `events.json` — 검색·표시에 필요한 평탄화 필드 배열(상세는 lazy fetch 가능).
- `facets.json` — {sido:count, theme:count, age_band:count, status:count} (필터 카운트 즉시 표시).
- `regions.geojson` — 시/도 경계 + 각 지역 행사 수(코로플레스 음영).
- `updated.json` — 마지막 갱신 시각/소스별 신선도(신뢰 배지).
- 대용량 대비: `events.json`을 시/도별 샤드(`events/seoul.json`)로 분할, 지도 클릭 시 lazy load.

## 3. 화면 구성
1. **지도 패널(좌)**: 시/도 코로플레스 → 클릭 시 시군구 드릴다운, 핀 클러스터.
2. **필터 바(상단)**: 지역 · 기간(진행중/예정/신청가능 + 날짜범위) · 나이대 · 테마 · 키워드.
3. **결과 리스트(우)**: 카드(포스터·제목·기간·지역·나이·무료여부·신청마감 D-day).
4. **상세 패널**: 전체 OKF 속성 + 출처 배지 + [신청 매크로 등록] [알람 켜기] [AI 플랜에 추가].

## 4. 필터 = 데이터 모델 1급 속성
| 축 | 소스 필드 | UI |
|---|---|---|
| 지역 | location.sido / sigungu | 지도 클릭 + 드롭다운 |
| 기간 | start_date / end_date / application_* | 프리셋 + 날짜 피커 |
| 나이대 | age(typicalAgeRange) → age_band | 밴드 칩(영유아~노년) |
| 테마 | themes | 멀티 셀렉트 칩 |
| 키워드 | name+description+themes 인덱스 | 검색창(Fuse.js) |
| 신청가능 | status=Open & now∈[app_start,app_end] | 토글 |

## 5. 성능/접근성
- 초기 로드: facets+regions 먼저, events는 뷰포트/필터 적용분만.
- 키보드 내비/aria, 색약 대비 코로플레스 팔레트.
- SEO: 각 행사 정적 상세 페이지에 schema.org/Event JSON-LD 주입(02 문서).

## 6. 검증 항목
- 17개 시/도 모두 클릭 → 해당 지역 결과만 표시.
- 5개 필터 조합 AND 동작, URL 복원.
- 신청가능 토글이 현재시각 기준 정확.
