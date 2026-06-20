---
title: 무료 SaaS 스택
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 09. 무료 SaaS 스택 (월 0원 목표)

## 1. 채택 스택과 무료 근거
| 영역 | 서비스 | 무료 한도(개략) | 역할 |
|---|---|---|---|
| 정적 호스팅 | **Cloudflare Pages** | 무제한 정적 요청/대역 | 검색·지도 UI 배포 |
| 스케줄/CI | **GitHub Actions** | public repo 무료 분 | 수집·빌드·알람 cron |
| 코드/지식 저장 | **GitHub repo (git)** | 무료 | SSOT 파일 DB |
| 엣지 함수 | **Cloudflare Workers** | 10만 req/일 | AI 프록시·구독·잡 큐 |
| KV/DB | **Cloudflare KV / D1** | free tier | 구독·잡·캐시 |
| LLM | **Gemini API free / Groq free** | 일/분 한도 | AI 추천 플래닝 |
| 지오코딩/지도 | **VWorld / OSM** | 무료 키 | 좌표·타일 |
| 공공데이터 | **KOPIS·TourAPI·data.go.kr** | 무료 키 | 행사 데이터 |
| 알람 | **Telegram Bot / Web Push(VAPID)** | 무료 | 통지 |

## 2. 무료 유지 원칙
- 읽기 경로는 전부 정적(CDN) → 트래픽 증가에도 무료.
- 상태/AI는 캐시·증분·한도 가드로 free tier 내 유지.
- 모든 한도 임계치를 `config/limits.yaml`에 명시, 초과 시 graceful degrade(규칙 추천/배치 지연).

## 3. 시크릿 관리
- GitHub Actions Secrets: `KOPIS_KEY, TOURAPI_KEY, DATAGOKR_KEY, VWORLD_KEY, TELEGRAM_TOKEN`.
- Cloudflare Workers Secrets: `GEMINI_KEY/GROQ_KEY, VAPID_*`.
- 저장소엔 키 미커밋. `.env.example`만 제공.

## 4. 대안/마이그레이션 여지
- Pages 대신 GitHub Pages/Vercel, Workers 대신 Deno Deploy, KV 대신 Supabase free.
- 추상화는 어댑터 인터페이스로(알람 채널/저장소) → 벤더 락인 최소.

## 5. 비용 모니터링
- 월 1회 `scripts/ops/usage_report.py`로 각 free tier 사용률 추정 → `knowledge/reports/usage-<month>.md`.
