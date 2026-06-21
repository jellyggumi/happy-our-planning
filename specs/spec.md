---
title: 놓치마(Notchima) — 동결 명세 (SSOT)
status: frozen-draft
okf_type: TechnicalDocument
layer: spec-stack/spec
spec_version: "1.0.0"
updated: 2026-06-21
source_of_truth: document        # 실행 SSOT는 specs/seed.yaml
supersedes_doc_map: docs/00-overview.md §6 (성공 기준을 기계검증형으로 승격)
---

# 놓치마 — 제품 명세 (Write 레이어)

> spec-stack 패턴 A(full-stack). 이 문서는 **문서 SSOT**다. 실행 SSOT는
> [`seed.yaml`](seed.yaml), 작업 분해는 [`tasks.md`](tasks.md), 검증 증거 계약은
> [`cli-harness.md`](cli-harness.md). 요구가 바뀌면 **이 문서를 먼저 고치고** seed를 재동결한다.
> 발견(discovery) 근거는 `.survey/free-saas-websearch-ai-stack-2026/`.

## 1. 한 줄 정의
대한민국 지도 기반으로 전국 행사(공연·축제·전시·교육·공모·정부지원)를 **지역·기간·나이대·테마·키워드**
5축으로 검색하고, **신청 매크로**로 신청기간 내 신청을 보조하며, **결과 알람**으로 통지하고,
**AI 추천 플래닝**으로 주간 일정을 설계하는 경량·무료·파일기반 웹 인프라.

## 2. 동결 제약 (Constraints) — 위반 시 스펙 드리프트
| ID | 제약 | 기계 검증 방법 |
|----|------|----------------|
| C1 | 유료 의존 0. 외부 호출은 무료티어 한도 내(공공 API·Exa/Brave/Tavily·Gemini/Groq 무료등급) | `config/*.yaml`에 유료 엔드포인트 없음 + 키 부재 시 오프라인 픽스처로 전 파이프라인 통과 |
| C2 | 지식 DB = flat-file. 별도 DBMS 서버 없음. `events.db`는 **재생성 가능한 파생물** | `web/public/data/events.db` 삭제 후 `run_pipeline`로 재생성 동일 카운트 |
| C3 | 각 행사 레코드는 schema.org/Event 정합 OKF(JSON-LD frontmatter) | `scripts/build/validate.py` rc==0, `knowledge/schema/event.schema.json` 준수 |
| C4 | 비밀키는 저장소 미커밋. `.env`/GitHub Secrets로만 주입 | `git grep`에 키 리터럴 0, `.env`는 gitignore |
| C5 | 약관상 자동화 금지 사이트는 매크로 자동제출 불가(반자동 강등) | `tests` `test_tos_blocked_site_is_semi_no_autosubmit` 통과 |
| C6 | AI 출력은 responseSchema 강제 + 환각 id 제거 + 규칙 폴백 필수 | `test_constrain_drops_hallucinated_ids`·`test_plan_falls_back_without_key` 통과 |
| C7 | 월 운영비 = 0원(free tier 한도 내), 정적 배포(Cloudflare Pages) | 호스팅·CI 무료티어, 빌드 산출물은 정적 자산 |

## 3. 데이터 모델 (계약)
정규 레코드 = `knowledge/schema/event.schema.json`. 필수 키:
`id, name, start_date, url, location.sido, source, fetched_at, content_hash`.
1급 필터 축은 모델의 정규 속성으로 보장한다:
- **지역** → `location.sido` / `location.sigungu` (+ `lat/lng` 33–39N·124–132E)
- **기간** → `start_date / end_date / application_start / application_end` + 파생 `status`
- **나이대** → `age` / `audience` (`config/age-bands.yaml`로 밴드 매핑)
- **테마** → `themes[]` (`config/themes.yaml`로 정규화), `event_type` enum
- **키워드** → `name / description / themes` 풀텍스트 (FTS5 + 클라이언트 Fuse.js)

## 4. 기능 명세 + 기계검증형 수용기준(AC)
각 AC는 **명령 + 기대 산출물**로 검증한다(“보기 좋다” 금지).

### F1 — 수집·적재 (지식 DB 인프라)
- 동작: 어댑터(`scripts/ingest/{kopis,tourapi,websearch}.py`) fetch→`to_okf`→`upsert`→`validate`→`build`.
  신규/변경분만 diff upsert, 출처·`fetched_at`·`content_hash` 유지.
