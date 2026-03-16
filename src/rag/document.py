"""RAG document model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Document:
    """A text document with optional metadata used in the RAG pipeline."""

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("Document content must not be empty.")

    def __repr__(self) -> str:  # pragma: no cover
        preview = self.content[:80].replace("\n", " ")
        return f"Document(content='{preview}...', metadata={self.metadata})"
