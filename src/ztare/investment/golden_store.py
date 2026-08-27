"""Append-only authority for investment evidence, decisions, and outcomes.

The store keeps content-addressed leaves as the canonical record.  Heads,
lineage edges, graph views, reports, and future vector indexes are projections.
SQLite supplies atomic commits, WAL concurrency, and an inspectable local
reference implementation without adding a runtime dependency.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator, Mapping
import zlib

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key


GOLDEN_LEAF_SCHEMA = "jaggedthoughts-golden-leaf-v1"
RESEARCH_EVIDENCE_QUARANTINE_SCHEMA = "jaggedthoughts-research-evidence-quarantine-v1"
_RELATIONS = {
    "based_on",
    "derived_from",
    "reviews",
    "selects",
    "settles",
    "scores",
    "supersedes",
    "cites",
    "contains",
    "supported_by",
}
_COMPRESSED_JSON_PREFIX = b"jaggedthoughts-zlib-json-v1\0"
_COMPRESS_AT_BYTES = 64 * 1024


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def encode_golden_body(value: Mapping[str, Any]) -> str | bytes:
    """Store large immutable JSON bodies compactly without changing their hashes."""
    raw = _json(value).encode("utf-8")
    if len(raw) < _COMPRESS_AT_BYTES:
        return raw.decode("utf-8")
    return _COMPRESSED_JSON_PREFIX + zlib.compress(raw, level=1)


def decode_golden_body(value: str | bytes | memoryview) -> dict[str, Any]:
    """Read both legacy text rows and compressed rows."""
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        if value.startswith(_COMPRESSED_JSON_PREFIX):
            value = zlib.decompress(value[len(_COMPRESSED_JSON_PREFIX):])
        value = value.decode("utf-8")
    payload = json.loads(value)
    if not isinstance(payload, dict):
        raise ValueError("golden-store body must decode to an object")
    return payload


def _refs(values: Iterable[Any]) -> tuple[str, ...]:
    return tuple(sorted({require_text(value, "golden leaf source ref") for value in values}))


@dataclass(frozen=True, slots=True)
class GoldenLeaf:
    """One immutable, typed fact at one evidence epoch."""

    owner: str
    object_kind: str
    object_id: str
    epoch: str
    occurred_at: str
    available_at: str
    payload: Mapping[str, Any]
    source_refs: tuple[str, ...]
    payload_schema: str = field(init=False)
    payload_sha256: str = field(init=False)
    leaf_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("owner", "object_kind", "object_id", "epoch"):
            object.__setattr__(self, attr, require_text(getattr(self, attr), f"leaf.{attr}"))
        occurred = canonical_timestamp(self.occurred_at, "leaf.occurred_at")
        available = canonical_timestamp(self.available_at, "leaf.available_at")
        if timestamp_key(available) < timestamp_key(occurred):
            raise ValueError("leaf available_at cannot precede occurred_at")
        payload = dict(self.payload)
        schema = require_text(payload.get("schema"), "leaf.payload.schema")
        refs = _refs(self.source_refs)
        if not refs:
            raise ValueError("golden leaf source_refs must be nonempty")
        object.__setattr__(self, "occurred_at", occurred)
        object.__setattr__(self, "available_at", available)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "source_refs", refs)
        object.__setattr__(self, "payload_schema", schema)
        object.__setattr__(self, "payload_sha256", stable_sha256(payload))
        object.__setattr__(self, "leaf_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": GOLDEN_LEAF_SCHEMA,
            "owner": self.owner,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "epoch": self.epoch,
            "occurred_at": self.occurred_at,
            "available_at": self.available_at,
            "payload_schema": self.payload_schema,
            "payload_sha256": self.payload_sha256,
            "payload": dict(self.payload),
            "source_refs": list(self.source_refs),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "leaf_sha256": self.leaf_sha256}


@dataclass(frozen=True, slots=True)
class GoldenEdge:
    src_leaf_sha256: str
    dst_leaf_sha256: str
    relation: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    edge_sha256: str = field(init=False)

    def __post_init__(self) -> None:
        for attr in ("src_leaf_sha256", "dst_leaf_sha256"):
            digest = require_text(getattr(self, attr), f"edge.{attr}")
            if len(digest) != 64:
                raise ValueError(f"edge {attr} must be a SHA-256 digest")
            object.__setattr__(self, attr, digest)
        relation = require_text(self.relation, "edge.relation")
        if relation not in _RELATIONS:
            raise ValueError(f"unsupported golden-store relation: {relation}")
        object.__setattr__(self, "relation", relation)
        object.__setattr__(self, "metadata", dict(self.metadata))
        object.__setattr__(self, "edge_sha256", stable_sha256(self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "jaggedthoughts-golden-edge-v1",
            "src_leaf_sha256": self.src_leaf_sha256,
            "dst_leaf_sha256": self.dst_leaf_sha256,
            "relation": self.relation,
            "metadata": dict(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "edge_sha256": self.edge_sha256}


class GoldenStore:
    """SQLite-backed append-only leaf store with rebuildable projections."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS golden_leaf (
                    leaf_sha256 TEXT PRIMARY KEY,
                    owner TEXT NOT NULL,
                    object_kind TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    epoch TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    available_at TEXT NOT NULL,
                    payload_schema TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(owner, object_kind, object_id, epoch)
                );
                CREATE INDEX IF NOT EXISTS ix_golden_leaf_object
                    ON golden_leaf(owner, object_kind, object_id, available_at);
                CREATE INDEX IF NOT EXISTS ix_golden_leaf_kind_available
                    ON golden_leaf(object_kind, available_at DESC, leaf_sha256);
                CREATE TABLE IF NOT EXISTS golden_edge (
                    edge_sha256 TEXT PRIMARY KEY,
                    src_leaf_sha256 TEXT NOT NULL REFERENCES golden_leaf(leaf_sha256),
                    dst_leaf_sha256 TEXT NOT NULL REFERENCES golden_leaf(leaf_sha256),
                    relation TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS ix_golden_edge_src
                    ON golden_edge(src_leaf_sha256, relation);
                CREATE INDEX IF NOT EXISTS ix_golden_edge_dst
                    ON golden_edge(dst_leaf_sha256, relation);
                CREATE INDEX IF NOT EXISTS ix_golden_edge_relation_digest
                    ON golden_edge(relation, edge_sha256);
                CREATE TABLE IF NOT EXISTS golden_head (
                    owner TEXT NOT NULL,
                    object_kind TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    leaf_sha256 TEXT NOT NULL REFERENCES golden_leaf(leaf_sha256),
                    available_at TEXT NOT NULL,
                    PRIMARY KEY(owner, object_kind, object_id)
                );
                CREATE TABLE IF NOT EXISTS golden_embedding_receipt (
                    receipt_sha256 TEXT PRIMARY KEY,
                    leaf_sha256 TEXT NOT NULL REFERENCES golden_leaf(leaf_sha256),
                    model_id TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    dimensions INTEGER NOT NULL,
                    task_type TEXT NOT NULL,
                    content_sha256 TEXT NOT NULL,
                    vector_ref TEXT NOT NULL,
                    body_json TEXT NOT NULL,
                    inserted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(leaf_sha256, model_id, model_version, task_type, content_sha256)
                );
                CREATE TRIGGER IF NOT EXISTS golden_leaf_no_update
                    BEFORE UPDATE ON golden_leaf
                    BEGIN SELECT RAISE(ABORT, 'golden_leaf is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS golden_leaf_no_delete
                    BEFORE DELETE ON golden_leaf
                    BEGIN SELECT RAISE(ABORT, 'golden_leaf is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS golden_edge_no_update
                    BEFORE UPDATE ON golden_edge
                    BEGIN SELECT RAISE(ABORT, 'golden_edge is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS golden_edge_no_delete
                    BEFORE DELETE ON golden_edge
                    BEGIN SELECT RAISE(ABORT, 'golden_edge is append-only'); END;
                CREATE TRIGGER IF NOT EXISTS golden_head_no_delete
                    BEFORE DELETE ON golden_head
                    BEGIN SELECT RAISE(ABORT, 'golden_head identities are monotone'); END;
                CREATE TRIGGER IF NOT EXISTS golden_head_identity_no_update
                    BEFORE UPDATE OF owner, object_kind, object_id ON golden_head
                    BEGIN SELECT RAISE(ABORT, 'golden_head identity is immutable'); END;
                """
            )

    def append_bundle(
        self,
        leaves: Iterable[GoldenLeaf],
        edges: Iterable[GoldenEdge] = (),
        *,
        make_heads: bool = True,
    ) -> dict[str, tuple[str, ...]]:
        """Commit a coherent leaf/edge bundle in one SQLite transaction."""
        leaf_rows = tuple(leaves)
        edge_rows = tuple(edges)
        if len({row.leaf_sha256 for row in leaf_rows}) != len(leaf_rows):
            raise ValueError("golden-store bundle contains duplicate leaves")
        if len({row.edge_sha256 for row in edge_rows}) != len(edge_rows):
            raise ValueError("golden-store bundle contains duplicate edges")
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            for leaf in leaf_rows:
                conflict = connection.execute(
                    """SELECT leaf_sha256 FROM golden_leaf
                       WHERE owner=? AND object_kind=? AND object_id=? AND epoch=?""",
                    (leaf.owner, leaf.object_kind, leaf.object_id, leaf.epoch),
                ).fetchone()
                if conflict and conflict["leaf_sha256"] != leaf.leaf_sha256:
                    raise ValueError(
                        "golden leaf identity already exists with different content: "
                        f"{leaf.owner}/{leaf.object_kind}/{leaf.object_id}@{leaf.epoch}"
                    )
                connection.execute(
                    """INSERT OR IGNORE INTO golden_leaf
                       (leaf_sha256, owner, object_kind, object_id, epoch, occurred_at,
                        available_at, payload_schema, payload_sha256, body_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        leaf.leaf_sha256, leaf.owner, leaf.object_kind, leaf.object_id,
                        leaf.epoch, leaf.occurred_at, leaf.available_at,
                        leaf.payload_schema, leaf.payload_sha256,
                        encode_golden_body(leaf.to_dict()),
                    ),
                )
                if make_heads:
                    current = connection.execute(
                        """SELECT h.leaf_sha256, h.available_at, l.rowid AS leaf_rowid
                           FROM golden_head h JOIN golden_leaf l
                             ON l.leaf_sha256=h.leaf_sha256
                           WHERE h.owner=? AND h.object_kind=? AND h.object_id=?""",
                        (leaf.owner, leaf.object_kind, leaf.object_id),
                    ).fetchone()
                    leaf_rowid = connection.execute(
                        "SELECT rowid FROM golden_leaf WHERE leaf_sha256=?",
                        (leaf.leaf_sha256,),
                    ).fetchone()[0]
                    if current is None or (
                        timestamp_key(leaf.available_at), int(leaf_rowid)
                    ) > (
                        timestamp_key(current["available_at"]), int(current["leaf_rowid"])
                    ):
                        connection.execute(
                            """INSERT INTO golden_head(owner, object_kind, object_id, leaf_sha256, available_at)
                               VALUES (?, ?, ?, ?, ?)
                               ON CONFLICT(owner, object_kind, object_id) DO UPDATE SET
                                 leaf_sha256=excluded.leaf_sha256,
                                 available_at=excluded.available_at""",
                            (leaf.owner, leaf.object_kind, leaf.object_id, leaf.leaf_sha256, leaf.available_at),
                        )
            for edge in edge_rows:
                missing = [
                    digest for digest in (edge.src_leaf_sha256, edge.dst_leaf_sha256)
                    if connection.execute(
                        "SELECT 1 FROM golden_leaf WHERE leaf_sha256=?", (digest,)
                    ).fetchone() is None
                ]
                if missing:
                    raise ValueError(f"golden edge references missing leaves: {missing}")
                connection.execute(
                    """INSERT OR IGNORE INTO golden_edge
                       (edge_sha256, src_leaf_sha256, dst_leaf_sha256, relation, body_json)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        edge.edge_sha256, edge.src_leaf_sha256, edge.dst_leaf_sha256,
                        edge.relation, _json(edge.to_dict()),
                    ),
                )
        return {
            "leaves": tuple(row.leaf_sha256 for row in leaf_rows),
            "edges": tuple(row.edge_sha256 for row in edge_rows),
        }

    def append_leaf(self, leaf: GoldenLeaf, *, make_head: bool = True) -> str:
        self.append_bundle((leaf,), make_heads=make_head)
        return leaf.leaf_sha256

    def append_edge(self, edge: GoldenEdge) -> str:
        self.append_bundle((), (edge,))
        return edge.edge_sha256

    def get_leaf(self, leaf_sha256: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT body_json FROM golden_leaf WHERE leaf_sha256=?", (leaf_sha256,)
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown golden leaf: {leaf_sha256}")
        return decode_golden_body(row["body_json"])

    def get_leaves(self, leaf_sha256s: Iterable[str]) -> dict[str, dict[str, Any]]:
        """Read many immutable leaves without one SQLite connection per leaf."""
        identities = tuple(dict.fromkeys(
            require_text(value, "golden leaf hash") for value in leaf_sha256s
        ))
        if not identities:
            return {}
        result: dict[str, dict[str, Any]] = {}
        with self._connect() as connection:
            for start in range(0, len(identities), 900):
                chunk = identities[start:start + 900]
                rows = connection.execute(
                    "SELECT leaf_sha256, body_json FROM golden_leaf WHERE leaf_sha256 IN ("
                    + ",".join("?" for _ in chunk) + ")",
                    chunk,
                ).fetchall()
                result.update({
                    str(row["leaf_sha256"]): decode_golden_body(row["body_json"])
                    for row in rows
                })
        missing = set(identities) - set(result)
        if missing:
            raise KeyError(f"unknown golden leaf: {min(missing)}")
        return result

    def head(self, owner: str, object_kind: str, object_id: str) -> dict[str, Any]:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT leaf_sha256 FROM golden_head
                   WHERE owner=? AND object_kind=? AND object_id=?""",
                (owner, object_kind, object_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"no golden head: {owner}/{object_kind}/{object_id}")
        return self.get_leaf(row["leaf_sha256"])

    def heads_as_of(
        self,
        owner: str,
        object_kind: str,
        as_of: str,
        *,
        object_ids: Iterable[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return one latest immutable leaf per typed object at a past cutoff."""

        cutoff = canonical_timestamp(as_of, "golden-store as_of")
        ids = tuple(sorted({require_text(value, "golden object id") for value in object_ids or ()}))
        values: list[Any] = [
            require_text(owner, "golden owner"),
            require_text(object_kind, "golden object kind"),
            cutoff,
        ]
        clause = ""
        if ids:
            clause = " AND object_id IN (" + ",".join("?" for _ in ids) + ")"
            values.extend(ids)
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT body_json FROM (
                       SELECT body_json, object_id,
                              ROW_NUMBER() OVER (
                                PARTITION BY owner, object_kind, object_id
                                ORDER BY available_at DESC, occurred_at DESC, leaf_sha256 DESC
                              ) AS rank
                       FROM golden_leaf
                       WHERE owner=? AND object_kind=? AND available_at<=?"""
                + clause
                + ") WHERE rank=1 ORDER BY object_id",
                values,
            ).fetchall()
        return [decode_golden_body(row["body_json"]) for row in rows]

    def identity(
        self, owner: str, object_kind: str, object_id: str, epoch: str,
    ) -> dict[str, Any] | None:
        """Return the immutable leaf at an exact typed identity, if present."""
        with self._connect() as connection:
            row = connection.execute(
                """SELECT leaf_sha256 FROM golden_leaf
                   WHERE owner=? AND object_kind=? AND object_id=? AND epoch=?""",
                (owner, object_kind, object_id, epoch),
            ).fetchone()
        return self.get_leaf(row["leaf_sha256"]) if row else None

    def list_leaves(
        self,
        *,
        owner: str | None = None,
        object_kind: str | None = None,
        object_ids: Iterable[str] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        if limit < 1 or limit > 10_000:
            raise ValueError("limit must be in [1, 10000]")
        where: list[str] = []
        values: list[Any] = []
        if owner:
            where.append("owner=?")
            values.append(owner)
        if object_kind:
            where.append("object_kind=?")
            values.append(object_kind)
        identities = tuple(sorted({str(value) for value in object_ids or () if str(value)}))
        if identities:
            where.append(f"object_id IN ({','.join('?' for _ in identities)})")
            values.extend(identities)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT leaf_sha256, owner, object_kind, object_id, epoch,
                          occurred_at, available_at, payload_schema, payload_sha256
                   FROM golden_leaf""" + clause +
                " ORDER BY available_at DESC, leaf_sha256 LIMIT ?",
                (*values, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_edges(
        self, *, relation: str | None = None,
        src_leaf_sha256: str | None = None,
        dst_leaf_sha256: str | None = None,
        limit: int = 1_000,
    ) -> list[dict[str, Any]]:
        """Read an inspectable edge projection in either dependency direction."""
        if limit < 1 or limit > 100_000:
            raise ValueError("edge limit must be in [1, 100000]")
        where: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("relation", relation), ("src_leaf_sha256", src_leaf_sha256),
            ("dst_leaf_sha256", dst_leaf_sha256),
        ):
            if value:
                where.append(f"{column}=?")
                values.append(value)
        clause = " WHERE " + " AND ".join(where) if where else ""
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT body_json FROM golden_edge" + clause
                + " ORDER BY edge_sha256 LIMIT ?",
                (*values, int(limit)),
            ).fetchall()
        return [decode_golden_body(row["body_json"]) for row in rows]
    def lineage(self, leaf_sha256: str, *, max_depth: int = 12) -> dict[str, Any]:
        if max_depth < 0 or max_depth > 100:
            raise ValueError("max_depth must be in [0, 100]")
        self.get_leaf(leaf_sha256)
        nodes: dict[str, dict[str, Any]] = {}
        edges: dict[str, dict[str, Any]] = {}
        frontier = [(leaf_sha256, 0)]
        while frontier:
            digest, depth = frontier.pop(0)
            if digest in nodes:
                continue
            nodes[digest] = self.get_leaf(digest)
            if depth >= max_depth:
                continue
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT body_json FROM golden_edge WHERE src_leaf_sha256=? ORDER BY edge_sha256",
                    (digest,),
                ).fetchall()
            for row in rows:
                edge = decode_golden_body(row["body_json"])
                edges[edge["edge_sha256"]] = edge
                frontier.append((edge["dst_leaf_sha256"], depth + 1))
        return {
            "schema": "jaggedthoughts-golden-lineage-v1",
            "root_leaf_sha256": leaf_sha256,
            "nodes": [nodes[key] for key in sorted(nodes)],
            "edges": [edges[key] for key in sorted(edges)],
        }

    def register_embedding(
        self,
        *,
        leaf_sha256: str,
        model_id: str,
        model_version: str,
        dimensions: int,
        task_type: str,
        content_sha256: str,
        vector_ref: str,
    ) -> str:
        leaf = self.get_leaf(leaf_sha256)
        if dimensions < 1:
            raise ValueError("embedding dimensions must be positive")
        if content_sha256 != leaf["payload_sha256"]:
            raise ValueError("embedding receipt content hash does not match leaf payload")
        body = {
            "schema": "jaggedthoughts-golden-embedding-receipt-v1",
            "leaf_sha256": leaf_sha256,
            "model_id": require_text(model_id, "embedding.model_id"),
            "model_version": require_text(model_version, "embedding.model_version"),
            "dimensions": int(dimensions),
            "task_type": require_text(task_type, "embedding.task_type"),
            "content_sha256": content_sha256,
            "vector_ref": require_text(vector_ref, "embedding.vector_ref"),
        }
        receipt = stable_sha256(body)
        with self._connect() as connection:
            connection.execute(
                """INSERT OR IGNORE INTO golden_embedding_receipt
                   (receipt_sha256, leaf_sha256, model_id, model_version, dimensions,
                    task_type, content_sha256, vector_ref, body_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    receipt, leaf_sha256, body["model_id"], body["model_version"],
                    dimensions, body["task_type"], content_sha256, body["vector_ref"],
                    _json({**body, "receipt_sha256": receipt}),
                ),
            )
        return receipt

    def verify(self) -> dict[str, Any]:
        errors: list[str] = []
        leaf_count = 0
        edge_count = 0
        with self._connect() as connection:
            for row in connection.execute(
                """SELECT leaf_sha256, owner, object_kind, object_id, epoch,
                          occurred_at, available_at, payload_schema, payload_sha256, body_json
                   FROM golden_leaf ORDER BY leaf_sha256"""
            ):
                leaf_count += 1
                body = decode_golden_body(row["body_json"])
                declared = body.pop("leaf_sha256", "")
                if stable_sha256(body) != declared or declared != row["leaf_sha256"]:
                    errors.append(f"leaf hash mismatch: {row['leaf_sha256']}")
                if stable_sha256(body.get("payload")) != row["payload_sha256"]:
                    errors.append(f"payload hash mismatch: {row['leaf_sha256']}")
                for field in (
                    "owner", "object_kind", "object_id", "epoch", "occurred_at",
                    "available_at", "payload_schema", "payload_sha256",
                ):
                    if body.get(field) != row[field]:
                        errors.append(f"leaf {field} projection mismatch: {row['leaf_sha256']}")
            for row in connection.execute(
                """SELECT edge_sha256, src_leaf_sha256, dst_leaf_sha256, relation, body_json
                   FROM golden_edge ORDER BY edge_sha256"""
            ):
                edge_count += 1
                body = decode_golden_body(row["body_json"])
                declared = body.pop("edge_sha256", "")
                if stable_sha256(body) != declared or declared != row["edge_sha256"]:
                    errors.append(f"edge hash mismatch: {row['edge_sha256']}")
                for field in ("src_leaf_sha256", "dst_leaf_sha256", "relation"):
                    if body.get(field) != row[field]:
                        errors.append(f"edge {field} projection mismatch: {row['edge_sha256']}")
            heads = connection.execute(
                """SELECT h.owner, h.object_kind, h.object_id FROM golden_head h
                   LEFT JOIN golden_leaf l ON l.leaf_sha256=h.leaf_sha256
                   WHERE l.leaf_sha256 IS NULL
                      OR l.owner<>h.owner OR l.object_kind<>h.object_kind
                      OR l.object_id<>h.object_id OR l.available_at<>h.available_at
                      OR EXISTS (
                           SELECT 1 FROM golden_leaf newer
                           WHERE newer.owner=h.owner AND newer.object_kind=h.object_kind
                             AND newer.object_id=h.object_id
                             AND newer.available_at>h.available_at
                      )
                      OR EXISTS (
                           SELECT 1 FROM golden_leaf tied
                           WHERE tied.owner=h.owner AND tied.object_kind=h.object_kind
                             AND tied.object_id=h.object_id
                             AND tied.available_at=h.available_at
                             AND tied.rowid>l.rowid
                      )"""
            ).fetchall()
        if heads:
            errors.append(f"{len(heads)} head projections violate identity or recency")
        return {
            "schema": "jaggedthoughts-golden-store-verification-v1",
            "path": str(self.path),
            "leaf_count": leaf_count,
            "edge_count": edge_count,
            "ok": not errors,
            "errors": errors,
        }

    def refresh_heads(self) -> int:
        """Project each existing identity to latest availability, then append order."""
        changed = 0
        with self._connect() as connection:
            heads = connection.execute(
                "SELECT owner, object_kind, object_id, leaf_sha256 FROM golden_head"
            ).fetchall()
            for head in heads:
                latest = connection.execute(
                    """SELECT leaf_sha256, available_at FROM golden_leaf
                       WHERE owner=? AND object_kind=? AND object_id=?
                       ORDER BY available_at DESC, rowid DESC LIMIT 1""",
                    (head["owner"], head["object_kind"], head["object_id"]),
                ).fetchone()
                if latest and latest["leaf_sha256"] != head["leaf_sha256"]:
                    connection.execute(
                        """UPDATE golden_head SET leaf_sha256=?, available_at=?
                           WHERE owner=? AND object_kind=? AND object_id=?""",
                        (
                            latest["leaf_sha256"], latest["available_at"],
                            head["owner"], head["object_kind"], head["object_id"],
                        ),
                    )
                    changed += 1
        return changed


def research_evidence_quarantine(
    store: GoldenStore, *, owner: str, target_leaf: str, as_of: str | None = None,
) -> dict[str, Any] | None:
    """Return the append-only quarantine fact for one evidence leaf, if any."""
    target_sha = require_text(target_leaf, "quarantined research evidence leaf")
    owner_id = require_text(owner, "research evidence owner")
    object_id = f"research-quarantine:{target_sha}"
    if as_of is None:
        try:
            record = store.head(owner_id, "research_evidence_quarantine", object_id)
        except KeyError:
            return None
    else:
        rows = store.heads_as_of(
            owner_id, "research_evidence_quarantine", as_of, object_ids=(object_id,),
        )
        if not rows:
            return None
        record = rows[0]
    payload = record.get("payload") or {}
    if (
        payload.get("schema") != RESEARCH_EVIDENCE_QUARANTINE_SCHEMA
        or payload.get("status") != "quarantined"
        or payload.get("target_leaf_sha256") != target_sha
    ):
        raise ValueError("research evidence quarantine identity is invalid")
    return record


def research_evidence_is_admissible(
    store: GoldenStore, *, owner: str, target_leaf: str, as_of: str | None = None,
) -> bool:
    """Whether a research leaf and every declared research ancestor are admissible."""
    return research_evidence_admissibility(
        store, owner=owner, target_leaf=target_leaf, as_of=as_of,
    )["admissible"]


def research_evidence_admissibility(
    store: GoldenStore, *, owner: str, target_leaf: str, as_of: str | None = None,
) -> dict[str, Any]:
    """Resolve direct or inherited quarantine through dossier derivation edges."""
    owner_id = require_text(owner, "research evidence owner")
    target_sha = require_text(target_leaf, "research evidence leaf")
    cutoff = canonical_timestamp(as_of, "research evidence as_of") if as_of else None
    frontier = [(target_sha, 0)]
    visited: set[str] = set()
    while frontier:
        leaf_sha, depth = frontier.pop(0)
        if leaf_sha in visited:
            continue
        visited.add(leaf_sha)
        try:
            record = store.get_leaf(leaf_sha)
        except KeyError:
            return {
                "admissible": False,
                "target_leaf": target_sha,
                "quarantined_leaf": None,
                "quarantine_leaf": None,
                "reason_code": "missing_evidence_leaf",
                "missing_leaf": leaf_sha,
                "inherited": leaf_sha != target_sha,
                "depth": depth,
                "quarantine": None,
            }
        if record.get("owner") != owner_id or record.get("object_kind") != "candidate_research_dossier":
            raise ValueError("research admissibility lineage left owned candidate dossiers")
        if cutoff and str(record.get("available_at") or "") > cutoff:
            return {
                "admissible": False,
                "target_leaf": target_sha,
                "quarantined_leaf": None,
                "quarantine_leaf": None,
                "reason_code": "evidence_unavailable_at_cutoff",
                "missing_leaf": leaf_sha,
                "inherited": leaf_sha != target_sha,
                "depth": depth,
                "quarantine": None,
            }
        quarantine = research_evidence_quarantine(
            store, owner=owner_id, target_leaf=leaf_sha, as_of=cutoff,
        )
        if quarantine is not None:
            payload = quarantine.get("payload") or {}
            return {
                "admissible": False,
                "target_leaf": target_sha,
                "quarantined_leaf": leaf_sha,
                "quarantine_leaf": quarantine["leaf_sha256"],
                "reason_code": payload.get("reason_code"),
                "inherited": leaf_sha != target_sha,
                "depth": depth,
                "quarantine": quarantine,
            }
        if depth >= 32:
            raise ValueError("research evidence derivation lineage exceeds 32 hops")
        frontier.extend(
            (str(edge["dst_leaf_sha256"]), depth + 1)
            for edge in store.list_edges(
                relation="derived_from", src_leaf_sha256=leaf_sha, limit=10_000,
            )
        )
    return {
        "admissible": True, "target_leaf": target_sha,
        "quarantined_leaf": None, "quarantine_leaf": None,
        "reason_code": None, "inherited": False, "depth": 0,
        "quarantine": None,
    }


def record_research_evidence_quarantine(
    store: GoldenStore, *, owner: str, target_leaf: str,
    reason_code: str, detected_at: str, source_refs: Iterable[str],
    details: Mapping[str, Any] | None = None,
) -> str:
    """Append a quarantine fact without mutating or deleting the target evidence."""
    owner_id = require_text(owner, "research evidence owner")
    target_sha = require_text(target_leaf, "quarantined research evidence leaf")
    target = store.get_leaf(target_sha)
    if target.get("owner") != owner_id or target.get("object_kind") != "candidate_research_dossier":
        raise ValueError("research evidence quarantine must target an owned candidate dossier")
    existing = research_evidence_quarantine(
        store, owner=owner_id, target_leaf=target_sha,
    )
    if existing is not None:
        return str(existing["leaf_sha256"])
    observed_at = canonical_timestamp(detected_at, "research evidence quarantine detected_at")
    payload = {
        "schema": RESEARCH_EVIDENCE_QUARANTINE_SCHEMA,
        "status": "quarantined",
        "target_leaf_sha256": target_sha,
        "target_object_kind": target["object_kind"],
        "target_object_id": target["object_id"],
        "target_payload_sha256": target["payload_sha256"],
        "target_available_at": target["available_at"],
        "reason_code": require_text(reason_code, "research evidence quarantine reason"),
        "detected_at": observed_at,
        "details": dict(details or {}),
        "capital_authority": False,
    }
    leaf = GoldenLeaf(
        owner=owner_id,
        object_kind="research_evidence_quarantine",
        object_id=f"research-quarantine:{target_sha}",
        epoch=stable_sha256(payload),
        occurred_at=observed_at,
        available_at=observed_at,
        payload=payload,
        source_refs=tuple(source_refs),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, target_sha, "reviews"),),
    )
    return leaf.leaf_sha256


def _source_refs(decision: Mapping[str, Any]) -> tuple[str, ...]:
    refs = {
        str(row["source_id"])
        for row in decision.get("source_receipts", [])
    }
    refs.update(
        str(row["source_ref"])
        for row in decision.get("point_in_time_snapshot", {}).get("observations", [])
    )
    return _refs(refs)


def record_investment_decision(store: GoldenStore, decision: Mapping[str, Any]) -> dict[str, str]:
    """Atomize one compiled decision and link its typed dependencies."""
    body = dict(decision)
    declared = str(body.pop("decision_record_sha256", ""))
    if declared != stable_sha256(body):
        raise ValueError("decision record content hash mismatch")
    if body.get("schema") != "jaggedthoughts-investment-decision-v1":
        raise ValueError("unsupported investment decision schema")
    owner = str(body["owner"])
    as_of = str(body["as_of"])
    refs = _source_refs(body)

    def make(kind: str, object_id: str, epoch: str, payload: Mapping[str, Any]) -> GoldenLeaf:
        return GoldenLeaf(
            owner=owner,
            object_kind=kind,
            object_id=object_id,
            epoch=epoch,
            occurred_at=as_of,
            available_at=as_of,
            payload=payload,
            source_refs=refs,
        )

    snapshot = body["point_in_time_snapshot"]
    fingerprint = body["fingerprint"]
    market = body["market_state"]
    valuation = body["valuation_envelope"]
    thesis = body["thesis"]
    underwriting = body["underwriting_case"]
    review = body["review_packet"]
    policy = body["policy_synthesis"]
    snapshot_leaf = make("point_in_time_snapshot", snapshot["snapshot_id"], snapshot["snapshot_sha256"], snapshot)
    fingerprint_leaf = make("entity_fingerprint", fingerprint["fingerprint_id"], fingerprint["evidence_epoch"], fingerprint)
    market_leaf = make("market_state", market["committee_id"], as_of, market)
    valuation_leaf = make("valuation_envelope", valuation["envelope_id"], valuation["evidence_epoch"], valuation)
    thesis_leaf = make(
        "investment_thesis",
        f"{thesis['thesis_id']}@{thesis['version']}@{thesis['evidence_epoch']}",
        thesis["evidence_epoch"], thesis,
    )
    underwriting_leaf = make(
        "underwriting_case",
        f"{underwriting['case_id']}@{underwriting['evidence_epoch']}",
        underwriting["evidence_epoch"], underwriting,
    )
    review_leaf = make("thesis_review_packet", review["packet_id"], as_of, review)
    policy_leaf = make("recursive_policy_frontier", body["decision_id"], snapshot["snapshot_sha256"], policy)
    decision_payload = {**body, "decision_record_sha256": declared}
    decision_leaf = make("paper_decision", body["decision_id"], as_of, decision_payload)

    edges = tuple(GoldenEdge(src.leaf_sha256, dst.leaf_sha256, relation) for src, dst, relation in (
        (fingerprint_leaf, snapshot_leaf, "derived_from"),
        (review_leaf, fingerprint_leaf, "reviews"),
        (review_leaf, market_leaf, "reviews"),
        (review_leaf, valuation_leaf, "reviews"),
        (review_leaf, thesis_leaf, "reviews"),
        (review_leaf, underwriting_leaf, "reviews"),
        (policy_leaf, fingerprint_leaf, "derived_from"),
        (policy_leaf, market_leaf, "derived_from"),
        (policy_leaf, valuation_leaf, "derived_from"),
        (policy_leaf, thesis_leaf, "derived_from"),
        (policy_leaf, underwriting_leaf, "derived_from"),
        (decision_leaf, snapshot_leaf, "based_on"),
        (decision_leaf, review_leaf, "based_on"),
        (decision_leaf, valuation_leaf, "based_on"),
        (decision_leaf, underwriting_leaf, "based_on"),
        (decision_leaf, policy_leaf, "selects"),
    ))
    store.append_bundle(
        (
            snapshot_leaf, fingerprint_leaf, market_leaf, valuation_leaf, thesis_leaf,
            underwriting_leaf, review_leaf, policy_leaf, decision_leaf,
        ),
        edges,
    )
    return {
        "snapshot": snapshot_leaf.leaf_sha256,
        "fingerprint": fingerprint_leaf.leaf_sha256,
        "market_state": market_leaf.leaf_sha256,
        "valuation_envelope": valuation_leaf.leaf_sha256,
        "thesis": thesis_leaf.leaf_sha256,
        "underwriting_case": underwriting_leaf.leaf_sha256,
        "review_packet": review_leaf.leaf_sha256,
        "policy_frontier": policy_leaf.leaf_sha256,
        "decision": decision_leaf.leaf_sha256,
    }


def record_investment_settlement(
    store: GoldenStore,
    *,
    decision: Mapping[str, Any],
    outcome: Mapping[str, Any],
    scorecard: Mapping[str, Any],
) -> dict[str, str]:
    """Append a later outcome and its economic score without rewriting history."""
    owner = require_text(decision.get("owner"), "decision.owner")
    decision_id = require_text(decision.get("decision_id"), "decision.decision_id")
    decision_leaf = store.head(owner, "paper_decision", decision_id)
    if decision_leaf["payload"].get("decision_record_sha256") != outcome.get("decision_record_sha256"):
        raise ValueError("settlement outcome does not bind the stored decision")
    refs = _refs(outcome.get("source_refs", []))
    observed_at = str(outcome["observed_at"])
    available_at = str(outcome["available_at"])
    outcome_leaf = GoldenLeaf(
        owner=owner,
        object_kind="investment_outcome",
        object_id=f"{decision_id}@{observed_at}",
        epoch=str(outcome["outcome_sha256"]),
        occurred_at=observed_at,
        available_at=available_at,
        payload=outcome,
        source_refs=refs,
    )
    score_leaf = GoldenLeaf(
        owner=owner,
        object_kind="economic_scorecard",
        object_id=f"{decision_id}@{observed_at}",
        epoch=str(scorecard["scorecard_sha256"]),
        occurred_at=observed_at,
        available_at=available_at,
        payload=scorecard,
        source_refs=refs,
    )
    store.append_bundle(
        (outcome_leaf, score_leaf),
        (
            GoldenEdge(outcome_leaf.leaf_sha256, decision_leaf["leaf_sha256"], "settles"),
            GoldenEdge(score_leaf.leaf_sha256, outcome_leaf.leaf_sha256, "scores"),
            GoldenEdge(score_leaf.leaf_sha256, decision_leaf["leaf_sha256"], "scores"),
        ),
    )
    return {"outcome": outcome_leaf.leaf_sha256, "scorecard": score_leaf.leaf_sha256}


def record_portfolio_assembly(
    store: GoldenStore,
    *,
    assembly: Mapping[str, Any],
    decisions: Iterable[Mapping[str, Any]],
) -> str:
    """Append a paper portfolio assembly and link every candidate decision."""
    body = dict(assembly)
    declared = str(body.pop("portfolio_assembly_sha256", ""))
    if declared != stable_sha256(body):
        raise ValueError("portfolio assembly content hash mismatch")
    if body.get("schema") != "jaggedthoughts-portfolio-assembly-v1":
        raise ValueError("unsupported portfolio assembly schema")
    decision_rows = tuple(dict(row) for row in decisions)
    expected = {str(row["decision_record_sha256"]) for row in body.get("candidates", [])}
    provided = {str(row.get("decision_record_sha256")) for row in decision_rows}
    if expected != provided:
        raise ValueError("portfolio assembly decisions do not match its candidate set")
    decision_leaves: list[dict[str, Any]] = []
    refs: set[str] = set()
    for decision in decision_rows:
        record_investment_decision(store, decision)
        decision_leaves.append(store.head(
            str(decision["owner"]), "paper_decision", str(decision["decision_id"])
        ))
        refs.update(_source_refs(decision))
    leaf = GoldenLeaf(
        owner=str(body["owner"]),
        object_kind="portfolio_assembly",
        object_id=str(body["portfolio_id"]),
        epoch=declared,
        occurred_at=str(body["as_of"]),
        available_at=str(body["as_of"]),
        payload={**body, "portfolio_assembly_sha256": declared},
        source_refs=tuple(refs),
    )
    store.append_bundle(
        (leaf,),
        tuple(GoldenEdge(leaf.leaf_sha256, row["leaf_sha256"], "based_on") for row in decision_leaves),
        make_heads=False,
    )
    return leaf.leaf_sha256


def record_strategy_move_library(
    store: GoldenStore, *, owner: str, library: Mapping[str, Any],
) -> str:
    """Atomize an outcome-linked strategy library without granting policy authority."""

    body = dict(library)
    declared = str(body.pop("library_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-move-library-v1":
        raise ValueError("unsupported strategy move library schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy move library content hash mismatch")
    moves = [dict(row) for row in body.get("moves") or ()]
    if not moves:
        raise ValueError("golden strategy move library requires at least one move")
    epoch = max(str(row["evidence_epoch"]) for row in moves)
    frontier_refs = tuple(sorted({
        f"strategy-frontier:{row['strategy_frontier_sha256']}" for row in moves
    }))
    library_leaf = GoldenLeaf(
        owner=require_text(owner, "strategy move library owner"),
        object_kind="strategy_move_library",
        object_id="jaggedthoughts-strategy-move-library",
        epoch=declared,
        occurred_at=epoch,
        available_at=epoch,
        payload={**body, "library_sha256": declared},
        source_refs=frontier_refs,
    )
    leaves = [library_leaf]
    edges = []
    for move in moves:
        exact = {
            key: value for key, value in move.items()
            if key not in {
                "outcome_episodes", "learning_status", "evidence_grade",
                "mechanism_phenotype", "mechanism_phenotype_sha256",
                "strategy_program_attribution",
                "scenario_direction_hypotheses",
                "scenario_calibration_receipts", "scenario_calibration_status",
                "scenario_calibration_next_transition",
            }
        }
        move_leaf = GoldenLeaf(
            owner=owner,
            object_kind="strategy_move",
            object_id=str(move["move_id"]),
            epoch=stable_sha256(exact),
            occurred_at=str(move["evidence_epoch"]),
            available_at=str(move["evidence_epoch"]),
            payload=exact,
            source_refs=tuple(str(value) for value in move.get("evidence_refs") or frontier_refs),
        )
        leaves.append(move_leaf)
        edges.append(GoldenEdge(library_leaf.leaf_sha256, move_leaf.leaf_sha256, "contains"))
        for episode in move.get("outcome_episodes") or ():
            episode_leaf = GoldenLeaf(
                owner=owner,
                object_kind="strategy_move_outcome",
                object_id=str(episode["episode_sha256"]),
                epoch=str(episode["episode_sha256"]),
                occurred_at=str(episode["observed_at"]),
                available_at=str(episode["available_at"]),
                payload=dict(episode),
                source_refs=tuple(episode.get("source_refs") or ()),
            )
            leaves.append(episode_leaf)
            edges.append(GoldenEdge(episode_leaf.leaf_sha256, move_leaf.leaf_sha256, "settles"))
    store.append_bundle(tuple(leaves), tuple(edges), make_heads=False)
    return library_leaf.leaf_sha256


def record_company_contingent_recourse_selection(
    store: GoldenStore, *, owner: str, policy: Mapping[str, Any],
    selection: Mapping[str, Any],
) -> dict[str, str]:
    """Record one frozen policy and its point-in-time branch selection."""
    policy_body = dict(policy)
    policy_sha = str(policy_body.pop("contingent_policy_sha256", ""))
    if (
        policy_body.get("schema") != "jaggedthoughts-company-contingent-policy-v1"
        or policy_sha != stable_sha256(policy_body)
    ):
        raise ValueError("contingent policy identity is invalid")
    selection_body = dict(selection)
    selection_sha = str(selection_body.pop("selection_sha256", ""))
    if (
        selection_body.get("schema")
        != "jaggedthoughts-company-contingent-recourse-selection-v1"
        or selection_sha != stable_sha256(selection_body)
        or selection_body.get("contingent_policy_sha256") != policy_sha
    ):
        raise ValueError("contingent recourse selection identity is invalid")

    owner_id = require_text(owner, "contingent recourse owner")
    company_id = require_text(policy_body.get("company_id"), "contingent policy company")
    policy_id = require_text(policy_body.get("policy_id"), "contingent policy id")
    policy_payload = {**policy_body, "contingent_policy_sha256": policy_sha}
    selection_payload = {**selection_body, "selection_sha256": selection_sha}
    policy_leaf = GoldenLeaf(
        owner=owner_id, object_kind="company_contingent_policy",
        object_id=f"{company_id}:{policy_id}", epoch=policy_sha,
        occurred_at=str(policy_body["frozen_at"]),
        available_at=str(policy_body["frozen_at"]), payload=policy_payload,
        source_refs=(
            f"strategy-choice-space:{policy_body['feasibility_receipt']['choice_space_sha256']}",
        ),
    )
    observation_refs = tuple(
        str(row["source_ref"]) for row in selection_body.get("observations") or ()
    )
    selection_leaf = GoldenLeaf(
        owner=owner_id, object_kind="company_contingent_recourse_selection",
        object_id=f"{company_id}:{policy_id}", epoch=selection_sha,
        occurred_at=str(selection_body["evaluated_at"]),
        available_at=str(selection_body["evaluated_at"]), payload=selection_payload,
        source_refs=(*observation_refs, f"strategy-policy:{policy_sha}"),
    )
    store.append_bundle(
        (policy_leaf, selection_leaf),
        (GoldenEdge(selection_leaf.leaf_sha256, policy_leaf.leaf_sha256, "selects"),),
    )
    return {
        "policy_leaf_sha256": policy_leaf.leaf_sha256,
        "selection_leaf_sha256": selection_leaf.leaf_sha256,
    }


def record_strategy_program_adoption_request(
    store: GoldenStore, *, owner: str, request: Mapping[str, Any],
) -> str:
    """Record one immutable recursive-program evidence question."""
    body = dict(request)
    declared = str(body.pop("request_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-program-adoption-research-request-v1":
        raise ValueError("unsupported strategy program adoption request schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy program adoption request content hash mismatch")
    candidate_sha = require_text(body.get("candidate_leaf"), "strategy program candidate leaf")
    candidate = store.get_leaf(candidate_sha)
    if candidate.get("owner") != owner or candidate.get("object_kind") != "discovery_candidate":
        raise ValueError("strategy program adoption request must bind an owned discovery candidate")
    if (
        body.get("candidate_sha256")
        and (candidate.get("payload") or {}).get("candidate_sha256") != body["candidate_sha256"]
    ):
        raise ValueError("strategy program adoption request crossed candidate identity")
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_adoption_request",
        object_id=str(body["request_id"]), epoch=declared,
        occurred_at=str(body["evidence_epoch"]), available_at=str(body["search_end_at"]),
        payload={**body, "request_sha256": declared},
        source_refs=(f"strategy-frontier:{body['strategy_frontier_sha256']}",),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, candidate_sha, "based_on"),),
    )
    return leaf.leaf_sha256


def record_strategy_program_adoption_result(
    store: GoldenStore, *, owner: str, request: Mapping[str, Any],
    result: Mapping[str, Any],
) -> str:
    """Record one source-backed program classification without policy authority."""
    result_body = dict(result)
    declared = str(result_body.pop("result_sha256", ""))
    if result_body.get("schema") != "jaggedthoughts-strategy-program-adoption-research-result-v1":
        raise ValueError("unsupported strategy program adoption result schema")
    if declared != stable_sha256(result_body):
        raise ValueError("strategy program adoption result content hash mismatch")
    if result_body.get("request_sha256") != request.get("request_sha256"):
        raise ValueError("strategy program adoption result crossed request identity")
    request_leaf_sha = record_strategy_program_adoption_request(
        store, owner=owner, request=request,
    )
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_adoption_result",
        object_id=str(request["request_id"]), epoch=declared,
        occurred_at=str(result_body["assessed_at"]), available_at=str(result_body["assessed_at"]),
        payload={**result_body, "result_sha256": declared},
        source_refs=tuple(str(row["url"]) for row in result_body.get("sources") or ()),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, request_leaf_sha, "settles"),),
    )
    return leaf.leaf_sha256


def record_strategy_program_outcome_plan(
    store: GoldenStore, *, owner: str, result_leaf_sha256: str,
    plan: Mapping[str, Any],
) -> str:
    """Record prospective program readouts beneath their source classification."""
    body = dict(plan)
    declared = str(body.pop("plan_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-program-outcome-plan-v1":
        raise ValueError("unsupported strategy program outcome plan schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy program outcome plan content hash mismatch")
    result_leaf = store.get_leaf(result_leaf_sha256)
    if result_leaf.get("owner") != owner or result_leaf.get("object_kind") != "strategy_program_adoption_result":
        raise ValueError("strategy program outcome plan must bind an owned program result")
    if (result_leaf.get("payload") or {}).get("result_sha256") != body["result_sha256"]:
        raise ValueError("strategy program outcome plan crossed result identity")
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_outcome_plan",
        object_id=str(body["result_sha256"]), epoch=declared,
        occurred_at=str((result_leaf.get("payload") or {})["assessed_at"]),
        available_at=str((result_leaf.get("payload") or {})["assessed_at"]),
        payload={**body, "plan_sha256": declared},
        source_refs=(f"strategy-program-result:{body['result_sha256']}",),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, result_leaf_sha256, "derived_from"),),
    )
    return leaf.leaf_sha256


