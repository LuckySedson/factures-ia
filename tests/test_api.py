import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_document_service, get_ocr_service
from app.config import Settings, get_settings
from app.main import app
from app.services.documents import DocumentService
from app.services.ocr_service import OcrService
from app.services.storage import StorageService

JPG_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "tests" / "facture_scan_002.jpg"
)
MAX_MB = 1


@pytest.fixture
def client(fake_db, tmp_path, fake_engine):
    storage = StorageService(tmp_path, max_bytes=MAX_MB * 1024 * 1024)
    app.dependency_overrides[get_document_service] = lambda: DocumentService(
        fake_db, storage
    )
    app.dependency_overrides[get_ocr_service] = lambda: OcrService(
        fake_db, storage, fake_engine
    )
    app.dependency_overrides[get_settings] = lambda: Settings(max_upload_mb=MAX_MB)
    yield TestClient(app)
    app.dependency_overrides.clear()


def unique_image() -> bytes:
    return JPG_FILE.read_bytes() + uuid.uuid4().bytes


def post_file(client, content: bytes, name: str = "scan.jpg"):
    return client.post("/documents", files={"file": (name, content)})


def test_post_new_document_returns_201(client):
    response = post_file(client, unique_image())
    assert response.status_code == 201
    body = response.json()
    assert body["statut"] == "recu"
    assert body["type_document"] == "image"
    assert body["facture_id"] is not None


def test_post_duplicate_returns_200(client):
    content = unique_image()
    first = post_file(client, content)
    second = post_file(client, content, name="copie.jpg")
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["statut"] == "doublon_exact"
    assert second.json()["document_id"] == first.json()["document_id"]


def test_post_fake_pdf_returns_415(client):
    response = post_file(client, b"ceci n'est pas un pdf", name="faux.pdf")
    assert response.status_code == 415
    assert "detail" in response.json()


def test_post_too_large_returns_413(client):
    content = b"%PDF-" + b"0" * (MAX_MB * 1024 * 1024 + 10)
    response = post_file(client, content, name="gros.pdf")
    assert response.status_code == 413


def test_post_without_file_returns_422(client):
    assert client.post("/documents").status_code == 422


def test_get_document_returns_details(client):
    created = post_file(client, unique_image()).json()
    response = client.get(f"/documents/{created['document_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["hash_sha256"] == created["sha256"]
    assert body["nom_fichier_original"] == "scan.jpg"
    assert body["facture"]["id"] == created["facture_id"]
    assert body["facture"]["statut"] == "en_attente"
    assert body["facture"]["devise"] == "MGA"
    assert body["facture"]["montant_ttc"] is None


def test_get_unknown_document_returns_404(client):
    assert client.get("/documents/999999999").status_code == 404


def test_get_invalid_id_returns_422(client):
    assert client.get("/documents/abc").status_code == 422


def test_health_with_real_database():
    with TestClient(app) as real_client:
        response = real_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"api": "ok", "database": "ok"}

def test_ocr_route_extracts_text(client, fake_engine):
    created = post_file(client, unique_image()).json()
    response = client.post(f"/documents/{created['document_id']}/ocr")
    assert response.status_code == 200
    body = response.json()
    assert body["engine"] == "fake"
    assert body["nb_caracteres"] == len(fake_engine.text)
    assert body["deja_realise"] is False


def test_ocr_route_is_idempotent(client, fake_engine):
    created = post_file(client, unique_image()).json()
    url = f"/documents/{created['document_id']}/ocr"
    client.post(url)
    second = client.post(url)
    assert second.json()["deja_realise"] is True
    assert fake_engine.calls == 1
    forced = client.post(url, params={"force": "true"})
    assert forced.json()["deja_realise"] is False
    assert fake_engine.calls == 2


def test_ocr_route_unknown_document_returns_404(client):
    assert client.post("/documents/999999999/ocr").status_code == 404


def test_ocr_route_empty_text_returns_422(client, fake_engine):
    fake_engine.text = "   "
    created = post_file(client, unique_image()).json()
    response = client.post(f"/documents/{created['document_id']}/ocr")
    assert response.status_code == 422