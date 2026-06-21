"""신청 매크로 Playwright 러너 테스트 (T1 · AC-F3-runner).

Playwright/chromium은 무료·선택 의존. 미설치 환경에서는 E2E 테스트가 skip 되고
dry-run 테스트만 항상 실행되어 계획 경로(C1 무키·오프라인)를 회귀한다.

실행: python -m unittest tests.test_runner
"""
from __future__ import annotations

import unittest
from pathlib import Path

from scripts.macro import apply as macro
from scripts.macro import runner

FIXTURE = Path(__file__).parent / "fixtures" / "mock_apply_form.html"


def _chromium_runnable() -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
        return True
    except Exception:
        return False


_RUNNABLE = _chromium_runnable()


class TestRunner(unittest.TestCase):
    def _job(self, url: str) -> dict:
        """plan_job 산출 잡의 goto 타깃을 로컬 픽스처로 치환한다."""
        job = macro.plan_job({"id": "t", "url": url},
                             {"name": "홍길동", "phone": "010-1234-5678"})
        for step in job["steps"]:
            if step.get("action") == "goto":
                step["url"] = FIXTURE.as_uri()
        return job

    @unittest.skipUnless(_RUNNABLE, "playwright chromium 미설치 — 선택 의존")
    def test_auto_site_fills_and_submits_mock(self):
        job = self._job("https://mock.local/apply/x")
        res = runner.run_job(job, headless=True)
        self.assertEqual(res["mode"], "auto")
        self.assertTrue(res["submitted"])
        self.assertIn("신청완료", res["result_text"])

    @unittest.skipUnless(_RUNNABLE, "playwright chromium 미설치 — 선택 의존")
    def test_semi_site_pauses_before_submit(self):
        job = self._job("https://apply.example-city.go.kr/e")
        res = runner.run_job(job, headless=True)
        self.assertEqual(res["mode"], "semi")
        self.assertFalse(res["submitted"])
        self.assertEqual(res["paused_reason"], "본인인증/최종제출은 사용자가 수행")
        self.assertTrue(any(s["action"] == "pause" for s in job["steps"]))

    @unittest.skipUnless(_RUNNABLE, "playwright chromium 미설치 — 선택 의존")
    def test_guard_strips_submit_when_not_auto(self):
        # 반자동 잡에 submit이 잘못 끼어 있어도 러너가 실행하지 않는다(C5 이중 방어).
        job = self._job("https://apply.example-city.go.kr/e")
        job["steps"].append({"action": "submit", "selector": "#submit"})
        res = runner.run_job(job, headless=True)
        self.assertFalse(res["submitted"])

    def test_dry_run_no_browser(self):
        # Playwright 유무와 무관하게 항상 통과(무키·오프라인 계획 경로).
        job = self._job("https://mock.local/apply/x")
        res = runner.run_job(job, dry_run=True)
        self.assertFalse(res["submitted"])
        self.assertEqual(res["mode"], "auto")
        self.assertIn("스텝", res["result_text"])

    def test_dry_run_semi_mode_reports_no_submit_step(self):
        job = self._job("https://apply.example-city.go.kr/e")
        res = runner.run_job(job, dry_run=True)
        self.assertEqual(res["mode"], "semi")
        self.assertFalse(res["submitted"])


if __name__ == "__main__":
    unittest.main()
