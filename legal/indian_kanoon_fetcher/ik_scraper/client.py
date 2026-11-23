from __future__ import annotations

import time
from typing import Callable

import requests


class FetchError(RuntimeError):
    def __init__(self, url: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class WebClient:
    def __init__(
        self,
        delay: float = 1.0,
        timeout: float = 30.0,
        retries: int = 3,
        user_agent: str = "IndianKanoonResearchScraper/0.1 (+local research tool)",
        session: requests.Session | None = None,
        sleeper: Callable[[float], None] = time.sleep,
    ):
        self.delay = max(0.0, delay)
        self.timeout = timeout
        self.retries = max(0, retries)
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml"})
        self._sleeper = sleeper
        self._last_request = 0.0

    def get(self, url: str) -> str:
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            self._sleeper(wait)
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout)
                self._last_request = time.monotonic()
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    self._sleeper(min(30.0, 2**attempt))
                    continue
                response.raise_for_status()
                return response.text
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.retries:
                    self._sleeper(min(30.0, 2**attempt))
                    continue
                status = getattr(getattr(exc, "response", None), "status_code", None)
                raise FetchError(url, str(exc), status) from exc
        raise FetchError(url, str(last_error or "request failed"))
