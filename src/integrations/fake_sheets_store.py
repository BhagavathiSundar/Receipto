"""
A tiny in-memory stand-in for Google Sheets, used only by
scripts/simulate_e2e.py and the test suite so the full pipeline can run
with zero external services. Never used in production code paths.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.schemas.receipt import StructuredReceipt

_ROWS: list[dict] = []


def reset():
    _ROWS.clear()


def append_receipt_row(receipt: StructuredReceipt) -> bool:
    if any(r.get("content_hash") == receipt.content_hash and receipt.content_hash for r in _ROWS):
        return False
    items_summary = "; ".join(f"{i.name} x{i.quantity}" for i in receipt.items) if receipt.items else ""
    _ROWS.append(
        {
            "receipt_id": receipt.receipt_id,
            "date": receipt.date.isoformat(),
            "merchant_name": receipt.merchant_name,
            "category": receipt.category,
            "total_amount": receipt.total_amount,
            "tax_amount": receipt.tax_amount,
            "currency": receipt.currency,
            "payment_method": receipt.payment_method,
            "items_summary": items_summary,
            "source_chat_id": receipt.source_chat_id or "",
            "content_hash": receipt.content_hash or "",
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return True


def fetch_rows_for_month(month: int, year: int) -> list[dict]:
    out = []
    for r in _ROWS:
        y, m, _ = r["date"].split("-")
        if int(y) == year and int(m) == month:
            out.append(r)
    return out


def all_rows() -> list[dict]:
    return list(_ROWS)
