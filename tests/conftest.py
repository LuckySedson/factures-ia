import pytest

from app.config import get_settings
from app.db.connection import Database


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