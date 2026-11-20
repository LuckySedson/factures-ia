from datetime import date
from decimal import Decimal

from app.services.extraction.grounding import (
    amount_candidates,
    date_candidates,
    is_text_grounded,
)


def test_amount_candidates(sample_pdf_text):
    amounts = amount_candidates(sample_pdf_text)
    assert Decimal("4380000.00") in amounts
    assert Decimal("730000.00") in amounts
    assert Decimal("99999.00") not in amounts


def test_date_candidates_and_text_grounding(sample_fr_text):
    dates = date_candidates(sample_fr_text)
    assert date(2026, 12, 3) in dates
    assert date(2027, 1, 3) in dates
    assert date(2026, 1, 1) not in dates
    assert is_text_grounded("Établissements RAKOTO", sample_fr_text)
    assert not is_text_grounded("Société Inventée", sample_fr_text)