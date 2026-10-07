from __future__ import annotations

import pytest

from medsql.data import normalize as n


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("09/07/2002", "2002-07-09"),
        ("20190612", "2019-06-12"),
        ("2017-08-24", "2017-08-24"),
        (" 01/01/1996 ", "1996-01-01"),
        ("31/02/2020", None),
        ("", None),
        (None, None),
        ("n/a", None),
    ],
)
def test_parse_date(raw: str | None, expected: str | None) -> None:
    assert n.parse_date(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2,18", 2.18),
        ("1,086,58", 1086.58),
        ("2,868,45", 2868.45),
        ("1 086,58", 1086.58),
        ("1\xa0086,58", 1086.58),
        ("12.5", 12.5),
        ("", None),
        ("abc", None),
    ],
)
def test_parse_price(raw: str, expected: float | None) -> None:
    assert n.parse_price(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("65%", 65), ("65 %", 65), ("100%", 100), ("", None)]
)
def test_parse_rate(raw: str, expected: int | None) -> None:
    assert n.parse_rate(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [("oui", 1), ("Non", 0), ("Oui", 1), ("?", None), (None, None)]
)
def test_parse_bool(raw: str | None, expected: int | None) -> None:
    assert n.parse_bool(raw) == expected


def test_decode_falls_back_to_cp1252() -> None:
    assert n.decode("comprimé".encode("cp1252")) == "comprimé"
    assert n.decode("﻿comprimé".encode()) == "comprimé"


def test_split_routes_dedupes_and_lowercases() -> None:
    assert n.split_routes("orale; Orale;sublinguale") == ["orale", "sublinguale"]
    assert n.split_routes(None) == []


def test_generic_label() -> None:
    assert n.generic_label(0) == "princeps"
    assert n.generic_label(3) is None
