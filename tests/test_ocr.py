import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.models.ocr import (
    OcrError,
    _preprocess,
    build_document_timeline,
    extract_dates,
    extract_medication_mentions,
    extract_text,
)


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


# --- extract_medication_mentions -------------------------------------------------


def test_extract_medication_mentions_finds_realistic_dosage_line():
    text = "Tab. Paracetamol 500mg BD x 5 days"

    result = extract_medication_mentions(text)

    assert result != []
    assert any("Paracetamol" in mention and "500mg" in mention for mention in result)


def test_extract_medication_mentions_finds_multiple_and_dedupes():
    text = (
        "Cap. Omeprazole 20mg OD before breakfast.\n"
        "AMOXICILLIN 250 mg TID for 7 days.\n"
        "Repeat: AMOXICILLIN 250 mg TID for 7 days."
    )

    result = extract_medication_mentions(text)

    # Two distinct mentions, the repeated exact line deduplicated to one entry.
    assert any("Omeprazole" in mention for mention in result)
    assert any("AMOXICILLIN" in mention for mention in result)
    assert len(result) == len(set(result))
    amoxicillin_hits = [m for m in result if "AMOXICILLIN" in m]
    assert len(amoxicillin_hits) == 1


def test_extract_medication_mentions_returns_empty_list_for_plain_text():
    result = extract_medication_mentions("The patient reports mild headache since yesterday.")

    assert result == []


# --- extract_dates -----------------------------------------------------------------


def test_extract_dates_finds_slash_format():
    result = extract_dates("Report date: 05/01/2025")

    assert "05/01/2025" in result


def test_extract_dates_finds_dash_format():
    result = extract_dates("Report date: 05-01-2025")

    assert "05-01-2025" in result


def test_extract_dates_finds_day_month_year_format():
    result = extract_dates("Sample collected on 5 January 2025 in the morning.")

    assert "5 January 2025" in result


def test_extract_dates_finds_month_day_year_format():
    result = extract_dates("This prescription was issued January 5, 2025 by Dr. Rao.")

    assert "January 5, 2025" in result


def test_extract_dates_returns_empty_list_when_no_date_present():
    result = extract_dates("No date anywhere in this line of text.")

    assert result == []


# --- build_document_timeline --------------------------------------------------------


def test_build_document_timeline_orders_dated_documents_before_undated():
    documents = [
        ("intake note", "Patient reports fatigue, no specific date mentioned."),
        ("lab report", "Blood test collected on 5 January 2025, results attached."),
    ]

    timeline = build_document_timeline(documents)

    labels_in_order = [entry["label"] for entry in timeline]
    # Before: the undated "intake note" appears first in the input list.
    assert [label for label, _ in documents] == ["intake note", "lab report"]
    # After: build_document_timeline moves the dated "lab report" ahead of it.
    assert labels_in_order == ["lab report", "intake note"]
    assert timeline[0]["dates_found"] == ["5 January 2025"]
    assert timeline[1]["dates_found"] == []


def test_build_document_timeline_preserves_relative_order_within_groups():
    documents = [
        ("undated A", "no date here"),
        ("dated A", "Visit on 01/02/2025"),
        ("undated B", "still no date"),
        ("dated B", "Follow-up on 02/03/2025"),
    ]

    timeline = build_document_timeline(documents)

    labels_in_order = [entry["label"] for entry in timeline]
    # Both dated documents come first (stable relative order: A before B),
    # then both undated documents (again A before B), matching the
    # documented "stable partition" behavior.
    assert labels_in_order == ["dated A", "dated B", "undated A", "undated B"]


def test_build_document_timeline_includes_text_and_dates_found_keys():
    documents = [("scan", "Dated 10-04-2025, follow up needed")]

    timeline = build_document_timeline(documents)

    assert timeline[0]["label"] == "scan"
    assert timeline[0]["text"] == "Dated 10-04-2025, follow up needed"
    assert timeline[0]["dates_found"] == ["10-04-2025"]
