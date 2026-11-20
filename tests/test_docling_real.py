from pathlib import Path

import pytest

from app.services.ocr.docling_engine import DoclingEngine

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "tests"


@pytest.fixture(scope="module")
def engine():
    docling = DoclingEngine()
    docling.warm_up()
    return docling


@pytest.mark.slow
def test_docling_reads_native_pdf(engine):
    result = engine.extract(DATA_DIR / "facture_propre_001.pdf")
    assert "FAC-2026-001" in result.text
    assert "4380000" in result.text
    assert result.duration_ms > 0


@pytest.mark.slow
def test_docling_reads_scanned_image(engine):
    result = engine.extract(DATA_DIR / "facture_scan_002.jpg")
    assert "FAC-2026-002" in result.text