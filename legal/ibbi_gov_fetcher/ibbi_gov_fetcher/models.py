from __future__ import annotations

from dataclasses import dataclass


@dataclass
class OrderRow:
    section: str
    section_url: str
    listing_page: str
    page_number: int
    serial_number: str
    order_date: str
    subject: str
    order_remarks: str
    pdf_url: str = ""
    local_pdf_path: str = ""
    download_status: str = "not_downloaded"
    http_status: str | int = ""
    file_size_bytes: int | str = ""
    sha256: str = ""
    downloaded_at: str = ""
    error: str = ""

    def as_dict(self) -> dict[str, str | int]:
        return self.__dict__.copy()
