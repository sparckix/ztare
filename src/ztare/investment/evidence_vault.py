"""Point-in-time public evidence archive for sealed investment replay."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import MetricObservation, canonical_timestamp, require_text, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore


EVIDENCE_SNAPSHOT_SCHEMA = "jaggedthoughts-point-in-time-evidence-snapshot-v1"
EVIDENCE_MANIFEST_SCHEMA = "jaggedthoughts-point-in-time-evidence-manifest-v1"
EVIDENCE_RECONSTRUCTION_SCHEMA = "jaggedthoughts-point-in-time-reconstruction-v1"
EVIDENCE_STATUS_SCHEMA = "jaggedthoughts-point-in-time-evidence-status-v1"
EVIDENCE_REF_SCHEMA = "jaggedthoughts-point-in-time-evidence-ref-v1"
EVIDENCE_OWNER = "jaggedthoughts-evidence-vault"
_SNAPSHOT_KIND = "point_in_time_evidence_snapshot"
_MANIFEST_KIND = "point_in_time_evidence_manifest"
_CAPTURE_INDEX_SCHEMA = "jaggedthoughts-evidence-capture-index-v1"
_BLOB_DIGEST_CACHE: dict[tuple[str, int, int, int], str] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def _write_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise ValueError(f"content-addressed evidence changed: {path.name}")
        return
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=f".{path.name}.", delete=False) as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
        temporary = Path(handle.name)
    try:
        os.link(temporary, path)
    except FileExistsError:
        if path.read_bytes() != content:
            raise ValueError(f"content-addressed evidence changed: {path.name}")
    finally:
        temporary.unlink(missing_ok=True)


def _observations(path: Path) -> Iterable[MetricObservation]:
    if not path.is_file():
        return
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            yield MetricObservation(
                observation_id=str(row["observation_id"]),
                entity_id=str(row["entity_id"]), metric_id=str(row["metric_id"]),
                value=float(row["value"]), unit=str(row["unit"]),
                observed_at=str(row["observed_at"]), available_at=str(row["available_at"]),
                source_ref=str(row["source_ref"]),
            )


def _capture_index(root: Path) -> sqlite3.Connection:
    """Open the disposable membership index used to emit observation deltas."""

    path = root / "evidence_vault" / "capture_index.sqlite3"
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE TABLE IF NOT EXISTS captured (
            observation_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            capture_token TEXT NOT NULL,
            seen_token TEXT NOT NULL
        ) WITHOUT ROWID;
        CREATE INDEX IF NOT EXISTS captured_source ON captured(source_id);
        CREATE TABLE IF NOT EXISTS source_head (
            source_id TEXT PRIMARY KEY,
            snapshot_leaf_sha256 TEXT NOT NULL,
            observation_count INTEGER NOT NULL
        ) WITHOUT ROWID;
        """
    )
    schema = dict(connection.execute("SELECT key, value FROM metadata")).get("schema")
    if schema not in (None, _CAPTURE_INDEX_SCHEMA):
        connection.close()
        raise ValueError("unsupported evidence capture-index schema")
    connection.execute(
        "INSERT OR REPLACE INTO metadata(key, value) VALUES ('schema', ?)",
        (_CAPTURE_INDEX_SCHEMA,),
    )
    return connection


def _verified_blob_path(root: Path, payload: Mapping[str, Any]) -> tuple[dict[str, Any], Path]:
    blob = dict(payload.get("observation_segment") or payload.get("observation_set") or {})
    path = (root / require_text(blob.get("path"), "evidence observation blob path")).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise ValueError("observation blob escapes workspace") from error
    before = path.stat()
    key = (str(path), before.st_ino, before.st_size, before.st_mtime_ns)
    digest = _BLOB_DIGEST_CACHE.get(key)
    if digest is None:
        hasher = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                hasher.update(chunk)
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns,
        ):
            raise RuntimeError("evidence observation blob changed while hashing")
        digest = hasher.hexdigest()
        _BLOB_DIGEST_CACHE[key] = digest
    if digest != blob.get("sha256"):
        raise ValueError(f"observation blob hash mismatch: {payload.get('source_id')}")
    return blob, path