def record_strategy_program_outcome_episode(
    store: GoldenStore, *, owner: str, episode: Mapping[str, Any],
) -> str:
    """Record one point-in-time program readout beneath its prospective plan."""
    body = dict(episode)
    declared = str(body.pop("episode_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-program-outcome-v1":
        raise ValueError("unsupported strategy program outcome episode schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy program outcome episode content hash mismatch")
    plan = store.head(
        owner, "strategy_program_outcome_plan", str(body["result_sha256"]),
    )
    if (plan.get("payload") or {}).get("plan_sha256") != body["plan_sha256"]:
        raise ValueError("strategy program outcome episode crossed plan identity")
    if str(body["readout_sha256"]) not in {
        str(row.get("readout_sha256"))
        for row in (plan.get("payload") or {}).get("readouts") or ()
    }:
        raise ValueError("strategy program outcome episode names an unbound readout")
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_outcome",
        object_id=str(body["readout_sha256"]), epoch=declared,
        occurred_at=str(body["observed_at"]), available_at=str(body["available_at"]),
        payload={**body, "episode_sha256": declared},
        source_refs=tuple(str(value) for value in body.get("source_refs") or ()),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, str(plan["leaf_sha256"]), "settles"),),
    )
    return leaf.leaf_sha256


def record_strategy_program_control_outcome_plan(
    store: GoldenStore, *, owner: str, plan: Mapping[str, Any],
    acquisition_card_sha256: str, transfer_card_sha256: str,
) -> str:
    """Record one assessment-time matched-control plan."""
    body = dict(plan)
    declared = str(body.pop("control_plan_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-program-control-outcome-plan-v1":
        raise ValueError("unsupported strategy program control outcome plan schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy program control outcome plan content hash mismatch")
    payload = {
        **body, "control_plan_sha256": declared,
        "acquisition_card_sha256": acquisition_card_sha256,
        "transfer_card_sha256": transfer_card_sha256,
    }
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_control_outcome_plan",
        object_id=declared, epoch=declared,
        occurred_at=str(body["measurement_start_at"]),
        available_at=str(body["measurement_start_at"]), payload=payload,
        source_refs=(
            f"strategy-program-request:{body['request_sha256']}",
            f"strategy-program-result:{body['result_sha256']}",
        ),
    )
    return store.append_leaf(leaf)


def record_strategy_program_control_outcome_episode(
    store: GoldenStore, *, owner: str, episode: Mapping[str, Any],
) -> str:
    """Record one point-in-time matched-control operating outcome."""
    body = dict(episode)
    declared = str(body.pop("episode_sha256", ""))
    if body.get("schema") != "jaggedthoughts-strategy-program-control-outcome-v1":
        raise ValueError("unsupported strategy program control outcome episode schema")
    if declared != stable_sha256(body):
        raise ValueError("strategy program control outcome episode content hash mismatch")
    plan = store.head(
        owner, "strategy_program_control_outcome_plan",
        str(body["control_plan_sha256"]),
    )
    if (plan.get("payload") or {}).get("control_plan_sha256") != body["control_plan_sha256"]:
        raise ValueError("strategy program control outcome crossed plan identity")
    leaf = GoldenLeaf(
        owner=owner, object_kind="strategy_program_control_outcome",
        object_id=str(body["control_plan_sha256"]), epoch=declared,
        occurred_at=str(body["observed_at"]), available_at=str(body["available_at"]),
        payload={**body, "episode_sha256": declared},
        source_refs=tuple(str(value) for value in body.get("source_refs") or ()),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, str(plan["leaf_sha256"]), "settles"),),
    )
    return leaf.leaf_sha256


