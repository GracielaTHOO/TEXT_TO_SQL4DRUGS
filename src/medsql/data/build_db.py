"""Construction de la base SQLite à partir des fichiers bruts de la BDPM."""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path

from medsql.data import normalize as n
from medsql.data.schema import TABLES, TABLES_BY_NAME

logger = logging.getLogger(__name__)

Row = tuple[object, ...]
RowParser = Callable[[list[str | None]], Iterable[tuple[str, Row]]]


def _fields(line: str, width: int) -> list[str | None]:
    """Découpe une ligne tabulée en exactement ``width`` champs nettoyés."""
    parts: list[str | None] = [n.clean(p) for p in line.rstrip("\r\n").split("\t")]
    if len(parts) > width:
        # Champ texte final contenant des tabulations : on le recolle.
        head = parts[: width - 1]
        tail = " ".join(p for p in parts[width - 1 :] if p)
        parts = [*head, tail or None]
    return parts + [None] * (width - len(parts))


def _cis(value: str | None) -> int | None:
    return n.parse_int(value)


def parse_cis(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    cis = _cis(f[0])
    if cis is None:
        return
    yield (
        "medicaments",
        (
            cis,
            f[1],
            f[2],
            f[3],
            f[4],
            f[5],
            f[6],
            n.parse_date(f[7]),
            f[8],
            f[9],
            f[10],
            n.parse_bool(f[11]),
        ),
    )
    for route in n.split_routes(f[3]):
        yield "medicament_voies", (cis, route)


def parse_cip(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    if f[6] is None:
        return
    yield (
        "presentations",
        (
            f[6],
            f[1],
            _cis(f[0]),
            f[2],
            f[3],
            f[4],
            n.parse_date(f[5]),
            n.parse_bool(f[7]),
            n.parse_rate(f[8]),
            n.parse_price(f[9]),
            n.parse_price(f[10]),
            n.parse_price(f[11]),
            f[12],
        ),
    )


def parse_compo(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    yield (
        "compositions",
        (_cis(f[0]), f[1], n.parse_int(f[2]), f[3], f[4], f[5], f[6], n.parse_int(f[7])),
    )


def parse_gener(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    code = n.parse_int(f[3])
    yield (
        "groupes_generiques",
        (n.parse_int(f[0]), f[1], _cis(f[2]), code, n.generic_label(code), n.parse_int(f[4])),
    )


def _parse_has(table: str) -> RowParser:
    def parser(f: list[str | None]) -> Iterator[tuple[str, Row]]:
        yield table, (_cis(f[0]), f[1], f[2], n.parse_date(f[3]), f[4], f[5])

    return parser


def parse_cpd(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    yield "conditions_prescription", (_cis(f[0]), f[1])


def parse_dispo(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    yield (
        "disponibilites",
        (
            _cis(f[0]),
            f[1],
            n.parse_int(f[2]),
            f[3],
            n.parse_date(f[4]),
            n.parse_date(f[5]),
            n.parse_date(f[6]),
            f[7],
        ),
    )


def parse_mitm(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    yield "mitm", (_cis(f[0]), f[1], f[2], f[3])


def parse_info(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    yield "informations_importantes", (_cis(f[0]), n.parse_date(f[1]), n.parse_date(f[2]), f[3])


def parse_liens_ct(f: list[str | None]) -> Iterator[tuple[str, Row]]:
    if f[0] is not None:
        yield "liens_avis_ct", (f[0], f[1])


@dataclass(frozen=True)
class SourceSpec:
    width: int
    parser: RowParser


SOURCES: dict[str, SourceSpec] = {
    "CIS_bdpm.txt": SourceSpec(12, parse_cis),
    "CIS_CIP_bdpm.txt": SourceSpec(13, parse_cip),
    "CIS_COMPO_bdpm.txt": SourceSpec(8, parse_compo),
    "CIS_GENER_bdpm.txt": SourceSpec(5, parse_gener),
    "CIS_HAS_SMR_bdpm.txt": SourceSpec(6, _parse_has("avis_smr")),
    "CIS_HAS_ASMR_bdpm.txt": SourceSpec(6, _parse_has("avis_asmr")),
    "CIS_CPD_bdpm.txt": SourceSpec(2, parse_cpd),
    "CIS_CIP_Dispo_Spec.txt": SourceSpec(8, parse_dispo),
    "CIS_MITM.txt": SourceSpec(4, parse_mitm),
    "CIS_InfoImportantes.txt": SourceSpec(4, parse_info),
    "HAS_LiensPageCT_bdpm.txt": SourceSpec(2, parse_liens_ct),
}


@dataclass
class BuildReport:
    rows: dict[str, int] = field(default_factory=dict)
    skipped_lines: dict[str, int] = field(default_factory=dict)
    missing_files: list[str] = field(default_factory=list)


def _create_schema(conn: sqlite3.Connection) -> None:
    for table in TABLES:
        conn.execute(f"DROP TABLE IF EXISTS {table.name}")
        conn.execute(table.ddl())


def _create_indexes(conn: sqlite3.Connection) -> None:
    for table in TABLES:
        for cols in table.indexes:
            name = f"idx_{table.name}_{'_'.join(cols)}"
            conn.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table.name} ({', '.join(cols)})")


def build_database(raw_dir: Path, db_path: Path) -> BuildReport:
    """Charge chaque fichier source dans SQLite et renvoie un rapport de volumétrie.

    La base est construite dans un fichier temporaire puis renommée : une construction
    interrompue ne laisse jamais de base à moitié remplie.
    """
    report = BuildReport()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = db_path.with_suffix(".tmp")
    tmp_path.unlink(missing_ok=True)

    conn = sqlite3.connect(tmp_path)
    try:
        _create_schema(conn)
        for file_name, spec in SOURCES.items():
            path = raw_dir / file_name
            if not path.exists():
                report.missing_files.append(file_name)
                logger.warning("Fichier absent : %s", path)
                continue
            _load_file(conn, path, spec, report)
        _create_indexes(conn)
        conn.commit()
        report.rows = {
            t.name: conn.execute(f"SELECT COUNT(*) FROM {t.name}").fetchone()[0] for t in TABLES
        }
        conn.execute("ANALYZE")
        conn.commit()
    finally:
        conn.close()
    tmp_path.replace(db_path)
    return report


def _load_file(conn: sqlite3.Connection, path: Path, spec: SourceSpec, report: BuildReport) -> None:
    buffers: dict[str, list[Row]] = {}
    skipped = 0
    for line in n.decode(path.read_bytes()).splitlines():
        if not line.strip():
            continue
        produced = False
        for table, row in spec.parser(_fields(line, spec.width)):
            buffers.setdefault(table, []).append(row)
            produced = True
        skipped += not produced
    for table, rows in buffers.items():
        cols = TABLES_BY_NAME[table].column_names
        placeholders = ", ".join("?" * len(cols))
        # OR IGNORE : la BDPM contient quelques doublons exacts sur les clés primaires.
        sql = f"INSERT OR IGNORE INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
        conn.executemany(sql, rows)
    if skipped:
        report.skipped_lines[path.name] = skipped
