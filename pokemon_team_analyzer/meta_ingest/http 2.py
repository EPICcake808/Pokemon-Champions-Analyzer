"""Minimal, dependency-light HTTP client for the ingestion pipeline.

Mirrors the ``urllib`` + ``certifi`` style already used in
:mod:`pokemon_team_analyzer.meta_snapshots` so ingestion needs no extra runtime
dependency. Adds retries, exponential backoff, and best-effort honoring of
``Retry-After`` / rate-limit response headers so the Limitless API is queried
politely.
"""

from __future__ import annotations

import json
import ssl
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi

from . import USER_AGENT

_SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.5
# Statuses worth retrying: transient server errors + explicit rate limiting.
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})


class HttpError(RuntimeError):
    """Raised when a request ultimately fails after exhausting retries."""

    def __init__(self, url: str, status: int | None, reason: str) -> None:
        self.url = url
        self.status = status
        self.reason = reason
        super().__init__(f"GET {url} failed (status={status}): {reason}")


@dataclass(frozen=True)
class HttpResponse:
    url: str
    status: int
    body: str


def _retry_after_seconds(headers: Any, attempt: int) -> float:
    """Resolve a backoff delay, preferring the server's ``Retry-After`` hint."""

    retry_after = None
    if headers is not None:
        retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return max(0.0, float(retry_after))
        except (TypeError, ValueError):
            pass
    return DEFAULT_BACKOFF_SECONDS * (2 ** attempt)


def get(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    max_retries: int = DEFAULT_MAX_RETRIES,
    accept: str = "application/json",
    sleep=time.sleep,
) -> HttpResponse:
    """GET ``url`` with retries/backoff. Raises :class:`HttpError` on failure.

    ``sleep`` is injectable so tests can run without real delays.
    """

    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": accept,
    }
    if headers:
        request_headers.update(headers)

    last_status: int | None = None
    last_reason = "no attempt made"

    for attempt in range(max_retries + 1):
        request = Request(url, headers=request_headers)
        try:
            with urlopen(request, timeout=timeout, context=_SSL_CONTEXT) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
                return HttpResponse(url=response.url, status=response.status, body=body)
        except HTTPError as error:  # noqa: PERF203 - retry loop is intentional
            last_status = error.code
            last_reason = f"HTTP {error.code} {error.reason}"
            if error.code in _RETRYABLE_STATUSES and attempt < max_retries:
                sleep(_retry_after_seconds(error.headers, attempt))
                continue
            raise HttpError(url, error.code, last_reason) from error
        except (URLError, TimeoutError, OSError) as error:
            last_status = None
            last_reason = str(getattr(error, "reason", error)) or error.__class__.__name__
            if attempt < max_retries:
                sleep(DEFAULT_BACKOFF_SECONDS * (2 ** attempt))
                continue
            raise HttpError(url, None, last_reason) from error

    raise HttpError(url, last_status, last_reason)


def get_json(url: str, **kwargs: Any) -> Any:
    """GET ``url`` and parse the response body as JSON."""

    response = get(url, accept="application/json", **kwargs)
    try:
        return json.loads(response.body)
    except json.JSONDecodeError as error:
        raise HttpError(url, response.status, f"invalid JSON: {error}") from error


def get_text(url: str, *, accept: str = "text/html,application/xhtml+xml", **kwargs: Any) -> str:
    """GET ``url`` and return the response body as text."""

    return get(url, accept=accept, **kwargs).body


def post_json(
    url: str,
    payload: Any,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
) -> HttpResponse:
    """POST ``payload`` as JSON to ``url``. Raises :class:`HttpError` on failure.

    POSTs are not retried (they are not assumed idempotent); the caller decides.
    """

    body = json.dumps(payload).encode("utf-8")
    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if headers:
        request_headers.update(headers)

    request = Request(url, data=body, headers=request_headers, method="POST")
    try:
        with urlopen(request, timeout=timeout, context=_SSL_CONTEXT) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return HttpResponse(url=response.url, status=response.status, body=response.read().decode(charset, errors="replace"))
    except HTTPError as error:
        detail = ""
        try:
            detail = error.read().decode("utf-8", errors="replace")[:300]
        except Exception:  # noqa: BLE001 - best-effort error detail only
            detail = ""
        raise HttpError(url, error.code, f"HTTP {error.code} {error.reason} {detail}".strip()) from error
    except (URLError, TimeoutError, OSError) as error:
        reason = str(getattr(error, "reason", error)) or error.__class__.__name__
        raise HttpError(url, None, reason) from error
