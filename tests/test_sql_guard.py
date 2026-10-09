from __future__ import annotations

import sqlite3

import pytest

from medsql.sql_guard import UnsafeQueryError, extract_sql, run_query, sans_accents, validate


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("```sql\nSELECT 1;\n```", "SELECT 1"),
        ("Voici :\n```SQL\nSELECT 1\n```\nVoilà", "SELECT 1"),
        ("SQL: SELECT 2;", "SELECT 2"),
        ("  SELECT 3  ", "SELECT 3"),
    ],
)
def test_extract_sql(text: str, expected: str) -> None:
    assert extract_sql(text) == expected


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE medicaments",
        "DELETE FROM medicaments",
        "UPDATE medicaments SET cis = 1",
        "INSERT INTO medicaments (cis) VALUES (1)",
        "SELECT 1; DROP TABLE medicaments",
        "PRAGMA table_info(medicaments)",
        "ATTACH DATABASE 'x.db' AS x",
        "CREATE TABLE t (a)",
        "",
        "SELEC * FROM",
        "SELECT 'chaîne non fermée",
        'SELECT "identifiant non fermé',
    ],
)
def test_validate_rejects(sql: str) -> None:
    with pytest.raises(UnsafeQueryError):
        validate(sql)


def test_validate_accepts_cte_and_union() -> None:
    validate("WITH x AS (SELECT 1 AS a) SELECT a FROM x")
    validate("SELECT 1 UNION ALL SELECT 2")


def test_readonly_connection_blocks_writes_even_without_validation(
    conn: sqlite3.Connection,
) -> None:
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM medicaments")


def test_run_query_caps_rows(conn: sqlite3.Connection) -> None:
    result = run_query(conn, "SELECT cis FROM medicaments", max_rows=5)
    assert len(result.rows) == 5
    assert result.truncated
    assert result.columns == ["cis"]


def test_run_query_timeout(conn: sqlite3.Connection) -> None:
    slow = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(TimeoutError):
        run_query(conn, slow, timeout_s=0.2)


def test_sans_accents(conn: sqlite3.Connection) -> None:
    assert sans_accents("Paracétamol") == "PARACETAMOL"
    assert sans_accents(None) is None
    rows = run_query(
        conn, "SELECT COUNT(*) FROM compositions WHERE sans_accents(substance) LIKE '%IBUPROFENE%'"
    ).rows
    assert rows == [(2,)]
