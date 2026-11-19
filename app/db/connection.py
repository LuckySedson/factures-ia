from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection
from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.config import Settings


class Database:
    def __init__(self, settings: Settings, min_size: int = 1, max_size: int = 5):
        conninfo = make_conninfo(
            host=settings.postgres_host,
            port=settings.postgres_port,
            dbname=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password.get_secret_value(),
        )
        self._pool = ConnectionPool(
            conninfo,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row},
            check=ConnectionPool.check_connection,
            open=False,
        )

    def open(self) -> None:
        self._pool.open(wait=True, timeout=10)

    def close(self) -> None:
        self._pool.close()

    @contextmanager
    def connection(self, timeout: float = 10.0) -> Iterator[Connection]:
        with self._pool.connection(timeout=timeout) as conn:
            yield conn

    def ping(self) -> bool:
        try:
            with self.connection(timeout=3.0) as conn:
                conn.execute("SELECT 1")
            return True
        except Exception:
            return False
