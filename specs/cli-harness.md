---
title: 놓치마 — 하니스/증거 계약 (cli-anything 레이어)
status: active
okf_type: TechnicalDocument
layer: spec-stack/tools
updated: 2026-06-21
---

# 하니스 & 증거 계약 (Tools 레이어)

> spec-stack 규칙: **종료코드가 아니라 산출물을 검증**한다. evaluate 단계가 받는 증거는
> 아래 명령의 산출물(JSON/파일/카운트)이다. 새 하니스는 레지스트리 우선, 생성은 폴백.

## 검증 하니스 (이미 존재하는 스크립트를 하니스로 사용)
| 하니스 | 명령 | 증거(artifact) | 게이트하는 AC |
|--------|------|----------------|----------------|
| pipeline | `python -m scripts.run_pipeline` | `web/public/data/{events.json,facets.json,regions.json,updated.json}` + rc | AC-F1, AC-F6 |
| schema-validate | `python scripts/build/validate.py` | rc==0 + 위반 레코드 목록 | C3, AC-F1 |
| sqlite-rebuild | `python -m scripts.build.build_sqlite` | `events.db` 재생성 + row 카운트 | C2, AC-F2-search |
| tests | `python -m unittest discover -s tests` | Ran N / OK 요약 | 전 AC 회귀 |
| macro-plan | `python -m scripts.macro.apply <event.json>` | `job`(steps[], mode) JSON | AC-F3-gate |
| macro-run(신규) | `python -m scripts.macro.runner --job job.json --headless` | `{submitted, result_text, screenshot}` JSON | AC-F3-runner |
| notify | `python -m scripts.notify.dispatch` | 전송/ dry-run 요약 JSON | AC-F4 |
| ai-plan | `python -m scripts.recommend.ai_planner <profile.json>` | 주간 플랜 JSON(responseSchema 정합) | AC-F5 |
| survey-validate | `python3 ~/.agents/skills/survey/scripts/validate_survey_artifacts.py .survey/<slug> --platform-topic` | OK/FAIL 행 | 발견 계약 |

## 증거 규율
1. **재생성 동일성**(C2): `rm web/public/data/events.db && python -m scripts.run_pipeline` →
   `sqlite3 events.db "select count(*) from events"`가 이전과 동일.
2. **무키 오프라인 통과**(C1): 환경변수 키 미설정 상태에서 위 모든 하니스 rc==0.
3. **키 비노출**(C4): `git grep -nE "(API_KEY|TOKEN)\s*[:=]\s*['\"][A-Za-z0-9_-]{12,}"` → 0 매치.
4. **AI 가드레일**(C6): ai-plan 산출 플랜의 모든 `event_id`가 후보 집합의 부분집합.

## 신규 하니스 도입 정책 (cli-anything)
- 먼저 레지스트리/기존 스크립트 재사용. 없을 때만 생성.
- 외부 도구는 무료·선택. Playwright는 `playwright install chromium`(CI) / 로컬 미설치 시 테스트 skip.
- 새 하니스는 반드시 `--json`(또는 구조화 stdout) 산출을 제공해 evaluate가 파싱 가능해야 한다.
