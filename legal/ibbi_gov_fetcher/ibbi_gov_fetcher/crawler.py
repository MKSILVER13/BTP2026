from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from .client import FetchError, WebClient
from .models import OrderRow
from .parser import pagination_links, parse_orders
from .storage import Storage


class IBBICrawler:
    def __init__(self, client: WebClient, storage: Storage, download: bool = False, max_documents: int | None = None):
        self.client = client
        self.storage = storage
        self.download = download
        self.max_documents = max_documents
        self.rows: list[OrderRow] = []
        self.errors: list[dict] = []
        self.downloaded_urls: dict[str, Path] = {}

    def run_section(self, section: dict, all_pages: bool = False, page: int = 1) -> None:
        first = section["url"] if page == 1 else f"{section['url']}?page={page}"
        queue = [first]
        visited: set[str] = set()
        while queue and (self.max_documents is None or len(self.rows) < self.max_documents):
            page_url = queue.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)
            try:
                html = self.client.text(page_url)
            except FetchError as exc:
                self.errors.append({"url": page_url, "error": str(exc), "status_code": exc.status_code})
                continue
            page_rows = parse_orders(html, section["name"], section["url"], page_url)
            for row in page_rows:
                if self.max_documents is not None and len(self.rows) >= self.max_documents:
                    break
                self.rows.append(row)
                if self.download:
                    self._download(row)
            if all_pages:
                for next_url in pagination_links(html, page_url):
                    if next_url not in visited and next_url not in queue:
                        queue.append(next_url)

    def _download(self, row: OrderRow) -> None:
        if not row.pdf_url:
            row.download_status = "missing_pdf_link"
            return
        if row.pdf_url in self.downloaded_urls:
            row.local_pdf_path = str(self.downloaded_urls[row.pdf_url])
            row.download_status = "already_exists"
            return
        destination = self.storage.destination(row, __import__("hashlib").sha256(row.pdf_url.encode()).hexdigest())
        if destination.exists():
            row.local_pdf_path = str(destination.relative_to(self.storage.root))
            row.download_status = "already_exists"
            self.downloaded_urls[row.pdf_url] = destination
            return
        try:
            status, digest, size = self.client.download_pdf(row.pdf_url, destination)
            row.local_pdf_path = str(destination.relative_to(self.storage.root))
            row.download_status = "downloaded"
            row.http_status = status
            row.sha256 = digest
            row.file_size_bytes = size
            row.downloaded_at = datetime.now(timezone.utc).isoformat()
            self.downloaded_urls[row.pdf_url] = destination
        except FetchError as exc:
            row.download_status = "invalid_pdf_response" if "not a PDF" in str(exc) else "request_failed"
            row.http_status = exc.status_code or ""
            row.error = str(exc)
            self.errors.append({"url": row.pdf_url, "error": str(exc), "status_code": exc.status_code})
        except OSError as exc:
            row.download_status = "write_failed"
            row.error = str(exc)
            self.errors.append({"url": row.pdf_url, "error": str(exc), "status_code": ""})
