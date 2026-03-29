"""Shared HTTP fetch with rate limiting and retry logic. stdlib only."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field


@dataclass(slots=True)
class RateLimiter:
    """Enforces a minimum interval between requests."""

    min_interval: float
    _last_call: float = field(default=0.0, repr=False)

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_call
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last_call = time.monotonic()


def fetch_json(
    url: str,
    *,
    rate_limiter: RateLimiter | None = None,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
    max_retries: int = 2,
) -> dict | list:
    """GET *url* and return parsed JSON.

    Retries on HTTP 429 and 5xx with exponential backoff.
    """
    if rate_limiter is not None:
        rate_limiter.wait()

    request_headers = {"Accept": "application/json", "User-Agent": "DiscoveryEngine/0.1"}
    if headers:
        request_headers.update(headers)

    req = urllib.request.Request(url, headers=request_headers)
    last_exc: Exception | None = None

    for attempt in range(1 + max_retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in (429, 500, 502, 503, 504) and attempt < max_retries:
                time.sleep(2**attempt)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(2**attempt)
                continue
            raise

    raise RuntimeError(f"fetch_json exhausted retries for {url}: {last_exc}")
