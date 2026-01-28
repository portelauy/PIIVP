"""OpenAI extractor implementation."""

from __future__ import annotations

import json
import os
from typing import Dict, Any, Optional

from openai import AsyncOpenAI

from .base import InvoiceExtractor, ExtractionMetrics


class OpenAIInvoiceExtractor(InvoiceExtractor):
    """OpenAI-based invoice extraction implementation."""

    def __init__(self, model: str = "gpt-4o-mini") -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    def get_provider_name(self) -> str:
        return "openai"

    async def extract(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured invoice data using OpenAI."""
        if not ocr_text:
            raise ValueError("OpenAI extractor requires OCR text")

        system_prompt = (
            "You are an assistant that extracts structured invoice data from OCR text. "
            "Return ONLY valid JSON matching the specified schema, with no extra text. "
            "If a value is missing or uncertain, use null for that field."
        )

        user_prompt = (
            "Extract the following fields from the provided OCR text of an invoice.\n\n"
            "Return ONLY a JSON object with this exact schema (no markdown, no comments):\n\n"
            "{\n"
            "  \"provider\": { \"name\": string | null, \"rut\": string | null },\n"
            "  \"line_items\": [\n"
            "    {\n"
            "      \"rubro_raw\": string | null,\n"
            "      \"quantity\": number | null,\n"
            "      \"unit_price\": number | null,\n"
            "      \"subtotal\": number | null\n"
            "    }\n"
            "  ],\n"
            "  \"totals\": {\n"
            "    \"subtotal\": number | null,\n"
            "    \"iva_rate\": number | null,\n"
            "    \"iva\": number | null,\n"
            "    \"total\": number | null\n"
            "  }\n"
            "}\n\n"
            "OCR text:\n" + ocr_text
        )

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.1,
            )
        except Exception as exc:
            raise RuntimeError(f"OpenAI API call failed: {exc}") from exc

        try:
            content = response.choices[0].message.content or ""
        except (AttributeError, IndexError) as exc:
            raise RuntimeError("Unexpected OpenAI API response format") from exc

        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI response was not valid JSON") from exc

        if not isinstance(data, dict):
            raise RuntimeError("OpenAI response JSON is not an object")

        # Normalize with defaults
        provider = data.get("provider") or {}
        line_items = data.get("line_items") or []
        totals = data.get("totals") or {}

        normalized = {
            "provider": {
                "name": provider.get("name", ""),
                "rut": provider.get("rut", ""),
                "address": provider.get("address", ""),
            },
            "line_items": line_items,
            "totals": {
                "subtotal": float(totals.get("subtotal", 0)),
                "iva": float(totals.get("iva", 0)),
                "iva_rate": float(totals.get("iva_rate", 0)),
                "total": float(totals.get("total", 0)),
            },
        }

        return normalized

    def _extract_confidence(self, result: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract confidence from OpenAI response."""
        # OpenAI doesn't provide confidence scores, but we can estimate based on completeness
        confidence = 0.7  # Base confidence
        
        provider = result.get("provider", {})
        if provider.get("name") and provider.get("rut"):
            confidence += 0.1
            
        totals = result.get("totals", {})
        if totals.get("total") and totals.get("subtotal"):
            confidence += 0.1
            
        if result.get("line_items"):
            confidence += 0.1
            
        return {"overall": min(confidence, 1.0)}
