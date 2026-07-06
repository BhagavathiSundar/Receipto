"""
Process every receipt image/text file in a local folder through the real
configured pipeline (OCR provider + LLM provider + Google Sheet from your
.env). Useful for testing with your own scanned receipts before wiring up
Telegram.

Usage:
    python scripts/process_local_receipts.py --dir ./my_receipts --chat-id 12345
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.mcp_server.tools.run_ocr import run_ocr  # noqa: E402
from src.mcp_server.tools.extract_receipt import extract_receipt_structured  # noqa: E402
from src.mcp_server.tools.update_sheet import update_sheet  # noqa: E402

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".txt"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", required=True, help="Folder containing receipt files")
    parser.add_argument("--chat-id", default="local-test", help="Chat id to associate with these receipts")
    args = parser.parse_args()

    folder = Path(args.dir)
    if not folder.is_dir():
        raise SystemExit(f"Not a directory: {folder}")

    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if not files:
        print(f"No supported receipt files found in {folder}")
        return

    for file_path in files:
        receipt_id = f"local-{file_path.stem}"
        print(f"\n--- Processing {file_path.name} ({receipt_id}) ---")

        ocr_result = run_ocr(receipt_id=receipt_id, file_path=str(file_path))
        print(f"OCR confidence: {ocr_result['confidence']}")

        extraction = extract_receipt_structured(
            receipt_id=receipt_id, raw_text=ocr_result["raw_text"], chat_id=args.chat_id
        )
        if not extraction["valid"]:
            print(f"Validation failed: {extraction['validation_errors']}")
            continue

        write_result = update_sheet(structured_receipt=extraction["receipt"])
        receipt = extraction["receipt"]
        status = "written" if write_result["written"] else "duplicate, skipped"
        print(f"{receipt['merchant_name']} — {receipt['currency']} {receipt['total_amount']} ({status})")


if __name__ == "__main__":
    main()
