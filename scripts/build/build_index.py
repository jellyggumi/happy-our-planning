"""지식 DB(Markdown) → 정적 프런트엔드용 JSON 빌드.

산출(web/public/data/):
  events.json   검색/지도/리스트용 평탄화 배열(archived 제외)
  facets.json   필터 카운트(지역/테마/나이밴드/상태/유형)
  regions.json  시/도별 건수 + 대표 좌표(코로플레스/핀 보조)
  updated.json  생성시각·총계·소스별 신선도
"""
from __future__ import annotations

import datetime as dt
import json
from collections import Counter, defaultdict
from pathlib import Path

from scripts.common.config import ROOT, age_bands, all_regions
from scripts.common.okf import iter_events

OUT_DIR = ROOT / "web" / "public" / "data"


def _flatten(fm: dict) -> dict:
    loc = fm.get("location") or {}
    age = fm.get("age")
    return {
        "id": fm.get("id"),
        "name": fm.get("name"),
        "description": fm.get("description"),
        "event_type": fm.get("event_type"),
        "themes": fm.get("themes") or [],
        "start_date": fm.get("start_date"),
        "end_date": fm.get("end_date"),
        "application_start": fm.get("application_start"),
        "application_end": fm.get("application_end"),
        "status": fm.get("status"),
        "sido": loc.get("sido"),
        "sigungu": loc.get("sigungu"),
        "lat": loc.get("lat"),
        "lng": loc.get("lng"),
        "age": age,
        "age_bands": age_bands(age),
        "audience": fm.get("audience") or [],
        "price": fm.get("price"),
        "organizer": fm.get("organizer"),
        "url": fm.get("url"),
        "image": fm.get("image"),
        "source": fm.get("source"),
        "verification": fm.get("x_verification"),
        "confidence": fm.get("x_confidence"),
    }


def build() -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    events: list[dict] = []
    archived = 0
    by_source_count: Counter = Counter()
    oldest_fetch: dict[str, str] = {}

    for _path, fm, _body in iter_events():
        src = fm.get("source") or "unknown"
        by_source_count[src] += 1
        fetched = fm.get("fetched_at")
        if fetched and (src not in oldest_fetch or fetched < oldest_fetch[src]):
            oldest_fetch[src] = fetched
        if fm.get("status") == "archived":
            archived += 1
            continue
        events.append(_flatten(fm))

    # 정렬: 시작일 오름차순
    events.sort(key=lambda e: (e.get("start_date") or "9999"))

    # facets
    facets = {
        "sido": Counter(),
        "theme": Counter(),
        "age_band": Counter(),
        "status": Counter(),
        "event_type": Counter(),
    }
    region_count: Counter = Counter()
    region_coord: dict[str, list] = defaultdict(lambda: [0.0, 0.0, 0])
    for e in events:
        if e["sido"]:
            facets["sido"][e["sido"]] += 1
            region_count[e["sido"]] += 1
            if e["lat"] and e["lng"]:
                acc = region_coord[e["sido"]]
                acc[0] += e["lat"]; acc[1] += e["lng"]; acc[2] += 1
        for t in e["themes"]:
            facets["theme"][t] += 1
        for b in e["age_bands"]:
            facets["age_band"][b] += 1
        if e["status"]:
            facets["status"][e["status"]] += 1
        if e["event_type"]:
            facets["event_type"][e["event_type"]] += 1

    facets_out = {k: dict(v) for k, v in facets.items()}

    regions_out = []
    region_meta = {r["name"]: r for r in all_regions()}
    for name, cnt in sorted(region_count.items(), key=lambda x: -x[1]):
        acc = region_coord.get(name)
        centroid = ([acc[0] / acc[2], acc[1] / acc[2]] if acc and acc[2] else None)
        regions_out.append({
            "sido": name,
            "slug": region_meta.get(name, {}).get("slug", "unknown"),
            "count": cnt,
            "centroid": centroid,
        })

    updated = {
        "generated_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(timespec="seconds"),
        "total_active": len(events),
        "archived": archived,
        "by_source": dict(by_source_count),
        "freshness": oldest_fetch,
    }

    (OUT_DIR / "events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "facets.json").write_text(json.dumps(facets_out, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "regions.json").write_text(json.dumps(regions_out, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "updated.json").write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"build: events={len(events)} archived={archived} sido={len(regions_out)} themes={len(facets_out['theme'])}")
    return {"events": len(events), "archived": archived, "regions": len(regions_out)}


if __name__ == "__main__":
    build()