def _blob_from_snapshot(root: Path, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    blob, path = _verified_blob_path(root, payload)
    body = json.loads(path.read_text(encoding="utf-8"))
    return blob, body


def _snapshot_chain(
    root: Path, store: GoldenStore, leaf_sha256: str,
) -> tuple[tuple[dict[str, Any], dict[str, Any]], ...]:
    chain: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    current = leaf_sha256
    while current:
        if current in seen:
            raise ValueError("evidence snapshot parent cycle")
        seen.add(current)
        leaf = store.get_leaf(current)
        if leaf.get("leaf_sha256") != current:
            raise ValueError("evidence snapshot leaf hash mismatch")
        payload = dict(leaf.get("payload") or {})
        if payload.get("schema") != EVIDENCE_SNAPSHOT_SCHEMA:
            raise ValueError("unsupported evidence snapshot schema")
        chain.append((payload, _blob_from_snapshot(root, payload)[1]))
        current = str(payload.get("parent_snapshot_leaf_sha256") or "")
    return tuple(chain)


def _sync_capture_source(
    root: Path, store: GoldenStore, connection: sqlite3.Connection,
    *, source_id: str, cutoff: str,
) -> tuple[str | None, int, str | None]:
    """Align a disposable source membership index with the durable Golden head."""

    heads = store.heads_as_of(
        EVIDENCE_OWNER, _SNAPSHOT_KIND, cutoff, object_ids=(source_id,),
    )
    head_sha = str(heads[0]["leaf_sha256"]) if heads else None
    indexed = connection.execute(
        "SELECT snapshot_leaf_sha256, observation_count FROM source_head WHERE source_id = ?",
        (source_id,),
    ).fetchone()
    if indexed and indexed[0] == head_sha:
        payload = dict(store.get_leaf(head_sha)["payload"]) if head_sha else {}
        chain_sha = str(
            payload.get("observation_chain_sha256")
            or (payload.get("observation_set") or {}).get("sha256")
            or ""
        ) or None
        return head_sha, int(indexed[1]), chain_sha

    connection.execute("DELETE FROM captured WHERE source_id = ?", (source_id,))
    connection.execute("DELETE FROM source_head WHERE source_id = ?", (source_id,))
    if not head_sha:
        return None, 0, None
    rows: dict[str, str] = {}
    chain = _snapshot_chain(root, store, head_sha)
    for _, body in reversed(chain):
        for observation_id in body.get("removed_observation_ids") or ():
            rows.pop(require_text(observation_id, "archived removed observation id"), None)
        for raw in body.get("observations") or ():
            observation_id = require_text(raw.get("observation_id"), "archived observation id")
            rows[observation_id] = source_id
    connection.executemany(
        "INSERT INTO captured(observation_id, source_id, capture_token, seen_token) "
        "VALUES (?, ?, 'seed', 'seed')",
        rows.items(),
    )
    payload = chain[0][0]
    count = len(rows)
    declared_count = int(payload.get("cumulative_observation_count") or count)
    if declared_count != count:
        raise ValueError(f"evidence snapshot cumulative count mismatch: {source_id}")
    connection.execute(
        "INSERT INTO source_head VALUES (?, ?, ?)", (source_id, head_sha, count),
    )
    chain_sha = str(
        payload.get("observation_chain_sha256")
        or (payload.get("observation_set") or {}).get("sha256")
        or ""
    ) or None
    return head_sha, count, chain_sha


def _verified_receipt(raw: Mapping[str, Any]) -> dict[str, Any]:
    receipt = dict(raw)
    declared = require_text(receipt.pop("receipt_sha256", None), "source receipt hash")
    if stable_sha256(receipt) != declared:
        raise ValueError(f"source receipt hash mismatch: {receipt.get('source_id')}")
    return {**receipt, "receipt_sha256": declared}


def _leakage_class(availability_mode: str) -> str:
    return {
        "provider_vintage": "provider_vintage_with_capture_floor",
        "provider_filed_date": "provider_filed_date_with_capture_floor",
        "declared_column": "declared_availability_with_capture_floor",
        "declared_lag": "declared_lag_with_capture_floor",
        "retrieval_only": "retrieval_floor",
    }.get(availability_mode, "unverified_availability")


def _range(rows: Iterable[MetricObservation], attr: str) -> dict[str, str | None]:
    first = last = None
    for row in rows:
        value = getattr(row, attr)
        first = value if first is None or value < first else first
        last = value if last is None or value > last else last
    return {"first": first, "last": last}


def capture_public_source_run(
    workspace: str | Path,
    source_run: Mapping[str, Any],
    *,
    ingested_at: str | None = None,
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Archive one completed source run without granting decision authority."""

    root = Path(workspace).expanduser().resolve()
    run = dict(source_run)
    run_sha = require_text(run.pop("run_sha256", None), "source run hash")
    if stable_sha256(run) != run_sha:
        raise ValueError("source run hash mismatch")
    receipts = tuple(sorted(
        (_verified_receipt(row) for row in run.get("source_receipts") or ()),
        key=lambda row: (str(row["source_id"]), str(row["receipt_sha256"])),
    ))
    if not receipts:
        return {"status": "no_source_receipts", "source_run_sha256": run_sha}
    capture_path = root / "evidence_vault" / "latest_capture.json"
    if capture_path.is_file():
        previous_capture = json.loads(capture_path.read_text(encoding="utf-8"))
        if previous_capture.get("source_run_sha256") == run_sha:
            return previous_capture
    clock_authority = "system_clock" if ingested_at is None else "declared_clock"
    ingestion = canonical_timestamp(ingested_at or _utc_now(), "evidence ingested_at")
    if any(timestamp_key(ingestion) < timestamp_key(str(row["retrieved_at"])) for row in receipts):
        raise ValueError("evidence ingestion cannot precede source retrieval")
    rows = _observations(root / "data" / "observations.csv")
    rows_by_source: dict[str, list[MetricObservation]] = {}
    for row in rows:
        rows_by_source.setdefault(row.source_ref, []).append(row)
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    leaves: list[GoldenLeaf] = []
    item_refs: list[dict[str, Any]] = []
    staged_heads: list[tuple[str, str, int]] = []
    with _capture_index(root) as capture_index:
        for receipt in receipts:
            source_id = require_text(receipt.get("source_id"), "source receipt source_id")
            retrieved = canonical_timestamp(receipt.get("retrieved_at"), "source receipt retrieved_at")
            raw_path = (root / require_text(receipt.get("raw_path"), "source receipt raw path")).resolve()
            try:
                raw_path.relative_to(root)
            except ValueError as error:
                raise ValueError("source receipt raw path escapes workspace") from error
            raw_content = raw_path.read_bytes()
            content_sha = hashlib.sha256(raw_content).hexdigest()
            if content_sha != receipt.get("content_sha256"):
                raise ValueError(f"source bytes do not match receipt: {source_id}")
            known_rows = tuple(
                row for row in rows_by_source.get(source_id, ())
                if row.available_at <= retrieved
            )
            parent_sha, prior_count, parent_chain_sha = _sync_capture_source(
                root, store, capture_index, source_id=source_id, cutoff=ingestion,
            )
            capture_token = stable_sha256((run_sha, source_id, ingestion))
            existing_ids = {
                str(row[0]) for row in capture_index.execute(
                    "SELECT observation_id FROM captured WHERE source_id = ?",
                    (source_id,),
                )
            }
            current_ids = {row.observation_id for row in known_rows}
            new_ids = current_ids - existing_ids
            removed_ids = tuple(sorted(existing_ids - current_ids))
            capture_index.executemany(
                "INSERT OR IGNORE INTO captured"
                "(observation_id, source_id, capture_token, seen_token) VALUES (?, ?, ?, ?)",
                (
                    (observation_id, source_id, capture_token, capture_token)
                    for observation_id in new_ids
                ),
            )
            delta_rows = tuple(sorted(
                (row for row in known_rows if row.observation_id in new_ids),
                key=lambda row: (
                    row.entity_id, row.metric_id, row.available_at, row.observation_id,
                ),
            ))
            segment_body = {
                "schema": "jaggedthoughts-point-in-time-observation-set-v2",
                "source_id": source_id,
                "receipt_sha256": receipt["receipt_sha256"],
                "retrieved_at": retrieved,
                "base_snapshot_leaf_sha256": parent_sha,
                "removed_observation_ids": list(removed_ids),
                "observations": [row.to_dict() for row in delta_rows],
            }
            segment_bytes = (
                json.dumps(segment_body, sort_keys=True, separators=(",", ":")) + "\n"
            ).encode()
            segment_sha = hashlib.sha256(segment_bytes).hexdigest()
            segment_relative = Path("evidence_vault") / "observation_segments" / f"{segment_sha}.json"
            _write_once(root / segment_relative, segment_bytes)
            chain_sha = stable_sha256({
                "parent_observation_chain_sha256": parent_chain_sha,
                "observation_segment_sha256": segment_sha,
            })
            cumulative_count = prior_count + len(delta_rows) - len(removed_ids)
            if cumulative_count != len(known_rows):
                raise ValueError(f"evidence capture membership mismatch: {source_id}")
            capture_index.executemany(
                "DELETE FROM captured WHERE observation_id = ? AND source_id = ?",
                ((observation_id, source_id) for observation_id in removed_ids),
            )
            mode = require_text(receipt.get("availability_mode"), "source availability mode")
            payload = {
                "schema": EVIDENCE_SNAPSHOT_SCHEMA,
                "storage_layout": "incremental_observation_segment_v1",
                "source_id": source_id,
                "receipt": receipt,
                "parent_snapshot_leaf_sha256": parent_sha,
                "observation_chain_sha256": chain_sha,
                "cumulative_observation_count": cumulative_count,
                "epochs": {
                    "occurrence": _range(known_rows, "observed_at"),
                    "availability": _range(known_rows, "available_at"),
                    "retrieved_at": retrieved,
                    "ingested_at": ingestion,
                    "ingestion_clock_authority": clock_authority,
                },
                "observation_set": {
                    "path": segment_relative.as_posix(),
                    "sha256": segment_sha,
                    "count": cumulative_count,
                    "encoding": "incremental_v1",
                    "upsert_count": len(delta_rows),
                    "tombstone_count": len(removed_ids),
                },
                "leakage_classification": _leakage_class(mode),
                "replay_floor": ingestion,
                "authority": {
                    "evidence_input": True,
                    "historical_use_before_replay_floor": False,
                    "paper_policy_authority": False,
                    "capital_authority": False,
                },
            }
            leaf = GoldenLeaf(
                owner=EVIDENCE_OWNER, object_kind=_SNAPSHOT_KIND, object_id=source_id,
                epoch=stable_sha256(payload), occurred_at=retrieved, available_at=ingestion,
                payload=payload,
                source_refs=(str(receipt["receipt_sha256"]), f"sha256:{content_sha}"),
            )
            leaves.append(leaf)
            staged_heads.append((source_id, leaf.leaf_sha256, cumulative_count))
            item_refs.append({
                "source_id": source_id, "snapshot_leaf_sha256": leaf.leaf_sha256,
                "receipt_sha256": receipt["receipt_sha256"],
                "observation_segment_sha256": segment_sha,
                "observation_set_sha256": segment_sha,
                "cumulative_observation_count": cumulative_count,
            })
        manifest_payload = {
            "schema": EVIDENCE_MANIFEST_SCHEMA,
            "source_run_sha256": run_sha,
            "source_as_of": canonical_timestamp(run.get("as_of"), "source run as_of"),
            "retrieved_at": canonical_timestamp(run.get("retrieved_at"), "source run retrieved_at"),
            "ingested_at": ingestion,
            "ingestion_clock_authority": clock_authority,
            "snapshots": item_refs,
            "authority": {
                "evidence_input": True,
                "point_in_time_archive": clock_authority == "system_clock",
                "model_latent_knowledge_controlled": False,
                "sufficient_for_alpha_claim": False,
                "paper_policy_authority": False,
                "capital_authority": False,
            },
        }
        manifest = GoldenLeaf(
            owner=EVIDENCE_OWNER, object_kind=_MANIFEST_KIND, object_id=run_sha,
            epoch=stable_sha256(manifest_payload),
            occurred_at=str(manifest_payload["retrieved_at"]), available_at=ingestion,
            payload=manifest_payload,
            source_refs=tuple(str(row["receipt_sha256"]) for row in receipts),
        )
        store.append_bundle(
            (*leaves, manifest),
            tuple(GoldenEdge(manifest.leaf_sha256, row.leaf_sha256, "contains") for row in leaves),
            make_heads=False,
        )
        capture_index.executemany(
            "INSERT INTO source_head(source_id, snapshot_leaf_sha256, observation_count) "
            "VALUES (?, ?, ?) ON CONFLICT(source_id) DO UPDATE SET "
            "snapshot_leaf_sha256=excluded.snapshot_leaf_sha256, "
            "observation_count=excluded.observation_count",
            staged_heads,
        )
    projection = {
        "schema": "jaggedthoughts-point-in-time-evidence-capture-v1",
        "status": "captured",
        "source_run_sha256": run_sha,
        "manifest_leaf_sha256": manifest.leaf_sha256,
        "snapshot_count": len(leaves),
        "ingested_at": ingestion,
        "authority": manifest_payload["authority"],
    }
    _atomic_json(capture_path, projection)
    return projection


def reconstruct_evidence_as_of(
    workspace: str | Path,
    *,
    as_of: str,
    source_ids: Iterable[str] | None = None,
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Rebuild the latest source information set knowable at ``as_of``."""

    root = Path(workspace).expanduser().resolve()
    cutoff = canonical_timestamp(as_of, "evidence reconstruction as_of")
    selected = tuple(sorted({require_text(row, "source id") for row in source_ids or ()}))
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    leaves = store.heads_as_of(
        EVIDENCE_OWNER, _SNAPSHOT_KIND, cutoff, object_ids=selected or None,
    )
    observations: dict[str, dict[str, Any]] = {}
    sources: list[dict[str, Any]] = []
    for leaf in leaves:
        payload = dict(leaf["payload"])
        chain = _snapshot_chain(root, store, str(leaf["leaf_sha256"]))
        for _, body in reversed(chain):
            for observation_id in body.get("removed_observation_ids") or ():
                observations.pop(
                    require_text(observation_id, "archived removed observation id"), None,
                )
            for raw in body.get("observations") or ():
                row = MetricObservation(**raw)
                if timestamp_key(row.available_at) <= timestamp_key(cutoff):
                    observations[row.observation_id] = row.to_dict()
        current_blob_sha = str((payload.get("observation_set") or {}).get("sha256") or "")
        sources.append({
            "source_id": payload["source_id"],
            "snapshot_leaf_sha256": leaf["leaf_sha256"],
            "retrieved_at": payload["epochs"]["retrieved_at"],
            "ingested_at": payload["epochs"]["ingested_at"],
            "ingestion_clock_authority": payload["epochs"]["ingestion_clock_authority"],
            "leakage_classification": payload["leakage_classification"],
            "observation_set_sha256": current_blob_sha,
        })
    found_ids = {str(row["source_id"]) for row in sources}
    missing_ids = sorted(set(selected) - found_ids)
    coverage_complete = bool(sources) and not missing_ids
    archive_authority = coverage_complete and all(
        row["ingestion_clock_authority"] == "system_clock" for row in sources
    )
    body = {
        "schema": EVIDENCE_RECONSTRUCTION_SCHEMA,
        "status": "complete" if coverage_complete else "incomplete",
        "as_of": cutoff,
        "requested_source_ids": list(selected),
        "missing_source_ids": missing_ids,
        "sources": sorted(sources, key=lambda row: row["source_id"]),
        "observations": [observations[key] for key in sorted(observations)],
        "authority": {
            "evidence_replay": (
                "point_in_time_archive" if archive_authority
                else "declared_clock_reconstruction"
            ),
            "model_latent_knowledge_controlled": False,
            "sufficient_for_alpha_claim": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        },
    }
    return {**body, "reconstruction_sha256": stable_sha256(body)}


def _status_snapshot(
    root: Path, store: GoldenStore, item: Mapping[str, Any], *, ingested_at: str,
) -> dict[str, Any]:
    """Verify one captured blob without rebuilding its observation objects."""

    source_id = require_text(item.get("source_id"), "evidence snapshot source id")
    leaf_sha = require_text(
        item.get("snapshot_leaf_sha256"), "evidence snapshot leaf",
    )
    leaf = store.get_leaf(leaf_sha)
    declared_leaf_sha = require_text(
        leaf.pop("leaf_sha256", None), "evidence snapshot declared leaf",
    )
    if declared_leaf_sha != leaf_sha or stable_sha256(leaf) != leaf_sha:
        raise ValueError(f"evidence snapshot leaf hash mismatch: {source_id}")
    payload = dict(leaf.get("payload") or {})
    if stable_sha256(payload) != leaf.get("payload_sha256"):
        raise ValueError(f"evidence snapshot payload hash mismatch: {source_id}")
    if (
        leaf.get("owner") != EVIDENCE_OWNER
        or leaf.get("object_kind") != _SNAPSHOT_KIND
        or leaf.get("object_id") != source_id
        or payload.get("schema") != EVIDENCE_SNAPSHOT_SCHEMA
        or payload.get("source_id") != source_id
        or (payload.get("epochs") or {}).get("ingested_at") != ingested_at
    ):
        raise ValueError(f"evidence snapshot identity mismatch: {source_id}")

    blob, _ = _verified_blob_path(root, payload)
    blob_sha = require_text(blob.get("sha256"), "evidence observation-blob hash")
    if blob.get("encoding") == "incremental_v1":
        if (
            blob_sha != item.get("observation_segment_sha256")
            or blob_sha != item.get("observation_set_sha256")
        ):
            raise ValueError(f"evidence observation-segment lineage mismatch: {source_id}")
        parent_sha = str(payload.get("parent_snapshot_leaf_sha256") or "")
        parent_chain_sha = None
        if parent_sha:
            parent = store.get_leaf(parent_sha)
            parent_payload = dict(parent.get("payload") or {})
            parent_chain_sha = str(
                parent_payload.get("observation_chain_sha256")
                or (parent_payload.get("observation_set") or {}).get("sha256")
                or ""
            ) or None
        expected_chain_sha = stable_sha256({
            "parent_observation_chain_sha256": parent_chain_sha,
            "observation_segment_sha256": blob_sha,
        })
        if (
            payload.get("observation_chain_sha256") != expected_chain_sha
        ):
            raise ValueError(f"evidence observation-chain lineage mismatch: {source_id}")
        count = int(blob.get("count") or 0)
        if count != int(payload.get("cumulative_observation_count") or 0):
            raise ValueError(f"evidence cumulative count lineage mismatch: {source_id}")
    else:
        if blob_sha != item.get("observation_set_sha256"):
            raise ValueError(f"evidence observation-set lineage mismatch: {source_id}")
        count = int(blob.get("count") or 0)
    if count < 0:
        raise ValueError(f"evidence observation count is negative: {source_id}")
    return {
        "source_id": source_id,
        "observation_count": count,
        "ingestion_clock_authority": str(
            (payload.get("epochs") or {}).get("ingestion_clock_authority") or ""
        ),
        "leakage_classification": require_text(
            payload.get("leakage_classification"), "evidence leakage classification",
        ),
    }


def evidence_vault_status(
    workspace: str | Path, *, store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Verify and summarize the latest archived public information set."""

    root = Path(workspace).expanduser().resolve()
    capture_path = root / "evidence_vault" / "latest_capture.json"
    if not capture_path.is_file():
        return {
            "schema": EVIDENCE_STATUS_SCHEMA, "enabled": False,
            "status": "awaiting_first_system_clock_capture",
            "capital_authority": False,
        }
    capture = json.loads(capture_path.read_text(encoding="utf-8"))
    manifest_sha = require_text(
        capture.get("manifest_leaf_sha256"), "evidence manifest leaf",
    )
    store = GoldenStore(store_path or root / "state" / "golden_store.sqlite3")
    manifest_leaf = store.get_leaf(manifest_sha)
    manifest = dict(manifest_leaf.get("payload") or {})
    if manifest.get("schema") != EVIDENCE_MANIFEST_SCHEMA:
        raise ValueError("latest evidence capture does not resolve to an evidence manifest")
    snapshots = tuple(manifest.get("snapshots") or ())
    if len(snapshots) != int(capture.get("snapshot_count") or 0):
        raise ValueError("evidence capture snapshot count does not match its manifest")
    expected = {str(row["snapshot_leaf_sha256"]) for row in snapshots}
    contained = {
        str(row["dst_leaf_sha256"])
        for row in store.list_edges(
            relation="contains", src_leaf_sha256=manifest_sha,
            limit=max(1, len(expected)),
        )
    }
    if contained != expected:
        raise ValueError("evidence manifest containment edges are incomplete")
    ingested_at = canonical_timestamp(
        manifest["ingested_at"], "evidence manifest ingested_at",
    )
    verified = tuple(
        _status_snapshot(root, store, row, ingested_at=ingested_at)
        for row in snapshots
    )
    source_ids = [row["source_id"] for row in verified]
    if len(set(source_ids)) != len(source_ids):
        raise ValueError("evidence manifest contains duplicate source identities")
    archive_authority = bool(verified) and all(
        row["ingestion_clock_authority"] == "system_clock" for row in verified
    )
    authority = {
        "evidence_replay": (
            "point_in_time_archive" if archive_authority
            else "declared_clock_reconstruction"
        ),
        "model_latent_knowledge_controlled": False,
        "sufficient_for_alpha_claim": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    body = {
        "schema": EVIDENCE_STATUS_SCHEMA, "enabled": True,
        "status": "point_in_time_archive_ready",
        "source_run_sha256": manifest["source_run_sha256"],
        "manifest_leaf_sha256": manifest_sha,
        "source_count": len(verified),
        "observation_count": sum(row["observation_count"] for row in verified),
        "ingested_at": ingested_at,
        "ingestion_clock_authority": manifest["ingestion_clock_authority"],
        "missing_source_ids": [],
        "leakage_classes": sorted({
            str(row["leakage_classification"])
            for row in verified
        }),
        "integrity_verified": True,
        "authority": authority,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


def evidence_manifest_ref(
    workspace: str | Path, *, as_of: str,
    required_source_ids: Iterable[str] = (),
    store_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve the latest archived information set covering named sources."""

    root = Path(workspace).expanduser().resolve()
    cutoff = canonical_timestamp(as_of, "evidence ref as_of")
    required = tuple(sorted({
        require_text(value, "required evidence source")
        for value in required_source_ids
    }))
    path = Path(store_path or root / "state" / "golden_store.sqlite3")
    if not path.is_file():
        body = {
            "schema": EVIDENCE_REF_SCHEMA, "as_of": cutoff,
            "status": "archive_unavailable", "required_source_ids": list(required),
            "missing_source_ids": list(required), "manifest_leaf_sha256": None,
            "source_run_sha256": None, "archive_authority": "unarchived_source_packet",
        }
        return {**body, "ref_sha256": stable_sha256(body)}
    store = GoldenStore(path)
    candidates = []
    for metadata in store.list_leaves(
        owner=EVIDENCE_OWNER, object_kind=_MANIFEST_KIND, limit=10_000,
    ):
        if timestamp_key(str(metadata["available_at"])) > timestamp_key(cutoff):
            continue
        leaf = store.get_leaf(str(metadata["leaf_sha256"]))
        payload = dict(leaf.get("payload") or {})
        if payload.get("schema") != EVIDENCE_MANIFEST_SCHEMA:
            continue
        source_ids = {str(row["source_id"]) for row in payload.get("snapshots") or ()}
        candidates.append((metadata, payload, source_ids))
    compatible = [row for row in candidates if set(required) <= row[2]]
    if not compatible:
        newest = max(
            candidates,
            key=lambda row: (
                timestamp_key(str(row[0]["available_at"])),
                str(row[0]["leaf_sha256"]),
            ),
            default=None,
        )
        observed = newest[2] if newest else set()
        body = {
            "schema": EVIDENCE_REF_SCHEMA, "as_of": cutoff,
            "status": "required_sources_unarchived" if newest else "archive_unavailable",
            "required_source_ids": list(required),
            "missing_source_ids": sorted(set(required) - observed),
            "manifest_leaf_sha256": newest[0]["leaf_sha256"] if newest else None,
            "source_run_sha256": newest[1]["source_run_sha256"] if newest else None,
            "archive_authority": "incomplete_point_in_time_archive",
        }
        return {**body, "ref_sha256": stable_sha256(body)}
    metadata, payload, _source_ids = max(
        compatible,
        key=lambda row: (
            timestamp_key(str(row[0]["available_at"])),
            str(row[0]["leaf_sha256"]),
        ),
    )
    body = {
        "schema": EVIDENCE_REF_SCHEMA, "as_of": cutoff, "status": "covered",
        "required_source_ids": list(required), "missing_source_ids": [],
        "manifest_leaf_sha256": metadata["leaf_sha256"],
        "source_run_sha256": payload["source_run_sha256"],
        "manifest_ingested_at": payload["ingested_at"],
        "archive_authority": (
            "point_in_time_archive"
            if (payload.get("authority") or {}).get("point_in_time_archive")
            else "declared_clock_reconstruction"
        ),
    }
    return {**body, "ref_sha256": stable_sha256(body)}


__all__ = [
    "EVIDENCE_MANIFEST_SCHEMA", "EVIDENCE_RECONSTRUCTION_SCHEMA",
    "EVIDENCE_REF_SCHEMA", "EVIDENCE_SNAPSHOT_SCHEMA", "EVIDENCE_STATUS_SCHEMA",
    "capture_public_source_run", "evidence_vault_status",
    "evidence_manifest_ref", "reconstruct_evidence_as_of",
]
