import uuid
from pathlib import Path

import pytest

from app.db.repositories.anomalies import AnomalieRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.control_service import ControlService
from app.services.documents import DocumentService
from app.services.errors import (
    DocumentNotFoundError,
    ExtractionRequiredError,
    FactureLockedError,
)
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.regex_extractor import RegexExtractor
from app.services.extraction_service import ExtractionService
from app.services.storage import StorageService

JPG_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "tests" / "facture_scan_002.jpg"
)


@pytest.fixture
def controls(fake_db):
    return ControlService(fake_db)


@pytest.fixture
def make_extracted(fake_db, conn, tmp_path):
    storage = StorageService(tmp_path, max_bytes=5 * 1024 * 1024)
    documents = DocumentService(fake_db, storage)
    extraction = ExtractionService(fake_db, ExtractionPipeline(RegexExtractor()))

    def _make(text, extract=True):
        content = JPG_FILE.read_bytes() + uuid.uuid4().bytes
        received = documents.receive(content, "scan.jpg")
        DocumentRepository(conn).update_texte_ocr(received.document_id, text)
        if extract:
            extraction.run(received.document_id)
        return received

    return _make


def test_clean_pdf_is_auto_validated(controls, make_extracted, sample_pdf_text, conn):
    received = make_extracted(sample_pdf_text)
    outcome = controls.run(received.document_id)

    assert outcome.statut == "validee_auto"
    assert outcome.anomalies == []
    facture = FactureRepository(conn).get_by_id(received.facture_id)
    assert facture.statut == "validee_auto"
    assert facture.validated_at is not None
    assert facture.duree_traitement_ms is not None
    logs = LogRepository(conn).list_by_facture(received.facture_id)
    assert logs[-1].etape == "VERIFICATION_METIER"


def test_garbled_scan_needs_review(controls, make_extracted, sample_scan_text, conn):
    received = make_extracted(sample_scan_text)
    outcome = controls.run(received.document_id)

    assert outcome.statut == "a_verifier"
    kinds = {item.type_anomalie for item in outcome.anomalies}
    assert {"champ_manquant", "faible_confiance"} <= kinds
    stored = AnomalieRepository(conn).list_by_facture(received.facture_id)
    assert {item.type_anomalie for item in stored} == kinds
    assert FactureRepository(conn).get_by_id(received.facture_id).validated_at is None


def test_duplicate_invoice_is_suspect(controls, make_extracted, sample_pdf_text, conn):
    first = make_extracted(sample_pdf_text)
    second = make_extracted(sample_pdf_text)

    assert controls.run(first.document_id).statut == "validee_auto"
    outcome = controls.run(second.document_id)

    assert outcome.statut == "doublon_suspect"
    duplicate = [item for item in outcome.anomalies if item.type_anomalie == "doublon_metier"][0]
    assert duplicate.facture_liee_id == first.facture_id
    stored = FactureRepository(conn).get_by_id(second.facture_id)
    assert stored.statut == "doublon_suspect"
    assert stored.validated_at is None


def test_same_amount_and_date_is_suspect(controls, make_extracted, sample_pdf_text):
    first = make_extracted(sample_pdf_text)
    second = make_extracted(sample_pdf_text.replace("FAC-2026-001", "FAC-2026-777"))

    controls.run(first.document_id)
    outcome = controls.run(second.document_id)

    assert outcome.statut == "doublon_suspect"
    duplicate = [item for item in outcome.anomalies if item.type_anomalie == "doublon_metier"][0]
    assert "montant" in duplicate.details


def test_rerun_replaces_open_anomalies(controls, make_extracted, sample_scan_text, conn):
    received = make_extracted(sample_scan_text)
    controls.run(received.document_id)
    first_count = len(AnomalieRepository(conn).list_by_facture(received.facture_id))
    controls.run(received.document_id)
    assert len(AnomalieRepository(conn).list_by_facture(received.facture_id)) == first_count


def test_controls_require_extraction(controls, make_extracted, sample_pdf_text):
    received = make_extracted(sample_pdf_text, extract=False)
    with pytest.raises(ExtractionRequiredError):
        controls.run(received.document_id)


def test_manually_validated_invoice_is_locked(controls, make_extracted, sample_pdf_text, conn):
    received = make_extracted(sample_pdf_text)
    conn.execute(
        "UPDATE factures SET statut = 'validee_manuelle' WHERE id = %s",
        (received.facture_id,),
    )
    with pytest.raises(FactureLockedError):
        controls.run(received.document_id)


def test_controls_unknown_document(controls):
    with pytest.raises(DocumentNotFoundError):
        controls.run(999999999)