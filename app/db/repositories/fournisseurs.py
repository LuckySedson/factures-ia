from psycopg import Connection


class FournisseurRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def get_or_create(self, nom: str, nom_normalise: str) -> int:
        row = self._conn.execute(
            "INSERT INTO fournisseurs (nom, nom_normalise) VALUES (%s, %s) "
            "ON CONFLICT (nom_normalise) DO UPDATE SET nom = fournisseurs.nom "
            "RETURNING id",
            (nom, nom_normalise),
        ).fetchone()
        return row["id"]