def record_world_model_tournament(
    store: GoldenStore,
    tournament: Mapping[str, Any],
) -> dict[str, Any]:
    """Atomically record model tracks, settled episodes, and their tournament."""
    body = dict(tournament)
    declared = str(body.pop("tournament_sha256", ""))
    if declared != stable_sha256(body):
        raise ValueError("world-model tournament content hash mismatch")
    if body.get("schema") != "jaggedthoughts-world-model-tournament-v1":
        raise ValueError("unsupported world-model tournament schema")
    owner = require_text(body.get("owner"), "tournament.owner")
    as_of = canonical_timestamp(body.get("as_of"), "tournament.as_of")
    leaves: list[GoldenLeaf] = []
    model_leaves: list[GoldenLeaf] = []
    episode_leaves: list[GoldenLeaf] = []
    for track in body.get("model_tracks", []):
        model = dict(track["model"])
        if model.get("generation_process") == "unknown":
            model.pop("generation_process")
            model.pop("model_sha256", None)
            model["model_sha256"] = stable_sha256(model)
        forecasts = tuple(dict(row) for row in track["forecasts"])
        track_payload = {
            "schema": "jaggedthoughts-world-model-track-v1",
            "model": model,
            "forecasts": list(forecasts),
        }
        latest_issue = max(str(row["issued_at"]) for row in forecasts)
        refs = set(model.get("source_refs", []))
        for forecast in forecasts:
            refs.update(forecast.get("source_refs", []))
        leaf = GoldenLeaf(
            owner=owner,
            object_kind="world_model_track",
            object_id=str(model["model_key"]),
            epoch=stable_sha256(track_payload),
            occurred_at=latest_issue,
            available_at=latest_issue,
            payload=track_payload,
            source_refs=tuple(refs),
        )
        model_leaves.append(leaf)
        leaves.append(leaf)
    for episode in body.get("episodes", []):
        episode_body = dict(episode)
        leaf = GoldenLeaf(
            owner=owner,
            object_kind="backtest_episode",
            object_id=str(episode_body["episode_id"]),
            epoch=str(episode_body["episode_sha256"]),
            occurred_at=str(episode_body["end_at"]),
            available_at=str(episode_body["outcome_available_at"]),
            payload={"schema": "jaggedthoughts-backtest-episode-v1", **episode_body},
            source_refs=tuple(episode_body.get("source_refs", [])),
        )
        episode_leaves.append(leaf)
        leaves.append(leaf)
    tournament_leaf = GoldenLeaf(
        owner=owner,
        object_kind="world_model_tournament",
        object_id=f"{body['tournament_id']}@{declared[:16]}",
        epoch=declared,
        occurred_at=as_of,
        available_at=as_of,
        payload={**body, "tournament_sha256": declared},
        source_refs=tuple(body.get("source_refs", [])),
    )
    leaves.append(tournament_leaf)
    edges = tuple(
        GoldenEdge(tournament_leaf.leaf_sha256, leaf.leaf_sha256, "based_on")
        for leaf in (*model_leaves, *episode_leaves)
    )
    store.append_bundle(tuple(leaves), edges)
    return {
        "tournament": tournament_leaf.leaf_sha256,
        "model_tracks": {leaf.object_id: leaf.leaf_sha256 for leaf in model_leaves},
        "episodes": {leaf.object_id: leaf.leaf_sha256 for leaf in episode_leaves},
    }


