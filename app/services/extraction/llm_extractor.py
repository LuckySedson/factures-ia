import logging
import re
import threading

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.services.extraction.base import FIELD_NAMES, FieldExtractor, FieldValue
from app.services.extraction.grounding import (
    amount_candidates,
    date_candidates,
    is_text_grounded,
)
from app.services.extraction.normalizers import parse_amount, parse_date

logger = logging.getLogger(__name__)

METHOD = "llm"
GROUNDED_CONFIDENCE = 0.75
UNGROUNDED_CONFIDENCE = 0.3
MAX_TEXT_CHARS = 6000
EMPTY_VALUES = {"", "null", "none", "n/a", "inconnu"}

SYSTEM_PROMPT = (
    "Tu extrais des informations d'une facture fournisseur à partir de son texte OCR, "
    "parfois bruité. Réponds uniquement par un objet JSON. Règles : recopie les valeurs "
    "présentes dans le texte, sans rien inventer ni calculer ; si une information est "
    "absente ou illisible, mets null. fournisseur : nom de l'entreprise qui émet la "
    "facture. numero_facture : identifiant de la facture (pas un numéro de client ni de "
    "TVA). date_facture : date d'émission au format AAAA-MM-JJ (les dates du texte sont "
    "écrites jour/mois/année). montant_ht, tva, montant_ttc : nombres écrits sans devise "
    "ni séparateur de milliers, avec un point pour les décimales. tva est le montant de "
    "la taxe, pas son taux."
)


class LlmInvoice(BaseModel):
    model_config = ConfigDict(coerce_numbers_to_str=True)

    fournisseur: str | None
    numero_facture: str | None
    date_facture: str | None
    montant_ht: str | None
    tva: str | None
    montant_ttc: str | None


SCHEMA = LlmInvoice.model_json_schema()


class LlmExtractor(FieldExtractor):
    name = METHOD

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_s: float = 180.0,
        client: httpx.Client | None = None,
    ):
        self._url = base_url.rstrip("/") + "/api/chat"
        self._model = model
        self._timeout = timeout_s
        self._client = client or httpx.Client()
        self._lock = threading.Lock()

    def extract(self, text: str) -> dict[str, FieldValue]:
        try:
            with self._lock:
                content = self._ask(text)
            parsed = LlmInvoice.model_validate_json(content)
        except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as exc:
            logger.warning("Repli LLM indisponible : %s", exc)
            return self._all_missing()
        return self._build(parsed, text)

    def _ask(self, text: str) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Texte OCR de la facture :\n\n{text[:MAX_TEXT_CHARS]}",
                },
            ],
            "stream": False,
            "format": SCHEMA,
            "options": {"temperature": 0},
            "keep_alive": "10m",
        }
        response = self._client.post(self._url, json=body, timeout=self._timeout)
        response.raise_for_status()
        return response.json()["message"]["content"]

    def _build(self, parsed: LlmInvoice, text: str) -> dict[str, FieldValue]:
        amounts = amount_candidates(text)
        dates = date_candidates(text)
        return {
            "fournisseur": self._text_field(parsed.fournisseur, text),
            "numero_facture": self._text_field(parsed.numero_facture, text),
            "date_facture": self._date_field(parsed.date_facture, dates),
            "montant_ht": self._amount_field(parsed.montant_ht, amounts),
            "tva": self._amount_field(parsed.tva, amounts),
            "montant_ttc": self._amount_field(parsed.montant_ttc, amounts),
        }

    @staticmethod
    def _all_missing() -> dict[str, FieldValue]:
        return {name: FieldValue(None, 0.0, METHOD) for name in FIELD_NAMES}

    @staticmethod
    def _text_field(raw: str | None, text: str) -> FieldValue:
        value = (raw or "").strip()
        if value.lower() in EMPTY_VALUES:
            return FieldValue(None, 0.0, METHOD)
        grounded = is_text_grounded(value, text)
        return FieldValue(
            value, GROUNDED_CONFIDENCE if grounded else UNGROUNDED_CONFIDENCE, METHOD
        )

    @staticmethod
    def _date_field(raw: str | None, dates: set) -> FieldValue:
        parsed = parse_date(raw.strip()) if raw else None
        if parsed is None:
            return FieldValue(None, 0.0, METHOD)
        confidence = GROUNDED_CONFIDENCE if parsed in dates else UNGROUNDED_CONFIDENCE
        return FieldValue(parsed.isoformat(), confidence, METHOD)

    @staticmethod
    def _amount_field(raw: str | None, amounts: set) -> FieldValue:
        cleaned = re.sub(r"[^\d.,\s\u00a0\u202f]", "", raw or "")
        amount = parse_amount(cleaned)
        if amount is None:
            return FieldValue(None, 0.0, METHOD)
        confidence = GROUNDED_CONFIDENCE if amount in amounts else UNGROUNDED_CONFIDENCE
        return FieldValue(str(amount), confidence, METHOD)