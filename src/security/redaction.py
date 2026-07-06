"""
Redaction utilities.

Used everywhere BEFORE writing raw OCR text, receipt images, or any user
content to logs or persistent stores that aren't the final structured
Sheet row. The goal is to strip payment-card numbers, long digit runs
(often account/phone numbers), and email addresses from free text prior
to logging.

This is a pragmatic best-effort filter, not a certified PCI-DSS solution.
It exists to reduce accidental leakage of sensitive substrings into logs,
error messages, and stack traces.
"""
from __future__ import annotations

import re

# 13-19 digit sequences, optionally separated by spaces/dashes every 4 digits
_CARD_NUMBER_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
# Bare long digit runs (phone numbers, account numbers, etc.)
_LONG_DIGIT_RUN_RE = re.compile(r"\b\d{9,}\b")
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
# CVV-looking 3-4 digit sequences preceded by the word cvv/cvc
_CVV_RE = re.compile(r"(?i)\b(cvv|cvc)\s*[:\-]?\s*\d{3,4}\b")


def _mask_digits(match: "re.Match") -> str:
    digits = re.sub(r"\D", "", match.group(0))
    if len(digits) <= 4:
        return "*" * len(digits)
    return "*" * (len(digits) - 4) + digits[-4:]


def redact_text(text: str) -> str:
    """Return a copy of `text` with likely-sensitive substrings masked."""
    if not text:
        return text
    redacted = _CARD_NUMBER_RE.sub(_mask_digits, text)
    redacted = _LONG_DIGIT_RUN_RE.sub(_mask_digits, redacted)
    redacted = _EMAIL_RE.sub("[redacted-email]", redacted)
    redacted = _CVV_RE.sub("[redacted-cvv]", redacted)
    return redacted


def safe_log_payload(payload: dict) -> dict:
    """Shallow-redact a dict meant for logging (does not mutate the input)."""
    out = {}
    for key, value in payload.items():
        if isinstance(value, str):
            out[key] = redact_text(value)
        elif key.lower() in ("image_bytes", "file_bytes", "raw_image"):
            out[key] = f"<{len(value) if value else 0} bytes omitted>"
        else:
            out[key] = value
    return out