def record_opportunity_watchlist(
    store: GoldenStore, *, owner: str, watchlist: Mapping[str, Any]
) -> str:
    """Record one compiled opportunity queue as an immutable analytical leaf."""
    body = dict(watchlist)
    declared = str(body.pop("watchlist_sha256", ""))
    if declared != stable_sha256(body):
        raise ValueError("opportunity watchlist content hash mismatch")
    if body.get("schema") != "jaggedthoughts-opportunity-watchlist-result-v1":
        raise ValueError("unsupported opportunity watchlist schema")
    refs = set(body.get("factor_premium_source_refs", []))
    holdings_graph = body.get("fund_holdings_graph") or {}
    refs.update(
        str(row["source_id"])
        for row in holdings_graph.get("snapshots", [])
        if row.get("source_id")
    )
    available_at = max(
        (
            str(body["as_of"]),
            str(body.get("compiler_available_at") or body["as_of"]),
            str(holdings_graph.get("available_at") or body["as_of"]),
        ),
        key=timestamp_key,
    )
    for candidate in body.get("candidates", []):
        analysis = candidate.get("analysis") or {}
        refs.update(analysis.get("source_refs", []))
        refs.update((candidate.get("fund_evidence") or {}).get("source_refs", []))
        if str(analysis.get("available_at") or "") > available_at:
            available_at = str(analysis["available_at"])
    leaf = GoldenLeaf(
        owner=require_text(owner, "watchlist owner"),
        object_kind="opportunity_watchlist",
        object_id=str(body["watchlist_id"]),
        epoch=declared,
        occurred_at=str(body["as_of"]),
        available_at=available_at,
        payload={**body, "watchlist_sha256": declared},
        source_refs=tuple(refs),
    )
    return store.append_leaf(leaf)


