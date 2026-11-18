import hashlib
import io
from pathlib import Path

import pytest
from PIL import Image

from app.services.errors import FileTooLargeError, UnsupportedFileTypeError
from app.services.storage import StorageService

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "tests"
PDF_FILE = DATA_DIR / "facture_propre_001.pdf"
JPG_FILE = DATA_DIR / "facture_scan_002.jpg"


@pytest.fixture
def storage(tmp_path):
    return StorageService(tmp_path, max_bytes=1024 * 1024)


def test_pdf_with_text_is_detected(storage):
    content = PDF_FILE.read_bytes()
    info = storage.inspect(content, PDF_FILE.name)
    assert info.extension == "pdf"
    assert info.type_document == "pdf_texte"
    assert info.sha256 == hashlib.sha256(content).hexdigest()
    assert info.nom_original == "facture_propre_001.pdf"
    assert info.size == len(content)


def test_jpg_is_detected_as_image(storage):
    info = storage.inspect(JPG_FILE.read_bytes(), JPG_FILE.name)
    assert info.extension == "jpg"
    assert info.type_document == "image"


def test_png_is_detected_as_image(storage):
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50), "white").save(buffer, "PNG")
    info = storage.inspect(buffer.getvalue(), "capture.png")
    assert info.extension == "png"
    assert info.type_document == "image"


def test_pdf_without_text_is_a_scan(storage):
    buffer = io.BytesIO()
    Image.new("RGB", (400, 400), "white").save(buffer, "PDF")
    info = storage.inspect(buffer.getvalue(), "scan.pdf")
    assert info.extension == "pdf"
    assert info.type_document == "pdf_scan"


def test_content_decides_not_extension(storage):
    info = storage.inspect(PDF_FILE.read_bytes(), "photo.jpg")
    assert info.extension == "pdf"


def test_unsupported_content_rejected(storage):
    with pytest.raises(UnsupportedFileTypeError):
        storage.inspect(b"ceci est du texte", "facture.pdf")


def test_empty_file_rejected(storage):
    with pytest.raises(UnsupportedFileTypeError):
        storage.inspect(b"", "vide.pdf")


def test_corrupted_pdf_rejected(storage):
    with pytest.raises(UnsupportedFileTypeError):
        storage.inspect(b"%PDF-1.4 contenu invalide", "casse.pdf")


def test_file_too_large_rejected(tmp_path):
    small = StorageService(tmp_path, max_bytes=100)
    with pytest.raises(FileTooLargeError):
        small.inspect(PDF_FILE.read_bytes(), PDF_FILE.name)


def test_path_in_filename_is_removed(storage):
    info = storage.inspect(JPG_FILE.read_bytes(), "..\\..\\secret\\scan.jpg")
    assert info.nom_original == "scan.jpg"


def test_save_and_delete(storage, tmp_path):
    content = PDF_FILE.read_bytes()
    info = storage.inspect(content, PDF_FILE.name)
    relative = storage.save(content, info)
    assert relative == f"{info.sha256}.pdf"
    assert (tmp_path / relative).read_bytes() == content
    storage.delete(relative)
    assert not (tmp_path / relative).exists()