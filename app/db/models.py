from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass(frozen=True)
class Document:
    id: int
    nom_fichier_original: str
    chemin_stockage: str
    type_document: str
    hash_sha256: str
    texte_ocr: str | None
    created_at: datetime


@dataclass(frozen=True)
class Facture:
    id: int
    document_id: int
    fournisseur_id: int | None
    numero_facture: str | None
    date_facture: date | None
    montant_ht: Decimal | None
    tva: Decimal | None
    montant_ttc: Decimal | None
    devise: str
    statut: str
    score_confiance: float | None
    duree_traitement_ms: int | None
    created_at: datetime
    validated_at: datetime | None


@dataclass(frozen=True)
class ProcessingLog:
    id: int
    facture_id: int | None
    etape: str
    temps_execution_ms: int | None
    statut_execution: str
    details: str | None
    created_at: datetime

@dataclass(frozen=True)
class ChampExtrait:
    id: int
    facture_id: int
    nom_champ: str
    valeur_extraite: str | None
    valeur_corrigee: str | None
    confiance: float | None
    methode: str