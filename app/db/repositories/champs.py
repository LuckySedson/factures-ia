from psycopg import Connection
from psycopg.rows import class_row

from app.db.models import ChampExtrait


class ChampRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def upsert(
        self,
        facture_id: int,
        nom_champ: str,
        valeur_extraite: str | None,
        confiance: float,
        methode: str,
    ) -> ChampExtrait:
        with self._conn.cursor(row_factory=class_row(ChampExtrait)) as cur:
            cur.execute(
                "INSERT INTO champs_extraits "
                "(facture_id, nom_champ, valeur_extraite, confiance, methode) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (facture_id, nom_champ) DO UPDATE SET "
                "valeur_extraite = EXCLUDED.valeur_extraite, "
                "valeur_corrigee = NULL, "
                "confiance = EXCLUDED.confiance, "
                "methode = EXCLUDED.methode "
                "RETURNING *",
                (facture_id, nom_champ, valeur_extraite, confiance, methode),
            )
            return cur.fetchone()

    def list_by_facture(self, facture_id: int) -> list[ChampExtrait]:
        with self._conn.cursor(row_factory=class_row(ChampExtrait)) as cur:
            cur.execute(
                "SELECT * FROM champs_extraits WHERE facture_id = %s ORDER BY id",
                (facture_id,),
            )
            return cur.fetchall()