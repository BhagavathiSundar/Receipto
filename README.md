# Receipto — the everyday expense concierge agent

A small multi-agent system that watches a Telegram chat for receipt
photos, extracts structured expense data with OCR + an LLM, logs it into
a Google Sheet, and sends back monthly spending summaries — built for the
**Kaggle "AI Agents: Intensive Vibe Coding Capstone Project"** (Agents for
Business / Concierge Agents track).

---

## 1. Problem & motivation

Most people's receipts pile up as unread photos in a chat thread or a
phone gallery. Manually re-typing them into a spreadsheet is tedious
enough that almost nobody does it consistently — so budgeting and
expense reports rely on memory instead of data.

Receipto turns "I photographed my receipt" into "it's already a row in
my expense sheet, categorized" with zero manual data entry, and answers
"how much did I spend this month?" on request.

## 2. Solution overview

1. You send a photo (or PDF) of a receipt to a Telegram bot.
2. An **orchestrator agent** picks up the new message, and hands it to an
   **OCR & extraction agent**, which turns the image into validated JSON
   (merchant, date, total, tax, items, category).
3. A **sheets & reporting agent** writes that JSON as a new row into your
   Google Sheet — skipping it if it's a duplicate of something already
   logged.
4. The bot replies with a one-line confirmation ("Logged: Cafe Mocha
   House — INR 441.00 (Food)"), or a plain-language error if something
   went wrong.
5. On request (or on a schedule), the same reporting agent aggregates the
   sheet by month and sends back a short summary with category totals
   and top merchants.

## 3. Architecture

```
                         ┌─────────────────────────┐
                         │   Telegram (or WhatsApp) │
                         │   chat — receipt photos  │
                         └────────────┬─────────────┘
                                      │ new message / poll
                                      ▼
                     ┌────────────────────────────────┐
                     │   Planner / Orchestrator Agent   │
                     │  - dispatches events             │
                     │  - sequences tool calls           │
                     │  - simple, explicit error recovery│
                     └───────┬───────────────┬──────────┘
                             │               │
             new_receipt_msg │               │ generate_monthly_summary
                             ▼               ▼
        ┌───────────────────────────┐  ┌────────────────────────────┐
        │ OCR & Extraction Agent     │  │ Sheets & Reporting Agent   │
        │  tools:                    │  │  tools:                   │
        │  - run_ocr                 │  │  - update_sheet            │
        │  - extract_receipt_        │  │  - get_monthly_summary     │
        │    structured               │  └──────────────┬─────────────┘
        └──────────────┬─────────────┘                   │
                        │                                  │
                        ▼                                  ▼
              ┌──────────────────────────────────────────────────┐
              │                 MCP Server (FastMCP)               │
              │  download_new_receipts · run_ocr ·                 │
              │  extract_receipt_structured · update_sheet ·       │
              │  get_monthly_summary · send_notification           │
              └───────┬───────────────┬───────────────┬───────────┘
                      │               │               │
                      ▼               ▼               ▼
              Telegram Bot API   OCR provider     Google Sheets
              (download/send)  (tesseract /       (gspread)
                                 google_vision)
                      ▲
                      │
              LLM provider (Anthropic / OpenAI) — structured
              extraction + categorization + summary text
```

Every agent talks to the outside world **only** through MCP tools — none
of them call Telegram, Tesseract, an LLM API, or Google Sheets directly.
That boundary is what keeps the agents swappable and testable (see the
`mock` providers used by the offline demo scripts).

## 4. Agent & MCP design

### Agents (`src/agents/`)

| Agent | File | Responsibility |
|---|---|---|
| Planner / Orchestrator | `orchestrator.py` | Receives `new_receipt_message` / `generate_monthly_summary` events, sequences tool calls across the other two agents, handles failures per-receipt without blocking a batch. |
| OCR & Extraction | `ocr_extraction_agent.py` | `run_ocr` → `extract_receipt_structured`, with one retry (stricter hint) on validation failure. |
| Sheets & Reporting | `sheets_reporting_agent.py` | `update_sheet` (idempotent) and `get_monthly_summary`. |

`src/agents/base.py` is a small `Agent` base class shaped to mirror
Google's **Agent Development Kit (ADK)** primitives (`name`,
`instructions`, `tools`, `run()`), so it's a near drop-in port to a real
`google.adk.Agent` if you want to swap in the actual ADK runtime.

### MCP tools (`src/mcp_server/`)

| Tool | Input | Output |
|---|---|---|
| `download_new_receipts` | `source`, `since_timestamp?` | list of `{receipt_id, chat_id, message_id, file_path}` |
| `run_ocr` | `receipt_id`, `file_path` | `{raw_text, language, confidence}` |
| `extract_receipt_structured` | `raw_text`, `hints?` | validated receipt JSON + `valid`/`validation_errors` |
| `update_sheet` | structured receipt JSON | `{written, receipt_id}` (idempotent on content hash) |
| `get_monthly_summary` | `month`, `year`, `user_id?` | category totals, top merchants, summary text |
| `send_notification` | `chat_id`, `message_text` | `{sent}` |

Server entrypoint: `src/mcp_server/server.py`, built on the official
`mcp` Python SDK's `FastMCP` helper.

## 5. Setup & running locally

```bash
git clone <this-repo>
cd receipto
cp .env.example .env        # fill in your real tokens/keys
make install                 # pip install -r requirements.txt
```

**Run the offline demo (no external services needed at all):**

