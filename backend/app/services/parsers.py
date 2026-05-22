"""Document parsers for multiple file formats.

Each parser implements :class:`DocumentParser.parse` returning plain text. The
:class:`ParserRegistry` selects the right parser by MIME type or extension.
"""

from __future__ import annotations

import io
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.exceptions import IngestionError
from app.utils.text import clean_text


class DocumentParser(ABC):
    """Abstract parser. One concrete subclass per supported format."""

    content_types: tuple[str, ...] = ()
    extensions: tuple[str, ...] = ()

    @abstractmethod
    def parse(self, data: bytes) -> str:
        """Parse raw bytes and return plain text."""


class TextParser(DocumentParser):
    """UTF-8 plain-text parser."""

    content_types = ("text/plain",)
    extensions = (".txt",)

    def parse(self, data: bytes) -> str:
        return clean_text(data.decode("utf-8", errors="replace"))


class MarkdownParser(DocumentParser):
    """Markdown parser — strips fences and HTML, keeps body text."""

    content_types = ("text/markdown",)
    extensions = (".md", ".markdown")

    def parse(self, data: bytes) -> str:
        import markdown
        from bs4 import BeautifulSoup

        raw = data.decode("utf-8", errors="replace")
        html = markdown.markdown(raw, extensions=["fenced_code", "tables"])
        text = BeautifulSoup(html, "html.parser").get_text(separator="\n")
        return clean_text(text)


class HTMLParser(DocumentParser):
    """HTML parser — extracts visible text and drops scripts/styles."""

    content_types = ("text/html",)
    extensions = (".html", ".htm")

    def parse(self, data: bytes) -> str:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(data.decode("utf-8", errors="replace"), "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return clean_text(soup.get_text(separator="\n"))


class PDFParser(DocumentParser):
    """PDF parser using pypdf."""

    content_types = ("application/pdf",)
    extensions = (".pdf",)

    def parse(self, data: bytes) -> str:
        from pypdf import PdfReader

        try:
            reader = PdfReader(io.BytesIO(data))
            pages = [p.extract_text() or "" for p in reader.pages]
            return clean_text("\n\n".join(pages))
        except Exception as exc:
            raise IngestionError("Failed to read PDF.", details={"reason": str(exc)}) from exc


class DocxParser(DocumentParser):
    """DOCX parser using python-docx."""

    content_types = (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    extensions = (".docx",)

    def parse(self, data: bytes) -> str:
        from docx import Document as DocxDocument

        try:
            doc = DocxDocument(io.BytesIO(data))
            paragraphs = [p.text for p in doc.paragraphs if p.text]
            return clean_text("\n".join(paragraphs))
        except Exception as exc:
            raise IngestionError("Failed to read DOCX.", details={"reason": str(exc)}) from exc


class ParserRegistry:
    """Resolve the right :class:`DocumentParser` for an input."""

    def __init__(self) -> None:
        self._parsers: list[DocumentParser] = [
            TextParser(),
            MarkdownParser(),
            HTMLParser(),
            PDFParser(),
            DocxParser(),
        ]

    def by_content_type(self, content_type: str) -> DocumentParser | None:
        ct = content_type.lower().split(";")[0].strip()
        for p in self._parsers:
            if ct in p.content_types:
                return p
        return None

    def by_filename(self, filename: str) -> DocumentParser | None:
        ext = Path(filename).suffix.lower()
        for p in self._parsers:
            if ext in p.extensions:
                return p
        return None

    def resolve(self, *, filename: str | None, content_type: str | None) -> DocumentParser:
        """Choose a parser by content-type first, then by extension."""
        if content_type:
            parser = self.by_content_type(content_type)
            if parser:
                return parser
        if filename:
            parser = self.by_filename(filename)
            if parser:
                return parser
        raise IngestionError(
            "Unsupported file type.",
            details={"filename": filename, "content_type": content_type},
        )
