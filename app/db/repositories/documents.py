from psycopg import Connection
from psycopg.rows import class_row

from app.db.models import Document


class DocumentRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def create(
        self,
        nom_fichier_original: str,
        chemin_stockage: str,
        type_document: str,
        hash_sha256: str,
        texte_ocr: str | None = None,
    ) -> Document:
        return self._fetch_one(
            "INSERT INTO documents "
            "(nom_fichier_original, chemin_stockage, type_document, hash_sha256, texte_ocr) "
            "VALUES (%s, %s, %s, %s, %s) RETURNING *",
            (nom_fichier_original, chemin_stockage, type_document, hash_sha256, texte_ocr),
        )

    def create_if_new(
            self,
            nom_fichier_original: str,
            chemin_stockage: str,
            type_document: str,
            hash_sha256: str,
            texte_ocr: str | None = None,
        ) -> Document | None:
            return self._fetch_one(
                "INSERT INTO documents "
                "(nom_fichier_original, chemin_stockage, type_document, hash_sha256, texte_ocr) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (hash_sha256) DO NOTHING RETURNING *",
                (nom_fichier_original, chemin_stockage, type_document, hash_sha256, texte_ocr),
            )

    def get_by_id(self, document_id: int) -> Document | None:
        return self._fetch_one(
            "SELECT * FROM documents WHERE id = %s", (document_id,)
        )

    def get_by_hash(self, hash_sha256: str) -> Document | None:
        return self._fetch_one(
            "SELECT * FROM documents WHERE hash_sha256 = %s", (hash_sha256,)
        )

    def _fetch_one(self, query: str, params: tuple) -> Document | None:
        with self._conn.cursor(row_factory=class_row(Document)) as cur:
            cur.execute(query, params)
            return cur.fetchone()