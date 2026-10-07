from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from medsql.data.build_db import SOURCES, _fields, build_database
from medsql.data.schema import SOURCE_FILES, TABLES
from tests.conftest import FIXTURES


def test_every_schema_source_has_a_parser() -> None:
    assert set(SOURCE_FILES) == set(SOURCES)


def test_fields_pads_and_merges() -> None:
    assert _fields("a\tb", 4) == ["a", "b", None, None]
    assert _fields("a\tb\tc\td", 3) == ["a", "b", "c d"]
    assert _fields(" a \t\r\n", 2) == ["a", None]


@pytest.fixture
def raw(db_path: Path) -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(db_path)
    yield conn
    conn.close()


def test_build_loads_all_tables(raw: sqlite3.Connection) -> None:
    conn = raw
    for table in TABLES:
        count = conn.execute(f"SELECT COUNT(*) FROM {table.name}").fetchone()[0]
        assert count > 0, table.name


def test_values_are_normalized(raw: sqlite3.Connection) -> None:
    conn = raw
    titulaires, date_amm, sr = conn.execute(
        "SELECT titulaires, date_amm, surveillance_renforcee FROM medicaments WHERE cis = 69000008"
    ).fetchone()
    assert titulaires == "MERCK SHARP & DOHME"  # espace initial supprimé
    assert date_amm == "2015-07-17"
    assert sr == 1
    taux, prix, ttc = conn.execute(
        "SELECT taux_remboursement, prix_euros, prix_ttc_euros FROM presentations WHERE cip13 = '3400955012345'"
    ).fetchone()
    assert (taux, prix, ttc) == (100, 2868.45, 2891.47)
    assert conn.execute(
        "SELECT taux_remboursement FROM presentations WHERE cip13='3400934998331'"
    ).fetchone() == (65,)


def test_routes_are_exploded(raw: sqlite3.Connection) -> None:
    conn = raw
    voies = {r[0] for r in conn.execute("SELECT voie FROM medicament_voies WHERE cis = 61000020")}
    assert voies == {"intraveineuse", "sous-cutanée", "périneurale"}


def test_missing_files_are_reported(tmp_path: Path) -> None:
    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "CIS_bdpm.txt").write_bytes((FIXTURES / "CIS_bdpm.txt").read_bytes())
    report = build_database(raw, tmp_path / "db.sqlite")
    assert report.rows["medicaments"] == 22
    assert "CIS_CIP_bdpm.txt" in report.missing_files


def test_build_is_atomic(tmp_path: Path) -> None:
    db = tmp_path / "db.sqlite"
    build_database(FIXTURES, db)
    assert db.exists()
    assert not db.with_suffix(".tmp").exists()
