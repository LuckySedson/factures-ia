from dataclasses import dataclass

from app.db.connection import Database
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.errors import DocumentNotFoundError, OcrError
from app.services.ocr.base import OcrEngine
from app.services.storage import StorageService

PREVIEW_LENGTH = 500


@dataclass(frozen=True)
class OcrOutcome:
    document_id: int
    facture_id: int | None
    engine: str | None
    duration_ms: int | None
    nb_caracteres: int
    apercu: str
    deja_realise: bool


class OcrService:
    def __init__(self, db: Database, storage: StorageService, engine: OcrEngine):
        self._db = db
        self._storage = storage
        self._engine = engine

    def run(self, document_id: int, force: bool = False) -> OcrOutcome:
        with self._db.connection() as conn:
            document = DocumentRepository(conn).get_by_id(document_id)
            if document is None:
                raise DocumentNotFoundError(f"Document {document_id} introuvable")
            facture = FactureRepository(conn).get_by_document_id(document_id)
        facture_id = facture.id if facture else None

        if document.texte_ocr is not None and not force:
            return OcrOutcome(
                document_id=document_id,
                facture_id=facture_id,
                engine=None,
                duration_ms=None,
                nb_caracteres=len(document.texte_ocr),
                apercu=document.texte_ocr[:PREVIEW_LENGTH],
                deja_realise=True,
            )

        path = self._storage.absolute_path(document.chemin_stockage)
        try:
            if not path.exists():
                raise OcrError("Fichier introuvable dans le stockage")
            result = self._engine.extract(path)
            if not result.text.strip():
                raise OcrError("Aucun texte reconnu dans le document")
        except OcrError as exc:
            self._log_failure(facture_id, str(exc))
            raise

        with self._db.connection() as conn:
            DocumentRepository(conn).update_texte_ocr(document_id, result.text)
            LogRepository(conn).add(
                "OCR",
                "succes",
                facture_id=facture_id,
                temps_execution_ms=result.duration_ms,
                details=f"moteur={result.engine}, {len(result.text)} caractères",
            )

        return OcrOutcome(
            document_id=document_id,
            facture_id=facture_id,
            engine=result.engine,
            duration_ms=result.duration_ms,
            nb_caracteres=len(result.text),
            apercu=result.text[:PREVIEW_LENGTH],
            deja_realise=False,
        )

    def _log_failure(self, facture_id: int | None, message: str) -> None:
        with self._db.connection() as conn:
            LogRepository(conn).add(
                "OCR", "erreur", facture_id=facture_id, details=message[:500]
            )