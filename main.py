"""
Receipto CLI entrypoint.

Usage:
    python main.py mcp-server          # run the standalone MCP server
    python main.py poll                # poll Telegram once for new receipts, process them
    python main.py summary --month 7 --year 2026 --chat-id 12345
"""
from __future__ import annotations

import argparse
import logging

from src.config import settings
from src.agents.orchestrator import OrchestratorAgent

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("receipto.main")


def cmd_mcp_server(_args):
    from src.mcp_server.server import mcp

    mcp.run()


def cmd_poll(args):
    orchestrator = OrchestratorAgent()
    outcomes = orchestrator.handle_new_receipt_message(source=args.source)
    for outcome in outcomes:
        logger.info("Outcome: %s", outcome)
    if not outcomes:
        logger.info("No new receipts found.")


def cmd_summary(args):
    orchestrator = OrchestratorAgent()
    summary = orchestrator.handle_generate_monthly_summary(
        chat_id=args.chat_id, month=args.month, year=args.year
    )
    print(summary["summary_text"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Receipto — everyday expense concierge agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("mcp-server", help="Run the standalone MCP server").set_defaults(func=cmd_mcp_server)

    poll_parser = sub.add_parser("poll", help="Poll for new receipt messages and process them")
    poll_parser.add_argument("--source", default="telegram", choices=["telegram", "whatsapp"])
    poll_parser.set_defaults(func=cmd_poll)

    summary_parser = sub.add_parser("summary", help="Generate and send a monthly summary")
    summary_parser.add_argument("--month", type=int, required=True)
    summary_parser.add_argument("--year", type=int, required=True)
    summary_parser.add_argument("--chat-id", required=True)
    summary_parser.set_defaults(func=cmd_summary)

    return parser


if __name__ == "__main__":
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
