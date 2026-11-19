import time
from dataclasses import dataclass

from app.db.connection import Database
from app.db.repositories.documents import DocumentRepository
from app.db.repositories.factures import FactureRepository
from app.db.repositories.logs import LogRepository
from app.services.storage import InspectedFile, StorageService

STATUT_RECU = "recu"
STATUT_DOUBLON_EXACT = "doublon_exact"


@dataclass(frozen=True)
class ReceptionResult:
    statut: str
    document_id: int
    facture_id: int | None
    type_document: str
    sha256: str
    nom_fichier: str


class DocumentService:
    def __init__(self, db: Database, storage: StorageService):
        self._db = db
        self._storage = storage

    def receive(self, content: bytes, original_name: str) -> ReceptionResult:
        started = time.perf_counter()
        info = self._storage.inspect(content, original_name)

        with self._db.connection() as conn:
            documents = DocumentRepository(conn)
            factures = FactureRepository(conn)
            logs = LogRepository(conn)

            document = documents.create_if_new(
                nom_fichier_original=info.nom_original,
                chemin_stockage=self._storage.relative_path(info),
                type_document=info.type_document,
                hash_sha256=info.sha256,
            )
            if document is None:
                return self._duplicate(info, documents, factures, logs, started)

            facture = factures.create_pending(document.id)
            self._storage.save(content, info)
            logs.add(
                "RECEPTION",
                "succes",
                facture_id=facture.id,
                temps_execution_ms=self._elapsed_ms(started),
                details=f"{info.type_document}, {info.size} octets",
            )
            return ReceptionResult(
                statut=STATUT_RECU,
                document_id=document.id,
                facture_id=facture.id,
                type_document=info.type_document,
                sha256=info.sha256,
                nom_fichier=info.nom_original,
            )

    def _duplicate(
        self,
        info: InspectedFile,
        documents: DocumentRepository,
        factures: FactureRepository,
        logs: LogRepository,
        started: float,
    ) -> ReceptionResult:
        original = documents.get_by_hash(info.sha256)
        facture = factures.get_by_document_id(original.id)
        logs.add(
            "RECEPTION",
            "succes",
            temps_execution_ms=self._elapsed_ms(started),
            details=(
                f"doublon_exact: '{info.nom_original}' "
                f"identique au document {original.id}"
            ),
        )
        return ReceptionResult(
            statut=STATUT_DOUBLON_EXACT,
            document_id=original.id,
            facture_id=facture.id if facture else None,
            type_document=original.type_document,
            sha256=info.sha256,
            nom_fichier=info.nom_original,
        )

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return int((time.perf_counter() - started) * 1000)