def record_funnel_transition(
    store: GoldenStore, *, owner: str, receipt: Mapping[str, Any]
) -> str:
    """Append one guarded lifecycle edge without turning the projection into authority."""
    from .funnel import FunnelTransitionReceipt

    transition = FunnelTransitionReceipt.from_dict(receipt)
    payload = transition.to_dict()
    leaf = GoldenLeaf(
        owner=require_text(owner, "funnel transition owner"),
        object_kind="opportunity_funnel_transition",
        object_id=transition.transition_id,
        epoch=transition.receipt_sha256,
        occurred_at=transition.occurred_at,
        available_at=transition.occurred_at,
        payload=payload,
        source_refs=transition.guard_refs,
    )
    return store.append_leaf(leaf, make_head=False)


def record_company_quality_report(
    store: GoldenStore, *, owner: str, report: Mapping[str, Any]
) -> str:
    """Record one point-in-time durable-earnings screen and its evidence refs."""
    body = dict(report)
    declared = str(body.pop("quality_report_sha256", ""))
    if body.get("schema") != "jaggedthoughts-company-quality-report-v1":
        raise ValueError("unsupported company quality report schema")
    if declared != stable_sha256(body):
        raise ValueError("company quality report content hash mismatch")
    leaf = GoldenLeaf(
        owner=require_text(owner, "company quality owner"),
        object_kind="company_quality_report",
        object_id=str(body["report_id"]),
        epoch=declared,
        occurred_at=str(body["as_of"]),
        available_at=str(body["as_of"]),
        payload={**body, "quality_report_sha256": declared},
        source_refs=tuple(body.get("source_refs") or ()),
    )
    return store.append_leaf(leaf, make_head=False)


