from __future__ import annotations

from typing import Tuple

from ..core.models import Invoice, InvoiceValidationIssue, InvoiceValidationResult


def validate_invoice_numeric_consistency(invoice: Invoice) -> InvoiceValidationResult:
    """Validate basic numeric consistency of an invoice.

    Architectural decision: keep validation as a pure function over domain models
    so it is easy to test and reuse.
    """

    issues = []

    # Check line subtotals
    lines_subtotal = 0.0
    for idx, line in enumerate(invoice.line_items):
        expected = round(line.quantity * line.unit_price, 2)
        if abs(line.subtotal - expected) > 0.01:
            issues.append(
                InvoiceValidationIssue(
                    code="line_subtotal_mismatch",
                    message=f"Line {idx} subtotal {line.subtotal} != quantity*unit_price {expected}",
                    field=f"line_items[{idx}].subtotal",
                )
            )
        lines_subtotal += line.subtotal

    # Check subtotal matches sum of lines
    if abs(invoice.totals.subtotal - lines_subtotal) > 0.01:
        issues.append(
            InvoiceValidationIssue(
                code="subtotal_mismatch",
                message=f"Invoice subtotal {invoice.totals.subtotal} != sum of lines {lines_subtotal}",
                field="totals.subtotal",
            )
        )

    # Check IVA amount
    expected_iva = round(invoice.totals.subtotal * invoice.totals.iva_rate, 2)
    if abs(invoice.totals.iva - expected_iva) > 0.01:
        issues.append(
            InvoiceValidationIssue(
                code="iva_mismatch",
                message=f"IVA {invoice.totals.iva} != subtotal*iva_rate {expected_iva}",
                field="totals.iva",
            )
        )

    # Check total
    expected_total = round(invoice.totals.subtotal + invoice.totals.iva, 2)
    if abs(invoice.totals.total - expected_total) > 0.01:
        issues.append(
            InvoiceValidationIssue(
                code="total_mismatch",
                message=f"Total {invoice.totals.total} != subtotal+iva {expected_total}",
                field="totals.total",
            )
        )

    return InvoiceValidationResult(is_valid=len(issues) == 0, issues=issues)
