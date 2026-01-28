from __future__ import annotations

import io
import os
from typing import List

from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract

from .ocr_client import OCRClient


class TesseractOCRClient(OCRClient):
    """OCRClient implementation backed by Tesseract.

    This class is purely infrastructure: it translates files (PDF/images)
    into plain text for the rest of the pipeline. It performs no business
    validation and exposes the same async interface as OCRClient while
    internally using synchronous libraries.
    """

    def __init__(self, tesseract_cmd: str | None = None) -> None:
        # Optional explicit Tesseract binary path; if not provided, rely on PATH.
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    async def extract_text(self, file_bytes: bytes, filename: str) -> str:  # type: ignore[override]
        try:
            ext = os.path.splitext(filename)[1].lower()
        except Exception:
            ext = ""

        if ext in {".png", ".jpg", ".jpeg"}:
            return self._extract_from_image_bytes(file_bytes)
        if ext == ".pdf":
            return self._extract_from_pdf_bytes(file_bytes)

        raise RuntimeError(f"Unsupported file format for OCR: '{ext or 'unknown'}'")

    def _extract_from_image_bytes(self, file_bytes: bytes) -> str:
        try:
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to open image for OCR: {exc}") from exc

        return self._run_tesseract(image)

    def _extract_from_pdf_bytes(self, file_bytes: bytes) -> str:
        try:
            # Convert all pages in the PDF to images.
            pages: List[Image.Image] = convert_from_bytes(file_bytes)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to convert PDF to images for OCR: {exc}") from exc

        if not pages:
            raise RuntimeError("PDF appears to have no pages")

        texts: List[str] = []
        for page in pages:
            texts.append(self._run_tesseract(page))

        # Preserve page boundaries as blank lines between pages to help LLM.
        combined = "\n\n".join(texts)
        return self._normalize_ocr_output(combined)

    def _run_tesseract(self, image: Image.Image) -> str:
        try:
            raw_text = pytesseract.image_to_string(image)
        except pytesseract.TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract executable not found. Make sure it is installed and available in PATH "
                "or configure tesseract_cmd explicitly."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Tesseract OCR failed: {exc}") from exc

        return self._normalize_ocr_output(raw_text)

    def _normalize_ocr_output(self, text: str) -> str:
        # Normalize whitespace while preserving line breaks.
        normalized_lines: List[str] = []
        for line in text.splitlines():
            stripped = " ".join(line.split())  # collapse internal whitespace
            if stripped:
                normalized_lines.append(stripped)
        return "\n".join(normalized_lines)
