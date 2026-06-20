---
title: 결과 알람 / 알림
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 07. 결과 알람 (Notifications)

## 1. 알람 종류
| 종류 | 트리거 | 데이터 출처 |
|---|---|---|
| 신규 행사 | 관심필터(지역/테마/나이)에 매칭되는 신규 upsert | build diff |
| 신청 오픈 | now ≥ application_start | event.application_start |
| 마감 임박 | application_end - now ≤ D-1/D-3 | event.application_end |
| 신청 결과 | 매크로 결과/사이트 결과 캡처 | scripts/macro 결과 |

## 2. 채널 (무료 우선)
- **Telegram Bot** (1차): 봇 토큰 무료, 사용자 chat_id로 push. 설정 간단.
- **Web Push** (2차): VAPID 키 무료, Service Worker 구독을 KV에 저장.
- **Email**: 무료 SMTP(예: 개인 Gmail 앱비번 한도) 또는 무료 티어 메일 API. 저빈도용.
- (선택) RSS/iCal export로 캘린더 구독.

## 3. 구독 모델 (경량)
- 익명 우선: 사용자가 필터 조건을 저장 → `subscription = {filters, channel, target}`.
- 저장소: Cloudflare **KV/D1** free tier. PII 최소(채널 식별자만).
- 구독 토큰으로 해지/수정(서버 계정 불필요).

## 4. 디스패처 (scripts/notify/dispatch.py)
1. cron(6h)으로 실행 또는 build 후 호출.
2. 후보 이벤트 계산: 신규/오픈/마감임박/결과.
3. 각 구독의 필터와 매칭 → 메시지 렌더(템플릿) → 채널 어댑터 전송.
4. **중복 억제**: `knowledge/notify/sent.json`(subscription_id+event_id+type 해시)로 1회만 발송.
5. 전송 결과 로그 → `knowledge/sources/notify-<date>.md`.

## 5. 메시지 템플릿 예
```
[마감 D-1] 서울 어린이 여름 음악축제 (무료)
신청마감: 2026-07-10 18:00 · 종로구 세종문화회관
신청하기: https://... · 매크로 등록: https://app/.../macro
```

## 6. 검증
- 신규 1건 upsert → 매칭 구독에 1회 발송(중복 없음).
- 마감 D-1 경계 정확(시간대 KST).
- 매크로 결과 캡처 → 결과 알람 도달.
