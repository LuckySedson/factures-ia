import uuid
from pathlib import Path

import pytest

from app.db.repositories.documents import DocumentRepository
from app.db.repositories.logs import LogRepository
from app.services.documents import DocumentService
from app.services.errors import DocumentNotFoundError, OcrError
from app.services.ocr.base import OcrEngine
from app.services.ocr_service import OcrService
from app.services.storage import StorageService

JPG_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "tests" / "facture_scan_002.jpg"
)


class FailingEngine(OcrEngine):
    name = "failing"

    def extract(self, path):
        raise OcrError("moteur en panne")


@pytest.fixture
def storage(tmp_path):
    return StorageService(tmp_path, max_bytes=5 * 1024 * 1024)


@pytest.fixture
def received(fake_db, storage):
    content = JPG_FILE.read_bytes() + uuid.uuid4().bytes
    return DocumentService(fake_db, storage).receive(content, "scan.jpg")


def steps(conn, facture_id):
    logs = LogRepository(conn).list_by_facture(facture_id)
    return [(entry.etape, entry.statut_execution) for entry in logs]


def test_ocr_stores_text_and_logs(fake_db, storage, fake_engine, received, conn):
    outcome = OcrService(fake_db, storage, fake_engine).run(received.document_id)

    assert outcome.deja_realise is False
    assert outcome.engine == "fake"
    assert outcome.nb_caracteres == len(fake_engine.text)
    document = DocumentRepository(conn).get_by_id(received.document_id)
    assert document.texte_ocr == fake_engine.text
    assert steps(conn, received.facture_id) == [
        ("RECEPTION", "succes"),
        ("OCR", "succes"),
    ]
    ocr_log = LogRepository(conn).list_by_facture(received.facture_id)[1]
    assert ocr_log.temps_execution_ms == 5


def test_ocr_is_idempotent(fake_db, storage, fake_engine, received):
    service = OcrService(fake_db, storage, fake_engine)
    service.run(received.document_id)
    second = service.run(received.document_id)
    assert second.deja_realise is True
    assert fake_engine.calls == 1


def test_force_reruns_ocr(fake_db, storage, fake_engine, received):
    service = OcrService(fake_db, storage, fake_engine)
    service.run(received.document_id)
    forced = service.run(received.document_id, force=True)
    assert forced.deja_realise is False
    assert fake_engine.calls == 2


def test_unknown_document_raises(fake_db, storage, fake_engine):
    with pytest.raises(DocumentNotFoundError):
        OcrService(fake_db, storage, fake_engine).run(999999999)


def test_engine_failure_is_logged(fake_db, storage, received, conn):
    with pytest.raises(OcrError):
        OcrService(fake_db, storage, FailingEngine()).run(received.document_id)
    assert steps(conn, received.facture_id) == [
        ("RECEPTION", "succes"),
        ("OCR", "erreur"),
    ]
    assert DocumentRepository(conn).get_by_id(received.document_id).texte_ocr is None


def test_empty_text_is_an_error(fake_db, storage, fake_engine, received, conn):
    fake_engine.text = "   "
    with pytest.raises(OcrError):
        OcrService(fake_db, storage, fake_engine).run(received.document_id)
    assert steps(conn, received.facture_id)[-1] == ("OCR", "erreur")
    assert DocumentRepository(conn).get_by_id(received.document_id).texte_ocr is None


def test_missing_file_is_an_error(fake_db, storage, fake_engine, received, tmp_path):
    (tmp_path / f"{received.sha256}.jpg").unlink()
    with pytest.raises(OcrError):
        OcrService(fake_db, storage, fake_engine).run(received.document_id)