"""
OCR & Information Extraction Agent.

Responsibility: turn a downloaded receipt file into a validated
StructuredReceipt. Calls the `run_ocr` and `extract_receipt_structured`
MCP tools in sequence, and applies a single retry with a stricter hint
if the first extraction fails validation.
"""
from __future__ import annotations

import logging

from src.agents.base import Agent
from src.mcp_server.tools.run_ocr import run_ocr
from src.mcp_server.tools.extract_receipt import extract_receipt_structured

logger = logging.getLogger("receipto.agents.ocr_extraction")

INSTRUCTIONS = """You turn raw receipt images into clean structured JSON.
Steps: (1) OCR the image, (2) extract structured fields, (3) validate.
If validation fails once, retry extraction with a stricter hint asking
for ISO dates and numeric-only amounts. If it fails twice, surface the
error to the orchestrator rather than writing bad data downstream."""


class OcrExtractionAgent(Agent):
    def __init__(self):
        super().__init__(
            name="ocr_extraction_agent",
            instructions=INSTRUCTIONS,
            tools={"run_ocr": run_ocr, "extract_receipt_structured": extract_receipt_structured},
        )

    def run(self, event: dict, context: dict | None = None) -> dict:
        receipt_id = event["receipt_id"]
        file_path = event["file_path"]

        ocr_result = self.call_tool("run_ocr", receipt_id=receipt_id, file_path=file_path)

        extraction = self.call_tool(
            "extract_receipt_structured",
            receipt_id=receipt_id,
            raw_text=ocr_result["raw_text"],
            hints=event.get("hints"),
            chat_id=event.get("chat_id"),
            message_id=event.get("message_id"),
        )

        if not extraction["valid"]:
            logger.warning("Retrying extraction for %s with stricter hint", receipt_id)
            extraction = self.call_tool(
                "extract_receipt_structured",
                receipt_id=receipt_id,
                raw_text=ocr_result["raw_text"],
                hints="Return ISO 8601 dates (YYYY-MM-DD) and numeric-only amounts, no currency symbols.",
                chat_id=event.get("chat_id"),
                message_id=event.get("message_id"),
            )

        return {
            "ok": extraction["valid"],
            "receipt": extraction["receipt"],
            "validation_errors": extraction.get("validation_errors", []),
            "ocr_confidence": ocr_result["confidence"],
        }
