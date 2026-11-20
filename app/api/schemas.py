from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    statut: Literal["recu", "doublon_exact"]
    document_id: int
    facture_id: int | None
    type_document: str
    sha256: str
    nom_fichier: str


class FactureSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    statut: str
    devise: str
    numero_facture: str | None
    date_facture: date | None
    montant_ht: Decimal | None
    tva: Decimal | None
    montant_ttc: Decimal | None
    score_confiance: float | None


class DocumentResponse(BaseModel):
    id: int
    nom_fichier_original: str
    type_document: str
    hash_sha256: str
    created_at: datetime
    facture: FactureSummary | None

class OcrResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: int
    facture_id: int | None
    engine: str | None
    duration_ms: int | None
    nb_caracteres: int
    apercu: str
    deja_realise: bool

class ChampResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    valeur: str | None
    confiance: float
    methode: str


class ExtractionResponse(BaseModel):
    document_id: int
    facture_id: int
    champs: dict[str, ChampResponse]
    score_global: float
    deja_realise: bool