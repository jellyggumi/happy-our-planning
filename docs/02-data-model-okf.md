---
title: 데이터 모델 / Open Knowledge Format
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 02. 데이터 모델 — Open Knowledge Format (schema.org/Event)

## 1. 왜 schema.org/Event 인가
"Open Knowledge Format(Google)"의 실용적 구현은 **Google이 구조화 데이터로 인식하는 어휘 =
schema.org JSON-LD**다. 행사 도메인은 `schema.org/Event` 및 하위 타입
(`Festival`, `MusicEvent`, `ExhibitionEvent`, `EducationEvent`, `BusinessEvent`)이 표준.
우리는 각 행사 레코드를 schema.org Event JSON-LD로 정규화해
- Google 리치결과/SEO에 그대로 노출 가능,
- 외부 상호운용성(타 KG로 import) 확보,
- llm-wiki/graphify가 frontmatter를 그래프 노드로 적재.

## 2. 저장 단위 = Markdown 파일 (frontmatter = OKF 레코드)
경로: `knowledge/events/<YYYY>/<MM>/<sido-slug>/<event-id>.md`
- frontmatter(YAML): 정규화된 OKF 필드(아래 표) — 기계가 읽음.
- 본문(Markdown): 사람이 읽는 요약/원문 발췌/큐레이션 노트 — llm-wiki 페이지.
- 빌드 시 frontmatter → `events.json`, 동시에 `<head>`용 schema.org JSON-LD 생성.

## 3. 정규 필드 (frontmatter 스키마)

| 필드 | schema.org 매핑 | 타입 | 필수 | 비고 |
|---|---|---|---|---|
| `id` | identifier | string | ✔ | `<source>:<source_id>` 안정 키 (dedupe 기준) |
| `name` | name | string | ✔ | 행사명 |
| `description` | description | string |  | 요약(정규화) |
| `event_type` | @type | enum |  | Festival/MusicEvent/ExhibitionEvent/EducationEvent/BusinessEvent/Event |
| `themes` | keywords | string[] |  | 통제 어휘(테마 분류, themes.yaml) |
| `start_date` | startDate | date-time | ✔ | ISO 8601 (KST, `+09:00`) |
| `end_date` | endDate | date-time |  | ISO 8601 |
| `application_start` | (확장) `x_applicationStart` | date-time |  | 신청 시작 — 매크로 트리거 |
| `application_end` | (확장) `x_applicationEnd` | date-time |  | 신청 마감 — 알람/매크로 |
| `status` | eventStatus | enum |  | Scheduled/Postponed/Cancelled/Moved + (확장)Open/Closed 신청상태 |
| `attendance_mode` | eventAttendanceMode | enum |  | Offline/Online/Mixed |
| `location.name` | location.name | string |  | 장소명 |
| `location.sido` | location.address.addressRegion | string | ✔ | 시/도 (regions.yaml 코드) |
| `location.sigungu` | location.address.addressLocality | string |  | 시군구 |
| `location.address` | location.address.streetAddress | string |  | 도로명 |
| `location.lat`/`lng` | location.geo.latitude/longitude | number |  | 지도 핀(geocode 보강) |
| `age` | typicalAgeRange | string |  | 예 `7-13`, `19-`, `all` (나이대 필터) |
| `audience` | audience.audienceType | string[] |  | 가족/청소년/노년/장애인 등 |
| `price` | offers.price | number/`free` |  | 0=무료 |
| `organizer` | organizer.name | string |  | 주최 |
| `url` | url | url | ✔ | 공식/신청 페이지 |
| `image` | image | url |  | 포스터 |
| `source` | (확장) `x_source` | string | ✔ | kopis/tourapi/datagokr/... |
| `source_url` | (확장) `x_sourceUrl` | url |  | 원본 레코드 위치 |
| `fetched_at` | (확장) `x_fetchedAt` | date-time | ✔ | 수집 시각(신선도) |
| `content_hash` | (확장) `x_contentHash` | string | ✔ | 변경 감지(증분 upsert) |

> 표준 외 필드는 `x_` 접두사로 확장(JSON-LD `additionalProperty` 또는 커스텀 컨텍스트).

## 4. 통제 어휘 (config로 관리)
- `config/regions.yaml`: 17개 시/도 + 시군구 코드 ↔ 표시명 ↔ geojson 매핑.
- `config/themes.yaml`: 테마 택소노미 (공연/축제/전시/교육/공모전/채용·취업/복지·지원/체험·관광/스포츠/봉사 …), 소스별 카테고리 → 표준 테마 매핑 규칙.
- `config/age-bands.yaml`: 나이대 밴드(영유아 0-6, 어린이 7-13, 청소년 14-18, 청년 19-34, 중장년 35-64, 노년 65-) 와 `typicalAgeRange` 파싱 규칙.

## 5. 식별성 & 증분 적재
- `id = source:source_id` 로 전역 유일. 동일 행사 멀티소스는 `same_as`로 연결(병합 후보).
- 수집 시 `content_hash` 비교 → 변경분만 파일 갱신 → git diff 최소화.
- 삭제 정책: 소스에서 사라진 행사는 즉시 삭제하지 않고 `status: archived` + `x_lastSeen`. 지식은 축적.

## 6. 검증
- `knowledge/schema/event.schema.json` (JSON Schema Draft 2020-12)로 CI에서 모든 frontmatter 검증.
- 정규화기는 pydantic 모델로 1차 검증 후 파일 기록 → 스키마와 1:1 유지.

관련 산출물:
- 스키마: `knowledge/schema/event.schema.json`
- 샘플 레코드: `knowledge/events/2026/07/seoul/example-demo-application.md` (신청형, application_* 필드 포함)
