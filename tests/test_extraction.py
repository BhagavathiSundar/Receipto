import json
import os
import sys
from pathlib import Path

os.environ.setdefault("OCR_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mcp_server.tools.extract_receipt import extract_receipt_structured
from src.schemas.receipt import StructuredReceipt

FIXTURES = ROOT / "tests" / "fixtures"


def test_valid_receipt_fixture_parses():
    data = json.loads((FIXTURES / "sample_receipt_1.json").read_text())
    receipt = StructuredReceipt(**data)
    assert receipt.merchant_name == "Cafe Mocha House"
    assert receipt.total_amount == 441.0


def test_negative_amount_is_rejected():
    data = json.loads((FIXTURES / "sample_receipt_1.json").read_text())
    data["total_amount"] = -5
    try:
        StructuredReceipt(**data)
        assert False, "expected a validation error for a negative amount"
    except Exception:
        pass


def test_extract_from_mock_ocr_text():
    raw_text = json.loads((FIXTURES / "sample_ocr_output.json").read_text())["raw_text"]
    result = extract_receipt_structured(receipt_id="demo-001", raw_text=raw_text, chat_id="123")
    assert result["valid"] is True
    assert result["receipt"]["merchant_name"] == "Cafe Mocha House"
    assert result["receipt"]["category"] == "Food"
    assert result["receipt"]["total_amount"] == 441.0
