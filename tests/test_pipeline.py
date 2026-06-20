"""파이프라인 단위 테스트 (stdlib unittest, 외부 의존 없음).

실행: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import datetime as dt
import tempfile
import unittest
from pathlib import Path

from scripts.common import config, okf
from scripts.ingest.kopis import KopisAdapter
from scripts.ingest.tourapi import TourApiAdapter
from scripts.normalize import upsert as upsert_mod
from scripts.recommend import rank
from scripts.notify import dispatch as notify
from scripts.macro import apply as macro


class TestConfig(unittest.TestCase):
    def test_canonical_sido_alias_and_partial(self):
        self.assertEqual(config.canonical_sido("부산"), "부산광역시")
        self.assertEqual(config.canonical_sido("경기"), "경기도")
        self.assertEqual(config.canonical_sido("서울특별시"), "서울특별시")

    def test_age_bands_ranges(self):
        self.assertEqual(config.age_bands("7-13"), ["어린이"])
        self.assertIn("청년", config.age_bands("19-"))
        self.assertIn("노년", config.age_bands("19-"))
        self.assertEqual(config.age_bands(None), [])
        self.assertEqual(config.age_bands("12"), ["어린이"])

    def test_map_theme(self):
        self.assertEqual(config.map_theme("tourapi", "A02070100"), "축제")
        self.assertIsNone(config.map_theme("kopis", "ZZZZ"))


class TestOKF(unittest.TestCase):
    def _ev(self):
        return {
            "id": "kopis:X1", "name": "행사", "start_date": "2026-07-18T00:00:00+09:00",
            "url": "https://e", "location": {"sido": "서울특별시"}, "source": "kopis",
            "fetched_at": "2026-06-20T00:00:00+09:00",
        }

    def test_content_hash_ignores_volatile(self):
        a = self._ev(); b = dict(a, fetched_at="2026-06-21T00:00:00+09:00")
        self.assertEqual(okf.content_hash(a), okf.content_hash(b))

    def test_content_hash_detects_change(self):
        a = self._ev(); b = dict(a, name="다른행사")
        self.assertNotEqual(okf.content_hash(a), okf.content_hash(b))

    def test_event_path_layout(self):
        p = okf.event_path(self._ev())
        self.assertTrue(str(p).endswith("events/2026/07/seoul/kopis_X1.md"))

    def test_markdown_roundtrip(self):
        ev = self._ev()
        md = okf.to_markdown(ev, "본문")
        fm, body = okf.parse_markdown(md)
        self.assertEqual(fm["id"], "kopis:X1")
        self.assertIn("본문", body)


class TestAdapters(unittest.TestCase):
    def test_kopis_offline_mapping(self):
        rows = KopisAdapter(offline=True).collect()
        ids = {r["id"] for r in rows}
        self.assertIn("kopis:PF200001", ids)
        first = next(r for r in rows if r["id"] == "kopis:PF200001")
        self.assertEqual(first["location"]["sido"], "서울특별시")
        self.assertEqual(first["event_type"], "MusicEvent")
        self.assertTrue(first["start_date"].startswith("2026-07-18"))
        self.assertTrue(first["content_hash"].startswith("sha256:"))

    def test_tourapi_offline_mapping_geo(self):
        rows = TourApiAdapter(offline=True).collect()
        e = next(r for r in rows if r["id"] == "tourapi:3001001")
        self.assertEqual(e["event_type"], "Festival")
        self.assertEqual(e["location"]["sido"], "강원특별자치도")
        self.assertAlmostEqual(e["location"]["lat"], 37.7519, places=3)


class TestUpsert(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = okf.EVENTS_DIR
        okf.EVENTS_DIR = Path(self.tmp.name)

    def tearDown(self):
        okf.EVENTS_DIR = self._orig
        self.tmp.cleanup()

    def _ev(self, **over):
        ev = {
            "id": "kopis:U1", "name": "행사", "start_date": "2026-07-18T00:00:00+09:00",
            "url": "https://e", "location": {"sido": "서울특별시"}, "source": "kopis",
            "fetched_at": "2026-06-20T00:00:00+09:00", "status": "Scheduled",
        }
        ev.update(over)
        ev["content_hash"] = okf.content_hash(ev)
        return ev

    def test_create_then_skip_idempotent(self):
        ev = self._ev()
        self.assertEqual(upsert_mod.upsert([ev])["created"], 1)
        self.assertEqual(upsert_mod.upsert([ev])["skipped"], 1)

    def test_update_on_change(self):
        upsert_mod.upsert([self._ev()])
        s = upsert_mod.upsert([self._ev(name="변경")])
        self.assertEqual(s["updated"], 1)

    def test_archived_policy(self):
        upsert_mod.upsert([self._ev()])
        s = upsert_mod.upsert([], processed_sources={"kopis"})
        self.assertEqual(s["archived"], 1)
        # 두 번째엔 이미 archived → 다시 archive 안 함
        s2 = upsert_mod.upsert([], processed_sources={"kopis"})
        self.assertEqual(s2["archived"], 0)


class TestRecommend(unittest.TestCase):
    def _events(self):
        return [
            {"id": "a", "name": "무료공연", "sido": "서울특별시", "themes": ["공연"],
             "age_bands": ["어린이"], "price": "free", "status": "Open",
             "start_date": "2026-07-18T00:00:00+09:00", "end_date": "2026-07-20T00:00:00+09:00",
             "lat": 37.57, "lng": 126.97},
            {"id": "b", "name": "유료전시", "sido": "부산광역시", "themes": ["전시"],
             "age_bands": [], "price": 20000, "status": "Scheduled",
             "start_date": "2026-07-18T00:00:00+09:00"},
        ]

    def test_free_only_excludes_paid(self):
        prof = {"regions": ["서울특별시", "부산광역시"], "themes": ["공연", "전시"],
                "age_band": "어린이", "prefs": {"free_only": True}}
        recs = rank.recommend(prof, self._events())
        self.assertEqual([r["id"] for r in recs], ["a"])

    def test_plan_respects_max_per_day(self):
        prof = {"regions": ["서울특별시"], "themes": ["공연"], "age_band": "어린이",
                "available_dates": ["2026-07-18"], "prefs": {"free_only": True, "max_per_day": 1}}
        cands = rank.recommend(prof, self._events())
        plan = rank.plan_week(prof, cands)
        self.assertEqual(len(plan["days"][0]["items"]), 1)

    def test_haversine_zero(self):
        d = rank._haversine({"lat": 37.5, "lng": 127.0}, 37.5, 127.0)
        self.assertAlmostEqual(d, 0.0, places=4)


class TestNotify(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._orig = notify.SENT_PATH
        notify.SENT_PATH = Path(self.tmp.name) / "sent.json"

    def tearDown(self):
        notify.SENT_PATH = self._orig
        self.tmp.cleanup()

    def _events(self):
        return [{"id": "x", "name": "마감임박행사", "sido": "서울특별시", "themes": ["공연"],
                 "age_bands": ["어린이"], "status": "Open",
                 "application_start": "2026-06-25T09:00:00+09:00",
                 "application_end": "2026-07-10T18:00:00+09:00", "url": "https://e"}]

    def test_deadline_d1_and_filter_match(self):
        subs = [{"id": "s1", "filters": {"sido": "서울특별시"}, "channel": "stdout"}]
        now = dt.datetime(2026, 7, 9, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        out = notify.compute_notifications(self._events(), subs, now)
        self.assertEqual(len(out), 1)
        self.assertIn("D-1", out[0]["title"])

    def test_filter_mismatch_no_notif(self):
        subs = [{"id": "s2", "filters": {"sido": "부산광역시"}, "channel": "stdout"}]
        now = dt.datetime(2026, 7, 9, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        self.assertEqual(notify.compute_notifications(self._events(), subs, now), [])

    def test_dedupe_suppresses_second_run(self):
        subs = [{"id": "s1", "filters": {"sido": "서울특별시"}, "channel": "stdout"}]
        now = dt.datetime(2026, 7, 9, 10, 0, tzinfo=dt.timezone(dt.timedelta(hours=9)))
        r1 = notify.dispatch(self._events(), subs, now)
        r2 = notify.dispatch(self._events(), subs, now)
        self.assertEqual(r1["delivered"], 1)
        self.assertEqual(r2["suppressed"], 1)


class TestMacro(unittest.TestCase):
    def test_auto_site_has_submit(self):
        ev = {"id": "m1", "url": "https://mock.local/apply/x"}
        job = macro.plan_job(ev, {"name": "홍길동", "phone": "010"})
        self.assertEqual(job["mode"], "auto")
        self.assertTrue(any(s["action"] == "submit" for s in job["steps"]))
        self.assertTrue(macro.is_auto_submit(job))

    def test_tos_blocked_site_is_semi_no_autosubmit(self):
        ev = {"id": "m2", "url": "https://apply.example-city.go.kr/e"}
        job = macro.plan_job(ev, {"name": "홍길동", "phone": "010"})
        self.assertEqual(job["mode"], "semi")
        self.assertFalse(any(s["action"] == "submit" for s in job["steps"]))
        self.assertTrue(any(s["action"] == "pause" for s in job["steps"]))
        self.assertFalse(macro.is_auto_submit(job))  # 안전 보장

    def test_template_substitution(self):
        ev = {"id": "m3", "url": "https://mock.local/apply/z"}
        job = macro.plan_job(ev, {"name": "김철수", "phone": "010-1234"})
        fills = {s["selector"]: s["value"] for s in job["steps"] if s["action"] == "fill"}
        self.assertEqual(fills["#name"], "김철수")
        self.assertEqual(fills["#phone"], "010-1234")

    def test_unknown_site_manual(self):
        job = macro.plan_job({"id": "m4", "url": "https://unknown.example/x"}, {})
        self.assertEqual(job["mode"], "manual")


if __name__ == "__main__":
    unittest.main()