- **AC-F1.1** 키 없이 `python -m scripts.run_pipeline`(오프라인 픽스처) rc==0, `events.json` 생성.
- **AC-F1.2** 동일 입력 재실행 시 upsert가 멱등(생성→skip): `test_create_then_skip_idempotent`.
- **AC-F1.3** 내용 변경 시에만 update + `content_hash` 갱신: `test_update_on_change`.
- **AC-F1.4** 17개 시/도 enum과 별칭/부분일치 정규화: `test_canonical_sido_alias_and_partial`.

### F2 — 검색 & 지도 UI
- 동작: Leaflet 코로플레스 + 5축 필터 + Fuse.js/FTS5 검색, URL 상태 복원, 모바일 반응형.
- **AC-F2.1** SQLite FTS5 한국어 부분검색 + 시/도·테마 교차필터: `test_fts_korean_match`·`test_filter_sido_and_theme`.
- **AC-F2.2** `facets.json`/`regions.json`/`updated.json` 빌드 산출(신선도 노출).
- **AC-F2.3** (UI) 5필터 조합·URL 복원·360px 반응형 — `web/public/` 정적 검증(브라우저 스냅샷).

### F3 — 신청 매크로
- 동작: `plan_job(event, profile)`가 사이트 프로필로 스텝 렌더 → Playwright 러너가 소비.
  `automation_allowed=False`는 `mode='semi'`로 강등, 자동 submit 제거 + 사용자 최종제출 pause.
- **AC-F3.1** 자동 사이트는 submit 액션 보유: `test_auto_site_has_submit`.
- **AC-F3.2** 약관금지 사이트는 자동제출 없음: `test_tos_blocked_site_is_semi_no_autosubmit`.
- **AC-F3.3** 토큰 치환 정확: `test_template_substitution`; 미등록 사이트는 manual: `test_unknown_site_manual`.
- **AC-F3.4** (신규) Playwright 러너가 mock 폼에 `plan_job` 결과 입력→자동제출 E2E 성공(헤드리스).

### F4 — 결과 알람
- 동작: `compute_notifications`(순수) → `dispatch`(전송, 채널 토큰 없으면 dry-run). 중복 억제 `knowledge/notify/sent.json`.
- **AC-F4.1** 마감 D-1 + 필터 일치만 알림: `test_deadline_d1_and_filter_match`·`test_filter_mismatch_no_notif`.
- **AC-F4.2** 2회차 실행 중복 0: `test_dedupe_suppresses_second_run`.
- **AC-F4.3** (신규) Telegram 실채널 1건 도달(토큰 주입 시) / 무토큰 시 dry-run 무오류.

### F5 — AI 추천 플래닝
- 동작: 규칙 랭킹(`rank.py`) + Gemini 구조화 플랜(`ai_planner.py`, responseSchema) + 폴백 + 캐시.
- **AC-F5.1** 요청에 schema·후보 id 포함: `test_build_request_has_schema_and_ids`.
- **AC-F5.2** 유효 플랜 파싱 / 잘못된 형태 거부: `test_parse_plan_valid`·`test_parse_plan_rejects_bad_shape`.
- **AC-F5.3** 환각 event_id 제거: `test_constrain_drops_hallucinated_ids`; 무키 폴백: `test_plan_falls_back_without_key`.
- **AC-F5.4** `free_only` 준수·1일 상한: `test_free_only_excludes_paid`·`test_plan_respects_max_per_day`.

### F6 — 운영·지식 루프 (llm-wiki)
- 동작: `wiki_index.build()`로 `knowledge/` 갱신, graphify 그래프, 주간 큐레이션/ dedupe 리포트.
- **AC-F6.1** `run_pipeline` 5단계가 `knowledge/` wiki 인덱스 갱신.
- **AC-F6.2** GitHub Actions cron(ingest.yml)으로 일1회 갱신·신선도 노출.

## 5. 비범위 (1차)
결제·티켓팅 직접 처리(외부 위임), SSO 풀스택(익명+로컬 프로필), 모바일 네이티브 앱.

## 6. 전역 완료 정의 (DoD)
`python -m unittest discover -s tests` = 40+ green, `validate.py` rc==0,
`events.db` 재생성 동일성, C1–C7 전부 만족, F3.4/F4.3 신규 AC 충족.
