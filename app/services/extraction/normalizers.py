import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

MONTHS = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}
SPACES = " \u00a0\u202f"
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
NUMERIC_DATE = re.compile(r"(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{2,4})")
TEXT_DATE = re.compile(r"(\d{1,2})(?:er)?\s+([A-Za-zÀ-ÿ]+)\s+(\d{4})")


def parse_amount(raw: str) -> Decimal | None:
    cleaned = raw.strip()
    for char in SPACES:
        cleaned = cleaned.replace(char, "")
    if not cleaned or not re.fullmatch(r"[\d.,]+", cleaned):
        return None

    last_comma = cleaned.rfind(",")
    last_dot = cleaned.rfind(".")
    if last_comma != -1 and last_dot != -1:
        decimal_sep = "," if last_comma > last_dot else "."
    elif last_comma != -1 or last_dot != -1:
        sep = "," if last_comma != -1 else "."
        digits_after = len(cleaned) - cleaned.rfind(sep) - 1
        decimal_sep = sep if cleaned.count(sep) == 1 and digits_after <= 2 else None
    else:
        decimal_sep = None

    if decimal_sep is None:
        normalized = cleaned.replace(".", "").replace(",", "")
    else:
        thousands = "." if decimal_sep == "," else ","
        normalized = cleaned.replace(thousands, "").replace(decimal_sep, ".")

    try:
        return Decimal(normalized).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None


def parse_date(raw: str) -> date | None:
    text = raw.strip()

    iso = ISO_DATE.fullmatch(text)
    if iso:
        year, month, day = (int(part) for part in iso.groups())
        return _safe_date(year, month, day)

    numeric = NUMERIC_DATE.fullmatch(text)
    if numeric:
        day, month, year = (int(part) for part in numeric.groups())
        if year < 100:
            year += 2000
        return _safe_date(year, month, day)

    textual = TEXT_DATE.fullmatch(text)
    if textual:
        month = MONTHS.get(textual.group(2).lower())
        if month:
            return _safe_date(int(textual.group(3)), month, int(textual.group(1)))

    return None


def normalize_supplier(name: str) -> str:
    decomposed = unicodedata.normalize("NFKD", name)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()


def _safe_date(year: int, month: int, day: int) -> date | None:
    if not 1990 <= year <= 2100:
        return None
    try:
        return date(year, month, day)
    except ValueError:
        return None