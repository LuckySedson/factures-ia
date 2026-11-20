from datetime import date
from decimal import Decimal

import pytest

from app.services.extraction.normalizers import (
    normalize_supplier,
    parse_amount,
    parse_date,
)


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3500000", "3500000.00"),
        ("3 500 000", "3500000.00"),
        ("3\u00a0500\u00a0000", "3500000.00"),
        ("3.500.000", "3500000.00"),
        ("3,500,000.00", "3500000.00"),
        ("1 250 000,50", "1250000.50"),
        ("12,5", "12.50"),
        ("5", "5.00"),
    ],
)
def test_parse_amount(raw, expected):
    assert parse_amount(raw) == Decimal(expected)


def test_parse_amount_rejects_garbage():
    assert parse_amount("abc") is None
    assert parse_amount("") is None


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("15/11/2026", date(2026, 11, 15)),
        ("15-11-26", date(2026, 11, 15)),
        ("15.11.2026", date(2026, 11, 15)),
        ("2026-11-15", date(2026, 11, 15)),
        ("3 décembre 2026", date(2026, 12, 3)),
        ("1er janvier 2027", date(2027, 1, 1)),
        ("31/02/2026", None),
        ("hier", None),
        ("15/11/1850", None),
    ],
)
def test_parse_date(raw, expected):
    assert parse_date(raw) == expected


def test_normalize_supplier():
    assert normalize_supplier("  Établissements  RAKOTO, S.A.R.L. ") == (
        "etablissements rakoto s a r l"
    )
    assert normalize_supplier("Tech Solutions SARL") == normalize_supplier(
        "TECH  SOLUTIONS sarl"
    )