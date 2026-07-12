"""State convergence — the CvRDT merge layer for LeanMill's distributed fact logs.

WHY THIS EXISTS (the honest distributed-systems story)
------------------------------------------------------
LeanMill's durable truth is a set of APPEND-ONLY fact logs (proof_cache,
no_good_store, faithfulness_store, conjecture_book, closure_certificates,
phase_timings) plus one OLTP store (work_queue, WAL SQLite, leases). The banked
`.lean` library is a *materialized view* derived from "bank" events. That is
event-sourcing: the log is the truth, everything else is a derived view.

Those fact logs are a GROW-ONLY SET of kernel-verified facts — i.e. a CvRDT
(convergent replicated data type). The merge of two replicas' logs is their
set UNION. Crucially, KERNEL VERIFICATION *is* the conflict-freedom guarantee:
every element is independently kernel-checkable, so the union is automatically
valid. The only possible "conflict" — the same Prop both proved and refuted —
is forbidden by kernel soundness, so a merge that surfaces both is a BUG
DETECTOR, not a conflict to resolve (see `detect_conflicts`).

This means the correct distributed design for the facts is LOG-UNION + view
re-derivation, NOT consensus/locking. We avoid Paxos entirely for the facts and
localize the one thing that needs linearizable compare-and-set (the work
queue's claim) to a single-owner coordinator node (out of scope here).

WHAT THIS MODULE DOES
---------------------
Replaces the old `vps_pull.sh` rsync FILE-CLOBBER (last-write-wins on the whole
file → offline writes on one node are silently lost) with record-level UNION:

    merged = union_by_identity(local_records, incoming_records)

The merge is:
  * idempotent      — merge(A, A) == A
  * commutative     — merge(A, B) ≡ merge(B, A)  (as sets; output is sorted)
  * associative     — order of pulls does not matter
  * monotonic       — facts only accumulate; a record is never dropped on merge
                      unless an identical (same-identity) record is already present

so re-pulling, pulling in any order, or pulling from N nodes all converge to the
same state. That is the CvRDT property.

Identity (what makes two records "the same fact") is per-store:
  * keyed stores (proof_cache, ...) declare `identity_fields` — provenance and
    incidental fields (source strings, host stamps) are NOT part of identity, so
    the SAME fact recorded on two nodes dedups correctly.
  * event logs (closure_certificates, phase_timings, ...) use a content hash of
    the whole record (minus underscore-prefixed provenance fields) — distinct
    events all survive; byte-identical re-pulls dedup.
  * UNKNOWN stores fall back to the content-hash default — SAFE BY DEFAULT: a
    new store never silently loses a distinct record (anti-sibling: the policy
    lives at the one chokepoint, callers do not opt in).

Stdlib only (json, hashlib, os, socket). No Lean, no LLM, no new deps.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Provenance: every durable record may carry underscore-prefixed metadata that
# is NOT part of the fact's identity. Writers stamp these; identity ignores them
# so the same fact from two nodes converges to one element.
# ---------------------------------------------------------------------------
_PROVENANCE_PREFIX = "_"  # any key starting with "_" is merge/provenance metadata


def node_id() -> str:
    """Stable identity of THIS replica. Env override, else hostname.

    Mirrors `work_queue.node_id()` so the proving lane and the discovery lane
    agree on what a node is called.
    """
    return os.environ.get("LEANMILL_NODE_ID") or socket.gethostname() or "unknown"


def stamp_provenance(rec: dict, *, seen_at: "float | None" = None) -> dict:
    """Return a copy of `rec` with `_node` provenance, if absent.

    Non-destructive and identity-preserving: provenance lives under
    underscore-prefixed keys, which `record_identity` ignores. Writers call
    this at the WRITE chokepoint so every fact carries its origin; the merge
    never fabricates provenance (a record without `_node` is from before
    stamping was introduced and merges fine — its identity is unchanged).
    """
    if "_node" in rec:
        return rec
    out = dict(rec)
    out["_node"] = node_id()
    if seen_at is not None:
        out["_seen_at"] = seen_at
    return out


# ---------------------------------------------------------------------------
# Per-store merge policy. ONE registry = the single door. `identity_fields=None`
# means "content hash of the whole record (minus provenance)".
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MergeSpec:
    # Fields that DEFINE a record's identity. None => content hash of the whole
    # record minus underscore-prefixed provenance. Listed fields whose values
    # are dicts/lists are canonicalized; missing fields hash as null.
    identity_fields: "tuple[str, ...] | None" = None
    # Human note for the registry / docs.
    note: str = ""


# Registry keyed by the jsonl basename (the canonical store filename). New
# stores are SAFE without an entry — they get the content-hash default.
STORE_SPECS: "dict[str, MergeSpec]" = {
    # DP table: one verified proof per normalized-statement key. Two nodes that
    # prove the same statement (possibly different proof text / source) converge
    # to one deterministic record. Identity = the key only.
    "solver_lane_proof_cache.jsonl": MergeSpec(
        identity_fields=("key",),
        note="proof DP table; collapse to one per statement-key",
    ),
    # Grow-only refutation ledger. A statement may carry several distinct
    # failure classes / witnesses — all are valid facts. `source` is incidental.
    "solver_lane_no_good_store.jsonl": MergeSpec(
        identity_fields=("key", "failure_class", "witness"),
        note="refutation facts; grow by (key, class, witness)",
    ),
    # Faithfulness verdicts keyed by fingerprint+kind. `source`/`nl` incidental.
    "solver_lane_faithfulness_store.jsonl": MergeSpec(
        identity_fields=("key", "fingerprint", "kind"),
        note="faithfulness verdicts; grow by (key, fingerprint, kind)",
    ),
    # Bank events: the source-of-truth log the .lean library (materialized view)
    # is folded from. One rung per (substrate, content-stable name); two nodes
    # banking the same fact converge to one. `family_lemma_library.rederive_*`
    # rebuilds the .lean from the union of these.
    "solver_lane_bank_events.jsonl": MergeSpec(
        identity_fields=("substrate", "name"),
        note="bank events (the library's source-of-truth log); union by (substrate, name)",
    ),
    # Event logs: each row is a distinct event. Content-hash default keeps every
    # distinct event and dedups byte-identical re-pulls. Listed explicitly for
    # documentation; identity_fields=None == default.
    "conjecture_book.jsonl": MergeSpec(note="evidence event log (content hash)"),
    "adhoc_closure_certificates.jsonl": MergeSpec(note="closure event log (content hash)"),
    "solver_lane_phase_timings.jsonl": MergeSpec(note="timing event log (content hash)"),
}

DEFAULT_SPEC = MergeSpec(note="UNKNOWN store — safe content-hash G-Set default")


def spec_for(path: "str | Path") -> MergeSpec:
    """The merge policy for a store path, by basename. Unknown => safe default."""
    return STORE_SPECS.get(Path(path).name, DEFAULT_SPEC)


# ---------------------------------------------------------------------------
# Identity + canonicalization
# ---------------------------------------------------------------------------
def _canonical(obj) -> str:
    """Deterministic JSON: sorted keys, no whitespace. Stable across nodes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _strip_provenance(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if not k.startswith(_PROVENANCE_PREFIX)}


