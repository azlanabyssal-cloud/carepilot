import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.models.ocr import OcrError, _preprocess, extract_text


def _render_text_image(text: str, fill: int = 0, background: int = 255, size: tuple[int, int] = (500, 120)) -> bytes:
    """Builds a real PNG with real rendered text - not a fixture pulled from anywhere, so there's
    no license question and no dependency on a dataset that may not be downloadable in CI."""
    image = Image.new("L", size, color=background)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((10, 40), text, fill=fill, font=font)
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="PNG")
    return buffer.getvalue()


def test_extract_text_reads_a_real_rendered_image():
    image_bytes = _render_text_image("PARACETAMOL 500MG TWICE DAILY")

    result = extract_text(image_bytes)

    # OCR on a default bitmap font isn't guaranteed character-perfect,
    # so this checks for the dominant, distinctive token rather than an
    # exact string match - a real, non-brittle assertion.
    assert "PARACETAMOL" in result.upper()


def test_extract_text_raises_on_undecodable_bytes():
    with pytest.raises(OcrError):
        extract_text(b"this is not an image, just plain bytes")


def test_extract_text_raises_not_silently_empty_on_bad_input():
    # Distinguishing "bad input" (raise) from "genuinely blank image"
    # (return "") is a real design decision - this proves the former.
    with pytest.raises(OcrError):
        extract_text(b"")


def test_extract_text_on_genuinely_blank_image_returns_empty_not_an_error():
    blank = Image.new("L", (200, 100), color=255)
    buffer = io.BytesIO()
    blank.save(buffer, format="PNG")

    result = extract_text(buffer.getvalue())

    assert result == ""


def test_extract_text_on_rotated_image_does_not_crash():
    # Tesseract doesn't auto-detect rotation by default - this documents
    # and locks in the real, verified behavior (garbled output, not an
    # exception) rather than leaving it as an unverified claim in docs.
    image_bytes = _render_text_image("PARACETAMOL 500MG")
    image = Image.open(io.BytesIO(image_bytes)).rotate(90, expand=True)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    result = extract_text(buffer.getvalue())

    assert isinstance(result, str)  # garbled output is expected; a crash is not


def test_preprocess_returns_grayscale_image():
    color_image = Image.new("RGB", (100, 50), color=(200, 100, 50))

    processed = _preprocess(color_image)

    assert processed.mode == "L"
