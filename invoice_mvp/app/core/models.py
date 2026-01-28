from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class InvoiceParty(BaseModel):
    name: str = ""
    rut: str = ""
    address: str = ""


class InvoiceDocumentDetails(BaseModel):
    series: str = ""
    number: str = ""
    issue_date: str = ""
    due_date: str = ""
    project_number: str = ""
    general_description: str = ""


class InvoiceFinancialSummary(BaseModel):
    sub_total: int = 0
    iva_amount: int = 0
    total_amount: int = 0


class InvoiceLineItem(BaseModel):
    item_number: Optional[str] = None
    description: str = ""
    quantity: int = 0
    unit_of_measure: str = ""
    order_number: str = ""


class InvoiceExtraction(BaseModel):
    seller: InvoiceParty
    buyer: InvoiceParty
    document_details: InvoiceDocumentDetails
    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    financial_summary: InvoiceFinancialSummary


class InvoiceLineItemWithTotals(BaseModel):
    rubro_code: Optional[str] = Field(None, description="Code from nomenclator, if already normalized")
    rubro_raw: str = Field(..., description="Raw rubro/description as extracted from OCR/LLM")
    quantity: float
    unit_price: float
    subtotal: float


class InvoiceTotals(BaseModel):
    subtotal: float
    iva: float
    iva_rate: float = Field(..., description="IVA percentage as a fraction, e.g. 0.19 for 19%")
    total: float


class Invoice(BaseModel):
    provider: InvoiceParty
    buyer: InvoiceParty
    line_items: List[InvoiceLineItemWithTotals]
    totals: InvoiceTotals


class InvoiceValidationIssue(BaseModel):
    code: str
    message: str
    field: Optional[str] = None


class InvoiceValidationResult(BaseModel):
    is_valid: bool
    issues: List[InvoiceValidationIssue] = Field(default_factory=list)


class ProcessedInvoice(BaseModel):
    invoice: Invoice
    validation: InvoiceValidationResult


class RubroNomenclatorEntry(BaseModel):
    code: str
    name: str


class RubroNormalizationResult(BaseModel):
    line_index: int
    original_rubro: str
    normalized_code: Optional[str]
    normalized_name: Optional[str]
