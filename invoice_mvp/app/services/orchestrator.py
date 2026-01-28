from __future__ import annotations

from typing import Optional

from ..core import (
    Invoice,
    InvoiceLineItemWithTotals,
    InvoiceParty,
    InvoiceTotals,
    ProcessedInvoice,
    InvoiceExtraction,
)
from .ocr_client import OCRClient
from .rubro_normalizer import RubroNormalizerService
from .validator import validate_invoice_numeric_consistency
from .smart_extractor import SmartExtractorFactory
from .metrics import metrics_collector


class InvoiceProcessor:
    """High-level orchestrator that wires OCR, Smart Extractor and validation.

    Architectural decision: this class is the main entrypoint for the domain
    logic, shielding the FastAPI layer from AI/OCR specifics.
    """

    def __init__(
        self,
        ocr_client: OCRClient,
        extractor_provider: Optional[str] = None,
        rubro_normalizer: Optional[RubroNormalizerService] = None,
    ) -> None:
        self._ocr = ocr_client
        self._smart_extractor = SmartExtractorFactory.create_extractor(extractor_provider)
        self._rubro_normalizer = rubro_normalizer

    async def process_invoice_file(self, file_bytes: bytes, filename: str) -> ProcessedInvoice:
        # Step 1: OCR
        ocr_text = await self._ocr.extract_text(file_bytes, filename)

        # Step 2: Smart extraction with metrics
        llm_result, extraction_metrics = await self._smart_extractor.extract_with_metrics(
            file_bytes, filename, ocr_text
        )
        # Record metrics
        metrics_collector.record_extraction(extraction_metrics, filename)

        # Step 3: Map into domain model
        invoice = self._map_to_invoice(llm_result)

        # Step 4: Optional rubro normalization
        if self._rubro_normalizer is not None:
            normalization_results = self._rubro_normalizer.normalize_lines(
                [li.rubro_raw for li in invoice.line_items]
            )
            for res in normalization_results:
                if res.normalized_code:
                    invoice.line_items[res.line_index].rubro_code = res.normalized_code

        # Step 5: Validation
        validation = validate_invoice_numeric_consistency(invoice)

        return ProcessedInvoice(invoice=invoice, validation=validation)

    def _map_to_invoice(self, data: dict) -> Invoice:
        # Si viene en formato Llama Cloud, extraer de 'data' y usar InvoiceExtraction para validarlo
        if "data" in data and "seller" in data["data"] and "buyer" in data["data"]:
            extraction_data = data["data"]
            extraction = InvoiceExtraction(**extraction_data)
            
            # Mapear de Llama al dominio existente
            provider = InvoiceParty(
                name=extraction.seller.name or "",
                rut=extraction.seller.rut or "",
                address=extraction.seller.address or ""
            )
            
            buyer = InvoiceParty(
                name=extraction.buyer.name or "",
                rut=extraction.buyer.rut or "",
                address=extraction.buyer.address or ""
            )
            
            line_items = [
                InvoiceLineItemWithTotals(
                    rubro_raw=item.description or "",
                    rubro_code=None,
                    quantity=float(item.quantity or 0),
                    unit_price=0.0,  # Llama no da unit_price, se calculará después si es necesario
                    subtotal=0.0,   # Se calculará después si es necesario
                )
                for item in extraction.line_items
            ]
            
            totals = InvoiceTotals(
                subtotal=float(extraction.financial_summary.sub_total or 0),
                iva=float(extraction.financial_summary.iva_amount or 0),
                iva_rate=0.0,  # Llama no da tasa, se puede calcular si es necesario
                total=float(extraction.financial_summary.total_amount or 0),
            )
            
            return Invoice(provider=provider, buyer=buyer, line_items=line_items, totals=totals)
        
        # Si viene en formato antiguo (OpenAI/Mock), mapear como antes
        provider_data = data.get("provider", {})
        totals_data = data.get("totals", {})
        line_items_data = data.get("line_items", [])

        # Asegurar que todos los campos requeridos estén presentes
        provider = InvoiceParty(
            name=provider_data.get("name", ""),
            rut=provider_data.get("rut", ""),
            address=provider_data.get("address", "")
        )
        
        totals = InvoiceTotals(
            subtotal=float(totals_data.get("subtotal", 0)),
            iva=float(totals_data.get("iva", 0)),
            iva_rate=float(totals_data.get("iva_rate", 0)),
            total=float(totals_data.get("total", 0)),
        )
        
        line_items = [InvoiceLineItemWithTotals(**li) for li in line_items_data]

        return Invoice(provider=provider, buyer=InvoiceParty(), line_items=line_items, totals=totals)