def record_identity(rec: dict, spec: MergeSpec) -> str:
    """Stable identity hash for a record under a spec.

    Provenance (underscore-prefixed) fields NEVER affect identity, so the same
    fact from two nodes hashes equal and converges to one element.
    """
    if spec.identity_fields is None:
        payload = _canonical(_strip_provenance(rec))
    else:
        payload = _canonical([rec.get(f) for f in spec.identity_fields])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# The merge (CvRDT union)
# ---------------------------------------------------------------------------
def union_by_identity(
    *record_lists: "list[dict]", spec: MergeSpec
) -> "list[dict]":
    """Set-union N record lists by identity. Deterministic, order-independent.

    When two records share identity but differ (e.g. proof_cache: same key, two
    proof bodies), the tie-break keeps the record whose canonical JSON is
    lexicographically smallest — a total, node-agnostic order, so every replica
    picks the SAME survivor regardless of merge direction. Output is sorted by
    canonical JSON for a stable, diff-friendly, git-clean file.
    """
    chosen: "dict[str, str]" = {}   # identity -> canonical JSON of the survivor
    survivors: "dict[str, dict]" = {}  # identity -> survivor record
    for records in record_lists:
        for rec in records:
            if not isinstance(rec, dict):
                continue
            ident = record_identity(rec, spec)
            canon = _canonical(rec)
            prev = chosen.get(ident)
            if prev is None or canon < prev:
                chosen[ident] = canon
                survivors[ident] = rec
    return sorted(survivors.values(), key=_canonical)


