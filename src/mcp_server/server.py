"""
Receipto MCP server.

Exposes the five tools described in the project spec via the official
`mcp` Python SDK's FastMCP helper. Each agent (Planner/Orchestrator, OCR &
Extraction, Sheets & Reporting) talks to these tools rather than to raw
integrations directly — this is the "separation of concerns" boundary
called for in the capstone brief.

Run standalone with:
    python -m src.mcp_server.server
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from src.config import settings
from src.mcp_server.tools.download_receipts import download_new_receipts as _download_new_receipts
from src.mcp_server.tools.run_ocr import run_ocr as _run_ocr
from src.mcp_server.tools.extract_receipt import extract_receipt_structured as _extract_receipt_structured
from src.mcp_server.tools.update_sheet import update_sheet as _update_sheet
from src.mcp_server.tools.monthly_summary import get_monthly_summary as _get_monthly_summary
from src.mcp_server.tools.send_notification import send_notification as _send_notification

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("receipto.mcp_server")

mcp = FastMCP("receipto")


@mcp.tool()
def download_new_receipts(source: str = "telegram", since_timestamp: float | None = None) -> list[dict]:
    """Fetch and locally download new receipt images/PDFs from Telegram or WhatsApp."""
    return _download_new_receipts(source=source, since_timestamp=since_timestamp)


@mcp.tool()
def run_ocr(receipt_id: str, file_path: str) -> dict:
    """Run OCR on a downloaded receipt file and return raw text, language, confidence."""
    return _run_ocr(receipt_id=receipt_id, file_path=file_path)


@mcp.tool()
def extract_receipt_structured(
    receipt_id: str,
    raw_text: str,
    hints: str | None = None,
    chat_id: str | None = None,
    message_id: str | None = None,
) -> dict:
    """Extract structured receipt fields (merchant, date, totals, items, category) from OCR text."""
    return _extract_receipt_structured(
        receipt_id=receipt_id, raw_text=raw_text, hints=hints, chat_id=chat_id, message_id=message_id
    )


@mcp.tool()
def update_sheet(structured_receipt: dict) -> dict:
    """Append a validated receipt row into the configured Google Sheet tab (idempotent)."""
    return _update_sheet(structured_receipt=structured_receipt)


@mcp.tool()
def get_monthly_summary(month: int, year: int, user_id: str | None = None) -> dict:
    """Aggregate a month of expenses by category/merchant and return a summary."""
    return _get_monthly_summary(month=month, year=year, user_id=user_id)


@mcp.tool()
def send_notification(chat_id: str, message_text: str, source: str = "telegram") -> dict:
    """Send a text message back to the user (confirmation or summary)."""
    return _send_notification(chat_id=chat_id, message_text=message_text, source=source)


if __name__ == "__main__":
    logger.info("Starting Receipto MCP server on %s:%s", settings.mcp_host, settings.mcp_port)
    mcp.run()
