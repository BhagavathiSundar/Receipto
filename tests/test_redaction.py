import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.security.redaction import redact_text, safe_log_payload


def test_redacts_card_number():
    text = "Card ending charged: 4111 1111 1111 1111 approved"
    redacted = redact_text(text)
    assert "4111 1111 1111 1111" not in redacted
    assert "1111" in redacted  # last 4 digits preserved


def test_redacts_email():
    text = "Receipt sent to jane.doe@example.com"
    redacted = redact_text(text)
    assert "jane.doe@example.com" not in redacted
    assert "[redacted-email]" in redacted


def test_redacts_long_digit_run():
    text = "Account number 987654321012"
    redacted = redact_text(text)
    assert "987654321012" not in redacted


def test_safe_log_payload_omits_bytes():
    payload = {"file_bytes": b"x" * 100, "receipt_id": "abc"}
    out = safe_log_payload(payload)
    assert "bytes omitted" in out["file_bytes"]
    assert out["receipt_id"] == "abc"


def test_empty_text_passthrough():
    assert redact_text("") == ""
