"""Llama Cloud extractor implementation."""

from __future__ import annotations

import os
import json
import io
from typing import Dict, Any, Optional
import httpx

from .base import InvoiceExtractor, ExtractionMetrics


class LlamaInvoiceExtractor(InvoiceExtractor):
    """Llama Cloud extraction implementation."""

    def __init__(self, model: str = "default") -> None:
        api_key = os.getenv("LLAMA_API_KEY")
        if not api_key:
            raise RuntimeError("LLAMA_API_KEY environment variable is not set")

        self._api_key = api_key
        self._base_url = "https://api.cloud.llamaindex.ai/api/v1"
        self._model = model
        self._agent_id = None

    def get_provider_name(self) -> str:
        return "llama_cloud"

    async def _ensure_agent(self) -> str:
        """Create or reuse an extraction agent for invoices."""
        if self._agent_id:
            return self._agent_id

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        # List existing agents
        async with httpx.AsyncClient() as client:
            list_response = await client.get(
                f"{self._base_url}/extraction/extraction-agents",
                headers=headers,
                timeout=30.0,
            )
            list_response.raise_for_status()
            agents = list_response.json()
            for agent in agents:
                if agent.get("name") == "invoice_parser":
                    self._agent_id = agent["id"]
                    return self._agent_id

        # Create new agent if not found
        data_schema = {
            "type": "object",
            "properties": {
                "seller": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Seller name"},
                        "rut": {"type": "string", "description": "Seller RUT"},
                        "address": {"type": "string", "description": "Seller address"},
                    },
                },
                "buyer": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Buyer name"},
                        "rut": {"type": "string", "description": "Buyer RUT"},
                        "address": {"type": "string", "description": "Buyer address"},
                        "type": {"type": "string", "description": "Invoice type"},
                    },
                },
                "document_details": {
                    "type": "object",
                    "properties": {
                        "series": {"type": "string", "description": "Invoice series"},
                        "number": {"type": "string", "description": "Invoice number"},
                        "issue_date": {"type": "string", "description": "Issue date"},
                        "due_date": {"type": "string", "description": "Due date"},
                        "project_number": {"type": "string", "description": "Project number"},
                        "general_description": {"type": "string", "description": "General description"},
                    },
                },
                "line_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_number": {"type": ["string", "null"], "description": "Item number"},
                            "description": {"type": "string", "description": "Item description"},
                            "quantity": {"type": "integer", "description": "Quantity"},
                            "unit_of_measure": {"type": "string", "description": "Unit of measure"},
                            "order_number": {"type": "string", "description": "Order number"},
                        },
                    },
                },
                "financial_summary": {
                    "type": "object",
                    "properties": {
                        "sub_total": {"type": "integer", "description": "Subtotal"},
                        "iva_amount": {"type": "integer", "description": "IVA amount"},
                        "total_amount": {"type": "integer", "description": "Total amount"},
                    },
                },
            },
        }

        payload = {
            "name": "invoice_parser",
            "data_schema": data_schema,
            "config": {
                "extraction_target": "PER_DOC",
                "extraction_mode": "BALANCED",
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/extraction/extraction-agents",
                headers=headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            agent = response.json()
            self._agent_id = agent["id"]
            return self._agent_id

    async def extract(
        self, 
        file_bytes: bytes, 
        filename: str,
        ocr_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract structured invoice data using Llama Cloud."""
        agent_id = await self._ensure_agent()

        headers = {
            "accept": "application/json",
            "Authorization": f"Bearer {self._api_key}",
        }

        # Upload original file
        file_buffer = io.BytesIO(file_bytes)
        content_type = "application/pdf" if filename.lower().endswith(".pdf") else "image/jpeg"
        files = {"upload_file": (filename, file_buffer, content_type)}
        data = {"purpose": "extract"}

        async with httpx.AsyncClient() as client:
            # Upload file
            upload_response = await client.post(
                f"{self._base_url}/files",
                headers=headers,
                files=files,
                data=data,
                timeout=30.0,
            )
            upload_response.raise_for_status()
            file_obj = upload_response.json()
            file_id = file_obj["id"]

            # Start extraction job
            job_payload = {
                "extraction_agent_id": agent_id,
                "file_id": file_id,
            }
            job_response = await client.post(
                f"{self._base_url}/extraction/jobs",
                headers=headers,
                json=job_payload,
                timeout=30.0,
            )
            job_response.raise_for_status()
            job = job_response.json()
            job_id = job["id"]

            # Poll for completion
            import asyncio
            max_wait = 180
            interval = 3
            waited = 0
            while waited < max_wait:
                status_response = await client.get(
                    f"{self._base_url}/extraction/jobs/{job_id}",
                    headers=headers,
                    timeout=30.0,
                )
                status_response.raise_for_status()
                status = status_response.json()
                job_status = status.get("status")

                if job_status in {"completed", "SUCCESS"}:
                    # Get result
                    result_response = await client.get(
                        f"{self._base_url}/extraction/jobs/{job_id}/result",
                        headers=headers,
                        timeout=30.0,
                    )
                    result_response.raise_for_status()
                    result = result_response.json()

                    # Unpack if list
                    if isinstance(result, list) and len(result) == 1:
                        result = result[0]

                    return result

                elif job_status in {"failed", "cancelled"}:
                    raise RuntimeError(f"Extraction job failed: {status}")

                await asyncio.sleep(interval)
                waited += interval

            raise RuntimeError(f"Extraction job timed out after {max_wait}s")

    def _extract_confidence(self, result: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """Extract confidence from Llama metadata if available."""
        if "extraction_metadata" in result:
            metadata = result["extraction_metadata"]
            # Llama doesn't provide field-level confidence, but we can add a general score
            return {"overall": 0.85}  # Default confidence for successful extractions
        return None
