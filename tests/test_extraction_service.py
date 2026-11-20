import uuid
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.db.repositories.champs import ChampRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.documents import DocumentService
from app.services.errors import DocumentNotFoundError, OcrRequiredError
from app.services.extraction.base import FIELD_NAMES
from app.services.extraction.pipeline import ExtractionPipeline
from app.services.extraction.regex_extractor import RegexExtractor
from app.services.extraction_service import ExtractionService
from app.services.storage import StorageService

JPG_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "tests" / "facture_scan_002.jpg"
)


@pytest.fixture
def service(fake_db):
    return ExtractionService(fake_db, ExtractionPipeline(RegexExtractor()))


@pytest.fixture
def make_document(fake_db, conn, tmp_path):
    storage = StorageService(tmp_path, max_bytes=5 * 1024 * 1024)
    documents = DocumentService(fake_db, storage)

    def _make(text=None):
        content = JPG_FILE.read_bytes() + uuid.uuid4().bytes
        received = documents.receive(content, "scan.jpg")
        if text is not None:
            DocumentRepository(conn).update_texte_ocr(received.document_id, text)
        return received

    return _make


def test_extraction_fills_facture_and_fields(service, make_document, sample_pdf_text, conn):
    received = make_document(sample_pdf_text)
    outcome = service.run(received.document_id)

    assert outcome.deja_realise is False
    assert outcome.score_global == pytest.approx(0.9)
    facture = FactureRepository(conn).get_by_id(received.facture_id)
    assert facture.numero_facture == "FAC-2026-001"
    assert facture.date_facture == date(2026, 11, 15)
    assert facture.montant_ht == Decimal("3650000.00")
    assert facture.tva == Decimal("730000.00")
    assert facture.montant_ttc == Decimal("4380000.00")
    assert facture.fournisseur_id is not None
    assert facture.score_confiance == pytest.approx(0.9, abs=1e-6)

    champs = ChampRepository(conn).list_by_facture(received.facture_id)
    assert sorted(champ.nom_champ for champ in champs) == sorted(FIELD_NAMES)
    logs = LogRepository(conn).list_by_facture(received.facture_id)
    assert (logs[-1].etape, logs[-1].statut_execution) == ("EXTRACTION_REGEX", "succes")


def test_extraction_is_idempotent(service, make_document, sample_pdf_text, conn):
    received = make_document(sample_pdf_text)
    service.run(received.document_id)
    second = service.run(received.document_id)
    assert second.deja_realise is True
    assert second.champs["numero_facture"].valeur == "FAC-2026-001"
    assert len(LogRepository(conn).list_by_facture(received.facture_id)) == 2


def test_force_reruns_extraction(service, make_document, sample_pdf_text, conn):
    received = make_document(sample_pdf_text)
    service.run(received.document_id)
    forced = service.run(received.document_id, force=True)
    assert forced.deja_realise is False
    assert len(ChampRepository(conn).list_by_facture(received.facture_id)) == 6
    assert len(LogRepository(conn).list_by_facture(received.facture_id)) == 3


def test_extraction_requires_ocr(service, make_document):
    received = make_document()
    with pytest.raises(OcrRequiredError):
        service.run(received.document_id)


def test_extraction_unknown_document(service):
    with pytest.raises(DocumentNotFoundError):
        service.run(999999999)


def test_same_supplier_is_reused(service, make_document, sample_pdf_text, conn):
    first = make_document(sample_pdf_text)
    second = make_document(sample_pdf_text.replace("Tech Solutions SARL", "TECH  SOLUTIONS  SARL"))
    service.run(first.document_id)
    service.run(second.document_id)
    factures = FactureRepository(conn)
    assert (
        factures.get_by_id(first.facture_id).fournisseur_id
        == factures.get_by_id(second.facture_id).fournisseur_id
    )