# ---------------------------------------------------------------------------
# File-level helpers
# ---------------------------------------------------------------------------
def read_jsonl(path: "str | Path") -> "list[dict]":
    p = Path(path)
    if not p.exists():
        return []
    out: "list[dict]" = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue  # tolerate a torn final line (crash mid-append)
        if isinstance(obj, dict):
            out.append(obj)
    return out


def write_jsonl(path: "str | Path", records: "list[dict]") -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace: write to a temp sibling then rename, so a reader never
    # sees a half-written merged file.
    tmp = p.with_suffix(p.suffix + ".merge.tmp")
    tmp.write_text("".join(_canonical(r) + "\n" for r in records), encoding="utf-8")
    os.replace(tmp, p)


@dataclass
class MergeReport:
    path: str
    local_before: int = 0
    incoming: int = 0
    merged_total: int = 0
    added_from_incoming: int = 0
    spec_note: str = ""

    @property
    def changed(self) -> bool:
        return self.added_from_incoming > 0

    def line(self) -> str:
        tag = "MERGED" if self.changed else "noop"
        return (
            f"[{tag}] {Path(self.path).name}: local={self.local_before} "
            f"+incoming={self.incoming} -> {self.merged_total} "
            f"(+{self.added_from_incoming} new)  [{self.spec_note}]"
        )


def merge_into(local_path: "str | Path", incoming_path: "str | Path") -> MergeReport:
    """Union `incoming_path` into `local_path` in place (idempotent).

    This is the replacement for rsync-clobber. Safe to run in EITHER direction
    and any number of times — it converges. Returns a report; only rewrites the
    file when the merge actually adds records (keeps git diffs honest).
    """
    spec = spec_for(local_path)
    local = read_jsonl(local_path)
    incoming = read_jsonl(incoming_path)

    local_idents = {record_identity(r, spec) for r in local}
    merged = union_by_identity(local, incoming, spec=spec)
    added = sum(1 for r in incoming if record_identity(r, spec) not in local_idents)

    rep = MergeReport(
        path=str(local_path),
        local_before=len(local),
        incoming=len(incoming),
        merged_total=len(merged),
        added_from_incoming=added,
        spec_note=spec.note,
    )
    # Rewrite if the merge changed the content OR canonicalized an unsorted file.
    if rep.changed or merged != local:
        write_jsonl(local_path, merged)
    return rep


def merge_sqlite_by_key(local_db: "str | Path", incoming_db: "str | Path", table: str, key: str,
                        *, apply: bool = True) -> MergeReport:
    """The jsonl merge's sqlite sibling: converge a table the same CvRDT way — insert rows whose natural `key` is
    absent, never overwrite. Idempotent and order-free (keyed, not positional). Uses the INTERSECTION of the two
    nodes' columns, so a drifted schema still merges. `apply=False` reports the delta without writing (dry-run)."""
    con = sqlite3.connect(str(local_db), timeout=30)
    try:
        con.execute("PRAGMA busy_timeout=30000")
        con.execute("ATTACH ? AS src", (str(incoming_db),))
        mcols = [r[1] for r in con.execute(f"PRAGMA main.table_info({table})")]
        scols = [r[1] for r in con.execute(f"PRAGMA src.table_info({table})")]
        cols = [c for c in mcols if c in scols]
        if key not in cols:
            raise ValueError(f"natural key {key!r} missing from {table} on one node")
        collist = ",".join(cols)
        before = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        src_total = con.execute(f"SELECT COUNT(*) FROM src.{table}").fetchone()[0]
        add = con.execute(f"SELECT COUNT(*) FROM src.{table} "
                          f"WHERE {key} NOT IN (SELECT {key} FROM {table})").fetchone()[0]
        if apply and add:
            con.execute(f"INSERT INTO {table} ({collist}) SELECT {collist} FROM src.{table} "
                        f"WHERE {key} NOT IN (SELECT {key} FROM {table})")
            con.commit()
        total = before + (add if apply else 0)
        return MergeReport(path=str(local_db), local_before=before, incoming=src_total,
                           merged_total=total, added_from_incoming=add, spec_note=f"sqlite {table} by {key}")
    finally:
        con.close()


# ---------------------------------------------------------------------------
# The DDIA-elegant bit: the merge as a soundness BUG DETECTOR.
# A statement both PROVED (proof_cache) and REFUTED (no_good_store) violates
# kernel soundness — it cannot be a legitimate merge conflict. Surface it.
# ---------------------------------------------------------------------------
@dataclass
class Conflict:
    key: str
    detail: str


