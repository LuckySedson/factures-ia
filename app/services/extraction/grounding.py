import re
from datetime import date
from decimal import Decimal

from app.services.extraction.normalizers import (
    normalize_supplier,
    parse_amount,
    parse_date,
)
from app.services.extraction.regex_extractor import DATE_VALUE, NUM

AMOUNT_TOKEN = re.compile(NUM)
DATE_TOKEN = re.compile(DATE_VALUE, re.IGNORECASE)


def amount_candidates(text: str) -> set[Decimal]:
    amounts: set[Decimal] = set()
    for match in AMOUNT_TOKEN.finditer(text):
        amount = parse_amount(match.group(1))
        if amount is not None:
            amounts.add(amount)
    return amounts


def date_candidates(text: str) -> set[date]:
    dates: set[date] = set()
    for match in DATE_TOKEN.finditer(text):
        parsed = parse_date(match.group(1))
        if parsed is not None:
            dates.add(parsed)
    return dates


def is_text_grounded(value: str, text: str) -> bool:
    needle = normalize_supplier(value)
    return bool(needle) and needle in normalize_supplier(text)