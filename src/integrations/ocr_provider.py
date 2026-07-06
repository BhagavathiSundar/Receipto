"""
OCR provider abstraction.

Swap providers purely via the OCR_PROVIDER env var — no code changes
needed elsewhere. Default is `tesseract` (free, local, good enough for
a demo). `google_vision` is provided as a stub for higher accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.config import settings


@dataclass
class OcrResult:
    raw_text: str
    language: str
    confidence: float


def run_ocr(file_path: str) -> OcrResult:
    provider = settings.ocr_provider.lower()
    if provider == "mock":
        return _run_mock(file_path)
    if provider == "tesseract":
        return _run_tesseract(file_path)
    if provider == "google_vision":
        return _run_google_vision(file_path)
    raise ValueError(f"Unknown OCR_PROVIDER: {provider}")


def _run_mock(file_path: str) -> OcrResult:
    """
    Demo/test provider: if `file_path` points at a .txt file, its contents
    are returned as the "OCR'd" text verbatim. This lets the whole pipeline
    run end-to-end with no camera, no Tesseract binary, and no external
    API - used by scripts/simulate_e2e.py and the test suite.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return OcrResult(raw_text=text.strip(), language="en", confidence=0.95)


def _run_tesseract(file_path: str) -> OcrResult:
    try:
        import pytesseract
        from PIL import Image
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "pytesseract/Pillow not installed. Run `pip install -r requirements.txt` "
            "and ensure the `tesseract-ocr` system package is installed."
        ) from exc

    image = Image.open(file_path)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    text = pytesseract.image_to_string(image)
    confidences = [int(c) for c in data.get("conf", []) if c not in ("-1", -1)]
    avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
    return OcrResult(raw_text=text.strip(), language="auto", confidence=round(avg_conf, 2))


def _run_google_vision(file_path: str) -> OcrResult:  # pragma: no cover - stub
    """
    Placeholder for Google Cloud Vision integration.
    Fill in with `google-cloud-vision` client using GOOGLE_VISION_API_KEY
    or Application Default Credentials.
    """
    raise NotImplementedError(
        "Google Vision OCR is not wired up yet. Implement using the "
        "google-cloud-vision client and GOOGLE_VISION_API_KEY / ADC."
    )
