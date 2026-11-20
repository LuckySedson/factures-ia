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