def _is_confirmed_refutation_class(failure_class: str) -> bool:
    fc = str(failure_class or "")
    return fc == "statement_false" or fc.startswith("refut")


def detect_conflicts(queries_dir: "str | Path") -> "list[Conflict]":
    """Cross-store soundness check after a merge.

    Returns the (statement-key) collisions that should be IMPOSSIBLE under
    kernel soundness: the same normalized-statement key recorded as both a
    cached proof and a confirmed refutation. An empty list is the healthy case.
    """
    d = Path(queries_dir)
    proved = {
        r.get("key")
        for r in read_jsonl(d / "solver_lane_proof_cache.jsonl")
        if r.get("key")
    }
    refuted: "dict[str, str]" = {}
    for r in read_jsonl(d / "solver_lane_no_good_store.jsonl"):
        k = r.get("key")
        # Only a CONFIRMED counterexample refutes a Prop; a tactical dead-end
        # (failure_class without a witness) is not a soundness claim.
        fc = r.get("failure_class") or ""
        if k and r.get("witness") and _is_confirmed_refutation_class(fc):
            refuted[k] = fc
    out: "list[Conflict]" = []
    for k in sorted(proved & set(refuted)):
        out.append(Conflict(key=k, detail=f"proved AND refuted ({refuted[k]})"))
    return out


# Canonical default set of stores to converge on a pull (the append-only logs).
# The read-only daemon-owned snapshots are NOT here — they are authoritative on
# the VPS and rightly clobber-copied, never merged.
CONVERGENT_STORES = tuple(STORE_SPECS.keys())

# The sqlite sibling of STORE_SPECS: DB stores that reconcile by a natural key via `merge_sqlite_by_key`, so a
# cross-node pull unions their rows instead of clobbering one node's with the other's. `{filename: (table, key)}`.
DB_STORES: "dict[str, tuple[str, str]]" = {
    "solver_lane_attempts.db": ("attempts", "row_id"),
}


def merge_dir(local_dir: "str | Path", incoming_dir: "str | Path") -> "list[MergeReport]":
    """Merge every convergent store found in `incoming_dir` into `local_dir`."""
    reports: "list[MergeReport]" = []
    for name in CONVERGENT_STORES:
        inc = Path(incoming_dir) / name
        if inc.exists():
            reports.append(merge_into(Path(local_dir) / name, inc))
    return reports


