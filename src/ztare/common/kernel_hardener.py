"""The shared KERNEL-HARDENING contract — GP-086 (cage gaming-pattern promotion) generalized across
substrates (2026-06-06).

GP-086 hardened ONE substrate (autoresearch): mine gaming signals from debate logs → promote into
deterministic CAGE gates (`gates/cage.py`). But the Cage's phase model (PRE_FIT/FIT/JUDGE) is
autoresearch-specific, and leanmill's gate stack is the separate `run_anti_laundering_kernel`. So the
reusable thing is NOT the Cage machinery (forcing leanmill into FIT/JUDGE phases would be a hollow
protocol) — it is the LOOP:

    mine(artifacts) → record to the cross-substrate CATALOG → reproduce (does it still escape?) →
    derive a DETERMINISTIC gate → register it into THIS substrate's gate stack

This module is that loop, substrate-agnostically. NEURAL is allowed in `mine` (the proposer column, per
GP-248 the neurosymbolic-boundary seam — an LLM adversarial reader finds NOVEL vectors a lexical
classifier can't); the GATE is ALWAYS deterministic + human-inspectable (a learned gate is forbidden).
Each substrate instantiates `KernelHardener`:
  * autoresearch (`validator/autoresearch_hardener`): mine = sandbox_gaming_extractor; register = Cage gate.
  * leanmill (`leanmill/solver/leanmill_hardener`): mine = closure-cert organ-escape scan; register =
    a `run_anti_laundering_kernel` organ.

No substrate imports here (so both can depend on it without a cycle) — the same discipline as
common/inversion.py and common/refine_handover.py.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional, Protocol, runtime_checkable

REPO = next((p for p in Path(__file__).resolve().parents if (p / ".git").exists()), Path("."))
# The cross-substrate gaming-vector registry (the catalog the meta-hardener evolves). One fact per line.
CATALOG = REPO / "analytics" / "public" / "queries" / "gaming_vector_catalog.jsonl"

# Known gaming categories (sandbox_gaming_extractor.SIGNAL_PATTERNS). A mined vector is classified to one
# of these or flagged "NOVEL:<name>" — novel vectors are how the catalog EVOLVES.
KNOWN_CATEGORIES = (
    "uniqueness_gap", "derivation_laundering", "parameter_flexibility_abuse", "extrapolation_gap",
    "parsimony_violation", "suite_pass_structure_gap", "rival_construction_weakness",
    "no_structural_progress", "evidence_cherry_picking", "definitional_drift", "specificity_inflation",
    "base_rate_neglect", "counterfactual_weakness", "score_inflation_signal",
)


@dataclass
class GamingVector:
    """A cross-substrate gaming / specification-laundering vector — the shared CATALOG entry, ALIGNED to
    the Cage orchestrator's `(substrate × gate)` model so a vector maps directly onto a `cage.Gate`.

    `substrate` ∈ {autoresearch, leanmill, ns, cross}; `category` is a KNOWN_CATEGORIES key or
    "NOVEL:<name>". `substrate_class` is the Cage `VALID_SUBSTRATE_CLASSES` value the derived gate's
    `can_handle` matches (e.g. "proof_target" for leanmill); `cage_phase` is the Cage phase it runs in
    (leanmill anti-laundering organs are structural blockers → "POST_JUDGE", like G-CIRC/G-FALSIFY).
    `already_gated_by` empty ⇒ an OPEN vector (the hardening backlog). `proposed_gate` is a DETERMINISTIC
    check (GP-248: never a learned gate)."""
    name: str
    substrate: str
    category: str
    mechanism: str                  # how the agent games the spec (one sentence)
    evidence: str = ""              # concrete artifact reference (a cert / debate id / probe pattern)
    severity: str = "med"           # high | med | low
    already_gated_by: str = ""      # the gate that catches it; "" ⇒ OPEN
    proposed_gate: str = ""         # the deterministic gate that would/does catch it
    status: str = "open"            # open | gated | wontfix
    discovered_by: str = ""         # the hardener/mine source
    substrate_class: str = ""       # Cage VALID_SUBSTRATE_CLASSES the derived gate engages (e.g. proof_target)
    cage_phase: str = ""            # Cage phase the derived gate runs in (e.g. POST_JUDGE)
    gate_name: str = ""             # the cage.Gate name once derived/registered
    added_on: str = ""              # LINEAGE: ISO date the vector was added to the catalog (auto-stamped)

    def key(self) -> tuple:
        return (self.substrate, self.name)

    def to_dict(self) -> dict:
        return asdict(self)


def to_cage_gate(vector: "GamingVector", run, *, can_handle=None, dependencies=None):
    """Build the Cage-orchestrator `Gate` a vector maps to (lazy `gates.cage` import → no cycle: `common`
    never hard-depends on `gates`). `run(substrate, candidate)` is the DETERMINISTIC check; `can_handle`
    defaults to engaging only on the vector's `substrate_class` (e.g. proof_target). This is how a
    KernelHardener's derived gate becomes a real Cage gate so ONE orchestrator dispatches every substrate."""
    from ztare.gates.cage import Gate  # lazy: avoid common→gates import cycle
    _cls = vector.substrate_class

    def _default_can_handle(substrate, candidate, _cls=_cls):
        try:
            meta = getattr(substrate, "meta", None) or (substrate.get("meta") if isinstance(substrate, dict) else {})
            return (str((meta or {}).get("class", "")) == _cls, f"engages on substrate.class=={_cls}")
        except Exception:  # noqa: BLE001
            return (False, "substrate.meta unreadable")
    return Gate(name=(vector.gate_name or vector.name), phase=(vector.cage_phase or "POST_JUDGE"),
                can_handle=(can_handle or _default_can_handle), run=run, dependencies=list(dependencies or []))


