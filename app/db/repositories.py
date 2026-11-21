from psycopg import Connection
from psycopg.rows import class_row

from app.db.models import Anomalie


class AnomalieRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def delete_open(self, facture_id: int) -> None:
        self._conn.execute(
            "DELETE FROM anomalies WHERE facture_id = %s AND resolue = FALSE",
            (facture_id,),
        )

    def add(
        self,
        facture_id: int,
        type_anomalie: str,
        details: str | None,
        facture_liee_id: int | None = None,
    ) -> None:
        self._conn.execute(
            "INSERT INTO anomalies (facture_id, type_anomalie, details, facture_liee_id) "
            "VALUES (%s, %s, %s, %s)",
            (facture_id, type_anomalie, details, facture_liee_id),
        )

    def list_by_facture(self, facture_id: int) -> list[Anomalie]:
        with self._conn.cursor(row_factory=class_row(Anomalie)) as cur:
            cur.execute(
                "SELECT * FROM anomalies WHERE facture_id = %s ORDER BY id",
                (facture_id,),
            )
            return cur.fetchall()