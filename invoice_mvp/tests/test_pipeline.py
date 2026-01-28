from __future__ import annotations

import pytest

from app.core import ProcessedInvoice
from app.services.orchestrator import InvoiceProcessor
from app.services.rubro_normalizer import RubroNormalizerService
from tests.mocks import MockOCRClient, MockInvoiceExtractor


@pytest.mark.asyncio
async def test_invoice_processor_with_mocks() -> None:
    ocr = MockOCRClient()
    extractor = MockInvoiceExtractor()
    normalizer = RubroNormalizerService(nomenclator=None)

    # Create processor with mock extractor
    processor = InvoiceProcessor(
        ocr_client=ocr, 
        extractor_provider="mock",  # This will use our mock extractor
        rubro_normalizer=normalizer
    )

    processed = await processor.process_invoice_file(b"dummy", "dummy.pdf")

    assert isinstance(processed, ProcessedInvoice)
    assert processed.invoice.provider.name == "Proveedor Demo"
    assert processed.validation.is_valid is True
    assert processed.validation.issues == []


@pytest.mark.asyncio
async def test_smart_extractor_factory() -> None:
    """Test that SmartExtractorFactory can create mock extractor."""
    from app.services.smart_extractor import SmartExtractorFactory
    
    extractor = SmartExtractorFactory.create_extractor("mock")
    assert extractor.get_provider_name() == "mock"
    
    # Test extraction
    result = await extractor.extract(b"dummy", "dummy.pdf")
    assert "provider" in result
    assert result["provider"]["name"] == "Proveedor Demo"