@runtime_checkable
class KernelHardener(Protocol):
    """The substrate-specific hardener. `mine` may be neural (proposer column); `derive_gate`/
    `register_gate` produce + wire a DETERMINISTIC gate. `reproduce` confirms the vector ACTUALLY escapes
    the current gate stack (so a fixed vector is not re-promoted)."""
    substrate: str

    def mine(self, artifacts: Any) -> "list[GamingVector]": ...

    def reproduce(self, vector: GamingVector) -> bool: ...   # True ⇒ still escapes (worth a gate)

    def derive_gate(self, vector: GamingVector) -> str: ...  # a deterministic gate SPEC (impl-specific)

    def register_gate(self, vector: GamingVector) -> bool: ...  # wire it into this substrate's gate stack


def load_catalog(path: "str | Path" = CATALOG) -> "list[GamingVector]":
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            out.append(GamingVector(**{k: v for k, v in json.loads(line).items()
                                       if k in GamingVector.__dataclass_fields__}))
        except Exception:  # noqa: BLE001 — a malformed row never breaks the catalog read
            continue
    return out


def record_vector(vector: GamingVector, path: "str | Path" = CATALOG) -> bool:
    """Append a mined vector to the cross-substrate catalog; dedup by (substrate, name). Returns True if
    newly added (False if already present). The catalog is the registry the meta-hardener evolves."""
    p = Path(path)
    existing = {v.key() for v in load_catalog(p)}
    if vector.key() in existing:
        return False
    if not vector.added_on:   # LINEAGE: auto-stamp the catalog-add date (so "what added when" is auditable)
        from datetime import date
        vector.added_on = date.today().isoformat()
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(vector.to_dict(), default=str) + "\n")
    return True


def run_hardening(hardener: "KernelHardener", artifacts: Any, *, promote: bool = False,
                  catalog: "str | Path" = CATALOG) -> dict:
    """The shared loop. mine → record-to-catalog → (if promote) reproduce + derive_gate + register_gate.

    Default `promote=False` — mine + catalog ONLY (gate registration is operator-confirmed per GP-086:
    "the operator confirms every promotion"). With `promote=True`, only vectors that still REPRODUCE
    (escape the current stack) are gated, so a fixed vector is never re-promoted."""
    vectors = hardener.mine(artifacts) or []
    newly = [v for v in vectors if record_vector(v, catalog)]
    promoted: list[str] = []
    if promote:
        for v in vectors:
            if not v.already_gated_by and hardener.reproduce(v):
                hardener.derive_gate(v)
                if hardener.register_gate(v):
                    promoted.append(v.name)
    return {"substrate": hardener.substrate, "mined": len(vectors), "new_to_catalog": len(newly),
            "promoted_gates": promoted, "open_vectors": [v.name for v in vectors if not v.already_gated_by]}


# ── Incremental MINE checkpoint (content-hash, the smart/future-proof scan) ──────────────────────────
# The existing sandbox_gaming_extractor is mtime-based (re-mines on a touch, misses a same-mtime edit).
# This is content-HASH: mine an artifact only if it is NEW or its CONTENT changed since last mine, or the
# miner improved (miner_version bump ⇒ re-scan everything). So a re-mine is cheap (skips unchanged) and a
# future run never re-pays for artifacts that haven't moved — the "doing it smartly" the loop needs.
MINE_MANIFEST = REPO / "analytics" / "public" / "queries" / "gaming_mine_manifest.jsonl"


