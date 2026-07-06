"""
Simulate the full pipeline end-to-end with zero external services:

    sample_receipt (txt) -> run_ocr -> extract_receipt_structured
        -> update_sheet -> get_monthly_summary

Uses the built-in `mock` OCR/LLM providers and an in-memory fake sheet,
so it runs anywhere with just `pip install -r requirements.txt` (no
Telegram token, no Google service account, no LLM API key required).

Run with:
    python scripts/simulate_e2e.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Must be set BEFORE importing anything under src/, since settings are
# read from the environment at import time.
os.environ.setdefault("OCR_PROVIDER", "mock")
os.environ.setdefault("LLM_PROVIDER", "mock")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.integrations import fake_sheets_store  # noqa: E402
from src.mcp_server.tools import run_ocr as run_ocr_tool  # noqa: E402
from src.mcp_server.tools import extract_receipt as extract_tool  # noqa: E402
from src.mcp_server.tools import monthly_summary as summary_tool  # noqa: E402
from src.schemas.receipt import StructuredReceipt  # noqa: E402

# Patch the sheets-backed tools to use the offline fake store instead of
# a real Google Sheet, purely for this simulation script.
import src.integrations.google_sheets_client as sheets_client  # noqa: E402

sheets_client.append_receipt_row = fake_sheets_store.append_receipt_row
sheets_client.fetch_rows_for_month = fake_sheets_store.fetch_rows_for_month

FIXTURES = ROOT / "tests" / "fixtures" / "receipts"


def process_file(file_path: Path, chat_id: str = "demo-chat") -> dict:
    receipt_id = file_path.stem
    ocr = run_ocr_tool.run_ocr(receipt_id=receipt_id, file_path=str(file_path))
    extraction = extract_tool.extract_receipt_structured(
        receipt_id=receipt_id, raw_text=ocr["raw_text"], chat_id=chat_id
    )
    if not extraction["valid"]:
        print(f"[SKIP] {file_path.name}: validation errors {extraction['validation_errors']}")
        return {"status": "invalid"}

    receipt = StructuredReceipt(**extraction["receipt"])
    written = fake_sheets_store.append_receipt_row(receipt)
    print(f"[OK] {file_path.name} -> {receipt.merchant_name} {receipt.currency} {receipt.total_amount} "
          f"({'written' if written else 'duplicate, skipped'})")
    return {"status": "ok", "written": written}


def main():
    fake_sheets_store.reset()
    files = sorted(FIXTURES.glob("*.txt"))
    if not files:
        print(f"No fixture receipts found in {FIXTURES}")
        return

    print(f"Processing {len(files)} sample receipts from {FIXTURES}...\n")
    for f in files:
        process_file(f)

    print("\nAll rows currently in the (fake) sheet:")
    for row in fake_sheets_store.all_rows():
        print(" ", row)

    print("\nGenerating monthly summary for 2026-06...")
    summary = summary_tool.get_monthly_summary(month=6, year=2026)
    print(summary["summary_text"])
    print("Category totals:", summary["category_totals"])


if __name__ == "__main__":
    main()