def record_market_flow_experiment(
    store: GoldenStore, *, owner: str, result: Mapping[str, Any]
) -> str:
    """Record an isolated market-flow diagnostic without granting decision authority."""
    body = dict(result)
    hash_fields = {
        "jaggedthoughts-market-flow-backtest-v1": "market_flow_backtest_sha256",
        "jaggedthoughts-cross-sectional-market-flow-evidence-v2": "evidence_sha256",
        "jaggedthoughts-company-state-flow-evidence-v1": "evidence_sha256",
        "jaggedthoughts-company-state-path-action-run-v1": "run_sha256",
    }
    hash_field = hash_fields.get(str(body.get("schema") or ""))
    if hash_field is None:
        raise ValueError("unsupported market-flow result schema")
    declared = str(body.pop(hash_field, ""))
    if body.get("authority") != "experiment_only":
        raise ValueError("market-flow leaves require experiment_only authority")
    if declared != stable_sha256(body):
        raise ValueError("market-flow result content hash mismatch")
    payload = {**body, hash_field: declared}
    leaf = GoldenLeaf(
        owner=require_text(owner, "market-flow owner"),
        object_kind="market_flow_experiment",
        object_id=str(body["experiment_id"]),
        epoch=declared,
        occurred_at=str(body["as_of"]),
        available_at=str(body["as_of"]),
        payload=payload,
        source_refs=tuple(body.get("source_refs") or ()),
    )
    return store.append_leaf(leaf, make_head=False)


