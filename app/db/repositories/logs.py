from psycopg import Connection
from psycopg.rows import class_row

from app.db.models import ProcessingLog


class LogRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def add(
        self,
        etape: str,
        statut_execution: str,
        facture_id: int | None = None,
        temps_execution_ms: int | None = None,
        details: str | None = None,
    ) -> int:
        row = self._conn.execute(
            "INSERT INTO logs_traitement "
            "(facture_id, etape, temps_execution_ms, statut_execution, details) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (facture_id, etape, temps_execution_ms, statut_execution, details),
        ).fetchone()
        return row["id"]

    def list_by_facture(self, facture_id: int) -> list[ProcessingLog]:
        with self._conn.cursor(row_factory=class_row(ProcessingLog)) as cur:
            cur.execute(
                "SELECT * FROM logs_traitement WHERE facture_id = %s ORDER BY id",
                (facture_id,),
            )
            return cur.fetchall()

    def total_time_ms(self, facture_id: int) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(temps_execution_ms), 0) AS total "
            "FROM logs_traitement WHERE facture_id = %s",
            (facture_id,),
        ).fetchone()
        return int(row["total"])