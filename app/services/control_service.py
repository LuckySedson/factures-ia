import time
from dataclasses import dataclass

from app.db.connection import Database
from app.db.models import Facture
from app.db.repositories.anomalies import AnomalieRepository
from app.db.repositories.champs import ChampRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.controls import AnomalyDraft, DuplicateMatch, InvoiceChecker
from app.services.errors import (
    DocumentNotFoundError,
    ExtractionRequiredError,
    FactureLockedError,
)

LOCKED_STATUSES = ("validee_manuelle", "rejetee")


@dataclass(frozen=True)
class ControlOutcome:
    document_id: int
    facture_id: int
    statut: str
    score_global: float | None
    anomalies: list[AnomalyDraft]


class ControlService:
    def __init__(self, db: Database, checker: InvoiceChecker | None = None):
        self._db = db
        self._checker = checker or InvoiceChecker()

    def run(self, document_id: int) -> ControlOutcome:
        started = time.perf_counter()
        with self._db.connection() as conn:
            if DocumentRepository(conn).get_by_id(document_id) is None:
                raise DocumentNotFoundError(f"Document {document_id} introuvable")
            factures = FactureRepository(conn)
            facture = factures.get_by_document_id(document_id)
            if facture is None:
                raise DocumentNotFoundError(
                    f"Aucune facture pour le document {document_id}"
                )
            if facture.statut in LOCKED_STATUSES:
                raise FactureLockedError(
                    f"Facture {facture.id} déjà traitée manuellement ({facture.statut})"
                )
            champs = ChampRepository(conn).list_by_facture(facture.id)
            if not champs:
                raise ExtractionRequiredError(
                    f"Extraction non réalisée pour le document {document_id}"
                )

            duplicate = self._find_duplicate(factures, facture)
            decision = self._checker.check(facture, champs, duplicate)

            anomalies = AnomalieRepository(conn)
            anomalies.delete_open(facture.id)
            for draft in decision.anomalies:
                anomalies.add(
                    facture.id, draft.type_anomalie, draft.details, draft.facture_liee_id
                )
            factures.update_status(facture.id, decision.statut)

            logs = LogRepository(conn)
            kinds = ",".join(item.type_anomalie for item in decision.anomalies) or "aucune"
            logs.add(
                "VERIFICATION_METIER",
                "succes",
                facture_id=facture.id,
                temps_execution_ms=int((time.perf_counter() - started) * 1000),
                details=f"statut={decision.statut}, anomalies={kinds}",
            )
            factures.set_duration(facture.id, logs.total_time_ms(facture.id))

        score = round(facture.score_confiance, 2) if facture.score_confiance is not None else None
        return ControlOutcome(
            document_id=document_id,
            facture_id=facture.id,
            statut=decision.statut,
            score_global=score,
            anomalies=decision.anomalies,
        )

    @staticmethod
    def _find_duplicate(
        factures: FactureRepository, facture: Facture
    ) -> DuplicateMatch | None:
        if facture.fournisseur_id is None:
            return None
        if facture.numero_facture:
            match = factures.find_same_number(
                facture.id, facture.fournisseur_id, facture.numero_facture
            )
            if match:
                return DuplicateMatch(
                    match.id,
                    f"Même fournisseur et même numéro que la facture {match.id}",
                )
        if facture.montant_ttc is not None and facture.date_facture is not None:
            match = factures.find_same_amount_and_date(
                facture.id,
                facture.fournisseur_id,
                facture.montant_ttc,
                facture.date_facture,
            )
            if match:
                return DuplicateMatch(
                    match.id,
                    f"Même fournisseur, même montant TTC et même date que la facture {match.id}",
                )
        return None