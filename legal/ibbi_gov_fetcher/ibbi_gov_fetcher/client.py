from __future__ import annotations

import hashlib
from itertools import chain
import time
from pathlib import Path
from typing import Callable

import requests


class FetchError(RuntimeError):
    def __init__(self, url: str, message: str, status_code: int | None = None):
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class WebClient:
    def __init__(self, delay: float = 1.0, timeout: float = 60.0, retries: int = 3, sleeper: Callable[[float], None] = time.sleep):
        self.delay = max(0.0, delay)
        self.timeout = timeout
        self.retries = max(0, retries)
        self.sleeper = sleeper
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "IBBIGovResearchFetcher/0.1 (+local research tool)", "Accept": "text/html,application/xhtml+xml,application/pdf"})
        self.last_request = 0.0

    def request(self, url: str, stream: bool = False) -> requests.Response:
        wait = self.delay - (time.monotonic() - self.last_request)
        if wait > 0:
            self.sleeper(wait)
        for attempt in range(self.retries + 1):
            try:
                response = self.session.get(url, timeout=self.timeout, stream=stream)
                self.last_request = time.monotonic()
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.retries:
                    response.close()
                    self.sleeper(min(30.0, 2**attempt))
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                if attempt < self.retries:
                    self.sleeper(min(30.0, 2**attempt))
                    continue
                status = getattr(getattr(exc, "response", None), "status_code", None)
                raise FetchError(url, str(exc), status) from exc
        raise FetchError(url, "request failed")

    def text(self, url: str) -> str:
        response = self.request(url)
        try:
            return response.text
        finally:
            response.close()

    def download_pdf(self, url: str, destination: Path) -> tuple[int, str, int]:
        response = self.request(url, stream=True)
        try:
            first_chunk = next(response.iter_content(8192), b"")
            content_type = response.headers.get("Content-Type", "").lower()
            if not first_chunk.startswith(b"%PDF") and "pdf" not in content_type:
                raise FetchError(url, f"response is not a PDF (content-type: {content_type or 'unknown'})", response.status_code)
            destination.parent.mkdir(parents=True, exist_ok=True)
            partial = destination.with_suffix(destination.suffix + ".part")
            digest = hashlib.sha256()
            size = 0
            with partial.open("wb") as handle:
                for chunk in chain((first_chunk,), response.iter_content(1024 * 64)):
                    if not chunk:
                        continue
                    handle.write(chunk)
                    digest.update(chunk)
                    size += len(chunk)
            partial.replace(destination)
            return response.status_code, digest.hexdigest(), size
        finally:
            response.close()
