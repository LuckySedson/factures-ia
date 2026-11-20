from contextlib import contextmanager

import pytest

from app.config import get_settings
from app.db.connection import Database
from app.services.ocr.base import OcrEngine, OcrResult


class SingleConnectionDb:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self, timeout=10.0):
        yield self._conn


class FakeOcrEngine(OcrEngine):
    name = "fake"

    def __init__(self):
        self.text = "FACTURE N° TEST-001\nTOTAL TTC: 100 Ar"
        self.calls = 0

    def extract(self, path):
        self.calls += 1
        return OcrResult(text=self.text, engine=self.name, duration_ms=5)


@pytest.fixture(scope="session")
def db():
    database = Database(get_settings())
    database.open()
    yield database
    database.close()


@pytest.fixture
def conn(db):
    with db.connection() as connection:
        yield connection
        connection.rollback()


@pytest.fixture
def fake_db(conn):
    return SingleConnectionDb(conn)


@pytest.fixture
def fake_engine():
    return FakeOcrEngine()

SAMPLE_PDF_TEXT = (
    "FACTURE N° FAC-2026-001\n\n"
    "Fournisseur: Tech Solutions SARL Date: 15/11/2026 Description Quantité "
    "Prix Unitaire Total PC Portable Acer Nitro 5 1 3500000 Ar 3500000 Ar "
    "Souris Gamer RGB 2 75000 Ar 150000 Ar TOTAL HT: 3650000 Ar "
    "TVA (20%): 730000 Ar TOTAL TTC: 4380000 Ar"
)

SAMPLE_SCAN_TEXT = (
    "## FAC-2026-002\n\n"
    "Fournisseur: Librairie Universitaire Date: 16/11/2026\n\n"
    "| Description                    | Montant   |\n"
    "|--------------------------------|-----------|\n"
    "| 1x Livre Algorithmique Avancée | 45000 Ar  |\n"
    "| 1x Cahier de notes spiralé     | 5000 Ar   |\n\n"
    "## TOTAL TTC: 5 :50000 Ar"
)

SAMPLE_FR_TEXT = (
    "Établissements RAKOTO SARL\n"
    "Facture N° 2026/0042\n"
    "Date de facture : 3 décembre 2026\n"
    "Date d'échéance : 03/01/2027\n"
    "Montant HT : 1 250 000,50 Ar\n"
    "TVA 20 % : 250 000,10 Ar\n"
    "Net à payer : 1 500 000,60 Ar"
)


@pytest.fixture
def sample_pdf_text():
    return SAMPLE_PDF_TEXT


@pytest.fixture
def sample_scan_text():
    return SAMPLE_SCAN_TEXT


@pytest.fixture
def sample_fr_text():
    return SAMPLE_FR_TEXT