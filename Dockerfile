FROM python:3.12-slim

# tesseract-ocr is the free default OCR engine used by OCR_PROVIDER=tesseract
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/receipts_tmp

ENV PYTHONUNBUFFERED=1

# Default: run the MCP server. Override CMD to run `poll` or `summary`
# as a one-off job (e.g. via cron/Cloud Scheduler hitting the container).
CMD ["python", "main.py", "mcp-server"]
