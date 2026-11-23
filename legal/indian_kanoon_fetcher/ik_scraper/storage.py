from __future__ import annotations

import json
import csv
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import Document


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:80] or "uncategorized"


class Storage:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def category_dir(self, kind: str, path: list[str]) -> Path:
        directory = self.root / slug(kind)
        for part in path:
            directory /= slug(part)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def save_document(self, document: Document, directory: Path, classification: list[tuple[str, str]] | None = None) -> dict[str, Any]:
        text_name = f"{document.document_id}.txt"
        metadata_name = f"{document.document_id}.json"
        classification_name = f"{document.document_id}.classified.txt"
        (directory / text_name).write_text(document.text + "\n", encoding="utf-8")
        if classification:
            classification_status = "classified"
            classified_text = "\n".join(f"{label}: {text}" for label, text in classification) + "\n"
        else:
            classification_status = "classification_unavailable"
            unclassified = " ".join(document.text.split())
            classified_text = f"classification_unavailable: true\nunclassified: {unclassified}\n"
        (directory / classification_name).write_text(classified_text, encoding="utf-8")
        metadata = document.as_metadata(text_name)
        metadata["scraped_at"] = datetime.now(timezone.utc).isoformat()
        metadata["classification_status"] = classification_status
        metadata["classification_source"] = "indian_kanoon_data_structure"
        metadata["classification_file"] = classification_name
        metadata["classification_labels"] = sorted({label for label, _ in classification or []})
        (directory / metadata_name).write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return metadata

    def write_manifest(self, directory: Path, manifest: dict[str, Any]) -> None:
        (directory / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_reports(self) -> tuple[Path, Path]:
        """Create document-level and category-level CSV reports from saved output."""
        document_rows: list[dict[str, Any]] = []
        category_rows: list[dict[str, Any]] = []
        for manifest_path in self.root.rglob("manifest.json"):
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            relative_category = manifest_path.parent.relative_to(self.root).as_posix()
            category_rows.append({
                "category": relative_category,
                "category_url": manifest.get("category_url", ""),
                "available_count": manifest.get("available_count", ""),
                "downloaded_count": len(manifest.get("successful", [])),
                "failed_count": len(manifest.get("failed", [])),
                "discovery_failure_count": len(manifest.get("discovery_failures", [])),
            })
            for metadata_path in manifest_path.parent.glob("*.json"):
                if metadata_path.name == "manifest.json":
                    continue
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                document_rows.append({
                    "category": relative_category,
                    "document_id": metadata.get("document_id", ""),
                    "title": metadata.get("title", ""),
                    "document_type": metadata.get("document_type", ""),
                    "source_url": metadata.get("source_url", ""),
                    "text_file": metadata.get("text_file", ""),
                    "scraped_at": metadata.get("scraped_at", ""),
                })
        document_path = self.root / "document-report.csv"
        category_path = self.root / "category-report.csv"
        self._write_csv(document_path, ["category", "document_id", "title", "document_type", "source_url", "text_file", "scraped_at"], document_rows)
        self._write_csv(category_path, ["category", "category_url", "available_count", "downloaded_count", "failed_count", "discovery_failure_count"], category_rows)
        return document_path, category_path

    @staticmethod
    def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