def record_mechanism_research_result(
    store: GoldenStore, *, owner: str, result: Mapping[str, Any]
) -> str:
    """Record one evidence-bound model-search result without capital authority."""
    body = dict(result)
    declared = str(body.pop("research_result_sha256", ""))
    if body.get("schema") != "jaggedthoughts-mechanism-research-result-v1":
        raise ValueError("unsupported mechanism research result schema")
    if body.get("authority") != "experiment_only" or body.get("capital_authority") is not False:
        raise ValueError("mechanism research results require experiment-only authority")
    if declared != stable_sha256(body):
        raise ValueError("mechanism research result content hash mismatch")
    leaf = GoldenLeaf(
        owner=require_text(owner, "mechanism research owner"),
        object_kind="mechanism_research_result",
        object_id=f"{body['project_id']}@{declared[:16]}",
        epoch=declared,
        occurred_at=str(body["evaluated_at"]),
        available_at=str(body["evaluated_at"]),
        payload={**body, "research_result_sha256": declared},
        source_refs=tuple(body.get("source_refs") or ()),
    )
    return store.append_leaf(leaf, make_head=True)


def record_discovery_run(
    store: GoldenStore, *, owner: str, run: Mapping[str, Any]
) -> dict[str, Any]:
    """Record a ranked discovery run and each candidate as independently addressable leaves."""
    body = dict(run)
    declared = str(body.pop("run_sha256", ""))
    if body.get("schema") != "jaggedthoughts-discovery-run-v1":
        raise ValueError("unsupported discovery run schema")
    if declared != stable_sha256(body):
        raise ValueError("discovery run content hash mismatch")
    completed_at = str(body["completed_at"])
    run_source_ref = f"source_run:{str(body.get('source_run_sha256') or declared)}"
    candidate_leaves: list[GoldenLeaf] = []
    input_edges: list[GoldenEdge] = []
    for raw in body.get("candidates", []):
        if not isinstance(raw, Mapping):
            raise ValueError("discovery candidates must be mappings")
        candidate = dict(raw)
        candidate_sha256 = str(candidate.pop("candidate_sha256", ""))
        if candidate.get("schema") != "jaggedthoughts-discovery-candidate-v1":
            raise ValueError("unsupported discovery candidate schema")
        if candidate_sha256 != stable_sha256(candidate):
            raise ValueError(f"discovery candidate content hash mismatch: {candidate.get('candidate_id')}")
        candidate_payload = {**candidate, "candidate_sha256": candidate_sha256}
        leaf = GoldenLeaf(
            owner=require_text(owner, "discovery owner"),
            object_kind="discovery_candidate",
            object_id=str(candidate["candidate_id"]),
            epoch=candidate_sha256,
            occurred_at=str(candidate["as_of"]),
            available_at=completed_at,
            payload=candidate_payload,
            source_refs=tuple(candidate.get("source_refs") or (run_source_ref,)),
        )
        existing = store.identity(
            leaf.owner, leaf.object_kind, leaf.object_id, leaf.epoch,
        )
        if existing is not None:
            if existing.get("payload") != candidate_payload:
                raise ValueError(
                    f"discovery candidate epoch collision: {candidate.get('candidate_id')}"
                )
            leaf = GoldenLeaf(
                owner=str(existing["owner"]),
                object_kind=str(existing["object_kind"]),
                object_id=str(existing["object_id"]),
                epoch=str(existing["epoch"]),
                occurred_at=str(existing["occurred_at"]),
                available_at=str(existing["available_at"]),
                payload=dict(existing["payload"]),
                source_refs=tuple(existing["source_refs"]),
            )
        candidate_leaves.append(leaf)
        input_edges.extend(
            GoldenEdge(leaf.leaf_sha256, str(input_leaf), "derived_from")
            for input_leaf in candidate.get("input_golden_leaves", [])
        )
    run_leaf = GoldenLeaf(
        owner=require_text(owner, "discovery owner"),
        object_kind="discovery_run",
        object_id="workspace-opportunity-discovery",
        epoch=declared,
        occurred_at=str(body["as_of"]),
        available_at=completed_at,
        payload={**body, "run_sha256": declared},
        source_refs=tuple(sorted({
            ref for candidate in body.get("candidates", [])
            if isinstance(candidate, Mapping)
            for ref in candidate.get("source_refs", [])
        }) or [run_source_ref]),
    )
    selection_edges = [
        GoldenEdge(run_leaf.leaf_sha256, leaf.leaf_sha256, "selects")
        for leaf in candidate_leaves
    ]
    result = store.append_bundle(
        (run_leaf, *candidate_leaves), (*selection_edges, *input_edges), make_heads=True,
    )
    return {
        "run_leaf": run_leaf.leaf_sha256,
        "candidate_leaves": {
            leaf.object_id: leaf.leaf_sha256 for leaf in candidate_leaves
        },
        "edge_count": len(result["edges"]),
    }


def record_agent_research_request(
    store: GoldenStore, *, owner: str, request: Mapping[str, Any]
) -> str:
    """Append an agent handoff bound to one immutable discovery candidate."""
    body = dict(request)
    declared = str(body.pop("request_sha256", ""))
    if body.get("schema") != "jaggedthoughts-agent-research-request-v1":
        raise ValueError("unsupported agent research request schema")
    if declared != stable_sha256(body):
        raise ValueError("agent research request content hash mismatch")
    candidate_leaf = require_text(body.get("candidate_leaf"), "request.candidate_leaf")
    candidate = store.get_leaf(candidate_leaf)
    owner_id = require_text(owner, "request owner")
    if candidate.get("object_kind") != "discovery_candidate":
        raise ValueError("agent research request must target a discovery candidate")
    if str(candidate.get("owner")) != owner_id:
        raise ValueError("agent research request and candidate owners differ")
    candidate_payload = candidate.get("payload") or {}
    expected = {
        "candidate_sha256": candidate_payload.get("candidate_sha256"),
        "candidate_id": candidate_payload.get("candidate_id"),
        "entity_id": candidate_payload.get("entity_id"),
        "entity_kind": candidate_payload.get("entity_kind"),
        "as_of": candidate_payload.get("as_of"),
    }
    if {key: body.get(key) for key in expected} != expected:
        raise ValueError("agent research request identity differs from its candidate")
    payload = {**body, "request_sha256": declared}
    leaf = GoldenLeaf(
        owner=owner_id,
        object_kind="agent_research_request",
        object_id=str(body["request_id"]),
        epoch=declared,
        occurred_at=str(body["created_at"]),
        available_at=str(body["created_at"]),
        payload=payload,
        source_refs=tuple(body.get("source_refs") or (f"candidate_leaf:{candidate_leaf}",)),
    )
    store.append_bundle(
        (leaf,),
        (GoldenEdge(leaf.leaf_sha256, candidate_leaf, "based_on"),),
    )
    return leaf.leaf_sha256


def _research_source_bundle(
    store: GoldenStore, *, owner: str, sources: Iterable[Mapping[str, Any]],
    available_at: str,
) -> tuple[list[GoldenLeaf], dict[str, str], dict[str, str]]:
    """Resolve cited documents to shared evidence leaves."""
    new_leaves: list[GoldenLeaf] = []
    source_leaf_by_id: dict[str, str] = {}
    source_url_by_id: dict[str, str] = {}
    pending_by_object_id: dict[str, str] = {}
    for source in sources:
        source_id = require_text(source.get("id"), "research source id")
        document = {
            "schema": "jaggedthoughts-research-source-evidence-v1",
            "document_id": stable_sha256({
                key: source.get(key) for key in (
                    "title", "url", "publisher", "published_at", "source_kind",
                )
            }),
            "title": source.get("title"), "url": source.get("url"),
            "publisher": source.get("publisher"),
            "published_at": source.get("published_at"),
            "source_kind": source.get("source_kind"),
        }
        object_id = f"research-source:{document['document_id']}"
        source_leaf_sha = pending_by_object_id.get(object_id, "")
        if not source_leaf_sha:
            try:
                source_leaf_sha = str(
                    store.head(owner, "research_source_evidence", object_id)["leaf_sha256"]
                )
            except KeyError:
                source_leaf = GoldenLeaf(
                    owner=owner, object_kind="research_source_evidence",
                    object_id=object_id, epoch=str(document["document_id"]),
                    occurred_at=available_at, available_at=available_at,
                    payload=document, source_refs=(str(source["url"]),),
                )
                new_leaves.append(source_leaf)
                source_leaf_sha = source_leaf.leaf_sha256
                pending_by_object_id[object_id] = source_leaf_sha
        source_leaf_by_id[source_id] = source_leaf_sha
        source_url_by_id[source_id] = str(source["url"])
    return new_leaves, source_leaf_by_id, source_url_by_id


