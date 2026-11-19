import uuid
from contextlib import contextmanager
from pathlib import Path

import pytest

from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.documents import DocumentService
from app.services.errors import UnsupportedFileTypeError
from app.services.storage import StorageService

JPG_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "tests" / "facture_scan_002.jpg"
)


class SingleConnectionDb:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self, timeout=10.0):
        yield self._conn


@pytest.fixture
def service(conn, tmp_path):
    storage = StorageService(tmp_path, max_bytes=5 * 1024 * 1024)
    return DocumentService(SingleConnectionDb(conn), storage)


def unique_image() -> bytes:
    return JPG_FILE.read_bytes() + uuid.uuid4().bytes


def test_new_file_is_received(service, conn, tmp_path):
    result = service.receive(unique_image(), "scan.jpg")
    assert result.statut == "recu"
    assert result.type_document == "image"
    assert (tmp_path / f"{result.sha256}.jpg").exists()

    document = DocumentRepository(conn).get_by_hash(result.sha256)
    assert document.nom_fichier_original == "scan.jpg"
    facture = FactureRepository(conn).get_by_document_id(document.id)
    assert facture.id == result.facture_id
    assert facture.statut == "en_attente"

    logs = LogRepository(conn).list_by_facture(facture.id)
    assert [entry.etape for entry in logs] == ["RECEPTION"]
    assert logs[0].statut_execution == "succes"
    assert logs[0].temps_execution_ms >= 0


def test_exact_duplicate_is_detected(service, conn, tmp_path):
    content = unique_image()
    first = service.receive(content, "scan.jpg")
    second = service.receive(content, "copie_du_scan.jpg")

    assert second.statut == "doublon_exact"
    assert second.document_id == first.document_id
    assert second.facture_id == first.facture_id
    assert second.nom_fichier == "copie_du_scan.jpg"

    count = conn.execute(
        "SELECT count(*) AS n FROM documents WHERE hash_sha256 = %s",
        (first.sha256,),
    ).fetchone()["n"]
    assert count == 1
    assert len(list(tmp_path.iterdir())) == 1

    log = conn.execute(
        "SELECT details FROM logs_traitement "
        "WHERE facture_id IS NULL ORDER BY id DESC LIMIT 1"
    ).fetchone()
    assert log["details"].startswith("doublon_exact")
    assert str(first.document_id) in log["details"]


def test_unsupported_file_creates_nothing(service, tmp_path):
    with pytest.raises(UnsupportedFileTypeError):
        service.receive(b"ceci n'est pas un fichier valide", "faux.pdf")
    assert list(tmp_path.iterdir()) == []