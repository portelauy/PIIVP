"""OCR-only extractor implementation."""

from __future__ import annotations

import re
from typing import Dict, Any, Optional

from .base import InvoiceExtractor, ExtractionMetrics


class OCRInvoiceExtractor(InvoiceExtractor):
    """OCR-only extraction implementation (Tesseract output processing)."""

    def __init__(self) -> None:
        pass

    def get_provider_name(self) -> str:
        return "tesseract_ocr"

    async def extract(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract basic invoice data from OCR text using regex patterns."""
        if not ocr_text:
            raise ValueError("OCR extractor requires OCR text")

        # Clean and normalize OCR text
        text = ocr_text.strip()
        
        # Extract provider information
        provider_name = self._extract_provider_name(text)
        provider_rut = self._extract_rut(text)
        
        # Extract totals
        totals = self._extract_totals(text)
        
        # Extract line items (basic)
        line_items = self._extract_line_items(text)

        return {
            "provider": {
                "name": provider_name,
                "rut": provider_rut,
                "address": "",
            },
            "line_items": line_items,
            "totals": totals,
        }

    def _extract_provider_name(self, text: str) -> str:
        """Extract provider name using common patterns."""
        lines = text.split('\n')
        for line in lines[:5]:  # Usually in first few lines
            line = line.strip()
            # Skip common headers
            if any(word in line.upper() for word in ['FACTURA', 'INVOICE', 'RUT:', 'TOTAL']):
                continue
            # Look for name-like patterns (multiple words, proper case)
            if len(line.split()) >= 2 and len(line) > 10:
                return line
        return ""

    def _extract_rut(self, text: str) -> str:
        """Extract RUT using Chilean/Uruguayan format patterns."""
        # Pattern: XX.XXX.XXX-X or XXXXXXXX-X
        rut_patterns = [
            r'\b\d{1,2}\.\d{3}\.\d{3}-[0-9Kk]\b',
            r'\b\d{7,8}-[0-9Kk]\b',
        ]
        
        for pattern in rut_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group()
        return ""

    def _extract_totals(self, text: str) -> Dict[str, Any]:
        """Extract financial totals."""
        totals = {
            "subtotal": 0.0,
            "iva": 0.0,
            "iva_rate": 0.0,
            "total": 0.0,
        }
        
        # Look for total amount
        total_patterns = [
            r'TOTAL[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
            r'TOTAL GENERAL[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
            r'IMPORTE TOTAL[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                totals["total"] = float(match.group(1))
                break
        
        # Look for subtotal
        subtotal_patterns = [
            r'SUBTOTAL[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
            r'BASE IMPONIBLE[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in subtotal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                totals["subtotal"] = float(match.group(1))
                break
        
        # Look for IVA/IVA amount
        iva_patterns = [
            r'IVA[:\s]*\$?[\s]*(\d+(?:\.\d+)?)',
            r'IVA[\s]*(\d+(?:\.\d+)?)',
            r'IVA[\s]*\$?[\s]*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in iva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                totals["iva"] = float(match.group(1))
                break
        
        # Calculate IVA rate if we have both subtotal and IVA
        if totals["subtotal"] > 0 and totals["iva"] > 0:
            totals["iva_rate"] = round(totals["iva"] / totals["subtotal"], 4)
        
        return totals

    def _extract_line_items(self, text: str) -> list:
        """Extract basic line items."""
        items = []
        lines = text.split('\n')
        
        # Simple pattern: look for lines with quantities and descriptions
        for i, line in enumerate(lines):
            line = line.strip()
            # Skip headers and footers
            if any(word in line.upper() for word in ['DESCRIPCIÓN', 'CANTIDAD', 'PRECIO', 'TOTAL', 'IVA']):
                continue
            
            # Look for patterns like "2 Servicio $1000" or "1x Item"
            item_match = re.search(r'(\d+)\s+[xX\s]*(.+)', line)
            if item_match:
                quantity = int(item_match.group(1))
                description = item_match.group(2).strip()
                
                # Try to extract price from description or next line
                price = 0.0
                price_match = re.search(r'\$?(\d+(?:\.\d+)?)', description)
                if price_match:
                    price = float(price_match.group(1))
                elif i + 1 < len(lines):
                    next_price_match = re.search(r'\$?(\d+(?:\.\d+)?)', lines[i + 1])
                    if next_price_match:
                        price = float(next_price_match.group(1))
                
                items.append({
                    "rubro_raw": description,
                    "quantity": quantity,
                    "unit_price": price,
                    "subtotal": quantity * price,
                })
        
        return items

    def _extract_confidence(self, result: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract confidence based on pattern matching success."""
        confidence = 0.5  # Base confidence for OCR-only
        
        if result["provider"]["name"]:
            confidence += 0.1
        if result["provider"]["rut"]:
            confidence += 0.1
        if result["totals"]["total"] > 0:
            confidence += 0.2
        if result["line_items"]:
            confidence += 0.1
            
        return {"overall": min(confidence, 1.0)}
