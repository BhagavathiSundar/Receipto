"""Tool: run_ocr"""
from __future__ import annotations

import logging

from src.integrations.ocr_provider import run_ocr as _run_ocr
from src.security.redaction import safe_log_payload

logger = logging.getLogger("receipto.tools.run_ocr")


def run_ocr(receipt_id: str, file_path: str) -> dict:
    """
    Run OCR on a locally-downloaded receipt image/PDF page.

    Args:
        receipt_id: id from download_new_receipts
        file_path: local path to the image

    Returns:
        {raw_text, language, confidence}

    Note: raw_text is never logged verbatim; only a redacted, truncated
    preview is used in log lines.
    """
    result = _run_ocr(file_path)
    logger.info(
        "OCR complete for %s: %s",
        receipt_id,
        safe_log_payload({"raw_text_preview": result.raw_text[:60], "confidence": result.confidence}),
    )
    return {
        "receipt_id": receipt_id,
        "raw_text": result.raw_text,
        "language": result.language,
        "confidence": result.confidence,
    }
