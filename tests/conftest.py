from contextlib import contextmanager

import pytest

from app.config import get_settings
from app.db.connection import Database


class SingleConnectionDb:
    def __init__(self, conn):
        self._conn = conn

    @contextmanager
    def connection(self, timeout=10.0):
        yield self._conn


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