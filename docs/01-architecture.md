---
title: 시스템 아키텍처
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 01. 시스템 아키텍처

## 1. 큰 그림 (3계층 + 1 스케줄러)


                 ┌───────────────────────────── INGESTION (cron, free) ─────────────────────────────┐
  공공 API ─────▶│  fetch  →  normalize(OKF/schema.org Event)  →  dedupe/upsert  →  write .md files   │
  (KOPIS,        │  scripts/ingest/*.py            scripts/normalize/*.py        knowledge/events/**   │
   TourAPI,      └───────────────────────────────────────────────┬──────────────────────────────────┘
   data.go.kr)                                                    │  (git commit, graphify update)
                                                                  ▼
                              ┌──────────────── KNOWLEDGE DB (flat files, SSOT) ───────────────┐
                              │  knowledge/  (llm-wiki 패턴: index.md + events/** + regions/**) │
                              │  build → search index(JSON) + map geojson + facet counts        │
                              └───────────────────────────┬─────────────────────────────────────┘
                                                          │  (build step → /public/data/*.json)
                                                          ▼
   브라우저 ◀───── STATIC FRONTEND (Cloudflare Pages, free) ──────  Leaflet map + Fuse.js search + filters
       │                                                                 │ (fetch prebuilt JSON)
       │  (인증된 액션: 알람 구독, 매크로 큐 등록, AI 추천 요청)
       ▼
   EDGE FUNCTIONS (Cloudflare Workers + KV/D1, free) ── AI proxy(Gemini/Groq), push 구독, 매크로 잡 큐
       │
       ▼
   WORKER SCRIPTS (GitHub Actions / 로컬 러너) ── Playwright 신청 매크로 + 알람 디스패치(Telegram/Web Push/Email)


## 2. 컴포넌트 책임

| 컴포넌트 | 기술 | 무료 근거 | 책임 |
|---|---|---|---|
| 수집기 `scripts/ingest` | Python (httpx) | API 무료 | 소스별 원본 JSON/XML pull → `raw/` 저장 |
| 정규화기 `scripts/normalize` | Python (pydantic) | OSS | 원본 → schema.org Event Markdown 변환, geocode 보강 |
| 지식 DB | git + Markdown/YAML | git 무료 | 단일 진실원천. 출처/신선도/해시 메타 보관 |
| 빌더 `scripts/build` | Python | OSS | 파일 → `public/data/events.json`, `facets.json`, `regions.geojson` |
| 프런트엔드 | Vanilla + Vite, Leaflet, Fuse.js | OSS | 지도/검색/필터/상세/추천 표시 |
| Edge 함수 | Cloudflare Workers | free tier | AI 프록시(키 은닉), 푸시 구독 저장(KV), 매크로 잡 enqueue |
| 매크로 러너 | Playwright (Node/Python) | OSS | 신청 폼 자동/반자동 입력, 결과 캡처 |
| 알람 디스패처 | Telegram Bot / Web Push / SMTP | free | 마감임박·신규·신청결과 통지 |
| 스케줄러 | GitHub Actions cron | free (public repo) | 수집·빌드·알람 주기 실행 |

## 3. 데이터 흐름 핵심 결정
- **읽기 경로는 100% 정적**: 검색/지도는 사전 빌드된 JSON을 브라우저가 직접 fetch → 서버 비용 0, 빠름.
- **쓰기(상태) 경로만 edge**: 알람 구독·매크로 잡·AI 호출만 Workers+KV/D1로. 무료 한도 내 소량 트래픽.
- **SSOT는 파일**: DB가 죽어도 git 히스토리로 복구. graphify로 지식 그래프 생성(llm-wiki 연계).

## 4. 디렉터리 레이아웃 (확정)

happy-our-planning/
├─ docs/                      # 본 계획 문서들
├─ knowledge/                 # 지식 DB (llm-wiki 패턴)
│  ├─ index.md
│  ├─ events/<YYYY>/<MM>/<sido>/<event-id>.md
│  ├─ regions/<sido>.md
│  ├─ themes/<theme>.md
│  ├─ sources/                # 소스별 수집 로그/메타
│  └─ schema/event.schema.json
├─ raw/                       # 불변 원본 응답(소스별), .gitignore 후보(샘플만 커밋)
├─ scripts/
│  ├─ ingest/   (kopis.py, tourapi.py, datagokr.py, base.py)
│  ├─ normalize/(to_okf.py, geocode.py)
│  ├─ build/    (build_index.py)
│  ├─ macro/    (apply.py + sites/<site>.py)
│  └─ notify/   (dispatch.py, channels/*.py)
├─ web/                       # 정적 프런트엔드 (Vite)
│  ├─ index.html, src/, public/data/(빌드 산출)
├─ workers/                   # Cloudflare Workers (ai-proxy, push, macro-queue)
├─ .github/workflows/         # ingest.yml, build-deploy.yml, notify.yml
└─ config/                    # sources.yaml, regions.yaml, themes.yaml


## 5. 환경/시크릿
- API 키(공공데이터, LLM, Telegram)는 GitHub Actions Secrets + Workers Secrets. 저장소엔 미커밋.
- `config/*.yaml`로 소스·지역·테마 매핑을 선언적 관리(코드 변경 없이 소스 추가 가능).

## 6. 확장 시나리오
- 소스 추가 = `scripts/ingest/<src>.py` + `config/sources.yaml` 항목 1개. 나머지 파이프라인 불변.
- 트래픽 증가 시 정적 자산은 무한 확장(CDN). 상태 경로만 free→유료 전환 고려.
