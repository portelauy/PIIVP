"""Mock implementations for testing."""

from __future__ import annotations

from typing import Dict, Any

from app.services.extractors.base import InvoiceExtractor, ExtractionMetrics


class MockInvoiceExtractor(InvoiceExtractor):
    """Mock invoice extractor for testing."""

    def get_provider_name(self) -> str:
        return "mock"

    async def extract(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Return mock invoice data for testing."""
        return {
            "provider": {
                "name": "Proveedor Demo",
                "rut": "12.345.678-9",
                "address": "Calle Demo 123",
            },
            "buyer": {
                "name": "Cliente Demo",
                "rut": "98.765.432-1",
                "address": "Avenida Cliente 456",
                "type": "C.FINAL",
            },
            "line_items": [
                {
                    "rubro_raw": "Servicio de consultoría",
                    "quantity": 10,
                    "unit_price": 100.0,
                    "subtotal": 1000.0,
                }
            ],
            "totals": {
                "subtotal": 1000.0,
                "iva": 190.0,
                "iva_rate": 0.19,
                "total": 1190.0,
            },
        }

    def _extract_confidence(self, result: Dict[str, Any]) -> Optional[Dict[str, float]]:
        return {"overall": 1.0}  # Perfect confidence for mock


class MockOCRClient:
    """Mock OCR client for testing."""

    async def extract_text(self, file_bytes: bytes, filename: str) -> str:
        """Return mock OCR text for testing."""
        return """
        FACTURA A
        Proveedor Demo
        RUT: 12.345.678-9
        
        Servicio de consultoría    10    $100.00
        Subtotal: $1000.00
        IVA: $190.00
        Total: $1190.00
        """
