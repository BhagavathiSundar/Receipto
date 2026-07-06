"""
Sheets & Reporting Agent.

Responsibility: persist validated receipts into Google Sheets
idempotently, and produce monthly summaries on demand.
"""
from __future__ import annotations

import logging

from src.agents.base import Agent
from src.mcp_server.tools.update_sheet import update_sheet
from src.mcp_server.tools.monthly_summary import get_monthly_summary

logger = logging.getLogger("receipto.agents.sheets_reporting")

INSTRUCTIONS = """You persist structured receipts into the expense sheet
and answer monthly-summary requests. Never write a receipt that failed
upstream validation. Treat duplicate content hashes as a no-op, not an
error."""


class SheetsReportingAgent(Agent):
    def __init__(self):
        super().__init__(
            name="sheets_reporting_agent",
            instructions=INSTRUCTIONS,
            tools={"update_sheet": update_sheet, "get_monthly_summary": get_monthly_summary},
        )

    def record_receipt(self, structured_receipt: dict) -> dict:
        result = self.call_tool("update_sheet", structured_receipt=structured_receipt)
        logger.info("record_receipt result: %s", result)
        return result

    def monthly_summary(self, month: int, year: int, user_id: str | None = None) -> dict:
        return self.call_tool("get_monthly_summary", month=month, year=year, user_id=user_id)

    def run(self, event: dict, context: dict | None = None) -> dict:
        event_type = event.get("type")
        if event_type == "record_receipt":
            return self.record_receipt(event["receipt"])
        if event_type == "monthly_summary":
            return self.monthly_summary(event["month"], event["year"], event.get("user_id"))
        raise ValueError(f"Unknown event type for SheetsReportingAgent: {event_type}")
