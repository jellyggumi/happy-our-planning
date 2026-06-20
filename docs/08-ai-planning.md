---
title: AI 추천 플래닝
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 08. AI 추천 플래닝 (AI Recommendation & Planning)

## 1. 두 단계 추천
1. **검색/랭킹 (LLM 없이도 동작)** — 규칙 기반 스코어로 후보 선별(설명가능·무료·빠름).
2. **플래닝/큐레이션 (LLM)** — 후보를 받아 주간 일정·동선·이유를 생성(무료 LLM 티어).

## 2. 사용자 프로필
```json
{
  "regions": ["서울특별시", "경기도"],
  "age_band": "어린이",
  "themes": ["공연", "체험", "교육"],
  "available_dates": ["2026-07-18", "2026-07-19", "2026-07-20"],
  "prefs": { "free_only": true, "max_per_day": 2, "near": {"lat":37.57,"lng":126.97} }
}
```

## 3. 1단계 — 규칙 기반 스코어 (scripts/build 또는 edge)
score = Σ 가중치:
- 지역 일치(+), 거리 가까움(+, lat/lng 하버사인)
- 테마 일치 수(+), 나이대 일치(+, age_band ⊆ typicalAgeRange)
- 신청가능/마감임박(+), 무료(+ free_only일 때 필수)
- 가용일 내 개최(+), 신선도(+)
→ 상위 N개 후보 + 각 행사 매칭 이유(설명가능)를 반환.

## 4. 2단계 — LLM 플래닝
- 입력: 프로필 + 후보 N개(OKF 필드 축약) + 제약(하루 최대 2개, 동선 최소화).
- 출력: **구조화 주간 플랜 JSON**(아래) — UI 캘린더에 매핑.
```json
{
  "week_of": "2026-07-13",
  "days": [
    {"date":"2026-07-18","items":[
      {"event_id":"kopis:PF000001","time":"10:00","reason":"무료·어린이·도보권"}
    ]}
  ],
  "notes": "오전 공연 후 인근 박물관 연계 추천"
}
```
- 모델: **Gemini free tier** 또는 **Groq(무료)**. 키는 Cloudflare Worker `ai-proxy`에서만 사용(클라이언트 노출 금지).
- 강제 JSON: 스키마 프롬프트 + 응답 검증(실패 시 규칙 기반 폴백).

## 5. llm-wiki 연계 (지식 축적)
- 생성된 큐레이션/주간 트렌드는 `knowledge/reports/<date>-curation.md`로 적재(RAG 재활용).
- 추천 근거가 된 행사 관계는 graphify 그래프에 누적 → 추천 품질 개선 루프.
- 사용자 피드백(좋아요/숨김)은 익명 집계로 가중치 튜닝 데이터화(파일 누적).

## 6. 비용/한도 보호
- LLM 호출은 사용자 액션당 1회, 결과 캐시(동일 프로필 해시 → 캐시 응답).
- 무료 한도 초과 시 1단계 규칙 추천만으로 graceful degrade.

## 7. 검증
- 프로필 입력 → 유효 JSON 플랜 출력(스키마 통과).
- free_only=true면 유료 행사 미포함.
- LLM 실패 시 규칙 기반 폴백 동작.
