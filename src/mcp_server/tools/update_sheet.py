"""Tool: update_sheet"""
from __future__ import annotations

import logging

from src.integrations.google_sheets_client import append_receipt_row
from src.schemas.receipt import StructuredReceipt

logger = logging.getLogger("receipto.tools.update_sheet")


def update_sheet(structured_receipt: dict) -> dict:
    """
    Append a validated receipt as a row in the configured Google Sheet tab.
    Idempotent: rows with a content_hash already present are skipped.

    Args:
        structured_receipt: dict matching StructuredReceipt

    Returns:
        {written: bool, receipt_id: str}
    """
    receipt = StructuredReceipt(**structured_receipt)
    written = append_receipt_row(receipt)
    logger.info("Sheet update for %s: written=%s", receipt.receipt_id, written)
    return {"written": written, "receipt_id": receipt.receipt_id}
