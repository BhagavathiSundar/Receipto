import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integrations import fake_sheets_store
from src.schemas.receipt import StructuredReceipt

FIXTURES = ROOT / "tests" / "fixtures"


def test_duplicate_content_hash_is_skipped():
    fake_sheets_store.reset()
    data = json.loads((FIXTURES / "sample_receipt_1.json").read_text())
    receipt = StructuredReceipt(**data)

    first_write = fake_sheets_store.append_receipt_row(receipt)
    second_write = fake_sheets_store.append_receipt_row(receipt)  # same content_hash

    assert first_write is True
    assert second_write is False
    assert len(fake_sheets_store.all_rows()) == 1


def test_different_receipts_both_written():
    fake_sheets_store.reset()
    r1 = StructuredReceipt(**json.loads((FIXTURES / "sample_receipt_1.json").read_text()))
    r2 = StructuredReceipt(**json.loads((FIXTURES / "sample_receipt_2.json").read_text()))

    fake_sheets_store.append_receipt_row(r1)
    fake_sheets_store.append_receipt_row(r2)

    assert len(fake_sheets_store.all_rows()) == 2
