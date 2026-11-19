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