from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .models import OrderRow


FIELDS = ["source", "section", "section_url", "listing_page", "page_number", "serial_number", "order_date", "subject", "order_remarks", "pdf_url", "local_pdf_path", "download_status", "http_status", "file_size_bytes", "sha256", "downloaded_at", "error"]


class Storage:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.pdf_root = self.root / "pdf"
        self.report_root = self.root / "reports"
        self.report_root.mkdir(parents=True, exist_ok=True)
        (self.root / "metadata").mkdir(parents=True, exist_ok=True)

    def destination(self, row: OrderRow, content_key: str) -> Path:
        return self.pdf_root / row.section.lower().replace(" ", "-") / f"{safe_filename(row.order_date)}-{safe_filename(row.serial_number)}-{content_key[:12]}.pdf"

    def save_reports(self, rows: list[OrderRow], errors: list[dict]) -> None:
        document_path = self.report_root / "ibbi-unified-documents.csv"
        with document_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for row in rows:
                values = row.as_dict()
                values["source"] = "ibbi.gov.in"
                writer.writerow(values)
        summary: dict[str, dict] = {}
        for row in rows:
            item = summary.setdefault(row.section, {"section": row.section, "section_url": row.section_url, "pages_scanned": set(), "rows_discovered": 0, "unique_pdf_urls": set(), "downloaded_count": 0, "already_exists_count": 0, "failed_count": 0, "missing_pdf_count": 0})
            item["pages_scanned"].add(row.listing_page)
            item["rows_discovered"] += 1
            if row.pdf_url:
                item["unique_pdf_urls"].add(row.pdf_url)
            else:
                item["missing_pdf_count"] += 1
            if row.download_status == "downloaded": item["downloaded_count"] += 1
            if row.download_status == "already_exists": item["already_exists_count"] += 1
            if row.download_status in {"request_failed", "invalid_pdf_response", "write_failed"}: item["failed_count"] += 1
        summary_path = self.report_root / "ibbi-section-summary.csv"
        summary_fields = ["section", "section_url", "pages_scanned", "rows_discovered", "unique_pdf_urls", "downloaded_count", "already_exists_count", "failed_count", "missing_pdf_count"]
        with summary_path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=summary_fields)
            writer.writeheader()
            for item in summary.values():
                item = item.copy()
                item["pages_scanned"] = len(item["pages_scanned"])
                item["unique_pdf_urls"] = len(item["unique_pdf_urls"])
                writer.writerow(item)
        with (self.report_root / "ibbi-errors.csv").open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=["url", "error", "status_code"])
            writer.writeheader()
            writer.writerows(errors)
        (self.root / "metadata" / "manifest.json").write_text(json.dumps({"updated_at": datetime.now(timezone.utc).isoformat(), "documents": len(rows), "errors": len(errors)}, indent=2) + "\n", encoding="utf-8")


def safe_filename(value: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()[:50] or "unknown"
