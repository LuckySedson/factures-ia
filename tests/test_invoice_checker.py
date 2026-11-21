from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

from app.db.models import ChampExtrait, Facture
from app.services.controls import DuplicateMatch, InvoiceChecker
from app.services.extraction.base import FIELD_NAMES


def make_facture(**overrides):
    values = {
        "id": 2,
        "document_id": 2,
        "fournisseur_id": 1,
        "numero_facture": "FAC-001",
        "date_facture": date(2026, 11, 15),
        "montant_ht": Decimal("1000.00"),
        "tva": Decimal("200.00"),
        "montant_ttc": Decimal("1200.00"),
        "devise": "MGA",
        "statut": "en_attente",
        "score_confiance": 0.9,
        "duree_traitement_ms": None,
        "created_at": datetime(2026, 11, 15, 10, 0),
        "validated_at": None,
    }
    values.update(overrides)
    return Facture(**values)


def make_champs(confiance=0.9, **per_field):
    return [
        ChampExtrait(
            id=index,
            facture_id=2,
            nom_champ=name,
            valeur_extraite="x",
            valeur_corrigee=None,
            confiance=per_field.get(name, confiance),
            methode="regex",
        )
        for index, name in enumerate(FIELD_NAMES, start=1)
    ]


def kinds(decision):
    return {item.type_anomalie for item in decision.anomalies}


def test_clean_invoice_is_auto_validated():
    decision = InvoiceChecker().check(make_facture(), make_champs())
    assert decision.statut == "validee_auto"
    assert decision.anomalies == []


def test_missing_fields_need_review():
    facture = make_facture(montant_ht=None, tva=None)
    decision = InvoiceChecker().check(facture, make_champs(montant_ht=0.0, tva=0.0))
    assert decision.statut == "a_verifier"
    assert kinds(decision) == {"champ_manquant"}
    assert "montant_ht" in decision.anomalies[0].details
    assert "tva" in decision.anomalies[0].details


def test_amount_mismatch_needs_review():
    decision = InvoiceChecker().check(
        make_facture(montant_ttc=Decimal("1300.00")), make_champs()
    )
    assert decision.statut == "a_verifier"
    assert kinds(decision) == {"incoherence_montant"}


def test_rounding_within_tolerance_is_accepted():
    decision = InvoiceChecker().check(
        make_facture(montant_ttc=Decimal("1200.50")), make_champs()
    )
    assert decision.statut == "validee_auto"


def test_ttc_lower_than_ht_is_flagged():
    facture = make_facture(tva=None, montant_ttc=Decimal("5.00"))
    decision = InvoiceChecker().check(facture, make_champs(tva=0.0))
    assert kinds(decision) == {"champ_manquant", "incoherence_montant"}


def test_low_confidence_needs_review():
    decision = InvoiceChecker().check(make_facture(), make_champs(montant_ttc=0.3))
    assert decision.statut == "a_verifier"
    assert kinds(decision) == {"faible_confiance"}
    assert "montant_ttc" in decision.anomalies[0].details


def test_corrected_value_counts_as_confident():
    champs = [
        replace(champ, valeur_corrigee="1200.00") if champ.nom_champ == "montant_ttc" else champ
        for champ in make_champs(montant_ttc=0.3)
    ]
    decision = InvoiceChecker().check(make_facture(), champs)
    assert decision.statut == "validee_auto"


def test_duplicate_has_priority():
    duplicate = DuplicateMatch(7, "Même fournisseur et même numéro que la facture 7")
    decision = InvoiceChecker().check(make_facture(montant_ht=None), make_champs(), duplicate)
    assert decision.statut == "doublon_suspect"
    linked = [item for item in decision.anomalies if item.type_anomalie == "doublon_metier"][0]
    assert linked.facture_liee_id == 7


def test_threshold_is_configurable():
    champs = make_champs(numero_facture=0.75)
    assert InvoiceChecker().check(make_facture(), champs).statut == "a_verifier"
    relaxed = InvoiceChecker(confidence_threshold=0.7)
    assert relaxed.check(make_facture(), champs).statut == "validee_auto"


def test_negative_amount_is_flagged():
    decision = InvoiceChecker().check(make_facture(tva=Decimal("-5.00")), make_champs())
    assert kinds(decision) == {"incoherence_montant"}