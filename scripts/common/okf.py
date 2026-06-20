"""OKF(schema.org/Event) 레코드의 직렬화·해시·파일경로·파싱 유틸.

지식 DB의 단일 진실원천 단위인 Markdown(frontmatter=OKF) 파일을 다룬다.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Iterator

import yaml

from scripts.common.config import ROOT, sido_slug

EVENTS_DIR = ROOT / "knowledge" / "events"

# content_hash 계산에서 제외하는 휘발성/메타 필드
_VOLATILE = {"fetched_at", "content_hash", "x_lastSeen"}


def content_hash(event: dict) -> str:
    """정규 필드의 안정 직렬화에 대한 sha256. 휘발성 메타는 제외."""
    payload = {k: event[k] for k in sorted(event) if k not in _VOLATILE}
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _safe_id(event_id: str) -> str:
    return re.sub(r"[^0-9A-Za-z._-]", "_", event_id)


def event_path(event: dict) -> Path:
    """knowledge/events/<YYYY>/<MM>/<sido-slug>/<safe-id>.md"""
    start = str(event.get("start_date") or "0000-00")
    year, month = start[:4], start[5:7]
    if not month or not month.isdigit():
        month = "00"
    slug = sido_slug((event.get("location") or {}).get("sido"))
    return EVENTS_DIR / year / month / slug / f"{_safe_id(event['id'])}.md"


def to_markdown(event: dict, body: str = "") -> str:
    """OKF dict → frontmatter Markdown 문자열."""
    fm = yaml.safe_dump(event, allow_unicode=True, sort_keys=False, default_flow_style=False)
    body = body.strip()
    name = event.get("name", "")
    default_body = f"# {name}\n\n> 출처: {event.get('source','')} · 수집 {event.get('fetched_at','')}\n"
    return f"---\n{fm}---\n\n{body or default_body}\n"


def parse_markdown(text: str) -> tuple[dict | None, str]:
    """frontmatter Markdown → (OKF dict, body)."""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    fm = yaml.safe_load(text[3:end])
    body = text[end + 4:].lstrip("\n")
    return (fm if isinstance(fm, dict) else None), body


def iter_events() -> Iterator[tuple[Path, dict, str]]:
    """지식 DB의 모든 행사 (path, frontmatter, body)."""
    if not EVENTS_DIR.exists():
        return
    for path in sorted(EVENTS_DIR.rglob("*.md")):
        fm, body = parse_markdown(path.read_text(encoding="utf-8"))
        if fm is not None:
            yield path, fm, body