# ---------------------------------------------------------------------------
# CLI:  python -m ztare.leanmill.state_convergence <cmd>
# ---------------------------------------------------------------------------
def _cli(argv: "list[str] | None" = None) -> int:
    ap = argparse.ArgumentParser(prog="state_convergence", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    m = sub.add_parser("merge", help="union an incoming jsonl store into a local one")
    m.add_argument("local")
    m.add_argument("incoming")

    md = sub.add_parser("merge-dir", help="merge all convergent stores from a staging dir")
    md.add_argument("local_dir")
    md.add_argument("incoming_dir")

    c = sub.add_parser("conflicts", help="soundness check: proved-AND-refuted keys")
    c.add_argument("queries_dir")

    sub.add_parser("selftest", help="run the CvRDT property selftest")

    ns = ap.parse_args(argv)

    if ns.cmd == "merge":
        rep = merge_into(ns.local, ns.incoming)
        print(rep.line())
        return 0
    if ns.cmd == "merge-dir":
        reports = merge_dir(ns.local_dir, ns.incoming_dir)
        for rep in reports:
            print(rep.line())
        confs = detect_conflicts(ns.local_dir)
        for conf in confs:
            print(f"[CONFLICT] {conf.key}: {conf.detail}", file=sys.stderr)
        return 1 if confs else 0
    if ns.cmd == "conflicts":
        confs = detect_conflicts(ns.queries_dir)
        for conf in confs:
            print(f"[CONFLICT] {conf.key}: {conf.detail}")
        print(f"{len(confs)} conflict(s)")
        return 1 if confs else 0
    if ns.cmd == "selftest":
        return _selftest()
    return 2


def _selftest() -> int:
    import tempfile

    fails: "list[str]" = []

    def check(name: str, cond: bool) -> None:
        print(("  ok  " if cond else " FAIL ") + name)
        if not cond:
            fails.append(name)

    # --- identity ignores provenance ---
    spec = STORE_SPECS["solver_lane_proof_cache.jsonl"]
    a = {"key": "K1", "proof": "by simp", "source": "nodeA", "_node": "alpha"}
    b = {"key": "K1", "proof": "by simp", "source": "nodeB", "_node": "beta"}
    check("identity ignores provenance/source for keyed store",
          record_identity(a, spec) == record_identity(b, spec))

    # --- content-hash default ignores _provenance but keeps semantic diffs ---
    dspec = DEFAULT_SPEC
    e1 = {"phase": "leaf", "ts": 1.0, "_node": "alpha"}
    e2 = {"phase": "leaf", "ts": 1.0, "_node": "beta"}
    e3 = {"phase": "leaf", "ts": 2.0}
    check("content-hash default dedups by provenance-stripped content",
          record_identity(e1, dspec) == record_identity(e2, dspec))
    check("content-hash default keeps semantically distinct events",
          record_identity(e1, dspec) != record_identity(e3, dspec))

    # --- idempotency: merge(A, A) == A ---
    A = [{"key": "K1", "proof": "p1"}, {"key": "K2", "proof": "p2"}]
    once = union_by_identity(A, spec=spec)
    twice = union_by_identity(A, A, spec=spec)
    check("idempotent: union(A) == union(A, A)", once == twice and len(once) == 2)

    # --- commutativity: union(A,B) == union(B,A) ---
    B = [{"key": "K2", "proof": "p2"}, {"key": "K3", "proof": "p3"}]
    ab = union_by_identity(A, B, spec=spec)
    ba = union_by_identity(B, A, spec=spec)
    check("commutative: union(A,B) == union(B,A)", ab == ba)
    check("union grows to the distinct keys (K1,K2,K3)", len(ab) == 3)

    # --- deterministic tie-break: same key, different proof -> same survivor ---
    C = [{"key": "K1", "proof": "zzz"}]
    D = [{"key": "K1", "proof": "aaa"}]
    cd = union_by_identity(C, D, spec=spec)
    dc = union_by_identity(D, C, spec=spec)
    check("deterministic tie-break independent of merge order", cd == dc and len(cd) == 1)

    # --- file round-trip: merge_into is idempotent on disk ---
    with tempfile.TemporaryDirectory() as td:
        local = Path(td) / "solver_lane_proof_cache.jsonl"
        inc = Path(td) / "incoming.jsonl"
        local.write_text("".join(json.dumps(r) + "\n" for r in A), encoding="utf-8")
        inc.write_text("".join(json.dumps(r) + "\n" for r in B), encoding="utf-8")
        # rename incoming to the canonical store name so spec_for matches
        inc2 = Path(td) / "solver_lane_proof_cache.incoming.jsonl"
        inc.rename(inc2)
        r1 = merge_into(local, inc2)
        r2 = merge_into(local, inc2)  # second merge must be a noop
        check("merge_into adds new records on first pass", r1.added_from_incoming == 1)
        check("merge_into is idempotent (second pass noop)", r2.added_from_incoming == 0)
        check("merged file has 3 records", len(read_jsonl(local)) == 3)

    # --- conflict detector ---
    with tempfile.TemporaryDirectory() as td:
        d = Path(td)
        (d / "solver_lane_proof_cache.jsonl").write_text(
            json.dumps({"key": "BAD", "proof": "by trivial"}) + "\n", encoding="utf-8")
        (d / "solver_lane_no_good_store.jsonl").write_text(
            json.dumps({"key": "BAD", "failure_class": "refuted",
                        "witness": "n=2"}) + "\n", encoding="utf-8")
        confs = detect_conflicts(d)
        check("conflict detector flags proved-AND-refuted", len(confs) == 1)
        (d / "solver_lane_no_good_store.jsonl").write_text(
            json.dumps({"key": "BAD", "failure_class": "statement_false",
                        "witness": "counterexample"}) + "\n", encoding="utf-8")
        confs = detect_conflicts(d)
        check("conflict detector flags proved-AND-statement_false", len(confs) == 1)
        (d / "solver_lane_no_good_store.jsonl").write_text(
            json.dumps({"key": "OK", "failure_class": "timeout",
                        "witness": ""}) + "\n", encoding="utf-8")
        check("conflict detector clean when no soundness collision",
              len(detect_conflicts(d)) == 0)

    print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_cli())
