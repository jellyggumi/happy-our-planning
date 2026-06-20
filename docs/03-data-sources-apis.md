---
title: 데이터 소스 & 무료 API 카탈로그
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 03. 데이터 소스 & 무료 API 카탈로그

> 원칙: **무료 공공 API 우선**. 모든 소스는 `config/sources.yaml`에 선언적으로 등록하고,
> 소스별 어댑터 `scripts/ingest/<source>.py` 1개로 추가한다.

## 1. 1차 채택 소스 (행사 본체)

| 소스 | 제공 | 내용 | 인증 | 포맷 | 비용 |
|---|---|---|---|---|---|
| **KOPIS** 공연예술통합전산망 | 예술경영지원센터 | 전국 공연/전시 목록·상세·시설 | 서비스키(무료 발급) | XML | 무료 |
| **TourAPI 4.0** | 한국관광공사 | 지역축제(festival), 행사, 좌표 포함 | 서비스키(공공데이터포털, 무료) | JSON/XML | 무료 |
| **공공데이터포털 data.go.kr** | 행안부 | 한국문화정보원 공연전시정보, 지자체 행사/모집공고 다수 | 서비스키(무료, 트래픽 한도) | JSON/XML | 무료 |

## 2. 2차 확장 소스 (신청·모집·지원)

| 소스 | 내용 | 비고 |
|---|---|---|
| 지자체 OpenAPI / RSS | 시·군·구 행사·모집공고 | 지역별 추가, sources.yaml로 점진 등록 |
| 공모전/대외활동(예: 정부24, 청년정책 onyouth) | 신청형 행사(나이대·자격) | 매크로 대상과 강결합 |
| 문화비축전·박물관·도서관 공개 일정 | 전시/교육 | iCal/RSS 우선 |

## 3. 지오코딩(좌표 보강) — 무료
- **VWorld**(국토부) 지오코더 API: 무료 서비스키, 국내 주소 정확. 1차 채택.
- 대안: Nominatim(OpenStreetMap) — rate-limit 엄격, 배치엔 자체 캐시 필수.
- 좌표 캐시: `knowledge/_geocache.json` (주소→lat/lng) 로 중복 호출 차단.

## 4. 지도 타일/경계 — 무료
- 타일: **OpenStreetMap** 표준 타일 또는 **VWorld** 배경지도(국내 최적).
- 시/도·시군구 경계 GeoJSON: 행정구역 공개 데이터(공공데이터포털/통계청 SGIS) → `config/regions.yaml` 참조 후 `regions.geojson` 빌드.

## 5. 호출 정책(무료 한도 보호)
- 일 1회 배치(증분). ETag/`fetched_at` 비교로 변경분만 정규화.
- 소스별 rate-limit·일일 호출 상한을 `sources.yaml`에 명시, 어댑터가 백오프.
- 원본 응답은 `raw/<source>/<date>/` 에 보관(재처리 가능, 샘플만 커밋).

## 6. sources.yaml (예시 스키마)
```yaml
sources:
  - key: kopis
    enabled: true
    base_url: "https://www.kopis.or.kr/openApi/restful"
    auth: { type: query_key, param: service, secret_env: KOPIS_KEY }
    format: xml
    rate_limit_per_day: 5000
    endpoints:
      list: "/pblprfr?stdate={start}&eddate={end}&cpage={page}&rows=100"
      detail: "/pblprfr/{id}"
    map_profile: kopis      # normalize/profiles/kopis.yaml
  - key: tourapi
    enabled: true
    base_url: "https://apis.data.go.kr/B551011/KorService2"
    auth: { type: query_key, param: serviceKey, secret_env: TOURAPI_KEY }
    format: json
    endpoints:
      festival: "/searchFestival2?eventStartDate={start}&numOfRows=100&pageNo={page}&MobileOS=ETC&MobileApp=hop&_type=json"
    map_profile: tourapi
```

## 7. 라이선스/약관 준수
- 각 소스 출처표기 의무를 레코드 `source`/`source_url` + 상세화면 "출처" 배지로 충족.
- 신청 매크로는 **대상 사이트 약관(자동화 금지 여부)** 을 site-profile에 명시, 금지 사이트는 "반자동(폼 미리채움+사용자 제출)"로 강등(06 문서 참조).
