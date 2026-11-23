from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from .client import FetchError, WebClient
from .models import Document
from .parser import catalogue_search_url, document_links, pagination_links, parse_catalogue, parse_classification, parse_document
from .storage import Storage


class CategoryCrawler:
    def __init__(self, client: WebClient, storage: Storage):
        self.client = client
        self.storage = storage
        self.last_collection_errors: list[dict[str, str | int | None]] = []

    def collect_documents(self, start_url: str, max_documents: int | None = None) -> list[str]:
        self.last_collection_errors = []
        queue = [start_url]
        visited_pages: set[str] = set()
        documents: list[str] = []
        seen_documents: set[str] = set()
        while queue and (max_documents is None or len(documents) < max_documents):
            page_url = queue.pop(0)
            if page_url in visited_pages:
                continue
            visited_pages.add(page_url)
            try:
                html = self.client.get(page_url)
            except FetchError as exc:
                self.last_collection_errors.append({"url": page_url, "error": str(exc), "status_code": exc.status_code})
                continue
            for url in document_links(html, page_url):
                if url not in seen_documents:
                    seen_documents.add(url)
                    documents.append(url)
                    if max_documents is not None and len(documents) >= max_documents:
                        break
            if max_documents is None or len(documents) < max_documents:
                derived_search_url = catalogue_search_url(page_url)
                if derived_search_url and derived_search_url not in visited_pages and derived_search_url not in queue:
                    queue.append(derived_search_url)
                # Court and law collections are hierarchical (for example,
                # collection -> year -> document list), so pagination alone
                # is not sufficient to reach leaf pages.
                for item in parse_catalogue(html, page_url):
                    if item.kind == "category" and item.url not in visited_pages and item.url not in queue:
                        queue.append(item.url)
                for next_url in pagination_links(html, page_url):
                    if next_url not in visited_pages and next_url not in queue:
                        queue.append(next_url)
        return documents

    def download_category(
        self,
        start_url: str,
        kind: str,
        path: list[str],
        max_documents: int | None = None,
        available_count: int | None = None,
        on_error: Callable[[str, Exception], None] | None = None,
    ) -> dict:
        directory = self.storage.category_dir(kind, path)
        manifest = {
            "category_url": start_url,
            "category_path": path,
            "available_count": available_count,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "successful": [],
            "failed": [],
            "discovery_failures": [],
        }
        for url in self.collect_documents(start_url, max_documents):
            try:
                document_id = url.rstrip("/").split("/")[-1]
                text_path = directory / f"{document_id}.txt"
                metadata_path = directory / f"{document_id}.json"
                classification_path = directory / f"{document_id}.classified.txt"
                if text_path.exists() and metadata_path.exists() and classification_path.exists():
                    manifest["successful"].append(document_id)
                    continue
                html = self.client.get(url)
                document = parse_document(html, url)
                classification = parse_classification(html)
                metadata = self.storage.save_document(document, directory, classification)
                manifest["successful"].append(metadata["document_id"])
            except Exception as exc:  # continue a batch after one bad document
                manifest["failed"].append({"url": url, "error": str(exc)})
                if on_error:
                    on_error(url, exc)
        manifest["discovery_failures"] = self.last_collection_errors
        manifest["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.storage.write_manifest(directory, manifest)
        self.storage.write_reports()
        return manifest
