"""Disposable query index over the append-only investment observation stream."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, canonical_timestamp, require_text


OBSERVATION_INDEX_SCHEMA = "jaggedthoughts-observation-query-index-v1"
_COLUMNS = (
    "observation_id", "entity_id", "metric_id", "value", "unit",
    "observed_at", "available_at", "source_ref",
)


def _database_path(observations_path: Path) -> Path:
    return observations_path.with_name("observation_index.sqlite3")


def _row_tuple(row: MetricObservation | Mapping[str, Any]) -> tuple[Any, ...]:
    if isinstance(row, MetricObservation):
        payload = row.to_dict()
    else:
        payload = row
    return (
        require_text(payload.get("observation_id"), "observation index observation_id"),
        require_text(payload.get("entity_id"), "observation index entity_id").upper(),
        require_text(payload.get("metric_id"), "observation index metric_id"),
        float(payload.get("value")),
        require_text(payload.get("unit") or "unknown", "observation index unit"),
        canonical_timestamp(payload.get("observed_at"), "observation index observed_at"),
        canonical_timestamp(payload.get("available_at"), "observation index available_at"),
        require_text(payload.get("source_ref"), "observation index source_ref"),
    )


def _csv_rows(path: Path) -> Iterable[Mapping[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_observation_index(
    observations_path: str | Path,
    observations: Iterable[MetricObservation | Mapping[str, Any]] | None = None,
    *,
    as_of: str,
) -> dict[str, Any]:
    """Atomically replace the disposable index from the exact current CSV epoch."""

    source = Path(observations_path).expanduser().resolve()
    epoch = canonical_timestamp(as_of, "observation index as_of")
    stat = source.stat()
    destination = _database_path(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".tmp", delete=False,
    ) as handle:
        temporary = Path(handle.name)
    temporary.unlink()
    count = 0
    try:
        with sqlite3.connect(temporary) as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=OFF;
                PRAGMA synchronous=OFF;
                PRAGMA temp_store=MEMORY;
                CREATE TABLE observation (
                    observation_id TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    metric_id TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    observed_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    source_ref TEXT NOT NULL
                );
                CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL) WITHOUT ROWID;
                """
            )
            rows = observations if observations is not None else _csv_rows(source)
            batch: list[tuple[Any, ...]] = []
            for row in rows:
                batch.append(_row_tuple(row))
                if len(batch) == 10_000:
                    connection.executemany(
                        "INSERT INTO observation VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch,
                    )
                    count += len(batch)
                    batch.clear()
            if batch:
                connection.executemany(
                    "INSERT INTO observation VALUES (?, ?, ?, ?, ?, ?, ?, ?)", batch,
                )
                count += len(batch)
            connection.executescript(
                """
                CREATE INDEX observation_lookup
                    ON observation(metric_id, entity_id, available_at, observed_at, observation_id);
                """
            )
            metadata = {
                "schema": OBSERVATION_INDEX_SCHEMA,
                "as_of": epoch,
                "observation_count": str(count),
                "source_size": str(stat.st_size),
                "source_mtime_ns": str(stat.st_mtime_ns),
                "source_sha256": _file_sha256(source),
            }
            connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)", sorted(metadata.items()),
            )
        final_stat = source.stat()
        if (final_stat.st_size, final_stat.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
            raise RuntimeError("observation stream changed while its query index was building")
        temporary.replace(destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    body = {
        "schema": OBSERVATION_INDEX_SCHEMA,
        "as_of": epoch,
        "observation_count": count,
        "source_size": stat.st_size,
        "source_mtime_ns": stat.st_mtime_ns,
        "source_sha256": metadata["source_sha256"],
        "path": destination.as_posix(),
        "authority": "disposable_query_projection",
    }
    return {**body, "index_sha256": stable_sha256(body)}


def _index_matches(source: Path, connection: sqlite3.Connection) -> bool:
    try:
        metadata = dict(connection.execute("SELECT key, value FROM metadata"))
        stat = source.stat()
    except (OSError, sqlite3.Error):
        return False
    return (
        metadata.get("schema") == OBSERVATION_INDEX_SCHEMA
        and metadata.get("source_size") == str(stat.st_size)
        and metadata.get("source_mtime_ns") == str(stat.st_mtime_ns)
    )


def observation_source_sha256(observations_path: str | Path) -> str:
    """Reuse the source digest bound by a matching index, or hash the CSV once."""

    source = Path(observations_path).expanduser().resolve()
    index = _database_path(source)
    if index.is_file():
        try:
            with sqlite3.connect(f"file:{index}?mode=ro", uri=True) as connection:
                if _index_matches(source, connection):
                    value = dict(connection.execute(
                        "SELECT key, value FROM metadata"
                    )).get("source_sha256")
                    if value:
                        return str(value)
        except sqlite3.Error:
            pass
    stat = source.stat()
    digest = _file_sha256(source)
    after = source.stat()
    if (after.st_size, after.st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
        raise RuntimeError("observation stream changed while hashing")
    return digest


def _where(
    *, as_of: str, entity_ids: Iterable[str] | None, metric_ids: Iterable[str] | None,
) -> tuple[str, list[str]]:
    clauses = ["available_at <= ?", "observed_at <= ?"]
    parameters = [as_of, as_of]
    entities = sorted({str(value).upper() for value in entity_ids or () if str(value)})
    metrics = sorted({str(value) for value in metric_ids or () if str(value)})
    if entities:
        clauses.append(f"entity_id IN ({','.join('?' for _ in entities)})")
        parameters.extend(entities)
    if metrics:
        clauses.append(f"metric_id IN ({','.join('?' for _ in metrics)})")
        parameters.extend(metrics)
    return " AND ".join(clauses), parameters


def load_observation_rows(
    observations_path: str | Path,
    *,
    as_of: str,
    entity_ids: Iterable[str] | None = None,
    metric_ids: Iterable[str] | None = None,
    effective_per_observed: bool = False,
    latest_per_metric: bool = False,
    strict: bool = False,
) -> tuple[dict[str, Any], ...]:
    """Query the current index, falling back to the CSV if its epoch does not match."""

    if effective_per_observed and latest_per_metric:
        raise ValueError("observation query accepts only one revision projection")
    source = Path(observations_path).expanduser().resolve()
    cutoff = canonical_timestamp(as_of, "observation query as_of")
    where, parameters = _where(
        as_of=cutoff, entity_ids=entity_ids, metric_ids=metric_ids,
    )
    partition = (
        "entity_id, metric_id" if latest_per_metric else
        "entity_id, metric_id, observed_at" if effective_per_observed else ""
    )
    columns = ", ".join(_COLUMNS)
    query = f"SELECT {columns} FROM observation WHERE {where}"
    if partition:
        query = (
            f"WITH ranked AS (SELECT {columns}, ROW_NUMBER() OVER ("
            f"PARTITION BY {partition} ORDER BY available_at DESC, observed_at DESC, "
            f"observation_id DESC) AS revision_rank FROM observation WHERE {where}) "
            f"SELECT {columns} FROM ranked WHERE revision_rank = 1"
        )
    index = _database_path(source)
    if index.is_file():
        try:
            with sqlite3.connect(f"file:{index}?mode=ro", uri=True) as connection:
                connection.row_factory = sqlite3.Row
                if _index_matches(source, connection):
                    rows = tuple(dict(row) for row in connection.execute(query, parameters))
                    if _index_matches(source, connection):
                        return rows
        except sqlite3.Error:
            pass

    wanted_entities = {str(value).upper() for value in entity_ids or () if str(value)}
    wanted_metrics = {str(value) for value in metric_ids or () if str(value)}
    selected: list[dict[str, Any]] = []
    for row_number, raw in enumerate(_csv_rows(source), start=2):
        raw_entity = str(raw.get("entity_id") or "").upper()
        raw_metric = str(raw.get("metric_id") or "")
        if (
            (wanted_entities and raw_entity not in wanted_entities)
            or (wanted_metrics and raw_metric not in wanted_metrics)
        ):
            continue
        try:
            row = dict(zip(_COLUMNS, _row_tuple(raw), strict=True))
        except (TypeError, ValueError) as error:
            if strict:
                raise ValueError(f"invalid observations CSV row {row_number}: {error}") from error
            continue
        if (
            row["available_at"] > cutoff or row["observed_at"] > cutoff
        ):
            continue
        selected.append(row)
    if not partition:
        return tuple(selected)
    key_fields = (
        ("entity_id", "metric_id") if latest_per_metric
        else ("entity_id", "metric_id", "observed_at")
    )
    latest: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in selected:
        key = tuple(str(row[field]) for field in key_fields)
        current = latest.get(key)
        if current is None or (
            row["available_at"], row["observed_at"], row["observation_id"]
        ) > (
            current["available_at"], current["observed_at"], current["observation_id"]
        ):
            latest[key] = row
    return tuple(latest[key] for key in sorted(latest))


__all__ = [
    "OBSERVATION_INDEX_SCHEMA", "build_observation_index", "load_observation_rows",
    "observation_source_sha256",
]
