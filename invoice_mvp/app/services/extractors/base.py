"""Base interface for all invoice extractors."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from time import time


@dataclass
class ExtractionMetrics:
    """Metrics for extraction performance."""
    provider: str
    processing_time: float
    success: bool
    confidence: Optional[Dict[str, float]] = None
    error_message: Optional[str] = None


class InvoiceExtractor(ABC):
    """Abstract base class for all invoice extraction providers."""

    @abstractmethod
    async def extract(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured invoice data from file.
        
        Args:
            file_bytes: Raw file bytes (PDF/image)
            filename: Original filename
            ocr_text: Pre-extracted OCR text (optional, for providers that need it)
            
        Returns:
            Structured extraction result as dict
        """
        pass

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the provider name for metrics."""
        pass

    async def extract_with_metrics(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> tuple[Dict[str, Any], ExtractionMetrics]:
        """Extract data and return metrics."""
        start_time = time()
        provider_name = self.get_provider_name()
        
        try:
            result = await self.extract(file_bytes, filename, ocr_text)
            processing_time = time() - start_time
            
            metrics = ExtractionMetrics(
                provider=provider_name,
                processing_time=processing_time,
                success=True,
                confidence=self._extract_confidence(result)
            )
            return result, metrics
            
        except Exception as e:
            processing_time = time() - start_time
            
            metrics = ExtractionMetrics(
                provider=provider_name,
                processing_time=processing_time,
                success=False,
                error_message=str(e)
            )
            raise e

    def _extract_confidence(self, result: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract confidence scores from result if available."""
        # Override in subclasses that provide confidence
        return None
