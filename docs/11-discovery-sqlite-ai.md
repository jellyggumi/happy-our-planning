---
title: 웹검색 발견 · SQLite 인덱스 · Gemini 플래너 (2026 개선)
status: implemented
okf_type: TechnicalDocument
updated: 2026-06-21
---

# 11. 웹검색 발견 · SQLite(libSQL) 인덱스 · Gemini 플래너

> spec-stack 결과물. **Write**(이 문서) → **Freeze**(아래 Seed/검증) →
> **Run**(scripts/* + tests/test_pipeline.py, 무료 티어/오프라인 픽스처로 검증).

## 0. 동결된 Seed (변경 금지 기준선)

> 2026년 무료 SaaS를 전제로, 기존 공공 API 파이프라인을 4축으로 개선한다.
> ① 웹 검색 API(Exa/Brave/Tavily)로 **행사 발견** 레이어 추가,
> ② flat-file SSOT를 보완하는 **SQLite(libSQL) 쿼리 인덱스**(FTS5),
> ③ **Google AI Studio(Gemini)** 구조화 주간 플래너(+규칙 폴백),
> ④ **llm-wiki 지식 DB 구조 유지** — 파일이 단일 진실원천, SQLite는 파생물.
> 전 경로는 키 없이 오프라인 픽스처로 동작하고 월 0원을 유지한다.

## 1. 웹 검색 발견 레이어 (Exa · Brave · Tavily)

공공 API(KOPIS/TourAPI)가 다루지 않는 신규·모집형 행사를 **검색**으로 발견한다.

- 선언: `config/search.yaml`(제공자·질의·신뢰도 가드) + `config/sources.yaml`의
  `websearch` 소스. 어댑터: `scripts/ingest/websearch.py`.
- 제공자별 응답 → 공통 hit 정규화: `parse_exa / parse_brave / parse_tavily`.
  (Brave는 점수 미제공 → 순위 기반 근사 점수.)
- hit → OKF 매핑: 제목/요약에서 시/도 추출(`config.extract_sido`), 키워드로 테마
  추정, 날짜를 KST date-time으로 정규화. **날짜·지역·신뢰도(min_confidence)**
  미달이면 적재하지 않음(노이즈 차단).
- 발견 후보는 `source: websearch`, `x_verification: web-discovered`,
  `x_confidence`, `x_provider`, `x_query` 메타를 달고 일반 OKF Event로 적재되어
  검증·인덱스·지도에 그대로 흐른다(공식확인 전 "발견 후보" 표식).
- 무료 티어: Exa 월 1,000 / Brave 월 2,000 / Tavily 월 1,000. 키 없으면
  `raw/websearch/sample-*.json` 픽스처로 동작.

## 2. SQLite(libSQL) 쿼리 인덱스

flat-file Markdown이 **SSOT**, SQLite는 언제든 재생성하는 **파생 인덱스**다.
정적 `events.json`이 약한 전문검색·교차필터·범위질의를 보완한다.

- 빌드: `scripts/build/build_sqlite.py` → `web/public/data/events.db`.
- 스키마: `events` 테이블 + `events_fts`(FTS5, unicode61, name/description/themes)
  + `sido/status/event_type/start_date` 인덱스.
- 질의 헬퍼 `search(text=, sido=, theme=, status=, limit=)` — FTS MATCH와 컬럼
  필터를 교차. 한국어 전문검색 동작.
- 이식: 동일 스키마이므로 **Cloudflare D1** 또는 **Turso(libSQL)** 무료 티어로
  덤프 이관 가능(엣지에서 SQL 질의). 클라이언트는 sql.js로 동일 db 로드도 가능.

## 3. Google AI Studio(Gemini) 주간 플래너

규칙 랭킹(`scripts.recommend.rank`)으로 후보를 추리고 Gemini에 **responseSchema**를
강제해 구조화 주간 플랜을 만든다. 실패·무키 시 규칙 폴백으로 강등.

- 구현: `scripts/recommend/ai_planner.py`. 순수 함수
  `build_request / parse_plan / validate_plan`는 네트워크 없이 테스트.
- 환각 가드: LLM이 후보 밖 `event_id`를 만들면 `_constrain_to_candidates`가 제거.
- 키: `GOOGLE_AI_STUDIO_KEY`(우선) 또는 `GEMINI_KEY`, 모델 `GEMINI_MODEL`
  (기본 `gemini-2.0-flash`). 키는 서버/Worker(ai-proxy)에서만.
- 엔드포인트: `generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`.

## 4. llm-wiki 지식 DB 구조 유지

`knowledge/` 의 index.md + events/ + sources/ + themes/regions 허브 구조와
graphify 그래프는 04 문서 그대로. 본 개선은 **파일 SSOT를 깨지 않고** 발견 후보를
같은 포맷으로 적재하고(파일), SQLite/AI는 그 위의 파생/소비 계층으로 얹는다.

## 5. 검증 (Run 증거)

`python -m unittest discover -s tests` — 40 테스트 통과. 그중:

- `TestWebSearch` — 오프라인 매핑(3/4, 저신뢰·무날짜 제외), 신뢰 도메인 가점,
  텍스트→시/도 추출, 제공자별 파서(exa/brave/tavily).
- `TestSqlite` — 빌드 건수, 한국어 FTS 매치, sido/theme/status 필터, JSON 디코딩.
- `TestAiPlanner` — 요청 스키마·후보 id 포함, 응답 파싱/거부, event_id 강제,
  환각 id 제거, **무키 시 규칙 폴백**.

오프라인 전체 파이프라인: `python -m scripts.run_pipeline` →
수집(websearch 포함)·검증·index·**events.db**·wiki 갱신까지 월 0원으로 동작.

## 6. 문서 링크
- [03 데이터 소스 & 무료 API](03-data-sources-apis.md) — 웹검색 발견 소스
- [08 AI 추천 플래닝](08-ai-planning.md) — Gemini 플래너
- [09 무료 SaaS 스택](09-saas-free-stack.md) — 2026 갱신