```bash
python scripts/simulate_e2e.py
```

This processes three sample receipts from `tests/fixtures/receipts/`
using the built-in `mock` OCR/LLM providers and an in-memory fake sheet,
prints each logged row, and prints a monthly summary. Good first thing
to run to confirm the pipeline logic before wiring up real services.

**Run against your own receipt images** (uses your real `OCR_PROVIDER`
and `LLM_PROVIDER` from `.env`, still writes to a real Google Sheet):

```bash
python scripts/process_local_receipts.py --dir ./my_receipts --chat-id 12345
```

**Run the real Telegram + Sheets pipeline:**

```bash
make run-mcp        # starts the MCP server (src/mcp_server/server.py)
make poll            # in another terminal: pull + process new Telegram messages once
make summary MONTH=7 YEAR=2026 CHAT_ID=<your_chat_id>
```

**Tests:**

```bash
make test
```

### Telegram setup (polling vs webhook)

- **Polling** (simplest for a demo): set `TELEGRAM_MODE=polling` in
  `.env`, create a bot via [@BotFather](https://t.me/BotFather), put the
  token in `TELEGRAM_BOT_TOKEN`, then run `make poll` (or loop it, see
  the `receipto-poller` service in `docker-compose.yml`).
- **Webhook**: set `TELEGRAM_MODE=webhook` and `TELEGRAM_WEBHOOK_URL` to
  a public HTTPS URL that forwards to your server, and register it with
  Telegram's `setWebhook` API. Useful once you deploy somewhere with a
  stable public address.

## 6. Deployment guide

**Option A — Docker Compose (recommended for a cheap VM):**

```bash
cp .env.example .env   # fill in real values
docker compose build
docker compose up -d receipto-mcp-server
# optionally also run the polling loop:
docker compose --profile poller up -d receipto-poller
```

**Option B — single container, any host that runs Docker** (Fly.io,
Railway, a small GCE/EC2 instance, etc.):

```bash
docker build -t receipto .
docker run --env-file .env -p 8765:8765 \
  -v $(pwd)/secrets:/app/secrets:ro \
  -v $(pwd)/data:/app/data \
  receipto
```

Mount your Google service-account JSON under `./secrets/` and point
`GOOGLE_APPLICATION_CREDENTIALS` at the in-container path — never bake
the key into the image.

## 7. Security considerations

- **No secrets in code or logs.** All tokens/keys come from environment
  variables (`.env`, gitignored); `.env.example` documents every
  variable without real values.
- **PII redaction before logging.** `src/security/redaction.py` masks
  card-like numbers, long digit runs (phone/account numbers), emails,
  and CVV-looking sequences before anything touches a log line. Raw OCR
  text and receipt images are **never** logged in full — only redacted,
  truncated previews (see `run_ocr.py`, `extract_receipt.py`).
- **Minimal retention.** Downloaded receipt images live in
  `RECEIPT_STORAGE_DIR` and are meant to be cleaned up after
  `RECEIPT_RETENTION_HOURS` (wire a cron/cleanup job in production; the
  setting is read from config today as the hook point).
- **Input validation.** `send_notification` strips control characters
  and caps message length before calling the Bot API;
  `extract_receipt_structured` runs all fields through a strict Pydantic
  schema (non-negative amounts, ISO dates, uppercase currency) before
  anything reaches the sheet.
- **Idempotency as a safety property, not just a UX nicety.** Writing
  the same receipt twice (e.g., a retried poll) is a no-op keyed on a
  content hash — this also limits duplicate exposure of the same data.

## 8. Limitations & future work

- WhatsApp ingestion is stubbed (`download_new_receipts(source="whatsapp")`
  raises `NotImplementedError`) — Telegram was prioritized since it needs
  no business-account approval for a demo.
- Google Vision OCR is a stub; only `tesseract` (free/local) and `mock`
  (offline demo) are implemented today.
- No multi-user auth model yet — `user_id` is accepted by
  `get_monthly_summary` but not yet used to filter rows in the sheet
  schema; a real deployment would add a `user_id` column.
- Scheduled monthly summaries currently need an external cron/Cloud
  Scheduler hitting `make summary`; there's no built-in scheduler.
- The `Agent` base class is a lightweight stand-in for Google ADK, not
  the ADK runtime itself — ported deliberately to keep the demo
  dependency-light; see `src/agents/base.py` for the porting notes.

## 9. How this demonstrates the course concepts

- **Agent / multi-agent system (ADK-style):** three cooperating agents
  (`orchestrator.py`, `ocr_extraction_agent.py`,
  `sheets_reporting_agent.py`) with an ADK-shaped base class, explicit
  per-agent instructions, and simple, visible error-recovery logic in
  the orchestrator.
- **MCP Server:** `src/mcp_server/server.py` exposes six well-defined
  tools via the official `mcp` SDK; agents call tools, never raw
  integrations, directly.
- **Security features:** environment-only secrets, a dedicated
  redaction utility used at every logging call site, strict schema
  validation, input sanitization on outbound messages, and a documented
  retention story.
- **Deployability:** a `Dockerfile` + `docker-compose.yml` that runs the
  whole thing with one command, plus a `Makefile` for local dev.
- **Antigravity:** this repository's structure and code scaffolding were
  generated and iterated on from a single detailed capstone prompt (this
  README's sibling prompt document), then refined — the prompt-to-code
  loop is the "Antigravity usage" this project demonstrates.
