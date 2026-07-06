"""
Google Sheets client wrapper.

Uses a service account (path via GOOGLE_APPLICATION_CREDENTIALS) and the
`gspread` library. Creates the configured tab if it doesn't exist yet,
writes a header row, and appends data rows.

Idempotency: before appending, we check the `content_hash` column for a
match and skip the write if the same receipt was already recorded. This
protects against double-processing the same image (e.g., a Telegram
polling retry).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from src.config import settings
from src.schemas.receipt import SHEET_COLUMNS, StructuredReceipt

logger = logging.getLogger("receipto.sheets")


def _client():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("gspread/google-auth not installed") from exc

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(
        settings.google_application_credentials, scopes=scopes
    )
    return gspread.authorize(creds)


def _get_or_create_worksheet():
    gc = _client()
    sh = gc.open_by_key(settings.sheets_spreadsheet_id)
    try:
        ws = sh.worksheet(settings.sheets_tab_name)
    except Exception:
        ws = sh.add_worksheet(title=settings.sheets_tab_name, rows=1000, cols=len(SHEET_COLUMNS))
        ws.append_row(SHEET_COLUMNS)
    return ws


def _existing_hashes(ws) -> set[str]:
    try:
        header = ws.row_values(1)
        if "content_hash" not in header:
            return set()
        col_idx = header.index("content_hash") + 1
        values = ws.col_values(col_idx)[1:]  # skip header
        return set(v for v in values if v)
    except Exception:
        return set()


def append_receipt_row(receipt: StructuredReceipt) -> bool:
    """Returns True if a new row was written, False if skipped as a duplicate."""
    ws = _get_or_create_worksheet()

    if receipt.content_hash:
        if receipt.content_hash in _existing_hashes(ws):
            logger.info("Skipping duplicate receipt (hash already present)")
            return False

    items_summary = "; ".join(f"{i.name} x{i.quantity}" for i in receipt.items) if receipt.items else ""
    row = [
        receipt.receipt_id,
        receipt.date.isoformat(),
        receipt.merchant_name,
        receipt.category,
        receipt.total_amount,
        receipt.tax_amount,
        receipt.currency,
        receipt.payment_method,
        items_summary,
        receipt.source_chat_id or "",
        receipt.content_hash or "",
        datetime.now(timezone.utc).isoformat(),
    ]
    ws.append_row(row)
    return True


def fetch_rows_for_month(month: int, year: int) -> list[dict]:
    ws = _get_or_create_worksheet()
    records = ws.get_all_records()
    out = []
    for r in records:
        date_str = str(r.get("date", ""))
        if not date_str:
            continue
        try:
            y, m, _ = date_str.split("-")
        except ValueError:
            continue
        if int(y) == year and int(m) == month:
            out.append(r)
    return out
