from psycopg import Connection
from psycopg.rows import class_row

from app.db.models import Facture


class FactureRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def create_pending(self, document_id: int) -> Facture:
        return self._fetch_one(
            "INSERT INTO factures (document_id) VALUES (%s) RETURNING *",
            (document_id,),
        )

    def get_by_id(self, facture_id: int) -> Facture | None:
        return self._fetch_one(
            "SELECT * FROM factures WHERE id = %s", (facture_id,)
        )

    def get_by_document_id(self, document_id: int) -> Facture | None:
        return self._fetch_one(
            "SELECT * FROM factures WHERE document_id = %s", (document_id,)
        )

    def _fetch_one(self, query: str, params: tuple) -> Facture | None:
        with self._conn.cursor(row_factory=class_row(Facture)) as cur:
            cur.execute(query, params)
            return cur.fetchone()