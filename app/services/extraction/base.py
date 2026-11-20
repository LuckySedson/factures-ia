from abc import ABC, abstractmethod
from dataclasses import dataclass

FIELD_NAMES = (
    "fournisseur",
    "numero_facture",
    "date_facture",
    "montant_ht",
    "tva",
    "montant_ttc",
)


@dataclass(frozen=True)
class FieldValue:
    valeur: str | None
    confiance: float
    methode: str


class FieldExtractor(ABC):
    name: str

    @abstractmethod
    def extract(self, text: str) -> dict[str, FieldValue]:
        ...