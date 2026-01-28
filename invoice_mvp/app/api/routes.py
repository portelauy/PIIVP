from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import HTMLResponse

from ..core import ProcessedInvoice
from ..services.ocr_client import OCRClient
from ..services.tesseract_ocr_client import TesseractOCRClient
from ..services.orchestrator import InvoiceProcessor
from ..services.rubro_normalizer import RubroNormalizerService
from ..services.smart_extractor import SmartExtractorFactory
from ..services.metrics import metrics_collector
from tests.mocks import MockOCRClient

router = APIRouter()


async def get_ocr_client() -> OCRClient:
    # Single-line switch between mock and Tesseract-backed implementation.
    try:
        # return MockOCRClient()
        return TesseractOCRClient()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"OCR client init failed: {exc}") from exc


async def get_invoice_processor(
    ocr_client: OCRClient = Depends(get_ocr_client),
    provider: Optional[str] = Query(None, description="Extraction provider: llama, openai, ocr"),
) -> InvoiceProcessor:
    # Create processor with smart extractor
    rubro_normalizer = RubroNormalizerService(nomenclator=None)
    
    return InvoiceProcessor(
        ocr_client=ocr_client,
        extractor_provider=provider,
        rubro_normalizer=rubro_normalizer
    )


@router.post("/invoices/process", response_model=ProcessedInvoice)
async def process_invoice(
    file: UploadFile = File(...),
    processor: InvoiceProcessor = Depends(get_invoice_processor),
) -> ProcessedInvoice:
    contents = await file.read()
    try:
        result = await processor.process_invoice_file(contents, file.filename)
    except Exception as exc:  # noqa: BLE001 - expose error detail for debugging/demo
        # Surface the underlying error message so the demo UI and API clients
        # can see what went wrong. In a hardened production API this mapping
        # would likely be more restrictive.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@router.get("/providers")
async def get_providers():
    """Get available extraction providers."""
    return {
        "available": SmartExtractorFactory.get_available_providers(),
        "recommended": SmartExtractorFactory.get_recommended_provider(),
    }


@router.get("/metrics")
async def get_metrics():
    """Get extraction metrics and statistics."""
    return {
        "provider_stats": metrics_collector.get_provider_stats(),
        "recent_extractions": metrics_collector.get_recent_extractions(),
    }


@router.get("/", response_class=HTMLResponse)
async def ui_index() -> HTMLResponse:
    """Serve the minimal HTML demo UI.

    Architectural note: this is an optional, thin UI layer for manual testing
    and demo purposes. The core API remains fully usable without it.
    """

    ui_path = Path(__file__).resolve().parent.parent / "ui" / "index.html"
    if not ui_path.exists():
        return HTMLResponse("<h1>UI not found</h1>", status_code=404)

    return HTMLResponse(ui_path.read_text(encoding="utf-8"))

