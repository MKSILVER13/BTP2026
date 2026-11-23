from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .models import OrderRow


def text(node) -> str:
    return re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()


def parse_orders(html: str, section: str, section_url: str, page_url: str) -> list[OrderRow]:
    soup = BeautifulSoup(html, "html.parser")
    table = None
    for candidate in soup.select("table"):
        headers = [text(cell).lower() for cell in candidate.select("thead th")]
        if not headers:
            first = candidate.select_one("tr")
            headers = [text(cell).lower() for cell in first.select("th,td")] if first else []
        if any("subject" in header for header in headers) and any("date" in header for header in headers):
            table = candidate
            break
    if table is None:
        return []
    rows: list[OrderRow] = []
    page_match = re.search(r"(?:[?&])page=(\d+)", page_url)
    page_number = int(page_match.group(1)) if page_match else 1
    for tr in table.select("tbody tr") or table.select("tr")[1:]:
        cells = tr.select("td")
        if len(cells) < 4:
            continue
        links = [urljoin(page_url, anchor.get("href", "")) for anchor in cells[2].select("a[href]")]
        pdf_url = next((url for url in links if ".pdf" in url.lower() or "/uploads/" in url.lower()), "")
        rows.append(OrderRow(section, section_url, page_url, page_number, text(cells[0]), text(cells[1]), text(cells[2]), text(cells[3]), pdf_url))
    return rows


def pagination_links(html: str, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    result: list[str] = []
    for anchor in soup.select("a[href]"):
        label = text(anchor).lower()
        url = urljoin(page_url, anchor["href"])
        if ("page=" in url and url not in result) or label in {"next", "next page", ">"}:
            result.append(url)
    return result


def safe_name(value: str, limit: int = 100) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return value[:limit] or "order"
