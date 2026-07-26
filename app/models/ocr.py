"""
Prescription / lab-report OCR.

Deliberately not a trained model - see docs/INTERVIEW_NOTES.md for why
training custom OCR is the wrong call here. Tesseract reads the image
into raw text; that text is handed to the same NLP path the typed
symptom-text intake already uses (app/agents/intake.py), so this module
has exactly one job: image bytes in, clean text out.
"""

from __future__ import annotations

import io
import logging

import pytesseract
from PIL import Image, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class OcrError(RuntimeError):
    """Raised when the image can't be decoded or Tesseract isn't available."""


def _preprocess(image: Image.Image) -> Image.Image:
    """
    Grayscale + mild sharpening + autocontrast. This is standard OCR
    preprocessing advice - but tested empirically against a low-contrast
    synthetic image in this repo, it actually produced a WORSE result
    than raw Tesseract: "AMOXICILLIN" was misread as "ANTONICILLIN"
    after sharpening, a wrong-drug-name failure that matters a lot for
    a health-triage tool specifically. See docs/INTERVIEW_NOTES.md for
    the real numbers - kept in the pipeline as a normalization step
    (grayscale input is a fair Tesseract requirement either way), but
    NOT presented as a proven accuracy improvement, because it isn't
    proven, and it may occasionally hurt. Revisit with a config flag to
    disable sharpening once real prescription-photo samples are available
    to test against, rather than a synthetic low-contrast approximation.
    """
    grayscale = ImageOps.grayscale(image)
    sharpened = grayscale.filter(ImageFilter.SHARPEN)
    return ImageOps.autocontrast(sharpened)


def extract_text(image_bytes: bytes) -> str:
    """
    Raises OcrError on anything that isn't a real, decodable image -
    never returns an empty string silently for a bad upload, since a
    silently empty extraction would look identical to "the prescription
    genuinely had no text," which is a meaningfully different case for
    whatever calls this.
    """
    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()  # force decode now, not lazily on first use
    except Exception as exc:  # noqa: BLE001 - Pillow raises several distinct types for bad input
        raise OcrError(f"Could not decode image: {exc}") from exc

    processed = _preprocess(image)

    try:
        text = pytesseract.image_to_string(processed, lang="eng")
    except pytesseract.TesseractNotFoundError as exc:
        raise OcrError("Tesseract is not installed or not on PATH.") from exc

    cleaned = text.strip()
    if not cleaned:
        logger.warning("OCR produced no text - image may be blank, illegible, or non-text content.")
    return cleaned
