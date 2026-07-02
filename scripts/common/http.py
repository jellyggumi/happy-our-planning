"""공통 HTTP 재시도/백오프 정책 (docs/08 견고성).

ai_planner 등 원격 호출이 일시적 장애(타임아웃·연결오류·5xx·429)에 한해서만
지수 백오프로 재시도하도록 정책을 한 곳에 모은다. 4xx(429 제외)는 클라이언트
오류이므로 즉시 실패한다(재시도해도 결과 동일).

순수 로직(should_retry_status / request_with_retry)은 send 콜러블과 sleep을
주입받아 네트워크 없이 테스트된다. httpx에 직접 의존하지 않는다(호출부가 주입).
"""
from __future__ import annotations

import json
import re
import time
from typing import Callable, Protocol

# 명시적 재시도 상태 + 그 외 5xx 일반화.
RETRY_STATUS = {429, 500, 502, 503, 504}
DEFAULT_MAX_DELAY = 300.0
_DURATION_RE = re.compile(r"^\s*(?P<num>\d+(?:\.\d+)?)s\s*$")



def should_retry_status(status: int) -> bool:
    """이 HTTP 상태코드가 재시도 가치가 있는 일시적 장애인가."""
    return status in RETRY_STATUS or 500 <= status < 600


class HttpError(Exception):
    """비재시도 HTTP 실패(4xx 또는 재시도 소진된 5xx)."""

    def __init__(
        self,
        status: int,
        body: str = "",
        *,
        retry_after: float | None = None,
    ) -> None:
        msg = f"HTTP {status}: {body[:200]}"
        if retry_after is not None:
            msg = f"{msg} (retry_after={retry_after:.3f}s)"
        super().__init__(msg)
        self.status = status
        self.body = body
        self.retry_after = retry_after


class _Resp(Protocol):
    status_code: int
    text: str
    headers: dict

    def json(self) -> dict: ...


def _duration_seconds(value: str | None) -> float | None:
    """Google RetryInfo 형식('103705.991s') 또는 Retry-After 초 값을 파싱."""
    if not value:
        return None
    value = value.strip()
    if value.isdigit():
        return float(value)
    m = _DURATION_RE.match(value)
    if m:
        return float(m.group("num"))
    return None


def _json_body(resp: _Resp) -> dict:
    try:
        return resp.json()
    except Exception:
        try:
            return json.loads(getattr(resp, "text", "") or "{}")
        except Exception:
            return {}


def retry_after_seconds(resp: _Resp) -> float | None:
    """응답 헤더/Google RPC RetryInfo에서 권장 재시도 지연(초)을 추출."""
    headers = getattr(resp, "headers", {}) or {}
    direct = _duration_seconds(headers.get("Retry-After") or headers.get("retry-after"))
    if direct is not None:
        return direct
    data = _json_body(resp)
    details = ((data.get("error") or {}).get("details") or [])
    for detail in details:
        if str(detail.get("@type", "")).endswith("google.rpc.RetryInfo"):
            parsed = _duration_seconds(detail.get("retryDelay"))
            if parsed is not None:
                return parsed
    metadata = {}
    for detail in details:
        metadata.update(detail.get("metadata") or {})
    return _duration_seconds(metadata.get("quotaResetDelay"))


def is_quota_exhausted(resp: _Resp) -> bool:
    """사용자/프로젝트 일일 할당량 소진처럼 즉시 폴백해야 하는 429인가."""
    if getattr(resp, "status_code", 200) != 429:
        return False
    data = _json_body(resp)
    err = data.get("error") or {}
    if err.get("status") == "RESOURCE_EXHAUSTED":
        return True
    for detail in err.get("details") or []:
        if detail.get("reason") == "QUOTA_EXHAUSTED":
            return True
    body = getattr(resp, "text", "") or ""
    return "QUOTA_EXHAUSTED" in body or "Individual quota reached" in body


def request_with_retry(
    send: Callable[[], _Resp],
    *,
    retries: int = 2,
    backoff: float = 0.5,
    max_delay: float = DEFAULT_MAX_DELAY,
    retry_exceptions: tuple[type[BaseException], ...] = (),
    sleep: Callable[[float], None] = time.sleep,
) -> _Resp:
    """`send()`를 호출하고 일시적 장애 시 지수 백오프로 재시도한다.

    인자:
        send: 인자 없는 호출자. `.status_code`(int) 응답을 반환하거나
              `retry_exceptions`(예: httpx.TransportError)를 던진다.
        retries: 추가 재시도 횟수(총 시도 = retries + 1).
        backoff: 1차 대기(초). n번째 재시도 전 `backoff * 2**n`초 대기.
        max_delay: 서버가 요구한 Retry-After/RetryInfo 지연의 허용 상한(초).
                   이보다 긴 지연이나 할당량 소진 429는 재시도하지 않고 즉시 실패한다.
        retry_exceptions: 재시도 대상 예외 튜플.
        sleep: 대기 함수(테스트 주입용).

    반환: status_code < 400 인 첫 응답.
    예외: HttpError(비재시도 상태 또는 재시도 소진), 또는 재시도 소진된 send 예외.
    """
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            resp = send()
        except retry_exceptions as exc:
            last_exc = exc
            if attempt < retries:
                sleep(backoff * (2 ** attempt))
                continue
            raise
        status = getattr(resp, "status_code", 200)
        if 200 <= status < 300:
            return resp
        if should_retry_status(status) and attempt < retries:
            server_delay = retry_after_seconds(resp)
            if is_quota_exhausted(resp) or (server_delay is not None and server_delay > max_delay):
                raise HttpError(status, getattr(resp, "text", ""), retry_after=server_delay)
            sleep(server_delay if server_delay is not None else backoff * (2 ** attempt))
            continue
        raise HttpError(status, getattr(resp, "text", ""), retry_after=retry_after_seconds(resp))
    # 도달 불가: 루프는 반환/예외로 종료된다.
    if last_exc is not None:  # pragma: no cover - 방어
        raise last_exc
    raise RuntimeError("request_with_retry: unreachable")  # pragma: no cover
