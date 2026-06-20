---
title: 신청 매크로
status: draft
okf_type: TechnicalDocument
updated: 2026-06-20
---

# 06. 신청 매크로 (Application Macro)

## 1. 목표와 경계 (중요)
신청기간 내 신청 폼을 **자동/반자동**으로 채워 신청을 보조하고 결과를 캡처한다.
- **약관 준수 우선**: 대상 사이트가 자동화/봇을 금지하면 자동 제출 금지.
  → 그 경우 **반자동(폼 미리채움 + 사용자가 직접 최종 제출)** 으로 강등.
- CAPTCHA·본인인증(휴대폰/공동인증서)은 **자동 우회하지 않음**. 사람 개입 지점으로 명시.
- 결제/금전 거래 신청은 1차 비범위. 무료/사전신청형만 자동화 대상.

## 2. 아키텍처
- 러너: **Playwright**(Python 또는 Node) — 헤드리스 브라우저로 폼 채움.
- 사이트별 어댑터: `scripts/macro/sites/<site>.py` — 셀렉터/스텝/약관 플래그를 캡슐화.
- 잡 큐: 사용자가 [매크로 등록] → Cloudflare Worker가 KV/D1에 잡 적재 →
  GitHub Actions(또는 로컬 러너)가 `application_start` 시점에 잡 실행.
- 프로필: 신청자 정보는 **사용자 로컬/암호화 저장**(서버에 평문 PII 저장 회피).
  민감정보는 사용자 디바이스 또는 본인 GitHub Secrets/로컬 `.env`에서만.

## 3. 사이트 프로필 스키마 (config/macro-sites.yaml)
```yaml
sites:
  - key: example-city-festival
    match_url: "apply.example-city.go.kr"
    automation_allowed: false      # 약관상 자동제출 금지 → 반자동
    auth: { type: phone_otp }       # 사람 개입 필요
    steps:
      - { action: goto, url: "{event.url}" }
      - { action: fill, selector: "#name", value: "{profile.name}" }
      - { action: fill, selector: "#phone", value: "{profile.phone}" }
      - { action: select, selector: "#session", value: "{event.session}" }
      - { action: check, selector: "#agree" }
      - { action: pause, reason: "본인인증/최종제출은 사용자가 수행" }
    success_signal: { selector: ".apply-complete", text: "신청완료" }
```

## 4. 실행 플로우
1. 등록: 상세화면 [신청 매크로 등록] → 잡 = {event_id, site_key, profile_ref, run_at=application_start}.
2. 트리거: 스케줄러가 `run_at`(또는 사용자 지정)에서 잡 pickup.
3. 실행: Playwright가 steps 수행. `automation_allowed=false`면 `pause`에서 정지 후
   스크린샷/접속링크를 사용자에게 알람 → 사용자가 마무리.
4. 결과 캡처: `success_signal` 매칭 → 결과(접수번호/스크린샷) 저장 → 07 알람 트리거.
5. 기록: `knowledge/applications/<date>/<event-id>.md`(상태 머신: queued→filled→submitted→result).

## 5. 안전/윤리 가드레일
- robots/ToS 스크래핑 금지 플래그 점검, 과도한 동시요청 금지(사이트당 동시 1).
- 인증 우회·CAPTCHA 자동해제 **미구현**(정책상 금지). 실패 시 사람에게 핸드오프.
- PII 최소수집·로컬 보관·실행 후 메모리 폐기. 로그에 PII 비기록.

## 6. 검증
- 데모 사이트(자체 mock 폼)에서 자동제출 end-to-end 성공.
- 실제 사이트 1곳에서 반자동(미리채움 + 사용자 제출) 데모.
- 약관 금지 사이트가 자동제출로 가지 않음을 테스트로 보장.
