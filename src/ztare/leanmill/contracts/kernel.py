"""Typed contracts + config foundation for the leanmill kernel (the world-class replacement for the
pervasive stringly-typed `dict.get(...)` / hand-rolled `.replace`/regex surfaces across the solver,
autoformalizer, and governance axes).

WHY (operator 2026-06-09): bare dicts passed between modules are the #1 bug class here — an integration
seam where one side writes `sorried_file` and the other reads `source_file`, or a result-shape drifts and a
`.get("results")` silently returns None (the real 2026-06-03 flywheel bug). A pydantic model makes the
shape EXPLICIT, VALIDATED ON CONSTRUCTION (a typo'd key / wrong type fails loud at the boundary, not three
calls later), and self-documenting. This module is the single home for those contracts; the convention is:

  • CONFIG (tactic cascades, thresholds, prover lists, timeouts) → a `YamlConfig` subclass + a YAML file.
  • CROSS-MODULE DATA (the proof `row`, a move's outcome) → a typed model here, with `.from_row` adapters
    at the boundaries so migration is incremental (existing dict call-sites keep working via `.to_row()`).
  • EXTERNAL-TOOL OUTPUT (Lean / Isabelle stdout) → still parsed, but with the PRODUCER's own decoder when
    one exists (e.g. `YXML.content_of`), regex only at the irreducible boundary.

Migration is INCREMENTAL and highest-bug-risk-first (see docs/concepts/leanmill_architecture.md § "Typed
contracts — the kernel data seams") — NOT a blind sweep (that would introduce the very bugs we're removing).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ── Config base: load-from-YAML convention (env override, validated, fail-loud on a bad value) ──────────
class YamlConfig(BaseModel):
    """Base for every leanmill config object. `load()` reads a YAML file (if present) → applies env
    overrides (via the subclass's `_env_map()`) → validates. A malformed YAML degrades to field defaults
    (a config file must never brick the kernel); a malformed VALUE (wrong type / out-of-range) fails loud."""

    model_config = ConfigDict(extra="forbid")  # a typo'd YAML key is an ERROR, not a silent no-op

    @classmethod
    def _env_map(cls) -> "dict[str, str]":
        """Override: {field_name: ENV_VAR} for ad-hoc env overrides of YAML values. Default: none."""
        return {}

    @classmethod
    def load(cls, path: "str | os.PathLike | None" = None, *, env_var: str = "") -> "YamlConfig":
        src = (path or (os.environ.get(env_var) if env_var else None))
        data: dict = {}
        if src and Path(src).exists():
            try:
                import yaml  # repo dep (requirements.txt)
                data = yaml.safe_load(Path(src).read_text(encoding="utf-8")) or {}
            except Exception:  # noqa: BLE001 — a broken YAML must not brick the kernel; fall back to defaults
                data = {}
        for field, env in cls._env_map().items():
            v = os.environ.get(env)
            if v is not None and v != "":
                data[field] = v
        return cls(**data)


# ── The proof TARGET (the `row` dict that flows through the solver — 7 keys, faithfully typed) ──────────
class ProofTarget(BaseModel):
    """A single proof target the solver attacks. Replaces the bare `row` dict (`row.get("source_file") or
    row.get("sorried_file")` — exactly the seam that drifts). `source_path()` ENCODES the source/sorried
    fallback so a call-site can never get it wrong again."""

    model_config = ConfigDict(extra="allow")  # tolerate extra row keys during incremental migration

    target_theorem_name: str = ""
    goal: str = ""
    source_file: str = ""
    sorried_file: str = ""
    row_id: Optional[str] = None
    # solver-internal annotations carried on the row (kept untyped Any until each is migrated)
    obstruction_seeds: Any = Field(default=None, alias="_obstruction_seeds")
    refine_context: Any = Field(default=None, alias="_refine_context")

    @field_validator("target_theorem_name", "goal", "source_file", "sorried_file", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        """A legacy row commonly carries an EXPLICIT `None` for an absent file/name (e.g. line 890 writes
        `row.get("source_file")` → None). The old `.get(k) or ""` access coerced that to ""; the typed model
        MUST do the same or `from_row` would raise where the dict path silently worked — the exact
        behaviour-drift this migration exists to PREVENT. So coerce None→"" for these str fields."""
        return "" if v is None else v

    @classmethod
    def from_row(cls, row: "dict | ProofTarget") -> "ProofTarget":
        """Adapter at a boundary: build from the legacy dict (or pass through a model). Tolerant — unknown
        keys are preserved (extra='allow'), missing keys default; the existing `_`-prefixed keys map via
        their aliases."""
        if isinstance(row, ProofTarget):
            return row
        return cls.model_validate(dict(row or {}))

    def source_path(self) -> str:
        """The real source file for this target — `source_file` preferred, else `sorried_file`. The single
        place this fallback lives (it was duplicated + drift-prone at every native_hammer/source call-site)."""
        return (self.source_file or self.sorried_file or "").strip()

    def to_row(self) -> dict:
        """Back to a plain dict (legacy call-sites that still expect one), aliases restored."""
        return self.model_dump(by_alias=True, exclude_none=True)


# ── A MOVE's outcome (replaces the ad-hoc (bool, str, str) tuples / result dicts) ───────────────────────
class MoveOutcome(BaseModel):
    """The result of one solver move. Replaces both the `(closed, proof_text, transcript)` tuples and the
    loose result dicts with their drifting `.get("results")`/`.get("proof")` keys. `meta` stays a dict for
    move-specific telemetry until each move's payload is itself worth typing."""

    closed: bool = False
    proof_text: str = ""
    transcript: str = ""
    move: str = ""
    meta: dict = Field(default_factory=dict)

    @classmethod
    def from_probe(cls, result: "tuple | MoveOutcome", *, move: str = "") -> "MoveOutcome":
        """Adapter for the legacy `(compile_ok, proof_text, transcript)` probe tuple."""
        if isinstance(result, MoveOutcome):
            return result
        closed, proof, transcript = (list(result) + ["", "", ""])[:3]
        return cls(closed=bool(closed), proof_text=str(proof or ""), transcript=str(transcript or ""), move=move)

    def as_tuple(self) -> "tuple[bool, str, str]":
        """Back to the legacy `(closed, proof_text, transcript)` shape for un-migrated call-sites."""
        return self.closed, self.proof_text, self.transcript


class AttackRecord(BaseModel):
    """One NL-line attack result from the notes/firewall→governed-solve loop (#49, 2026-06-13). Replaces the
    bare per-lemma dict that carried THE famous bug class: `solved` is decided ONCE, here, as
    `firewall_outcome == "closed"` — so no caller can re-derive it as `bool(outcome)` and read the TRUTHY
    strings "exact_gap"/"open" as a closure (that false-positive marked unproven gaps solved). `solved` is a
    typed BOOL field, so the bug is impossible by construction; `model_dump()` re-emits the legacy fields plus
    the solver's gap classification, so notes / Workbench can route gaps without re-classifying them.
    `extra="ignore"` keeps it forward-compatible."""

    model_config = ConfigDict(extra="ignore")

    nl: str
    lean_statement: str = ""
    faithful: Optional[bool] = None
    outcome: str = ""
    solved: bool = False                         # the invariant: ALWAYS a bool, True IFF outcome == "closed"
    faithfulness_reason: Optional[str] = None
    faithfulness_checks: Any = None              # list|dict, move-specific until worth typing
    decomposition: Any = None                    # the planner's sub-DAG (route_and_solve), #81
    failure_class: Optional[dict[str, Any]] = None  # solver's apparatus|math|cheat_caught classification
    budget_killed: bool = Field(default=False, strict=True)

    @classmethod
    def from_firewall_result(cls, r: "dict | AttackRecord", *, nl: str) -> "AttackRecord":
        """Build from `autoformalize_and_solve`'s result dict. CLOSURE = `r["solved"] == "closed"` (the
        firewall stuffs the OUTCOME string into `solved`); encoding it ONCE here is the whole point — every
        prior caller that did `bool(outcome)` reintroduced the gap-as-solved false positive."""
        if isinstance(r, AttackRecord):
            return r
        return cls(
            nl=nl,
            lean_statement=(r.get("lean_statement") or ""),
            faithful=r.get("faithful"),
            outcome=(r.get("outcome") or ""),
            solved=(r.get("solved") == "closed"),
            faithfulness_reason=r.get("faithfulness_reason"),
            faithfulness_checks=r.get("faithfulness_checks"),
            decomposition=r.get("decomposition"),
            failure_class=r.get("failure_class"),
            budget_killed=(False if r.get("budget_killed") is None else r.get("budget_killed")),
        )


# ── The OUTCOME VOCABULARY — single source of truth for the solver/firewall outcome strings (#49) ───────
# The bare string `"closed"` is compared in ~15 places (solver_core, proof_repair, autoformalize, the notes
# loop, the dashboard, run_standards) — every one a drift risk (a typo'd "close"/"Closed" silently scores a
# closure as not-closed, the AttackRecord truthy-string bug's sibling). Encode the vocabulary ONCE here; the
# typed accessors below (`MoveResult.is_closed`, `FirewallResult.is_admitted_closed`) are the canonical reads.
OUTCOME_CLOSED = "closed"
OUTCOME_FALSIFIED = "falsified"
OUTCOME_EXACT_GAP = "exact_gap"
FW_REJECTED = "rejected_by_firewall"           # the static firewall refused the formalization (sound: no solve)
FW_INADMISSIBLE = "inadmissible_provider_dead"  # dead instrument (#89) — NOT a faithful=False negative
FW_ADMITTED_PREFIX = "admitted_and_"            # admitted_and_<move outcome>, e.g. admitted_and_closed


class MoveResult(BaseModel):
    """The per-move result dict — `r0 = primary_result(solve())`. READ-ONLY typed accessor: encodes the
    `r0.get("outcome") == "closed"` test ONCE (it is duplicated 8× and each re-derivation can drift). Does NOT
    re-emit a dict (no lossy round-trip / no write-back) — construct it at a read site, ask `.is_closed`."""
    model_config = ConfigDict(extra="allow")   # keep proof_text / transcript / failure_class / meta untouched
    outcome: str = ""
    proof_text: str = ""
    failure_class: str = ""

    @field_validator("outcome", "proof_text", "failure_class", mode="before")
    @classmethod
    def _none_to_empty(cls, v):
        return "" if v is None else v

    @classmethod
    def from_dict(cls, r: "dict | MoveResult | None") -> "MoveResult":
        if isinstance(r, MoveResult):
            return r
        return cls.model_validate(dict(r or {}))

    @property
    def is_closed(self) -> bool:
        return self.outcome == OUTCOME_CLOSED

    @property
    def is_falsified(self) -> bool:
        return self.outcome == OUTCOME_FALSIFIED

    @property
    def has_proof(self) -> bool:
        return bool((self.proof_text or "").strip())


class GovernanceVerdict(BaseModel):
    """READ-ONLY accessor for the `res["governance"]` dict (`{governance_kernel:{passed,flags}, statement_
    integrity, integrity_unverified, error}`). Encodes the `_gov_verified = not gov.get("integrity_unverified")`
    derivation ONCE so a closure's trust state isn't recomputed (and drifted) at each consumer."""
    model_config = ConfigDict(extra="allow")
    governance_kernel: Any = None
    statement_integrity: Any = None
    integrity_unverified: Optional[bool] = None
    error: Optional[str] = None

    @classmethod
    def from_dict(cls, g: "dict | GovernanceVerdict | None") -> "GovernanceVerdict":
        if isinstance(g, GovernanceVerdict):
            return g
        return cls.model_validate(dict(g or {}))

    @property
    def integrity_verified(self) -> bool:
        """The closure's statement-integrity is VERIFIED iff the governance dict does NOT flag it unverified
        (mirrors solver_core `_gov_verified`). A bare/absent governance dict ⇒ verified (parity with the
        `not (… or {}).get("integrity_unverified")` default)."""
        return not bool(self.integrity_unverified)

    @property
    def kernel_passed(self) -> "bool | None":
        gk = self.governance_kernel
        return bool(gk.get("passed")) if isinstance(gk, dict) and gk.get("passed") is not None else None


class FirewallResult(BaseModel):
    """READ-ONLY typed accessor for `autoformalize_and_solve`'s result dict (the `out` dict — nl, lean_statement,
    faithful, outcome, solved, governance, decomposition, …). Encodes the FIREWALL outcome vocabulary ONCE: the
    firewall `outcome` is one of `rejected_by_firewall` / `inadmissible_provider_dead` / `admitted_and_<move>`,
    and a true CLOSURE is `outcome == admitted_and_closed` AND `solved == "closed"` (the `solved` field carries
    the move OUTCOME STRING — the exact AttackRecord truthy-string trap). Tolerant (`extra='allow'`); does NOT
    re-emit (no write-back) — the producer keeps mutating its dict, consumers read through this."""
    model_config = ConfigDict(extra="allow")
    nl: str = ""
    lean_statement: str = ""
    faithful: Optional[bool] = None
    outcome: str = ""
    solved: Any = None            # the move OUTCOME STRING (or None) — NOT a bool; `is_admitted_closed` decides
    governance: Any = None

    @classmethod
    def from_dict(cls, r: "dict | FirewallResult | None") -> "FirewallResult":
        if isinstance(r, FirewallResult):
            return r
        return cls.model_validate(dict(r or {}))

    @property
    def was_admitted(self) -> bool:
        return str(self.outcome or "").startswith(FW_ADMITTED_PREFIX)

    @property
    def is_admitted_closed(self) -> bool:
        """The ONLY true-closure predicate: admitted by the firewall AND the move closed it. Decided ONCE
        (`solved == "closed"`) so no caller reads the truthy string `solved` as a bool (the unproven-gap-as-
        solved false positive AttackRecord exists to kill)."""
        return self.was_admitted and self.solved == OUTCOME_CLOSED

    @property
    def is_rejected(self) -> bool:
        return self.outcome == FW_REJECTED

    @property
    def is_inadmissible(self) -> bool:
        return self.outcome == FW_INADMISSIBLE

    @property
    def governance_verdict(self) -> GovernanceVerdict:
        return GovernanceVerdict.from_dict(self.governance if isinstance(self.governance, dict) else None)


class SolveResult(BaseModel):
    """Top-level `solve()` / `solve_adhoc()` return contract.

    The solver still carries move-specific telemetry as dict extras, but the
    cross-module keys are validated at the boundary so a producer cannot omit
    or mistype the shape silently.
    """
    model_config = ConfigDict(extra="allow")

    results: list[dict[str, Any]] = Field(default_factory=list)
    quarantined_references: list[str] = Field(default_factory=list)
    closure_certificate: Optional[str] = None
    closure_lean: Optional[str] = None
    statement_false_verified: bool = False
    env_parity_retracted: bool = False
    governance: Any = None

    @field_validator("results", "quarantined_references", mode="before")
    @classmethod
    def _none_to_list(cls, v):
        return [] if v is None else v

    @classmethod
    def from_dict(cls, r: "dict | SolveResult | None") -> "SolveResult":
        if isinstance(r, SolveResult):
            return r
        return cls.model_validate(dict(r or {}))

    def primary(self) -> dict[str, Any]:
        return primary_result(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return dict(self.model_dump(exclude_none=False))


def primary_result(res: dict, *, warn_missing: bool = True) -> dict:
    """The first per-move result of a `solve()` return — replaces the flywheel-bug pattern
    `(res.get("results") or [{}])[0]` (roadmap #3). That pattern's silent `[{}]` default scored EVERY closure
    as not-closed when a producer omitted "results" (the 2026-06-03 flywheel bug). This (a) returns the LIVE
    dict reference when present — callers MUTATE the result (`r0["outcome"]="rejected_governance"`,
    `r0["failure_class"]=…`) and the writes MUST persist back into `res["results"][0]`, so this deliberately
    does NOT wrap in a pydantic copy (that would break the governance write-back — a worse bug) — and (b)
    fails LOUD when "results" is ABSENT (the producer-contract violation, distinct from an empty list = no
    move ran), so a future omission surfaces instead of silently mis-scoring. Behaviour-identical to the old
    expression otherwise. (Full typing of the result needs the organs' write-back migrated in the same diff;
    tracked under #49.)"""
    results = res.get("results")
    if results:
        return results[0]
    if warn_missing and "results" not in res:
        import warnings
        warnings.warn(f"solve() result has NO 'results' key — flywheel-bug signature (would score as "
                      f"not-closed). keys={sorted(res)[:12]}", stacklevel=2)
    return {}


def _selftest() -> int:
    fails: list[str] = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ProofTarget: source/sorried fallback encoded once
    t = ProofTarget.from_row({"target_theorem_name": "t", "goal": "g", "sorried_file": "/s.lean",
                              "_obstruction_seeds": [1], "row_id": "r1"})
    ok("ProofTarget.from_row maps fields + alias", t.target_theorem_name == "t" and t.obstruction_seeds == [1])
    ok("source_path() falls back to sorried_file", t.source_path() == "/s.lean")
    ok("source_file preferred over sorried", ProofTarget(source_file="/a", sorried_file="/b").source_path() == "/a")
    # BEHAVIOUR-EQUIVALENCE with the legacy `.get(k) or ""`: an EXPLICIT None must coerce to "", not raise
    for row in [{"source_file": None, "sorried_file": None}, {"source_file": None, "sorried_file": "/b"},
                {"goal": None, "target_theorem_name": None}, {}]:
        old_src = row.get("source_file") or row.get("sorried_file") or ""
        ok(f"from_row tolerates None like `.get() or ''` ({row})",
           ProofTarget.from_row(row).source_path() == (old_src or "").strip())
    ok("None goal/name coerce to ''", ProofTarget.from_row({"goal": None}).goal == "")
    ok("to_row round-trips the alias", t.to_row().get("_obstruction_seeds") == [1])
    ok("pass-through a model is idempotent", ProofTarget.from_row(t) is t)

    # primary_result: behaviour-equivalence with `(res.get("results") or [{}])[0]` + mutation preserved
    for res in [{"results": [{"outcome": "closed"}]}, {"results": []}, {"results": None}, {}]:
        old = (res.get("results") or [{}])[0]
        new = primary_result(res, warn_missing=False)
        ok(f"primary_result == legacy expr ({res})", new == old)
    _res = {"results": [{"outcome": "open"}]}
    _r0 = primary_result(_res); _r0["outcome"] = "rejected_governance"   # mutation MUST persist (live ref)
    ok("primary_result returns LIVE ref (governance write-back preserved)",
       _res["results"][0]["outcome"] == "rejected_governance")

    # MoveOutcome: tuple adapter
    mo = MoveOutcome.from_probe((True, "by simp", "tail"), move="native_hammer")
    ok("MoveOutcome.from_probe maps the legacy tuple", mo.closed and mo.proof_text == "by simp")
    ok("as_tuple round-trips", mo.as_tuple() == (True, "by simp", "tail"))

    # MoveResult: the `outcome == "closed"` vocabulary encoded once (behaviour-equivalence with the bare compare)
    for r in [{"outcome": "closed"}, {"outcome": "exact_gap"}, {"outcome": "falsified"}, {"outcome": None}, {}]:
        ok(f"MoveResult.is_closed == legacy compare ({r})",
           MoveResult.from_dict(r).is_closed == (r.get("outcome") == "closed"))
    ok("MoveResult.is_falsified", MoveResult.from_dict({"outcome": "falsified"}).is_falsified is True)
    ok("MoveResult.has_proof", MoveResult.from_dict({"proof_text": "by simp"}).has_proof and
       not MoveResult.from_dict({"proof_text": ""}).has_proof)
    ok("MoveResult tolerates None outcome (no crash, not closed)",
       MoveResult.from_dict({"outcome": None}).is_closed is False)
    ok("MoveResult keeps extra keys (extra=allow)",
       MoveResult.from_dict({"outcome": "closed", "transcript": "t"}).model_dump().get("transcript") == "t")

    # GovernanceVerdict: integrity_verified mirrors `not gov.get("integrity_unverified")`
    for g in [{"integrity_unverified": True}, {"integrity_unverified": False}, {}, None,
              {"governance_kernel": {"passed": True}}]:
        ok(f"GovernanceVerdict.integrity_verified == legacy ({g})",
           GovernanceVerdict.from_dict(g).integrity_verified == (not bool((g or {}).get("integrity_unverified"))))
    ok("GovernanceVerdict.kernel_passed reads the nested kernel",
       GovernanceVerdict.from_dict({"governance_kernel": {"passed": True}}).kernel_passed is True)
    ok("GovernanceVerdict.kernel_passed None when absent",
       GovernanceVerdict.from_dict({}).kernel_passed is None)

    # FirewallResult: the closure predicate is `admitted_and_* AND solved == "closed"` — NOT bool(solved)
    fw_closed = FirewallResult.from_dict({"outcome": "admitted_and_closed", "solved": "closed"})
    fw_gap = FirewallResult.from_dict({"outcome": "admitted_and_exact_gap", "solved": "exact_gap"})
    fw_rej = FirewallResult.from_dict({"outcome": "rejected_by_firewall", "solved": None})
    fw_inadm = FirewallResult.from_dict({"outcome": "inadmissible_provider_dead", "faithful": None})
    ok("FirewallResult: admitted_and_closed + solved=closed ⇒ is_admitted_closed", fw_closed.is_admitted_closed)
    ok("FirewallResult: TRUTHY-STRING TRAP — solved='exact_gap' is NOT a closure",
       fw_gap.is_admitted_closed is False and bool(fw_gap.solved) is True)   # bool(solved) would be the bug
    ok("FirewallResult: rejected is not admitted/closed", fw_rej.is_rejected and not fw_rej.was_admitted
       and not fw_rej.is_admitted_closed)
    ok("FirewallResult: inadmissible classified", fw_inadm.is_inadmissible and not fw_inadm.is_admitted_closed)
    ok("FirewallResult.was_admitted true for any admitted_and_*", fw_gap.was_admitted and fw_closed.was_admitted)
    ok("FirewallResult.governance_verdict bridges to GovernanceVerdict",
       FirewallResult.from_dict({"governance": {"integrity_unverified": True}}).governance_verdict.integrity_verified
       is False)
    # consistency with AttackRecord (same closure semantics, two contracts must agree)
    ar = AttackRecord.from_firewall_result({"solved": "closed", "outcome": "admitted_and_closed"}, nl="x")
    ok("AttackRecord.solved agrees with FirewallResult.is_admitted_closed", ar.solved == fw_closed.is_admitted_closed)

    # YamlConfig: extra key forbidden (fail-loud), env override
    class _C(YamlConfig):
        x: int = 1
        name: str = "d"

        @classmethod
        def _env_map(cls):
            return {"name": "_ZTARE_TEST_CFG_NAME"}
    ok("YamlConfig defaults when no file", _C.load().x == 1)
    try:
        _C(x=1, bogus=2); fails.append("YamlConfig should forbid extra keys")
    except Exception:  # noqa: BLE001
        ok("YamlConfig forbids a typo'd key (fail-loud)", True)
    os.environ["_ZTARE_TEST_CFG_NAME"] = "envd"
    try:
        ok("YamlConfig env override applies", _C.load().name == "envd")
    finally:
        os.environ.pop("_ZTARE_TEST_CFG_NAME", None)

    print("CONTRACTS SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
