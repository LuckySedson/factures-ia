import re

from app.services.extraction.base import FIELD_NAMES, FieldExtractor, FieldValue
from app.services.extraction.normalizers import parse_amount, parse_date

METHOD = "regex"
FLAGS = re.IGNORECASE

CODE = r"[A-Za-z0-9](?:[A-Za-z0-9\-/_.]*[A-Za-z0-9])?"
NUM = (
    r"(\d{1,3}(?:[ \u00a0\u202f.,]\d{3})+(?:[.,]\d{1,2})?"
    r"|\d+(?:[.,]\d{1,2})?)(?!\d)"
)
GAP = r"[\s:|=]{0,10}"
RATE = r"(?:\s*\(?\s*\d{1,2}(?:[.,]\d+)?\s*%\s*\)?)?"

INVOICE_NUMBER_PATTERNS = (
    (re.compile(rf"facture\s*(?:n\s*[°º]|no\.?|num[ée]ro|#)\s*:?\s*({CODE})", FLAGS), 0.9),
    (re.compile(rf"(?:n\s*[°º]|num[ée]ro)\s*(?:de\s+)?facture\s*:?\s*({CODE})", FLAGS), 0.9),
    (re.compile(rf"invoice\s*(?:n\s*[°º]|no\.?|number|#)\s*:?\s*({CODE})", FLAGS), 0.9),
    (re.compile(rf"\bn\s*[°º]\s*:?\s*({CODE})", FLAGS), 0.7),
    (re.compile(r"\b([A-Z]{2,6}-\d{2,4}-\d{2,6})\b"), 0.6),
    (re.compile(r"\b([A-Z]{2,6}-\d{3,})\b"), 0.5),
)

DATE_VALUE = (
    r"(\d{4}-\d{2}-\d{2}"
    r"|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{2,4}"
    r"|\d{1,2}(?:er)?\s+[A-Za-zÀ-ÿ]+\s+\d{4})"
)
DATE_LABELED = re.compile(
    r"\bdate\b(?!\s*(?:d['’]\s*)?(?:[ée]ch[ée]ance|limite|de\s+(?:paiement|livraison|r[èe]glement)))"
    r"(?:\s*(?:de\s+)?(?:facture|facturation|[ée]mission)|\s*d['’]\s*[ée]mission)?"
    rf"\s*:?\s*{DATE_VALUE}",
    FLAGS,
)
DATE_ANY = re.compile(DATE_VALUE, FLAGS)

SUPPLIER_LABELED = re.compile(
    r"(?:fournisseur|vendeur|[ée]metteur|raison\s+sociale|soci[ée]t[ée])\s*[:|]\s*"
    r"(.{2,80}?)"
    r"(?=\s+(?:date|n\s*[°º]|facture|adresse|nif|stat|rcs|t[ée]l|email|description|client|r[ée]f)\b"
    r"|\s*[|\r\n]|$)",
    FLAGS,
)
SUPPLIER_BY_SUFFIX = re.compile(
    r"\b((?:[A-ZÀ-Ý][\w&'’.\-]*\s+){0,3}[A-ZÀ-Ý][\w&'’.\-]*)"
    r"\s+(SARLU|SARL|SASU|SAS|EURL|SUARL|SA|LTD|LLC|INC)\b"
)

AMOUNT_PATTERNS = {
    "montant_ht": (
        re.compile(
            rf"(?:total|montant|sous[\s-]*total)\s*(?:h\.?\s*t\.?|hors[\s-]*taxes?)(?![a-z]){GAP}{NUM}",
            FLAGS,
        ),
    ),
    "tva": (
        re.compile(
            rf"(?<![a-z])(?:montant\s+)?(?:tva|t\.v\.a\.?){RATE}{GAP}{NUM}",
            FLAGS,
        ),
    ),
    "montant_ttc": (
        re.compile(rf"(?:total|montant)\s*t\.?\s*t\.?\s*c\.?(?![a-z]){GAP}{NUM}", FLAGS),
        re.compile(rf"net\s+[àa]\s+payer{GAP}{NUM}", FLAGS),
        re.compile(rf"total\s+[àa]\s+payer{GAP}{NUM}", FLAGS),
        re.compile(rf"(?<![a-z])ttc(?![a-z]){GAP}{NUM}", FLAGS),
    ),
}
PERCENT_AFTER = re.compile(r"\s*%")
GARBLED_AFTER = re.compile(r"\s*[:;]\s*\d")


class RegexExtractor(FieldExtractor):
    name = METHOD

    def extract(self, text: str) -> dict[str, FieldValue]:
        cleaned = text.replace("\r", "")
        return {
            "fournisseur": self._supplier(cleaned),
            "numero_facture": self._invoice_number(cleaned),
            "date_facture": self._date(cleaned),
            "montant_ht": self._amount(cleaned, "montant_ht"),
            "tva": self._amount(cleaned, "tva"),
            "montant_ttc": self._amount(cleaned, "montant_ttc"),
        }

    @staticmethod
    def _missing() -> FieldValue:
        return FieldValue(None, 0.0, METHOD)

    def _supplier(self, text: str) -> FieldValue:
        for match in SUPPLIER_LABELED.finditer(text):
            name = match.group(1).strip(" \t*#_|-:;,.")
            if len(name) >= 2:
                return FieldValue(name, 0.9, METHOD)
        fallback = SUPPLIER_BY_SUFFIX.search(text)
        if fallback:
            return FieldValue(f"{fallback.group(1)} {fallback.group(2)}", 0.5, METHOD)
        return self._missing()

    def _invoice_number(self, text: str) -> FieldValue:
        for pattern, confidence in INVOICE_NUMBER_PATTERNS:
            for match in pattern.finditer(text):
                code = match.group(1)
                if any(char.isdigit() for char in code):
                    return FieldValue(code, confidence, METHOD)
        return self._missing()

    def _date(self, text: str) -> FieldValue:
        for match in DATE_LABELED.finditer(text):
            parsed = parse_date(match.group(1))
            if parsed:
                return FieldValue(parsed.isoformat(), 0.9, METHOD)
        for match in DATE_ANY.finditer(text):
            parsed = parse_date(match.group(1))
            if parsed:
                return FieldValue(parsed.isoformat(), 0.6, METHOD)
        return self._missing()

    def _amount(self, text: str, field: str) -> FieldValue:
        for pattern in AMOUNT_PATTERNS[field]:
            found = None
            for match in pattern.finditer(text):
                after = text[match.end(1) : match.end(1) + 12]
                if PERCENT_AFTER.match(after):
                    continue
                amount = parse_amount(match.group(1))
                if amount is None:
                    continue
                confidence = 0.3 if GARBLED_AFTER.match(after) else 0.9
                found = FieldValue(str(amount), confidence, METHOD)
            if found:
                return found
        return self._missing()


assert set(FIELD_NAMES) == {
    "fournisseur",
    "numero_facture",
    "date_facture",
    "montant_ht",
    "tva",
    "montant_ttc",
}