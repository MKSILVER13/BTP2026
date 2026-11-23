from __future__ import annotations

import csv
import re
from pathlib import Path
from urllib.parse import urlparse

from .client import FetchError, WebClient
from .parser import catalogue_search_url, document_links, pagination_links, parse_catalogue, search_result_documents


class WebsiteInventory:
    """Build a one-time, document-level index without downloading documents."""

    def __init__(self, client: WebClient):
        self.client = client
        self.rows: dict[str, dict[str, str]] = {}
        self.categories: dict[str, dict[str, str | int]] = {}
        self.errors: list[dict[str, str | int | None]] = []

    def run(self) -> None:
        roots = [
            ("laws", "https://indiankanoon.org/browselaws/"),
            ("judgments", "https://indiankanoon.org/browse/"),
        ]
        for kind, url in roots:
            self._walk(kind, url, [])

    def _walk(self, kind: str, start_url: str, path: list[str]) -> None:
        queue: list[tuple[str, list[str]]] = [(start_url, path)]
        visited: set[str] = set()
        while queue:
            url, current_path = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            try:
                html = self.client.get(url)
            except FetchError as exc:
                self.errors.append({"url": url, "error": str(exc), "status_code": exc.status_code})
                continue
            category = "/".join(current_path) or kind
            self.categories.setdefault(category, {"kind": kind, "url": url, "catalogue_count": "", "pages": 0})
            self.categories[category]["pages"] = int(self.categories[category]["pages"]) + 1
            for result in search_result_documents(html, url):
                result.update({"document_type": kind, "catalogue_path": category, "year": self._year(current_path), "discovered_from": url})
                self.rows.setdefault(result["document_id"], result)
            for doc_url in document_links(html, url):
                doc_id = doc_url.rstrip("/").split("/")[-1]
                self.rows.setdefault(doc_id, {"document_id": doc_id, "title": doc_id, "url": doc_url, "document_type": kind, "catalogue_path": category, "year": self._year(current_path), "discovered_from": url})
            for item in parse_catalogue(html, url):
                if item.count is not None:
                    self.categories.setdefault(item.name, {"kind": kind, "url": item.url, "catalogue_count": item.count, "pages": 0})
                if item.kind == "category" and item.url not in visited and item.url not in {entry[0] for entry in queue}:
                    queue.append((item.url, current_path + [item.name]))
            derived = catalogue_search_url(url)
            if derived and derived not in visited and derived not in {entry[0] for entry in queue}:
                queue.append((derived, current_path))
            for next_url in pagination_links(html, url):
                if next_url not in visited and next_url not in {entry[0] for entry in queue}:
                    queue.append((next_url, current_path))

    @staticmethod
    def _year(path: list[str]) -> str:
        for value in reversed(path):
            if re.fullmatch(r"\d{4}", value):
                return value
        return ""

    def write_csv(self, output: str | Path) -> tuple[Path, Path, Path, Path]:
        root = Path(output)
        root.mkdir(parents=True, exist_ok=True)
        documents = root / "website-inventory.csv"
        categories = root / "website-category-summary.csv"
        errors = root / "website-inventory-errors.csv"
        type_year = root / "website-type-year-summary.csv"
        self._write(documents, ["document_id", "title", "url", "document_type", "catalogue_path", "year", "discovered_from"], list(self.rows.values()))
        category_rows = []
        for name, value in self.categories.items():
            category_rows.append({"catalogue_path": name, **value, "discovered_document_count": sum(1 for row in self.rows.values() if row["catalogue_path"] == name)})
        self._write(categories, ["catalogue_path", "kind", "url", "catalogue_count", "pages", "discovered_document_count"], category_rows)
        grouped: dict[tuple[str, str], int] = {}
        for row in self.rows.values():
            key = (row["document_type"], row["year"])
            grouped[key] = grouped.get(key, 0) + 1
        self._write(type_year, ["document_type", "year", "document_count"], [{"document_type": key[0], "year": key[1], "document_count": count} for key, count in sorted(grouped.items())])
        self._write(errors, ["url", "error", "status_code"], self.errors)
        return documents, categories, type_year, errors

    @staticmethod
    def _write(path: Path, fields: list[str], rows: list[dict]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
