"""
Planner / Orchestrator Agent.

Entry point for two high-level events:
  - "new_receipt_message": drive a single receipt through OCR -> extraction
    -> sheet write -> confirmation notification.
  - "generate_monthly_summary": pull a monthly summary and notify the user.

Error handling is intentionally simple and explicit rather than "smart":
each stage either succeeds or the orchestrator stops and reports back to
the user what went wrong, instead of silently swallowing errors or
writing partial/bad rows into the sheet.
"""
from __future__ import annotations

import logging

from src.agents.base import Agent
from src.agents.ocr_extraction_agent import OcrExtractionAgent
from src.agents.sheets_reporting_agent import SheetsReportingAgent
from src.mcp_server.tools.download_receipts import download_new_receipts
from src.mcp_server.tools.send_notification import send_notification

logger = logging.getLogger("receipto.agents.orchestrator")

INSTRUCTIONS = """You are the top-level planner. For "new_receipt_message"
events: run OCR+extraction, then write to the sheet only if extraction
was valid, then send a confirmation (or a clear failure notice) back to
the user. For "generate_monthly_summary" events: fetch the summary and
send it as a formatted message. Never let one failed receipt block
others in a batch."""


class OrchestratorAgent(Agent):
    def __init__(self):
        self.ocr_extraction_agent = OcrExtractionAgent()
        self.sheets_reporting_agent = SheetsReportingAgent()
        super().__init__(
            name="orchestrator_agent",
            instructions=INSTRUCTIONS,
            tools={
                "download_new_receipts": download_new_receipts,
                "send_notification": send_notification,
            },
        )

    # ---- event handlers -------------------------------------------------

    def handle_new_receipt_message(self, source: str = "telegram", since_timestamp: float | None = None) -> list[dict]:
        incoming = self.call_tool("download_new_receipts", source=source, since_timestamp=since_timestamp)
        outcomes = []
        for item in incoming:
            outcomes.append(self._process_single_receipt(item))
        return outcomes

    def _process_single_receipt(self, item: dict) -> dict:
        receipt_id = item["receipt_id"]
        chat_id = item["chat_id"]
        try:
            extraction_result = self.ocr_extraction_agent.run(
                {
                    "receipt_id": receipt_id,
                    "file_path": item["file_path"],
                    "chat_id": chat_id,
                    "message_id": item.get("message_id"),
                }
            )
        except Exception as exc:  # OCR/LLM/provider failure
            logger.exception("OCR/extraction pipeline failed for %s", receipt_id)
            self._notify_failure(chat_id, receipt_id, f"couldn't read that receipt ({type(exc).__name__})")
            return {"receipt_id": receipt_id, "status": "error", "stage": "ocr_extraction"}

        if not extraction_result["ok"]:
            self._notify_failure(
                chat_id,
                receipt_id,
                "some fields looked off (" + "; ".join(extraction_result["validation_errors"][:2]) + ")",
            )
            return {"receipt_id": receipt_id, "status": "invalid", "stage": "validation"}

        try:
            write_result = self.sheets_reporting_agent.record_receipt(extraction_result["receipt"])
        except Exception:
            logger.exception("Sheet write failed for %s", receipt_id)
            self._notify_failure(chat_id, receipt_id, "extracted it fine but couldn't save it to your sheet")
            return {"receipt_id": receipt_id, "status": "error", "stage": "sheet_write"}

        receipt = extraction_result["receipt"]
        if write_result["written"]:
            msg = (
                f"Logged: {receipt['merchant_name']} — {receipt['currency']} "
                f"{receipt['total_amount']} ({receipt['category']})"
            )
        else:
            msg = f"Already logged {receipt['merchant_name']} earlier — skipped the duplicate."
        self.call_tool("send_notification", chat_id=chat_id, message_text=msg)

        return {"receipt_id": receipt_id, "status": "ok", "written": write_result["written"]}

    def handle_generate_monthly_summary(self, chat_id: str, month: int, year: int, user_id: str | None = None) -> dict:
        summary = self.sheets_reporting_agent.monthly_summary(month, year, user_id)
        self.call_tool("send_notification", chat_id=chat_id, message_text=summary["summary_text"])
        return summary

    def _notify_failure(self, chat_id: str, receipt_id: str, reason: str) -> None:
        try:
            self.call_tool("send_notification", chat_id=chat_id, message_text=f"Hmm, {reason}. (ref: {receipt_id})")
        except Exception:
            logger.exception("Failed to even send the failure notification for %s", receipt_id)

    # ---- Agent.run dispatch ---------------------------------------------

    def run(self, event: dict, context: dict | None = None) -> dict | list[dict]:
        event_type = event.get("type")
        if event_type == "new_receipt_message":
            return self.handle_new_receipt_message(
                source=event.get("source", "telegram"), since_timestamp=event.get("since_timestamp")
            )
        if event_type == "generate_monthly_summary":
            return self.handle_generate_monthly_summary(
                chat_id=event["chat_id"], month=event["month"], year=event["year"], user_id=event.get("user_id")
            )
        raise ValueError(f"Unknown event type: {event_type}")
