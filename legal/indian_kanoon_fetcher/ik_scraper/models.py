from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class CatalogueItem:
    number: int
    name: str
    url: str
    kind: str = "category"
    count: int | None = None


@dataclass
class Document:
    document_id: str
    title: str
    url: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_metadata(self, text_file: str) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "title": self.title,
            "source_url": self.url,
            "text_file": text_file,
            **self.metadata,
        }
