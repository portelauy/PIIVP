from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol


class OCRClient(ABC):
    """Abstract OCR interface (can be backed by local Tesseract or cloud OCR).

    Architectural decision: the rest of the system only sees plain text, never
    vendor-specific OCR APIs.
    """

    @abstractmethod
    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """Extract raw text from a document (PDF or image)."""


class MockOCRClient(OCRClient):
    """Mock OCR that ignores the file and returns a canned text snippet."""

    async def extract_text(self, file_bytes: bytes, filename: str) -> str:  # type: ignore[override]
        return "Proveedor Demo RUT 12.345.678-9 Servicio de consultoría 10 x 100 = 1000 IVA 19% Total 1190"
