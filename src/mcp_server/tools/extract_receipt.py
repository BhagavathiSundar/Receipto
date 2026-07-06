"""Tool: extract_receipt_structured"""
from __future__ import annotations

import hashlib
import logging
from datetime import date as Date

from pydantic import ValidationError

from src.integrations.llm_provider import extract_structured_fields
from src.schemas.receipt import StructuredReceipt
from src.security.redaction import safe_log_payload

logger = logging.getLogger("receipto.tools.extract_receipt")


def extract_receipt_structured(
    receipt_id: str,
    raw_text: str,
    hints: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
    file_bytes_for_hash: bytes | None = None,
) -> dict:
    """
    Turn noisy OCR text into a validated structured receipt.

    Args:
        receipt_id: stable id for this receipt
        raw_text: OCR output
        hints: optional free-text hint, e.g. "country=IN"
        chat_id / message_id: source identifiers, stored for traceability
        file_bytes_for_hash: original image bytes, used only to compute a
            dedupe hash (never stored or logged)

    Returns:
        Structured JSON matching StructuredReceipt, plus a `valid` flag
        and any `validation_errors`.
    """
    fields = extract_structured_fields(raw_text, hints=hints)
    fields.setdefault("date", Date.today().isoformat())

    content_hash = None
    if file_bytes_for_hash:
        content_hash = hashlib.sha256(file_bytes_for_hash).hexdigest()[:16]

    payload = {
        "receipt_id": receipt_id,
        "source_chat_id": chat_id,
        "source_message_id": message_id,
        "content_hash": content_hash,
        **fields,
    }

    try:
        receipt = StructuredReceipt(**payload)
        logger.info("Extraction OK for %s", safe_log_payload({"receipt_id": receipt_id}))
        return {"valid": True, "receipt": receipt.model_dump(mode="json"), "validation_errors": []}
    except ValidationError as exc:
        logger.warning("Extraction validation failed for %s", receipt_id)
        return {
            "valid": False,
            "receipt": payload,
            "validation_errors": [str(e) for e in exc.errors()],
        }