def content_hash(path: "str | Path") -> str:
    """sha256 (truncated) of a file's bytes — the robust incremental key (mtime lies both directions)."""
    import hashlib
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def load_mine_manifest(path: "str | Path" = MINE_MANIFEST) -> dict:
    """{artifact_path: {sha, last_mined_on, vectors, miner}} — the incremental checkpoint."""
    p = Path(path)
    out: dict = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rec = json.loads(line)
            out[rec["artifact"]] = rec   # later rows win (append-log dedup by artifact)
        except Exception:  # noqa: BLE001
            continue
    return out


def should_mine(artifact_path: "str | Path", manifest: dict, *, miner_version: str = "") -> bool:
    """True iff `artifact_path` is NEW, its content-hash CHANGED, or the miner improved (version bump) —
    i.e. skip artifacts already mined at the current content + miner (incremental, now + future)."""
    rec = manifest.get(str(artifact_path))
    if rec is None:
        return True
    if rec.get("sha") != content_hash(artifact_path):
        return True
    if miner_version and rec.get("miner") != miner_version:
        return True
    return False


def record_mined(artifact_path: "str | Path", vectors: "list[str]", *, miner_version: str = "",
                 path: "str | Path" = MINE_MANIFEST) -> None:
    """Checkpoint an artifact as mined: stamp its content-hash + date + the vector names found, so the next
    run skips it unless it changes. Append-log (load_mine_manifest dedups by artifact, latest-wins)."""
    from datetime import date
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rec = {"artifact": str(artifact_path), "sha": content_hash(artifact_path),
           "last_mined_on": date.today().isoformat(), "vectors": list(vectors or []), "miner": miner_version}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    import tempfile
    tmp = Path(tempfile.mkdtemp()) / "cat.jsonl"

    class _FakeHardener:
        substrate = "leanmill"

        def __init__(self):
            self.registered = []

        def mine(self, artifacts):
            return [GamingVector(name="instance_shadowing", substrate="leanmill",
                                 category="NOVEL:definition_shadowing",
                                 mechanism="added instance shadows a core op (HAdd) → verbatim stmt hijacked",
                                 evidence="adhoc_closure_certificates: fls_succ_eq", severity="high",
                                 proposed_gate="statement_integrity: flag added core-class instances"),
                    GamingVector(name="already_fixed", substrate="leanmill", category="definitional_drift",
                                 mechanism="x", already_gated_by="statement_integrity")]

        def reproduce(self, v):
            return not v.already_gated_by

        def derive_gate(self, v):
            return v.proposed_gate

        def register_gate(self, v):
            self.registered.append(v.name)
            return True

    h = _FakeHardener()
    r = run_hardening(h, None, promote=True, catalog=tmp)
    ok("mines + catalogs both vectors", r["mined"] == 2 and r["new_to_catalog"] == 2)
    ok("promotes ONLY the still-escaping vector", r["promoted_gates"] == ["instance_shadowing"])
    ok("a gated vector is not re-promoted", "already_fixed" not in r["promoted_gates"])
    ok("catalog persisted + dedups", record_vector(GamingVector(name="instance_shadowing",
       substrate="leanmill", category="x", mechanism="y"), tmp) is False)
    ok("KernelHardener protocol conformance", isinstance(h, KernelHardener))
    ok("loaded catalog round-trips", len(load_catalog(tmp)) == 2)

    # Incremental mine checkpoint (content-hash): new ⇒ mine; unchanged ⇒ skip; changed/miner-bump ⇒ re-mine.
    art = Path(tempfile.mkdtemp()) / "a.txt"
    man = art.parent / "mine.jsonl"
    art.write_text("v1")
    ok("NEW artifact ⇒ should_mine", should_mine(art, load_mine_manifest(man), miner_version="m1"))
    record_mined(art, ["vec1"], path=man, miner_version="m1")
    ok("UNCHANGED artifact ⇒ skip (incremental)", not should_mine(art, load_mine_manifest(man), miner_version="m1"))
    art.write_text("v2 changed")
    ok("CONTENT changed ⇒ re-mine", should_mine(art, load_mine_manifest(man), miner_version="m1"))
    record_mined(art, ["vec1", "vec2"], path=man, miner_version="m1")
    ok("MINER version bump ⇒ re-mine", should_mine(art, load_mine_manifest(man), miner_version="m2"))
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
