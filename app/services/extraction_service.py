import time
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.db.connection import Database
from app.db.repositories.champs import ChampRepository
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.fournisseurs import FournisseurRepository
from app.db.repositories.logs import LogRepository
from app.services.errors import DocumentNotFoundError, OcrRequiredError
from app.services.extraction.base import FIELD_NAMES, FieldValue
from app.services.extraction.normalizers import normalize_supplier
from app.services.extraction.pipeline import ExtractionPipeline


@dataclass(frozen=True)
class ExtractionOutcome:
    document_id: int
    facture_id: int
    champs: dict[str, FieldValue]
    score_global: float
    deja_realise: bool


class ExtractionService:
    def __init__(self, db: Database, pipeline: ExtractionPipeline):
        self._db = db
        self._pipeline = pipeline

    def run(self, document_id: int, force: bool = False) -> ExtractionOutcome:
        with self._db.connection() as conn:
            document = DocumentRepository(conn).get_by_id(document_id)
            if document is None:
                raise DocumentNotFoundError(f"Document {document_id} introuvable")
            facture = FactureRepository(conn).get_by_document_id(document_id)
            if facture is None:
                raise DocumentNotFoundError(
                    f"Aucune facture pour le document {document_id}"
                )
            existing = ChampRepository(conn).list_by_facture(facture.id)

        if existing and not force:
            champs = {
                champ.nom_champ: FieldValue(
                    champ.valeur_extraite, round(champ.confiance or 0.0, 2), champ.methode
                )
                for champ in existing
            }
            return self._outcome(document_id, facture.id, champs, True)

        if document.texte_ocr is None:
            raise OcrRequiredError(f"OCR non réalisé pour le document {document_id}")

        started = time.perf_counter()
        champs = self._pipeline.run(document.texte_ocr)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        score = min(champ.confiance for champ in champs.values())

        with self._db.connection() as conn:
            fournisseur_id = self._supplier_id(conn, champs["fournisseur"].valeur)
            FactureRepository(conn).update_extraction(
                facture_id=facture.id,
                fournisseur_id=fournisseur_id,
                numero_facture=champs["numero_facture"].valeur,
                date_facture=self._to_date(champs["date_facture"].valeur),
                montant_ht=self._to_decimal(champs["montant_ht"].valeur),
                tva=self._to_decimal(champs["tva"].valeur),
                montant_ttc=self._to_decimal(champs["montant_ttc"].valeur),
                score_confiance=score,
            )
            repository = ChampRepository(conn)
            for name in FIELD_NAMES:
                champ = champs[name]
                repository.upsert(
                    facture.id, name, champ.valeur, champ.confiance, champ.methode
                )
            used_llm = any(champ.methode == "llm" for champ in champs.values())
            LogRepository(conn).add(
                "EXTRACTION_LLM" if used_llm else "EXTRACTION_REGEX",
                "succes",
                facture_id=facture.id,
                temps_execution_ms=elapsed_ms,
                details=", ".join(
                    f"{name}={champs[name].methode}:{champs[name].confiance:.2f}"
                    for name in FIELD_NAMES
                ),
            )

        return self._outcome(document_id, facture.id, champs, False)

    @staticmethod
    def _outcome(
        document_id: int,
        facture_id: int,
        champs: dict[str, FieldValue],
        deja_realise: bool,
    ) -> ExtractionOutcome:
        score = min(champ.confiance for champ in champs.values())
        return ExtractionOutcome(document_id, facture_id, champs, score, deja_realise)

    @staticmethod
    def _supplier_id(conn, name: str | None) -> int | None:
        if not name:
            return None
        normalized = normalize_supplier(name)
        if not normalized:
            return None
        return FournisseurRepository(conn).get_or_create(name, normalized)

    @staticmethod
    def _to_date(value: str | None) -> date | None:
        return date.fromisoformat(value) if value else None

    @staticmethod
    def _to_decimal(value: str | None) -> Decimal | None:
        return Decimal(value) if value else None