def record_candidate_research_dossier(
    store: GoldenStore, *, owner: str, dossier: Mapping[str, Any],
    request_leaf: str, derived_from_dossier_leaf: str | None = None,
) -> str:
    """Append a validated dossier beneath its request and candidate leaves."""
    body = dict(dossier)
    declared = str(body.pop("dossier_sha256", ""))
    if body.get("schema") != "jaggedthoughts-candidate-research-dossier-v1":
        raise ValueError("unsupported candidate research dossier schema")
    if declared != stable_sha256(body):
        raise ValueError("candidate research dossier content hash mismatch")
    owner_id = require_text(owner, "dossier owner")
    request_sha = require_text(request_leaf, "dossier request leaf")
    request = store.get_leaf(request_sha)
    if request.get("owner") != owner_id or request.get("object_kind") != "agent_research_request":
        raise ValueError("candidate dossier must target an owned agent research request")
    request_payload = request.get("payload") or {}
    candidate_sha = require_text(body.get("candidate_leaf"), "dossier candidate leaf")
    candidate = store.get_leaf(candidate_sha)
    if candidate.get("owner") != owner_id or candidate.get("object_kind") != "discovery_candidate":
        raise ValueError("candidate dossier must target an owned discovery candidate")
    expected = {
        "candidate_leaf": request_payload.get("candidate_leaf"),
        "candidate_sha256": request_payload.get("candidate_sha256"),
        "entity_id": request_payload.get("entity_id"),
        "as_of": request_payload.get("as_of"),
        "request_id": request_payload.get("request_id"),
        "request_sha256": request_payload.get("request_sha256"),
    }
    if {key: body.get(key) for key in expected} != expected:
        raise ValueError("candidate dossier identity differs from its request")
    payload = {**body, "dossier_sha256": declared}
    generated_at = canonical_timestamp(body.get("generated_at"), "dossier generated_at")
    source_refs = tuple(
        str(source.get("url") or source.get("id"))
        for source in body.get("sources", ()) if isinstance(source, Mapping)
    ) or (f"request_leaf:{request_sha}",)
    leaf = GoldenLeaf(
        owner=owner_id,
        object_kind="candidate_research_dossier",
        object_id=f"research:{body['entity_id']}:{candidate_sha}",
        epoch=declared,
        occurred_at=generated_at,
        available_at=generated_at,
        payload=payload,
        source_refs=source_refs,
    )
    source_rows = [
        source for source in body.get("sources", ()) if isinstance(source, Mapping)
    ]
    source_leaves, source_leaf_by_id, source_url_by_id = _research_source_bundle(
        store, owner=owner_id, sources=source_rows, available_at=generated_at,
    )
    new_leaves: list[GoldenLeaf] = [leaf, *source_leaves]
    edges: list[GoldenEdge] = [
        GoldenEdge(leaf.leaf_sha256, request_sha, "based_on"),
        GoldenEdge(leaf.leaf_sha256, candidate_sha, "based_on"),
    ]
    if derived_from_dossier_leaf is not None:
        parent_sha = require_text(
            derived_from_dossier_leaf, "derived research dossier leaf",
        )
        parent = store.get_leaf(parent_sha)
        if (
            parent.get("owner") != owner_id
            or parent.get("object_kind") != "candidate_research_dossier"
            or not research_evidence_is_admissible(
                store, owner=owner_id, target_leaf=parent_sha,
            )
        ):
            raise ValueError("candidate dossier cannot derive from inadmissible research")
        edges.append(GoldenEdge(leaf.leaf_sha256, parent_sha, "derived_from"))
    for source in source_rows:
        source_id = require_text(source.get("id"), "dossier source id")
        edges.append(GoldenEdge(
            leaf.leaf_sha256, source_leaf_by_id[source_id], "cites",
            metadata={"source_id": source_id, "supports": list(source.get("supports") or ())},
        ))

    strategy = body.get("strategy") if isinstance(body.get("strategy"), Mapping) else {}
    for choice in strategy.get("choices") or ():
        if not isinstance(choice, Mapping):
            continue
        choice_id = require_text(choice.get("id"), "dossier strategy choice id")
        evidence_refs = tuple(str(value) for value in choice.get("evidence_refs") or ())
        claim_payload = {
            "schema": "jaggedthoughts-strategy-mechanism-claim-v1",
            "claim_id": (
                f"{body['entity_id']}:{candidate_sha}:{choice_id}"
            ),
            "entity_id": body["entity_id"], "candidate_leaf": candidate_sha,
            "request_sha256": body["request_sha256"],
            "choice_id": choice_id, "description": choice.get("description"),
            "evidence_refs": list(evidence_refs),
        }
        claim_leaf = GoldenLeaf(
            owner=owner_id, object_kind="strategy_mechanism_claim",
            object_id=str(claim_payload["claim_id"]),
            epoch=stable_sha256(claim_payload),
            occurred_at=generated_at, available_at=generated_at,
            payload=claim_payload,
            source_refs=tuple(source_url_by_id[value] for value in evidence_refs),
        )
        new_leaves.append(claim_leaf)
        edges.append(GoldenEdge(leaf.leaf_sha256, claim_leaf.leaf_sha256, "contains"))
        for source_id in evidence_refs:
            edges.append(GoldenEdge(
                claim_leaf.leaf_sha256, source_leaf_by_id[source_id], "supported_by",
                metadata={"source_id": source_id},
            ))
    for index, mechanism_edge in enumerate(strategy.get("reinforcing_edges") or ()):
        if not isinstance(mechanism_edge, Mapping):
            continue
        evidence_refs = tuple(str(value) for value in mechanism_edge.get("evidence_refs") or ())
        edge_identity = stable_sha256({
            "from": mechanism_edge.get("from"), "to": mechanism_edge.get("to"),
            "mechanism": mechanism_edge.get("mechanism"), "index": index,
        })
        claim_payload = {
            "schema": "jaggedthoughts-strategy-mechanism-edge-claim-v1",
            "claim_id": f"{body['entity_id']}:{candidate_sha}:edge:{edge_identity[:16]}",
            "entity_id": body["entity_id"], "candidate_leaf": candidate_sha,
            "request_sha256": body["request_sha256"],
            "claim_kind": "reinforcing_edge",
            "from_choice_id": mechanism_edge.get("from"),
            "to_choice_id": mechanism_edge.get("to"),
            "mechanism": mechanism_edge.get("mechanism"),
            "evidence_refs": list(evidence_refs),
        }
        claim_leaf = GoldenLeaf(
            owner=owner_id, object_kind="strategy_mechanism_claim",
            object_id=str(claim_payload["claim_id"]),
            epoch=stable_sha256(claim_payload),
            occurred_at=generated_at, available_at=generated_at,
            payload=claim_payload,
            source_refs=tuple(source_url_by_id[value] for value in evidence_refs),
        )
        new_leaves.append(claim_leaf)
        edges.append(GoldenEdge(leaf.leaf_sha256, claim_leaf.leaf_sha256, "contains"))
        for source_id in evidence_refs:
            edges.append(GoldenEdge(
                claim_leaf.leaf_sha256, source_leaf_by_id[source_id], "supported_by",
                metadata={"source_id": source_id},
            ))
    store.append_bundle(tuple(new_leaves), tuple(edges))
    return leaf.leaf_sha256


def record_research_reassessment(
    store: GoldenStore, *, owner: str, reassessment: Mapping[str, Any],
    reopen_request_leaf: str,
) -> str:
    """Append a validated source-triggered reassessment below its frozen request."""
    body = dict(reassessment)
    declared = str(body.pop("reassessment_sha256", ""))
    if body.get("schema") != "jaggedthoughts-research-reassessment-v1":
        raise ValueError("unsupported research reassessment schema")
    if declared != stable_sha256(body):
        raise ValueError("research reassessment content hash mismatch")
    owner_id = require_text(owner, "reassessment owner")
    request_sha = require_text(reopen_request_leaf, "reassessment request leaf")
    request = store.get_leaf(request_sha)
    if request.get("owner") != owner_id or request.get("object_kind") != "research_reopen_request":
        raise ValueError("research reassessment must target an owned reopen request")
    request_payload = request.get("payload") or {}
    expected = {
        "request_sha256": request_payload.get("request_sha256"),
        "entity_id": request_payload.get("entity_id"),
        "subscription_leaf": request_payload.get("subscription_leaf"),
        "prior_dossier_leaf": request_payload.get("prior_dossier_leaf"),
        "source_change_event_leaf": request_payload.get("source_change_event_leaf"),
    }
    if {key: body.get(key) for key in expected} != expected:
        raise ValueError("research reassessment identity differs from its reopen request")
    assessed_at = canonical_timestamp(body.get("assessed_at"), "reassessment assessed_at")
    payload = {**body, "reassessment_sha256": declared}
    leaf = GoldenLeaf(
        owner=owner_id,
        object_kind="research_reassessment",
        object_id=f"research-reassessment:{request_sha}",
        epoch=declared,
        occurred_at=assessed_at,
        available_at=assessed_at,
        payload=payload,
        source_refs=tuple(str(row["url"]) for row in body.get("sources") or ()),
    )
    source_rows = [
        source for source in body.get("sources", ()) if isinstance(source, Mapping)
    ]
    source_leaves, source_leaf_by_id, _ = _research_source_bundle(
        store, owner=owner_id, sources=source_rows, available_at=assessed_at,
    )
    prior_dossier = require_text(body.get("prior_dossier_leaf"), "prior dossier leaf")
    edges: list[GoldenEdge] = [
        GoldenEdge(leaf.leaf_sha256, request_sha, "based_on"),
        GoldenEdge(leaf.leaf_sha256, prior_dossier, "based_on"),
    ]
    for source in source_rows:
        source_id = require_text(source.get("id"), "reassessment source id")
        edges.append(GoldenEdge(
            leaf.leaf_sha256, source_leaf_by_id[source_id], "cites",
            metadata={"source_id": source_id, "supports": list(source.get("supports") or ())},
        ))
    store.append_bundle((leaf, *source_leaves), tuple(edges))
    return leaf.leaf_sha256


__all__ = [
    "GOLDEN_LEAF_SCHEMA",
    "RESEARCH_EVIDENCE_QUARANTINE_SCHEMA",
    "GoldenEdge",
    "GoldenLeaf",
    "GoldenStore",
    "decode_golden_body",
    "encode_golden_body",
    "record_research_evidence_quarantine",
    "research_evidence_admissibility",
    "research_evidence_is_admissible",
    "research_evidence_quarantine",
    "record_investment_decision",
    "record_investment_settlement",
    "record_funnel_transition",
    "record_company_quality_report",
    "record_discovery_run",
    "record_agent_research_request",
    "record_candidate_research_dossier",
    "record_research_reassessment",
    "record_market_flow_experiment",
    "record_mechanism_research_result",
    "record_opportunity_watchlist",
    "record_portfolio_assembly",
    "record_strategy_move_library",
    "record_company_contingent_recourse_selection",
    "record_strategy_program_adoption_request",
    "record_strategy_program_adoption_result",
    "record_strategy_program_outcome_plan",
    "record_strategy_program_outcome_episode",
    "record_strategy_program_control_outcome_plan",
    "record_strategy_program_control_outcome_episode",
    "record_world_model_tournament",
]
