import pytest
from psycopg.errors import CheckViolation, UniqueViolation

from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository

HASH_A = "a" * 64


def make_document(conn, hash_value=HASH_A):
    return DocumentRepository(conn).create(
        nom_fichier_original="facture.pdf",
        chemin_stockage=f"{hash_value}.pdf",
        type_document="pdf_texte",
        hash_sha256=hash_value,
    )


def test_document_create_and_read(conn):
    repo = DocumentRepository(conn)
    doc = make_document(conn)
    assert doc.id > 0
    assert repo.get_by_id(doc.id) == doc
    assert repo.get_by_hash(HASH_A).id == doc.id


def test_document_unknown_returns_none(conn):
    repo = DocumentRepository(conn)
    assert repo.get_by_id(-1) is None
    assert repo.get_by_hash("b" * 64) is None


def test_document_hash_must_be_unique(conn):
    make_document(conn)
    with pytest.raises(UniqueViolation):
        make_document(conn)


def test_document_invalid_type_rejected(conn):
    with pytest.raises(CheckViolation):
        DocumentRepository(conn).create("f.pdf", "x.pdf", "video", "c" * 64)


def test_facture_pending_defaults(conn):
    doc = make_document(conn)
    repo = FactureRepository(conn)
    facture = repo.create_pending(doc.id)
    assert facture.statut == "en_attente"
    assert facture.devise == "MGA"
    assert facture.montant_ttc is None
    assert repo.get_by_document_id(doc.id).id == facture.id


def test_one_facture_per_document(conn):
    doc = make_document(conn)
    repo = FactureRepository(conn)
    repo.create_pending(doc.id)
    with pytest.raises(UniqueViolation):
        repo.create_pending(doc.id)


def test_log_add_and_list(conn):
    doc = make_document(conn)
    facture = FactureRepository(conn).create_pending(doc.id)
    logs = LogRepository(conn)
    logs.add("RECEPTION", "succes", facture_id=facture.id, temps_execution_ms=12)
    entries = logs.list_by_facture(facture.id)
    assert len(entries) == 1
    assert entries[0].etape == "RECEPTION"
    assert entries[0].temps_execution_ms == 12


def test_log_without_facture(conn):
    log_id = LogRepository(conn).add(
        "RECEPTION", "erreur", details="doublon exact du document 1"
    )
    assert log_id > 0

def test_create_if_new_returns_document(conn):
    doc = DocumentRepository(conn).create_if_new(
        "f.pdf", f"{'d' * 64}.pdf", "pdf_texte", "d" * 64
    )
    assert doc is not None
    assert doc.hash_sha256 == "d" * 64


def test_create_if_new_returns_none_on_duplicate(conn):
    repo = DocumentRepository(conn)
    first = repo.create_if_new("f.pdf", f"{HASH_A}.pdf", "pdf_texte", HASH_A)
    second = repo.create_if_new("g.pdf", f"{HASH_A}.pdf", "pdf_texte", HASH_A)
    assert first is not None
    assert second is None