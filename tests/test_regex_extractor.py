from decimal import Decimal

import pytest

from app.services.extraction.base import FIELD_NAMES
from app.services.extraction.regex_extractor import RegexExtractor


@pytest.fixture
def extractor():
    return RegexExtractor()


def test_native_pdf_text(extractor, sample_pdf_text):
    result = extractor.extract(sample_pdf_text)
    assert result["fournisseur"].valeur == "Tech Solutions SARL"
    assert result["numero_facture"].valeur == "FAC-2026-001"
    assert result["date_facture"].valeur == "2026-11-15"
    assert result["montant_ht"].valeur == "3650000.00"
    assert result["tva"].valeur == "730000.00"
    assert result["montant_ttc"].valeur == "4380000.00"
    assert all(champ.confiance == 0.9 for champ in result.values())


def test_scanned_image_text_flags_garbled_total(extractor, sample_scan_text):
    result = extractor.extract(sample_scan_text)
    assert result["fournisseur"].valeur == "Librairie Universitaire"
    assert result["numero_facture"].valeur == "FAC-2026-002"
    assert result["numero_facture"].confiance == 0.6
    assert result["date_facture"].valeur == "2026-11-16"
    assert result["montant_ht"].valeur is None
    assert result["tva"].valeur is None
    assert result["montant_ttc"].valeur == "5.00"
    assert result["montant_ttc"].confiance == 0.3


def test_french_layout_with_due_date(extractor, sample_fr_text):
    result = extractor.extract(sample_fr_text)
    assert result["fournisseur"].valeur == "Établissements RAKOTO SARL"
    assert result["fournisseur"].confiance == 0.5
    assert result["numero_facture"].valeur == "2026/0042"
    assert result["date_facture"].valeur == "2026-12-03"
    assert Decimal(result["montant_ht"].valeur) == Decimal("1250000.50")
    assert Decimal(result["tva"].valeur) == Decimal("250000.10")
    assert Decimal(result["montant_ttc"].valeur) == Decimal("1500000.60")


def test_tva_rate_is_not_an_amount(extractor):
    result = extractor.extract("TOTAL HT: 100 Ar TVA : 20 % TOTAL TTC: 120 Ar")
    assert result["tva"].valeur is None
    assert result["montant_ht"].valeur == "100.00"
    assert result["montant_ttc"].valeur == "120.00"


def test_text_without_invoice_returns_all_missing(extractor):
    result = extractor.extract("Bonjour, ceci est un simple message.")
    assert set(result) == set(FIELD_NAMES)
    assert all(champ.valeur is None and champ.confiance == 0.0 for champ in result.values())


def test_label_without_digits_is_not_an_invoice_number(extractor):
    result = extractor.extract("Facture normale pour services rendus")
    assert result["numero_facture"].valeur is None