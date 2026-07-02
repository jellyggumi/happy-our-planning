"""KOPIS(공연예술통합전산망) 어댑터. 공연/전시 목록 XML → OKF Event."""
from __future__ import annotations

import datetime as dt
from urllib.parse import parse_qsl, urljoin, urlsplit

from scripts.common.config import canonical_sido
from scripts.common.dates import combine_kst
from scripts.common.okf import content_hash
from scripts.ingest.base import SourceAdapter, log, now_kst

_GENRE_THEME = {
    "연극": ("공연", "Event"),
    "뮤지컬": ("공연", "MusicEvent"),
    "서양음악(클래식)": ("공연", "MusicEvent"),
    "한국음악(국악)": ("공연", "MusicEvent"),
    "대중음악": ("공연", "MusicEvent"),
    "무용": ("공연", "Event"),
    "대중무용": ("공연", "Event"),
    "서커스/마술": ("공연", "Event"),
    "복합": ("공연", "Event"),
    "전시": ("전시", "ExhibitionEvent"),
}

_STATE = {"공연중": "Scheduled", "공연예정": "Scheduled", "공연완료": "archived"}


def _kst_date(value: str, end: bool = False) -> str | None:
    """'2026.07.18' → ISO 8601(KST). end=True면 23:59:59."""
    value = (value or "").replace("-", ".").strip()
    try:
        d = dt.datetime.strptime(value, "%Y.%m.%d")
    except ValueError:
        return None
    return combine_kst(d, end)



def _api_window(days: int = 180) -> tuple[str, str]:
    """KOPIS 목록 API 조회 기본 기간: 오늘부터 `days`일."""
    today = dt.date.today()
    return today.strftime("%Y%m%d"), (today + dt.timedelta(days=days)).strftime("%Y%m%d")


def _auth_params(cfg: dict, api_key: str) -> dict[str, str]:
    auth = cfg.get("auth") or {}
    return {auth.get("param", "service"): api_key}


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


def _fetch_page(httpx, url: str, params: dict[str, str]) -> str:
    from scripts.common import http as _http

    resp = _http.request_with_retry(
        lambda: httpx.get(url, params=params, timeout=20, follow_redirects=True),
        retries=1,
        retry_exceptions=(httpx.TransportError,),
    )
    return resp.text

def _remote_error(records: list[dict]) -> str | None:
    if len(records) != 1:
        return None
    record = records[0]
    if record.get("mt20id"):
        return None
    code = record.get("returncode")
    msg = record.get("errmsg")
    if code or msg:
        return f"{code or 'unknown'} {msg or ''}".strip()
    return None


class KopisAdapter(SourceAdapter):
    key = "kopis"
    fmt = "xml"

    def _fetch_remote(self) -> list[dict]:  # pragma: no cover - 네트워크 경로
        import httpx

        start, end = _api_window()
        rows = _row_count(self.cfg)
        records: list[dict] = []
        for page in range(1, _page_count(self.cfg) + 1):
            url, endpoint_params = _endpoint_request(self.cfg, "list", start=start, end=end, page=page)
            text = _fetch_page(httpx, url, {**endpoint_params, **_auth_params(self.cfg, self.api_key)})
            page_records = self._parse_xml(text)
            err = _remote_error(page_records)
            if err:
                log.warning("[%s] remote error: %s", self.key, err)
                return []
            records.extend(page_records)
            if len(page_records) < rows:
                break
        return records

    def map_to_okf(self, n: dict) -> dict | None:
        mt20id = n.get("mt20id")
        name = n.get("prfnm")
        if not mt20id or not name:
            return None
        genre = (n.get("genrenm") or "").strip()
        theme, event_type = _GENRE_THEME.get(genre, ("공연", "Event"))
        start = _kst_date(n.get("prfpdfrom", ""))
        end = _kst_date(n.get("prfpdto", ""), end=True)
        sido = canonical_sido(n.get("area"))
        if not start or not sido:
            return None
        event = {
            "id": f"kopis:{mt20id}",
            "name": name,
            "event_type": event_type,
            "themes": [theme],
            "start_date": start,
            "status": _STATE.get((n.get("prfstate") or "").strip(), "Scheduled"),
            "attendance_mode": "Offline",
            "location": {
                "name": n.get("fcltynm") or None,
                "sido": sido,
            },
            "url": f"https://www.kopis.or.kr/por/db/pblprfr/pblprfrView.do?mt20id={mt20id}",
            "source": self.key,
            "source_url": f"{self.cfg.get('base_url','')}/pblprfr/{mt20id}",
            "fetched_at": now_kst(),
        }
        if end:
            event["end_date"] = end
        if n.get("poster"):
            event["image"] = n["poster"]
        event["content_hash"] = content_hash(event)
        return event


if __name__ == "__main__":
    rows = KopisAdapter().collect()
    print(f"kopis: {len(rows)} OKF 레코드")
    for r in rows[:3]:
        print(" -", r["id"], r["name"], r["location"]["sido"])
