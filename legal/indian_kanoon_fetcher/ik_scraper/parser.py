from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from .models import CatalogueItem, Document

BASE_URL = "https://indiankanoon.org"
_DOC_RE = re.compile(r"/(?:doc|docfragment)/(\d+)/?")

STRUCTURE_LABELS = {
    "facts": "fact",
    "fact": "fact",
    "issue": "issue",
    "issues": "issue",
    "petarg": "appellant_argument",
    "petitionerarg": "appellant_argument",
    "appellantarg": "appellant_argument",
    "resparg": "respondent_argument",
    "respondentarg": "respondent_argument",
    "precedent": "precedent_analysis",
    "precedentanalysis": "precedent_analysis",
    "section": "law_analysis",
    "analysisoflaw": "law_analysis",
    "cdiscource": "court_reasoning",
    "courtdiscourse": "court_reasoning",
    "courtreasoning": "court_reasoning",
    "conclusion": "conclusion",
}


def clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    result: list[str] = []
    for line in lines:
        if line and (not result or result[-1] != line):
            result.append(line)
    return "\n".join(result).strip()


def _absolute(href: str, base_url: str) -> str:
    return urljoin(base_url, href.split("#", 1)[0])


def _document_id(url: str) -> str | None:
    match = _DOC_RE.search(urlparse(url).path)
    return match.group(1) if match else None


def catalogue_search_url(url: str) -> str | None:
    """Translate a catalogue year URL into its result-page URL.

    Indian Kanoon catalogue pages such as ``/browse/bengalpresidency-act/1943/``
    show the count, but the document links are served by the equivalent search
    page: ``doctypes:bengalpresidency-act year:1943``.
    """
    parts = [part for part in urlparse(url).path.split("/") if part]
    if len(parts) < 3 or parts[0] != "browse":
        return None
    year = parts[-1]
    if not re.fullmatch(r"\d{4}", year):
        return None
    doctype = parts[1]
    query = quote_plus(f"doctypes:{doctype} year:{year}")
    return f"{BASE_URL}/search/?formInput={query}"


def parse_catalogue(html: str, base_url: str = BASE_URL) -> list[CatalogueItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[CatalogueItem] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        url = _absolute(anchor.get("href", ""), base_url)
        label = clean_text(anchor.get_text(" ", strip=True))
        if not label or not url.startswith(BASE_URL) or url in seen:
            continue
        path = urlparse(url).path
        if path in {"/", "/browse/", "/browselaws/"} or path.startswith("/search"):
            continue
        if not (path.startswith("/browse") or path.startswith("/law") or _document_id(url)):
            continue
        count = _find_count(anchor)
        display_label = _strip_count(label)
        kind = "document" if _document_id(url) else "category"
        seen.add(url)
        items.append(CatalogueItem(len(items) + 1, display_label, url, kind, count))
    return items


def _strip_count(label: str) -> str:
    # A bare numeric label is commonly a year (for example, "2026") and
    # must remain a valid catalogue name. Only remove numbers that are
    # visibly presented as counts.
    if not re.search(r"(?:documents?|cases?|judgments?|laws?)|\([\d,]+\)", label, re.I):
        return label
    return re.sub(r"\s*(?:\(|-)?\s*[\d,]+\s*(?:documents?|cases?|judgments?|laws?)?\s*\)?\s*$", "", label, flags=re.I).strip()


def _find_count(anchor) -> int | None:
    text = clean_text(anchor.parent.get_text(" ", strip=True)) if anchor.parent else ""
    match = re.search(r"(?:documents?|cases?|judgments?|laws?)\D*([\d,]+)", text, re.I)
    if not match:
        match = re.search(r"([\d,]+)\D*(?:documents?|cases?|judgments?|laws?)", text, re.I)
    if not match:
        match = re.search(r"\(([\d,]+)\)", text)
    return int(match.group(1).replace(",", "")) if match else None


def pagination_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.select("a[href]"):
        label = clean_text(anchor.get_text(" ", strip=True)).lower()
        url = _absolute(anchor["href"], base_url)
        if label in {"next", ">", "next page"} or "page=" in url or "pagenum=" in url:
            if url not in links:
                links.append(url)
    return links


def document_links(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for anchor in soup.select("a[href]"):
        url = _absolute(anchor["href"], base_url)
        if _document_id(url) and url not in links:
            links.append(url)
    return links


def search_result_documents(html: str, base_url: str) -> list[dict[str, str]]:
    """Extract document links and visible result titles from a search page."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.select("a[href]"):
        url = _absolute(anchor["href"], base_url)
        doc_id = _document_id(url)
        if not doc_id or url in seen:
            continue
        title = clean_text(anchor.get_text(" ", strip=True))
        if not title or title.lower() in {"full document", "cites", "cited by"}:
            title = doc_id
        seen.add(url)
        results.append({"document_id": doc_id, "title": title, "url": url})
    return results


def parse_classification(html: str) -> list[tuple[str, str]]:
    """Read Indian Kanoon's own paragraph-level structural labels."""
    soup = BeautifulSoup(html, "html.parser")
    segments: list[tuple[str, str]] = []
    for node in soup.select("[data-structure]"):
        raw_label = clean_text(node.get("data-structure", ""))
        label = STRUCTURE_LABELS.get(re.sub(r"[^a-z0-9]", "", raw_label.lower()))
        if not label:
            continue
        for hidden in node.select(".hidden_text"):
            hidden.decompose()
        text = " ".join(clean_text(node.get_text(" ", strip=True)).splitlines())
        if text:
            segments.append((label, text))
    return segments


def parse_document(html: str, url: str) -> Document:
    soup = BeautifulSoup(html, "html.parser")
    doc_id = _document_id(url) or "unknown"
    for tag in soup.select("script, style, nav, header, footer, form, aside"):
        tag.decompose()
    title_node = soup.select_one("h1, .doc_title, title")
    title = clean_text(title_node.get_text(" ", strip=True)) if title_node else doc_id
    content = soup.select_one(".judgments, .doc_content, #content, main") or soup.body or soup
    text = clean_text(content.get_text("\n", strip=True))
    return Document(doc_id, title, url, text, {"document_type": "document"})
