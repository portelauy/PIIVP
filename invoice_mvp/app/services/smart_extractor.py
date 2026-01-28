"""Smart extractor factory with adaptive strategy selection."""

from __future__ import annotations

import os
from typing import Optional

from .extractors.base import InvoiceExtractor, ExtractionMetrics
from .extractors.llama_extractor import LlamaInvoiceExtractor
from .extractors.openai_extractor import OpenAIInvoiceExtractor
from .extractors.ocr_extractor import OCRInvoiceExtractor


class SmartExtractorFactory:
    """Factory for creating invoice extractors with adaptive strategy selection."""

    @staticmethod
    def create_extractor(
        provider: Optional[str] = None,
        auto_detect: bool = True
    ) -> InvoiceExtractor:
        """Create an extractor instance.
        
        Args:
            provider: Specific provider to use ('llama', 'openai', 'ocr', 'mock')
            auto_detect: If True, auto-detect best provider based on environment
            
        Returns:
            Configured extractor instance
        """
        if provider:
            return SmartExtractorFactory._create_specific(provider)
        
        if auto_detect:
            return SmartExtractorFactory._auto_detect()
        
        # Default to Llama if available
        return SmartExtractorFactory._create_specific("llama")

    @staticmethod
    def _create_specific(provider: str) -> InvoiceExtractor:
        """Create a specific extractor by name."""
        providers = {
            "llama": LlamaInvoiceExtractor,
            "openai": OpenAIInvoiceExtractor,
            "ocr": OCRInvoiceExtractor,
            "mock": MockInvoiceExtractor,
        }
        
        if provider not in providers:
            raise ValueError(f"Unknown provider: {provider}. Available: {list(providers.keys())}")
        
        return providers[provider]()

    @staticmethod
    def _auto_detect() -> InvoiceExtractor:
        """Auto-detect the best available provider."""
        # Check for Llama Cloud
        if os.getenv("LLAMA_API_KEY"):
            return LlamaInvoiceExtractor()
        
        # Check for OpenAI
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIInvoiceExtractor()
        
        # Fallback to OCR-only
        return OCRInvoiceExtractor()

    @staticmethod
    def get_available_providers() -> list[str]:
        """Get list of available providers based on environment."""
        available = []
        
        if os.getenv("LLAMA_API_KEY"):
            available.append("llama")
        
        if os.getenv("OPENAI_API_KEY"):
            available.append("openai")
        
        # OCR and Mock are always available
        available.extend(["ocr", "mock"])
        
        return available

    @staticmethod
    def get_recommended_provider() -> str:
        """Get the recommended provider for current environment."""
        available = SmartExtractorFactory.get_available_providers()
        
        # Priority order: Llama > OpenAI > OCR > Mock
        for provider in ["llama", "openai", "ocr", "mock"]:
            if provider in available:
                return provider
        
        return "ocr"  # Ultimate fallback


# Import mock extractor for testing
try:
    from tests.mocks import MockInvoiceExtractor
except ImportError:
    # Create a simple mock if tests module not available
    class MockInvoiceExtractor(InvoiceExtractor):
        def get_provider_name(self) -> str:
            return "mock"
        
        async def extract(self, file_bytes: bytes, filename: str, ocr_text: Optional[str] = None) -> dict:
            return {"provider": {"name": "Mock Provider"}}


class SmartInvoiceExtractor:
    """High-level extractor with fallback and metrics."""

    def __init__(self, primary_provider: Optional[str] = None):
        self.primary = SmartExtractorFactory.create_extractor(primary_provider)
        self.fallback = SmartExtractorFactory._create_specific("ocr")  # Always have OCR fallback

    async def extract_with_fallback(
        self,
        file_bytes: bytes,
        filename: str,
        ocr_text: Optional[str] = None
    ) -> tuple[dict, ExtractionMetrics]:
        """Extract with automatic fallback on failure."""
        try:
            # Try primary extractor
            return await self.primary.extract_with_metrics(file_bytes, filename, ocr_text)
        except Exception as e:
            print(f"[SmartExtractor] Primary extractor failed: {e}. Trying fallback...")
            
            # Try fallback extractor
            try:
                return await self.fallback.extract_with_metrics(file_bytes, filename, ocr_text)
            except Exception as fallback_error:
                # Both failed
                metrics = ExtractionMetrics(
                    provider="smart_extractor",
                    processing_time=0.0,
                    success=False,
                    error_message=f"Primary: {str(e)}. Fallback: {str(fallback_error)}"
                )
                raise RuntimeError(f"All extractors failed: {metrics.error_message}")

    def get_primary_provider_name(self) -> str:
        """Get the name of the primary provider."""
        return self.primary.get_provider_name()
