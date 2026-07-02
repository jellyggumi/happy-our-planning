# Happy Our Planning — 지식 DB (Knowledge Wiki)

llm-wiki 패턴을 따르는 행사 지식 베이스. 검색/지도/추천의 단일 진실원천(SSOT).
각 행사는 `events/<YYYY>/<MM>/<sido>/<id>.md` 에 schema.org/Event(OKF) frontmatter로 저장된다.

- **Schema**: `schema/event.schema.json`
- **Graphify output**: `../graphify-out/` (행사↔지역↔테마↔주최 그래프)
- **갱신 주기**: 매일 03:00 KST (GitHub Actions)

## Regions
<!-- REGIONS:START -->
- 서울특별시 — 205건
- 경기도 — 57건
- 경상남도 — 50건
- 부산광역시 — 30건
- 대구광역시 — 18건
- 충청남도 — 17건
- 광주광역시 — 17건
- 인천광역시 — 16건
- 경상북도 — 15건
- 강원특별자치도 — 14건
- 전북특별자치도 — 13건
- 세종특별자치시 — 12건
- 울산광역시 — 12건
- 전라남도 — 10건
- 대전광역시 — 8건
- 제주특별자치도 — 7건
- 충청북도 — 4건
<!-- REGIONS:END -->

## Themes
<!-- THEMES:START -->
- 공연 — 499건
- 축제 — 5건
- 공모전 — 1건
- 교육 — 1건
- 체험 — 1건
<!-- THEMES:END -->

## Sources
<!-- SOURCES:START -->
- kopis — 498건 (최근 갱신 2026-07-02)
- tourapi — 3건 (최근 갱신 2026-06-20)
- websearch — 3건 (최근 갱신 2026-07-02)
- example — 1건 (최근 갱신 2026-06-20)
<!-- SOURCES:END -->

## Reports
- `reports/` — 주간 트렌드·큐레이션·dedupe 후보 (AI 생성)
