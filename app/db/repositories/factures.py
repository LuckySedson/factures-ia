from psycopg import Connection
from psycopg.rows import class_row
from datetime import date
from decimal import Decimal

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

    def update_extraction(
        self,
        facture_id: int,
        fournisseur_id: int | None,
        numero_facture: str | None,
        date_facture: date | None,
        montant_ht: Decimal | None,
        tva: Decimal | None,
        montant_ttc: Decimal | None,
        score_confiance: float,
    ) -> Facture | None:
        return self._fetch_one(
            "UPDATE factures SET fournisseur_id = %s, numero_facture = %s, "
            "date_facture = %s, montant_ht = %s, tva = %s, montant_ttc = %s, "
            "score_confiance = %s WHERE id = %s RETURNING *",
            (
                fournisseur_id,
                numero_facture,
                date_facture,
                montant_ht,
                tva,
                montant_ttc,
                score_confiance,
                facture_id,
            ),
        )

    def find_same_number(
        self, facture_id: int, fournisseur_id: int, numero_facture: str
    ) -> Facture | None:
        return self._fetch_one(
            "SELECT * FROM factures "
            "WHERE id <> %s AND fournisseur_id = %s "
            "AND upper(btrim(numero_facture)) = upper(btrim(%s)) "
            "AND statut <> 'rejetee' "
            "AND (id < %s OR statut IN ('validee_auto', 'validee_manuelle')) "
            "ORDER BY id LIMIT 1",
            (facture_id, fournisseur_id, numero_facture, facture_id),
        )

    def find_same_amount_and_date(
        self,
        facture_id: int,
        fournisseur_id: int,
        montant_ttc: Decimal,
        date_facture: date,
    ) -> Facture | None:
        return self._fetch_one(
            "SELECT * FROM factures "
            "WHERE id < %s AND fournisseur_id = %s AND montant_ttc = %s "
            "AND date_facture = %s AND statut <> 'rejetee' "
            "ORDER BY id LIMIT 1",
            (facture_id, fournisseur_id, montant_ttc, date_facture),
        )

    def update_status(self, facture_id: int, statut: str) -> Facture | None:
        return self._fetch_one(
            "UPDATE factures SET statut = %s, "
            "validated_at = CASE WHEN %s::text = 'validee_auto' "
            "THEN CURRENT_TIMESTAMP ELSE NULL END "
            "WHERE id = %s RETURNING *",
            (statut, statut, facture_id),
        )

    def set_duration(self, facture_id: int, duree_ms: int) -> None:
        self._conn.execute(
            "UPDATE factures SET duree_traitement_ms = %s WHERE id = %s",
            (duree_ms, facture_id),
        )

    def _fetch_one(self, query: str, params: tuple) -> Facture | None:
        with self._conn.cursor(row_factory=class_row(Facture)) as cur:
            cur.execute(query, params)
            return cur.fetchone()