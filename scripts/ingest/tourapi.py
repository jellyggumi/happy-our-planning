"""한국관광공사 TourAPI 4.0 searchFestival 어댑터. 지역축제 JSON → OKF Event."""
from __future__ import annotations

import datetime as dt
import json
from urllib.parse import parse_qsl, urljoin, urlsplit

from scripts.common.config import canonical_sido
from scripts.common.dates import combine_kst
from scripts.common.okf import content_hash
from scripts.ingest.base import SourceAdapter, now_kst


def _kst_date(value: str, end: bool = False) -> str | None:
    """'20260718' → ISO 8601(KST)."""
    value = (value or "").strip()
    try:
        d = dt.datetime.strptime(value, "%Y%m%d")
    except ValueError:
        return None
    return combine_kst(d, end)


def _api_window(days: int = 180) -> str:
    """TourAPI 축제 목록 조회 기본 시작일: 오늘부터."""
    return dt.date.today().strftime("%Y%m%d")


def _auth_params(cfg: dict, api_key: str) -> dict[str, str]:
    auth = cfg.get("auth") or {}
    return {auth.get("param", "serviceKey"): api_key}


def _endpoint_request(cfg: dict, name: str, **values) -> tuple[str, dict[str, str]]:
    base = cfg.get("base_url", "")
    path = (cfg.get("endpoints") or {}).get(name, "")
    rendered = path.lstrip("/").format(**values)
    parts = urlsplit(rendered)
    url = urljoin(base.rstrip("/") + "/", parts.path)
    return url, dict(parse_qsl(parts.query))


def _page_count(cfg: dict) -> int:
    return int(cfg.get("max_pages", 5))


def _row_count(cfg: dict) -> int:
    return int(cfg.get("rows", 100))


def _fetch_page(httpx, url: str, params: dict[str, str]) -> dict:
    from scripts.common import http as _http

    resp = _http.request_with_retry(
        lambda: httpx.get(url, params=params, timeout=20, follow_redirects=True),
        retries=1,
        retry_exceptions=(httpx.TransportError,),
    )
    return resp.json()


def _num(value) -> float | None:
    try:
        f = float(value)
        return f if f else None
    except (TypeError, ValueError):
        return None


class TourApiAdapter(SourceAdapter):
    key = "tourapi"
    fmt = "json"

    def _parse_json(self, text: str) -> list[dict]:
        data = json.loads(text)
        return self._items_from_response(data)

    @staticmethod
    def _items_from_response(data: dict) -> list[dict]:
        items = (
            data.get("response", {})
            .get("body", {})
            .get("items", {})
        )
        if not isinstance(items, dict):
            return []
        items = items.get("item", [])
        if isinstance(items, dict):  # 단건 응답
            return [items]
        return items if isinstance(items, list) else []

    def _fetch_remote(self) -> list[dict]:  # pragma: no cover - 네트워크 경로
        import httpx

        start = _api_window()
        rows = _row_count(self.cfg)
        records: list[dict] = []
        for page in range(1, _page_count(self.cfg) + 1):
            url, endpoint_params = _endpoint_request(self.cfg, "festival", start=start, page=page)
            data = _fetch_page(httpx, url, {**endpoint_params, **_auth_params(self.cfg, self.api_key)})
            page_records = self._items_from_response(data)
            records.extend(page_records)
            if len(page_records) < rows:
                break
        return records

    def map_to_okf(self, n: dict) -> dict | None:
        cid = n.get("contentid")
        name = n.get("title")
        start = _kst_date(n.get("eventstartdate", ""))
        if not cid or not name or not start:
            return None
        addr = (n.get("addr1") or "").strip()
        sido = canonical_sido(addr.split()[0]) if addr else None
        lat, lng = _num(n.get("mapy")), _num(n.get("mapx"))
        event = {
            "id": f"tourapi:{cid}",
            "name": name,
            "event_type": "Festival",
            "themes": ["축제"],
            "start_date": start,
            "status": "Scheduled",
            "attendance_mode": "Offline",
            "location": {
                "name": n.get("title"),
                "sido": sido,
                "address": addr or None,
            },
            "url": f"https://korean.visitkorea.or.kr/detail/ms_detail.do?cotid={cid}",
            "source": self.key,
            "source_url": f"{self.cfg.get('base_url','')}/detailCommon2?contentId={cid}",
            "fetched_at": now_kst(),
        }
        end = _kst_date(n.get("eventenddate", ""), end=True)
        if end:
            event["end_date"] = end
        if lat and lng:
            event["location"]["lat"] = lat
            event["location"]["lng"] = lng
        if n.get("firstimage"):
            event["image"] = n["firstimage"]
        event["content_hash"] = content_hash(event)
        return event


if __name__ == "__main__":
    rows = TourApiAdapter().collect()
    print(f"tourapi: {len(rows)} OKF 레코드")
    for r in rows[:3]:
        print(" -", r["id"], r["name"], r["location"]["sido"])
