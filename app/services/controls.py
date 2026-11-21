from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.db.models import ChampExtrait, Facture

STATUT_AUTO = "validee_auto"
STATUT_REVIEW = "a_verifier"
STATUT_DUPLICATE = "doublon_suspect"


@dataclass(frozen=True)
class AnomalyDraft:
    type_anomalie: str
    details: str
    facture_liee_id: int | None = None


@dataclass(frozen=True)
class DuplicateMatch:
    facture_id: int
    reason: str


@dataclass(frozen=True)
class ControlDecision:
    statut: str
    anomalies: list[AnomalyDraft]


class InvoiceChecker:
    def __init__(
        self,
        confidence_threshold: float = 0.8,
        amount_tolerance: Decimal = Decimal("1.00"),
    ):
        self._threshold = confidence_threshold
        self._tolerance = amount_tolerance

    def check(
        self,
        facture: Facture,
        champs: Sequence[ChampExtrait],
        duplicate: DuplicateMatch | None = None,
    ) -> ControlDecision:
        anomalies: list[AnomalyDraft] = []
        anomalies += self._missing_fields(facture)
        anomalies += self._amount_checks(facture)
        anomalies += self._low_confidence(facture, champs)
        if duplicate is not None:
            anomalies.append(
                AnomalyDraft("doublon_metier", duplicate.reason, duplicate.facture_id)
            )
        return ControlDecision(self._status(anomalies), anomalies)

    @staticmethod
    def _values(facture: Facture) -> dict:
        return {
            "fournisseur": facture.fournisseur_id,
            "numero_facture": facture.numero_facture,
            "date_facture": facture.date_facture,
            "montant_ht": facture.montant_ht,
            "tva": facture.tva,
            "montant_ttc": facture.montant_ttc,
        }

    def _missing_fields(self, facture: Facture) -> list[AnomalyDraft]:
        missing = [
            name
            for name, value in self._values(facture).items()
            if value is None or (isinstance(value, str) and not value.strip())
        ]
        if not missing:
            return []
        return [AnomalyDraft("champ_manquant", "Champs absents : " + ", ".join(missing))]

    def _amount_checks(self, facture: Facture) -> list[AnomalyDraft]:
        ht, tva, ttc = facture.montant_ht, facture.tva, facture.montant_ttc
        problems: list[str] = []
        for name, value in (("montant_ht", ht), ("tva", tva), ("montant_ttc", ttc)):
            if value is not None and value < 0:
                problems.append(f"{name} négatif ({value})")
        if ttc is not None and ttc == 0:
            problems.append("montant_ttc nul")
        if ht is not None and ttc is not None and ttc < ht - self._tolerance:
            problems.append(f"TTC ({ttc}) inférieur au HT ({ht})")
        if ht is not None and tva is not None and ttc is not None:
            gap = abs(ht + tva - ttc)
            if gap > self._tolerance:
                problems.append(f"HT + TVA = {ht + tva} mais TTC = {ttc} (écart {gap})")
        if not problems:
            return []
        return [AnomalyDraft("incoherence_montant", "; ".join(problems))]

    def _low_confidence(
        self, facture: Facture, champs: Sequence[ChampExtrait]
    ) -> list[AnomalyDraft]:
        values = self._values(facture)
        weak = []
        for champ in champs:
            if values.get(champ.nom_champ) is None:
                continue
            confidence = 1.0 if champ.valeur_corrigee is not None else (champ.confiance or 0.0)
            if round(confidence, 2) < self._threshold:
                weak.append(f"{champ.nom_champ}={confidence:.2f}")
        if not weak:
            return []
        return [
            AnomalyDraft(
                "faible_confiance",
                f"Confiance inférieure à {self._threshold:.2f} : " + ", ".join(weak),
            )
        ]

    @staticmethod
    def _status(anomalies: list[AnomalyDraft]) -> str:
        if any(item.type_anomalie == "doublon_metier" for item in anomalies):
            return STATUT_DUPLICATE
        if anomalies:
            return STATUT_REVIEW
        return STATUT_AUTO