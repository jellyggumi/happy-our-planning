---
title: 수집 파이프라인 & 지식 DB (llm-wiki)
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 04. 수집 파이프라인 & 지식 DB (llm-wiki 적용)

## 1. 파이프라인 단계 (스크립트 중심)

[1 fetch] scripts/ingest/<src>.py
   → raw/<src>/<date>/page-*.json   (불변 원본)
[2 normalize] scripts/normalize/to_okf.py --profile <src>
   → OKF Event dict (pydantic 검증) + geocode 보강
[3 upsert] scripts/normalize/upsert.py
   → knowledge/events/<YYYY>/<MM>/<sido>/<id>.md  (content_hash diff만 기록)
[4 validate] scripts/build/validate.py
   → JSON Schema(event.schema.json)로 전수 검증, 실패 시 CI fail
[5 build] scripts/build/build_index.py
   → web/public/data/{events.json, facets.json, regions.geojson, updated.json}
[6 wiki] scripts/build/wiki_index.py
   → knowledge/index.md(SOURCES/THEMES/REGIONS 블록 갱신) + graphify update .
[7 deploy] GitHub Actions → Cloudflare Pages

각 단계는 독립 실행 가능(idempotent). 실패 시 해당 소스만 skip, 나머지 진행.

## 2. 증분 적재 알고리즘 (가볍게 축적)
1. fetch는 `since = max(fetched_at)` 기준 신규/갱신 페이지만.
2. normalize 후 `content_hash = sha256(정규필드 정렬 직렬화)`.
3. 기존 파일의 hash와 동일 → skip(쓰기 없음 → git diff 0).
4. 다르면 파일 갱신 + `fetched_at` 갱신.
5. 소스에서 사라진 항목은 `status: archived`, `x_lastSeen` 기록(삭제 안 함).
→ 데이터는 **축적**되고 변경분만 **개선**된다.

## 3. llm-wiki 시스템 적용 (지식 DB = wiki)
`knowledge/` 를 llm-wiki 패턴으로 구성한다 (참조: `~/vaults/llm-wiki`).
- `knowledge/index.md` — 콘텐츠 지향 맵. 자동 생성 블록:
  - `<!-- SOURCES:START -->` 소스별 최신 수집 요약/건수
  - `<!-- THEMES:START -->` 테마별 행사 수 + 대표 링크
  - `<!-- REGIONS:START -->` 시/도별 행사 수 + 링크
- `knowledge/events/**` — 행사 페이지(frontmatter=OKF, 본문=큐레이션 노트).
- `knowledge/regions/<sido>.md`, `knowledge/themes/<theme>.md` — 집계/허브 페이지(빌드 생성).
- `knowledge/sources/<src>-<date>.md` — 수집 실행 로그(건수/에러/소요) = llm-wiki sources/.
- `knowledge/reports/` — 주간 트렌드/큐레이션 리포트(AI 생성, 09 참조).
- **graphify**: 파이프라인 6단계에서 `graphify update .` 실행 → `graphify-out/GRAPH_REPORT.md` 로 지식 그래프 유지(행사↔지역↔테마↔주최 관계).

## 4. 스케줄 (GitHub Actions, free)
- `.github/workflows/ingest.yml` — cron `0 18 * * *`(KST 03:00) 매일: fetch→normalize→upsert→validate→build→wiki→commit.
- `.github/workflows/build-deploy.yml` — push 시: build → Cloudflare Pages 배포.
- `.github/workflows/notify.yml` — cron 6시간마다: 마감임박/신규 알람 디스패치.

## 5. 관측/품질
- 매 실행 `knowledge/sources/<src>-<date>.md` 에 {fetched, upserted, skipped, errors, ms} 기록.
- 검증 실패율, 좌표 결측률, 소스별 신선도(가장 오래된 fetched_at)를 빌드 시 `updated.json`에 노출.
- 중복 병합 후보(`same_as`)는 `knowledge/reports/dedupe-candidates.md`로 주기 출력.

## 6. 로컬 실행
```bash
python -m scripts.ingest.kopis --since 2026-06-01
python -m scripts.normalize.to_okf --profile kopis
python -m scripts.normalize.upsert
python -m scripts.build.validate
python -m scripts.build.build_index
python -m scripts.build.wiki_index && graphify update .
```
